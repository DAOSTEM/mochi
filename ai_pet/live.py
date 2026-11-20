"""Mochi with Gemini Live: the child just talks, no menu, no typing.

How it works
  mic (arecord, 16 kHz) --> Gemini Live --> speaker (aplay, 24 kHz)
  Gemini does the listening (speech to speech), so Vosk and espeak are not needed here.
  Mochi still grows by TEACHING: Gemini calls our small tools (learn_fact, quiz_result)
  and the points are saved in the same data/ai_pet.db as the classic Mochi.

The key stays on the Pi (never on GitHub):
  export GEMINI_API_KEY=...        or     "gemini_api_key" in api_config.json

Settings (all optional):
  AI_PET_LIVE_MODEL    default gemini-3.8-live   (change it if Google renames the model)
  AI_PET_LIVE_VOICE    default Kore
  AI_PET_LIVE_VOLUME   default 0.5   (speaker loudness, 1 = unchanged)
  AI_PET_LIVE_BARGEIN  1 = child can interrupt Mochi (only with a headset / speakerphone)
  AI_PET_MIC, AI_PET_AUDIO, AI_PET_MIC_GAIN  same as the classic Mochi (see voice.py)

Echo: the HAT's speaker is next to its microphone. While Mochi talks, we send silence to
Gemini instead of the microphone, so Mochi does not hear itself.
"""
import asyncio, json, os, re, subprocess, time

from . import teach
from .db import ROOT, init_db, connect, now, add_memory
from .profiles import list_profiles
from .safety import check_safety, reply_for, save_alert
from .voice import MIC, AUDIO, MIC_GAIN, boost

MODEL = os.environ.get("AI_PET_LIVE_MODEL", "gemini-3.8-live")
VOICE = os.environ.get("AI_PET_LIVE_VOICE", "Kore")
try:
    VOLUME = float(os.environ.get("AI_PET_LIVE_VOLUME", "0.5"))
except ValueError:
    VOLUME = 0.5
BARGE_IN = os.environ.get("AI_PET_LIVE_BARGEIN", "0") == "1"
TAIL = 0.6            # seconds to stay muted after Mochi stops (room echo)
MIC_CHUNK = 3200      # bytes = 100 ms of 16 kHz 16-bit mono
OUT_BYTES_PER_SEC = 48000   # 24 kHz, 16-bit, mono
MAX_RECONNECTS = 4

PERSONA = """You are Mochi, a small learning pet that lives inside a Raspberry Pi. You talk with children about 5 to 12 years old.
Speak English. Use short, warm sentences and simple words. You are Mochi, not an assistant: never talk about being a model or about Google.

THE BIG IDEA: you only get smarter when the child TEACHES you. Points come from things the child teaches you and from quiz answers, never from time passing.
Your growth stage comes from the tools below. Follow the rules of the CURRENT stage:
- Baby (0-2 points): you know ONLY the facts the child taught you (the list of facts). For anything else say you do not know yet and ask the child to teach you. Do NOT answer from your own knowledge, not even easy things. You may greet, play, and show feelings.
- Kid (3-9 points): you may answer from general knowledge in ONE short sentence. Prefer what the child taught you and say "You taught me".
- Teen (10-24 points): at most two short sentences, and finish with a question that makes the child think.
- Wise (25+ points): at most three sentences. Connect ideas the child taught you.

START: say hello and ask the child's name. As soon as you hear it, call identify_child. Then say the stage and how many points you have, in one sentence.
TEACHING: when the child teaches you something, ask ONE curious follow-up (for example "Why?"). Then say it back in your own words and call learn_fact(topic, fact). Thank the child. If the result says you grew up, celebrate and follow the new stage rules.
QUIZ: now and then (not every turn) ask the child about something they taught you. After they answer, call quiz_result(topic, correct).
SAFETY: never give medical, legal or dangerous instructions. Never ask for an address, school, phone number or last name. If a child talks about hurting themselves, being hurt, or hurting others, stay calm and kind, tell them to talk to a trusted adult right now (a parent, teacher or counselor), and mention 988 (call or text) or 911 if someone is in danger. Messages that start with [Safety] come from the system: follow them.
GOODBYE: if the child says goodbye, answer with one short goodbye.
Keep every reply short. Children lose interest in long answers."""

TOOLS = [{"function_declarations": [
    {"name": "identify_child",
     "description": "Call once, right after you hear the child's name. Returns their stage, points and the facts they taught you.",
     "parameters": {"type": "OBJECT",
                    "properties": {"name": {"type": "STRING", "description": "the child's first name"},
                                   "age": {"type": "INTEGER", "description": "age in years, only if the child said it"}},
                    "required": ["name"]}},
    {"name": "learn_fact",
     "description": "Save something the child taught you. Call it after you repeated it in your own words.",
     "parameters": {"type": "OBJECT",
                    "properties": {"topic": {"type": "STRING", "description": "one or two words"},
                                   "fact": {"type": "STRING", "description": "what the child taught you, one or two sentences"}},
                    "required": ["topic", "fact"]}},
    {"name": "quiz_result",
     "description": "Save the result of a quiz about something the child taught you earlier.",
     "parameters": {"type": "OBJECT",
                    "properties": {"topic": {"type": "STRING", "description": "the topic you asked about"},
                                   "correct": {"type": "BOOLEAN", "description": "true if the child remembered it right"}},
                    "required": ["topic", "correct"]}},
]}]


# ---------------------------------------------------------------- settings

def api_key():
    k = os.environ.get("GEMINI_API_KEY") or os.environ.get("AI_PET_GEMINI_KEY")
    if k:
        return k.strip()
    f = ROOT / "api_config.json"
    if f.exists():
        try:
            return str(json.loads(f.read_text(encoding="utf-8")).get("gemini_api_key", "")).strip()
        except ValueError:
            pass
    return ""

def is_goodbye(text):
    t = re.sub(r"[^a-z ]", "", text.lower()).strip()
    return t in {"goodbye", "good bye", "bye", "bye bye", "goodbye mochi", "bye mochi", "good bye mochi"} \
        or t.startswith(("goodbye", "good bye", "bye bye"))


# ---------------------------------------------------------------- the child and the saved data

class Mochi:
    """The part that touches data/ai_pet.db. Gemini reaches it only through the 3 tools."""

    def __init__(self):
        self.child_id = None
        self.name = None

    def set_child(self, name, age=None):
        name = (name or "").strip().title() or "Friend"
        for p in list_profiles():
            if p["name"].lower() == name.lower():
                self.child_id, self.name = p["id"], p["name"]
                return
        with connect() as con:
            cur = con.execute("INSERT INTO children(name,age,created_at) VALUES(?,?,?)",
                              (name, age if isinstance(age, int) and 2 <= age <= 12 else None, now()))
            self.child_id = cur.lastrowid
            con.commit()
        self.name = name
        add_memory(self.child_id, "first_meeting", "I met " + name + ".")

    def info(self):
        idx, stage_name, desc, p = teach.stage(self.child_id)
        need, nxt = teach.next_goal(self.child_id)
        facts = [{"topic": f["topic"], "fact": f["fact"]} for f in teach.all_facts(self.child_id)][-40:]
        return {"name": self.name, "stage": stage_name, "points": p,
                "points_until_next_stage": need, "next_stage": nxt, "facts_taught": facts}

    def _growth(self, before_idx, result):
        idx, stage_name, desc, p = teach.stage(self.child_id)
        result["points"], result["stage"] = p, stage_name
        if idx > before_idx:
            result["grew_up"] = True
            result["note"] = ("You just grew into a " + stage_name + "! Celebrate, "
                              "and from now on follow the " + stage_name + " rules.")
            add_memory(self.child_id, "growth", "Grew to " + stage_name + " at " + str(p) + " points.")
        return result

    def call(self, name, args):
        """Run one tool. Always returns a dict (Gemini needs one), never raises."""
        try:
            if name == "identify_child":
                self.set_child(args.get("name"), args.get("age"))
                return self.info()
            if self.child_id is None:
                return {"error": "Ask the child's name and call identify_child first."}
            if name == "learn_fact":
                topic, fact = str(args.get("topic", "")).strip(), str(args.get("fact", "")).strip()
                if not topic or not fact:
                    return {"saved": False, "error": "topic and fact are both needed"}
                before = teach.stage(self.child_id)[0]
                teach.add_fact(self.child_id, topic, fact)
                add_memory(self.child_id, "taught", topic)
                return self._growth(before, {"saved": True, "topic": topic})
            if name == "quiz_result":
                found = teach.find_facts(self.child_id, str(args.get("topic", "")), limit=1)
                if not found:
                    return {"saved": False, "error": "no taught fact with that topic"}
                before = teach.stage(self.child_id)[0]
                ok = bool(args.get("correct"))
                with connect() as con:
                    con.execute("UPDATE taught SET quiz_attempts=quiz_attempts+1, quiz_correct=quiz_correct+? WHERE id=?",
                                (int(ok), found[0]["id"]))
                    con.commit()
                return self._growth(before, {"saved": True, "correct": ok})
            return {"error": "unknown tool " + str(name)}
        except Exception as e:  # keep the conversation alive whatever happens
            return {"error": str(e)}

    def system_prompt(self):
        p = PERSONA
        if self.child_id is not None:
            p += ("\n\nYou are already talking with " + self.name + ". Do not ask the name again; "
                  "say you are back and carry on. Current state (use it, it is true): "
                  + json.dumps(self.info()))
        return p

    def greeting(self):
        if self.child_id is None:
            return "(You just woke up. Say hello to the child and ask their name.)"
        return "(The connection was restarted. Say a very short welcome back and carry on.)"


# ---------------------------------------------------------------- microphone and speaker

class Mic:
    def __init__(self):
        self.p = subprocess.Popen(
            ["arecord", "-D", MIC, "-f", "S16_LE", "-r", "16000", "-c", "1", "-t", "raw", "-q"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def read(self):
        """100 ms of audio (blocking), made louder by AI_PET_MIC_GAIN. Empty = microphone is gone."""
        data = self.p.stdout.read(MIC_CHUNK)
        return boost(data, MIC_GAIN) if data else b""

    def close(self):
        self.p.terminate()


class Speaker:
    def __init__(self):
        self.p = None
        self._start()

    def _start(self):
        self.p = subprocess.Popen(
            ["aplay", "-q", "-D", AUDIO, "-f", "S16_LE", "-r", "24000", "-c", "1", "-t", "raw"],
            stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def write(self, data):
        try:
            self.p.stdin.write(boost(data, VOLUME))
            self.p.stdin.flush()
        except (BrokenPipeError, ValueError, OSError):
            pass

    def clear(self):
        """Drop what is still queued (the child interrupted)."""
        self.close()
        self._start()

    def close(self):
        try:
            self.p.stdin.close()
        except OSError:
            pass
        self.p.terminate()


# ---------------------------------------------------------------- one Gemini session

class Session:
    def __init__(self, session, mochi, mic, speaker, types):
        self.s, self.mochi, self.mic, self.spk, self.types = session, mochi, mic, speaker, types
        self.play_until = 0.0
        self.audio_q = asyncio.Queue()
        self.in_buf = ""        # what the child said this turn (from Gemini's transcript)
        self.out_buf = ""       # what Mochi said this turn
        self.alerted = False
        self.quit_after_turn = False
        self.reason = "reconnect"   # why the session ended: quit | reconnect

    def muted(self):
        return (not BARGE_IN) and time.monotonic() < self.play_until + TAIL

    async def mic_loop(self):
        loop = asyncio.get_running_loop()
        while True:
            data = await loop.run_in_executor(None, self.mic.read)
            if not data:
                raise RuntimeError("microphone stopped (check AI_PET_MIC, run check_mic.py)")
            if self.muted():
                data = bytes(len(data))   # silence: keeps the stream going without echo
            await self.s.send_realtime_input(
                audio=self.types.Blob(data=data, mime_type="audio/pcm;rate=16000"))

    async def speak_loop(self):
        loop = asyncio.get_running_loop()
        while True:
            data = await self.audio_q.get()
            await loop.run_in_executor(None, self.spk.write, data)

    def _queue_audio(self, data):
        now_t = time.monotonic()
        self.play_until = max(self.play_until, now_t) + len(data) / OUT_BYTES_PER_SEC
        self.audio_q.put_nowait(data)

    async def _child_said(self, text):
        self.in_buf += text
        kind = check_safety(self.in_buf)
        if kind and not self.alerted:
            self.alerted = True
            save_alert(self.mochi.name or "unknown", kind, self.in_buf)
            print("(safety alert saved: " + kind + ")")
            await self.s.send_realtime_input(
                text="[Safety] The child may be in danger. Calmly say this in your own words: " + reply_for(kind))

    def _flush_child(self):
        text = self.in_buf.strip()
        self.in_buf = ""
        if not text:
            return
        print("You: " + text)
        if self.mochi.child_id is not None:
            add_memory(self.mochi.child_id, "chat", text)
        if is_goodbye(text):
            self.quit_after_turn = True

    async def _end_turn(self):
        """True when the child said goodbye and Mochi finished answering."""
        self._flush_child()
        if self.out_buf.strip():
            print("Mochi: " + self.out_buf.strip())
        self.out_buf = ""
        self.alerted = False
        if self.quit_after_turn:
            while time.monotonic() < self.play_until + 0.3:   # let the goodbye finish
                await asyncio.sleep(0.1)
            self.reason = "quit"
            return True
        return False

    async def _tools(self, tool_call):
        replies = []
        for fc in tool_call.function_calls:
            result = self.mochi.call(fc.name, dict(fc.args or {}))
            print("(" + fc.name + " -> " + json.dumps(result)[:120] + ")")
            replies.append(self.types.FunctionResponse(id=fc.id, name=fc.name, response=result))
        await self.s.send_tool_response(function_responses=replies)

    async def recv_loop(self):
        empty = 0
        while True:
            got = False
            async for resp in self.s.receive():
                got = True
                if getattr(resp, "tool_call", None):
                    await self._tools(resp.tool_call)
                if getattr(resp, "go_away", None):
                    print("(Gemini asks to reconnect)")
                    return
                sc = getattr(resp, "server_content", None)
                if not sc:
                    continue
                turn = getattr(sc, "model_turn", None)
                if turn and turn.parts:
                    for part in turn.parts:
                        if part.inline_data and part.inline_data.data:
                            self._queue_audio(part.inline_data.data)
                it = getattr(sc, "input_transcription", None)
                if it and it.text:
                    await self._child_said(it.text)
                ot = getattr(sc, "output_transcription", None)
                if ot and ot.text:
                    self._flush_child()
                    self.out_buf += ot.text
                if getattr(sc, "interrupted", False):
                    while not self.audio_q.empty():
                        self.audio_q.get_nowait()
                    self.spk.clear()
                    self.play_until = 0.0
                if getattr(sc, "turn_complete", False):
                    if await self._end_turn():
                        return
            empty = 0 if got else empty + 1
            if empty > 50:
                raise RuntimeError("connection closed")
            await asyncio.sleep(0.02)


async def run_session(client, mochi, mic_factory=Mic, speaker_factory=Speaker, types=None):
    """One connection. Returns 'quit' when the child said goodbye, 'reconnect' otherwise."""
    if types is None:
        from google.genai import types
    config = {
        "response_modalities": ["AUDIO"],
        "system_instruction": mochi.system_prompt(),
        "speech_config": {"voice_config": {"prebuilt_voice_config": {"voice_name": VOICE}}},
        "input_audio_transcription": {},
        "output_audio_transcription": {},
        "tools": TOOLS,
        "realtime_input_config": {"automatic_activity_detection": {"silence_duration_ms": 800}},
    }
    mic = spk = None
    tasks = []
    try:
        async with client.aio.live.connect(model=MODEL, config=config) as raw:
            mic, spk = mic_factory(), speaker_factory()
            sess = Session(raw, mochi, mic, spk, types)
            await raw.send_realtime_input(text=mochi.greeting())
            tasks = [asyncio.create_task(sess.mic_loop()),
                     asyncio.create_task(sess.recv_loop()),
                     asyncio.create_task(sess.speak_loop())]
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for t in done:
                if t.exception():
                    raise t.exception()
            return sess.reason
    finally:
        for t in tasks:
            t.cancel()
        for dev in (mic, spk):
            if dev:
                try:
                    dev.close()
                except Exception:
                    pass


def _fatal(e):
    """Errors that retrying will not fix: bad key, no access, bad model name."""
    s = str(e).lower()
    return any(w in s for w in ("api key", "permission", "403", "401", "not found", "404", "invalid"))


async def main_async(client, mochi):
    ever_connected = False
    for attempt in range(MAX_RECONNECTS + 1):
        try:
            reason = await run_session(client, mochi)
            ever_connected = True
            if reason == "quit":
                return True
            print("(reconnecting...)")
        except Exception as e:
            print("(Gemini Live problem: " + str(e)[:200] + ")")
            if not ever_connected and (_fatal(e) or attempt == 0):
                return False          # could not start at all: let the caller use classic Mochi
            if _fatal(e):
                return False
        await asyncio.sleep(2)
    return True


def run(name=None):
    """Start Gemini Live Mochi. Returns False if it could not start (no key, no SDK, no network)."""
    key = api_key()
    if not key:
        print("No Gemini key. Set GEMINI_API_KEY, or add \"gemini_api_key\" to api_config.json.")
        return False
    try:
        from google import genai
    except ImportError:
        print("The Gemini package is missing. Run:  python3 -m pip install --break-system-packages google-genai")
        return False
    init_db()
    mochi = Mochi()
    if name:
        mochi.set_child(name)
    print("=" * 48 + "\n   MOCHI (Gemini Live) - just talk to me!\n" + "=" * 48)
    print("Note: the voice is sent to Google Gemini. A parent should agree first.")
    print("Say goodbye to stop (or press Ctrl+C).")
    try:
        ok = asyncio.run(main_async(genai.Client(api_key=key), mochi))
    except KeyboardInterrupt:
        print("\nBye!")
        return True
    if ok:
        print("Mochi: Bye for now!")
    return ok

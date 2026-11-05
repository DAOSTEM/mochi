"""Voice in and out. On the Raspberry Pi with the Voice HAT this turns on by itself.

Typing still works on a normal computer (no Voice HAT) or when you set:
  AI_PET_VOICE=0   Mochi does not talk out loud
  AI_PET_LISTEN=0  Mochi does not listen (type instead)
(use =1 to force them on)

Run check_mic.py first if Mochi talks but does not hear you.
"""
import json, os, subprocess, time
from pathlib import Path

AUDIO = os.environ.get("AI_PET_AUDIO", "plughw:1,0")
VOLUME = os.environ.get("AI_PET_VOLUME", "0.2")
LISTEN_SECONDS = 12
ROOT = Path(__file__).resolve().parents[1]
MODEL_NAME = "vosk-model-small-en-us-0.15"

_model = None
_listen_broken = False

QUIT_WORDS = {"goodbye", "good bye", "bye", "bye bye", "stop", "quit", "exit"}

class QuitRequested(Exception):
    """The child said goodbye. Raised anywhere so the program can end politely."""

def wants_quit(text):
    t = text.lower().strip(" .!?")
    return t in QUIT_WORDS or t.endswith(" goodbye") or t.startswith("goodbye")

def model_path():
    """First folder that exists: AI_PET_VOSK, ~/vosk-model, ~/<model>, ./models/<model>."""
    options = [os.environ.get("AI_PET_VOSK", ""),
               os.path.expanduser("~/vosk-model"),
               os.path.expanduser("~/" + MODEL_NAME),
               str(ROOT / "models" / MODEL_NAME)]
    for p in options:
        if p and os.path.isdir(p):
            return p
    raise FileNotFoundError("Vosk model not found. Expected ~/vosk-model (or set AI_PET_VOSK).")

def has_voice_hat():
    try:
        with open("/proc/asound/cards") as f:
            return "sndrpigooglevoi" in f.read()
    except OSError:
        return False

def _on(name):
    v = os.environ.get(name)
    return has_voice_hat() if v is None else v == "1"

def _play(path):
    subprocess.run(["aplay", "-q", "-D", AUDIO, path], check=True)

def say(text):
    print("Mochi: " + text)
    if not _on("AI_PET_VOICE"):
        return
    try:
        subprocess.run(["espeak-ng", "-w", "/tmp/pet.wav", text], check=True)
        subprocess.run(["sox", "/tmp/pet.wav", "/tmp/pet_quiet.wav", "vol", VOLUME], check=True)
        _play("/tmp/pet_quiet.wav")
        time.sleep(0.3)  # let the speaker go quiet so Mochi does not hear itself
    except (OSError, subprocess.CalledProcessError):
        pass

def _beep():
    """A short 'ding' that means: now you can talk."""
    try:
        subprocess.run(["sox", "-n", "/tmp/pet_beep.wav", "synth", "0.15", "sine", "880", "vol", VOLUME],
                       check=True, stderr=subprocess.DEVNULL)
        _play("/tmp/pet_beep.wav")
    except (OSError, subprocess.CalledProcessError):
        pass

def _listen_vosk(words):
    global _model
    from vosk import Model, KaldiRecognizer
    if _model is None:
        _model = Model(model_path())
    if words:  # only listen for these words: much more accurate for menus and yes/no
        rec = KaldiRecognizer(_model, 16000, json.dumps(list(words) + ["[unk]"]))
    else:
        rec = KaldiRecognizer(_model, 16000)
    proc = subprocess.Popen(
        ["arecord", "-D", AUDIO, "-f", "S16_LE", "-r", "16000", "-c", "1", "-t", "raw"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    end = time.time() + LISTEN_SECONDS
    try:
        while time.time() < end:
            data = proc.stdout.read(4000)
            if not data:
                break
            if rec.AcceptWaveform(data):
                text = json.loads(rec.Result()).get("text", "").replace("[unk]", "").strip()
                if text:
                    return " ".join(text.split())
        return ""
    finally:
        proc.terminate()

def listen(prompt="", words=None):
    """Return what the child said (or typed). Empty text means nothing was heard.
    words: optional list of words/phrases to listen for (voice only)."""
    global _listen_broken
    if _on("AI_PET_LISTEN") and not _listen_broken:
        try:
            _beep()
            print("(listening...)")
            text = _listen_vosk(words)
            if text:
                print("You said: " + text)
            return text
        except Exception as e:  # no model or no mic: type instead
            _listen_broken = True
            print("(voice input not available: " + str(e) + ")")
    try:
        return input(prompt or "You: ").strip()
    except EOFError:
        return "goodbye"

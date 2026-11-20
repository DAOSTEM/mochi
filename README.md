# Mochi — an AI pet that grows when a child teaches it

Mochi is a voice-capable learning pet for children (ages 5–12) that runs on a
Raspberry Pi 3A+ with a Google AIY Voice HAT. **A child makes Mochi smarter by
teaching it, not by asking it.** Mochi starts as a Baby that only knows what the
child taught it, and unlocks more abilities as the child teaches and remembers.

## How it works

| Stage | Points | What Mochi can do |
|-------|--------|-------------------|
| Baby  | 0      | Knows only what the child taught it. Says "teach me" when it does not know. |
| Kid   | 3      | Uses the cloud AI, short simple answers. Prefers the child's facts. |
| Teen  | 10     | Longer answers and asks the child questions back. |
| Wise  | 25     | Full answers, connects ideas the child taught. |

Points = facts taught + facts the child correctly remembered in Mochi's quizzes.
Growth comes from teaching and remembering, not from time passing.

**Teach-back:** the child explains, Mochi asks a follow-up ("Why is that?"),
repeats it in its own words, and later quizzes the child on it.

## Child safety and privacy (built in, not added later)

Every sentence goes through this order:
1. **Safety check on the device.** Self-harm or danger phrases are never sent to
   the cloud AI. Mochi answers with a caring message (trusted adult, 988, 911)
   and writes a line to `data/alerts.txt` for the parent or teacher.
   Nothing is reported automatically; a human decides what to do.
2. **Math on the device.** Simple arithmetic never leaves the Pi.
3. **Taught facts first.** Mochi uses what the child taught it before asking the cloud.
4. **Cloud AI last,** and only once Mochi has grown past Baby. The AI is told
   to reply `[ALERT]` if the child seems to be in danger.

- Speech recognition (Vosk) and speech output (espeak-ng) run locally.
- The API key belongs to the parent. It is never in the code or in this repository.
- All child data stays in a local SQLite file (`data/ai_pet.db`).

## Run (typing, any computer, Python 3.9+, no packages needed)

    python3 main.py

## Cloud AI setup

Copy `api_config.example.json` to `api_config.json` and fill it in, or set
`AI_PET_API_KEY`, `AI_PET_BASE_URL`, `AI_PET_MODEL`. Works with any provider that
has an OpenAI-style `/chat/completions` endpoint. Without a key Mochi still
works as a Baby-level pet that uses taught facts and local math.

## Voice on the Raspberry Pi

Voice is **automatic** when the Voice HAT is detected: Mochi talks and listens, and
the child never needs a keyboard. The child says a name, answers by voice, and picks
activities by saying a word: *math, puzzle, word, chat, teach me, quiz me, progress*.
Say **goodbye** to stop, or **shut down** to turn the Pi off.

On a normal computer it falls back to typing. Force it with `AI_PET_VOICE=0/1`
and `AI_PET_LISTEN=0/1`.

- Hardware: Pi 3A+, AIY Voice HAT v1, Raspberry Pi OS Lite 64-bit
- Packages: `espeak-ng`, `sox`, `vosk` + a Vosk English model in `~/vosk-model` (or `~/vosk-model-small-en-us-0.15`, or set `AI_PET_VOSK`)
- Audio device defaults to `plughw:1,0` (`AI_PET_AUDIO` to change)

## Talk with Gemini Live (optional, no menu)

    export GEMINI_API_KEY=...        # or "gemini_api_key" in api_config.json (never on GitHub)
    python3 test_gemini.py           # 10-second check, plays a hello
    python3 live_mochi.py            # the child just talks

Gemini listens and talks in one step (much better than Vosk + espeak). Mochi's idea is
unchanged: Gemini calls three small tools (`identify_child`, `learn_fact`, `quiz_result`)
so points and growth stages are still saved in `data/ai_pet.db`, and a **Baby** only
answers from what the child taught it. The keyword safety check still runs on Gemini's
transcript of the child's words and writes `data/alerts.txt`.

- While Mochi talks the microphone is muted (the HAT speaker is next to the mic).
  `AI_PET_LIVE_BARGEIN=1` lets the child interrupt; use it only with a headset.
- If it cannot start (no key, no internet) the classic Mochi starts instead.
- Privacy: the child's voice goes to Google. Parents must agree, and use a key whose
  terms do not train on prompts (check the plan's data terms).
- Model: `gemini-3.8-live` by default, change with `AI_PET_LIVE_MODEL`. Sessions last
  about 15 minutes, then Mochi reconnects by itself.

## Set up a new Pi (one step)

On a fresh Raspberry Pi OS Lite 64-bit with the Voice HAT attached:

    wget https://raw.githubusercontent.com/DAOSTEM/mochi/main/setup_mochi.sh
    bash setup_mochi.sh

It installs everything Mochi needs (programs, `vosk` and its speech model, the sound-card
setting), downloads this program to `~/mochi`, and checks the result. Safe to run again.
Reboot if it asks you to, then run `python3 check_mic.py` and `python3 main.py`.

## Files

- `ai_pet/teach.py` — teaching, quizzes, growth stages
- `ai_pet/chat.py` — safety → math → taught facts → cloud AI
- `ai_pet/safety.py`, `ai_pet/mathlocal.py` — on-device filters
- `ai_pet/live.py` — Gemini Live voice (`live_mochi.py` starts it)
- `ai_pet/llm.py` — cloud AI call; `ai_pet/voice.py` — speech in/out
- `ai_pet/learning.py` — math, logic and vocabulary games (English, 中文, Español)

## Limits (honest)

The safety filter is keyword based and will miss things; it is a first layer
beside an adult, not a replacement for one. Learning scores are practice signals,
not assessments. The vocabulary file holds 20 sample concepts.

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

## Files

- `ai_pet/teach.py` — teaching, quizzes, growth stages
- `ai_pet/chat.py` — safety → math → taught facts → cloud AI
- `ai_pet/safety.py`, `ai_pet/mathlocal.py` — on-device filters
- `ai_pet/llm.py` — cloud AI call; `ai_pet/voice.py` — speech in/out
- `ai_pet/learning.py` — math, logic and vocabulary games (English, 中文, Español)

## Limits (honest)

The safety filter is keyword based and will miss things; it is a first layer
beside an adult, not a replacement for one. Learning scores are practice signals,
not assessments. The vocabulary file holds 20 sample concepts.

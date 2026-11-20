"""Check Gemini Live on the Pi in 10 seconds (no microphone needed).

    export GEMINI_API_KEY=...      (or gemini_api_key in api_config.json)
    python3 test_gemini.py

It connects, says hello with text, and checks that audio comes back.
If it plays a short hello through the speaker, the whole voice path works.
"""
import asyncio, subprocess, sys
from ai_pet import live

async def main():
    key = live.api_key()
    if not key:
        print("No key. export GEMINI_API_KEY=... first."); return 1
    from google import genai
    client = genai.Client(api_key=key)
    config = {"response_modalities": ["AUDIO"], "output_audio_transcription": {}}
    pcm, said = b"", ""
    print("model:", live.MODEL)
    async with client.aio.live.connect(model=live.MODEL, config=config) as s:
        await s.send_realtime_input(text="Say hello to a child in one short sentence.")
        async for r in s.receive():
            sc = r.server_content
            if not sc:
                continue
            if sc.model_turn:
                for p in sc.model_turn.parts:
                    if p.inline_data and p.inline_data.data:
                        pcm += p.inline_data.data
            if sc.output_transcription and sc.output_transcription.text:
                said += sc.output_transcription.text
            if sc.turn_complete:
                break
    print("Gemini said:", said.strip() or "(no transcript)")
    print("audio received: %.1f seconds" % (len(pcm) / 48000))
    if not pcm:
        print("FAIL: no audio came back"); return 1
    p = subprocess.Popen(["aplay", "-q", "-D", live.AUDIO, "-f", "S16_LE", "-r", "24000", "-c", "1", "-t", "raw"],
                         stdin=subprocess.PIPE)
    p.communicate(live.boost(pcm, live.VOLUME))
    print("OK")
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

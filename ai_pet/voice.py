"""Optional voice for the Raspberry Pi (AIY Voice HAT). Typing always works.

  AI_PET_VOICE=1   Mochi talks out loud (espeak-ng + sox + aplay)
  AI_PET_LISTEN=1  Mochi listens (Vosk + arecord) instead of the keyboard
"""
import json, os, subprocess

AUDIO = os.environ.get("AI_PET_AUDIO", "plughw:1,0")
VOLUME = os.environ.get("AI_PET_VOLUME", "0.2")
MODEL_PATH = os.environ.get("AI_PET_VOSK", os.path.expanduser("~/vosk-model-small-en-us-0.15"))

_recognizer = None

def say(text):
    print("Mochi: " + text)
    if os.environ.get("AI_PET_VOICE") != "1":
        return
    try:
        subprocess.run(["espeak-ng", "-w", "/tmp/pet.wav", text], check=True)
        subprocess.run(["sox", "/tmp/pet.wav", "/tmp/pet_quiet.wav", "vol", VOLUME], check=True)
        subprocess.run(["aplay", "-q", "-D", AUDIO, "/tmp/pet_quiet.wav"], check=True)
    except (OSError, subprocess.CalledProcessError):
        pass  # no speaker? the text above is still shown

def _listen_vosk():
    global _recognizer
    from vosk import Model, KaldiRecognizer
    if _recognizer is None:
        _recognizer = Model(MODEL_PATH)
    rec = KaldiRecognizer(_recognizer, 16000)
    proc = subprocess.Popen(
        ["arecord", "-D", AUDIO, "-f", "S16_LE", "-r", "16000", "-c", "1", "-t", "raw"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        while True:
            data = proc.stdout.read(4000)
            if not data:
                return ""
            if rec.AcceptWaveform(data):
                text = json.loads(rec.Result()).get("text", "").strip()
                if text:
                    return text
    finally:
        proc.terminate()

def listen(prompt="You: "):
    """Return what the child said or typed."""
    if os.environ.get("AI_PET_LISTEN") == "1":
        try:
            print(prompt + "(listening...)")
            text = _listen_vosk()
            print("You said: " + text)
            return text
        except Exception as e:  # missing model, no mic: fall back to typing
            print("(voice input not available: " + str(e) + ")")
    try:
        return input(prompt).strip()
    except EOFError:
        return "bye"

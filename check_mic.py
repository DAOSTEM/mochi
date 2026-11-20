"""Find out why Mochi does not hear you. Run on the Pi:  python3 check_mic.py
Say a sentence like "hello my name is Amy" when it says SPEAK NOW."""
import array, json, os, subprocess, sys, wave
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ai_pet.voice import MIC, MIC_GAIN, model_path

WAV = "/tmp/check_mic.wav"
print("1) Sound card named sndrpigooglevoi:", end=" ")
try:
    print("YES" if "sndrpigooglevoi" in open("/proc/asound/cards").read() else "NO  (set AI_PET_VOICE=1 AI_PET_LISTEN=1 yourself)")
except OSError:
    print("cannot read /proc/asound/cards")

print("2) Recording 5 seconds from", MIC, "(gain", str(MIC_GAIN) + ") ... SPEAK NOW")
subprocess.run(["arecord", "-q", "-D", MIC, "-f", "S16_LE", "-r", "16000", "-c", "1", "-d", "5", WAV], check=True)
with wave.open(WAV) as wf:
    samples = array.array("h", wf.readframes(wf.getnframes()))
peak = max((abs(s) for s in samples), default=0)
print("   loudest point:", peak, "of 32767")
if peak < 500:
    print("   -> almost silent: mic not connected, wrong card number, or muted. Try: alsamixer")
elif peak < 3000:
    print("   -> quiet: speak closer, or make the mic louder in software. Try:")
    print("      export AI_PET_MIC_GAIN=" + str(max(2, min(8, int(10000 / max(peak, 1))))))
    print("      then run this check again")
else:
    print("   -> level is fine")

print("3) Vosk model:", end=" ")
try:
    path = model_path()
    print(path)
except FileNotFoundError as e:
    sys.exit("MISSING. " + str(e))

from vosk import Model, KaldiRecognizer
from ai_pet.voice import boost
rec = KaldiRecognizer(Model(path), 16000)
with wave.open(WAV) as wf:
    while True:
        data = wf.readframes(4000)
        if not data:
            break
        rec.AcceptWaveform(boost(data, MIC_GAIN))
print("4) Mochi heard:", repr(json.loads(rec.FinalResult()).get("text", "")))

#!/bin/bash
# Mochi one-step setup for a Raspberry Pi (Raspberry Pi OS Lite 64-bit + AIY Voice HAT v1).
# Safe to run again. Run it as the normal user (NOT with sudo):
#
#   wget https://raw.githubusercontent.com/DAOSTEM/mochi/main/setup_mochi.sh
#   bash setup_mochi.sh

MODEL=vosk-model-small-en-us-0.15
MODEL_URL=https://alphacephei.com/vosk/models/$MODEL.zip
REPO=https://github.com/DAOSTEM/mochi.git
APP="$HOME/mochi"
NEED_REBOOT=0
PROBLEMS=0

say() { echo; echo "== $1"; }
good() { echo "   OK    $1"; }
bad() { echo "   FIX   $1"; PROBLEMS=1; }

if [ "$(id -u)" -eq 0 ]; then
    echo "Please run this WITHOUT sudo:  bash setup_mochi.sh"
    exit 1
fi
cd "$HOME" || exit 1

say "1/8 Checking the system"
if [ "$(uname -m)" != "aarch64" ]; then
    echo "This Pi runs a 32-bit system ($(uname -m)). Mochi needs Raspberry Pi OS Lite 64-bit."
    echo "Please re-flash the SD card with the 64-bit image."
    exit 1
fi
good "64-bit system"
FREE_MB=$(df -m "$HOME" | awk 'NR==2 {print $4}')
if [ "$FREE_MB" -lt 300 ]; then
    echo "Only ${FREE_MB} MB free. Delete old files and run again."
    exit 1
fi
good "free space ${FREE_MB} MB"

say "2/8 Checking the internet"
if ! wget --spider -q https://github.com; then
    echo "No internet. Check that the Pi is on WiFi, then run this again."
    exit 1
fi
good "internet works"

say "3/8 Installing programs (this takes a few minutes)"
sudo apt update
sudo apt install -y git wget unzip python3-pip espeak-ng sox alsa-utils \
    || { echo "apt install failed. Run again; if it keeps failing, check the WiFi."; exit 1; }
good "programs installed"

say "4/8 Voice HAT sound card setting"
CONFIG=/boot/firmware/config.txt
[ -f "$CONFIG" ] || CONFIG=/boot/config.txt
if grep -q "^dtoverlay=googlevoicehat-soundcard" "$CONFIG"; then
    good "already set in $CONFIG"
else
    echo "dtoverlay=googlevoicehat-soundcard" | sudo tee -a "$CONFIG" >/dev/null
    NEED_REBOOT=1
    good "added to $CONFIG (needs a reboot)"
fi

say "5/8 Speech recognition package (vosk)"
if python3 -c "import vosk" 2>/dev/null; then
    good "vosk already installed"
else
    python3 -m pip install --break-system-packages vosk || { echo "pip install vosk failed"; exit 1; }
    good "vosk installed"
fi
if python3 -c "import google.genai" 2>/dev/null; then
    good "google-genai (Gemini Live) already installed"
else
    python3 -m pip install --break-system-packages google-genai && good "google-genai installed (for live_mochi.py)" \
        || echo "   note: google-genai not installed; classic Mochi still works (python3 main.py)"
fi

say "6/8 Speech model"
if [ -d "$HOME/vosk-model/am" ] && [ -d "$HOME/vosk-model/conf" ]; then
    good "model already in ~/vosk-model"
else
    rm -rf "$HOME/$MODEL" "$HOME/$MODEL.zip"
    wget -q --show-progress -O "$HOME/$MODEL.zip" "$MODEL_URL" || { echo "Model download failed"; rm -f "$HOME/$MODEL.zip"; exit 1; }
    unzip -q "$HOME/$MODEL.zip" || { echo "Unzip failed. Run again."; rm -f "$HOME/$MODEL.zip"; exit 1; }
    rm -rf "$HOME/vosk-model"
    mv "$HOME/$MODEL" "$HOME/vosk-model"
    rm -f "$HOME/$MODEL.zip"
    good "model installed in ~/vosk-model"
fi

say "7/8 Mochi program"
if [ -d "$APP/.git" ]; then
    git -C "$APP" fetch origin && git -C "$APP" reset --hard origin/main
    good "updated (your data and api_config.json are kept)"
else
    if [ -e "$APP" ]; then
        mv "$APP" "$APP.old.$(date +%s)"
        echo "   (old folder renamed to $(basename "$APP").old.*)"
    fi
    git clone "$REPO" "$APP" || { echo "git clone failed"; exit 1; }
    good "downloaded to ~/mochi"
fi
[ -f "$APP/api_config.json" ] || cp "$APP/api_config.example.json" "$APP/api_config.json"

say "8/8 Final check"
python3 -c "
import os, vosk
vosk.SetLogLevel(-1)
vosk.Model(os.path.expanduser('~/vosk-model'))
" 2>/dev/null && good "speech model loads" || bad "speech model does not load (run: python3 -c 'import vosk')"
command -v espeak-ng >/dev/null && good "espeak-ng (voice)" || bad "espeak-ng missing"
command -v sox >/dev/null && good "sox" || bad "sox missing"
if grep -q sndrpigooglevoi /proc/asound/cards 2>/dev/null; then
    good "Voice HAT sound card found"
elif [ "$NEED_REBOOT" -eq 1 ]; then
    echo "   INFO  sound card shows up after the reboot"
else
    bad "Voice HAT sound card not found (is the HAT pressed all the way on?)"
fi

echo
if [ "$NEED_REBOOT" -eq 1 ]; then
    echo ">>> Now reboot:  sudo reboot"
    echo ">>> After it starts again:  cd ~/mochi && python3 check_mic.py"
elif [ "$PROBLEMS" -eq 0 ]; then
    echo ">>> All good!  cd ~/mochi && python3 check_mic.py   then   python3 main.py"
else
    echo ">>> Some items need fixing (see FIX above). Send a photo of this screen to your teacher."
fi

"""Start Mochi with Gemini Live (just talk, no menu).

    python3 live_mochi.py          Mochi asks the child's name
    python3 live_mochi.py Amy      skip the name question

If Gemini Live cannot start (no key, no internet), the classic Mochi starts instead.
"""
import sys
from ai_pet import live

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else None
    if not live.run(name):
        print("\nStarting the classic Mochi instead...\n")
        from ai_pet.app import run
        run()

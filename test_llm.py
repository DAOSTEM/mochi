"""Test the cloud AI connection. Run on your own computer or the Pi:

    export AI_PET_API_KEY='your key'
    python3 test_llm.py

It tries the Meta Model API base URL (and any AI_PET_BASE_URL you set) and prints what works.
Copy the working base_url and a model name into api_config.json.
"""
import json, os, urllib.error, urllib.request

KEY = os.environ.get("AI_PET_API_KEY", "").strip()
if not KEY:
    raise SystemExit("Set AI_PET_API_KEY first.")

BASES = [
    os.environ.get("AI_PET_BASE_URL", "").rstrip("/"),
    "https://api.meta.ai/v1",  # from a third-party hackathon guide, check dev.meta.ai docs
]

def get(url):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + KEY})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")[:300]
    except Exception as e:
        return 0, str(e)

for base in [b for b in BASES if b]:
    status, text = get(base + "/models")
    print("\n" + base + "/models ->", status)
    print(text[:600])
    if status == 200:
        print("\nWORKS. Use this base_url:", base)
        break

"""Calls the cloud model. Settings come from environment variables or api_config.json
(api_config.json is NOT uploaded to GitHub, see .gitignore).

  AI_PET_API_KEY    the key. The parent keeps it, never the child.
  AI_PET_BASE_URL   e.g. https://<your provider>/v1   (we add /chat/completions)
  AI_PET_MODEL      model name from the provider docs

Works with any provider that has an OpenAI-style /chat/completions endpoint.
"""
import json, os, urllib.error, urllib.request
from .db import ROOT

CONFIG_FILE = ROOT / "api_config.json"

def settings():
    cfg = {}
    if CONFIG_FILE.exists():
        try:
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except ValueError:
            cfg = {}
    return (
        os.environ.get("AI_PET_API_KEY", cfg.get("api_key", "")).strip(),
        os.environ.get("AI_PET_BASE_URL", cfg.get("base_url", "")).strip().rstrip("/"),
        os.environ.get("AI_PET_MODEL", cfg.get("model", "")).strip(),
    )

def configured():
    return all(settings())

def ask(question, system_prompt):
    """Return the answer text, or None if the AI could not be reached."""
    key, base, model = settings()
    if not (key and base and model):
        return None
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        "max_tokens": 200,
    }
    req = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
        msg = data["choices"][0]["message"]["content"]
        if isinstance(msg, list):  # some providers return a list of parts
            msg = "".join(p.get("text", "") for p in msg if isinstance(p, dict))
        return msg.strip() or None
    except urllib.error.HTTPError as e:
        print("(AI error " + str(e.code) + ")")
    except (KeyError, IndexError, ValueError, TypeError):
        print("(AI answer was in an unexpected format)")
    except Exception as e:
        print("(AI connection problem: " + str(e) + ")")
    return None

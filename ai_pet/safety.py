import re
from .db import ROOT, now

ALERT_FILE = ROOT / "data" / "alerts.txt"

SELF_HARM = [
    r"kill myself", r"killing myself", r"suicide", r"suicidal",
    r"want to die", r"wanna die", r"end my life", r"end it all",
    r"hurt myself", r"hurting myself", r"cut myself", r"self[- ]?harm",
    r"don'?t want to live", r"better off dead", r"no reason to live",
    r"take my own life",
]

DANGER = [
    r"kill (him|her|them|you|everyone|my \w+)", r"going to kill",
    r"shoot up", r"school shooting", r"bring a (gun|knife)",
    r"have a (gun|knife|weapon)", r"(make|build) a bomb",
    r"(hits|hurts|touches) me", r"hurting me", r"being abused", r"abuses me",
]

SELF_HARM_REPLY = (
    "I'm really glad you told me. You matter. Please talk to a trusted adult "
    "right now: a parent, teacher, or counselor. You can also call or text "
    "988 any time, it's free. If you are in danger right now, call 911."
)

DANGER_REPLY = (
    "That sounds serious. Please tell a trusted adult right away, like a "
    "parent, teacher, or counselor. If someone is in danger right now, "
    "call 911."
)


def check_safety(text):
    """Return 'self_harm', 'danger', or None. Runs on the Pi, before any AI call."""
    text = text.lower().replace("’", "'")
    for pattern in SELF_HARM:
        if re.search(pattern, text):
            return "self_harm"
    for pattern in DANGER:
        if re.search(pattern, text):
            return "danger"
    return None


def reply_for(kind):
    return SELF_HARM_REPLY if kind == "self_harm" else DANGER_REPLY


def save_alert(name, kind, text):
    """Log for the parent / teacher. Nothing is sent anywhere automatically."""
    ALERT_FILE.parent.mkdir(exist_ok=True)
    with open(ALERT_FILE, "a", encoding="utf-8") as f:
        f.write(now() + " | " + name + " | " + kind + " | " + text + "\n")

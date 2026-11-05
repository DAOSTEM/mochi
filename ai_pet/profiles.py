from .db import connect, now, add_memory
import re
from .voice import say, listen, wants_quit, QuitRequested
from .mathlocal import words_to_digits

def ask(prompt):
    """Ask out loud; 'skip' or silence gives an empty answer."""
    say(prompt)
    value = listen().strip()
    if wants_quit(value):
        raise QuitRequested()
    return "" if value.lower() in ("skip", "") else value

def clean_name(text):
    """'hello my name is amy' -> 'Amy'"""
    t = text.lower().strip(" .!?")
    t = re.sub(r"^(hello|hi|hey)\b[ ,]*", "", t)
    t = re.sub(r"^(my name is|i am|i'm|im|it's|its|call me|this is)\s+", "", t)
    return t.strip().title()

def create_profile(name=None):
    say("Let's get to know each other.")
    a = {}
    a["name"] = name or clean_name(ask("What should I call you?"))
    a["age"] = ask("How old are you? You can say skip.")
    a["favorite_color"] = ask("What's your favorite color?")
    a["favorite_animal"] = ask("What's your favorite animal?")
    a["interests"] = ask("What do you like doing?")
    try:
        age = int(words_to_digits(a["age"]).split()[-1]) if a["age"] else None
        if age is not None and not 2 <= age <= 12: age = None
    except ValueError:
        age = None
    name = (a["name"] or "Friend").title()
    with connect() as con:
        cur = con.execute("""INSERT INTO children
          (name,age,favorite_color,favorite_animal,interests,created_at)
          VALUES(?,?,?,?,?,?)""",
          (name, age, a["favorite_color"], a["favorite_animal"], a["interests"], now()))
        child_id = cur.lastrowid
        con.commit()
    add_memory(child_id, "first_meeting", f"I met {name}.")
    for key in ("favorite_color", "favorite_animal", "interests"):
        if a[key]: add_memory(child_id, key, a[key])
    say(f"Nice to meet you, {name}!")
    return child_id

def list_profiles():
    with connect() as con:
        return con.execute("SELECT id,name,age FROM children ORDER BY id").fetchall()

def load_profile(child_id):
    with connect() as con:
        return con.execute("SELECT * FROM children WHERE id=?", (child_id,)).fetchone()

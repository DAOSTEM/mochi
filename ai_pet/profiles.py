from .db import connect, now, add_memory

def create_profile():
    print("\n🐾 Hi! I'm your AI Pet. Let's get to know each other.")
    questions = [
      ("name", "What should I call you?"),
      ("age", "How old are you? You can type skip."),
      ("favorite_color", "What's your favorite color?"),
      ("favorite_animal", "What's your favorite animal?"),
      ("interests", "What do you like doing?")
    ]
    a = {}
    for key, prompt in questions:
        value = input(f"\nPet: {prompt}\nYou: ").strip()
        a[key] = "" if value.lower() == "skip" else value
    try:
        age = int(a["age"]) if a["age"] else None
        if age is not None and not 2 <= age <= 12: age = None
    except ValueError:
        age = None
    name = a["name"] or "Friend"
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
    print(f"Pet: Nice to meet you, {name}! 💛")
    return child_id

def list_profiles():
    with connect() as con:
        return con.execute("SELECT id,name,age FROM children ORDER BY id").fetchall()

def load_profile(child_id):
    with connect() as con:
        return con.execute("SELECT * FROM children WHERE id=?", (child_id,)).fetchone()

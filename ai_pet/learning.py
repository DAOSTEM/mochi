import json, random
from pathlib import Path
from .db import connect, now, add_memory

VOCAB_FILE = Path(__file__).resolve().parents[1] / "knowledge" / "vocabulary_500.json"

def seed_vocab(child_id):
    data = json.loads(VOCAB_FILE.read_text(encoding="utf-8"))
    with connect() as con:
        for x in data:
            con.execute("""INSERT OR IGNORE INTO vocabulary
              (child_id,concept,english,chinese,spanish) VALUES(?,?,?,?,?)""",
              (child_id,x["concept"],x["english"],x["chinese"],x["spanish"]))
        con.commit()

def record(child_id, domain, skill, correct, hint=False):
    with connect() as con:
        con.execute("""INSERT INTO skills(child_id,domain,skill,attempts,correct,hints,last_seen)
          VALUES(?,?,?,1,?,?,?) ON CONFLICT(child_id,domain,skill) DO UPDATE SET
          attempts=attempts+1, correct=correct+excluded.correct,
          hints=hints+excluded.hints,last_seen=excluded.last_seen""",
          (child_id,domain,skill,int(correct),int(hint),now()))

def level(child_id, domain, skill):
    with connect() as con:
        r=con.execute("SELECT attempts,correct,hints FROM skills WHERE child_id=? AND domain=? AND skill=?",
                      (child_id,domain,skill)).fetchone()
    if not r or r["attempts"] < 2: return 1
    rate=r["correct"]/r["attempts"]
    return 2 if rate >= .85 and r["hints"] <= 1 else (0 if rate < .45 else 1)

def math_game(child_id):
    levels = {
      0: ("You have 1 apple. I give you 1 more. How many now?", "2", "Count one, then one more."),
      1: ("You have 3 apples. I give you 2 more. How many now?", "5", "Start at 3 and count two more."),
      2: ("You have 8 stars. You give me 3. How many are left?", "5", "Count backward three steps from 8.")
    }
    q,a,h=levels[level(child_id,"math","number_operations")]
    answer=input("\n🐾 "+q+"\nYou: ").strip().lower()
    correct=answer==a
    used_hint=False
    if not correct:
        used_hint=True
        print("Pet: Here's a hint: "+h)
        answer=input("Try again (or type skip): ").strip().lower()
        correct=answer==a
    record(child_id,"math","number_operations",correct,used_hint)
    print("Pet: You got it! ⭐" if correct else f"Pet: Nice try. The answer is {a}. We'll practice again later.")
    add_memory(child_id,"learning","Played a math game.")

def logic_game(child_id):
    q,a,h=random.choice([
      ("Red, blue, red, blue... what comes next?","red","The colors take turns."),
      ("Which is different: cat, dog, apple?","apple","Cat and dog are animals. Apple is food."),
      ("What whole number is bigger than 3 but smaller than 5?","4","Think of the number between 3 and 5.")
    ])
    answer=input("\n🐾 "+q+"\nYou: ").strip().lower().strip(" .!?")
    correct=answer==a
    hint=False
    if not correct:
        hint=True
        print("Pet: Let's think. "+h)
        answer=input("Try once more: ").strip().lower().strip(" .!?")
        correct=answer==a
    record(child_id,"logic","patterns_and_reasoning",correct,hint)
    print("Pet: Wonderful thinking! 🌟" if correct else f"Pet: The answer is {a}. Good trying!")
    add_memory(child_id,"learning","Played a logic game.")

def language_moment(child_id):
    with connect() as con:
        r=con.execute("""SELECT * FROM vocabulary WHERE child_id=?
          ORDER BY introduced ASC, RANDOM() LIMIT 1""",(child_id,)).fetchone()
        if not r: return
        con.execute("UPDATE vocabulary SET introduced=introduced+1,last_seen=? WHERE id=?",(now(),r["id"]))
    print(f"\n🐾 English word: {r['english']}")
    print(f"中文: {r['chinese']} | Español: {r['spanish']}")
    response=input(f"Can you say '{r['english']}'? ").strip().lower()
    ok=response==r["english"].lower()
    with connect() as con:
        con.execute("""UPDATE vocabulary SET recognized=recognized+?,
          recalled=recalled+?,used_correctly=used_correctly+? WHERE id=?""",
          (int(ok),int(ok),int(ok),r["id"]))
    print("Pet: Great remembering!" if ok else f"Pet: That's okay! {r['english']} means {r['chinese']} and {r['spanish']}.")
    add_memory(child_id,"vocabulary",f"Met the word {r['english']}.")

def progress(child_id):
    with connect() as con:
        skills=con.execute("SELECT * FROM skills WHERE child_id=?",(child_id,)).fetchall()
        vocab=con.execute("SELECT COUNT(*) total,SUM(introduced) shown,SUM(recognized) known FROM vocabulary WHERE child_id=?",
                          (child_id,)).fetchone()
    print("\n--- Learning progress ---")
    for s in skills:
        print(f"{s['domain']} / {s['skill']}: {s['correct']} correct out of {s['attempts']} attempts; hints: {s['hints']}")
    print(f"Vocabulary: {vocab['total']} concepts loaded; {vocab['shown'] or 0} introductions; {vocab['known'] or 0} recognized responses.")

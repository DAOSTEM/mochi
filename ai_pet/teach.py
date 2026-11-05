"""Mochi grows when the child teaches it.

points = facts taught + times the child correctly remembered a fact in a quiz
The stage (and what Mochi can do) depends on points, not on time.
"""
import random, re
from .db import connect, now, add_memory
from .voice import say, listen

# (points needed, name, what Mochi can do)
STAGES = [
    (0,  "Baby", "only knows what you taught it"),
    (3,  "Kid",  "can think with the cloud AI, short answers"),
    (10, "Teen", "longer answers, asks you questions"),
    (25, "Wise", "full answers and connects ideas you taught"),
]

STOP = set("a an the is are was were of to in on at and or it its this that what who how why "
           "do does did me my you your i we they he she for with about tell can please".split())

def words(text):
    return {w for w in re.findall(r"[a-z0-9']+", text.lower()) if w not in STOP and len(w) > 1}

def points(child_id):
    with connect() as con:
        r = con.execute("SELECT COUNT(*) n, COALESCE(SUM(quiz_correct),0) c FROM taught WHERE child_id=?",
                        (child_id,)).fetchone()
    return r["n"] + r["c"]

def stage(child_id):
    """Return (index, name, description, points)."""
    p = points(child_id)
    idx = 0
    for i, s in enumerate(STAGES):
        if p >= s[0]:
            idx = i
    return idx, STAGES[idx][1], STAGES[idx][2], p

def next_goal(child_id):
    p = points(child_id)
    for need, name, _ in STAGES:
        if p < need:
            return need - p, name
    return 0, None

def check_growth(child_id, before_idx):
    idx, name, desc, p = stage(child_id)
    if idx > before_idx:
        say("I feel different... I grew up! I am a " + name + " now! I " + desc + ".")
        add_memory(child_id, "growth", "Grew to " + name + " at " + str(p) + " points.")

def add_fact(child_id, topic, fact):
    with connect() as con:
        con.execute("INSERT INTO taught(child_id,topic,fact,created_at) VALUES(?,?,?,?)",
                    (child_id, topic, fact, now()))
        con.commit()

def all_facts(child_id):
    with connect() as con:
        return con.execute("SELECT * FROM taught WHERE child_id=? ORDER BY id", (child_id,)).fetchall()

def find_facts(child_id, question, limit=3):
    """Taught facts that share words with the question (topic words count double)."""
    q = words(question)
    scored = []
    for f in all_facts(child_id):
        score = 2 * len(q & words(f["topic"])) + len(q & words(f["fact"]))
        if score > 0:
            scored.append((score, f))
    scored.sort(key=lambda x: -x[0])
    return [f for _, f in scored[:limit]]

FOLLOW_UPS = [
    "Why is that? Can you explain it a different way?",
    "Can you give me an example?",
    "Hmm, I am not sure I understand. What is the most important part?",
]

def teach_flow(child_id):
    """Child teaches, Mochi asks a question back, then says it in its own words."""
    before = stage(child_id)[0]
    say("Yay! Teach me something. What is it about? (one or two words, or type skip)")
    topic = listen().strip()
    if topic.lower() in ("", "skip", "bye", "end"):
        return
    say("Tell me about " + topic + ". What should I know?")
    fact = listen().strip()
    if not fact or fact.lower() == "skip":
        return
    say(random.choice(FOLLOW_UPS))
    more = listen().strip()
    if more and more.lower() != "skip":
        fact = fact.rstrip(". ") + ". " + more.strip().rstrip(".") + "."
    add_fact(child_id, topic, fact)
    add_memory(child_id, "taught", topic)
    say("So " + topic + ": " + fact + " Did I get it? Thank you for teaching me!")
    check_growth(child_id, before)

def quiz_flow(child_id):
    """Mochi checks if the child still remembers what it taught (spaced review)."""
    facts = all_facts(child_id)
    if not facts:
        say("You have not taught me anything yet. Teach me first, then I can quiz you!")
        return
    before = stage(child_id)[0]
    # least practiced first
    facts.sort(key=lambda f: (f["quiz_attempts"], random.random()))
    f = facts[0]
    say("Quiz time! What did you teach me about " + f["topic"] + "?")
    answer = listen()
    target = words(f["fact"])
    overlap = len(words(answer) & target) / max(1, min(len(target), 6))
    ok = overlap >= 0.5
    with connect() as con:
        con.execute("UPDATE taught SET quiz_attempts=quiz_attempts+1, quiz_correct=quiz_correct+? WHERE id=?",
                    (int(ok), f["id"]))
        con.commit()
    if ok:
        say("Yes! You remembered. That is right!")
    else:
        say("Close! You told me: " + f["fact"])
    check_growth(child_id, before)

def status_line(child_id):
    idx, name, desc, p = stage(child_id)
    need, nxt = next_goal(child_id)
    line = "Mochi is a " + name + " (" + str(p) + " points). It " + desc + "."
    if nxt:
        line += " " + str(need) + " more points to become " + nxt + "."
    return line

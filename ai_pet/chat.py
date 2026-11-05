"""Chat with Mochi.

Every question goes through the same order:
  1. Safety check on the Pi. If it matches, NOTHING is sent to the cloud AI.
  2. Simple math is solved on the Pi.
  3. Things the child taught Mochi are used first.
  4. Only then, and only once Mochi has grown past Baby, the cloud AI helps.
"""
from . import llm
from .safety import check_safety, reply_for, save_alert
from .mathlocal import try_math, spoken_to_math
from .teach import find_facts, stage, teach_flow
from .voice import say, listen
from .db import add_memory

STYLE = {
    1: "Answer in ONE short sentence with simple words, like a young pet that is still learning.",
    2: "Answer in at most two short sentences. End with a question that makes the child think.",
    3: "Answer in at most three sentences. Connect to what the child taught you when it helps.",
}

def system_prompt(child, idx, facts):
    p = ("You are Mochi, a friendly learning pet for a child aged " + str(child["age"] or "5-12") + ". "
         + STYLE.get(idx, STYLE[1]) + " Never give medical, legal or dangerous instructions. "
         "If the child seems to be in danger, is being hurt, wants to hurt themselves or others, "
         "start your reply with the exact text [ALERT] and tell them to talk to a trusted adult. ")
    if facts:
        p += "The child taught you these things. Prefer them, and say 'You taught me' when you use one: "
        p += " | ".join(f["topic"] + ": " + f["fact"] for f in facts)
    return p

def answer_from_facts(facts):
    f = facts[0]
    return "You taught me about " + f["topic"] + ": " + f["fact"]

def chat(child_id, child):
    name = child["name"]
    say("Ask me anything! Say teach to teach me. Say bye to go back, or goodbye to turn me off.")
    while True:
        q = listen("You: ")
        low = q.lower().strip(" .!?")
        if low == "":
            continue
        if low in ("goodbye", "good bye", "stop"):
            say("Bye for now!")
            return "quit"
        if low in ("bye", "end", "back", "menu"):
            say("Okay, back to the menu.")
            return
        if low in ("teach", "teach you", "let me teach you"):
            teach_flow(child_id)
            continue

        # 1. safety
        kind = check_safety(q)
        if kind:
            save_alert(name, kind, q)
            say(reply_for(kind))
            continue

        # 2. math
        m = try_math(spoken_to_math(q))
        if m is not None:
            say(m)
            continue

        add_memory(child_id, "chat", q)
        facts = find_facts(child_id, q)
        idx, stage_name, _, _ = stage(child_id)

        # 3. Baby: only what was taught
        if idx == 0 or not llm.configured():
            if facts:
                say(answer_from_facts(facts))
            elif idx == 0:
                say("I do not know that yet. I am still a Baby. Say 'teach' and teach me!")
            else:
                say("I can't reach my big brain right now. Can you teach me about that?")
            continue

        # 4. cloud AI
        ans = llm.ask(q, system_prompt(child, idx, facts))
        if ans is None:
            say(answer_from_facts(facts) if facts else "I can't reach my big brain right now.")
        elif ans.startswith("[ALERT]"):
            save_alert(name, "ai_flagged", q)
            say(ans[len("[ALERT]"):].strip())
        else:
            say(ans)

import re, subprocess
from .db import init_db, add_memory
from .profiles import create_profile, list_profiles, load_profile, clean_name
from .learning import seed_vocab, math_game, logic_game, language_moment, progress
from .chat import chat
from .teach import teach_flow, quiz_flow, status_line
from .voice import say, listen, wants_quit, QuitRequested

HELP = ("You can say: math, puzzle, word, chat, teach me, quiz me, or progress. "
        "Say goodbye to stop. Say shut down to turn me off.")

# say one of these words and Mochi does the thing (typing 1 to 8 works too)
COMMANDS = [
    ("shutdown", ["shut down", "shutdown", "turn off", "power off"]),
    ("quit",     ["goodbye", "good bye", "bye", "stop", "end", "quit", "exit", "0"]),
    ("help",     ["help", "what can you do", "menu"]),
    ("math",     ["math", "number", "numbers", "count", "1"]),
    ("logic",    ["puzzle", "logic", "2"]),
    ("word",     ["word", "words", "english", "vocabulary", "3"]),
    ("progress", ["progress", "how big", "grow", "4"]),
    ("chat",     ["chat", "talk", "ask", "question", "6"]),
    ("teach",    ["teach", "learn", "7"]),
    ("quiz",     ["quiz", "test", "8"]),
]

MENU_WORDS = [k for _, keys in COMMANDS for k in keys if not k.isdigit()] + ["teach me", "quiz me"]

def pick(text):
    t = text.lower()
    for cmd, keys in COMMANDS:
        for k in keys:
            if re.search(r"\b" + re.escape(k) + r"\b", t):
                return cmd
    return None

def shutdown_pi():
    say("Do you want me to turn off? Say yes.")
    if "yes" in listen(words=["yes", "no"]).lower():
        say("Goodbye! Turning off now.")
        subprocess.run(["sudo", "shutdown", "-h", "now"])
        return True
    say("Okay, I'll stay awake.")
    return False

def who_is_playing():
    profiles = list_profiles()
    say("Hi! I am Mochi. What is your name? You can also say goodbye.")
    name = listen().strip()
    if name.lower() in ("", "skip"):
        say("I did not hear you. What is your name?")
        name = listen().strip()
    if wants_quit(name):
        raise QuitRequested()
    name = clean_name(name)
    for p in profiles:
        if p["name"].lower() == name.lower():
            return p["id"]
    return create_profile(name or None)

def run():
    try:
        play()
    except QuitRequested:
        say("Okay, goodbye! See you next time.")

def play():
    init_db()
    print("="*48+"\n       MOCHI — your learning pet\n"+"="*48)
    child_id = who_is_playing()
    child = load_profile(child_id)
    seed_vocab(child_id)
    add_memory(child_id,"session","Started a play session.")
    say(f"Hello, {child['name']}! I'm happy to see you.")
    if child["favorite_animal"]:
        say(f"I remember you like {child['favorite_animal']}!")
    say(status_line(child_id))
    say(HELP)
    while True:
        say("What shall we do?")
        cmd = pick(listen(words=MENU_WORDS))
        if cmd == "quit":
            say("Bye for now! See you next time.")
            break
        elif cmd == "shutdown":
            if shutdown_pi(): break
        elif cmd == "help": say(HELP)
        elif cmd == "math": math_game(child_id)
        elif cmd == "logic": logic_game(child_id)
        elif cmd == "word": language_moment(child_id)
        elif cmd == "progress":
            progress(child_id)
            say(status_line(child_id))
        elif cmd == "chat":
            if chat(child_id, child) == "quit":
                say("Goodbye!")
                break
        elif cmd == "teach": teach_flow(child_id)
        elif cmd == "quiz": quiz_flow(child_id)
        else: say("I did not understand. " + HELP)

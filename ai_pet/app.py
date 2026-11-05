from .db import init_db, add_memory, get_memories
from .profiles import create_profile, list_profiles, load_profile
from .learning import seed_vocab, math_game, logic_game, language_moment, progress
from .chat import chat
from .teach import teach_flow, quiz_flow, status_line

def run():
    init_db()
    print("="*48+"\n       AI PET — Math, Logic & Language\n"+"="*48)
    profiles=list_profiles()
    if profiles:
        print("\nWho is playing?")
        for p in profiles:
            print(f"{p['id']}. {p['name']}"+(f", age {p['age']}" if p['age'] else ""))
        choice=input("Enter profile number, or N for new: ").strip()
        try:
            child_id=int(choice)
            if not load_profile(child_id): raise ValueError()
        except ValueError:
            child_id=create_profile()
    else:
        child_id=create_profile()
    child=load_profile(child_id)
    seed_vocab(child_id)
    add_memory(child_id,"session","Started a play session.")
    print(f"\n🐾 Mochi: Hello, {child['name']}! I'm happy to see you.")
    if child["favorite_animal"]:
        print(f"I remember you like {child['favorite_animal']}!")
    print(status_line(child_id))
    while True:
        print("\nWhat shall we do?")
        print("1. Math game\n2. Logic puzzle\n3. English word + Chinese + Spanish")
        print("4. Learning progress\n5. Tell Mochi something")
        print("6. Chat with Mochi\n7. Teach Mochi\n8. Mochi quizzes you\n0. Goodbye")
        choice=input("Choose: ").strip()
        if choice=="6": chat(child_id, child)
        elif choice=="7": teach_flow(child_id)
        elif choice=="8": quiz_flow(child_id)
        elif choice=="1": math_game(child_id)
        elif choice=="2": logic_game(child_id)
        elif choice=="3": language_moment(child_id)
        elif choice=="4":
            progress(child_id)
            print(status_line(child_id))
        elif choice=="5":
            note=input("You: ").strip()
            if note:
                add_memory(child_id,"chat",note)
                print("Mochi: Thanks for sharing that with me. 💛")
        elif choice=="0":
            print("Mochi: Bye for now! See you next time. 🐾")
            break
        else: print("Please choose one of the menu options.")

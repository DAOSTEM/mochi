"""Teacher tool: give (or take away) saved points.   python3 give_points.py Amy 100
Negative numbers take points away:  python3 give_points.py Amy -5
Run it with no arguments to list the children and their points."""
import sys
from ai_pet.db import init_db
from ai_pet.profiles import list_profiles
from ai_pet.teach import add_points, stage, status_line

init_db()
kids = list_profiles()
if len(sys.argv) != 3:
    for k in kids:
        print(k["name"] + ": " + status_line(k["id"]))
    sys.exit("\nUsage: python3 give_points.py <name> <points>")
name, amount = sys.argv[1], int(sys.argv[2])
match = [k for k in kids if k["name"].lower() == name.lower()]
if not match:
    sys.exit("No child named " + name + ". Names: " + ", ".join(k["name"] for k in kids))
add_points(match[0]["id"], amount, "teacher bonus")
print(status_line(match[0]["id"]))

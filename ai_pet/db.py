import sqlite3
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ai_pet.db"

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def connect():
    DB_PATH.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con

def init_db():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS children(
          id INTEGER PRIMARY KEY, name TEXT NOT NULL, age INTEGER,
          favorite_color TEXT, favorite_animal TEXT, interests TEXT,
          created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS memories(
          id INTEGER PRIMARY KEY, child_id INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
          memory_type TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS skills(
          id INTEGER PRIMARY KEY, child_id INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
          domain TEXT NOT NULL, skill TEXT NOT NULL, attempts INTEGER DEFAULT 0,
          correct INTEGER DEFAULT 0, hints INTEGER DEFAULT 0, last_seen TEXT,
          UNIQUE(child_id,domain,skill));
        CREATE TABLE IF NOT EXISTS vocabulary(
          id INTEGER PRIMARY KEY, child_id INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
          concept TEXT NOT NULL, english TEXT NOT NULL, chinese TEXT, spanish TEXT,
          introduced INTEGER DEFAULT 0, recognized INTEGER DEFAULT 0,
          recalled INTEGER DEFAULT 0, used_correctly INTEGER DEFAULT 0, last_seen TEXT,
          UNIQUE(child_id,concept));
        CREATE TABLE IF NOT EXISTS taught(
          id INTEGER PRIMARY KEY, child_id INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
          topic TEXT NOT NULL, fact TEXT NOT NULL, quiz_attempts INTEGER DEFAULT 0,
          quiz_correct INTEGER DEFAULT 0, created_at TEXT NOT NULL);
        """)
        con.commit()

def add_memory(child_id, kind, content):
    with connect() as con:
        con.execute("INSERT INTO memories(child_id,memory_type,content,created_at) VALUES(?,?,?,?)",
                    (child_id, kind, content, now()))

def get_memories(child_id, limit=5):
    with connect() as con:
        return con.execute("SELECT * FROM memories WHERE child_id=? ORDER BY id DESC LIMIT ?",
                           (child_id, limit)).fetchall()

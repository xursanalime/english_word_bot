import sqlite3

conn = sqlite3.connect("words.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unit TEXT,
    eng TEXT,
    uzb TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS stats (
    id INTEGER PRIMARY KEY,
    tests INTEGER,
    correct INTEGER,
    wrong INTEGER
)
""")

cursor.execute("INSERT OR IGNORE INTO stats (id, tests, correct, wrong) VALUES (1,0,0,0)")

conn.commit()
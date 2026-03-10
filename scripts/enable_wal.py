import sqlite3
conn = sqlite3.connect("db/autoquant.db")
result = conn.execute("PRAGMA journal_mode=WAL").fetchone()
print(f"journal_mode set to: {result[0]}")
conn.execute("PRAGMA busy_timeout=5000")
conn.close()
print("WAL mode enabled successfully")

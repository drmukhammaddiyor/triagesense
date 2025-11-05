# view_db.py
import sqlite3
conn = sqlite3.connect("triagesense.db")
cur = conn.cursor()
for row in cur.execute("SELECT id, symptoms, created_at FROM submissions ORDER BY id DESC LIMIT 20"):
    print(row)
conn.close()

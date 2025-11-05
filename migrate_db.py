import sqlite3
DB_PATH = 'triagesense.db'
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Inspect existing columns
cur.execute("PRAGMA table_info(submissions)")
cols = [r[1] for r in cur.fetchall()]
print('Existing columns in submissions:', cols)

# Add triage_level if missing
if 'triage_level' not in cols:
    print('Adding triage_level column...')
    cur.execute("ALTER TABLE submissions ADD COLUMN triage_level TEXT")
else:
    print('triage_level column already exists.')

# Add triage_reason if missing
if 'triage_reason' not in cols:
    print('Adding triage_reason column...')
    cur.execute("ALTER TABLE submissions ADD COLUMN triage_reason TEXT")
else:
    print('triage_reason column already exists.')

conn.commit()
conn.close()
print('Migration complete.')

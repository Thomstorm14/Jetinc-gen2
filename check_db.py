import sqlite3
conn = sqlite3.connect("jettrix_sim.db")
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
for t in cursor.fetchall():
name = t[0]
count = cursor.execute("SELECT COUNT(*) FROM [" + name + "]").fetchone()[0]
print(f"Table: {name} | Rows: {count}")
conn.close()

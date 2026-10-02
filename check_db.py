import sqlite3

conn = sqlite3.connect("jettrix_sim.db")
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

for t in tables:
    name = t[0]
    count = cursor.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0]
    print(f"Table: {name} | Rows: {count}")

conn.close()

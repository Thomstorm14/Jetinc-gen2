import sqlite3
import argparse
import sys

DB_FILE = "jettrix_sim.db"

def query_dashboard(db_path=DB_FILE):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
    except sqlite3.Error as e:
        print(f"[ERROR] Could not connect to database '{db_path}': {e}")
        sys.exit(1)

    # Check table existence
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shift_logs';")
    if not cursor.fetchone():
        print(f"[ERROR] Table 'shift_logs' not found in '{db_path}'. Run sim_engine.py first.")
        conn.close()
        return

    # Total Count
    cursor.execute("SELECT COUNT(*) FROM shift_logs")
    total_logs = cursor.fetchone()[0]

    print("\n================================================================================")
    print(f"               JETTRIX SIMULATION DASHBOARD - {db_path}")
    print("================================================================================")
    print(f" Total Logged Shift Records: {total_logs}\n")

    # Group by City
    print("--------------------------------------------------------------------------------")
    print(" [1] SHIFT METRICS BY CITY")
    print("--------------------------------------------------------------------------------")
    cursor.execute("SELECT city, COUNT(*) FROM shift_logs GROUP BY city ORDER BY city;")
    city_counts = cursor.fetchall()
    for city, count in city_counts:
        pct = (count / total_logs) * 100 if total_logs else 0
        print(f"  • {city:<20} : {count:>5} shifts ({pct:5.1f}%)")

    # Group by Role
    print("\n--------------------------------------------------------------------------------")
    print(" [2] SHIFT METRICS BY ROLE")
    print("--------------------------------------------------------------------------------")
    cursor.execute("SELECT role, COUNT(*) FROM shift_logs GROUP BY role ORDER BY role;")
    role_counts = cursor.fetchall()
    for role, count in role_counts:
        pct = (count / total_logs) * 100 if total_logs else 0
        print(f"  • {role:<20} : {count:>5} shifts ({pct:5.1f}%)")

    # Group by Status
    print("\n--------------------------------------------------------------------------------")
    print(" [3] AGENT STATUS SUMMARY")
    print("--------------------------------------------------------------------------------")
    cursor.execute("SELECT status, COUNT(*) FROM shift_logs GROUP BY status ORDER BY status;")
    status_counts = cursor.fetchall()
    for status, count in status_counts:
        pct = (count / total_logs) * 100 if total_logs else 0
        print(f"  • {status:<20} : {count:>5} shifts ({pct:5.1f}%)")

    # Cross-tabulation: City x Role
    print("\n--------------------------------------------------------------------------------")
    print(" [4] CROSS-TABULATION: CITY x ROLE MATRIX")
    print("--------------------------------------------------------------------------------")
    print(f"  {'City':<20} | {'R&R':<10} | {'TriCore':<10} | {'Triformer':<10} | {'Total':<10}")
    print("  " + "-" * 68)

    cities = ["Mount Thomas", "Julian Bay", "Evans"]
    for c in cities:
        cursor.execute("SELECT role, COUNT(*) FROM shift_logs WHERE city = ? GROUP BY role;", (c,))
        role_map = dict(cursor.fetchall())
        r_rr = role_map.get("R&R", 0)
        r_tc = role_map.get("TriCore", 0)
        r_tf = role_map.get("Triformer", 0)
        c_tot = r_rr + r_tc + r_tf
        print(f"  {c:<20} | {r_rr:<10} | {r_tc:<10} | {r_tf:<10} | {c_tot:<10}")

    print("================================================================================\n")
    conn.close()

if __name__ == "__main__":
    query_dashboard()

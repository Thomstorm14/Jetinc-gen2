import sqlite3
import sys

DB_FILE = "jettrix_sim.db"
REQUIRED_QUORUM_PER_CITY = 12  # Minimum active agents needed per city for consensus
REQUIRED_PER_ROLE_PER_CITY = 4 # Minimum active agents needed per role in each city

def check_tri_city_quorum(db_path=DB_FILE):
    print("\n================================================================================")
    print("                JETTRIX TRI-CITY CONSENSUS QUORUM MONITOR")
    print("================================================================================")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
    except sqlite3.Error as e:
        print(f"[CRITICAL ALERT] Database connection failed: {e}")
        sys.exit(1)

    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shift_logs';")
    if not cursor.fetchone():
        print(f"[CRITICAL ALERT] Table 'shift_logs' missing in '{db_path}'. Cannot verify quorum.")
        conn.close()
        sys.exit(1)

    cities = ["Mount Thomas", "Julian Bay", "Evans"]
    roles = ["R&R", "TriCore", "Triformer"]

    global_quorum_pass = True
    city_statuses = {}

    for city in cities:
        print(f"\n[CITY EVALUATION] ---> {city.upper()}")
        
        # Get total active count for city
        cursor.execute("SELECT COUNT(*) FROM shift_logs WHERE city = ? AND status = 'ACTIVE_SYNC';", (city,))
        city_active_count = cursor.fetchone()[0]

        # Get per-role counts for city
        role_counts = {}
        for role in roles:
            cursor.execute("""
                SELECT COUNT(*) FROM shift_logs 
                WHERE city = ? AND role = ? AND status = 'ACTIVE_SYNC';
            """, (city, role))
            role_counts[role] = cursor.fetchone()[0]

        # Quorum Evaluation Logic
        city_passed = True
        warnings = []

        if city_active_count < REQUIRED_QUORUM_PER_CITY:
            city_passed = False
            warnings.append(f"Total capacity below quorum ({city_active_count}/{REQUIRED_QUORUM_PER_CITY})")

        for role, count in role_counts.items():
            print(f"  • Role [{role:<10}]: {count:>2} active agents (Min required: {REQUIRED_PER_ROLE_PER_CITY})")
            if count < REQUIRED_PER_ROLE_PER_CITY:
                city_passed = False
                warnings.append(f"Role '{role}' below threshold ({count}/{REQUIRED_PER_ROLE_PER_CITY})")

        if city_passed:
            status_str = f"[OK] QUORUM HEALTHY - Total Active: {city_active_count}"
            city_statuses[city] = "HEALTHY"
        else:
            status_str = f"[ALERT] QUORUM DEFICIT - Total Active: {city_active_count} | Issues: {'; '.join(warnings)}"
            city_statuses[city] = "DEFICIT"
            global_quorum_pass = False

        print(f"  --> Status: {status_str}")

    print("\n--------------------------------------------------------------------------------")
    print("                           OVERALL SYSTEM STATUS")
    print("--------------------------------------------------------------------------------")

    if global_quorum_pass:
        print("[SUCCESS] All tri-city nodes (Mount Thomas, Julian Bay, Evans) maintain active quorum.")
        print("[CONSENSUS] JETtrix Matrix state: OPERATIONAL & CONSENSUS-READY\n")
    else:
        print("[WARNING] One or more nodes failed quorum verification!")
        print("[CONSENSUS] JETtrix Matrix state: DEGRADED / CONSENSUS BLOCKED\n")

    conn.close()
    return global_quorum_pass

if __name__ == "__main__":
    check_tri_city_quorum()

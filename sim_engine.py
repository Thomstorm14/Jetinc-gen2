import sqlite3
import json
import datetime
import hashlib
import os

DB_FILE = "jettrix_sim.db"
LEDGER_FILE = "ledger_v1.jsonl"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shift_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            city TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def get_last_ledger_hash():
    if os.path.exists(LEDGER_FILE):
        with open(LEDGER_FILE, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
            if lines:
                return json.loads(lines[-1]).get("sha256", "0" * 64)
    return "0" * 64

def log_ledger_event(event, details):
    prev_hash = get_last_ledger_hash()
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    entry = {
        "timestamp": timestamp,
        "event": event,
        "details": details,
        "prev_hash": prev_hash
    }

    raw_bytes = json.dumps(entry, sort_keys=True).encode("utf-8")
    entry["sha256"] = hashlib.sha256(raw_bytes).hexdigest()

    with open(LEDGER_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def run_simulation_cycle(shift_id=1):
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cities = ["Mount Thomas", "Julian Bay", "Evans"]
    roles = ["R&R", "TriCore", "Triformer"]

    print(f"\n=== EXECUTING SIMULATION SHIFT CYCLE #{shift_id} ===")
    simulated_records = 0

    for idx in range(1, 49):
        city = cities[(idx - 1) % 3]
        role = roles[(idx - 1) % 3]
        agent_id = f"AGENT_{idx:02d}"
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

        cursor.execute(
            "INSERT INTO shift_logs (timestamp, city, agent_id, role, status) VALUES (?, ?, ?, ?, ?)",
            (timestamp, city, agent_id, role, "ACTIVE_SYNC")
        )
        simulated_records += 1

    conn.commit()
    conn.close()

    log_ledger_event("SIMULATION_CYCLE_COMPLETE", {
        "shift_id": shift_id,
        "agents_simulated": simulated_records,
        "cities": cities,
        "database": DB_FILE
    })

    print(f"[SUCCESS] Simulated {simulated_records} agent shifts. Recorded in '{DB_FILE}' and logged to Trident Ledger.")

if __name__ == "__main__":
    run_simulation_cycle(1)

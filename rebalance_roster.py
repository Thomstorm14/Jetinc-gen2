import sqlite3
import json
import hashlib
import time

DB_PATH = "jettrix_sim.db"
LEDGER_PATH = "ledger_v1.jsonl"

def rebalance_mesh():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Clear existing roster and rebuild 48 balanced nodes (16 per city, 16 per role)
    cursor.execute("DELETE FROM agent_roster")

    agent_id_counter = 1
    new_roster = []

    # Distribution: 16 agents per city across 3 roles
    distribution = {
        "Mount Thomas": {"R&R": 6, "TriCore": 5, "Triformer": 5},
        "Julian Bay":   {"R&R": 5, "TriCore": 6, "Triformer": 5},
        "Evans":        {"R&R": 5, "TriCore": 5, "Triformer": 6}
    }

    for city, roles in distribution.items():
        for role, count in roles.items():
            for _ in range(count):
                agent_id = f"AGT-{agent_id_counter:03d}"
                cursor.execute(
                    "INSERT INTO agent_roster (agent_id, city, role, status) VALUES (?, ?, ?, 'ACTIVE')",
                    (agent_id, city, role)
                )
                new_roster.append({"agent_id": agent_id, "city": city, "role": role})
                agent_id_counter += 1

    conn.commit()
    conn.close()
    print(f"[SUCCESS] Rebalanced {len(new_roster)} agents into 3x3 mesh in '{DB_PATH}'.")

    # Append event to Trident Ledger
    last_hash = "0000000000000000000000000000000000000000000000000000000000000000"
    try:
        with open(LEDGER_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if lines:
                last_record = json.loads(lines[-1].strip())
                last_hash = last_record.get("hash", last_hash)
    except FileNotFoundError:
        pass

    record_data = {
        "timestamp": time.time(),
        "event_type": "ROSTER_REBALANCE",
        "details": "Rebalanced 48-agent mesh to 16 per city and 16 per role across Mount Thomas, Julian Bay, and Evans.",
        "previous_hash": last_hash
    }

    record_bytes = json.dumps(record_data, sort_keys=True).encode('utf-8')
    record_hash = hashlib.sha256(record_bytes).hexdigest()
    record_data["hash"] = record_hash

    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record_data) + "\n")

    print(f"[LEDGER] Appended ROSTER_REBALANCE with hash: {record_hash[:16]}...")

if __name__ == "__main__":
    rebalance_mesh()

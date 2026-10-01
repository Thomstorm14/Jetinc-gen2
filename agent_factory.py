import json, hashlib, time

SHIFTS = ["Day", "Swing", "Graveyard"]
CITIES = ["Mount Thomas", "Julian Bay", "Evans"]

def log_shift_handoff(city, week_num, shift_type, active_count):
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event": "SHIFT_HANDOFF",
        "city": city,
        "week": week_num,
        "shift": shift_type,
        "active_agents": active_count
    }
    entry_bytes = json.dumps(entry, sort_keys=True).encode("utf-8")
    entry["sha256"] = hashlib.sha256(entry_bytes).hexdigest()
    with open("ledger_v1.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry["sha256"]

def initialize_48_roster():
    roster = []
    agent_id = 1
    for city in CITIES:
        for shift in SHIFTS:
            for _ in range(4):
                roster.append({"agent_id": f"AGT-{agent_id:02d}", "city": city, "type": "Full-Time", "base_shift": shift})
                agent_id += 1
    for i in range(12):
        roster.append({"agent_id": f"REL-{i+1:02d}", "city": "Relief Pool", "type": "Part-Time", "base_shift": "Flexible"})
    
    with open("roster_48.jsonl", "w") as f:
        for agent in roster:
            f.write(json.dumps(agent) + "\n")
    return roster

def execute_rotation(week=1):
    roster = initialize_48_roster()
    print(f"\n=== 48-AGENT SHIFT ROTATION MANAGER (WEEK {week}) ===")
    for city_idx, city in enumerate(CITIES):
        current_shift = SHIFTS[(city_idx + (week - 1)) % 3]
        active = [a for a in roster if a["city"] == city and a["base_shift"] == current_shift]
        h = log_shift_handoff(city, week, current_shift, len(active))
        print(f"[{city}] Week {week} -> Active Shift: {current_shift} ({len(active)} Agents) | SHA256: {h[:12]}...")

if __name__ == "__main__":
    execute_rotation(week=1)

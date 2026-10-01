import json, hashlib, time

LEDGER_FILE = "ledger_v1.jsonl"

CODEX_PROFILES = {
    "R&R": {
        "system_instruction": "You are an R&R Lead Agent. Your focus is direct observation, raw reasoning, and strict schema compliance.",
        "temperature": 0.2,
        "max_tokens": 1024
    },
    "TriCore": {
        "system_instruction": "You are a TriCore MTV Seat Agent. Your focus is seat-level evaluation, cross-agent pass-right grading, and consensus voting.",
        "temperature": 0.4,
        "max_tokens": 1024
    },
    "Triformer": {
        "system_instruction": "You are a Triformer Macro Agent. Your focus is multi-city aggregation, meta-synthesis, and Primal payload formatting.",
        "temperature": 0.3,
        "max_tokens": 2048
    }
}

def get_last_hash():
    try:
        with open(LEDGER_FILE, "r") as f:
            lines = [line.strip() for line in f if line.strip()]
            if lines:
                last_entry = json.loads(lines[-1])
                return last_entry.get("sha256", "")
    except FileNotFoundError:
        pass
    return "0" * 64

def log_event(event_type, details):
    prev_hash = get_last_hash()
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event": event_type,
        "details": details,
        "prev_hash": prev_hash
    }
    entry_bytes = json.dumps(entry, sort_keys=True).encode("utf-8")
    entry["sha256"] = hashlib.sha256(entry_bytes).hexdigest()
    with open(LEDGER_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry["sha256"]

def bind_codex_to_roster(roster_file="roster_48.jsonl"):
    print("\n=== CODEX LOADER: BINDING DIRECTIVES TO 48 AGENT SEATS ===")
    bound_count = 0
    bound_roster = []

    try:
        with open(roster_file, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                agent = json.loads(line)
                role = agent.get("role", "TriCore")
                profile = CODEX_PROFILES.get(role, CODEX_PROFILES["TriCore"])
                
                agent["codex_bound"] = True
                agent["system_instruction"] = profile["system_instruction"]
                agent["temperature"] = profile["temperature"]
                agent["max_tokens"] = profile["max_tokens"]
                
                bound_roster.append(agent)
                bound_count += 1

        h = log_event("CODEX_DYNAMIC_BINDING", {
            "bound_agents": bound_count,
            "roster_file": roster_file,
            "roles_assigned": list(CODEX_PROFILES.keys())
        })

        print(f"[SUCCESS] Bound Codex profiles to {bound_count} agents across all shift positions.")
        print(f"Ledger Audit Hash: {h[:12]}...")
        return bound_roster

    except FileNotFoundError:
        print(f"[ERROR] Roster file '{roster_file}' not found. Run agent_factory.py first.")
        return []

if __name__ == "__main__":
    bind_codex_to_roster()

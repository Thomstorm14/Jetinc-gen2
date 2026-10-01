import json
import os
import datetime
import hashlib

CODEX_CONFIG_FILE = "codex_profiles.json"
LEDGER_FILE = "ledger_v1.jsonl"

# Default profile templates for dynamic shift assignment
DEFAULT_PROFILES = {
    "R&R": {
        "temperature": 0.2,
        "max_tokens": 1024,
        "system_instruction": "Execute strict research and review protocols with high auditability."
    },
    "TriCore": {
        "temperature": 0.1,
        "max_tokens": 2048,
        "system_instruction": "Ensure core infrastructure decisions follow deterministic tri-city consensus."
    },
    "Triformer": {
        "temperature": 0.4,
        "max_tokens": 4096,
        "system_instruction": "Perform complex multi-agent synthesis and cross-city state synchronization."
    }
}

def load_or_init_profiles():
    if not os.path.exists(CODEX_CONFIG_FILE):
        with open(CODEX_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_PROFILES, f, indent=4)
        print(f"[CODEX] Initialized default profile configurations in {CODEX_CONFIG_FILE}")

    with open(CODEX_CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def log_to_ledger(event, details):
    prev_hash = "0" * 64
    if os.path.exists(LEDGER_FILE):
        with open(LEDGER_FILE, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
            if lines:
                last_entry = json.loads(lines[-1])
                prev_hash = last_entry.get("sha256", "0" * 64)

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

def bind_codex_to_roster(shift_name="STANDARD_SHIFT"):
    profiles = load_or_init_profiles()
    print(f"[CODEX] Binding dynamic profiles for shift: {shift_name}")
    for role, cfg in profiles.items():
        print(f" - Role [{role:<10}]: Temp={cfg['temperature']} | MaxTokens={cfg['max_tokens']}")

    log_to_ledger("CODEX_DYNAMIC_BINDING", {
        "shift": shift_name,
        "active_roles": list(profiles.keys()),
        "total_seats": 48
    })
    print("[CODEX] Profile binding logged to Trident Ledger successfully.")

if __name__ == "__main__":
    bind_codex_to_roster("INIT_PASS")

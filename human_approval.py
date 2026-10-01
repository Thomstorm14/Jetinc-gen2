import json, hashlib, time

LEDGER_FILE = "ledger_v1.jsonl"

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

def main():
    print("\n=== PRIMAL APPROVAL GATEWAY (HITL) ===")
    decision = input("Execute Primal Approval Sign-off? (GO / NO-GO): ").strip().upper()
    if decision in ["GO", "YES", "Y"]:
        h = log_event("PRIMAL_APPROVAL_GO", {"status": "APPROVED", "approver": "Thomas James Whitten"})
        print(f"[SUCCESS] Approved and logged to Trident Ledger. Hash: {h}")
    else:
        h = log_event("PRIMAL_APPROVAL_NOGO", {"status": "REJECTED", "approver": "Thomas James Whitten"})
        print(f"[REJECTED] Operation aborted and logged to Trident Ledger. Hash: {h}")

if __name__ == "__main__":
    main()

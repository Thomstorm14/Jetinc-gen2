import json, hashlib

LEDGER_FILE = "ledger_v1.jsonl"

def repair():
    print("=== REPAIRING TRIDENT LEDGER SHA-256 CHAIN ===")
    repaired = []
    prev_hash = "0" * 64
    count = 0

    with open(LEDGER_FILE, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]

    for idx, line in enumerate(lines, 1):
        data = json.loads(line)
        
        entry = {
            "timestamp": data.get("timestamp"),
            "event": data.get("event"),
            "details": data.get("details", {}),
            "prev_hash": prev_hash
        }
        
        raw_bytes = json.dumps(entry, sort_keys=True).encode("utf-8")
        h = hashlib.sha256(raw_bytes).hexdigest()
        entry["sha256"] = h
        
        repaired.append(entry)
        prev_hash = h
        count += 1

    with open(LEDGER_FILE, "w", encoding="utf-8") as f:
        for item in repaired:
            f.write(json.dumps(item) + "\n")

    print(f"[SUCCESS] Repaired {count} entries in {LEDGER_FILE}.")

if __name__ == "__main__":
    repair()

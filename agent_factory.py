import json
import hashlib
import sys
import codex_loader

LEDGER_FILE = "ledger_v1.jsonl"

def verify_ledger_chain(filepath=LEDGER_FILE):
    print("\n[GUARD] Verifying Trident Ledger SHA-256 chain integrity...")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        print(f"[WARN] Ledger file '{filepath}' not found. Initializing new chain.")
        return True

    prev_hash = "0" * 64
    for idx, line in enumerate(lines, 1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            print(f"[CRITICAL] Line {idx} is corrupted JSON. Pipeline halted.")
            return False

        stored_hash = entry.get("sha256", "")
        calc_dict = {
            "timestamp": entry.get("timestamp"),
            "event": entry.get("event"),
            "details": entry.get("details", {}),
            "prev_hash": entry.get("prev_hash", "")
        }

        computed_hash = hashlib.sha256(json.dumps(calc_dict, sort_keys=True).encode("utf-8")).hexdigest()
        if computed_hash != stored_hash:
            print(f"[CRITICAL] SHA-256 mismatch at entry line {idx}. Integrity check failed.")
            return False

    print(f"[SUCCESS] Trident Ledger verified cleanly ({len(lines)} entries intact).")
    return True

def run_agent_factory():
    if not verify_ledger_chain():
        print("[HALT] Factory execution aborted due to ledger integrity failure.")
        sys.exit(1)

    print("\n[HOOK] Executing automatic Codex profile binding for active shift...")
    codex_loader.bind_codex_to_roster()

if __name__ == "__main__":
    run_agent_factory()

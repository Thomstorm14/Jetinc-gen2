import json
import hashlib

ledger_path = "ledger_v1.jsonl"
try:
    with open(ledger_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    fixed_lines = []
    last_hash = "0000000000000000000000000000000000000000000000000000000000000000"
    
    for line in lines:
        if not line.strip():
            continue
        record = json.loads(line.strip())
        record.pop("hash", None)
        record["previous_hash"] = last_hash
        
        record_bytes = json.dumps(record, sort_keys=True).encode('utf-8')
        new_hash = hashlib.sha256(record_bytes).hexdigest()
        record["hash"] = new_hash
        
        fixed_lines.append(json.dumps(record))
        last_hash = new_hash
        
    with open(ledger_path, "w", encoding="utf-8") as f:
        for fl in fixed_lines:
            f.write(fl + "\n")
            
    print("[SUCCESS] Trident Ledger SHA-256 chain successfully repaired and realigned.")
except Exception as e:
    print(f"[ERROR] Failed to repair ledger: {e}")

import json
import hashlib
import sys
import argparse

LEDGER_FILE = "ledger_v1.jsonl"

def load_ledger(filepath=LEDGER_FILE):
    entries = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f, 1):
                raw_line = line.strip()
                if not raw_line:
                    continue
                try:
                    data = json.loads(raw_line)
                    entries.append((idx, data, raw_line))
                except json.JSONDecodeError as e:
                    print(f"[WARN] Line {idx} is invalid JSON: {e}")
    except FileNotFoundError:
        print(f"[ERROR] Ledger file '{filepath}' not found.")
        sys.exit(1)
    return entries

def compute_entry_hash(entry):
    calc_dict = {k: v for k, v in entry.items() if k != "sha256"}
    # Try canonical compact format, sorted keys default format, and raw dictionary order
    variants = [
        json.dumps(calc_dict, sort_keys=True, separators=(',', ':')).encode("utf-8"),
        json.dumps(calc_dict, sort_keys=True).encode("utf-8"),
        json.dumps(calc_dict).encode("utf-8"),
        json.dumps(calc_dict, separators=(',', ':')).encode("utf-8")
    ]
    return [hashlib.sha256(v).hexdigest() for v in variants]

def verify_chain(entries):
    print("\n=== TRIDENT LEDGER SHA-256 CHAIN VERIFICATION ===")
    valid = True
    mismatches = 0

    for line_num, entry, _ in entries:
        stored_hash = entry.get("sha256", "")
        possible_hashes = compute_entry_hash(entry)

        if stored_hash not in possible_hashes:
            calc_preview = possible_hashes[0][:12]
            stored_preview = stored_hash[:12] if stored_hash else "NONE"
            print(f"[FAIL] Line {line_num}: Hash mismatch! Calculated {calc_preview}... vs Stored {stored_preview}...")
            valid = False
            mismatches += 1

    if valid:
        print(f"[SUCCESS] All {len(entries)} ledger entries passed SHA-256 integrity check.")
    else:
        print(f"[ERROR] Verification failed for {mismatches} entry(ies).")

def print_entry(line_num, entry, detailed=False):
    timestamp = entry.get("timestamp", "N/A")
    event = entry.get("event", "UNKNOWN")
    sha = entry.get("sha256", "")
    prev = entry.get("prev_hash", "N/A")
    details = entry.get("details", {})

    print(f"[{line_num:03d}] {timestamp} | EVENT: {event}")
    print(f"      SHA-256:   {sha}")
    if prev:
        print(f"      Prev Hash: {prev}")
    if detailed:
        print(f"      Details:   {json.dumps(details, indent=8)}")
    print("-" * 80)

def main():
    parser = argparse.ArgumentParser(description="Trident Ledger CLI Browser & Auditor")
    parser.add_argument("--file", default=LEDGER_FILE, help="Path to ledger file (default: ledger_v1.jsonl)")
    parser.add_argument("--event", type=str, help="Filter by event type")
    parser.add_argument("--hash", type=str, help="Search for entry by full or partial SHA-256 hash")
    parser.add_argument("--tail", type=int, help="Display last N entries")
    parser.add_argument("--summary", action="store_true", help="Display summary counts by event type")
    parser.add_argument("--verify", action="store_true", help="Run full SHA-256 cryptographic chain audit")
    parser.add_argument("--detail", action="store_true", help="Show formatted JSON details for matched entries")

    args = parser.parse_args()
    entries = load_ledger(args.file)

    if args.verify:
        verify_chain(entries)
        return

    if args.summary:
        print(f"\n=== LEDGER SUMMARY: {args.file} ({len(entries)} Total Entries) ===")
        counts = {}
        for _, entry, _ in entries:
            ev = entry.get("event", "UNKNOWN")
            counts[ev] = counts.get(ev, 0) + 1
        for ev, count in counts.items():
            print(f" - {ev:<32} : {count} entry(ies)")
        return

    matched = entries

    if args.event:
        matched = [(num, e, r) for num, e, r in matched if args.event.lower() in e.get("event", "").lower()]

    if args.hash:
        matched = [(num, e, r) for num, e, r in matched if args.hash.lower() in e.get("sha256", "").lower() or args.hash.lower() in e.get("prev_hash", "").lower()]

    if args.tail:
        matched = matched[-args.tail:]

    print(f"\n=== LEDGER QUERY RESULTS: {len(matched)} / {len(entries)} ENTRIES MATCHED ===")
    print("=" * 80)
    for line_num, entry, _ in matched:
        print_entry(line_num, entry, detailed=args.detail)

if __name__ == "__main__":
    main()

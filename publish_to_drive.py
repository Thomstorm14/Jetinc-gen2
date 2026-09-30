"""
publish_to_drive.py — copies the live ledger + benchmark results + a
status summary into a Google Drive–synced folder, so Apps Script can
pick them up on its next hourly scan.

This is DELIBERATELY standalone — it does not touch genone.py,
benchmark_harness.py, or ledger.py. Run it manually after a session,
or (better) set it up as a Windows Scheduled Task to run every 15-30
minutes so the live dashboard updates itself with no manual work.

SETUP (one time):
1. Install Google Drive for Desktop: https://www.google.com/drive/download/
2. Sign in with whichever account you want to own the live folder
   (tomwhitten9@gmail.com or jetstorm.central@gmail.com -- your call).
3. In that Drive, create a folder named exactly: JETinc_Live_Ledger
4. Find where Drive for Desktop mounted it locally -- usually something
   like G colon backslash My Drive backslash JETinc_Live_Ledger, or
   under your user folder's Google Drive directory. Confirm the exact
   path once installed and update DRIVE_SYNC_FOLDER below.

USAGE:
    python publish_to_drive.py
"""

import json
import os
import shutil
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Confirmed real path on this machine (found via the shortcut target,
# 7/19/2026 session):
DRIVE_SYNC_FOLDER = "C:/Users/tomwh/My Drive/JETinc_Live_Ledger"
# ---------------------------------------------------------------------------

LOCAL_LEDGER_JSONL = r"C:\JETinc\Logs\Trident\ledger_v1.jsonl"
LOCAL_BENCHMARK_RESULTS = r"C:\JETinc\JETcity_Launchpad\jetinc_build\benchmark_results.json"


def verify_local_chain():
    """Re-runs the same verification logic ledger.py uses, so the status
    file reflects a real, current check — not a stale claim."""
    import hashlib

    GENESIS_HASH = "0" * 64
    if not os.path.exists(LOCAL_LEDGER_JSONL):
        return False, "no ledger file found", 0

    entries = []
    with open(LOCAL_LEDGER_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    expected_prev = GENESIS_HASH
    for e in entries:
        if e["prev_hash"] != expected_prev:
            return False, f"chain break at index {e['index']}", len(entries)
        payload = {
            "index": e["index"], "timestamp": e["timestamp"], "agent": e["agent"],
            "phase": e["phase"], "role": e["role"], "content": e["content"],
            "meta": e["meta"], "prev_hash": e["prev_hash"],
        }
        recomputed = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if recomputed != e["entry_hash"]:
            return False, f"tamper detected at index {e['index']}", len(entries)
        expected_prev = e["entry_hash"]
    return True, "chain intact", len(entries)


def main():
    if not os.path.isdir(DRIVE_SYNC_FOLDER):
        print(f"ERROR: Drive sync folder not found at:\n  {DRIVE_SYNC_FOLDER}")
        print("Edit DRIVE_SYNC_FOLDER at the top of this script to the real path")
        print("once Google Drive for Desktop is installed and synced.")
        return

    chain_ok, chain_detail, entry_count = verify_local_chain()

    status = {
        "last_published_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "chain_ok": chain_ok,
        "chain_detail": chain_detail,
        "entry_count": entry_count,
    }
    status_path = os.path.join(DRIVE_SYNC_FOLDER, "status.json")
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2)
    print(f"Wrote status.json — chain_ok={chain_ok}, entries={entry_count}")

    if os.path.exists(LOCAL_LEDGER_JSONL):
        dest = os.path.join(DRIVE_SYNC_FOLDER, "ledger_v1.jsonl")
        shutil.copy2(LOCAL_LEDGER_JSONL, dest)
        print(f"Copied ledger_v1.jsonl ({entry_count} entries)")
    else:
        print("WARNING: local ledger_v1.jsonl not found — nothing copied.")

    if os.path.exists(LOCAL_BENCHMARK_RESULTS):
        dest = os.path.join(DRIVE_SYNC_FOLDER, "benchmark_results.json")
        shutil.copy2(LOCAL_BENCHMARK_RESULTS, dest)
        print("Copied benchmark_results.json")

    print("\nDone. Google Drive for Desktop will sync these automatically.")
    print("Apps Script's hourly trigger will pick up changes on its next run.")


if __name__ == "__main__":
    main()

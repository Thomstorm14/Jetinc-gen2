"""
bootstrap_roster.py — one-time setup. Run this ONCE before genone.py's
roster-based version will work. It creates real, permanent Prime IDs
for 1 TV + 3 MTVs in each of the three cities (9 agents total, on DAY
shift to start) and adds them to the working roster.

Safe to re-run: existing short_codes are skipped (register() already
raises on duplicates, this catches that and moves on), so re-running
this after adding more cities/shifts later won't create duplicates.

Run this from the same folder as genone.py:
    python bootstrap_roster.py
"""

import os
from prime_registry import PrimeRegistry, DuplicatePrimeIDError
from roster import Roster, CITIES

REGISTRY_PATH = r"C:\JETinc\Logs\Trident\prime_registry.jsonl"
ROSTER_PATH = r"C:\JETinc\Logs\Trident\roster.jsonl"
STARTING_SHIFT = "DAY"


def main():
    registry = PrimeRegistry(REGISTRY_PATH)
    roster = Roster(ROSTER_PATH, registry)

    created = 0
    skipped = 0

    for city in CITIES:
        # One TV per city
        tv_code = f"TV-{city}"
        try:
            tv = registry.register(tv_code, "TV", city, STARTING_SHIFT, f"TVSEAT-{city}")
            roster.add_agent(tv.prime_id, home_city=city, current_shift=STARTING_SHIFT)
            print(f"Created TV  : {tv_code} -> {tv.prime_id}")
            created += 1
        except DuplicatePrimeIDError:
            existing = registry.resolve(tv_code)
            roster.add_agent(existing.prime_id, home_city=city, current_shift=STARTING_SHIFT)
            print(f"Already existed, added to roster: {tv_code} -> {existing.prime_id}")
            skipped += 1

        # Three MTVs per city
        for i in range(3):
            mtv_code = f"MTV-{city}-{i}"
            try:
                mtv = registry.register(mtv_code, "MTV", city, STARTING_SHIFT, f"MTVSEAT-{city}-{i}")
                roster.add_agent(mtv.prime_id, home_city=city, current_shift=STARTING_SHIFT)
                print(f"Created MTV : {mtv_code} -> {mtv.prime_id}")
                created += 1
            except DuplicatePrimeIDError:
                existing = registry.resolve(mtv_code)
                roster.add_agent(existing.prime_id, home_city=city, current_shift=STARTING_SHIFT)
                print(f"Already existed, added to roster: {mtv_code} -> {existing.prime_id}")
                skipped += 1

    print(f"\nDone. {created} new agents created, {skipped} already existed.")
    print(f"Registry : {REGISTRY_PATH}")
    print(f"Roster   : {ROSTER_PATH}")
    print("\nYou can now run genone.py — it will pull real agents from this roster.")


if __name__ == "__main__":
    main()

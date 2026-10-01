"""
roster.py — Cross-city, cross-shift roster and workstack assignment for
JETinc / GenOne.

CORE IDEA
---------
prime_registry.py already gives every agent a permanent Prime ID with a
city, shift, and seat baked into the ID at creation time. What that file
does NOT do is track an agent's CURRENT city/shift over time, or answer
the question "which 12 agents should form the next workstack?" That is
what this file adds, on top of — not instead of — the existing registry.

TWO INDEPENDENT ROTATIONS
--------------------------
  1. Shift rotation (weekly): DAY -> NIGHT -> GRAVEYARD -> DAY ...
  2. City rotation (weekly, independent clock): JULIANBAY -> EVANSRIDGE
     -> MOUNTTHOMAS -> JULIANBAY ...

Because these two rotations move independently, at any given moment
there is always at least one agent covering every (city, shift) pair —
9 pairs total — which is what makes true 24/7, cross-context coverage
possible without needing a separate roster per city.

WORKSTACK ASSIGNMENT RULE
--------------------------
A full workstack (Triformer + 3 Tricores) is 12 seats total:
  - 3 TV seats  (Triformer level)
  - 9 MTV seats (3 per Tricore, one Tricore per TV)

Per Thom's design: the cross-city triangulation happens at the TV level.
The 3 TV seats are filled by 3 agents from 3 DIFFERENT cities, all on
the SAME shift — this is what makes the final merge genuinely
cross-context (matches the "Fractal Triangulation" invariant in
ISSUE_001). Each TV's 3 MTV seats are filled by agents from that SAME
TV's city (tight internal deliberation, not cross-context — the
cross-context work already happened one level up, at the TV merge).

This file does not replace prime_registry.py. It reads/writes its own
roster.jsonl and looks up real Prime IDs via a PrimeRegistry instance
passed in at construction.
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from prime_registry import PrimeRegistry, RegistryEntry


CITIES = ["JULIANBAY", "EVANSRIDGE", "MOUNTTHOMAS"]
SHIFTS = ["DAY", "NIGHT", "GRAVEYARD"]  # ALLSHIFT (Admiral/SS) never rotates


def next_in_cycle(current: str, cycle: list[str]) -> str:
    """Advances one step through a fixed rotation list, wrapping around."""
    idx = cycle.index(current)
    return cycle[(idx + 1) % len(cycle)]


@dataclass
class RosterEntry:
    prime_id: str
    short_code: str
    entity_type: str   # "TV" or "MTV" — roster only tracks working agents
    home_city: str      # rotates independently of shift
    current_shift: str  # rotates independently of city
    last_rotated: str

    def to_json(self) -> dict:
        return {
            "prime_id": self.prime_id,
            "short_code": self.short_code,
            "entity_type": self.entity_type,
            "home_city": self.home_city,
            "current_shift": self.current_shift,
            "last_rotated": self.last_rotated,
        }


class Roster:
    def __init__(self, roster_path: str, registry: PrimeRegistry):
        """
        roster_path: full path to a .jsonl file tracking CURRENT
                     city/shift per agent (separate from prime_registry's
                     permanent registration record).
        registry:    an already-constructed PrimeRegistry, used to
                     validate that a prime_id is real before it's added
                     to the roster.
        """
        self.roster_path = roster_path
        self.registry = registry
        self._entries: dict[str, RosterEntry] = {}  # keyed by prime_id
        self._load_existing()

    # ------------------------------------------------------------------
    def _load_existing(self) -> None:
        if not os.path.exists(self.roster_path):
            return
        with open(self.roster_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                entry = RosterEntry(**data)
                self._entries[entry.prime_id] = entry

    def _save_all(self) -> None:
        """Roster is small (one line per active agent) and rewritten in
        full on every change — unlike the ledger, this is current STATE,
        not an append-only history, so overwriting is correct here."""
        os.makedirs(os.path.dirname(self.roster_path) or ".", exist_ok=True)
        with open(self.roster_path, "w", encoding="utf-8") as f:
            for entry in self._entries.values():
                f.write(json.dumps(entry.to_json(), sort_keys=True) + "\n")

    # ------------------------------------------------------------------
    # Adding an agent to the roster
    # ------------------------------------------------------------------
    def add_agent(self, prime_id: str, home_city: str, current_shift: str) -> RosterEntry:
        """Adds an already-registered agent (must already exist in
        PrimeRegistry) onto the working roster with a starting city/shift.
        """
        registry_entry = self.registry.get(prime_id)
        if registry_entry is None:
            raise ValueError(f"Prime ID '{prime_id}' is not a registered agent — register it in PrimeRegistry first.")
        if registry_entry.entity_type not in ("TV", "MTV"):
            raise ValueError(f"Only TV and MTV entities go on the working roster, not '{registry_entry.entity_type}'.")

        entry = RosterEntry(
            prime_id=prime_id,
            short_code=registry_entry.short_code,
            entity_type=registry_entry.entity_type,
            home_city=home_city.upper(),
            current_shift=current_shift.upper(),
            last_rotated=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        self._entries[prime_id] = entry
        self._save_all()
        return entry

    # ------------------------------------------------------------------
    # Weekly rotation — two independent clocks
    # ------------------------------------------------------------------
    def rotate_shifts(self) -> None:
        """Advances every roster agent one step: DAY -> NIGHT -> GRAVEYARD -> DAY."""
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for entry in self._entries.values():
            entry.current_shift = next_in_cycle(entry.current_shift, SHIFTS)
            entry.last_rotated = now
        self._save_all()

    def rotate_cities(self) -> None:
        """Advances every roster agent one step: JULIANBAY -> EVANSRIDGE -> MOUNTTHOMAS -> JULIANBAY."""
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for entry in self._entries.values():
            entry.home_city = next_in_cycle(entry.home_city, CITIES)
            entry.last_rotated = now
        self._save_all()

    # ------------------------------------------------------------------
    # Workstack assignment — the actual "pull 12 agents" logic
    # ------------------------------------------------------------------
    def assign_workstack(self, shift: str, rng: Optional[random.Random] = None) -> dict:
        """Returns a full 12-seat workstack assignment for the given shift:

            {
              "shift": "DAY",
              "tv_seats": [
                 {"city": "JULIANBAY",  "tv_prime_id": "...",
                  "mtv_prime_ids": ["...", "...", "..."]},
                 {"city": "EVANSRIDGE", "tv_prime_id": "...",
                  "mtv_prime_ids": ["...", "...", "..."]},
                 {"city": "MOUNTTHOMAS","tv_prime_id": "...",
                  "mtv_prime_ids": ["...", "...", "..."]},
              ]
            }

        Rule: one TV per city (all same shift) — this is the cross-city
        triangulation point. Each TV's 3 MTVs come from that SAME city
        (and same shift) — tight internal deliberation, not cross-context.

        Raises ValueError with a clear message if any city is short of
        agents for this shift, rather than silently returning a partial
        or wrong-shaped workstack.
        """
        shift = shift.upper()
        rng = rng or random.Random()
        result_seats = []

        for city in CITIES:
            candidates_tv = [
                e for e in self._entries.values()
                if e.entity_type == "TV" and e.home_city == city and e.current_shift == shift
            ]
            candidates_mtv = [
                e for e in self._entries.values()
                if e.entity_type == "MTV" and e.home_city == city and e.current_shift == shift
            ]

            if not candidates_tv:
                raise ValueError(f"No TV available in {city} on {shift} shift — cannot assign workstack.")
            if len(candidates_mtv) < 3:
                raise ValueError(
                    f"Only {len(candidates_mtv)} MTV(s) available in {city} on {shift} shift "
                    f"— need 3. Cannot assign workstack."
                )

            chosen_tv = rng.choice(candidates_tv)
            chosen_mtvs = rng.sample(candidates_mtv, 3)

            result_seats.append({
                "city": city,
                "tv_prime_id": chosen_tv.prime_id,
                "mtv_prime_ids": [m.prime_id for m in chosen_mtvs],
            })

        return {"shift": shift, "tv_seats": result_seats}


if __name__ == "__main__":
    # Self-test: build a small registry + roster, populate it, assign a
    # workstack, and prove the cross-city / same-city rules both hold.
    import tempfile

    tmpdir = tempfile.mkdtemp()
    reg = PrimeRegistry(os.path.join(tmpdir, "prime_registry.jsonl"))
    roster = Roster(os.path.join(tmpdir, "roster.jsonl"), reg)

    # Register + add 1 TV and 3 MTVs per city, all on DAY shift
    for city in CITIES:
        tv = reg.register(f"TV-{city}", "TV", city, "DAY", f"TVSEAT-{city}")
        roster.add_agent(tv.prime_id, home_city=city, current_shift="DAY")
        for i in range(3):
            mtv = reg.register(f"MTV-{city}-{i}", "MTV", city, "DAY", f"MTVSEAT-{city}-{i}")
            roster.add_agent(mtv.prime_id, home_city=city, current_shift="DAY")

    assignment = roster.assign_workstack("DAY")
    print("Workstack assignment:")
    print(json.dumps(assignment, indent=2))

    # Prove the rule: exactly 3 TV seats, one per city, no duplicates
    cities_used = [seat["city"] for seat in assignment["tv_seats"]]
    assert sorted(cities_used) == sorted(CITIES), "Each city must supply exactly one TV seat."

    # Prove each TV's MTVs are registered to that SAME city
    for seat in assignment["tv_seats"]:
        for mtv_id in seat["mtv_prime_ids"]:
            mtv_entry = roster._entries[mtv_id]
            assert mtv_entry.home_city == seat["city"], (
                f"MTV {mtv_id} is from {mtv_entry.home_city} but was assigned "
                f"under {seat['city']}'s TV — MTVs must stay within their TV's city."
            )

    print("\nSelf-test passed: 3 TV seats, one per city, no city repeated;")
    print("every MTV stayed within its own TV's city.")

    # Prove rotation actually moves things
    before = {e.prime_id: (e.home_city, e.current_shift) for e in roster._entries.values()}
    roster.rotate_shifts()
    after_shift = {e.prime_id: (e.home_city, e.current_shift) for e in roster._entries.values()}
    assert before != after_shift, "rotate_shifts() should change every entry's shift."
    roster.rotate_cities()
    after_city = {e.prime_id: (e.home_city, e.current_shift) for e in roster._entries.values()}
    assert after_shift != after_city, "rotate_cities() should change every entry's city."
    print("Rotation self-test passed: shift and city rotations both apply independently.")

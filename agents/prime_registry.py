"""
prime_registry.py — Prime ID generation, registry, and validation for
JETinc / GenOne.

CORE IDEA
---------
Every entity that ever exists in the system — every MTV, every TV,
every Triformer seat, Storm Shadow, Admiral Prime (Thom), and every
future subscribed user — gets exactly one Prime ID, created once, at
first instantiation, and never reused.

A Prime ID is not just a name. It's a self-describing, verifiable
token: anyone (or anything) holding a Prime ID string can be checked
against the registry to prove it is real, was legitimately created,
and has not been duplicated or forged. That check is the whole
security model: the system isn't built to keep people out, it's built
so nothing can move inside it without a Prime ID that validates —
and any Prime ID that doesn't validate is instantly, unambiguously
identifiable as a breach.

SHADOW
------
There is no separate "Shadow" system. An agent's Shadow IS simply its
complete, filtered history inside the Trident Ledger — every entry
that entry's `meta["prime_id"]` matches. Because the ledger is
SHA-256 block-chained, every Shadow is automatically tamper-evident.
`get_shadow()` below does that filtering. As long as every
`ledger.add_entry()` call includes `meta={"prime_id": ..., ...}`,
this works for free.

PRIME ID FORMAT
---------------
    JET-<entity>-<city>-<shift>-<seat>-<epoch>-<hash8>

    entity : TV | MTV | TRIFORMER | SS | ADMIRAL | USER
    city   : JULIANBAY | EVANSRIDGE | MOUNTTHOMAS | PRIME (Admiral/SS/system-level)
    shift  : DAY | NIGHT | GRAVEYARD | ALLSHIFT
    seat   : the permanent seat code (e.g. TV1CORE2, TRIFORMER1, OVERSEER)
    epoch  : unix timestamp (int, seconds) at creation — guarantees
             no two agents ever collide even if every other field matches
    hash8  : first 8 hex chars of SHA256(entity|city|shift|seat|epoch|salt)
             — a checksum on the ID's own components. Anyone can
             recompute this from the visible fields and confirm it
             matches. If it doesn't match, the ID has been altered
             or fabricated, full stop.

The `salt` is a fixed system secret (not embedded in the ID itself),
so an attacker who sees a valid Prime ID cannot forge a new one for a
different seat/time just by copying the hashing pattern — they'd also
need the salt, which never leaves this file / the registry's trust
boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# System salt — NOT a real secret management solution. This is a placeholder
# so the hashing scheme is demonstrably correct. Before any real deployment
# (i.e. before Tri-Cities go-live, Section 5F #5), move this to an actual
# secrets store / environment variable and rotate it. Flagging clearly here
# rather than pretending a hardcoded string is real security.
# ---------------------------------------------------------------------------
SYSTEM_SALT = "JETINC-DEV-SALT-REPLACE-BEFORE-LIVE"

VALID_ENTITIES = {"TV", "MTV", "TRIFORMER", "SS", "ADMIRAL", "USER"}
VALID_CITIES = {"JULIANBAY", "EVANSRIDGE", "MOUNTTHOMAS", "PRIME"}
VALID_SHIFTS = {"DAY", "NIGHT", "GRAVEYARD", "ALLSHIFT"}


class PrimeIDError(Exception):
    pass


class DuplicatePrimeIDError(PrimeIDError):
    pass


class InvalidPrimeIDError(PrimeIDError):
    pass


@dataclass
class RegistryEntry:
    short_code: str
    prime_id: str
    entity_type: str
    city: str
    shift: str
    seat: str
    epoch: int
    created: str
    status: str = "active"  # active | retired | REVOKED-BREACH

    def to_json(self) -> dict:
        return {
            "short_code": self.short_code,
            "prime_id": self.prime_id,
            "entity_type": self.entity_type,
            "city": self.city,
            "shift": self.shift,
            "seat": self.seat,
            "epoch": self.epoch,
            "created": self.created,
            "status": self.status,
        }


def _compute_hash8(entity: str, city: str, shift: str, seat: str, epoch: int) -> str:
    payload = f"{entity}|{city}|{shift}|{seat}|{epoch}|{SYSTEM_SALT}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8]


def _build_prime_id(entity: str, city: str, shift: str, seat: str, epoch: int) -> str:
    hash8 = _compute_hash8(entity, city, shift, seat, epoch)
    return f"JET-{entity}-{city}-{shift}-{seat}-{epoch}-{hash8}"


class PrimeRegistry:
    def __init__(self, registry_path: str):
        """
        registry_path: full path to a .jsonl file, e.g.
                       r"C:\\JETinc\\Logs\\Trident\\prime_registry.jsonl"
        """
        self.registry_path = registry_path
        self._by_short: dict[str, RegistryEntry] = {}
        self._by_prime_id: dict[str, RegistryEntry] = {}
        self._load_existing()

    # ------------------------------------------------------------------
    def _load_existing(self) -> None:
        if not os.path.exists(self.registry_path):
            return
        with open(self.registry_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                entry = RegistryEntry(**data)
                self._by_short[entry.short_code] = entry
                self._by_prime_id[entry.prime_id] = entry

    def _append(self, entry: RegistryEntry) -> None:
        os.makedirs(os.path.dirname(self.registry_path) or ".", exist_ok=True)
        with open(self.registry_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_json(), sort_keys=True) + "\n")

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------
    def register(
        self,
        short_code: str,
        entity_type: str,
        city: str,
        shift: str,
        seat: str,
    ) -> RegistryEntry:
        """Creates and registers a new Prime ID. Raises if short_code is
        already taken (agents don't move seats — a short_code should map
        to exactly one Prime ID for its entire active life; retire the
        old one explicitly before reissuing a short_code).
        """
        entity_type = entity_type.upper()
        city = city.upper()
        shift = shift.upper()
        if entity_type not in VALID_ENTITIES:
            raise PrimeIDError(f"Unknown entity_type '{entity_type}', must be one of {VALID_ENTITIES}")
        if city not in VALID_CITIES:
            raise PrimeIDError(f"Unknown city '{city}', must be one of {VALID_CITIES}")
        if shift not in VALID_SHIFTS:
            raise PrimeIDError(f"Unknown shift '{shift}', must be one of {VALID_SHIFTS}")

        if short_code in self._by_short and self._by_short[short_code].status == "active":
            raise DuplicatePrimeIDError(
                f"short_code '{short_code}' already has an ACTIVE Prime ID "
                f"({self._by_short[short_code].prime_id}). Retire it first "
                f"if this is intentional reassignment."
            )

        # Loop guards against the astronomically unlikely case of an
        # epoch-second collision producing the same hash8 twice.
        while True:
            epoch = int(time.time())
            prime_id = _build_prime_id(entity_type, city, shift, seat, epoch)
            if prime_id not in self._by_prime_id:
                break
            time.sleep(1)

        entry = RegistryEntry(
            short_code=short_code,
            prime_id=prime_id,
            entity_type=entity_type,
            city=city,
            shift=shift,
            seat=seat,
            epoch=epoch,
            created=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        self._by_short[short_code] = entry
        self._by_prime_id[prime_id] = entry
        self._append(entry)
        return entry

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------
    def resolve(self, short_code: str) -> Optional[RegistryEntry]:
        """Short-hand glossary lookup: 'TV1-CORE-2' -> full RegistryEntry."""
        return self._by_short.get(short_code)

    def get(self, prime_id: str) -> Optional[RegistryEntry]:
        return self._by_prime_id.get(prime_id)

    # ------------------------------------------------------------------
    # Validation — this IS the Silent Dispatch Red trigger check
    # ------------------------------------------------------------------
    def validate(self, prime_id: str) -> tuple[bool, str]:
        """Checks a presented Prime ID two ways:
          1. Structural: recompute hash8 from the visible fields embedded
             in the ID and confirm it matches. Catches fabricated/altered
             IDs immediately, without even touching the registry.
          2. Registry: confirm this exact Prime ID was actually issued
             and is still 'active'. Catches replay of a retired ID, or
             a structurally-valid-looking ID that was never really issued
             (which would require the attacker to already have the salt).

        Returns (True, "ok") only if both checks pass.
        Any False result is, by design, a Silent Dispatch Red trigger
        condition — see silent_dispatch_red.md.
        """
        parts = prime_id.split("-")
        if len(parts) != 7 or parts[0] != "JET":
            return False, "STRUCTURAL_FAIL: malformed Prime ID shape"

        _, entity, city, shift, seat, epoch_str, hash8 = parts
        try:
            epoch = int(epoch_str)
        except ValueError:
            return False, "STRUCTURAL_FAIL: epoch is not a valid integer"

        expected_hash8 = _compute_hash8(entity, city, shift, seat, epoch)
        if expected_hash8 != hash8:
            return False, "STRUCTURAL_FAIL: hash8 does not match recomputed value — ID altered or forged"

        registry_entry = self._by_prime_id.get(prime_id)
        if registry_entry is None:
            return False, "REGISTRY_FAIL: structurally valid ID was never issued by this registry"
        if registry_entry.status != "active":
            return False, f"REGISTRY_FAIL: ID exists but status is '{registry_entry.status}', not active"

        return True, "ok"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def retire(self, short_code: str) -> None:
        entry = self._by_short.get(short_code)
        if entry is None:
            raise PrimeIDError(f"No registry entry for short_code '{short_code}'")
        entry.status = "retired"
        self._append(entry)  # append-only log: retirement is its own record

    def revoke_breach(self, prime_id: str) -> None:
        """Marks a Prime ID as compromised. Used during Silent Dispatch Red
        containment/review — does not delete history, just flags status so
        future validate() calls fail closed on this ID going forward.
        """
        entry = self._by_prime_id.get(prime_id)
        if entry is None:
            raise PrimeIDError(f"No registry entry for prime_id '{prime_id}'")
        entry.status = "REVOKED-BREACH"
        self._append(entry)


# ---------------------------------------------------------------------------
# Shadow lookup — pulls an agent's full traceable history straight from the
# Trident Ledger's .jsonl chain, filtered by prime_id. Read-only, ledger.py
# stays the single source of truth; this just filters it.
# ---------------------------------------------------------------------------
def get_shadow(ledger_jsonl_path: str, prime_id: str) -> list[dict]:
    """Returns every ledger entry whose meta.prime_id matches, in order.
    This IS the agent's Shadow: its complete, chained, chronological
    record inside the system.
    """
    shadow = []
    if not os.path.exists(ledger_jsonl_path):
        return shadow
    with open(ledger_jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if entry.get("meta", {}).get("prime_id") == prime_id:
                shadow.append(entry)
    return shadow


if __name__ == "__main__":
    import tempfile

    tmpdir = tempfile.mkdtemp()
    reg_path = os.path.join(tmpdir, "prime_registry.jsonl")
    reg = PrimeRegistry(reg_path)

    # Register a few legitimate agents + Admiral Prime + SS
    ss = reg.register("SS", "SS", "PRIME", "ALLSHIFT", "OVERSEER")
    admiral = reg.register("ADMIRAL-PRIME", "ADMIRAL", "PRIME", "ALLSHIFT", "FOUNDER")
    tv1core2 = reg.register("TV1-CORE-2", "MTV", "JULIANBAY", "DAY", "TV1CORE2")

    print("SS Prime ID:      ", ss.prime_id)
    print("Admiral Prime ID: ", admiral.prime_id)
    print("TV1-CORE-2 ID:    ", tv1core2.prime_id)

    # Legit validation
    ok, detail = reg.validate(tv1core2.prime_id)
    print("\nValidate legit ID:", ok, detail)
    assert ok

    # Duplicate short_code should fail
    try:
        reg.register("TV1-CORE-2", "MTV", "JULIANBAY", "DAY", "TV1CORE2")
        print("ERROR: duplicate registration should have raised")
    except DuplicatePrimeIDError as e:
        print("Duplicate short_code correctly rejected:", e)

    # Forged ID (structurally malformed) should fail
    ok, detail = reg.validate("JET-MTV-JULIANBAY-DAY-TV1CORE2-1752710400-deadbeef")
    print("\nValidate forged ID:", ok, detail)
    assert not ok

    # Structurally-plausible but never-issued ID should fail at registry check
    fake_epoch = 1752710400
    fake_hash = _compute_hash8("MTV", "JULIANBAY", "DAY", "TV1CORE2", fake_epoch)
    fake_but_unregistered = f"JET-MTV-JULIANBAY-DAY-TV1CORE2-{fake_epoch}-{fake_hash}"
    ok, detail = reg.validate(fake_but_unregistered)
    print("Validate unregistered-but-structurally-valid ID:", ok, detail)
    assert not ok

    # Revoke and re-check
    reg.revoke_breach(tv1core2.prime_id)
    ok, detail = reg.validate(tv1core2.prime_id)
    print("\nValidate after revoke_breach:", ok, detail)
    assert not ok

    print("\nSelf-test passed: registration, duplicate rejection, forgery")
    print("detection, and breach revocation all behave correctly.")

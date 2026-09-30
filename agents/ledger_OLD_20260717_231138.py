"""
TridentLedger — SHA-256 block-chained ledger for JETinc / GenOne.

Replaces the old ad-hoc markdown-append ledger. Every entry's hash
incorporates the previous entry's hash, so any edit to an earlier
entry breaks the chain from that point forward — tamper-evident,
not tamper-proof (matches the Blueprint Level 11 philosophy: not
unhackable, but any tampering is provably detectable).

Writes incrementally after every call to add_entry() — this preserves
the fix from the previous ledger version where a crash mid-run could
silently lose all data. Two files are kept in sync on every write:

  - <base>.jsonl   machine-readable chain, one JSON object per line,
                   this is the file verify_chain() actually checks
  - <base>.md      human-readable rendering of the same chain, for
                   the "read it in a text editor" use case

Usage (drop-in for the old ledger.write_ledger() call pattern):

    from ledger import TridentLedger

    ledger = TridentLedger(r"C:\\JETinc\\Logs\\Trident\\ledger_v1")
    ledger.add_entry(
        agent="TV-1", phase="OR", role="Triformer-Lead",
        content="...output text...",
        meta={"seat": 1, "cycle": 4},
    )
    # ledger.add_entry(...) again after every phase, as before

    ok, detail = ledger.verify_chain()
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


GENESIS_HASH = "0" * 64


@dataclass
class LedgerEntry:
    index: int
    timestamp: str
    agent: str
    phase: str
    role: str
    content: str
    meta: dict
    prev_hash: str
    entry_hash: str = field(default="")

    def canonical_payload(self) -> str:
        """Deterministic string used as hashing input.

        Field order and separators are fixed so the same logical
        entry always hashes to the same value, and so this class
        (or any re-implementation) can independently reproduce it
        for verification.
        """
        payload = {
            "index": self.index,
            "timestamp": self.timestamp,
            "agent": self.agent,
            "phase": self.phase,
            "role": self.role,
            "content": self.content,
            "meta": self.meta,
            "prev_hash": self.prev_hash,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def compute_hash(self) -> str:
        return hashlib.sha256(self.canonical_payload().encode("utf-8")).hexdigest()

    def to_json(self) -> dict:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "agent": self.agent,
            "phase": self.phase,
            "role": self.role,
            "content": self.content,
            "meta": self.meta,
            "prev_hash": self.prev_hash,
            "entry_hash": self.entry_hash,
        }


class TridentLedger:
    def __init__(self, base_path: str):
        """
        base_path: path WITHOUT extension, e.g.
                   r"C:\\JETinc\\Logs\\Trident\\ledger_v1"
                   -> writes ledger_v1.jsonl and ledger_v1.md
        """
        self.base_path = base_path
        self.jsonl_path = base_path + ".jsonl"
        self.md_path = base_path + ".md"
        self.entries: list[LedgerEntry] = []
        self._load_existing()

    # ------------------------------------------------------------------
    # Loading / bootstrapping
    # ------------------------------------------------------------------
    def _load_existing(self) -> None:
        """If a chain already exists on disk, load it so a new run
        continues the SAME chain rather than starting a disconnected
        one. If not, the first add_entry() call will create genesis.
        """
        if not os.path.exists(self.jsonl_path):
            return
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                entry = LedgerEntry(
                    index=data["index"],
                    timestamp=data["timestamp"],
                    agent=data["agent"],
                    phase=data["phase"],
                    role=data["role"],
                    content=data["content"],
                    meta=data.get("meta", {}),
                    prev_hash=data["prev_hash"],
                    entry_hash=data["entry_hash"],
                )
                self.entries.append(entry)

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------
    def add_entry(
        self,
        agent: str,
        phase: str,
        role: str,
        content: str,
        meta: Optional[dict[str, Any]] = None,
    ) -> LedgerEntry:
        prev_hash = self.entries[-1].entry_hash if self.entries else GENESIS_HASH
        entry = LedgerEntry(
            index=len(self.entries),
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            agent=agent,
            phase=phase,
            role=role,
            content=content,
            meta=meta or {},
            prev_hash=prev_hash,
        )
        entry.entry_hash = entry.compute_hash()
        self.entries.append(entry)
        self._append_jsonl(entry)
        self._append_markdown(entry)
        return entry

    def _append_jsonl(self, entry: LedgerEntry) -> None:
        os.makedirs(os.path.dirname(self.jsonl_path) or ".", exist_ok=True)
        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_json(), sort_keys=True) + "\n")

    def _append_markdown(self, entry: LedgerEntry) -> None:
        os.makedirs(os.path.dirname(self.md_path) or ".", exist_ok=True)
        is_new = not os.path.exists(self.md_path)
        with open(self.md_path, "a", encoding="utf-8") as f:
            if is_new:
                f.write("# Trident Ledger — SHA-256 Block-Chained\n\n")
                f.write(
                    "Each entry hash = SHA256(index, timestamp, agent, phase, "
                    "role, content, meta, prev_hash). Chain integrity can be "
                    "checked with `TridentLedger.verify_chain()`.\n\n---\n\n"
                )
            f.write(f"## Entry {entry.index} — {entry.phase} — {entry.agent}\n\n")
            f.write(f"- **Timestamp:** {entry.timestamp}\n")
            f.write(f"- **Role:** {entry.role}\n")
            if entry.meta:
                f.write(f"- **Meta:** {json.dumps(entry.meta, sort_keys=True)}\n")
            f.write(f"- **Prev hash:** `{entry.prev_hash}`\n")
            f.write(f"- **Entry hash:** `{entry.entry_hash}`\n\n")
            f.write(f"{entry.content}\n\n---\n\n")

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------
    def verify_chain(self) -> tuple[bool, str]:
        """Recomputes every hash from stored fields and checks linkage.
        Returns (True, "ok") if intact, or (False, detail) pointing at
        the first broken entry.
        """
        expected_prev = GENESIS_HASH
        for entry in self.entries:
            if entry.prev_hash != expected_prev:
                return False, (
                    f"Chain break at index {entry.index}: prev_hash on file "
                    f"({entry.prev_hash}) does not match expected "
                    f"({expected_prev}) — an entry before this one was "
                    f"altered, deleted, or reordered."
                )
            recomputed = entry.compute_hash()
            if recomputed != entry.entry_hash:
                return False, (
                    f"Tamper detected at index {entry.index} ({entry.agent}/"
                    f"{entry.phase}): stored hash {entry.entry_hash} does not "
                    f"match recomputed hash {recomputed} — this entry's "
                    f"content was modified after being written."
                )
            expected_prev = entry.entry_hash
        return True, f"ok — {len(self.entries)} entries verified, chain intact"

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------
    def latest_hash(self) -> str:
        return self.entries[-1].entry_hash if self.entries else GENESIS_HASH

    def __len__(self) -> int:
        return len(self.entries)


if __name__ == "__main__":
    # Self-test: write a small chain, verify it, then tamper and
    # verify again to prove detection works.
    import tempfile

    tmpdir = tempfile.mkdtemp()
    test_base = os.path.join(tmpdir, "test_ledger")
    led = TridentLedger(test_base)

    led.add_entry("TV-1", "OR", "Triformer-Lead", "First output.", {"cycle": 1})
    led.add_entry("MTV-1a", "SR1", "Tricore-Member", "Second output.", {"cycle": 1})
    led.add_entry("MTV-1b", "SR2", "Tricore-Member", "Third output.", {"cycle": 1})

    ok, detail = led.verify_chain()
    print("Fresh chain:", ok, detail)
    assert ok

    # Tamper: reload from disk and mutate one entry's content directly,
    # simulating an after-the-fact edit to the jsonl file.
    with open(led.jsonl_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    tampered = json.loads(lines[1])
    tampered["content"] = "TAMPERED CONTENT"
    lines[1] = json.dumps(tampered, sort_keys=True) + "\n"
    with open(led.jsonl_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    led2 = TridentLedger(test_base)
    ok2, detail2 = led2.verify_chain()
    print("Tampered chain:", ok2, detail2)
    assert not ok2

    print("\nSelf-test passed: chain verifies clean, tamper is detected.")

"""
GenOne Bootstrap — JETtrix Chamber Model (CORRECTED ARCHITECTURE + TRIDENT
LEDGER / PRIME ID INTEGRATION)

Same task-cycle architecture as the previous corrected version (concurrent
Tricores + Triformer, Co Final Prime combine step, votes at both tiers).

WHAT CHANGED IN THIS PASS:
  - Ledger writes now go through TridentLedger (SHA-256 block-chained,
    structured per-entry, incremental — see agents/ledger.py). The old
    plain-markdown ledger_lines/write_ledger() buffering is gone.
  - Every seat's agent is registered once with PrimeRegistry
    (agents/prime_registry.py) at bootstrap, producing a real Prime ID
    per agent. Every ledger entry now carries that Prime ID in its meta,
    which is what makes an agent's full history ("Shadow") pullable by
    ID later via prime_registry.get_shadow().
  - Admiral Prime is registered once and logs OBSERVE entries at run
    start/end. There is no separate "Storm Shadow" Prime ID — Shadow is
    not a 15th watcher agent, it is the property every Prime ID already
    has: get_shadow(prime_id) IS that entity's shadow, for any entity.

Agents remain permanently seated. Only role bundles rotate, via
chamber.py's ChamberSystem, same as before.
"""

import time
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from triformer.triformer import Triformer
from chamber import ChamberSystem
from agents.ledger import TridentLedger
from agents.prime_registry import PrimeRegistry, PrimeIDError

# ============================================================
# PATHS
# ============================================================

LEDGER_BASE = r"C:\JETinc\Logs\Trident\ledger_v1"  # -> ledger_v1.jsonl + ledger_v1.md
REGISTRY_PATH = r"C:\JETinc\Logs\Trident\prime_registry.jsonl"

# Default deployment context for this single-machine dev run. When real
# multi-city deployment happens (Section 5F #5), these become per-agent
# instead of one blanket default.
from roster import Roster

DEFAULT_SHIFT = "DAY"
ROSTER_PATH = r"C:\JETinc\Logs\Trident\roster.jsonl"

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def safe_call(fn, label, *args):
    """Wraps any agent method call. Never lets one failure kill a run."""
    try:
        return fn(*args)
    except Exception as e:
        print(f"  [FAILED] {label}: {e}")
        return f"[FAILED — {label} did not respond: {e}]"


class Timer:
    """Small helper so every phase can report its own elapsed time,
    which then gets written straight into the ledger as proof of
    work — not just proof of output."""
    def __init__(self):
        self.start = time.time()

    def elapsed(self):
        return round(time.time() - self.start, 2)


# ============================================================
# SEAT DEFINITIONS — agents are permanent; roles are not
# ============================================================

class Seat:
    def __init__(self, seat_id, role, tier, is_lead=False):
        self.seat_id = seat_id
        self.role = role
        self.tier = tier
        self.is_lead = is_lead
        self.agent = None
        self.prime_id = None  # set once by register_all_seats()

    def seat_agent(self, agent):
        self.agent = agent

    def __repr__(self):
        lead_tag = " [R&R]" if self.is_lead else ""
        agent_name = self.agent.name if self.agent else "EMPTY"
        return f"{self.seat_id} ({self.role}){lead_tag} <- {agent_name}"


def build_triformer_seats():
    return [
        Seat("TRIFORMER-1", "R&R", "triformer", is_lead=True),
        Seat("TRIFORMER-2", "Flank-Alpha", "triformer"),
        Seat("TRIFORMER-3", "Flank-Beta", "triformer"),
    ]


def build_tricore_seats(tv_label):
    return [
        Seat(f"{tv_label}-CORE-1", "R&R", "tricore", is_lead=True),
        Seat(f"{tv_label}-CORE-2", "Flank-Alpha", "tricore"),
        Seat(f"{tv_label}-CORE-3", "Flank-Beta", "tricore"),
    ]


def assign_seats(triformer):
    triformer_seats = build_triformer_seats()
    tv_agents = [triformer.tv1, triformer.tv2, triformer.tv3]

    for seat, tv in zip(triformer_seats, tv_agents):
        seat.seat_agent(tv)

    tricore_groups = []
    for label, tv in zip(["TV1", "TV2", "TV3"], tv_agents):
        core_seats = build_tricore_seats(label)
        mtv_agents = [tv.mtv1, tv.mtv2, tv.mtv3]
        for seat, mtv in zip(core_seats, mtv_agents):
            seat.seat_agent(mtv)
        tricore_groups.append(core_seats)

    # NOTE: tricore_groups[i] is always physically housed inside
    # triformer_seats[i].agent (TV1/TV2/TV3 respectively). This
    # mapping is by SEATING, not by current role, so it stays fixed
    # even after roles rotate — that's what makes the Co Final Prime
    # combine step below always pair the right Tricore with its TV.
    return triformer_seats, tricore_groups


# ============================================================
# PRIME ID REGISTRATION — one Prime ID per seat, created once,
# reused on every subsequent run (seats don't move, so their
# Prime ID shouldn't churn either).
# ============================================================

def register_all_seats(registry: PrimeRegistry, triformer_seats, tricore_groups):
    roster = Roster(ROSTER_PATH, registry)
    assignment = roster.assign_workstack(DEFAULT_SHIFT)
    for i, seat in enumerate(triformer_seats):
        seat.prime_id = assignment["tv_seats"][i]["tv_prime_id"]
    for i, group in enumerate(tricore_groups):
        mtv_ids = assignment["tv_seats"][i]["mtv_prime_ids"]
        for seat, prime_id in zip(group, mtv_ids):
            seat.prime_id = prime_id


def register_admiral_prime(registry: PrimeRegistry):
    """Admiral Prime — registered once, reused forever.

    NOTE: there is deliberately no separate "Storm Shadow" registration
    here. Storm Shadow is not a 15th agent watching the other 14 — it is
    the property every single Prime ID already has: call
    prime_registry.get_shadow(ledger_path, any_prime_id) and you get that
    entity's complete, chained history. That's its shadow. Admiral Prime
    has one. Every TV and MTV seat has one. There is no global watcher
    Prime ID, because the shadow already belongs to the entity itself.
    """
    admiral = registry.resolve("ADMIRAL-PRIME")
    if admiral is None:
        admiral = registry.register(
            short_code="ADMIRAL-PRIME", entity_type="ADMIRAL", city="PRIME",
            shift="ALLSHIFT", seat="FOUNDER",
        )
    return admiral.prime_id


# ============================================================
# ROLE ROTATION — driven by chamber.py's ChamberSystem
# ============================================================

def apply_rotation(seats, chamber, is_triformer_tier):
    chamber.advance()
    roles = chamber.rotate_triformer() if is_triformer_tier else chamber.rotate_tricore()
    for seat, role in zip(seats, roles):
        seat.role = role
        seat.is_lead = (role == "R&R")


# ============================================================
# LEDGER HELPER — every call site below funnels through this,
# so every entry consistently carries prime_id/seat_id/cycle in meta.
# ============================================================

def log_entry(ledger: TridentLedger, seat, phase, content, cycle, extra_meta=None):
    meta = {"prime_id": seat.prime_id, "seat_id": seat.seat_id, "cycle": cycle}
    if extra_meta:
        meta.update(extra_meta)
    ledger.add_entry(
        agent=seat.agent.name,
        phase=phase,
        role=seat.role,
        content=str(content),
        meta=meta,
    )


# ============================================================
# SHARED DELIBERATION PRIMITIVES (used by both Tricore and
# Triformer levels — same pattern, different scale)
# ============================================================

def gather_or(seats, task, ledger, label, cycle):
    """Each seat produces an Original Response independently."""
    timer = Timer()

    def get_or(seat):
        print(f"  [{label}] OR | {seat.seat_id} ({seat.agent.name}) thinking...")
        text = safe_call(seat.agent.generate_or, f"OR/{seat.seat_id}", task)
        return seat, text

    with ThreadPoolExecutor(max_workers=3) as ex:
        results = [f.result() for f in [ex.submit(get_or, s) for s in seats]]

    or_responses = {}
    for seat, text in results:
        or_responses[seat.seat_id] = text
        log_entry(ledger, seat, "OR", text, cycle, {"tier_label": label})
    ledger.add_entry(
        agent="SYSTEM", phase="TIMING", role=label,
        content=f"OR phase time: {timer.elapsed()}s",
        meta={"cycle": cycle, "tier_label": label},
    )
    return or_responses


def gather_grades(seats, or_responses, task, ledger, label, cycle):
    """Each seat grades its right neighbor (SR1) and left neighbor (SR2)."""
    timer = Timer()
    n = len(seats)

    def get_grades(i):
        seat = seats[i]
        right = seats[(i + 1) % n]
        left = seats[(i - 1) % n]
        sr1 = safe_call(
            seat.agent.grade, f"SR1/{seat.seat_id}->{right.seat_id}",
            right.seat_id, or_responses[right.seat_id], task
        )
        sr2 = safe_call(
            seat.agent.grade, f"SR2/{seat.seat_id}->{left.seat_id}",
            left.seat_id, or_responses[left.seat_id], task
        )
        return seat, sr1, sr2

    with ThreadPoolExecutor(max_workers=3) as ex:
        results = [f.result() for f in [ex.submit(get_grades, i) for i in range(n)]]

    sr1_received, sr2_received = {}, {}
    for seat, sr1, sr2 in results:
        sr1_received[seat.seat_id] = sr1
        sr2_received[seat.seat_id] = sr2
        log_entry(ledger, seat, "SR1", sr1, cycle, {"tier_label": label, "grades": "right_neighbor"})
        log_entry(ledger, seat, "SR2", sr2, cycle, {"tier_label": label, "grades": "left_neighbor"})
    ledger.add_entry(
        agent="SYSTEM", phase="TIMING", role=label,
        content=f"Grading phase time: {timer.elapsed()}s",
        meta={"cycle": cycle, "tier_label": label},
    )
    return sr1_received, sr2_received


# ============================================================
# TRICORE CYCLE — full cycle, ends in a voted Tricore Final
# ============================================================

def run_tricore_cycle(seats, task, ledger, tier_label, cycle):
    ledger.add_entry(
        agent="SYSTEM", phase="CYCLE-START", role=tier_label,
        content=f"Directive: {task}", meta={"cycle": cycle, "timestamp": utc_now()},
    )

    or_responses = gather_or(seats, task, ledger, tier_label, cycle)
    sr1_received, sr2_received = gather_grades(seats, or_responses, task, ledger, tier_label, cycle)

    # CoMerge — each MTV combines its own OR + the two grades it received
    timer = Timer()

    def get_comerge(seat):
        return seat, safe_call(
            seat.agent.comerge, f"CoMerge/{seat.seat_id}",
            or_responses[seat.seat_id], sr1_received[seat.seat_id], sr2_received[seat.seat_id], task
        )

    with ThreadPoolExecutor(max_workers=3) as ex:
        comerge_results_list = [f.result() for f in [ex.submit(get_comerge, s) for s in seats]]
    comerge_results = {}
    for seat, result in comerge_results_list:
        comerge_results[seat.seat_id] = result
        log_entry(ledger, seat, "COMERGE", result, cycle, {"tier_label": tier_label})
    ledger.add_entry(
        agent="SYSTEM", phase="TIMING", role=tier_label,
        content=f"CoMerge phase time: {timer.elapsed()}s", meta={"cycle": cycle},
    )

    # Subprimal Merge — R&R seat only
    timer = Timer()
    rr_seat = next((s for s in seats if s.role == "R&R"), seats[0])
    flank_seats = [s for s in seats if s.role != "R&R"]
    merged = safe_call(
        rr_seat.agent.subprimal_merge, f"SubprimalMerge/{rr_seat.seat_id}",
        list(comerge_results.values()), task
    )
    log_entry(ledger, rr_seat, "SUBPRIMAL-MERGE", merged, cycle, {"tier_label": tier_label})
    ledger.add_entry(
        agent="SYSTEM", phase="TIMING", role=tier_label,
        content=f"Subprimal Merge time: {timer.elapsed()}s", meta={"cycle": cycle},
    )

    # Vote — the two flank seats vote on R&R's merge (Tricore-level vote)
    timer = Timer()
    for fs in flank_seats:
        v = safe_call(fs.agent.vote, f"Vote/{fs.seat_id}", merged, task)
        log_entry(ledger, fs, "VOTE", v, cycle, {"tier_label": tier_label, "voted_on": "subprimal_merge"})
    ledger.add_entry(
        agent="SYSTEM", phase="TIMING", role=tier_label,
        content=f"Vote phase time: {timer.elapsed()}s", meta={"cycle": cycle},
    )
    ledger.add_entry(
        agent="SYSTEM", phase="CYCLE-COMPLETE", role=tier_label,
        content=f"{tier_label} cycle complete. Tricore Final produced.",
        meta={"cycle": cycle},
    )

    return merged  # this is the Tricore Final for whichever TV houses this group


# ============================================================
# TRIFORMER OWN-MERGE — OR -> SR -> right/left submerge -> own merge
# (no vote yet — that happens after the Co Final Prime combine)
# ============================================================

def run_triformer_own_merge(tv_seats, task, ledger, cycle):
    label = "Triformer"
    ledger.add_entry(
        agent="SYSTEM", phase="CYCLE-START", role=label,
        content=f"Directive: {task}", meta={"cycle": cycle, "timestamp": utc_now()},
    )

    or_responses = gather_or(tv_seats, task, ledger, label, cycle)
    sr1_received, sr2_received = gather_grades(tv_seats, or_responses, task, ledger, label, cycle)

    # Right-submerge (own OR + right-pass grade) and left-submerge
    # (own OR + left-pass grade), then merge those two into one
    # Triformer-level merge per TV — exactly as specced.
    timer = Timer()

    def get_own_merge(seat):
        sid = seat.seat_id
        right_sub = safe_call(
            seat.agent.comerge, f"RightSubmerge/{sid}",
            or_responses[sid], sr1_received[sid], "", task
        )
        left_sub = safe_call(
            seat.agent.comerge, f"LeftSubmerge/{sid}",
            or_responses[sid], "", sr2_received[sid], task
        )
        own_merge = safe_call(
            seat.agent.comerge, f"OwnTriformerMerge/{sid}",
            right_sub, left_sub, "", task
        )
        return seat, own_merge

    with ThreadPoolExecutor(max_workers=3) as ex:
        own_merge_list = [f.result() for f in [ex.submit(get_own_merge, s) for s in tv_seats]]

    own_merges = {}
    for seat, merge in own_merge_list:
        own_merges[seat.seat_id] = merge
        log_entry(ledger, seat, "TRIFORMER-OWN-MERGE", merge, cycle, {"tier_label": label})
    ledger.add_entry(
        agent="SYSTEM", phase="TIMING", role=label,
        content=f"Right/Left submerge + own-merge time: {timer.elapsed()}s",
        meta={"cycle": cycle},
    )

    return own_merges  # dict: seat_id -> that TV's own Triformer-level merge


# ============================================================
# MAIN
# ============================================================

def run_genone():
    run_timer = Timer()
    print("=== GenOne Bootstrap Starting (CORRECTED ARCHITECTURE) ===")

    ledger = TridentLedger(LEDGER_BASE)
    registry = PrimeRegistry(REGISTRY_PATH)
    admiral_prime_id = register_admiral_prime(registry)

    cycle = ledger.entries[-1].meta.get("cycle", 0) + 1 if ledger.entries else 1

    ledger.add_entry(
        agent="Admiral-Prime", phase="OBSERVE", role="Admiral-Prime",
        content="GenOne run starting.",
        meta={"prime_id": admiral_prime_id, "cycle": cycle, "event": "run_start"},
    )

    triformer = Triformer(name="GenOne-Triformer-Prime")
    print(f"Triformer created: {triformer.name} | Prime ID {triformer.prime_id}")

    triformer_seats, tricore_groups = assign_seats(triformer)
    register_all_seats(registry, triformer_seats, tricore_groups)

    ledger.add_entry(
        agent="SYSTEM", phase="BOOTSTRAP", role="Triformer",
        content=f"Triformer instantiated: {triformer.name} | internal Prime ID {triformer.prime_id}",
        meta={"cycle": cycle},
    )

    triformer_chamber = ChamberSystem("triformer")
    tricore_chambers = [ChamberSystem(label) for label in ["TV1", "TV2", "TV3"]]

    print("\n--- Initial Seat Assignments (PERMANENT — agents do not move) ---")
    all_seats = list(triformer_seats) + [s for group in tricore_groups for s in group]
    for seat in all_seats:
        print(seat)
        ledger.add_entry(
            agent="SYSTEM", phase="SEAT-ASSIGNMENT", role=seat.role,
            content=str(seat),
            meta={"cycle": cycle, "prime_id": seat.prime_id, "seat_id": seat.seat_id},
        )

    task = input("\nEnter task directive (or press Enter for default demo task): ").strip()
    if not task:
        task = "Assess whether a rotating peer-review chamber reduces AI hallucination compared to a single-pass response."

    # --- CONCURRENT: all 3 Tricores + the Triformer own-merge run AT THE SAME TIME ---
    print("\n--- Running Tricores and Triformer concurrently ---")
    concurrent_timer = Timer()
    tricore_labels = ["TV1-Tricore", "TV2-Tricore", "TV3-Tricore"]

    with ThreadPoolExecutor(max_workers=4) as ex:
        tricore_futures = [
            ex.submit(run_tricore_cycle, group, task, ledger, label, cycle)
            for group, label in zip(tricore_groups, tricore_labels)
        ]
        triformer_future = ex.submit(run_triformer_own_merge, triformer_seats, task, ledger, cycle)

        tricore_finals = [f.result() for f in tricore_futures]  # index-aligned with triformer_seats
        triformer_own_merges = triformer_future.result()  # dict seat_id -> merge

    ledger.add_entry(
        agent="SYSTEM", phase="TIMING", role="ALL",
        content=f"Concurrent Tricore + Triformer phase total time: {concurrent_timer.elapsed()}s",
        meta={"cycle": cycle},
    )

    # --- COMBINE STEP: each TV merges its own Triformer merge + its housed Tricore Final ---
    print("\n--- Combining each TV's Triformer merge with its housed Tricore Final (Co Final Prime) ---")
    timer = Timer()
    co_final_primes = {}
    for i, seat in enumerate(triformer_seats):
        sid = seat.seat_id
        own_merge = triformer_own_merges[sid]
        tricore_final = tricore_finals[i]  # tricore_groups[i] is always housed in triformer_seats[i].agent
        co_final = safe_call(
            seat.agent.comerge, f"CoFinalPrime/{sid}",
            own_merge, tricore_final, "", task
        )
        co_final_primes[sid] = co_final
        log_entry(ledger, seat, "CO-FINAL-PRIME", co_final, cycle)
    ledger.add_entry(
        agent="SYSTEM", phase="TIMING", role="Triformer",
        content=f"Co Final Prime combine time: {timer.elapsed()}s", meta={"cycle": cycle},
    )

    # --- R&R merges all 3 Co Final Primes, other 2 TVs vote ---
    print("\n--- R&R merging all Co Final Primes, flank TVs voting ---")
    timer = Timer()
    rr_seat = next((s for s in triformer_seats if s.role == "R&R"), triformer_seats[0])
    flank_tv_seats = [s for s in triformer_seats if s.role != "R&R"]

    final_merge = safe_call(
        rr_seat.agent.subprimal_merge, f"FinalMerge/{rr_seat.seat_id}",
        list(co_final_primes.values()), task
    )
    log_entry(ledger, rr_seat, "FINAL-MERGE", final_merge, cycle)

    for fs in flank_tv_seats:
        v = safe_call(fs.agent.vote, f"FinalVote/{fs.seat_id}", final_merge, task)
        log_entry(ledger, fs, "FINAL-VOTE", v, cycle, {"voted_on": "final_merge"})
    ledger.add_entry(
        agent="SYSTEM", phase="TIMING", role="Triformer",
        content=f"Final merge + vote time: {timer.elapsed()}s", meta={"cycle": cycle},
    )
    ledger.add_entry(
        agent="SYSTEM", phase="PAC-SUBMIT", role="Triformer",
        content="Result sent to Primal Approval Container (PAC) — awaiting human review.",
        meta={"cycle": cycle},
    )

    # --- Rotate roles for next task ---
    print("\n--- Rotating ROLES only (agents stay seated) ---")
    apply_rotation(triformer_seats, triformer_chamber, is_triformer_tier=True)
    for group, chamber in zip(tricore_groups, tricore_chambers):
        apply_rotation(group, chamber, is_triformer_tier=False)

    ledger.add_entry(
        agent="SYSTEM", phase="ROTATION", role="ALL",
        content="Roles rotated (Triformer CCW, Tricores CW — agents did not move)",
        meta={"cycle": cycle},
    )
    for seat in all_seats:
        print(seat)
        ledger.add_entry(
            agent="SYSTEM", phase="SEAT-ASSIGNMENT-POST-ROTATION", role=seat.role,
            content=str(seat),
            meta={"cycle": cycle, "prime_id": seat.prime_id, "seat_id": seat.seat_id},
        )

    ledger.add_entry(
        agent="SYSTEM", phase="RUN-COMPLETE", role="ALL",
        content=f"TOTAL RUN TIME: {run_timer.elapsed()}s", meta={"cycle": cycle},
    )
    ledger.add_entry(
        agent="Admiral-Prime", phase="OBSERVE", role="Admiral-Prime",
        content="GenOne run complete.",
        meta={"prime_id": admiral_prime_id, "cycle": cycle, "event": "run_end"},
    )

    chain_ok, chain_detail = ledger.verify_chain()

    print(f"\nLedger written to: {LEDGER_BASE}.jsonl / {LEDGER_BASE}.md")
    print(f"Chain integrity check: {chain_ok} — {chain_detail}")
    print(f"\n=== FINAL RESULT (pending PAC human review) ===\n{final_merge}")
    print(f"\n=== TOTAL RUN TIME: {run_timer.elapsed()}s ===")
    print("=== GenOne Bootstrap Complete ===")


if __name__ == "__main__":
    run_genone()

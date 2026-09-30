"""
GenOne Bootstrap — JETtrix Chamber Model (CORRECTED ARCHITECTURE)

This is a full rewrite implementing the confirmed real design, which
the previous version did NOT implement correctly:

  - The 3 Tricores (inside TV1/TV2/TV3) and the Triformer-level cycle
    now run CONCURRENTLY, not sequentially, and not as two disconnected
    task cycles on raw task text.
  - Each Tricore completes its own OR -> SR1/SR2 -> CoMerge ->
    Subprimal Merge -> VOTE, producing a "Tricore Final" per TV.
  - Each TV, at the Triformer level, does its own OR -> SR1/SR2 ->
    right-submerge / left-submerge -> its own "Triformer Merge".
  - THE MISSING STEP (now added): each TV combines its own Triformer
    Merge with its own housed Tricore Final into a "Co Final Prime".
  - All 3 Co Final Primes go to the Triformer's R&R TV, who merges
    them into one, passes that copy to the other 2 TVs, who VOTE on
    it. That is the final result -> PAC.

Also fixed: OR generation now uses generate_or() uniformly on both
MTV and TV seats (returns clean text). The previous version called
generate_sr() for OR, which returns a raw data dict on MTV — so MTV
"OR" ledger entries were dict dumps, not readable text.

TIMING: every phase now records elapsed seconds and writes them to
the ledger, so the ledger itself is proof of how long each step took
— not just proof of what was said.

Agents remain permanently seated. Only role bundles rotate, via
chamber.py's ChamberSystem, same as before.
"""

import time
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from triformer.triformer import Triformer
from chamber import ChamberSystem

LEDGER_PATH = Path(r"C:\JETinc\Logs\Trident\ledger_v1.md")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_ledger(lines):
    """Appends immediately — never buffers a whole run in memory."""
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
    lines.clear()


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
# ROLE ROTATION — driven by chamber.py's ChamberSystem
# ============================================================

def apply_rotation(seats, chamber, is_triformer_tier):
    chamber.advance()
    roles = chamber.rotate_triformer() if is_triformer_tier else chamber.rotate_tricore()
    for seat, role in zip(seats, roles):
        seat.role = role
        seat.is_lead = (role == "R&R")


# ============================================================
# SHARED DELIBERATION PRIMITIVES (used by both Tricore and
# Triformer levels — same pattern, different scale)
# ============================================================

def gather_or(seats, task, ledger_lines, label):
    """Each seat produces an Original Response independently."""
    timer = Timer()

    def get_or(seat):
        print(f"  [{label}] OR | {seat.seat_id} ({seat.agent.name}) thinking...")
        text = safe_call(seat.agent.generate_or, f"OR/{seat.seat_id}", task)
        return seat.seat_id, seat.role, seat.agent.name, text

    with ThreadPoolExecutor(max_workers=3) as ex:
        results = [f.result() for f in [ex.submit(get_or, s) for s in seats]]

    or_responses = {}
    for sid, role, aname, text in results:
        or_responses[sid] = text
        ledger_lines.append(f"  - OR | {sid} ({role}) -> {aname}: {text}")
    ledger_lines.append(f"  - [{label}] OR phase time: {timer.elapsed()}s")
    write_ledger(ledger_lines)
    return or_responses


def gather_grades(seats, or_responses, task, ledger_lines, label):
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
        return seat.seat_id, sr1, sr2

    with ThreadPoolExecutor(max_workers=3) as ex:
        results = [f.result() for f in [ex.submit(get_grades, i) for i in range(n)]]

    sr1_received, sr2_received = {}, {}
    for sid, sr1, sr2 in results:
        sr1_received[sid] = sr1
        sr2_received[sid] = sr2
        ledger_lines.append(f"  - SR1 | {sid} grades right neighbor: {sr1}")
        ledger_lines.append(f"  - SR2 | {sid} grades left neighbor: {sr2}")
    ledger_lines.append(f"  - [{label}] Grading phase time: {timer.elapsed()}s")
    write_ledger(ledger_lines)
    return sr1_received, sr2_received


# ============================================================
# TRICORE CYCLE — full cycle, ends in a voted Tricore Final
# ============================================================

def run_tricore_cycle(seats, task, ledger_lines, tier_label):
    ledger_lines.append(f"\n### {tier_label} Task Cycle — {utc_now()}")
    ledger_lines.append(f"- Directive: {task}")
    write_ledger(ledger_lines)

    or_responses = gather_or(seats, task, ledger_lines, tier_label)
    sr1_received, sr2_received = gather_grades(seats, or_responses, task, ledger_lines, tier_label)

    # CoMerge — each MTV combines its own OR + the two grades it received
    timer = Timer()

    def get_comerge(seat):
        return seat.seat_id, safe_call(
            seat.agent.comerge, f"CoMerge/{seat.seat_id}",
            or_responses[seat.seat_id], sr1_received[seat.seat_id], sr2_received[seat.seat_id], task
        )

    with ThreadPoolExecutor(max_workers=3) as ex:
        comerge_results = dict([f.result() for f in [ex.submit(get_comerge, s) for s in seats]])
    for sid, result in comerge_results.items():
        ledger_lines.append(f"  - CoMerge | {sid}: {result}")
    ledger_lines.append(f"  - [{tier_label}] CoMerge phase time: {timer.elapsed()}s")
    write_ledger(ledger_lines)

    # Subprimal Merge — R&R seat only
    timer = Timer()
    rr_seat = next((s for s in seats if s.role == "R&R"), seats[0])
    flank_seats = [s for s in seats if s.role != "R&R"]
    merged = safe_call(
        rr_seat.agent.subprimal_merge, f"SubprimalMerge/{rr_seat.seat_id}",
        list(comerge_results.values()), task
    )
    ledger_lines.append(f"  - Subprimal Merge | {rr_seat.seat_id}: {merged}")
    ledger_lines.append(f"  - [{tier_label}] Subprimal Merge time: {timer.elapsed()}s")
    write_ledger(ledger_lines)

    # Vote — the two flank seats vote on R&R's merge (Tricore-level vote,
    # confirmed as a required step — was missing before this rewrite)
    timer = Timer()
    votes = {}
    for fs in flank_seats:
        v = safe_call(fs.agent.vote, f"Vote/{fs.seat_id}", merged, task)
        votes[fs.seat_id] = v
        ledger_lines.append(f"  - VOTE | {fs.seat_id}: {v}")
    ledger_lines.append(f"  - [{tier_label}] Vote phase time: {timer.elapsed()}s")
    ledger_lines.append(f"  - {tier_label} cycle complete. Tricore Final produced.")
    write_ledger(ledger_lines)

    return merged  # this is the Tricore Final for whichever TV houses this group


# ============================================================
# TRIFORMER OWN-MERGE — OR -> SR -> right/left submerge -> own merge
# (no vote yet — that happens after the Co Final Prime combine)
# ============================================================

def run_triformer_own_merge(tv_seats, task, ledger_lines):
    label = "Triformer"
    ledger_lines.append(f"\n### {label} Task Cycle — {utc_now()}")
    ledger_lines.append(f"- Directive: {task}")
    write_ledger(ledger_lines)

    or_responses = gather_or(tv_seats, task, ledger_lines, label)
    sr1_received, sr2_received = gather_grades(tv_seats, or_responses, task, ledger_lines, label)

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
        return sid, own_merge

    with ThreadPoolExecutor(max_workers=3) as ex:
        own_merges = dict([f.result() for f in [ex.submit(get_own_merge, s) for s in tv_seats]])

    for sid, merge in own_merges.items():
        ledger_lines.append(f"  - Triformer Own-Merge | {sid}: {merge}")
    ledger_lines.append(f"  - [{label}] Right/Left submerge + own-merge time: {timer.elapsed()}s")
    write_ledger(ledger_lines)

    return own_merges  # dict: seat_id -> that TV's own Triformer-level merge


# ============================================================
# MAIN
# ============================================================

def run_genone():
    run_timer = Timer()
    print("=== GenOne Bootstrap Starting (CORRECTED ARCHITECTURE) ===")
    ledger_lines = [f"\n## GenOne Run — {utc_now()} — CORRECTED ARCHITECTURE\n"]

    triformer = Triformer(name="GenOne-Triformer-Prime")
    ledger_lines.append(f"- Triformer instantiated: `{triformer.name}` | Prime ID `{triformer.prime_id}`")
    print(f"Triformer created: {triformer.name} | Prime ID {triformer.prime_id}")

    triformer_seats, tricore_groups = assign_seats(triformer)

    triformer_chamber = ChamberSystem("triformer")
    tricore_chambers = [ChamberSystem(label) for label in ["TV1", "TV2", "TV3"]]

    print("\n--- Initial Seat Assignments (PERMANENT — agents do not move) ---")
    for seat in triformer_seats:
        print(seat)
        ledger_lines.append(f"  - {seat}")
    for group in tricore_groups:
        for seat in group:
            print(seat)
            ledger_lines.append(f"  - {seat}")
    write_ledger(ledger_lines)

    task = input("\nEnter task directive (or press Enter for default demo task): ").strip()
    if not task:
        task = "Assess whether a rotating peer-review chamber reduces AI hallucination compared to a single-pass response."

    # --- CONCURRENT: all 3 Tricores + the Triformer own-merge run AT THE SAME TIME ---
    print("\n--- Running Tricores and Triformer concurrently ---")
    concurrent_timer = Timer()
    tricore_labels = ["TV1-Tricore", "TV2-Tricore", "TV3-Tricore"]

    with ThreadPoolExecutor(max_workers=4) as ex:
        tricore_futures = [
            ex.submit(run_tricore_cycle, group, task, ledger_lines, label)
            for group, label in zip(tricore_groups, tricore_labels)
        ]
        triformer_future = ex.submit(run_triformer_own_merge, triformer_seats, task, ledger_lines)

        tricore_finals = [f.result() for f in tricore_futures]  # index-aligned with triformer_seats
        triformer_own_merges = triformer_future.result()  # dict seat_id -> merge

    ledger_lines.append(f"\n- Concurrent Tricore + Triformer phase total time: {concurrent_timer.elapsed()}s")
    write_ledger(ledger_lines)

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
        ledger_lines.append(f"  - Co Final Prime | {sid}: {co_final}")
    ledger_lines.append(f"  - Co Final Prime combine time: {timer.elapsed()}s")
    write_ledger(ledger_lines)

    # --- R&R merges all 3 Co Final Primes, other 2 TVs vote ---
    print("\n--- R&R merging all Co Final Primes, flank TVs voting ---")
    timer = Timer()
    rr_seat = next((s for s in triformer_seats if s.role == "R&R"), triformer_seats[0])
    flank_tv_seats = [s for s in triformer_seats if s.role != "R&R"]

    final_merge = safe_call(
        rr_seat.agent.subprimal_merge, f"FinalMerge/{rr_seat.seat_id}",
        list(co_final_primes.values()), task
    )
    ledger_lines.append(f"  - FINAL MERGE (R&R {rr_seat.seat_id}): {final_merge}")

    votes = {}
    for fs in flank_tv_seats:
        v = safe_call(fs.agent.vote, f"FinalVote/{fs.seat_id}", final_merge, task)
        votes[fs.seat_id] = v
        ledger_lines.append(f"  - FINAL VOTE | {fs.seat_id}: {v}")
    ledger_lines.append(f"  - Final merge + vote time: {timer.elapsed()}s")
    ledger_lines.append(f"  - Result sent to Primal Approval Container (PAC) — awaiting human review.")
    write_ledger(ledger_lines)

    # --- Rotate roles for next task ---
    print("\n--- Rotating ROLES only (agents stay seated) ---")
    apply_rotation(triformer_seats, triformer_chamber, is_triformer_tier=True)
    for group, chamber in zip(tricore_groups, tricore_chambers):
        apply_rotation(group, chamber, is_triformer_tier=False)

    ledger_lines.append("\n- Roles rotated (Triformer CCW, Tricores CW — agents did not move)")
    for seat in triformer_seats:
        print(seat)
        ledger_lines.append(f"  - {seat}")
    for group in tricore_groups:
        for seat in group:
            print(seat)
            ledger_lines.append(f"  - {seat}")

    ledger_lines.append(f"\n- TOTAL RUN TIME: {run_timer.elapsed()}s")
    write_ledger(ledger_lines)

    print(f"\nLedger written to: {LEDGER_PATH}")
    print(f"\n=== FINAL RESULT (pending PAC human review) ===\n{final_merge}")
    print(f"\n=== TOTAL RUN TIME: {run_timer.elapsed()}s ===")
    print("=== GenOne Bootstrap Complete ===")


if __name__ == "__main__":
    run_genone()
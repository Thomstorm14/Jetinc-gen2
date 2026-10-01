"""
benchmark_harness.py — Tier 2/3 proof harness.

Runs every task in task_bank.json TWO ways on the same real task:
  1. BASELINE — one TV agent, single-pass, no deliberation (reuses the
     same pattern as test_single_tv.py).
  2. DELIBERATED — the full 12-agent concurrent Tricore + Triformer
     cycle (reuses run_tricore_cycle / run_triformer_own_merge straight
     from genone.py — no logic duplicated or reinvented).

Both runs are logged to their own ledger entries (separate benchmark
chain, production untouched) and every result is written to
benchmark_results.json with the ground truth included, so scoring can
happen afterward — either by a person reading both answers next to the
ground truth, or via --auto-score (see caveat below).

WHY SCORING ISN'T FULLY AUTOMATED BY DEFAULT:
The only judge available locally is the same qwen2.5:0.5b model doing
the deliberation. Using it to grade its own family's output is a real
methodology weakness — a small model judging correctness isn't reliable
science, and self-grading bias is a known failure mode. --auto-score is
provided as a rough first pass ONLY. The honest, defensible number comes
from a human (Admiral Prime) reading both answers against the ground
truth and marking CORRECT / PARTIAL / INCORRECT, plus a separate
HALLUCINATED flag for any invented detail not present in the passage.

USAGE:
    python benchmark_harness.py                  # run all 10 tasks, both ways
    python benchmark_harness.py --task-id T03     # just one task
    python benchmark_harness.py --auto-score      # add a rough auto-grade pass
"""

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor

from triformer.triformer import Triformer
from chamber import ChamberSystem
from agents.ledger import TridentLedger
from agents.prime_registry import PrimeRegistry
from agents.triverai.triverai import Triverai
from agents.qwen_client import ask_qwen

from genone import (
    assign_seats,
    register_all_seats,
    register_admiral_prime,
    run_tricore_cycle,
    run_triformer_own_merge,
    safe_call,
    Timer,
    LEDGER_BASE,
    REGISTRY_PATH,
)

BENCH_LEDGER_BASE = LEDGER_BASE.replace("ledger_v1", "ledger_benchmark_v1")
TASK_BANK_PATH = os.path.join(os.path.dirname(__file__), "task_bank.json")
RESULTS_PATH = os.path.join(os.path.dirname(__file__), "benchmark_results.json")


def build_prompt(task):
    return (
        f"{task['passage']}\n\n"
        f"Question: {task['question']}\n\n"
        f"Answer using ONLY the information above. Do not add outside facts."
    )


def run_baseline(prompt, admiral_prime_id, ledger, task_id):
    tv = Triverai(name=f"Benchmark-TV-Baseline-{task_id}")
    timer = Timer()
    answer = tv.generate_or(prompt)
    elapsed = timer.elapsed()
    ledger.add_entry(
        agent=tv.name, phase="BENCHMARK-BASELINE", role="TV-Solo",
        content=answer,
        meta={"prime_id": getattr(tv, "prime_id", None), "task_id": task_id, "elapsed_s": elapsed},
    )
    return answer, elapsed


def run_deliberation(prompt, registry, ledger, task_id):
    triformer = Triformer(name=f"Benchmark-Triformer-{task_id}")
    triformer_seats, tricore_groups = assign_seats(triformer)
    register_all_seats(registry, triformer_seats, tricore_groups)

    tricore_labels = ["TV1-Tricore", "TV2-Tricore", "TV3-Tricore"]
    timer = Timer()

    with ThreadPoolExecutor(max_workers=4) as ex:
        tricore_futures = [
            ex.submit(run_tricore_cycle, group, prompt, ledger, f"{label}-{task_id}", 1)
            for group, label in zip(tricore_groups, tricore_labels)
        ]
        triformer_future = ex.submit(run_triformer_own_merge, triformer_seats, prompt, ledger, 1)
        tricore_finals = [f.result() for f in tricore_futures]
        triformer_own_merges = triformer_future.result()

    co_final_primes = {}
    for i, seat in enumerate(triformer_seats):
        sid = seat.seat_id
        own_merge = triformer_own_merges[sid]
        tricore_final = tricore_finals[i]
        co_final = safe_call(
            seat.agent.comerge, f"CoFinalPrime/{sid}/{task_id}",
            own_merge, tricore_final, "", prompt
        )
        co_final_primes[sid] = co_final
        ledger.add_entry(
            agent=seat.agent.name, phase="BENCHMARK-CO-FINAL-PRIME", role=seat.role,
            content=co_final, meta={"prime_id": seat.prime_id, "task_id": task_id},
        )

    rr_seat = next((s for s in triformer_seats if s.role == "R&R"), triformer_seats[0])
    final_merge = safe_call(
        rr_seat.agent.subprimal_merge, f"FinalMerge/{rr_seat.seat_id}/{task_id}",
        list(co_final_primes.values()), prompt
    )
    elapsed = timer.elapsed()

    ledger.add_entry(
        agent=rr_seat.agent.name, phase="BENCHMARK-FINAL-MERGE", role="R&R",
        content=final_merge,
        meta={"prime_id": rr_seat.prime_id, "task_id": task_id, "elapsed_s": elapsed},
    )
    return final_merge, elapsed


def auto_score(answer, ground_truth, question):
    """Rough, NOT authoritative — see module docstring caveat. Returns the
    raw judge text so a human can still read and override it."""
    prompt = (
        f"QUESTION: {question}\n"
        f"GROUND TRUTH ANSWER: {ground_truth}\n"
        f"AGENT'S ANSWER: {answer}\n\n"
        f"Does the agent's answer match the ground truth? Reply with exactly "
        f"one word — CORRECT, PARTIAL, or INCORRECT — then a short reason."
    )
    try:
        return ask_qwen(prompt, max_tokens=60)
    except RuntimeError as e:
        return f"[AUTO-SCORE ERROR — {e}]"


def main():
    parser = argparse.ArgumentParser(description="Tier 2/3 benchmark: baseline vs full deliberation.")
    parser.add_argument("--task-id", type=str, default=None, help="Run just one task by ID (e.g. T03).")
    parser.add_argument("--auto-score", action="store_true", help="Add a rough auto-grade pass (not authoritative).")
    args = parser.parse_args()

    with open(TASK_BANK_PATH, "r", encoding="utf-8") as f:
        bank = json.load(f)
    tasks = bank["tasks"]
    if args.task_id:
        tasks = [t for t in tasks if t["id"] == args.task_id]
        if not tasks:
            print(f"No task with id {args.task_id} found.")
            return

    ledger = TridentLedger(BENCH_LEDGER_BASE)
    registry = PrimeRegistry(REGISTRY_PATH)
    admiral_prime_id = register_admiral_prime(registry)

    results = []
    if os.path.exists(RESULTS_PATH):
        with open(RESULTS_PATH, "r", encoding="utf-8") as f:
            try:
                results = json.load(f)
            except json.JSONDecodeError:
                results = []

    for task in tasks:
        print(f"\n{'='*60}\nTASK {task['id']} ({task['type']})\n{'='*60}")
        prompt = build_prompt(task)

        print(f"--- Running BASELINE (single TV, no deliberation) ---")
        baseline_answer, baseline_time = run_baseline(prompt, admiral_prime_id, ledger, task["id"])
        print(f"Baseline ({baseline_time}s): {baseline_answer[:200]}")

        print(f"\n--- Running FULL DELIBERATION (12-agent cycle) ---")
        deliberated_answer, deliberated_time = run_deliberation(prompt, registry, ledger, task["id"])
        print(f"Deliberated ({deliberated_time}s): {deliberated_answer[:200]}")

        result = {
            "task_id": task["id"],
            "type": task["type"],
            "question": task["question"],
            "ground_truth": task["ground_truth"],
            "baseline_answer": baseline_answer,
            "baseline_time_s": baseline_time,
            "deliberated_answer": deliberated_answer,
            "deliberated_time_s": deliberated_time,
            "baseline_score": None,       # fill in: CORRECT / PARTIAL / INCORRECT
            "deliberated_score": None,    # fill in: CORRECT / PARTIAL / INCORRECT
            "baseline_hallucinated": None,     # fill in: YES / NO
            "deliberated_hallucinated": None,  # fill in: YES / NO
        }

        if args.auto_score:
            result["baseline_auto_score_ROUGH"] = auto_score(baseline_answer, task["ground_truth"], task["question"])
            result["deliberated_auto_score_ROUGH"] = auto_score(deliberated_answer, task["ground_truth"], task["question"])

        results = [r for r in results if r["task_id"] != task["id"]] + [result]

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    chain_ok, chain_detail = ledger.verify_chain()
    print(f"\n{'='*60}")
    print(f"Chain integrity check: {chain_ok} — {chain_detail}")
    print(f"Results written to: {RESULTS_PATH}")
    print(f"{'='*60}")
    print(
        "\nNEXT STEP: open benchmark_results.json. For each task, read "
        "baseline_answer and deliberated_answer against ground_truth. "
        "Fill in baseline_score / deliberated_score as CORRECT, PARTIAL, "
        "or INCORRECT, and the _hallucinated fields as YES/NO (did the "
        "answer invent any detail not in the passage?). That scored file "
        "is your real Tier 2/3 proof."
    )


if __name__ == "__main__":
    main()

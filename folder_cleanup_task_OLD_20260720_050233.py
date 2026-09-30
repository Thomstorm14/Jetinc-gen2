"""
folder_cleanup_task.py — a real, checkable task with an OBJECTIVE ground
truth: which files in the messy Drive folder are true duplicates.

"True duplicate" is defined by MD5 hash match (byte-for-byte identical
content) — not by name similarity. That ground truth is computed by you,
directly in PowerShell, with zero AI involvement, so there's no
circularity: the answer key is independent of anything GenOne produces.

GenOne only ever sees file NAMES and SIZES (never hashes), and is asked
to guess which files are likely duplicates. This is scored two ways:

  PRECISION — of the files GenOne flagged as duplicates, what fraction
              actually were (per the real hash-based ground truth)?
  RECALL    — of the real duplicate groups that exist, what fraction
              did GenOne correctly find?

This runs the SAME task two ways for direct comparison, same pattern as
benchmark_harness.py:
  1. BASELINE — one TV, single-pass guess
  2. DELIBERATED — one full Tricore (3 MTVs: OR -> grade -> comerge ->
     subprimal merge -> vote), reusing run_tricore_cycle from genone.py

USAGE:
    python folder_cleanup_task.py
"""

import json
import re

from triformer.triformer import Triformer
from agents.ledger import TridentLedger
from agents.prime_registry import PrimeRegistry
from agents.triverai.triverai import Triverai

from genone import (
    assign_seats,
    register_all_seats,
    register_admiral_prime,
    run_tricore_cycle,
    Timer,
    LEDGER_BASE,
    REGISTRY_PATH,
)

GROUND_TRUTH_PATH = "ground_truth_duplicates.json"
FILE_LISTING_PATH = "file_listing.json"
TASK_LEDGER_BASE = LEDGER_BASE.replace("ledger_v1", "ledger_foldertask_v1")


def build_task_prompt(file_listing):
    lines = [f"{f['Name']} ({f['Length']} bytes)" for f in file_listing]
    file_block = "\n".join(lines)
    return (
        f"Here is a list of files in a messy folder, with their sizes:\n\n"
        f"{file_block}\n\n"
        f"Identify groups of files that are LIKELY DUPLICATES of each "
        f"other (same underlying content, possibly saved multiple times "
        f"with different names like 'file (1).py', 'file (2).py'). "
        f"Base your judgment on file name patterns and matching sizes.\n\n"
        f"Respond ONLY in this exact format, one group per line:\n"
        f"GROUP: filename1.ext, filename2.ext, filename3.ext\n\n"
        f"List every group you find this way. Do not include files you "
        f"believe are NOT duplicates of anything."
    )


def parse_groups(answer_text):
    """Extracts GROUP: lines into a list of filename sets."""
    groups = []
    for line in answer_text.splitlines():
        line = line.strip()
        if line.upper().startswith("GROUP:"):
            names_part = line.split(":", 1)[1]
            names = [n.strip() for n in names_part.split(",") if n.strip()]
            names = [re.sub(r"\s*\(\d+\s*bytes?\)\s*$", "", n) for n in names]
            if len(names) >= 2:
                groups.append(set(names))
    return groups


def score_groups(predicted_groups, ground_truth_groups):
    """Precision: of predicted duplicate pairs, how many are real.
    Recall: of real duplicate groups, how many were correctly found
    (a group counts as found if predicted_groups contains a group that
    is a subset of, or matches, the real group with 2+ overlapping files)."""
    gt_sets = [set(g["files"]) for g in ground_truth_groups]

    correct_predictions = 0
    total_predictions = len(predicted_groups)
    for pg in predicted_groups:
        if any(len(pg & gt) >= 2 for gt in gt_sets):
            correct_predictions += 1

    found_gt = 0
    for gt in gt_sets:
        if any(len(pg & gt) >= 2 for pg in predicted_groups):
            found_gt += 1

    precision = correct_predictions / total_predictions if total_predictions else 0.0
    recall = found_gt / len(gt_sets) if gt_sets else 0.0
    return precision, recall, total_predictions, len(gt_sets)


def run_baseline(prompt, ledger):
    tv = Triverai(name="FolderTask-TV-Baseline")
    timer = Timer()
    answer = tv.generate_or(prompt)
    elapsed = timer.elapsed()
    ledger.add_entry(
        agent=tv.name, phase="FOLDERTASK-BASELINE", role="TV-Solo",
        content=answer, meta={"elapsed_s": elapsed},
    )
    return answer, elapsed


def run_deliberated(prompt, registry, ledger):
    triformer = Triformer(name="FolderTask-Triformer")
    triformer_seats, tricore_groups = assign_seats(triformer)
    register_all_seats(registry, triformer_seats, tricore_groups)
    tv1_group = tricore_groups[0]

    timer = Timer()
    result = run_tricore_cycle(tv1_group, prompt, ledger, "FolderTask-Tricore", 1)
    elapsed = timer.elapsed()
    return result, elapsed


def main():
    with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
        ground_truth_groups = json.load(f)
    with open(FILE_LISTING_PATH, "r", encoding="utf-8") as f:
        file_listing = json.load(f)

    print(f"Loaded {len(file_listing)} files, {len(ground_truth_groups)} real duplicate groups (ground truth).")

    ledger = TridentLedger(TASK_LEDGER_BASE)
    registry = PrimeRegistry(REGISTRY_PATH)
    register_admiral_prime(registry)

    prompt = build_task_prompt(file_listing)

    print("\n--- Running BASELINE (single TV) ---")
    baseline_answer, baseline_time = run_baseline(prompt, ledger)
    print(f"Baseline ({baseline_time}s):\n{baseline_answer}\n")

    print("--- Running DELIBERATED (full Tricore: OR -> grade -> comerge -> merge -> vote) ---")
    deliberated_answer, deliberated_time = run_deliberated(prompt, registry, ledger)
    print(f"Deliberated ({deliberated_time}s):\n{deliberated_answer}\n")

    baseline_groups = parse_groups(baseline_answer)
    deliberated_groups = parse_groups(deliberated_answer)

    b_prec, b_rec, b_pred_count, gt_count = score_groups(baseline_groups, ground_truth_groups)
    d_prec, d_rec, d_pred_count, _ = score_groups(deliberated_groups, ground_truth_groups)

    chain_ok, chain_detail = ledger.verify_chain()

    print("=" * 60)
    print(f"REAL DUPLICATE GROUPS (ground truth): {gt_count}")
    print(f"\nBASELINE   — predicted {b_pred_count} groups | precision {b_prec:.0%} | recall {b_rec:.0%}")
    print(f"DELIBERATED — predicted {d_pred_count} groups | precision {d_prec:.0%} | recall {d_rec:.0%}")
    print(f"\nChain integrity check: {chain_ok} — {chain_detail}")
    print("=" * 60)

    results = {
        "ground_truth_group_count": gt_count,
        "baseline": {
            "answer": baseline_answer, "time_s": baseline_time,
            "predicted_groups": [list(g) for g in baseline_groups],
            "precision": b_prec, "recall": b_rec,
        },
        "deliberated": {
            "answer": deliberated_answer, "time_s": deliberated_time,
            "predicted_groups": [list(g) for g in deliberated_groups],
            "precision": d_prec, "recall": d_rec,
        },
    }
    with open("folder_task_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("\nFull results written to: folder_task_results.json")


if __name__ == "__main__":
    main()

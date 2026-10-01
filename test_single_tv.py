"""
test_single_tv.py — isolated single-TV test mode.

Runs ONE Triverai (TV) agent by itself, with NO Tricore chamber.
This is the baseline: single multi-MTV agent, single-pass OR -> PAC.

Reuses shared infrastructure from genone.py:
- PrimeRegistry / register_system_roles()
- TridentLedger (same base path logic)
- Timer

Writes to a SEPARATE ledger chain (ledger_tv_test_v1.jsonl/.md) so
baseline runs don't mix into the main Trident Ledger. Use --main-ledger
if you specifically want a TV-only run recorded in the production chain.
"""

import argparse

from agents.ledger import TridentLedger
from agents.prime_registry import PrimeRegistry
from agents.triverai.triverai import Triverai

from genone import (
    register_system_roles,
    Timer,
    LEDGER_BASE,
    REGISTRY_PATH,
)


TV_TEST_LEDGER_BASE = LEDGER_BASE.replace("ledger_v1", "ledger_tv_test_v1")


def run_tv_solo(tv_name: str, task: str, ledger: TridentLedger, admiral_prime_id: str):
    """
    Baseline TV-only run:
    - instantiate one Triverai
    - generate OR
    - log to ledger
    - return result + elapsed time
    """
    tv = Triverai(name=tv_name)

    ledger.add_entry(
        agent="Admiral-Prime",
        phase="OBSERVE",
        role="Admiral-Prime",
        content=f"TV-solo test starting: {tv_name} only.",
        meta={
            "prime_id": admiral_prime_id,
            "mode": "tv_solo",
            "tv_name": tv_name,
        },
    )

    run_timer = Timer()
    print(f"\n--- Running TV-solo baseline for {tv_name} ---")
    or_text = tv.generate_or(task)
    elapsed = run_timer.elapsed()

    ledger.add_entry(
        agent=tv_name,
        phase="OR",
        role="TV-Solo",
        content=f"TV OR output:\n{or_text}",
        meta={
            "prime_id": tv.prime_id,
            "mode": "tv_solo",
            "task": task,
            "elapsed_s": elapsed,
        },
    )

    ledger.add_entry(
        agent="Admiral-Prime",
        phase="OBSERVE",
        role="Admiral-Prime",
        content=f"TV-solo test complete: {tv_name} only. Elapsed: {elapsed}s.",
        meta={
            "prime_id": admiral_prime_id,
            "mode": "tv_solo",
            "tv_name": tv_name,
        },
    )

    return or_text, elapsed


def main():
    parser = argparse.ArgumentParser(description="Isolated single-TV baseline test run.")
    parser.add_argument(
        "--tv-name",
        type=str,
        default="TV1-Solo-Baseline",
        help="Name for the TV agent. Default: TV1-Solo-Baseline.",
    )
    parser.add_argument(
        "--task",
        type=str,
        default=None,
        help="Task directive. If omitted, you'll be prompted (Enter for default demo task).",
    )
    parser.add_argument(
        "--main-ledger",
        action="store_true",
        help=(
            "Write to the PRODUCTION ledger_v1 chain instead of the separate TV test chain. "
            "Only use this if the run should count as a real logged cycle."
        ),
    )
    args = parser.parse_args()

    ledger_base = LEDGER_BASE if args.main_ledger else TV_TEST_LEDGER_BASE
    ledger = TridentLedger(ledger_base)
    registry = PrimeRegistry(REGISTRY_PATH)

    # Correct function from your real genone.py
    ss_prime_id, admiral_prime_id = register_system_roles(registry)

    print(f"=== Isolated TV-Solo Test — {args.tv_name} ===")
    print(f"Ledger: {ledger_base}.jsonl / {ledger_base}.md")
    if not args.main_ledger:
        print("(separate TV TEST chain — production ledger_v1 is untouched)")

    task = args.task
    if task is None:
        task = input("\nEnter task directive (or press Enter for default demo task): ").strip()
    if not task:
        task = "Assess whether a rotating peer-review chamber reduces AI hallucination compared to a single-pass response."

    result, elapsed = run_tv_solo(args.tv_name, task, ledger, admiral_prime_id)

    chain_ok, chain_detail = ledger.verify_chain()

    print(f"\n=== TV-SOLO FINAL ({args.tv_name}) ===\n{result}")
    print(f"\nChain integrity check: {chain_ok} — {chain_detail}")
    print(f"=== TOTAL TV-SOLO TEST RUN TIME: {elapsed}s ===")


if __name__ == "__main__":
    main()

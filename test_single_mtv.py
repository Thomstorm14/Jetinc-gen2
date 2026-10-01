"""
test_single_mtv.py — isolated single-MTV test mode.
"""
import argparse
from agents.ledger import TridentLedger
from agents.prime_registry import PrimeRegistry
# Correct import for your actual folder layout
from mtv import MTV
from genone import (
    register_admiral_prime,
    Timer,
    LEDGER_BASE,
    REGISTRY_PATH,
)
MTV_TEST_LEDGER_BASE = LEDGER_BASE.replace("ledger_v1", "ledger_mtv_test_v1")
def run_mtv_solo(mtv_name: str, task: str, ledger: TridentLedger, admiral_prime_id: str):
    """
    Baseline MTV-only run.
    """
    # MTV requires a perspective argument — we give a safe default
    mtv = MTV(name=mtv_name, perspective="baseline")
    ledger.add_entry(
        agent="Admiral-Prime",
        phase="OBSERVE",
        role="Admiral-Prime",
        content=f"MTV-solo test starting: {mtv_name} only.",
        meta={
            "prime_id": admiral_prime_id,
            "mode": "mtv_solo",
            "mtv_name": mtv_name,
        },
    )
    run_timer = Timer()
    print(f"\n--- Running MTV-solo baseline for {mtv_name} ---")
    or_text = mtv.generate_or(task)
    elapsed = run_timer.elapsed()
    ledger.add_entry(
        agent=mtv_name,
        phase="OR",
        role="MTV-Solo",
        content=f"MTV OR output:\n{or_text}",
        meta={
            "prime_id": mtv.prime_id,
            "mode": "mtv_solo",
            "task": task,
            "elapsed_s": elapsed,
        },
    )
    ledger.add_entry(
        agent="Admiral-Prime",
        phase="OBSERVE",
        role="Admiral-Prime",
        content=f"MTV-solo test complete: {mtv_name} only. Elapsed: {elapsed}s.",
        meta={
            "prime_id": admiral_prime_id,
            "mode": "mtv_solo",
            "mtv_name": mtv_name,
        },
    )
    return or_text, elapsed
def main():
    parser = argparse.ArgumentParser(description="Isolated single-MTV baseline test run.")
    parser.add_argument(
        "--mtv-name",
        type=str,
        default="MTV1-Solo-Baseline",
        help="Name for the MTV agent.",
    )
    parser.add_argument(
        "--task",
        type=str,
        default=None,
        help="Task directive.",
    )
    parser.add_argument(
        "--main-ledger",
        action="store_true",
        help="Write to production ledger instead of MTV test chain.",
    )
    args = parser.parse_args()
    ledger_base = LEDGER_BASE if args.main_ledger else MTV_TEST_LEDGER_BASE
    ledger = TridentLedger(ledger_base)
    registry = PrimeRegistry(REGISTRY_PATH)
    admiral_prime_id = register_admiral_prime(registry)
    print(f"=== Isolated MTV-Solo Test — {args.mtv_name} ===")
    print(f"Ledger: {ledger_base}.jsonl / {ledger_base}.md")
    if not args.main_ledger:
        print("(separate MTV TEST chain — production ledger_v1 is untouched)")
    task = args.task
    if task is None:
        task = input("\nEnter task directive (or press Enter for default demo task): ").strip()
    if not task:
        task = "Assess whether a rotating peer-review chamber reduces AI hallucination compared to a single-pass response."
    result, elapsed = run_mtv_solo(args.mtv_name, task, ledger, admiral_prime_id)
    chain_ok, chain_detail = ledger.verify_chain()
    print(f"\n=== MTV-SOLO FINAL ({args.mtv_name}) ===\n{result}")
    print(f"\nChain integrity check: {chain_ok} — {chain_detail}")
    print(f"=== TOTAL MTV-SOLO TEST RUN TIME: {elapsed}s ===")
if __name__ == "__main__":
    main()

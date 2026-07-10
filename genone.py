"""
JETinc - GenOne Bootstrap
The origin workstack. Instantiates one Triformer (which internally creates
3 TVs x 3 MTVs = 12 agents), assigns each agent its elemental identity and
Prime ID, then steps the workstack through the build sequence, writing each
step to the Trident Ledger.
"""
import time
from datetime import datetime, timezone
from pathlib import Path
from triformer.triformer import Triformer

# ============================================================
# CANON - 12 elemental identities
# ============================================================
ELEMENTAL_IDENTITIES = [
    "Scribe", "Archivist", "Coder", "Logician", 
    "Strategist", "Operator", "Builder", "Engineer", 
    "Integrator", "Governance", "Legal", "Planner"
]

# ============================================================
# CANON - 12-step build sequence
# ============================================================
BUILD_SEQUENCE = [
    ("Step 1", "Initialize Registry"),
    ("Step 2", "Validate Prime IDs"),
    ("Step 3", "Allocate Agent Memory"),
    ("Step 4", "Establish Transport Layer"),
    ("Step 5", "Sync Codex Registry"),
    ("Step 6", "Verify Triformer Integrity"),
    ("Step 7", "Handshake Protocol Initiation"),
    ("Step 8", "Prime Core Synchronization"),
    ("Step 9", "Activate Logic Gate A"),
    ("Step 10", "Activate Logic Gate B"),
    ("Step 11", "System Stability Check"),
    ("Step 12", "JETINC IS LIVE")
]

LEDGER_PATH = Path(r"C:\JETinc\Logs\Trident\ledger_v1.md")

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def assign_identities(triformer):
    ordered_agents = []
    for tv in (triformer.tv1, triformer.tv2, triformer.tv3):
        ordered_agents.append(tv)
        ordered_agents.extend([tv.mtv1, tv.mtv2, tv.mtv3])

    assignments = []
    for agent, identity in zip(ordered_agents, ELEMENTAL_IDENTITIES):
        agent.elemental_identity = identity
        assignments.append({
            "agent_name": agent.name,
            "prime_id": agent.prime_id,
            "elemental_identity": identity
        })
    return assignments

def write_ledger(lines):
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

def run_genone():
    print("=== GenOne Bootstrap Starting ===")
    ledger_lines = [f"\n## GenOne Run - {utc_now()}\n"]

    triformer = Triformer(name="GenOne-Triformer-Prime")
    ledger_lines.append(f"- Triformer instantiated: `{triformer.name}` | Prime ID `{triformer.prime_id}`")
    print(f"Triformer created: {triformer.name} | Prime ID {triformer.prime_id}")

    assignments = assign_identities(triformer)
    ledger_lines.append(f"- 12 agents assigned elemental identities:")
    for a in assignments:
        line = f"  - `{a['agent_name']}` (Prime ID `{a['prime_id']}`) -> {a['elemental_identity']}"
        ledger_lines.append(line)
        print(line)

    print("\n--- Running 12-step build sequence ---")
    for step_id, description in BUILD_SEQUENCE:
        line = f"{step_id} - {description}"
        ledger_lines.append(f"- {line}")
        print(line)
        time.sleep(0.05)

    write_ledger(ledger_lines)
    print(f"\nLedger written to: {LEDGER_PATH}")
    print("=== GenOne Bootstrap Complete ===")

if __name__ == "__main__":
    run_genone()
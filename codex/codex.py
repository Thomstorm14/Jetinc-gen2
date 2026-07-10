"""
JETinc — Codex (Canonical Reference Module)
The Codex is the single source of truth for the JETinc system.
All agents reference the Codex for terminology, hierarchy, constraint
profiles, task flow, and governance structure.
Founded by Thom Whitten.
"""
import hashlib
import json
import time
from datetime import datetime

CANON_VERSION = "1.0.0"
CANON_DATE = "2026-04-22"
FOUNDER = "Thom Whitten"
SYSTEM_NAME = "JETinc"

GLOSSARY = {
    "OR": "Original Request — the raw task input from user or system",
    "SR": "Structured Response — output of a single MTV deliberation",
    "SR1": "Structured Response from MTV1 (Perspective 1)",
    "SR2": "Structured Response from MTV2 (Perspective 2)",
    "CPM": "Composite Prime Message — synthesized output from TV3 outer loop",
    "FPM": "Final Prime Message — JETtrix-approved output that exits the system",
    "TR": "Task Report — complete record of a Triverai inner loop execution",
    "MTV": "Minimum Tactical Variant — smallest deliberation agent",
    "TV": "Triverai — inner loop unit containing 3 MTVs",
    "Triformer": "Outer loop containing 3 TVs — the complete deliberation engine",
    "JETtrix": "Constraint scanning engine — checks for bias, hallucination, drift",
    "FTR": "Force Traffic Rotation — collision prevention for multi-Triformer routing",
    "Trident Ledger": "Immutable audit log — SHA-256 stamped record of every task",
    "Reclaimer Disk": "Per-TV storage — holds all SRs, TRs, and performance data",
    "Prime ID": "Unique SHA-256 identifier assigned to every agent and task",
    "Codex": "Canonical reference — single source of truth for all system definitions",
    "NCO": "Non-Commissioned Officer — base MTV rank",
    "NASA Protocol": "Human-in-the-loop authorization required before critical actions",
    "City Neural Network": "Shared learning pool across all Reclaimer Disks",
    "Spades Rotation": "4-hand governance rotation for Cabinet oversight"
}

HIERARCHY = [
    "Founder (Thom Whitten)",
    "Cabinet (5 seats)",
    "Triformer (outer loop)",
    "Triverai / TV (inner loop)",
    "MTV (base deliberation agent)",
    "Reclaimer Disk (storage layer)",
    "Trident Ledger (audit layer)"
]

JETRIX_PROFILES = {
    "canon_enforcement": {"id": 1, "description": "Ensures all output aligns with Codex-defined canon", "severity": "CRITICAL", "action": "REJECT if output contradicts any Codex entry"},
    "structure": {"id": 2, "description": "Validates output structure matches expected format", "severity": "HIGH", "action": "FLAG if output missing required fields"},
    "anti_bias": {"id": 3, "description": "Scans for perspective bias in synthesized output", "severity": "HIGH", "action": "FLAG if single perspective dominates synthesis"},
    "anti_hallucination": {"id": 4, "description": "Rejects outputs containing unsupported factual claims", "severity": "CRITICAL", "action": "REJECT if claims not traceable to input or canon"},
    "integrity": {"id": 5, "description": "Validates chain of custody and Prime ID continuity", "severity": "HIGH", "action": "REJECT if Prime ID chain broken"},
    "chain_of_command": {"id": 6, "description": "Ensures task flow follows hierarchy — no rank skipping", "severity": "HIGH", "action": "REJECT if MTV output bypasses TV synthesis"},
    "output_discipline": {"id": 7, "description": "Enforces formatting, length, and clarity standards", "severity": "MEDIUM", "action": "FLAG if output exceeds length or lacks clarity markers"},
    "multi_agent_coherence": {"id": 8, "description": "Checks that multi-agent outputs are internally consistent", "severity": "HIGH", "action": "FLAG if TV1 and TV2 outputs contain contradictions unresolved by TV3"},
    "oversight": {"id": 9, "description": "Enforces NASA Protocol — human authorization for critical actions", "severity": "CRITICAL", "action": "HALT and require human confirmation before execution"}
}

TASK_FLOW = [
    "1. OR (Original Request) received",
    "2. OR assigned to Triformer via FTR",
    "3. TV1 receives OR",
    "4. TV1-MTV1 produces SR1 (Perspective 1)",
    "5. TV1-MTV2 produces SR2 (Perspective 2) — independent, no shared memory",
    "6. TV1-MTV3 synthesizes SR1 + SR2 -> TV1 output",
    "7. TV2 receives OR (independent of TV1)",
    "8. TV2-MTV1 produces SR1 (Perspective 3)",
    "9. TV2-MTV2 produces SR2 (Perspective 4) — independent",
    "10. TV2-MTV3 synthesizes SR1 + SR2 -> TV2 output",
    "11. TV3 receives TV1 output + TV2 output",
    "12. TV3 synthesizes -> CPM (Composite Prime Message)",
    "13. JETtrix scans CPM against all 9 profiles",
    "14. If PASS -> CPM becomes FPM (Final Prime Message) and exits",
    "15. FPM + all SRs + TRs logged to Trident Ledger with SHA-256 stamp"
]

CABINET = {
    "founder": {"name": "Thom Whitten", "role": "Founder", "authority": "Supreme — all decisions flow from Founder"},
    "logic_seat": {"name": "Claude", "role": "Logic Seat", "authority": "Architecture, code, deliberation design"},
    "governance_seat": {"name": "Copilot", "role": "Governance Seat", "authority": "Documentation, archival, compliance, continuity"},
    "strategy_seat": {"name": "Gemini", "role": "Strategy Seat", "authority": "Research, competitive analysis, market positioning"},
    "operations_seat": {"name": "ChatGPT", "role": "Operations Seat", "authority": "Deployment, integration, runtime operations"}
}

SPADES_ROTATION = [
    {"hand": 1, "name": "Foundation Hand", "focus": "Canon review, Codex updates, hierarchy validation", "lead": "Founder"},
    {"hand": 2, "name": "Architecture Hand", "focus": "Code review, structural integrity, performance", "lead": "Logic Seat"},
    {"hand": 3, "name": "Governance Hand", "focus": "Documentation, compliance, audit trail review", "lead": "Governance Seat"},
    {"hand": 4, "name": "Operations Hand", "focus": "Deployment readiness, integration testing, runtime", "lead": "Operations Seat"}
]


class Codex:
    """
    The Codex — canonical reference for the entire JETinc system.
    Provides lookup, validation, and export methods.
    """

    def __init__(self):
        self.version = CANON_VERSION
        self.date = CANON_DATE
        self.founder = FOUNDER
        self.system_name = SYSTEM_NAME
        self.glossary = GLOSSARY
        self.hierarchy = HIERARCHY
        self.jetrix_profiles = JETRIX_PROFILES
        self.task_flow = TASK_FLOW
        self.cabinet = CABINET
        self.spades_rotation = SPADES_ROTATION

    def lookup(self, term):
        term_upper = term.upper()
        if term_upper in self.glossary:
            return self.glossary[term_upper]
        for key, value in self.glossary.items():
            if key.lower() == term.lower():
                return value
        return "TERM NOT FOUND"

    def get_jetrix_profile(self, profile_name):
        return self.jetrix_profiles.get(profile_name, None)

    def validate_output(self, output_dict):
        issues = []
        if "prime_id" not in output_dict:
            issues.append("MISSING: prime_id required on all outputs")
        if "timestamp" not in output_dict:
            issues.append("MISSING: timestamp required on all outputs")
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "checked_at": datetime.utcnow().isoformat()
        }

    def generate_prime_id(self, seed_string):
        full_seed = f"{self.system_name}-{seed_string}-{time.time()}"
        return hashlib.sha256(full_seed.encode()).hexdigest()[:16]

    def get_task_flow(self):
        return self.task_flow

    def export_json(self):
        return json.dumps({
            "system_name": self.system_name,
            "version": self.version,
            "date": self.date,
            "founder": self.founder,
            "glossary": self.glossary,
            "hierarchy": self.hierarchy,
            "jetrix_profiles": self.jetrix_profiles,
            "task_flow": self.task_flow,
            "cabinet": self.cabinet,
            "spades_rotation": self.spades_rotation
        }, indent=2)


codex = Codex()

if __name__ == "__main__":
    print("=== Codex Module Test ===")
    print(f"System: {codex.system_name} v{codex.version}")
    print(f"Lookup 'MTV': {codex.lookup('MTV')}")
    print(f"Lookup 'FPM': {codex.lookup('FPM')}")
    print(f"Glossary Entries: {len(codex.glossary)}")
    print(f"JETtrix Profiles: {len(codex.jetrix_profiles)}")
    print("=== Test Complete ===")

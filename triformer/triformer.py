"""
JETinc — Triformer (Outer Loop)
The complete deliberation engine.
Contains 3 Triverai (TV) units + JETtrix constraint scanner.
Produces the Final Prime Message (FPM).
"""
import hashlib
import time
from datetime import datetime
from agents.triverai.triverai import Triverai

JETRIX_PROFILES = {
    "canon_enforcement": {
        "description": "Ensures output aligns with Codex canon",
        "severity": "CRITICAL"
    },
    "anti_bias": {
        "description": "Scans for perspective bias in synthesis",
        "severity": "HIGH"
    },
    "anti_hallucination": {
        "description": "Rejects unsupported factual claims",
        "severity": "CRITICAL"
    },
    "integrity": {
        "description": "Validates chain of custody and audit trail",
        "severity": "HIGH"
    },
    "output_discipline": {
        "description": "Enforces format and structure standards",
        "severity": "MEDIUM"
    }
}


class Triformer:
    """
    Triformer — outer deliberation loop.
    Runs 3 TVs, synthesizes via TV3, scans via JETtrix,
    and produces the Final Prime Message (FPM).
    """

    def __init__(self, name="Triformer-Prime"):
        """
        Initialize the Triformer with 3 Triverai units.

        Args:
            name (str): Triformer designation
        """
        self.name = name
        self.prime_id = self._generate_prime_id()
        self.created_at = datetime.utcnow().isoformat()
        self.tasks_completed = 0
        self.trident_ledger = []

        self.tv1 = Triverai("TV1", ["analytical", "critical", "synthesis"])
        self.tv2 = Triverai("TV2", ["strategic", "ethical", "synthesis"])
        self.tv3 = Triverai("TV3", ["integrative", "adversarial", "synthesis"])
        self.ftr_index = 0

    def _generate_prime_id(self):
        """Generate unique Prime ID using SHA-256."""
        seed = f"TRIFORMER-{self.name}-{time.time()}"
        return hashlib.sha256(seed.encode()).hexdigest()[:16]

    def jetrix_scan(self, cpm):
        """
        Run JETtrix constraint scan on Composite Prime Message.

        Args:
            cpm (dict): The synthesized output from TV3

        Returns:
            dict: Scan result with pass/fail and any violations
        """
        violations = []
        for profile_name, profile in JETRIX_PROFILES.items():
            passed = self._run_profile_check(profile_name, cpm)
            if not passed:
                violations.append({
                    "profile": profile_name,
                    "severity": profile["severity"],
                    "description": profile["description"]
                })
        return {
            "passed": len(violations) == 0,
            "violations": violations,
            "profiles_checked": len(JETRIX_PROFILES),
            "timestamp": datetime.utcnow().isoformat()
        }

    def _run_profile_check(self, profile_name, cpm):
        """
        Execute a single JETtrix profile check.
        Override with real validation logic per profile.
        """
        return True

    def process_or(self, task):
        """
        Process an Original Request (OR) through the full Triformer pipeline.
        1. TV1 runs inner loop -> TR1
        2. TV2 runs inner loop -> TR2 (independent)
        3. TV3 synthesizes TR1 + TR2 -> CPM
        4. JETtrix scans CPM
        5. If clean -> FPM exits
        6. Everything logged to Trident Ledger

        Args:
            task (str): Original Request

        Returns:
            dict: Final Prime Message (FPM) or rejection
        """
        start_time = time.time()

        tr1 = self.tv1.generate_tr(task)
        tr2 = self.tv2.generate_tr(task)

        synthesis_task = (
            f"SYNTHESIZE OUTER LOOP:\n"
            f"TV1 Output: {tr1['synthesis']['analysis']}\n"
            f"TV2 Output: {tr2['synthesis']['analysis']}"
        )
        cpm = self.tv3.generate_tr(synthesis_task)

        scan_result = self.jetrix_scan(cpm)

        fpm = {
            "triformer": self.name,
            "prime_id": self.prime_id,
            "task": task,
            "tr1": tr1,
            "tr2": tr2,
            "cpm": cpm,
            "jetrix_scan": scan_result,
            "status": "APPROVED" if scan_result["passed"] else "REJECTED",
            "timestamp": datetime.utcnow().isoformat(),
            "total_time": round(time.time() - start_time, 4)
        }

        ledger_entry = {
            "task_hash": hashlib.sha256(task.encode()).hexdigest(),
            "fpm_status": fpm["status"],
            "timestamp": fpm["timestamp"],
            "total_time": fpm["total_time"]
        }
        self.trident_ledger.append(ledger_entry)
        self.tasks_completed += 1

        self.force_traffic_rotation()

        return fpm

    def generate_tr(self, task):
        """Public interface — process OR and return FPM."""
        return self.process_or(task)

    def force_traffic_rotation(self):
        """
        Rotate lead agents across all TVs to prevent collision.
        Called automatically after each task.
        """
        self.tv1.rotate_lead()
        self.tv2.rotate_lead()
        self.tv3.rotate_lead()
        self.ftr_index += 1

    def get_status(self):
        """Return full Triformer status."""
        return {
            "name": self.name,
            "prime_id": self.prime_id,
            "tasks_completed": self.tasks_completed,
            "ftr_index": self.ftr_index,
            "created_at": self.created_at,
            "ledger_entries": len(self.trident_ledger),
            "tv1": self.tv1.get_status(),
            "tv2": self.tv2.get_status(),
            "tv3": self.tv3.get_status()
        }


if __name__ == "__main__":
    print("=== Triformer Full Pipeline Test ===")
    triformer = Triformer(name="Triformer-Prime")
    print(f"Created: {triformer.name} | Prime ID: {triformer.prime_id}")
    fpm = triformer.process_or("Evaluate risk of deploying new ATC routing algorithm")
    print("\nFPM Output:")
    print(f"  Status: {fpm['status']}")
    print(f"  JETtrix Passed: {fpm['jetrix_scan']['passed']}")
    print(f"  Profiles Checked: {fpm['jetrix_scan']['profiles_checked']}")
    print(f"  Total Time: {fpm['total_time']}s")
    print(f"  Ledger Entries: {len(triformer.trident_ledger)}")
    status = triformer.get_status()
    print("\nTriformer Status:")
    print(f"  Tasks: {status['tasks_completed']}")
    print(f"  FTR Index: {status['ftr_index']}")
    print("=== Test Complete ===")

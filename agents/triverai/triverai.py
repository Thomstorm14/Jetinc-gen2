"""
JETinc — Triverai (TV) Agent
Inner loop of the Triformer system.
Each Triverai contains 3 MTVs and produces a Task Report (TR).
"""
import hashlib
import time
from datetime import datetime
from agents.mtv.mtv import MTV


class Triverai:
    """
    Triverai (TV) — inner deliberation loop.
    Contains 3 MTVs that analyze a task from different perspectives.
    MTV3 synthesizes SR1 + SR2 into a unified TV output.
    """

    def __init__(self, name, perspectives=None):
        """
        Initialize a Triverai with 3 MTVs.

        Args:
            name (str): TV designation (e.g., "TV1")
            perspectives (list): 3 perspective strings for MTVs.
                Defaults to ["analytical", "critical", "synthesis"]
        """
        self.name = name
        self.prime_id = self._generate_prime_id()
        self.created_at = datetime.utcnow().isoformat()
        self.tasks_completed = 0
        self.reclaimer_disk = []

        if perspectives is None:
            perspectives = ["analytical", "critical", "synthesis"]

        self.mtv1 = MTV(f"{name}-MTV1", perspectives[0], tv_parent=name)
        self.mtv2 = MTV(f"{name}-MTV2", perspectives[1], tv_parent=name)
        self.mtv3 = MTV(f"{name}-MTV3", perspectives[2], tv_parent=name)
        self.lead = self.mtv1

    def _generate_prime_id(self):
        """Generate unique Prime ID using SHA-256."""
        seed = f"TV-{self.name}-{time.time()}"
        return hashlib.sha256(seed.encode()).hexdigest()[:16]

    def run_inner_loop(self, task):
        """
        Execute the full inner loop on a task.
        1. MTV1 produces SR1
        2. MTV2 produces SR2 (independent — no access to SR1)
        3. MTV3 synthesizes SR1 + SR2 into TV output

        Args:
            task (str): The Original Request (OR)

        Returns:
            dict: Task Report (TR) with all SRs and synthesis
        """
        start_time = time.time()
        sr1 = self.mtv1.generate_sr(task)
        sr2 = self.mtv2.generate_sr(task)
        synthesis_input = f"SYNTHESIZE:\nSR1: {sr1['analysis']}\nSR2: {sr2['analysis']}"
        sr3 = self.mtv3.generate_sr(synthesis_input)

        tr = {
            "tv_name": self.name,
            "prime_id": self.prime_id,
            "task": task,
            "sr1": sr1,
            "sr2": sr2,
            "synthesis": sr3,
            "lead_agent": self.lead.name,
            "timestamp": datetime.utcnow().isoformat(),
            "loop_time": round(time.time() - start_time, 4)
        }
        self.reclaimer_disk.append(tr)
        self.tasks_completed += 1

        self.mtv1.rank_up()
        self.mtv2.rank_up()
        self.mtv3.rank_up()

        return tr

    def generate_tr(self, task):
        """Public interface — alias for run_inner_loop(). Returns Task Report."""
        return self.run_inner_loop(task)

    def rotate_lead(self):
        """Rotate lead MTV for next task (prevents bias)."""
        rotation = [self.mtv1, self.mtv2, self.mtv3]
        current_index = rotation.index(self.lead)
        self.lead = rotation[(current_index + 1) % 3]
        return self.lead.name

    def get_status(self):
        """Return current TV status including all MTV statuses."""
        return {
            "name": self.name,
            "prime_id": self.prime_id,
            "tasks_completed": self.tasks_completed,
            "lead_agent": self.lead.name,
            "created_at": self.created_at,
            "mtv1": self.mtv1.get_status(),
            "mtv2": self.mtv2.get_status(),
            "mtv3": self.mtv3.get_status(),
            "reclaimer_entries": len(self.reclaimer_disk)
        }


if __name__ == "__main__":
    print("=== Triverai (TV) Test ===")
    tv = Triverai(name="TV1", perspectives=["risk", "ethics", "synthesis"])
    print(f"Created: {tv.name} | Prime ID: {tv.prime_id}")
    tr = tv.generate_tr("Should we approve the new routing algorithm for ATC?")
    print("\nTask Report:")
    print(f"  TV: {tr['tv_name']}")
    print(f"  Lead: {tr['lead_agent']}")
    print(f"  Loop Time: {tr['loop_time']}s")
    print(f"  SR1 Perspective: {tr['sr1']['perspective']}")
    print(f"  SR2 Perspective: {tr['sr2']['perspective']}")
    new_lead = tv.rotate_lead()
    print(f"\nRotated lead to: {new_lead}")
    print(f"Status: {tv.get_status()['name']} — {tv.tasks_completed} tasks")
    print("=== Test Complete ===")

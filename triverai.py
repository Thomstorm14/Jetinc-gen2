"""
JETinc — Triverai (TV) Agent
Inner loop of the Triformer system.
Each Triverai contains 3 MTVs.

PATCHED: added chamber-level pass-through methods (generate_or, grade,
comerge, subprimal_merge, vote) so a TV can act as a single seat in the
Triformer-level chamber cycle, same interface as an MTV seat. These
delegate to the TV's current lead MTV. The original run_inner_loop /
generate_tr (3-step SR1/SR2/synthesis) is preserved and untouched for
any internal-report use separate from the chamber cycle.
"""
import hashlib
import time
from datetime import datetime
from agents.mtv.mtv import MTV


class Triverai:
    def __init__(self, name, perspectives=None):
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
        seed = f"TV-{self.name}-{time.time()}"
        return hashlib.sha256(seed.encode()).hexdigest()[:16]

    # ---- Chamber-level pass-through (Triformer tier uses these) ----

    def generate_or(self, task):
        """Original Response for this TV seat — delegates to lead MTV."""
        sr = self.lead.generate_sr(task)
        return sr["analysis"]["assessment"]

    def generate_sr(self, task):
        """Structured Response for this TV seat — runs full inner loop."""
        return self.run_inner_loop(task)

    def grade(self, peer_name, peer_response, task):
        return self.lead.grade(peer_name, peer_response, task)

    def comerge(self, own_or, sr1_feedback, sr2_feedback, task):
        return self.lead.comerge(own_or, sr1_feedback, sr2_feedback, task)

    def subprimal_merge(self, comerged_responses, task):
        return self.lead.subprimal_merge(comerged_responses, task)

    def vote(self, final_merge, task):
        return self.lead.vote(final_merge, task)

    # ---- Original inner-loop report (unchanged, still available) ----

    def run_inner_loop(self, task):
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
        return self.run_inner_loop(task)

    def rotate_lead(self):
        rotation = [self.mtv1, self.mtv2, self.mtv3]
        current_index = rotation.index(self.lead)
        self.lead = rotation[(current_index + 1) % 3]
        return self.lead.name

    def get_status(self):
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
    print(f"  Lead: {tr['lead_agent']}  Loop Time: {tr['loop_time']}s")
    print("=== Test Complete ===")

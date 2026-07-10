"""
JETinc — MTV (Minimum Tactical Variant) Agent
The smallest deliberation unit in the Triverai system.
Each MTV produces a Structured Response (SR) for its assigned perspective.
"""
import hashlib
import time
from datetime import datetime


class MTV:
    """
    Minimum Tactical Variant — base deliberation agent.
    Each MTV analyzes a task from one assigned perspective and produces
    a Structured Response (SR).
    """

    def __init__(self, name, perspective, tv_parent=None):
        """
        Initialize an MTV agent.

        Args:
            name (str): Agent designation (e.g., "MTV1-Alpha")
            perspective (str): Deliberation lens (e.g., "risk", "ethics", "efficiency")
            tv_parent (str): Parent TV identifier
        """
        self.name = name
        self.perspective = perspective
        self.tv_parent = tv_parent
        self.prime_id = self._generate_prime_id()
        self.rank = "NCO Active"
        self.score = 0
        self.tasks_completed = 0
        self.created_at = datetime.utcnow().isoformat()
        self.reclaimer_disk = []

    def _generate_prime_id(self):
        """Generate unique Prime ID using SHA-256."""
        seed = f"{self.name}-{self.perspective}-{time.time()}"
        return hashlib.sha256(seed.encode()).hexdigest()[:16]

    def deliberate(self, task):
        """
        Run deliberation on a task from this MTV's perspective.

        Args:
            task (str): The Original Request (OR) text

        Returns:
            dict: Structured Response (SR) with analysis and metadata
        """
        start_time = time.time()
        sr = {
            "agent": self.name,
            "prime_id": self.prime_id,
            "perspective": self.perspective,
            "task": task,
            "analysis": self._analyze(task),
            "confidence": self._assess_confidence(task),
            "flags": self._check_flags(task),
            "timestamp": datetime.utcnow().isoformat(),
            "deliberation_time": 0
        }
        sr["deliberation_time"] = round(time.time() - start_time, 4)
        self.reclaimer_disk.append(sr)
        self.tasks_completed += 1
        return sr

    def _analyze(self, task):
        """
        Produce analysis from this MTV's perspective.
        Override in specialized subclasses for domain-specific analysis.
        """
        return {
            "perspective_lens": self.perspective,
            "input_received": task[:200],
            "assessment": f"Analysis from {self.perspective} perspective pending model integration",
            "recommendations": []
        }

    def _assess_confidence(self, task):
        """Return confidence score 0.0 - 1.0 for this analysis."""
        return 0.75

    def _check_flags(self, task):
        """Check for red flags from this perspective."""
        flags = []
        if len(task) < 10:
            flags.append("INSUFFICIENT_INPUT")
        return flags

    def generate_sr(self, task):
        """Public interface — alias for deliberate(). Returns Structured Response (SR)."""
        return self.deliberate(task)

    def rank_up(self):
        """Evaluate and apply promotion based on score."""
        self.score += 1
        if self.score >= 25:
            self.rank = "TV-Ready"
        elif self.score >= 10:
            self.rank = "Senior NCO"
        else:
            self.rank = "NCO Active"
        return self.rank

    def get_status(self):
        """Return current agent status."""
        return {
            "name": self.name,
            "prime_id": self.prime_id,
            "perspective": self.perspective,
            "rank": self.rank,
            "score": self.score,
            "tasks_completed": self.tasks_completed,
            "tv_parent": self.tv_parent,
            "created_at": self.created_at,
            "reclaimer_entries": len(self.reclaimer_disk)
        }


if __name__ == "__main__":
    print("=== MTV Agent Test ===")
    mtv = MTV(name="MTV1-Alpha", perspective="risk", tv_parent="TV1")
    print(f"Created: {mtv.name} | Prime ID: {mtv.prime_id}")
    print(f"Status: {mtv.get_status()}")
    sr = mtv.generate_sr("Evaluate defensive formation against spread offense")
    print("\nSR Output:")
    for key, val in sr.items():
        print(f"  {key}: {val}")
    mtv.rank_up()
    print(f"\nAfter rank_up: {mtv.rank} (score: {mtv.score})")
    print("=== Test Complete ===")

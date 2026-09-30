"""
JETinc — MTV (Minimum Tactical Variant) Agent
The smallest deliberation unit in the Triverai system.
Each MTV produces a Structured Response (SR) for its assigned perspective.

PATCHED: _analyze(), grade(), and comerge() now call Qwen via Ollama
instead of returning placeholder text. Everything else is unchanged.
"""
import hashlib
import time
from datetime import datetime
from agents.qwen_client import ask_qwen


class MTV:
    """
    Minimum Tactical Variant — base deliberation agent.
    Each MTV analyzes a task from one assigned perspective and produces
    a Structured Response (SR).
    """

    def __init__(self, name, perspective, tv_parent=None):
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
        seed = f"{self.name}-{self.perspective}-{time.time()}"
        return hashlib.sha256(seed.encode()).hexdigest()[:16]

    def deliberate(self, task):
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
        Produce the Original Response (OR) for this seat, from this
        agent's assigned perspective. REAL Qwen call — no placeholder.
        """
        prompt = (
            f"You are analyzing a task strictly from a '{self.perspective}' "
            f"perspective. Be concise — 2 to 4 sentences.\n\n"
            f"TASK: {task}\n\n"
            f"Your {self.perspective}-perspective response:"
        )
        try:
            response_text = ask_qwen(prompt)
        except RuntimeError as e:
            response_text = f"[ERROR — {e}]"

        return {
            "perspective_lens": self.perspective,
            "input_received": task[:200],
            "assessment": response_text,
            "recommendations": []
        }

    def grade(self, peer_name, peer_response, task):
        """
        Grade a peer's OR — this is SR1 or SR2 depending on which
        neighbor called it. Returns graded feedback text from Qwen.
        """
        prompt = (
            f"You are grading a peer agent's response from your "
            f"'{self.perspective}' perspective.\n\n"
            f"ORIGINAL TASK: {task}\n\n"
            f"PEER ({peer_name})'S RESPONSE: {peer_response}\n\n"
            f"In 2-4 sentences: is this response good, adequate, or "
            f"flawed from your perspective, and specifically why? "
            f"If it's flawed, say what would fix it."
        )
        try:
            return ask_qwen(prompt)
        except RuntimeError as e:
            return f"[ERROR — {e}]"

    def comerge(self, own_or, sr1_feedback, sr2_feedback, task):
        """
        CoMerge — combine this agent's own OR with the SR1 (right-neighbor
        grading) and SR2 (left-neighbor grading) it received, producing
        one improved combined response.
        """
        prompt = (
            f"You produced this original response to a task, then received "
            f"two peer reviews of it. Revise your response into one improved, "
            f"combined answer that incorporates any valid feedback.\n\n"
            f"TASK: {task}\n\n"
            f"YOUR ORIGINAL RESPONSE: {own_or}\n\n"
            f"PEER REVIEW 1: {sr1_feedback}\n\n"
            f"PEER REVIEW 2: {sr2_feedback}\n\n"
            f"Your combined, improved response (2-5 sentences):"
        )
        try:
            return ask_qwen(prompt)
        except RuntimeError as e:
            return f"[ERROR — {e}]"

    def subprimal_merge(self, comerged_responses, task):
        """
        R&R-seat-only action: merge all CoMerged responses from this
        tier into one final synthesized response.
        """
        joined = "\n\n".join(
            f"RESPONSE {i+1}: {r}" for i, r in enumerate(comerged_responses)
        )
        prompt = (
            f"You are the lead (R&R) agent. Merge the following combined "
            f"responses into one final, best answer to the task.\n\n"
            f"TASK: {task}\n\n{joined}\n\n"
            f"Final merged response (3-6 sentences):"
        )
        try:
            return ask_qwen(prompt)
        except RuntimeError as e:
            return f"[ERROR — {e}]"

    def vote(self, final_merge, task):
        """
        NASA Preflight vote — this flank agent votes Green/Yellow/Red
        on the final merged response.
        """
        prompt = (
            f"Vote on this final answer to the task. Respond with exactly "
            f"one word first — GREEN, YELLOW, or RED — then a one-sentence "
            f"reason.\n\nTASK: {task}\n\nFINAL ANSWER: {final_merge}\n\nVote:"
        )
        try:
            return ask_qwen(prompt)
        except RuntimeError as e:
            return f"[ERROR — {e}]"

    def _assess_confidence(self, task):
        return 0.75

    def _check_flags(self, task):
        flags = []
        if len(task) < 10:
            flags.append("INSUFFICIENT_INPUT")
        return flags

    def generate_sr(self, task):
        return self.deliberate(task)

    def generate_or(self, task):
        """Original Response as plain text — same interface as Triverai.generate_or,
        so a chamber seat holding either an MTV or a TV can be called identically."""
        sr = self.generate_sr(task)
        return sr["analysis"]["assessment"]

    def rank_up(self):
        self.score += 1
        if self.score >= 25:
            self.rank = "TV-Ready"
        elif self.score >= 10:
            self.rank = "Senior NCO"
        else:
            self.rank = "NCO Active"
        return self.rank

    def get_status(self):
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
    print("=== MTV Agent Test (LIVE QWEN CALL) ===")
    mtv = MTV(name="MTV1-Alpha", perspective="risk", tv_parent="TV1")
    print(f"Created: {mtv.name} | Prime ID: {mtv.prime_id}")
    sr = mtv.generate_sr("Evaluate defensive formation against spread offense")
    print("\nSR Output:")
    for key, val in sr.items():
        print(f"  {key}: {val}")
    print("=== Test Complete ===")

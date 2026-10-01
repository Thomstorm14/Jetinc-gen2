"""
JETinc — Chamber Rotation System
Triformer: counter-clockwise | Tricore: clockwise
Agents seated permanently. Roles rotate.

FIXED: tick now advances via explicit advance(), called once per task
cycle regardless of tier. Previously tick only incremented inside
rotate_triformer(), so any ChamberSystem instance used only for a
Tricore (which never calls rotate_triformer) would never rotate —
rotate_tricore() would return the same assignment forever.
"""

TRIFORMER_CHAMBERS = ["R&R", "Flank-Alpha", "Flank-Beta"]
TRICORE_CHAMBERS = ["R&R", "Flank-Alpha", "Flank-Beta"]


class ChamberSystem:
    def __init__(self, label):
        self.label = label
        self.tick = 0

    def advance(self):
        """Call once per completed task cycle, regardless of tier."""
        self.tick += 1
        return self.tick

    def rotate_triformer(self):
        return [
            TRIFORMER_CHAMBERS[(0 - self.tick) % 3],
            TRIFORMER_CHAMBERS[(1 - self.tick) % 3],
            TRIFORMER_CHAMBERS[(2 - self.tick) % 3]
        ]

    def rotate_tricore(self):
        return [
            TRICORE_CHAMBERS[(0 + self.tick) % 3],
            TRICORE_CHAMBERS[(1 + self.tick) % 3],
            TRICORE_CHAMBERS[(2 + self.tick) % 3]
        ]

    def get_rr_tv(self, assignments):
        for tv, role in assignments.items():
            if role == "R&R":
                return tv
        return None

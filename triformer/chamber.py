"""
JETinc — Chamber Rotation System
Triformer: counter-clockwise | Tricore: clockwise
Agents seated permanently. Roles rotate.
"""

TRIFORMER_CHAMBERS = ["R&R", "Flank-Alpha", "Flank-Beta"]
TRICORE_CHAMBERS = ["R&R", "Flank-Alpha", "Flank-Beta"]

class ChamberSystem:
    def __init__(self, label):
        self.label = label
        self.tick = 0

    def rotate_triformer(self):
        self.tick += 1
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
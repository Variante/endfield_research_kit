import json
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_secondary_dynamics_constraint_schedule_contract as target


class ConstraintScheduleContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = target.build_contract()

    def test_pins_two_distance_passes_and_full_order(self):
        self.assertEqual(self.contract["distancePassCount"], 2)
        self.assertEqual(
            self.contract["projectionOrder"][:6],
            ["Tether", "Distance pass 1", "Angle", "Triangle Bending", "Collider Collision", "Distance pass 2"],
        )

    def test_endminf_requires_projection_but_not_motion_or_self_collision(self):
        boundary = self.contract["endminfBoundary"]
        self.assertEqual(len(self.contract["endminfOwners"]), 4)
        self.assertEqual(
            boundary["authoredOrTopologyNoOpFamilies"],
            ["triangleBending", "motion", "selfCollision"],
        )
        for family in boundary["requiredForAllOwners"]:
            self.assertEqual(len(self.contract["endminfRequiredOwnersByFamily"][family]), 4)
        self.assertEqual(len(self.contract["endminfRequiredOwnersByFamily"]["colliderCollision"]), 3)
        self.assertEqual(len(self.contract["endminfRequiredOwnersByFamily"]["triangleBending"]), 0)
        self.assertEqual(sum(row["simulatedVertexCount"] for row in self.contract["endminfOwners"]), 126)

    def test_remains_fail_closed_on_numerics(self):
        boundary = self.contract["implementationBoundary"]
        self.assertTrue(boundary["managedCallOrderClosed"])
        self.assertFalse(boundary["constraintBurstNumericsClosed"])
        self.assertFalse(boundary["solverImplemented"])

    def test_generated_contract_matches(self):
        expected = json.dumps(self.contract, indent=2) + "\n"
        self.assertEqual(target.OUTPUT.read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()

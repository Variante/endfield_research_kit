import json
import sys
import tempfile
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
        self.assertEqual(len(self.contract["endminfRequiredOwnersByFamily"]["edgeColliderCollision"]), 0)
        self.assertEqual({row["colliderCollisionMode"] for row in self.contract["endminfOwners"]}, {1})
        self.assertEqual(len(self.contract["endminfRequiredOwnersByFamily"]["triangleBending"]), 0)
        self.assertEqual(sum(row["simulatedVertexCount"] for row in self.contract["endminfOwners"]), 126)

    def test_closes_only_the_source_static_active_avx2_candidate(self):
        boundary = self.contract["implementationBoundary"]
        self.assertTrue(boundary["managedCallOrderClosed"])
        self.assertTrue(boundary["endminfActiveAvx2CandidateNumericsClosed"])
        self.assertFalse(boundary["constraintBurstNumericsClosed"])
        self.assertFalse(boundary["solverImplemented"])
        self.assertFalse(boundary["selectedRetailRouteProven"])
        self.assertFalse(boundary["transformWritebackConnected"])

        candidate = self.contract["activeConstraintCandidate"]
        self.assertEqual(candidate["cpuCandidate"], "avx2")
        self.assertEqual(
            candidate["closedFamilies"],
            ["tether", "distance", "angle", "pointCollider"],
        )
        self.assertEqual(
            candidate["nativeGoldenVectorCounts"],
            {"tether": 5, "distance": 8, "angle": 25, "pointCollision": 6},
        )
        self.assertEqual(candidate["angleEndminfBaselineVectorCount"], 18)
        self.assertFalse(candidate["selectedRetailCpuRouteProven"])
        self.assertFalse(candidate["runtimeSolverCompositionConnected"])
        self.assertFalse(candidate["transformWritebackConnected"])

    def test_numeric_child_contract_hash_drift_fails_closed(self):
        source = target.NUMERIC_CONTRACTS[0]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / source[1]
            path.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(target.schedule.ContractError, "numeric contract drift"):
                target._numeric_constraint_coverage((source,), Path(temp_dir))

    def test_generated_contract_matches(self):
        expected = json.dumps(self.contract, indent=2) + "\n"
        self.assertEqual(target.OUTPUT.read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()

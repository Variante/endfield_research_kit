from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_secondary_dynamics_center_update_contract as builder


class SecondaryDynamicsCenterUpdateContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = builder.build_contract()

    def test_manager_and_burst_chain_are_pinned(self) -> None:
        methods = {row["methodIndex"]: row for row in self.payload["managedMethods"]}
        self.assertEqual(methods[384598]["startVa"], "0x1835bc3e0")
        self.assertEqual(methods[384598]["spanBytes"], 896)
        identity = self.payload["burstIdentity"]
        self.assertEqual(identity["export"]["name"], builder.EXPORT_NAME)
        self.assertEqual(identity["avx2"]["core"]["rva"], "0x28eb60")
        self.assertEqual(identity["avx2"]["core"]["bytes"], 16366)

    def test_schedule_and_payload_provenance_are_exact(self) -> None:
        self.assertEqual(self.payload["schedule"]["order"][:3], [
            "VirtualMeshManager.PreProxyMeshUpdate",
            "TeamManager.CalcCenterAndInertiaAndWind",
            "SimulationManager.PreSimulationUpdate",
        ])
        offsets = self.payload["schedule"]["jobPayloadOffsets"]
        self.assertEqual(offsets["centerDataArray"], "0x18")
        self.assertEqual(offsets["transformPositionArray"], "0x88")
        self.assertEqual(offsets["windZoneCount"], "0xb8")

    def test_endminf_scope_is_closed_to_zero_wind(self) -> None:
        scope = self.payload["endminfNoWindDomain"]
        self.assertEqual(scope["authoredMovingWindValues"], [0.0])
        self.assertEqual(scope["requiredRuntimeWindZoneCount"], 0)
        self.assertEqual(len(scope["clothOwners"]), 4)
        self.assertTrue(all(row["teamWindElementUnchanged"] for row in self.payload["goldenVectors"]))

    def test_selected_native_source_vectors_are_bit_exact(self) -> None:
        self.assertEqual(len(self.payload["goldenVectors"]), 4)
        for vector in self.payload["goldenVectors"]:
            self.assertEqual(set(vector["nativeSourceBitExact"]), set(builder.SELECTED_FIELDS))
            self.assertTrue(all(vector["nativeSourceBitExact"].values()), vector["name"])

    def test_endminf_fixed_lists_and_counts_are_source_pinned(self) -> None:
        rows = {row["owner"]: row for row in self.payload["endminfNoWindDomain"]["fixedCenters"]}
        self.assertEqual(rows["MC_Ribbon2"]["fixedArrayUInt16"], [0])
        self.assertEqual(rows["MC_Hair"]["fixedArrayUInt16"], [0, 3, 7, 10, 13, 17, 22, 26])
        self.assertEqual(rows["MC_Ribbon"]["fixedArrayUInt16"], [0, 6, 10, 16])
        self.assertEqual(rows["MC_Coat"]["fixedArrayUInt16"], [2, 4, 12, 26, 28, 33, 45, 47, 55])
        self.assertEqual([rows[name]["fixedCount"] for name in builder.ENDMINF_FIXED], [1, 8, 4, 9])
        self.assertEqual([rows[name]["centerTransformIndex"] for name in builder.ENDMINF_FIXED], [6, 30, 20, 70])

    def test_fixed_position_and_rotation_vectors_are_native_source_bit_exact(self) -> None:
        vectors = self.payload["fixedCenterGoldenVectors"]
        self.assertEqual([len(row["inputs"]["fixedArrayUInt16"]) for row in vectors],
                         [1, 8, 4, 9, 8, 4, 9])
        for vector in vectors:
            self.assertEqual(set(vector["nativeSourceBitExact"]), set(builder.TARGET_FIXED_CERTIFIED_FIELDS))
            self.assertTrue(all(vector["nativeSourceBitExact"].values()), vector["name"])
            self.assertTrue(vector["teamWindElementUnchanged"])

    def test_multi_fixed_rotation_is_closed_but_downstream_feed_remains_fail_closed(self) -> None:
        equations = " ".join(self.payload["exactClosedEquations"]["fixedCenterAggregation"])
        self.assertIn("rotated up=(0,1,0) and forward=(0,0,1)", equations)
        self.assertIn("spatial 8/4/9", equations)
        unresolved = " ".join(self.payload["failClosedBoundary"]["unresolved"])
        self.assertNotIn("multi-fixed", unresolved)
        self.assertIn("SimulationStepTeamUpdate", unresolved)
        self.assertIn("angularVelocity", unresolved)
        self.assertIn("gravityRatio", unresolved)
        self.assertIn("scaleRatio", unresolved)

    def test_calc_center_preserves_simulation_start_feed_sentinels(self) -> None:
        vectors = self.payload["targetMotionGoldenVectors"]
        self.assertEqual([row["owner"] for row in vectors], ["MC_Hair", "MC_Coat"])
        for vector in vectors:
            self.assertEqual(set(vector["preservedSimulationFeedFields"]),
                             set(builder.PRESERVED_SIMULATION_FEED_FIELDS))
            self.assertTrue(all(vector["preservedSimulationFeedFields"].values()))
            self.assertNotEqual(vector["bootstrapOutputs"]["center.frameWorldPosition"],
                                vector["animatedStepOutputs"]["center.frameWorldPosition"])
            self.assertTrue(all(vector["zeroRootSmoothingNativeSourceBitExact"].values()))
            self.assertTrue(vector["teamWindElementUnchanged"])
        ownership = self.payload["fieldAndArrayProvenance"]["simulationFeedOwnership"]
        self.assertIn("0x1c0..0x22b", ownership)
        self.assertIn("SimulationStepTeamUpdate", ownership)
        native_ownership = self.payload["simulationFeedWriteOwnership"]
        self.assertEqual(native_ownership["preservedRange"], "CenterData+0x1c0..0x22b")
        self.assertEqual(len(native_ownership["loadStoreOnlyChunks"]), 5)
        self.assertTrue(all(row["stackReferenceCount"] == 2
                            for row in native_ownership["loadStoreOnlyChunks"]))
        smoothing = " ".join(self.payload["exactClosedEquations"]["zeroRootMovementSmoothing"])
        self.assertIn("pow_f32(base, 3.0f)", smoothing)
        self.assertIn("0.22384002804756165", smoothing)

    def test_endminf_root_motion_is_target_closed_noop_only(self) -> None:
        proof = self.payload["endminfNoWindDomain"]["overviewRootMotionTargetProof"]
        self.assertEqual(proof["recoveredClipCount"], 2)
        self.assertFalse(proof["bothClips"]["hasRootCurves"])
        self.assertFalse(proof["bothClips"]["hasMotionCurves"])
        self.assertEqual(proof["bothClips"]["averageSpeed"], [0.0, 0.0, 0.0])
        self.assertEqual(proof["bothClips"]["averageAngularSpeed"], 0.0)
        self.assertIn("internally animated fixed vertices remain live", proof["boundary"])

    def test_team_clock_and_interpolation_ownership_is_explicit(self) -> None:
        provenance = self.payload["fieldAndArrayProvenance"]
        self.assertIn("candidateTime", " ".join(provenance["teamClock"]["equations"]))
        self.assertIn("frameInterpolation", " ".join(provenance["solverInterpolation"]))
        equations = " ".join(self.payload["exactClosedEquations"]["selectedTranslationDomain"])
        self.assertIn("preserves TeamData.frameInterpolation", equations)

    def test_unresolved_state_fails_closed(self) -> None:
        boundary = self.payload["failClosedBoundary"]
        self.assertFalse(boundary["runtimeFeedReady"])
        self.assertGreaterEqual(len(boundary["unresolved"]), 4)
        self.assertIn("Consumers must reject", boundary["rule"])

    def test_generated_contract_matches_builder(self) -> None:
        self.assertTrue(builder.DEFAULT_OUTPUT.is_file())
        self.assertEqual(json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8")), self.payload)


if __name__ == "__main__":
    unittest.main()

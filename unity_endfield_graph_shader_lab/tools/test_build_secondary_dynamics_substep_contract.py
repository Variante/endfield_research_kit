from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_secondary_dynamics_substep_contract as builder


class SecondaryDynamicsSubstepContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = builder.build_contract()

    def test_native_methods_and_equation_spans_are_pinned(self) -> None:
        self.assertEqual(len(self.payload["nativeMethods"]), 12)
        methods = {row["methodIndex"]: row for row in self.payload["nativeMethods"]}
        self.assertEqual(
            methods[384711]["sha256"],
            "54845866e2a08ec3f0d14a88960cb4ac64b7e54fdcfbf9b337f635ed885207f5",
        )
        self.assertEqual(
            methods[384614]["sha256"],
            "b5a49b1d2726d050c11d0eb4d9ae7cd99ab7baa96298887bbee8497e198619c7",
        )
        spans = {row["name"]: row for row in self.payload["equationSpans"]}
        self.assertEqual(spans["clothUpdateSolverLoop"]["spanBytes"], 76)
        self.assertEqual(spans["stepKernelGateAndClockAdvance"]["spanBytes"], 254)

    def test_field_and_array_provenance_is_exact(self) -> None:
        layouts = {row["type"]: row["fields"] for row in self.payload["fieldAndArrayProvenance"]["layouts"]}
        team = {row["name"]: row for row in layouts["BeyondDynamicBone.TeamManager+TeamData"]}
        self.assertEqual(team["time"]["nativePayloadOffset"], "0x14")
        self.assertEqual(team["nowUpdateTime"]["nativePayloadOffset"], "0x1c")
        self.assertEqual(team["updateCount"]["nativePayloadOffset"], "0x34")
        self.assertEqual(team["skipCount"]["nativePayloadOffset"], "0x38")
        manager = {row["name"]: row for row in layouts["BeyondDynamicBone.TeamManager"]}
        self.assertEqual(manager["teamDataArray"]["boxedFieldOffset"], "0x10")
        self.assertEqual(manager["maxUpdateCount"]["boxedFieldOffset"], "0x30")

    def test_default_clamps_and_solver_count_meaning_are_closed(self) -> None:
        frame = self.payload["frameUpdate"]
        self.assertEqual(frame["configurationClampsInclusive"]["simulationFrequency"], [30, 150])
        self.assertEqual(frame["configurationClampsInclusive"]["maxSimulationCountPerFrame"], [1, 5])
        self.assertEqual(frame["retailDefaults"]["simulationFrequency"], 90)
        self.assertEqual(frame["retailDefaults"]["maxSimulationCountPerFrame"], 3)
        self.assertIn("maximum active team count", self.payload["solverLoop"]["meaning"])

    def test_float32_accumulator_clamps_backlog_and_advances_clock(self) -> None:
        sd = builder._f32(1.0 / 90.0)
        count, skipped, time, now = builder.advance_normal_team(
            time=0.0,
            now_update_time=0.0,
            frame_delta_time=0.1,
            simulation_delta_time=sd,
            max_count=3,
        )
        self.assertEqual(count, 3)
        self.assertGreater(skipped, 0)
        self.assertEqual(now, builder._f32(builder._f32(builder._f32(sd + sd)) + sd))
        self.assertLess(builder._f32(time - now), sd)

    def test_ordinary_60fps_uses_one_or_two_steps_and_tracks_90hz(self) -> None:
        ordinary = self.payload["ordinary60FpsDefault90Hz"]
        self.assertEqual(ordinary["perRenderFrameSolverSteps"], [1, 2])
        self.assertEqual(ordinary["zeroInitializedFirst12Frames"]["counts"], [
            1, 2, 1, 2, 1, 1, 2, 2, 1, 1, 2, 1,
        ])
        self.assertEqual(ordinary["zeroInitializedFirst60Frames"]["totalSolverSteps"], 89)
        self.assertEqual(ordinary["zeroInitializedFirst1200Frames"]["totalSolverSteps"], 1800)
        self.assertFalse(ordinary["maxThreeClampReached"])

    def test_open_boundaries_fail_closed(self) -> None:
        boundary = self.payload["implementationBoundary"]
        self.assertTrue(boundary["perTeamAccumulatorClosed"])
        self.assertTrue(boundary["solverLoopCountClosed"])
        self.assertFalse(boundary["ifixPatchedRouteClosed"])
        self.assertFalse(boundary["runtimeImplemented"])
        self.assertFalse(boundary["visualVerificationPerformed"])

    def test_generated_contract_matches_builder(self) -> None:
        self.assertTrue(builder.DEFAULT_OUTPUT.is_file())
        self.assertEqual(
            json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8")),
            self.payload,
        )


if __name__ == "__main__":
    unittest.main()

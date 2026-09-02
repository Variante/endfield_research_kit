#!/usr/bin/env python3
"""Focused offline tests for pinned CalcLine Burst numeric vectors."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import build_secondary_dynamics_calc_line_burst_golden_vectors as builder


class SecondaryDynamicsCalcLineBurstGoldenVectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = builder.build_contract()

    def test_exact_dual_cpu_cores_and_source_transcription_match(self) -> None:
        payload = self.payload
        self.assertEqual(
            payload["status"],
            "dual_cpu_core_source_and_endminf_topology_exact",
        )
        self.assertEqual(
            payload["schema"],
            "endfield.charinfo.secondary-dynamics-calc-line-burst-golden-vectors.v2",
        )
        self.assertEqual(
            [(row["cpuVariant"], row["rva"], row["sha256"]) for row in payload["cores"]],
            [
                (
                    "x64_sse2",
                    "0xf4100",
                    "d2981125e4685061134d4e7c1048efc84c33ecc9053f09d3dc9d104756282824",
                ),
                (
                    "avx2",
                    "0x284c50",
                    "fd0fd8d14052cccdcf137f7e90391faadd0bae6c88c5e199fc908f0b8fe5b07c",
                ),
            ],
        )
        self.assertEqual(
            [row["sincosHelperRva"] for row in payload["cores"]],
            ["0x6e860", "0x1e5d30"],
        )
        boundary = payload["boundary"]
        self.assertEqual(boundary["nativeCpuVariantsExecuted"], ["x64_sse2", "avx2"])
        self.assertTrue(boundary["sourceOnlyTranscriptionMatchedBitForBit"])

    def test_traversal_equations_and_degeneracy_are_explicit(self) -> None:
        equations = self.payload["equations"]
        self.assertIn("per-child direction", equations["traversal"])
        self.assertIn("parent direction sum", equations["traversal"])
        self.assertIn("mulBurstBinary32(fromTo", equations["childRotation"])
        self.assertIn("Flag_Move", equations["childWriteGate"])
        self.assertIn("packed float4 grouping", equations["quaternionGrouping"])
        self.assertEqual(len(equations["acos64PolynomialCoefficients"]), 12)
        self.assertIn("even0=z2*(z*c0+c2)", equations["acos64Grouping"])
        self.assertIn("CPU-local pinned sincos helper", equations["axisAngle"])
        degeneracy = self.payload["degeneracy"]
        self.assertIn("returns identity", degeneracy["parallel"])
        self.assertIn("reference Y", degeneracy["antiparallel"])
        self.assertIn("canonical NaN", degeneracy["negativeXAxis"])
        self.assertEqual(degeneracy["emptyChild"], "no parent or child rotation write occurs")

    def test_character_neutral_vectors_cover_parent_sum_and_edge_cases(self) -> None:
        vectors = {row["name"]: row for row in self.payload["vectors"]}
        self.assertEqual(
            set(vectors),
            {
                "parallel_move",
                "quarter_turn_move",
                "antiparallel_positive_x",
                "non_move_assignment",
                "two_child_parent_direction_sum",
                "empty_child_no_write",
                "negative_x_antiparallel_zero_axis",
            },
        )
        self.assertEqual(vectors["two_child_parent_direction_sum"]["childCount"], 2)
        self.assertEqual(
            vectors["empty_child_no_write"]["rotationBitsLe"],
            [["0000003e", "000080be", "0000c03e", "0000003f"]],
        )
        self.assertEqual(
            vectors["negative_x_antiparallel_zero_axis"]["rotationBitsLe"],
            [["0000c0ff"] * 4, ["0000c0ff"] * 4],
        )

    def test_boundaries_remain_fail_closed(self) -> None:
        boundary = self.payload["boundary"]
        self.assertFalse(boundary["captureUsed"])
        self.assertFalse(boundary["runtimeRouteSelected"])
        self.assertFalse(boundary["writebackConnected"])
        self.assertFalse(boundary["managedIfixPatchStateClosed"])
        self.assertFalse(boundary["solverImplemented"])
        self.assertFalse(boundary["retailEquivalent"])

    def test_hash_pinned_endminf_topology_fixture_is_complete(self) -> None:
        sources = self.payload["sourceFiles"]
        self.assertEqual(
            sources["payloadDecode"]["sha256"],
            "6c8eed435f2acd645d3fb3560acf7c993b5ef34c8ff2336de1a9fa87a1cbff1a",
        )
        self.assertEqual(
            sources["solverInputs"]["sha256"],
            "fe91726b102a1104ed223be0aeb9138a76d58887a79851cc70736fd0d4ed6251",
        )
        owners = self.payload["endminfTopologyCases"]
        self.assertEqual(
            [owner["ownerPath"] for owner in owners],
            ["MC_Ribbon2", "MC_Hair", "MC_Ribbon", "MC_Coat"],
        )
        self.assertEqual(
            [owner["coverage"] for owner in owners],
            [
                {
                    "vertexCount": 6,
                    "lineCount": 5,
                    "baselineCount": 1,
                    "baselineParentVisitCount": 6,
                    "rootCount": 1,
                    "leafCount": 1,
                    "multiChildParentCount": 0,
                    "fixedVertexCount": 1,
                    "movableVertexCount": 5,
                },
                {
                    "vertexCount": 30,
                    "lineCount": 22,
                    "baselineCount": 8,
                    "baselineParentVisitCount": 29,
                    "rootCount": 8,
                    "leafCount": 9,
                    "multiChildParentCount": 1,
                    "fixedVertexCount": 9,
                    "movableVertexCount": 21,
                },
                {
                    "vertexCount": 20,
                    "lineCount": 16,
                    "baselineCount": 4,
                    "baselineParentVisitCount": 18,
                    "rootCount": 4,
                    "leafCount": 4,
                    "multiChildParentCount": 0,
                    "fixedVertexCount": 6,
                    "movableVertexCount": 14,
                },
                {
                    "vertexCount": 70,
                    "lineCount": 65,
                    "baselineCount": 5,
                    "baselineParentVisitCount": 32,
                    "rootCount": 5,
                    "leafCount": 14,
                    "multiChildParentCount": 5,
                    "fixedVertexCount": 43,
                    "movableVertexCount": 27,
                },
            ],
        )
        for owner in owners:
            self.assertEqual(
                [state["name"] for state in owner["states"]],
                ["bind_rest", "seeded_perturbation_a", "seeded_perturbation_b"],
            )
            self.assertEqual(len(owner["attributes"]), owner["coverage"]["vertexCount"])
            self.assertEqual(
                len(owner["localPositionBitsLe"]), owner["coverage"]["vertexCount"]
            )
            self.assertEqual(
                len(owner["localRotationBitsLe"]), owner["coverage"]["vertexCount"]
            )
            for state in owner["states"]:
                self.assertEqual(
                    len(state["outputRotationBitsLe"]), owner["coverage"]["vertexCount"]
                )
                for variant in ("x64_sse2", "avx2"):
                    mutation = state["nativeMutation"][variant]
                    self.assertEqual(mutation["declaredMutableBuffers"], ["rotations"])
                    self.assertEqual(mutation["changedBuffers"], ["rotations"])
                    self.assertEqual(
                        mutation["immutableBeforeSha256"],
                        mutation["immutableAfterSha256"],
                    )
                    self.assertNotEqual(
                        mutation["rotationBeforeSha256"],
                        mutation["rotationAfterSha256"],
                    )
        boundary = self.payload["boundary"]
        self.assertEqual(boundary["endminfOwnerCount"], 4)
        self.assertEqual(boundary["endminfStateCountPerOwner"], 3)
        self.assertEqual(boundary["endminfTopologyCaseCount"], 12)
        self.assertTrue(boundary["fullBaselinePackedChildTraversalExecuted"])
        self.assertTrue(boundary["rotationOnlyMutationProven"])

    def test_generated_contract_matches(self) -> None:
        expected = json.dumps(self.payload, indent=2, allow_nan=True) + "\n"
        self.assertEqual(builder.OUTPUT.read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()

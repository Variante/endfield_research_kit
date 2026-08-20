#!/usr/bin/env python3
"""Tests for the fixed-client Wind helper static contract."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys


TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import build_secondary_dynamics_wind_helper_contract as builder  # noqa: E402


class SecondaryDynamicsWindHelperContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        cls.by_index = {row["methodIndex"]: row for row in cls.payload["methods"]}

    def test_report_is_pinned_and_current(self) -> None:
        self.assertEqual(self.payload["status"], "native_spans_hash_pinned_wind_helpers")
        self.assertEqual(self.payload["solverStatus"], "managed_helper_static_semantics_only_burst_solver_unresolved")
        self.assertEqual(builder.build_contract(), self.payload)

    def test_wind_span_calls_and_two_blend_edges(self) -> None:
        wind = self.by_index[builder.WIND_INDEX]
        calls = {(row["offset"], row["targetVa"]) for row in wind["directCalls"]}
        self.assertIn(("0x28a", "0x186776394"), calls)
        self.assertIn(("0x318", "0x186776394"), calls)
        self.assertEqual([row["offset"] for row in wind["blendCallSemantics"]], ["0x28a", "0x318"])
        self.assertEqual(wind["blendCallSemantics"][0]["setupInstructions"][0]["rawBytes"], "4c8d4d90")
        self.assertEqual(wind["blendCallSemantics"][1]["setupInstructions"][-1]["rawBytes"], "f30f11742420")

    def test_wind_buffer_strides_and_displacements(self) -> None:
        accesses = {row["jobField"]: row for row in self.by_index[builder.WIND_INDEX]["bufferAccesses"]}
        self.assertEqual(accesses["vertexRootIndices"]["strideBytes"], 4)
        self.assertEqual(accesses["teamWindArray"]["strideBytes"], 152)
        self.assertEqual(accesses["teamWindArray"]["elementFieldDisplacements"][-1], 144)
        self.assertEqual(accesses["windDataArray"]["strideBytes"], 212)
        self.assertEqual(accesses["windDataArray"]["elementFieldDisplacements"][-1], 208)
        self.assertEqual(accesses["frictionArray"]["strideBytes"], 4)
        self.assertEqual(self.by_index[builder.WIND_INDEX]["canonicalJobFields"]["0x68"]["name"], "vertexRootIndices")

    def test_helper_branches_constants_and_result_boundary(self) -> None:
        helper = self.by_index[builder.WIND_FORCE_BLEND_INDEX]
        self.assertEqual([(row["offset"], row["targetOffset"], row["condition"]) for row in helper["branches"]], [("0x50", "0x2f3", "jne"), ("0x68", "0x2db", "ja")])
        self.assertEqual(helper["branches"][0]["opcode"], "0f85")
        constants = {row["meaning"]: row["float32Bits"] for row in helper["constants"]}
        self.assertEqual(constants["minimum-wind-info"], "0x3c23d70a")
        self.assertEqual(constants["degrees-to-radians"], "0x3c8efa35")
        self.assertEqual(helper["resultContract"]["normalPath"]["writes"][-1]["widthBytes"], 4)
        self.assertEqual(helper["resultContract"]["thresholdPath"]["value"], "zero")

    def test_native_gate_fails_closed_for_missing_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.dll"
            with self.assertRaises(builder.ContractError):
                builder.build_contract(missing, missing)

    def test_body_hash_and_call_drift_are_rejected(self) -> None:
        original_hash = builder.EXPECTED_SPANS[builder.WIND_INDEX]["bodySha256"]
        builder.EXPECTED_SPANS[builder.WIND_INDEX]["bodySha256"] = "0" * 64
        try:
            with self.assertRaises(builder.ContractError):
                builder.build_contract()
        finally:
            builder.EXPECTED_SPANS[builder.WIND_INDEX]["bodySha256"] = original_hash

        original_calls = builder.EXPECTED_CALLS[builder.WIND_INDEX]
        builder.EXPECTED_CALLS[builder.WIND_INDEX] = original_calls[:-1]
        try:
            with self.assertRaises(builder.ContractError):
                builder.build_contract()
        finally:
            builder.EXPECTED_CALLS[builder.WIND_INDEX] = original_calls

        original_access = builder.WIND_BUFFER_ACCESS[1]["elementFieldDisplacements"][-1]
        builder.WIND_BUFFER_ACCESS[1]["elementFieldDisplacements"][-1] = original_access + 1
        try:
            with self.assertRaises(builder.ContractError):
                builder.build_contract()
        finally:
            builder.WIND_BUFFER_ACCESS[1]["elementFieldDisplacements"][-1] = original_access

    def test_constant_and_branch_drift_are_rejected(self) -> None:
        original = builder.EXPECTED_CONSTANTS[builder.WIND_FORCE_BLEND_INDEX][0]
        builder.EXPECTED_CONSTANTS[builder.WIND_FORCE_BLEND_INDEX][0] = (original[0], original[1], original[2], 0)
        try:
            with self.assertRaises(builder.ContractError):
                builder.build_contract()
        finally:
            builder.EXPECTED_CONSTANTS[builder.WIND_FORCE_BLEND_INDEX][0] = original

        original_branch = builder.EXPECTED_BRANCHES[builder.WIND_INDEX][0]
        builder.EXPECTED_BRANCHES[builder.WIND_INDEX][0] = (original_branch[0], original_branch[1], original_branch[2] + 1, original_branch[3])
        try:
            with self.assertRaises(builder.ContractError):
                builder.build_contract()
        finally:
            builder.EXPECTED_BRANCHES[builder.WIND_INDEX][0] = original_branch

        original_condition = builder.EXPECTED_BRANCHES[builder.WIND_INDEX][0]
        builder.EXPECTED_BRANCHES[builder.WIND_INDEX][0] = (original_condition[0], "je", original_condition[2], original_condition[3])
        try:
            with self.assertRaises(builder.ContractError):
                builder.build_contract()
        finally:
            builder.EXPECTED_BRANCHES[builder.WIND_INDEX][0] = original_condition


if __name__ == "__main__":
    unittest.main()

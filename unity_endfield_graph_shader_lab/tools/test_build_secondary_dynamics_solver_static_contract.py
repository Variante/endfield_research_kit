#!/usr/bin/env python3
"""Tests for the fail-closed solver boundary contract."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))
import build_secondary_dynamics_solver_static_contract as builder


class SecondaryDynamicsSolverStaticContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        cls.by_index = {row["methodIndex"]: row for row in cls.payload["targets"]}

    def test_report_is_pinned_and_current(self) -> None:
        self.assertEqual(self.payload["status"], "native_spans_hash_pinned")
        self.assertEqual(self.payload["nativeGate"]["gameAssembly"]["sha256"], builder.EXPECTED_GAME_ASSEMBLY_SHA256)
        self.assertEqual(self.payload["nativeGate"]["globalMetadata"]["sha256"], builder.EXPECTED_METADATA_SHA256)
        self.assertEqual(builder.build_contract(), self.payload)

    def test_execute_wrappers_are_not_solver(self) -> None:
        for method_index, callee in ((385696, 385697), (385703, 385704), (385450, 385451), (385454, 385455)):
            row = self.by_index[method_index]
            self.assertEqual(row["role"], "managed_dispatch_wrapper")
            self.assertEqual(row["solverStatus"], "wrapper_only")
            self.assertEqual(row["nextCalls"][0]["methodIndex"], callee)

    def test_unsafedo_next_calls_are_burst_wrappers(self) -> None:
        self.assertEqual(self.by_index[385701]["nextCalls"][0]["methodIndex"], 385542)
        self.assertEqual(self.by_index[385701]["nextCalls"][1]["methodIndex"], 385570)
        self.assertEqual(self.by_index[385452]["nextCalls"][0]["methodIndex"], 385394)
        self.assertEqual(self.by_index[385456]["nextCalls"][0]["methodIndex"], 385295)
        self.assertEqual(self.by_index[385705]["nextCalls"][0]["methodIndex"], 385602)
        for method_index in (385701, 385705, 385452, 385456):
            self.assertEqual(self.by_index[method_index]["solverStatus"], "wrapper_only_burst_solver_unresolved")

    def test_wind_helper_closes_wind_force_blend(self) -> None:
        wind = self.by_index[385699]
        self.assertEqual(wind["nextCalls"][0]["methodIndex"], 385700)
        self.assertEqual(wind["nextCalls"][0]["instructionOffsets"], ["0x28a", "0x318"])

    def test_managed_fallback_strides_and_field_displacements(self) -> None:
        sim = {row["jobField"]: row for row in self.by_index[385697]["bufferAccesses"]}
        self.assertEqual(sim["stepParticleIndexArray"]["strideBytes"], 4)
        self.assertEqual(sim["teamDataArray"]["strideBytes"], 464)
        self.assertEqual(sim["parameterArray"]["strideBytes"], 808)
        self.assertEqual(sim["positions"]["strideBytes"], 24)
        self.assertEqual(sim["rotations"]["strideBytes"], 16)
        self.assertEqual(sim["positions"]["elementFieldDisplacements"], [0, 16])

        update = {row["jobField"]: row for row in self.by_index[385704]["bufferAccesses"]}
        self.assertEqual(update["stepBaseLineIndexArray"]["strideBytes"], 4)
        self.assertEqual(update["teamDataArray"]["strideBytes"], 464)
        self.assertEqual(update["vertexLocalPositions"]["strideBytes"], 12)
        self.assertEqual(update["vertexLocalRotations"]["strideBytes"], 16)
        self.assertEqual(update["basePosArray"]["strideBytes"], 24)
        self.assertEqual(update["stepBasicPositionArray"]["elementFieldDisplacements"], [0, 16])

        collider = {row["jobField"]: row for row in self.by_index[385455]["bufferAccesses"]}
        self.assertEqual(collider["jobColliderIndexList"]["strideBytes"], 4)
        self.assertEqual(collider["nowPositions"]["strideBytes"], 24)
        self.assertEqual(collider["oldRotations"]["strideBytes"], 16)

    def test_native_gate_fails_closed_for_missing_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.dll"
            with self.assertRaises(builder.ContractError):
                builder.build_contract(missing, missing)

    def test_body_hash_drift_is_rejected(self) -> None:
        original = builder.TARGETS[0]["bodySha256"]
        try:
            builder.TARGETS[0]["bodySha256"] = "0" * 64
            with self.assertRaises(builder.ContractError):
                builder.build_contract()
        finally:
            builder.TARGETS[0]["bodySha256"] = original

    def test_method_identity_and_instruction_arithmetic_are_rejected_when_changed(self) -> None:
        target = builder.TARGETS[1]
        original_type = target["type"]
        target["type"] = "wrong.Type"
        try:
            with self.assertRaises(builder.ContractError):
                builder.build_contract()
        finally:
            target["type"] = original_type

        access = target["bufferAccesses"][0]
        original_stride = access["strideBytes"]
        access["strideBytes"] = original_stride + 1
        try:
            with self.assertRaises(builder.ContractError):
                builder.build_contract()
        finally:
            access["strideBytes"] = original_stride


if __name__ == "__main__":
    unittest.main()

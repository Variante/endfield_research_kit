#!/usr/bin/env python3
"""Tests for the fail-closed secondary-dynamics Burst wrapper contract."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))
import build_secondary_dynamics_burst_wrapper_contract as builder


GAME_ASSEMBLY = Path(r"D:\Program Files\Endfield Game\GameAssembly.dll")
METADATA = Path(r"D:\Program Files\Endfield Game\Endfield_Data\il2cpp_data\Metadata\global-metadata.dat")


class SecondaryDynamicsBurstWrapperContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        cls.by_index = {row["methodIndex"]: row for row in cls.payload["targets"]}

    def test_report_is_pinned_and_current(self) -> None:
        self.assertEqual(self.payload["status"], "initialization_resolution_chain_closed_export_mapping_unresolved")
        self.assertEqual(self.payload["nativeGate"]["gameAssembly"]["sha256"], builder.EXPECTED_GAME_ASSEMBLY_SHA256)
        self.assertEqual(self.payload["nativeGate"]["globalMetadata"]["sha256"], builder.EXPECTED_METADATA_SHA256)
        self.assertEqual(self.payload["nativeGate"]["libBurstGenerated"]["sha256"], builder.EXPECTED_LIB_BURST_SHA256)
        self.assertEqual(builder.build_contract(gameassembly=GAME_ASSEMBLY, metadata=METADATA), self.payload)

    def test_requested_entries_are_exact_wrappers(self) -> None:
        self.assertEqual(self.by_index[385570]["role"], "simulation_start_entry")
        self.assertEqual(self.by_index[385394]["role"], "collider_start_entry")
        self.assertEqual(self.by_index[385295]["role"], "collider_end_entry")
        self.assertEqual(self.by_index[385570]["spanBytes"], 944)
        self.assertEqual(self.by_index[385394]["spanBytes"], 300)
        self.assertEqual(self.by_index[385295]["spanBytes"], 136)

    def test_wrapper_fallback_and_pointer_calls_are_recorded(self) -> None:
        sim = self.by_index[385570]
        self.assertEqual({row["methodIndex"] for row in sim["directCalls"] if "methodIndex" in row}, {489283, 385566, 385547})
        self.assertEqual(sim["indirectCalls"][0]["register"], "rdx")
        self.assertEqual(self.by_index[385394]["directCalls"][-1]["methodIndex"], 385416)
        self.assertEqual(self.by_index[385295]["directCalls"][-1]["methodIndex"], 385317)
        self.assertEqual(self.by_index[385416]["indirectCalls"][0]["register"], "r10")
        self.assertEqual(self.by_index[385317]["indirectCalls"][0]["register"], "rax")

    def test_initialization_chain_reaches_burst_compiler_service(self) -> None:
        path = self.payload["resolutionPath"]
        self.assertEqual(path["managedBurstCompilerMethods"], [489283, 489284, 489285, 489288])
        self.assertEqual(path["burstCompilerServiceMethods"], [402096, 402097])
        self.assertFalse(path["getProcAddressObservedStatically"])
        self.assertTrue(path["runtimeTelemetryRequired"])
        self.assertEqual(self.payload["burstGenerated"]["count"], 628)
        self.assertEqual(self.payload["burstGenerated"]["mappingStatus"], "unresolved_wrapper_to_hashed_export")
        self.assertEqual(len(self.payload["unresolved"]), 3)

    def test_rip_globals_are_pinned(self) -> None:
        sim = self.by_index[385570]
        targets = {row["targetVa"] for row in sim["ripGlobals"]}
        self.assertIn("0x18f38145d", targets)
        self.assertIn("0x18e366608", targets)
        self.assertIn("0x18e30d578", targets)
        self.assertTrue(self.payload["burstGenerated"]["stringEvidence"]["pdbPathStringObserved"])

    def test_native_gate_fails_closed_for_missing_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.dll"
            with self.assertRaises(builder.ContractError):
                builder.build_contract(gameassembly=missing, metadata=missing)

    def test_body_hash_drift_is_rejected(self) -> None:
        original = builder.TARGET_SPECS[385570]["sha"]
        builder.TARGET_SPECS[385570]["sha"] = "0" * 64
        try:
            with self.assertRaises(builder.ContractError):
                builder.build_contract(gameassembly=GAME_ASSEMBLY, metadata=METADATA)
        finally:
            builder.TARGET_SPECS[385570]["sha"] = original

    def test_semantic_table_attacks_fail_closed(self) -> None:
        original = builder.TARGET_SPECS[385570]
        try:
            builder.TARGET_SPECS[385570] = dict(original, role="fake_role")
            with self.assertRaises(builder.ContractError):
                builder.build_contract(gameassembly=GAME_ASSEMBLY, metadata=METADATA)
            builder.TARGET_SPECS[385570] = dict(original)
            builder.TARGET_SPECS[385570]["calls"] = dict(original["calls"])
            builder.TARGET_SPECS[385570]["calls"].pop(0x7B)
            with self.assertRaises(builder.ContractError):
                builder.build_contract(gameassembly=GAME_ASSEMBLY, metadata=METADATA)
            builder.TARGET_SPECS[385570] = dict(original)
            builder.TARGET_SPECS[385570]["rip"] = list(original["rip"])
            builder.TARGET_SPECS[385570]["rip"][0] = (0x0A, 7, "fake_rip")
            with self.assertRaises(builder.ContractError):
                builder.build_contract(gameassembly=GAME_ASSEMBLY, metadata=METADATA)
            builder.TARGET_SPECS[385570] = dict(original)
            builder.TARGET_SPECS[385570]["indirect"] = [(0x208, "rax", "fake_indirect")]
            with self.assertRaises(builder.ContractError):
                builder.build_contract(gameassembly=GAME_ASSEMBLY, metadata=METADATA)
        finally:
            builder.TARGET_SPECS[385570] = original

    def test_target_set_and_static_ctor_export_attacks_fail_closed(self) -> None:
        original = builder.TARGET_SPECS[385570]
        builder.TARGET_SPECS[999999] = original
        try:
            with self.assertRaises(builder.ContractError):
                builder.build_contract(gameassembly=GAME_ASSEMBLY, metadata=METADATA)
        finally:
            del builder.TARGET_SPECS[999999]

        cctor = builder.STATIC_CCTOR_SPECS[385569]
        original_end = cctor["end"]
        cctor["end"] = original_end + 1
        try:
            with self.assertRaises(builder.ContractError):
                builder.build_contract(gameassembly=GAME_ASSEMBLY, metadata=METADATA)
        finally:
            cctor["end"] = original_end

        exports = builder.build_contract(gameassembly=GAME_ASSEMBLY, metadata=METADATA)["burstGenerated"]
        bad_exports = dict(exports)
        bad_exports["ordinalRvaSha256"] = "0" * 64
        with patch.object(builder, "_exports", return_value=bad_exports):
            with self.assertRaises(builder.ContractError):
                builder.build_contract(gameassembly=GAME_ASSEMBLY, metadata=METADATA)


if __name__ == "__main__":
    unittest.main()

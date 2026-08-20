#!/usr/bin/env python3
"""Focused tests for the direct secondary-dynamics element layout contract."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(TOOLS_ROOT))

import build_secondary_dynamics_element_layout_contract as builder


class SecondaryDynamicsElementLayoutTests(unittest.TestCase):
    def test_published_contract_reconstructs_and_keeps_solver_false(self) -> None:
        observed = builder.build_contract()
        published = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(observed, published)
        self.assertEqual(published["status"], "element_struct_direct_layout_closed")
        self.assertTrue(published["element_struct_layout_recovered"])
        self.assertTrue(published["direct_fields_recovered"])
        self.assertFalse(published["job_payload_layout_recovered"])
        self.assertFalse(published["secondary_dynamics_verified"])
        self.assertFalse(published["solver_implemented"])
        self.assertFalse(published["retail_equivalent"])

        expected_sizes = {
            "BeyondDynamicBone.TeamManager+TeamData": (464, 69),
            "BeyondDynamicBone.InertiaConstraint+CenterData": (696, 40),
            "BeyondDynamicBone.ClothParameters": (808, 21),
            "BeyondDynamicBone.ColliderManager+WorkData": (184, 6),
            "BeyondDynamicBone.TeamWindData": (152, 2),
            "BeyondDynamicBone.WindManager+WindData": (212, 12),
        }
        self.assertEqual(len(published["elements"]), len(expected_sizes))
        for element in published["elements"]:
            self.assertEqual(
                (element["nativeSizeBytes"], element["fieldCount"]),
                expected_sizes[element["name"]],
            )
            self.assertTrue(element["directFieldsOnly"])
            self.assertEqual(element["fields"][-1]["slotEndNativePayloadOffset"],
                             f"0x{element['nativeSizeBytes']:x}")
            for field in element["fields"]:
                self.assertGreater(field["slotSpanBytes"], 0)
                self.assertEqual(
                    int(field["boxedFieldOffset"], 16) - 0x10,
                    int(field["nativePayloadOffset"], 16),
                )
                self.assertEqual(
                    int(field["slotEndNativePayloadOffset"], 16),
                    int(field["nativePayloadOffset"], 16) + field["slotSpanBytes"],
                )

    def test_known_boundaries_and_generic_fields_are_explicit(self) -> None:
        payload = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        by_name = {element["name"]: element for element in payload["elements"]}
        team = by_name["BeyondDynamicBone.TeamManager+TeamData"]
        parent = next(field for field in team["fields"] if field["name"] == "syncParentTeamId")
        self.assertEqual(parent["metadataTypeIndex"], 34499)
        self.assertEqual(parent["metadataTypeName"],
                         "Unity.Collections.FixedList32Bytes`1<System.Int32>")
        self.assertEqual(parent["nativePayloadOffset"], "0xc0")
        self.assertEqual(parent["slotSpanBytes"], 32)
        self.assertEqual(parent["metadataType"]["genericOrReferenceBoundary"],
                         "generic_arguments_not_recursed")
        wind = by_name["BeyondDynamicBone.TeamWindData"]
        zones = wind["fields"][0]
        self.assertEqual(zones["metadataTypeName"],
                         "Unity.Collections.FixedList128Bytes`1<BeyondDynamicBone.TeamWindInfo>")
        self.assertEqual(zones["slotSpanBytes"], 128)
        self.assertEqual(zones["metadataType"]["genericContext"]["argumentCount"], 1)
        center = by_name["BeyondDynamicBone.InertiaConstraint+CenterData"]
        scale = next(field for field in center["fields"] if field["name"] == "componentWorldScale")
        # The field's float3 value is 12 bytes, but the native slot reaches the
        # next 16-byte boundary.  Keep both notions visible and separate.
        self.assertEqual(scale["metadataTypeName"], "Unity.Mathematics.float3")
        self.assertEqual(scale["metadataType"]["typeDefinitionNativeSizeBytes"], 12)
        self.assertEqual(scale["slotSpanBytes"], 16)

    def test_common_gate_receives_explicit_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            gameassembly = root / "GameAssembly.dll"
            metadata = root / "global-metadata.dat"
            gameassembly.write_bytes(b"game")
            metadata.write_bytes(b"metadata")
            result = SimpleNamespace(
                validated=True,
                status="validated",
                detail="",
                gameassembly=gameassembly,
                metadata=metadata,
                gameassembly_sha256=builder.EXPECTED_GAME_ASSEMBLY_SHA256,
                metadata_sha256=builder.EXPECTED_METADATA_SHA256,
            )
            with patch.object(builder, "check_installed_native_inputs", return_value=result) as check:
                observed = builder._native_gate(gameassembly, metadata)
            check.assert_called_once_with(
                builder.EXPECTED_GAME_ASSEMBLY_SHA256,
                builder.EXPECTED_METADATA_SHA256,
                gameassembly=gameassembly,
                metadata=metadata,
            )
            self.assertEqual(observed["gameAssembly"]["path"], gameassembly.resolve().as_posix())

    def test_gate_rejects_missing_input_before_metadata_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / "missing"
            with self.assertRaisesRegex(builder.ContractError, "installed GameAssembly.dll"):
                builder._native_gate(missing, missing)

    def test_declaration_drift_is_fail_closed(self) -> None:
        original = builder.STRUCTS
        drifted = list(original)
        name, type_index, field_start, field_count, fields = drifted[0]
        drifted[0] = (name, type_index, field_start, field_count,
                       (("wrongField", fields[0][1]),) + fields[1:])
        with patch.object(builder, "STRUCTS", tuple(drifted)):
            with self.assertRaisesRegex(builder.ContractError, "declaration drift"):
                builder.build_contract()


if __name__ == "__main__":
    unittest.main()

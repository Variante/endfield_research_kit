#!/usr/bin/env python3
"""Focused tests for helper-accessed secondary-dynamics value layouts."""

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

import build_secondary_dynamics_accessed_layout_contract as builder


class SecondaryDynamicsAccessedLayoutTests(unittest.TestCase):
    def test_published_contract_reconstructs_without_solver_claim(self) -> None:
        observed = builder.build_contract()
        published = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(observed, published)
        self.assertEqual(published["status"], "accessed_nested_direct_layouts_closed")
        self.assertTrue(published["accessed_layouts_recovered"])
        self.assertFalse(published["secondary_dynamics_verified"])
        self.assertFalse(published["solver_implemented"])
        self.assertFalse(published["retail_equivalent"])

        expected_sizes = {
            "BeyondDynamicBone.SpringConstraint+SpringConstraintParams": (16, 4),
            "BeyondDynamicBone.WindParams": (28, 7),
            "BeyondDynamicBone.TeamWindInfo": (24, 4),
            "Unity.Mathematics.double3": (24, 3),
            "Unity.Mathematics.quaternion": (16, 1),
            "Unity.Mathematics.float3": (12, 3),
        }
        for layout in published["layouts"]:
            self.assertEqual(
                (layout["nativeSizeBytes"], len(layout["fields"])),
                expected_sizes[layout["name"]],
            )
            self.assertTrue(layout["directFieldsOnly"])
            self.assertEqual(
                int(layout["fields"][-1]["slotEndNativePayloadOffset"], 16),
                layout["nativeSizeBytes"],
            )

    def test_static_fields_are_not_instance_layout_claims(self) -> None:
        payload = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        by_name = {layout["name"]: layout for layout in payload["layouts"]}
        double3 = by_name["Unity.Mathematics.double3"]
        self.assertEqual(double3["staticFields"][0]["name"], "zero")
        self.assertLess(int(double3["staticFields"][0]["nativePayloadOffset"], 16), 0)
        quaternion = by_name["Unity.Mathematics.quaternion"]
        self.assertEqual(quaternion["fields"][0]["metadataTypeName"], "Unity.Mathematics.float4")
        self.assertIn("opaque 16-byte float4 payload", payload["boundary"]["quaternionValue"])

    def test_method_evidence_is_exactly_the_three_helpers(self) -> None:
        payload = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(
            [row["methodIndex"] for row in payload["methodEvidence"]],
            [385698, 385699, 385700],
        )
        self.assertEqual(payload["methodEvidence"][0]["bodySha256"],
                         "149382eea39d5d1a3ca0e27ed701a665f51406664766283b070305adc52050b5")
        self.assertEqual(payload["methodEvidence"][2]["accesses"][0]["accessedOffsets"],
                         ["0x4", "0x8", "0xc", "0x14"])

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

    def test_gate_rejects_unvalidated_inputs(self) -> None:
        with patch.object(
            builder,
            "check_installed_native_inputs",
            return_value=SimpleNamespace(validated=False, status="mismatched", detail="wrong build"),
        ):
            with self.assertRaisesRegex(builder.ContractError, "mismatched"):
                builder._native_gate(None, None)


if __name__ == "__main__":
    unittest.main()

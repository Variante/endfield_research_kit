#!/usr/bin/env python3
"""Focused tests for the pinned Burst export candidate contract."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import build_secondary_dynamics_burst_export_contract as builder


class SecondaryDynamicsBurstExportTests(unittest.TestCase):
    def test_published_report_is_pinned_and_fail_closed(self) -> None:
        payload = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "secondary_dynamics_static_candidate_classification_unresolved_export_identity")
        self.assertEqual(payload["native_gate"]["gameAssembly"]["sha256"], builder.EXPECTED_GAME_ASSEMBLY_SHA256)
        self.assertEqual(payload["native_gate"]["globalMetadata"]["sha256"], builder.EXPECTED_METADATA_SHA256)
        self.assertEqual(payload["native_gate"]["libBurstGenerated"]["sha256"], builder.EXPECTED_LIB_BURST_SHA256)
        self.assertEqual(payload["pe"]["totalNamedExportCount"], 3141)
        self.assertEqual(payload["pe"]["hashedExportCount"], 628)
        self.assertEqual(
            payload["targets"]["simulationStartRange"]["candidates"][0]["hash"],
            "c7e2be088565d3ff7a6e7ba86d23fd51",
        )
        self.assertEqual(
            [row["hash"] for row in payload["targets"]["colliderStartRange"]["candidates"]],
            [
                "4aa6773b1eaf6055e0feb9593e092585",
                "7342567c29c434b5b924be51bd8e34b7",
                "8b3d2761aaaac71a35d4a2557d570456",
            ],
        )
        self.assertEqual(
            [row["hash"] for row in payload["targets"]["colliderEndRange"]["candidates"]],
            [
                "5d15fdfe5676d33316f2415a1f41d523",
                "e6aec003f0525fe127cd9c0ccb59b1e2",
            ],
        )
        unresolved = " ".join(payload["unresolved"])
        self.assertIn("GetProcAddress", unresolved)
        self.assertIn("hash bytes", unresolved)

    def test_stack_feature_decoder_preserves_width_and_offsets(self) -> None:
        body = bytes.fromhex(
            "f3 0f 11 64 24 20 "
            "48 89 44 24 28 "
            "4c 89 84 24 80 00 00 00"
        )
        self.assertEqual(
            builder._stack_writes(body),
            [
                {"offset": 32, "widthBytes": 4, "kind": "xmm"},
                {"offset": 40, "widthBytes": 8},
                {"offset": 128, "widthBytes": 8},
            ],
        )

    def test_export_parser_rejects_non_pe_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "lib_burst_generated.dll"
            path.write_bytes(b"0" * 128)
            with self.assertRaisesRegex(builder.ContractError, "not a PE image"):
                builder._pe_exports(path)

    def test_missing_burst_dll_fails_closed(self) -> None:
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
            with patch.object(builder, "check_installed_native_inputs", return_value=result):
                with self.assertRaisesRegex(builder.ContractError, "missing pinned lib_burst_generated"):
                    builder._native_gate(gameassembly, metadata)


if __name__ == "__main__":
    unittest.main()

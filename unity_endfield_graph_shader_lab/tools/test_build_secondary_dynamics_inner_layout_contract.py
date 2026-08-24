#!/usr/bin/env python3
"""Focused tests for the secondary-dynamics inner payload evidence gate."""

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

import build_secondary_dynamics_inner_layout_contract as builder


class SecondaryDynamicsInnerLayoutTests(unittest.TestCase):
    def test_published_contract_closes_selected_job_payload_and_fails_at_burst_boundary(self) -> None:
        payload = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema"], "endfield.charinfo.secondary-dynamics-inner-layout.v2")
        self.assertEqual(payload["status"], "selected_job_inner_payload_layout_closed_burst_mapping_unresolved")
        self.assertTrue(payload["inner_payload_layout_recovered"])
        self.assertTrue(payload["inner_payload_offsets_recovered"])
        self.assertTrue(payload["job_payload_layout_recovered"])
        self.assertIsNone(payload["nativeArray"]["nativeSizeBytes"])
        self.assertEqual(payload["nativeArray"]["selectedJobInstanceSizeBytes"], 16)
        self.assertEqual(payload["nativeArray"]["nativeSizeEvidence"]["selectedClosedSlotCount"], 59)
        self.assertEqual(payload["nativeArray"]["fields"]["m_Buffer"]["offset"], "0x0")
        self.assertEqual(payload["nativeArray"]["fields"]["m_Length"]["offset"], "0x8")
        self.assertEqual(payload["nativeArray"]["fields"]["m_AllocatorLabel"]["offset"], "0xc")
        self.assertEqual(payload["nativeReference"]["fields"]["m_Data"]["offset"], "0x0")
        self.assertEqual(payload["nativeReference"]["fields"]["m_AllocatorLabel"]["offset"], "0x8")
        self.assertIsNone(payload["nativeReference"]["nativeSizeBytes"])
        self.assertEqual(payload["nativeReference"]["selectedJobInstanceSizeBytes"], 16)
        self.assertEqual(payload["nativeReference"]["nativeSizeEvidence"]["payloadBytes"], 12)
        self.assertEqual(payload["nativeReference"]["nativeSizeEvidence"]["trailingPaddingBytes"], 4)
        self.assertFalse(payload["nativeReference"]["nativeSizeEvidence"]["paddingValueClaimed"])
        self.assertNotIn("padding", payload["nativeReference"]["fields"])
        self.assertEqual(
            payload["selectedJobSlotEvidence"]["closedSlotCounts"],
            {"NativeArray": 59, "NativeReference": 4},
        )
        self.assertEqual(payload["burstExports"]["mappingStatus"], "unresolved_wrapper_to_hashed_export")

    def test_job_slot_contract_hash_drift_fails_closed(self) -> None:
        with patch.object(builder, "EXPECTED_JOB_LAYOUT_SHA256", "0" * 64):
            with self.assertRaisesRegex(builder.ContractError, "outer job layout contract hash drift"):
                builder._closed_job_slot_evidence()

    def test_evidence_rejects_pattern_drift(self) -> None:
        class FakePe:
            def bytes_at_va(self, _va, size):
                return b"\x90" * size

            def file_offset_for_va(self, _va):
                return 0, ".text", 0

        with self.assertRaisesRegex(builder.ContractError, "lacks expected"):
            builder._evidence(FakePe(), 0x1000, "expected", (("expected", b"\xc3"),), 16, 0x1010)

    def test_evidence_rejects_unbounded_or_oversized_span(self) -> None:
        class FakePe:
            def bytes_at_va(self, _va, size):
                return b"\x90" * size

            def file_offset_for_va(self, _va):
                return 0, ".text", 0

        for size in (0, 257):
            with self.subTest(size=size):
                with self.assertRaisesRegex(builder.ContractError, "no bounded method span"):
                    builder._evidence(FakePe(), 0x1000, "bounded", (("nop", b"\x90"),), size, None)

    def test_export_parser_rejects_non_pe_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "lib_burst_generated.dll"
            path.write_bytes(b"0" * 128)
            with self.assertRaisesRegex(builder.ContractError, "not a PE image"):
                builder._exports(path)

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

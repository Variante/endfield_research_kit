#!/usr/bin/env python3
"""Focused tests for the fail-closed outer job layout contract."""

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
import build_secondary_dynamics_job_layout_contract as builder


class SecondaryDynamicsJobLayoutContractTests(unittest.TestCase):
    def test_current_contract_closes_only_outer_layout(self) -> None:
        observed = builder.build_contract()
        payload = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(observed, payload)
        self.assertEqual(payload["status"], "outer_job_layout_closed")
        self.assertTrue(payload["outer_job_layout_recovered"])
        self.assertFalse(payload["job_payload_layout_recovered"])
        self.assertFalse(payload["secondary_dynamics_verified"])
        self.assertEqual(len(payload["jobs"]), 4)
        start = next(row for row in payload["jobs"] if row["typeIndex"] == 48376)
        self.assertEqual(start["nativeSizeBytes"], 0x110)
        self.assertEqual(start["fields"][0]["nativePayloadOffset"], "0x0")
        self.assertEqual(start["fields"][-1]["nativePayloadOffset"], "0x100")
        self.assertEqual(start["setIndexCount"]["store"]["payloadOffset"], "0x100")
        basis = payload["layoutBasis"]["concreteGenericSlotWidths"]
        self.assertEqual(basis["status"], "closed_from_adjacent_offsets_and_native_size_tail")
        self.assertFalse(basis["genericTypeSizeClaimed"])
        for job in payload["jobs"]:
            for field in job["fields"]:
                if field["kind"] not in builder.GENERIC_FIELD_KINDS:
                    continue
                self.assertEqual(field["slotWidthBytes"], 16)
                evidence = field["slotWidthEvidence"]
                self.assertEqual(evidence["status"], "closed")
                self.assertEqual(evidence["slotSpanBytes"], 16)
                self.assertEqual(evidence["abiAlignmentBytes"], 8)
                self.assertTrue(evidence["abiAligned"])
                self.assertFalse(evidence["genericTypeSizeClaimed"])

    def test_generic_slot_width_is_derived_from_adjacent_boundary(self) -> None:
        width, evidence = builder._field_slot_evidence(
            name="array",
            kind="NativeArray",
            native_offset=0x10,
            next_native_offset=0x20,
            native_size=0x30,
            # Deliberately not used for generic fields.  The width must come
            # from the concrete job offsets, not a generic-size convention.
            declared_width=0x7FFFFFFF,
            next_field_name="next",
        )
        self.assertEqual(width, 16)
        self.assertEqual(evidence["basis"], "next_field_native_offset")
        self.assertEqual(evidence["slotSpanBytes"], 16)

    def test_final_reference_slot_width_uses_native_size_tail(self) -> None:
        width, evidence = builder._field_slot_evidence(
            name="_indexCount",
            kind="NativeReference",
            native_offset=0x100,
            next_native_offset=0x110,
            native_size=0x110,
            declared_width=1,
            next_field_name=None,
        )
        self.assertEqual(width, 16)
        self.assertEqual(evidence["basis"], "native_size_tail")
        self.assertEqual(evidence["nextNativePayloadOffset"], "0x110")

    def test_slot_alignment_drift_fails_closed(self) -> None:
        with self.assertRaisesRegex(builder.ContractError, "8-byte ABI alignment"):
            builder._field_slot_evidence(
                name="array",
                kind="NativeArray",
                native_offset=0x8,
                next_native_offset=0x1c,
                native_size=0x20,
                declared_width=16,
                next_field_name="next",
            )

    def test_missing_native_input_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / "missing"
            with self.assertRaisesRegex(builder.ContractError, "installed GameAssembly.dll"):
                builder.build_contract(game_assembly=missing, metadata=missing)

    def test_common_gate_is_called_with_explicit_overrides(self) -> None:
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

    def test_verifier_rejects_drifted_contract(self) -> None:
        payload = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        payload["jobs"][0]["fields"][0]["nativePayloadOffset"] = "0x10"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "drifted.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with patch.object(builder, "build_contract", return_value=json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))):
                import verify_secondary_dynamics_job_layout_contract as verifier
                with patch("sys.argv", ["verify", "--contract", str(path)]):
                    self.assertEqual(verifier.main(), 1)

    def test_setter_pattern_rejects_wrong_offset(self) -> None:
        class FakePe:
            def file_offset_for_va(self, _va):
                return 0, ".text", 0

            def bytes_at_va(self, _va, _size):
                return bytes.fromhex("488bf9488bda0f10030f118700000000c3")

        with self.assertRaisesRegex(builder.ContractError, "expected 0x100"):
            builder._setter_evidence(FakePe(), 0x100, 0x100)

    def test_setter_prologue_drift_is_rejected(self) -> None:
        class FakePe:
            def file_offset_for_va(self, _va):
                return 0, ".text", 0

            def bytes_at_va(self, _va, _size):
                return bytes.fromhex("488bf94890da0f10030f118700000000c3")

        with self.assertRaisesRegex(builder.ContractError, "exact this/argument prologue"):
            builder._setter_evidence(FakePe(), 0x100, 0)

    def test_setter_parameter_metadata_drift_is_rejected(self) -> None:
        method = SimpleNamespace(
            name_index=1,
            declaring_type=builder.JOBS[0]["typeIndex"],
            parameter_count=2,
        )

        class MethodTable:
            def __getitem__(self, _index):
                return method

        metadata = SimpleNamespace(
            methods=MethodTable(),
            string=lambda _index: "SetIndexCount",
            parameters_for=lambda _method: [SimpleNamespace(type_index=83617)],
        )
        with self.assertRaisesRegex(builder.ContractError, "parameter metadata drift"):
            builder._validate_setter_metadata(metadata, builder.JOBS[0])


if __name__ == "__main__":
    unittest.main()

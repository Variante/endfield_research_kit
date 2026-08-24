#!/usr/bin/env python3
"""Focused tests for the exact Endminf M28 VFXRefract gate."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("verify_endminf_refract_admission.py")
SPEC = importlib.util.spec_from_file_location("verify_endminf_refract_admission", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class VerifyEndminfRefractAdmissionTests(unittest.TestCase):
    def test_exact_pair_program_gate_and_fail_closed_admission(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "report.json"
            self.assertEqual(MODULE.main(True, output), 0)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                report["status"],
                "exact_program_pairs_validated_unity_admission_fail_closed",
            )
            self.assertEqual(len(report["programs"]), 4)
            self.assertTrue(report["admissionDecision"]["programEvidenceComplete"])
            self.assertTrue(report["admissionDecision"]["sourceMaterialComplete"])
            self.assertFalse(report["admissionDecision"]["admitted"])
            fragment_rows = [
                row for row in report["programs"] if row["stageFromDxbc"] == "fragment"
            ]
            self.assertEqual(len(fragment_rows), 2)
            for row in fragment_rows:
                self.assertEqual(
                    [(item["semantic"], item["index"]) for item in row["outputs"]],
                    [("SV_Target", 0), ("SV_Target", 1)],
                )
            self.assertTrue(
                all(report["fragmentContract"]["checks"].values())
            )
            self.assertEqual(len(report["runtimePrerequisites"]), 6)
            self.assertEqual(len(report["remainingGates"]), 4)
            self.assertGreaterEqual(len(report["currentUnityConsumer"]["gaps"]), 6)
            self.assertEqual(
                report["currentUnityConsumer"]["m28FixedValueEquivalence"]["status"],
                "closed_for_four_fragment_differences_only",
            )
            self.assertTrue(all(
                report["currentUnityConsumer"]["m28FixedValueEquivalence"]["checks"].values()
            ))

    def test_malformed_dxbc_is_rejected(self) -> None:
        with self.assertRaisesRegex(MODULE.VerificationError, "DXBC chunk table"):
            MODULE.chunks(b"DXBC" + b"\0" * 24 + (99).to_bytes(4, "little"))


if __name__ == "__main__":
    unittest.main()

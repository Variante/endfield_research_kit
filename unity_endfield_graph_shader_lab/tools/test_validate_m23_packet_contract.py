#!/usr/bin/env python3
"""Unit tests for the fail-closed M23 source-input evidence join."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_m23_packet_contract.py")
SPEC = importlib.util.spec_from_file_location("validate_m23_packet_contract", SCRIPT)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


ROOT = SCRIPT.parents[1]
CENSUS = ROOT / "scratch/character_recovery/lizhiyan_m23_packet_census/pts_40000.json"
ORACLE = ROOT / "scratch/character_recovery/lizhiyan_m23_source_mesh_oracle/pts_40000.json"
EXACT = ROOT / "tools/original_m23_dxbc_exact/build/m23_dxbc_validation.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class ValidateM23PacketContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.census = _load(CENSUS)
        cls.oracle = _load(ORACLE)
        cls.exact = _load(EXACT)

    def test_current_evidence_join_passes_without_visual_admission(self) -> None:
        result = M.validate_documents(self.census, self.oracle, self.exact)
        self.assertEqual(result["status"], "pass", result["summary"])
        self.assertEqual(result["summary"]["failed"], 0)
        self.assertEqual(result["admission"]["publicInputCensus"], True)
        self.assertFalse(result["admission"]["exactPackedRowParity"])
        self.assertFalse(result["admission"]["drawTimeCb3Available"])
        self.assertFalse(result["admission"]["visualAdmission"])
        self.assertEqual(result["admission"]["visualFidelityClaim"], 0)

    def test_color_hash_drift_reports_actionable_first_failure(self) -> None:
        oracle = copy.deepcopy(self.oracle)
        oracle["renderers"][0]["particles"][1]["bakedColorSegmentSha256"] = "00" * 32
        result = M.validate_documents(self.census, oracle, self.exact)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["summary"]["firstFailure"],
                         "color.P_fxui_lizhiyan_overview_start_04_2/xuanzhuan03.particle.1.bakedColorSegmentSha256")
        failure = next(row for row in result["checks"] if row["status"] == "fail")
        self.assertIn("expected", failure)
        self.assertIn("actual", failure)

    def test_admission_gate_drift_cannot_pass(self) -> None:
        census = copy.deepcopy(self.census)
        census["exactPackedRowParity"] = True
        result = M.validate_documents(census, self.oracle, self.exact)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["summary"]["firstFailure"], "census.exactPackedRowParity")

    def test_missing_exact_report_is_fail_closed(self) -> None:
        result = M.validate_documents(self.census, self.oracle, None)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["summary"]["firstFailure"], "input.exact.present")


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


PATH = Path(__file__).with_name("validate_m23_source_dxcap_capture.py")
SPEC = importlib.util.spec_from_file_location("m23_source_dxcap", PATH)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def runtime() -> dict:
    return {"schema": M.RUNTIME_SCHEMA, "status": "pass", "graphicsDeviceType": "Direct3D11", "applicationIsBatchMode": False, "sourceRendererSubmissionPath": True, "noBakeMeshContract": True, "noProxyContract": True, "exactIdentityClosed": True, "foregroundWindowRequested": True, "foregroundWindowHandleNonZero": True, "foregroundWindowIsWindow": True, "particleCount": 2}


def evidence(vs=3036, ps=3956, stride=60, exact=False) -> dict:
    return {"schema": M.DXCAP_SCHEMA, "draw_calls": [{"moment": 9, "draw_type": "DrawIndexed", "parameters": {"index_count": 3456}, "ia_vertex_buffers": [{"stride": stride}], "m23_candidate": {"vs_bytecode_length": vs, "ps_bytecode_length": ps, "exact_m23_candidate": exact}}]}


class Tests(unittest.TestCase):
    def test_source_baseline_passes_without_retail_claim(self):
        report = M.validate(runtime(), evidence())
        self.assertEqual(report["status"], "pass")
        self.assertIn("does not prove", report["claimBoundary"])

    def test_exact_candidate_is_rejected_from_source_baseline(self):
        report = M.validate(runtime(), evidence(10720, 8100, 136, True))
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["summary"]["firstFailure"], "dxcap.source_draw_unique")

    def test_hidden_window_fails_closed(self):
        row = runtime(); row["foregroundWindowIsWindow"] = False
        report = M.validate(row, evidence())
        self.assertEqual(report["summary"]["firstFailure"], "runtime.foregroundWindowIsWindow")


if __name__ == "__main__":
    unittest.main()

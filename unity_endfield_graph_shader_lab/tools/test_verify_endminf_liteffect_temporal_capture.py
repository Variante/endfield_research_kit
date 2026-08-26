#!/usr/bin/env python3

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).with_name(
    "verify_endminf_liteffect_temporal_capture.py")
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location(
    "endminf_liteffect_temporal_capture", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class EndminfLitEffectTemporalCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = MODULE.verify_session(MODULE.CAPTURE)

    def test_full_capture_and_exact_pair_counts_are_pinned(self) -> None:
        self.assertEqual(
            self.report["schema"],
            "endfield.endminf-liteffect-temporal-capture.v1")
        self.assertEqual(self.report["status"], "validated")
        self.assertEqual(self.report["counts"]["frames"], 38)
        self.assertEqual(self.report["counts"]["draws"], 157)
        self.assertEqual(self.report["counts"]["brightM01OrM27Draws"], 105)
        self.assertEqual(self.report["counts"]["lowM38Draws"], 52)
        self.assertAlmostEqual(
            self.report["frames"][0]["phaseSeconds"], 0.15, places=6)
        peak = next(row for row in self.report["frames"] if row["frame"] == 2978)
        self.assertAlmostEqual(peak["phaseSeconds"], 4.433333, places=6)

    def test_phase_structure_is_fail_closed(self) -> None:
        transition = next(
            row for row in self.report["frames"] if row["frame"] == 2970)
        self.assertEqual(transition["drawCount"], 0)
        for row in self.report["frames"]:
            if row["frame"] >= 2978:
                self.assertEqual(row["drawCount"], 1)
                self.assertEqual(
                    row["draws"][0]["psB3C29"]["classification"],
                    MODULE.BRIGHT_NAME)
        mutated = copy.deepcopy(self.report["frames"])
        late = next(row for row in mutated if row["frame"] == 2978)
        late["fingerprintCounts"] = {
            MODULE.BRIGHT_NAME: 0, MODULE.LOW_NAME: 1}
        with self.assertRaisesRegex(MODULE.CaptureError, "fingerprint counts"):
            MODULE.enforce_phase_structure(mutated)

    def test_all_draws_retain_topology_and_complete_constant_buffers(self) -> None:
        for frame in self.report["frames"]:
            for draw in frame["draws"]:
                self.assertEqual(draw["indexCount"] % 72, 0)
                self.assertEqual(draw["vertexCount"], draw["copies"] * 29)
                self.assertEqual(len(draw["constantBuffers"]), 8)
                self.assertEqual(len(draw["indexSha256"]), 64)
                self.assertEqual(len(draw["vertexSha256"]), 64)

    def test_source_uv_signature_is_observed_not_an_admission_gate(self) -> None:
        signatures = [
            draw["sourceUvSignature"]
            for frame in self.report["frames"] for draw in frame["draws"]
        ]
        self.assertIn(True, signatures)
        self.assertIn(False, signatures)
        self.assertEqual(
            self.report["counts"]["sourceUvSignatureTrue"]
            + self.report["counts"]["sourceUvSignatureFalse"], 157)

    def test_third_ps_b3_c29_fingerprint_is_rejected(self) -> None:
        with self.assertRaisesRegex(MODULE.CaptureError, "rejected fingerprint"):
            MODULE.classify_fingerprint(bytes(16), 2721, 0)


if __name__ == "__main__":
    unittest.main()

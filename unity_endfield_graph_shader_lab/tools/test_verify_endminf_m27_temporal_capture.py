#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).with_name("verify_endminf_m27_temporal_capture.py")
SPEC = importlib.util.spec_from_file_location("m27_temporal_capture", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class M27TemporalCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = MODULE.verify_session(MODULE.CAPTURE)

    def test_current_capture_closes_early_and_peak_packets(self) -> None:
        self.assertEqual(self.report["status"], "validated")
        self.assertEqual(self.report["sampleCount"], 16)
        early = next(row for row in self.report["frames"] if row["frame"] == 2905)
        peak = next(row for row in self.report["frames"] if row["frame"] == 2978)
        self.assertEqual(early["drawCount"], 4)
        self.assertEqual(early["binding"]["vertexStride"], 68)
        self.assertEqual([row["indexCount"] for row in early["draws"]], [72] * 4)
        self.assertEqual(peak["drawCount"], 1)
        self.assertEqual(peak["draws"][0]["indexCount"], 1080)
        self.assertEqual(peak["binding"]["vertexStride"], 60)

    def test_transition_sample_preserves_zero_m27_draws(self) -> None:
        transition = next(
            row for row in self.report["frames"] if row["frame"] == 2970)
        self.assertEqual(transition["drawCount"], 0)
        self.assertEqual(transition["draws"], [])

    def test_effective_ia_slices_are_hash_pinned(self) -> None:
        for frame in self.report["frames"]:
            for draw in frame["draws"]:
                self.assertEqual(len(draw["vertexSha256"]), 64)
                self.assertEqual(len(draw["indexSha256"]), 64)
                self.assertEqual(len(draw["constantBuffers"]), 8)


if __name__ == "__main__":
    unittest.main()

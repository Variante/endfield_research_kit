#!/usr/bin/env python3
"""Focused tests for the exact Endminf VFXBaseV2 peak cohort builder."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "build_endminf_vfxbasev2_peak_cohort",
    HERE / "build_endminf_vfxbasev2_peak_cohort.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class VFXBaseV2PeakCohortTests(unittest.TestCase):
    def test_authoritative_capture_builds_complete_ordered_cohort(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cs, cpp = MODULE.build(
                MODULE.CAPTURE, MODULE.REPORT, root / "data.cs", root / "data.h")
        self.assertIn("DrawCount = 15", cs)
        self.assertIn("TextureCount = 5", cs)
        self.assertIn(
            "DrawOrdinals = { 68, 74, 75, 76, 77, 78, 79, 80, 81, 83, 84, 85, 86, 87, 88 }",
            cs)
        self.assertIn(
            "IndexCounts = { 6, 6, 6, 6, 12, 240, 144, 12, 6, 6, 6, 6, 6, 12, 18 }",
            cs)
        self.assertIn("g_EndfieldVFXPeakDrawCount", cpp)
        self.assertIn("g_EndfieldVFXPeakTextureCount", cpp)
        self.assertIn("g_EndfieldVFXPeakPayloadPrepared = true", cpp)

    def test_report_hash_gate_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / "report.json"
            report.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "report hash drifted"):
                MODULE.collect(MODULE.CAPTURE, report)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).with_name("compare_endminf_dense_window.py")
SPEC = importlib.util.spec_from_file_location("compare_endminf_dense_window", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class DenseWindowComparisonTests(unittest.TestCase):
    def test_sheet_indices_are_bounded_for_short_probe(self) -> None:
        self.assertEqual(MODULE.sheet_indices(10), [0, 2, 4, 6, 8, 9])

    def test_sheet_indices_preserve_established_dense_cadence(self) -> None:
        self.assertEqual(
            MODULE.sheet_indices(16), [0, 2, 4, 6, 8, 10, 12, 14, 15])

    def test_empty_probe_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "no recovered frames"):
            MODULE.sheet_indices(0)

    def test_source_frame_uses_measured_body_phase(self) -> None:
        source_frame, body_phase, error = MODULE.source_frame_from_body_phase(
            {
                "requestedSeconds": 4.35,
                "activeBodyClipTime": 4.384253502,
            },
            {
                "bodyClipStartSourceFrame": 91,
                "bodyClipPhaseSeconds": 0.05090830227,
            },
            60.0,
        )
        self.assertEqual(source_frame, 351)
        self.assertAlmostEqual(body_phase, 4.384253502)
        self.assertLess(abs(error), 0.001)

    def test_source_anchor_phase_maps_to_anchor_frame(self) -> None:
        source_frame, _, error = MODULE.source_frame_from_body_phase(
            {"activeBodyClipTime": 0.05090830227},
            {
                "bodyClipStartSourceFrame": 91,
                "bodyClipPhaseSeconds": 0.05090830227,
            },
            60.0,
        )
        self.assertEqual(source_frame, 91)
        self.assertEqual(error, 0.0)

    def test_missing_body_phase_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing activeBodyClipTime"):
            MODULE.source_frame_from_body_phase(
                {"requestedSeconds": 4.35},
                {
                    "bodyClipStartSourceFrame": 91,
                    "bodyClipPhaseSeconds": 0.05090830227,
                },
                60.0,
            )


if __name__ == "__main__":
    unittest.main()

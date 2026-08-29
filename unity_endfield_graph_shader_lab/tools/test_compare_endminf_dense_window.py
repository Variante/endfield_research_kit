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

    def test_sequence_mapping_stays_chronological_across_loop_reset(self) -> None:
        mappings = MODULE.source_frames_from_sequence_elapsed(
            [
                {
                    "actualSeconds": 0.05,
                    "activeBodyClip": "A_actor_endminf_ui_overview_start",
                    "activeBodyClipTime": 0.05,
                },
                {
                    "actualSeconds": 5.05,
                    "activeBodyClip": "A_actor_endminf_ui_overview_start",
                    "activeBodyClipTime": 5.05,
                },
                {
                    "actualSeconds": 5.0666666667,
                    "activeBodyClip": "A_actor_endminf_ui_overview_loop",
                    "activeBodyClipTime": 0.7333333333,
                },
                {
                    "actualSeconds": 7.15,
                    "activeBodyClip": "A_actor_endminf_ui_overview_loop",
                    "activeBodyClipTime": 0.7333333333,
                },
            ],
            {
                "bodyClipStartSourceFrame": 91,
                "bodyClipPhaseSeconds": 0.05,
            },
            60.0,
        )
        self.assertEqual([row[0] for row in mappings], [91, 391, 392, 517])
        self.assertTrue(all(row[3] == "start_anchor_elapsed" for row in mappings))

    def test_independent_loop_anchor_uses_elapsed_time_after_transition(self) -> None:
        mappings = MODULE.source_frames_from_sequence_elapsed(
            [
                {
                    "actualSeconds": 0.05,
                    "activeBodyClip": "A_actor_endminf_ui_overview_start",
                    "activeBodyClipTime": 0.05,
                },
                {
                    "actualSeconds": 5.05,
                    "activeBodyClip": "A_actor_endminf_ui_overview_loop",
                    "activeBodyClipTime": 0.75,
                },
                {
                    "actualSeconds": 7.1333333333,
                    "activeBodyClip": "A_actor_endminf_ui_overview_loop",
                    "activeBodyClipTime": 0.75,
                },
            ],
            {
                "bodyClipStartSourceFrame": 91,
                "bodyClipPhaseSeconds": 0.05,
                "loopClipStartSourceFrame": 350,
                "loopClipPhaseSeconds": 0.0,
            },
            60.0,
        )
        self.assertEqual([row[0] for row in mappings], [91, 395, 520])
        self.assertEqual(
            [row[3] for row in mappings],
            ["start_anchor_elapsed", "loop_anchor_elapsed", "loop_anchor_elapsed"],
        )

    def test_partial_loop_anchor_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "incomplete loop-clip anchor"):
            MODULE.source_frames_from_sequence_elapsed(
                [{
                    "actualSeconds": 0.05,
                    "activeBodyClip": "A_actor_endminf_ui_overview_start",
                    "activeBodyClipTime": 0.05,
                }],
                {
                    "bodyClipStartSourceFrame": 91,
                    "bodyClipPhaseSeconds": 0.05,
                    "loopClipStartSourceFrame": 350,
                },
                60.0,
            )

    def test_loop_only_diagnostic_accepts_explicit_sequence_origin(self) -> None:
        mappings = MODULE.source_frames_from_sequence_elapsed(
            [
                {
                    "actualSeconds": 7.2166666667,
                    "activeBodyClip": "A_actor_endminf_ui_overview_loop",
                    "activeBodyClipTime": 0.7675893,
                },
                {
                    "actualSeconds": 7.2333333333,
                    "activeBodyClip": "A_actor_endminf_ui_overview_loop",
                    "activeBodyClipTime": 0.7842560,
                },
            ],
            {
                "bodyClipStartSourceFrame": 91,
                "bodyClipPhaseSeconds": 0.05090830227,
            },
            60.0,
            sequence_origin_actual_seconds=0.0166666667,
            sequence_origin_source_frame=91,
        )
        self.assertEqual([row[0] for row in mappings], [523, 524])
        self.assertTrue(
            all(row[3] == "explicit_sequence_origin" for row in mappings)
        )

    def test_partial_explicit_sequence_origin_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires both"):
            MODULE.source_frames_from_sequence_elapsed(
                [{
                    "actualSeconds": 7.2166666667,
                    "activeBodyClip": "A_actor_endminf_ui_overview_loop",
                    "activeBodyClipTime": 0.7675893,
                }],
                {
                    "bodyClipStartSourceFrame": 91,
                    "bodyClipPhaseSeconds": 0.05090830227,
                },
                60.0,
                sequence_origin_actual_seconds=0.0166666667,
            )


if __name__ == "__main__":
    unittest.main()

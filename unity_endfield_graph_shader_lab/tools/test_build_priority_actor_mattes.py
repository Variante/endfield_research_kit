"""Focused contract tests for build_priority_actor_mattes.py."""

from __future__ import annotations

import unittest

import numpy as np

import build_priority_actor_mattes as matte


class PriorityActorMatteTests(unittest.TestCase):
    def test_exact_priority_windows_are_frame_aligned(self) -> None:
        chen = matte._actor_window("chen")
        pelica = matte._actor_window("pelica")
        self.assertEqual((chen.start_frame, chen.end_frame_exclusive), (11958, 12560))
        self.assertEqual((pelica.start_frame, pelica.end_frame_exclusive), (12560, 13237))
        self.assertEqual(chen.end_frame_exclusive, pelica.start_frame)

    def test_hard_exclusions_zero_every_ui_rectangle(self) -> None:
        mask = np.full((matte.EXPECTED_SIZE[1], matte.EXPECTED_SIZE[0]), 255, np.uint8)
        constrained = matte.apply_hard_exclusions(mask)
        self.assertEqual(matte._ui_overlap_pixels(constrained), 0)
        x0, y0, x1, y1 = matte.ACTOR_ROI
        self.assertEqual(int(np.count_nonzero(constrained[:y0])), 0)
        self.assertEqual(int(np.count_nonzero(constrained[y1:])), 0)
        self.assertGreater(int(np.count_nonzero(constrained[y0:y1, x0:x1])), 0)

    def test_contiguous_ranges_are_deterministic(self) -> None:
        self.assertEqual(list(matte._contiguous_ranges([4, 3, 2, 9, 10, 12])), [(2, 4), (9, 10), (12, 12)])
        self.assertEqual(list(matte._contiguous_ranges([])), [])

    def test_source_pin_is_not_replaced_by_name_only(self) -> None:
        self.assertEqual(matte.VIDEO_RELATIVE.as_posix(), "videos/2026-08-15_10-32-32.mkv")
        self.assertEqual(len(matte.VIDEO_SHA256), 64)
        self.assertEqual(matte.VIDEO_BYTES, 1678613397)


if __name__ == "__main__":
    unittest.main()

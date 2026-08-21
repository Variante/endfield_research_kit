"""Focused contract tests for build_priority_actor_mattes.py."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile

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

    def test_header_underline_boundaries_are_hard_excluded(self) -> None:
        mask = np.zeros((matte.EXPECTED_SIZE[1], matte.EXPECTED_SIZE[0]), np.uint8)
        mask[182, 1000] = 255
        mask[183:188, 1000] = 255
        mask[188, 1000] = 255
        constrained = matte.apply_hard_exclusions(mask)
        self.assertEqual(int(constrained[182, 1000]), 255)
        self.assertEqual(int(np.count_nonzero(constrained[183:188, 1000])), 0)
        self.assertEqual(int(constrained[188, 1000]), 255)

    def test_transition_interval_is_explicit_and_actor_specific(self) -> None:
        window = matte._actor_window("pelica")
        expected = list(range(12560, 12602))
        self.assertEqual(matte._expected_transition_frames("pelica", window), expected)
        self.assertTrue(matte._expected_transition_frame("pelica", 12560))
        self.assertTrue(matte._expected_transition_frame("pelica", 12601))
        self.assertFalse(matte._expected_transition_frame("pelica", 12602))
        self.assertFalse(matte._expected_transition_frame("chen", 12560))

    def test_temporal_iou_accepts_small_motion_and_rejects_disjoint_mask(self) -> None:
        prior = np.zeros((matte.WORK_SIZE[1], matte.WORK_SIZE[0]), np.uint8)
        prior[70:180, 160:230] = 255
        shifted = np.zeros_like(prior)
        shifted[70:180, 163:233] = 255
        disjoint = np.zeros_like(prior)
        disjoint[70:180, 300:370] = 255
        self.assertFalse(matte._temporal_metrics(shifted, prior)["temporalFailure"])
        self.assertTrue(matte._temporal_metrics(disjoint, prior)["temporalFailure"])

    def test_detached_component_is_a_purity_failure(self) -> None:
        mask = np.zeros((matte.WORK_SIZE[1], matte.WORK_SIZE[0]), np.uint8)
        mask[70:190, 150:230] = 255
        mask[50:100, 330:360] = 255
        _selected, diagnostics = matte._select_person_components(mask, None)
        self.assertEqual(diagnostics["detachedComponentCount"], 1)
        self.assertTrue(diagnostics["purityFailure"])

    def test_ffv1_metadata_gate_requires_actual_codec_and_pix_fmt(self) -> None:
        good = {
            "codec_name": "ffv1", "pix_fmt": "bgr0", "width": 3840,
            "height": 2160, "avg_frame_rate": "0/0", "r_frame_rate": "60/1", "nb_read_frames": 677,
        }
        normalized = matte._validate_encoded_metadata(good, 677)
        self.assertEqual(normalized["pix_fmt"], "bgr0")
        self.assertEqual(normalized["fps"], 60.0)
        for field, value in (("codec_name", "h264"), ("pix_fmt", "bgr24"), ("nb_read_frames", 676)):
            bad = dict(good)
            bad[field] = value
            with self.assertRaises(matte.MatteError):
                matte._validate_encoded_metadata(bad, 677)
        bad_rate = dict(good)
        bad_rate["r_frame_rate"] = "0/0"
        bad_rate["tags"] = {"DURATION": "00:00:11.283333333"}
        self.assertEqual(matte._validate_encoded_metadata(bad_rate, 677)["fpsEvidence"], "frame_count_over_duration")
        bad_rate["tags"] = {"DURATION": "00:00:00"}
        with self.assertRaises(matte.MatteError):
            matte._validate_encoded_metadata(bad_rate, 677)

    def test_discontinuous_rows_fail_closed(self) -> None:
        with self.assertRaises(matte.MatteError):
            matte._validate_contiguous_frame_rows(
                [{"frame": 10}, {"frame": 12}], 10, 13, "pelica"
            )

    def test_stale_report_path_and_schema_fail_closed(self) -> None:
        with NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            handle.write('{"schema":"wrong","status":"ok"}')
            path = Path(handle.name)
        try:
            with self.assertRaises(matte.MatteError):
                matte.check_manifest(path)
        finally:
            path.unlink(missing_ok=True)
        with self.assertRaises(matte.MatteError):
            matte._resolve_repo_relative("../outside.json", "stale report")

    def test_source_and_weight_hash_gates_fail_closed(self) -> None:
        source = {
            "path": matte.VIDEO_RELATIVE.as_posix(),
            "bytes": matte.VIDEO_BYTES,
            "sha256": "0" * 64,
            "width": 3840,
            "height": 2160,
            "fps": 60.0,
        }
        report = {
            "schema": matte.MANIFEST_SCHEMA,
            "status": "ok",
            "pathBase": "repo_root",
            "source": source,
            "algorithm": {"name": "deeplabv3_resnet50_person_class_with_hard_ui_exclusions", "modelWeightsSha256": matte.DEEPLAB_WEIGHT_SHA256},
        }
        with self.assertRaises(matte.MatteError):
            matte._check_manifest_data(report, Path("manifest.json"))
        source["sha256"] = matte.VIDEO_SHA256
        report["algorithm"]["modelWeightsSha256"] = "0" * 64
        with self.assertRaises(matte.MatteError):
            matte._check_manifest_data(report, Path("manifest.json"))

    def test_publication_gates_expose_temporal_purity_and_ui_failures(self) -> None:
        report = {
            "actor": "pelica",
            "transitionFrameRanges": [[12560, 12601]],
            "temporalContinuityFailureCount": 0,
            "componentPurityFailureCount": 0,
            "componentLossFrameCount": 0,
            "rowsContiguous": True,
            "uiOverlapPixels": 0,
            "encoded": {"codec": "ffv1", "pix_fmt": "bgr0"},
        }
        gates = matte._manifest_publication_gates([report])
        self.assertTrue(gates["temporalContinuity"])
        self.assertTrue(gates["componentPurity"])
        report["componentPurityFailureCount"] = 1
        report["uiOverlapPixels"] = 3
        gates = matte._manifest_publication_gates([report])
        self.assertFalse(gates["componentPurity"])
        self.assertFalse(gates["uiExclusionZero"])
        self.assertEqual(gates["uiOverlapPixels"], 3)

    def test_contiguous_ranges_are_deterministic(self) -> None:
        self.assertEqual(list(matte._contiguous_ranges([4, 3, 2, 9, 10, 12])), [(2, 4), (9, 10), (12, 12)])
        self.assertEqual(list(matte._contiguous_ranges([])), [])

    def test_source_pin_is_not_replaced_by_name_only(self) -> None:
        self.assertEqual(matte.VIDEO_RELATIVE.as_posix(), "videos/2026-08-15_10-32-32.mkv")
        self.assertEqual(len(matte.VIDEO_SHA256), 64)
        self.assertEqual(matte.VIDEO_BYTES, 1678613397)


if __name__ == "__main__":
    unittest.main()

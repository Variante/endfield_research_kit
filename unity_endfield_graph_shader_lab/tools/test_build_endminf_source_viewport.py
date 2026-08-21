import unittest
import json

import numpy as np

import build_endminf_source_viewport as viewport


class EndminfSourceViewportTests(unittest.TestCase):
    def test_crop_is_exact_source_viewport_and_outer_ui_safe(self) -> None:
        contract = viewport._assert_crop_contract()
        self.assertEqual(contract["sourceCropHalfOpen"], [800, 188, 3000, 2120])
        self.assertEqual(contract["outputSize"], [2200, 1932])
        self.assertEqual(contract["knownOuterUiOverlapPixels"], 0)

    def test_phase_ranges_cover_exact_requested_frames(self) -> None:
        self.assertEqual(viewport.PHASE_RANGES["start"], (9783, 10028))
        self.assertEqual(viewport.PHASE_RANGES["transition"], (10029, 10116))
        self.assertEqual(viewport.PHASE_RANGES["clean_loop"], (10117, 10409))
        rows = [frame for start, end in viewport.PHASE_RANGES.values() for frame in range(start, end + 1)]
        self.assertEqual(rows, list(range(9783, 10410)))
        self.assertEqual(len(rows), 627)

    def test_cursor_protection_is_invalid_not_synthesized(self) -> None:
        mask = viewport._cursor_mask()
        self.assertEqual(mask.shape, (1932, 2200))
        self.assertEqual(int(np.count_nonzero(mask == 0)), 36 * 36)
        self.assertEqual(int(np.count_nonzero(mask == 255)), 1932 * 2200 - 36 * 36)
        x0, y0, x1, y1 = viewport.CURSOR_PROTECTION_RELATIVE
        self.assertEqual((x0, y0, x1, y1), (1734, 690, 1770, 726))
        # The mask does not carry a replacement RGB value or an alpha claim.
        self.assertEqual(set(np.unique(mask)), {0, 255})

    def test_cursor_detector_pin_cannot_be_silently_disabled(self) -> None:
        raw = np.zeros((viewport.CROP_HEIGHT, viewport.CROP_WIDTH, 4), dtype=np.uint8)
        detected, facts = viewport._cursor_detected(raw.tobytes())
        self.assertFalse(detected)
        self.assertEqual(facts["grayAtLeast230"], 0)
        self.assertEqual(facts["grayAtLeast245"], 0)

    def test_no_ui_visualization_marks_only_invalid_cursor_region(self) -> None:
        raw_array = np.zeros((viewport.CROP_HEIGHT, viewport.CROP_WIDTH, 4), dtype=np.uint8)
        raw_array[:, :, :3] = (7, 11, 13)
        raw = raw_array.tobytes()
        marked = np.frombuffer(viewport._no_ui_visualization(raw), dtype=np.uint8).reshape(raw_array.shape)
        x0, y0, x1, y1 = viewport.CURSOR_PROTECTION_RELATIVE
        self.assertTrue(np.array_equal(marked[:y0, :, :3], raw_array[:y0, :, :3]))
        self.assertTrue(np.array_equal(marked[y1:, :, :3], raw_array[y1:, :, :3]))
        self.assertTrue(np.array_equal(marked[y0:y1, :x0, :3], raw_array[y0:y1, :x0, :3]))
        self.assertTrue(np.array_equal(marked[y0:y1, x1:, :3], raw_array[y0:y1, x1:, :3]))
        colors = {tuple(color) for color in np.unique(marked[y0:y1, x0:x1, :3].reshape(-1, 3), axis=0)}
        self.assertEqual(colors, {(0, 0, 0), (255, 0, 255)})

    def test_pixel_policy_never_claims_clean_no_ui_or_complete_silhouette(self) -> None:
        self.assertEqual(viewport.PIXEL_POLICY, "exact_decoded_source_crop_no_segmentation_no_compositing_no_inpainting")
        self.assertEqual(viewport.CURSOR_PROTECTION_RELATIVE, (1734, 690, 1770, 726))
        self.assertNotEqual(viewport.CURSOR_PROTECTION, (0, 0, 0, 0))

    def test_durable_report_exposes_masked_status_and_rejects_clean_claim(self) -> None:
        report = json.loads(viewport.REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "published_with_invalid_ui_mask")
        self.assertFalse(report["publicationGates"]["noUiClaim"])
        self.assertFalse(report["publicationGates"]["completeSilhouetteClaim"])
        overlay = report["uiValidity"]["knownPersistentOverlays"][0]
        self.assertEqual(overlay["sourceBox"], [2534, 878, 2570, 914])
        self.assertEqual(overlay["cropBox"], [1734, 690, 1770, 726])
        self.assertEqual(overlay["detectedFrames"], 627)
        self.assertEqual(overlay["actorIntersectionFrameCount"], 192)

    def test_report_rows_pin_source_mapping_and_cursor_hashes(self) -> None:
        report = json.loads(viewport.REPORT_PATH.read_text(encoding="utf-8"))
        rows = report["frames"]
        self.assertEqual(len(rows), 627)
        self.assertEqual([row["sourceFrame"] for row in rows], list(range(9783, 10410)))
        self.assertTrue(all(len(row["cropSha256"]) == 64 for row in rows))
        self.assertTrue(all(len(row["cursorCoreSha256"]) == 64 for row in rows))
        self.assertTrue(all(row["invalidPixels"] == 1296 for row in rows))


if __name__ == "__main__":
    unittest.main()

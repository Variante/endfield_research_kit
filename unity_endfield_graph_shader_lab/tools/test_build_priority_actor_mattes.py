"""Focused contract tests for build_priority_actor_mattes.py."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import patch

import numpy as np

import build_priority_actor_mattes as matte


class PriorityActorMatteTests(unittest.TestCase):
    def test_exact_priority_windows_are_frame_aligned(self) -> None:
        endminf = matte._actor_window("endminf")
        chen = matte._actor_window("chen")
        pelica = matte._actor_window("pelica")
        self.assertEqual((endminf.start_frame, endminf.end_frame_exclusive), (9767, 10500))
        self.assertEqual((chen.start_frame, chen.end_frame_exclusive), (11958, 12560))
        self.assertEqual((pelica.start_frame, pelica.end_frame_exclusive), (12560, 13237))
        self.assertEqual(chen.end_frame_exclusive, pelica.start_frame)

    def test_endminf_requires_exact_identity_evidence_and_has_no_gap_exemption(self) -> None:
        evidence = matte._endminf_identity_evidence()
        self.assertEqual(evidence["path"], "unity_endfield_graph_shader_lab/tools/endminf_video_identity_evidence.json")
        self.assertEqual(len(evidence["sha256"]), 64)
        window = matte._actor_window("endminf")
        self.assertEqual(
            matte._expected_transition_frames("endminf", window),
            list(range(9767, 9783)) + list(range(10410, 10500)),
        )
        self.assertEqual(matte._transition_contract("endminf")[1], 9783)

    def test_endminf_candidate_matrix_hostile_mutations_fail_closed(self) -> None:
        source_path = matte.REPO_ROOT / matte.ENDMINF_IDENTITY_EVIDENCE_RELATIVE
        base = json.loads(source_path.read_text(encoding="utf-8"))
        mutations = {
            "target_score": lambda value: value["identity"]["candidateMatrix"].__setitem__("targetScore", 0.79),
            "camera_hash": lambda value: value["identity"]["candidateMatrix"]["comparisonContract"]["cameraContract"].__setitem__("sha256", "0" * 64),
            "competitor_count": lambda value: value["identity"]["candidateMatrix"].__setitem__("comparableCompetitorCount", 0),
            "comparable_list": lambda value: value["identity"]["candidateMatrix"].__setitem__("comparableCompetitors", []),
            "target_margin": lambda value: value["identity"]["candidateMatrix"].__setitem__("targetMargin", 1.0),
            "competitor_availability": lambda value: value["identity"]["candidateMatrix"]["candidates"][3]["render"].__setitem__("available", False),
            "competitor_score_null": lambda value: value["identity"]["candidateMatrix"]["candidates"][3]["render"].__setitem__("score", None),
            "rejection_reason": lambda value: value["identity"]["candidateMatrix"]["candidates"][3].__setitem__("rejection", "mutated rejection"),
            "candidate_asset_path": lambda value: value["identity"]["candidateMatrix"]["candidates"][0]["sourceAssets"]["prefab"].__setitem__("path", "stale.prefab"),
            "candidate_asset_hash": lambda value: value["identity"]["candidateMatrix"]["candidates"][0]["sourceAssets"]["manifest"].__setitem__("sha256", "0" * 64),
            "status": lambda value: value["identity"].__setitem__("status", "candidate"),
            "combined_window": lambda value: value["phase"]["combinedActorWindow"]["frameRangeExclusive"].__setitem__(0, 9768),
            "source_transition_ranges": lambda value: value["phase"]["sourceTransition"]["frameRangesInclusive"].__setitem__(0, [9767, 9781]),
            "source_transition_reason": lambda value: value["phase"]["sourceTransition"].__setitem__("reason", "mutated transition reason"),
            "first_gap_mask_row_frame": lambda value: value["phase"]["sourceTransition"]["perFramePinnedDeepLabScan"]["rows"][0].__setitem__("frame", 9768),
            "first_gap_mask_row_pixels": lambda value: value["phase"]["sourceTransition"]["perFramePinnedDeepLabScan"]["rows"][0].__setitem__("workMaskPixels", 1),
            "deep_lab_weight_hash": lambda value: value["phase"]["sourceTransition"]["perFramePinnedDeepLabScan"].__setitem__("weightSha256", "0" * 64),
            "tail_classification": lambda value: value["phase"]["tailTransition"].__setitem__("classification", "mutated_tail_policy"),
            "tail_next_boundary": lambda value: value["phase"]["tailTransition"].__setitem__("nextSegmentBoundaryFrame", 10499),
            "tail_following_identity": lambda value: value["phase"]["tailTransition"].__setitem__("followingActorIdentity", "chr_0007_ikut"),
            "tail_frame_number": lambda value: value["phase"]["tailTransition"]["perFrame"][0].__setitem__("frame", 10411),
            "tail_frame_hash": lambda value: value["phase"]["tailTransition"]["perFrame"][0].__setitem__("bgrSha256", "0" * 64),
            "tail_frame_stats": lambda value: value["phase"]["tailTransition"]["perFrame"][0].__setitem__("characterBandMean", 0.0),
            "tail_frame_classification": lambda value: value["phase"]["tailTransition"]["perFrame"][0].__setitem__("classification", "mutated_tail_frame"),
            "clean_loop_duration": lambda value: value["phase"]["cleanLoop"].__setitem__("durationSeconds", 1.0),
            "clean_loop_status": lambda value: value["phase"]["cleanLoop"].__setitem__("publicationStatus", "published"),
            "clean_loop_cycles": lambda value: value["phase"]["cleanLoop"].__setitem__("completeRuntimePeriods", 1),
            "source_hash": lambda value: value["source"].__setitem__("sha256", "0" * 64),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                candidate = copy.deepcopy(base)
                mutate(candidate)
                with NamedTemporaryFile("w", suffix=".json", dir=matte.PROJECT_ROOT / "tools", delete=False) as handle:
                    handle.write(json.dumps(candidate))
                    temp_path = Path(handle.name)
                try:
                    relative = temp_path.resolve().relative_to(matte.REPO_ROOT.resolve())
                    with patch.object(matte, "ENDMINF_IDENTITY_EVIDENCE_RELATIVE", relative):
                        with self.assertRaises(matte.MatteError):
                            matte._endminf_identity_evidence()
                finally:
                    temp_path.unlink(missing_ok=True)

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

        chen = matte._actor_window("chen")
        self.assertEqual(
            matte._expected_transition_frames("chen", chen),
            list(range(11958, 11970)),
        )
        self.assertTrue(matte._expected_transition_frame("chen", 11958))
        self.assertTrue(matte._expected_transition_frame("chen", 11969))
        self.assertFalse(matte._expected_transition_frame("chen", 11970))

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

    def test_enclosed_component_without_temporal_evidence_is_rejected(self) -> None:
        # A current-frame bounding box alone is not actor proof: an island
        # inside the torso envelope still needs prior/next temporal evidence.
        mask = np.zeros((matte.WORK_SIZE[1], matte.WORK_SIZE[0]), np.uint8)
        mask[70:90, 150:230] = 255
        mask[90:170, 150:170] = 255
        mask[90:170, 210:230] = 255
        mask[170:190, 150:230] = 255
        mask[120:140, 180:200] = 255
        selected, diagnostics = matte._select_person_components(mask, None)
        self.assertEqual(diagnostics["detachedComponentCount"], 1)
        self.assertTrue(diagnostics["purityFailure"])
        self.assertEqual(int(np.count_nonzero(selected[120:140, 180:200])), 0)

    def test_temporally_overlapping_component_is_retained(self) -> None:
        prior = np.zeros((matte.WORK_SIZE[1], matte.WORK_SIZE[0]), np.uint8)
        prior[70:190, 150:230] = 255
        mask = np.zeros_like(prior)
        mask[70:190, 150:215] = 255
        # This actor limb enters immediately beside the prior torso envelope;
        # it is disconnected at work resolution but has temporal bbox proof.
        mask[155:190, 220:260] = 255
        selected, diagnostics = matte._select_person_components(mask, prior)
        self.assertEqual(diagnostics["detachedComponentCount"], 0)
        self.assertFalse(diagnostics["purityFailure"])
        self.assertGreater(int(np.count_nonzero(selected[155:190, 220:260])), 0)

    def test_next_frame_support_retains_boundary_actor_component(self) -> None:
        current = np.zeros((matte.WORK_SIZE[1], matte.WORK_SIZE[0]), np.uint8)
        current[50:180, 150:230] = 255
        current[220:270, 220:270] = 255
        future = np.zeros_like(current)
        future[50:180, 150:230] = 255
        future[215:270, 218:272] = 255
        selected, diagnostics = matte._select_person_components(current, None, future)
        self.assertEqual(diagnostics["detachedComponentCount"], 0)
        self.assertFalse(diagnostics["purityFailure"])
        self.assertGreater(int(np.count_nonzero(selected[220:270, 220:270])), 0)

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

    def test_audit_report_rechecks_manifest_source_weight_and_artifact_identity(self) -> None:
        report_path = matte.PROJECT_ROOT / "tools" / "actor_matte_report.json"
        base = json.loads(report_path.read_text(encoding="utf-8"))
        matte._check_audit_report(base, report_path)
        mutations = {
            "source_sha256": lambda value: value["source"].__setitem__("sha256", "0" * 64),
            "source_timeline_count": lambda value: value["source"].__setitem__("timelineFrameCount", matte.EXPECTED_TIMELINE_FRAME_COUNT + 1),
            "source_decoded_count": lambda value: value["source"].__setitem__("decodedFrameCount", matte.EXPECTED_DECODED_FRAME_COUNT + 1),
            "source_packet_count": lambda value: value["source"].__setitem__("packetCount", matte.EXPECTED_PACKET_COUNT + 1),
            "source_count_relationship": lambda value: value["source"].__setitem__("decodedFrameCount", value["source"]["timelineFrameCount"]),
            "source_stale_legacy_frame_count": lambda value: value["source"].__setitem__("frameCount", matte.EXPECTED_TIMELINE_FRAME_COUNT),
            "weight_sha256": lambda value: value["algorithm"].__setitem__("modelWeightsSha256", "0" * 64),
            "artifact_pix_fmt": lambda value: value["artifacts"][0].__setitem__("pix_fmt", "bgr24"),
            "artifact_codec": lambda value: value["artifacts"][0].__setitem__("codec", "h264"),
            "artifact_frames": lambda value: value["artifacts"][0].__setitem__("frames", 676),
            "requested_windows": lambda value: value["requestedWindows"]["pelica"]["framesExclusive"].__setitem__(0, 12561),
            "excluded_actors": lambda value: value["excludedActors"].append(
                {"actor": "pelica", "reason": "mutated exclusion"}
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                candidate = copy.deepcopy(base)
                mutate(candidate)
                with self.assertRaises(matte.MatteError):
                    matte._check_audit_report(candidate, report_path)

    def test_manifest_rechecks_actor_transition_top_level_contract(self) -> None:
        manifest_path = matte.PROJECT_ROOT / "scratch" / "character_recovery" / "actor_clips" / "actor_matte_manifest.json"
        base = json.loads(manifest_path.read_text(encoding="utf-8"))
        matte._check_manifest_data(base, manifest_path)
        mutations = {
            "transition_frame_count": lambda value: value.__setitem__(
                "transitionFrameCount", value["transitionFrameCount"] + 1
            ),
            "transition_reason": lambda value: value.__setitem__(
                "transitionReason", "mutated transition evidence"
            ),
            "transition_range": lambda value: value.__setitem__(
                "transitionRangeInclusive", [11958, 11968]
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                candidate = copy.deepcopy(base)
                actor = next(item for item in candidate["actors"] if item["actor"] == "chen")
                mutate(actor)
                with self.assertRaises(matte.MatteError):
                    matte._check_manifest_data(candidate, manifest_path)

    def test_manifest_rechecks_requested_windows_and_excluded_actors(self) -> None:
        manifest_path = matte.PROJECT_ROOT / "scratch" / "character_recovery" / "actor_clips" / "actor_matte_manifest.json"
        base = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(base["actorSet"], ["chen", "endminf", "pelica"])
        self.assertEqual(base["excludedActors"], [])
        matte._check_manifest_data(base, manifest_path)
        mutations = {
            "requested_windows": lambda value: value["requestedWindows"]["pelica"]["framesExclusive"].__setitem__(0, 12561),
            "excluded_actors": lambda value: value["excludedActors"].append(
                {"actor": "endminf", "status": "unpublished", "reason": "mutated exclusion"}
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                candidate = copy.deepcopy(base)
                mutate(candidate)
                with self.assertRaises(matte.MatteError):
                    matte._check_manifest_data(candidate, manifest_path)

    def test_contiguous_ranges_are_deterministic(self) -> None:
        self.assertEqual(list(matte._contiguous_ranges([4, 3, 2, 9, 10, 12])), [(2, 4), (9, 10), (12, 12)])
        self.assertEqual(list(matte._contiguous_ranges([])), [])

    def test_source_pin_is_not_replaced_by_name_only(self) -> None:
        self.assertEqual(matte.VIDEO_RELATIVE.as_posix(), "videos/2026-08-15_10-32-32.mkv")
        self.assertEqual(len(matte.VIDEO_SHA256), 64)
        self.assertEqual(matte.VIDEO_BYTES, 1678613397)

    def test_source_contract_separates_timeline_and_decoded_counts(self) -> None:
        source = matte._expected_source_contract()
        self.assertNotIn("frameCount", source)
        self.assertEqual(source["timelineFrameCount"], 22702)
        self.assertEqual(source["decodedFrameCount"], 22701)
        self.assertEqual(source["packetCount"], 22701)
        self.assertTrue(source["decodedCountAuthoritative"])
        self.assertEqual(source["timelineFrameCount"], source["decodedFrameCount"] + 1)
        self.assertEqual(source["missingFinalPtsGap"]["missingTimelineFrameIndex"], 22700)
        self.assertEqual(source["missingFinalPtsGap"]["missingFrameCount"], 1)
        for actor in matte.ACTOR_WINDOWS:
            self.assertLess(matte._actor_window(actor).end_frame_exclusive, source["decodedFrameCount"])


if __name__ == "__main__":
    unittest.main()

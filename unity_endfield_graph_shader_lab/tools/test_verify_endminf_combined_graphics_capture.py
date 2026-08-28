#!/usr/bin/env python3

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import verify_endminf_combined_graphics_capture as subject


class CombinedGraphicsCaptureTests(unittest.TestCase):
    def test_combined_gate_includes_opening_owner_and_shader_archive(self) -> None:
        self.assertEqual(
            subject.opening.EXPECTED_INDEX_COUNTS,
            [11610, 7998, 4176, 420],
        )
        self.assertTrue(callable(subject.shader_archive.build_report))

    def test_peak_owner_audit_requires_both_m20_and_m21(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            capture = Path(temporary)
            frame = capture / "graphics/frames/1"
            frame.mkdir(parents=True)
            m20 = next(iter(subject.PEAK_SHADER_PAIRS["M20"]))
            m21 = next(iter(subject.PEAK_SHADER_PAIRS["M21"]))
            draws = []
            for vertex, pixel in (m20, m21):
                draws.append({"count": 6, "shaders": [
                    {"stage": 0, "identityHash": vertex},
                    {"stage": 4, "identityHash": pixel},
                ]})
            (frame / "metadata.json").write_text(
                json.dumps({"frame": 1, "drawRecords": draws}),
                encoding="utf-8")
            report = subject.audit_peak_owner_presence(capture)
            self.assertEqual("validated_peak_owner_presence", report["status"])
            self.assertEqual([], report["errors"])

            (frame / "metadata.json").write_text(
                json.dumps({"frame": 1, "drawRecords": draws[1:]}),
                encoding="utf-8")
            report = subject.audit_peak_owner_presence(capture)
            self.assertEqual("rejected", report["status"])
            self.assertTrue(any("M20" in error for error in report["errors"]))

    def test_transparent_cape_is_a_required_palette_owner(self) -> None:
        self.assertEqual(subject.skinning.MESHES["cloth_02"], (2_286, 29))
        self.assertIn("cloth_02", subject.MINIMUM_TOTAL)
        self.assertIn("cloth_02", subject.MINIMUM_PER_SEQUENCE)

    def test_split_sequences_uses_large_gap(self) -> None:
        frames = list(range(100, 500, 8)) + list(range(900, 1300, 8))
        sequences = subject.split_sequences(frames)
        self.assertEqual([50, 50], [len(row) for row in sequences])

    def test_automatic_sequence_policy_requires_complete_quiescent_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            capture = Path(temporary)
            (capture / "runtime.status.json").write_text(json.dumps({
                "endminfAutoTriggerObserved": True,
                "graphicsSequenceAutomatic": True,
                "graphicsSequenceMaxFrames": 72,
                "graphicsSequenceFrames": 72,
                "graphicsSequenceActive": False,
                "framePending": False,
                "graphicsSequenceCapturePending": False,
                "graphicsDropped": 0,
            }), encoding="utf-8")
            policy = subject.sequence_policy(capture)
            self.assertEqual("automatic_endminf_72", policy["name"])
            self.assertEqual(1, policy["expectedSequenceCount"])
            self.assertEqual(72, policy["minimumFramesPerSequence"])
            self.assertEqual([], policy["errors"])

    def test_automatic_sequence_policy_rejects_partial_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            capture = Path(temporary)
            (capture / "runtime.status.json").write_text(json.dumps({
                "endminfAutoTriggerObserved": True,
                "graphicsSequenceAutomatic": True,
                "graphicsSequenceMaxFrames": 72,
                "graphicsSequenceFrames": 51,
                "graphicsSequenceActive": False,
                "framePending": True,
                "graphicsSequenceCapturePending": True,
                "graphicsDropped": 2,
            }), encoding="utf-8")
            errors = subject.sequence_policy(capture)["errors"]
            self.assertTrue(any("completed 51" in row for row in errors))
            self.assertTrue(any("pending" in row for row in errors))
            self.assertTrue(any("dropped 2" in row for row in errors))

    def test_automatic_sequence_does_not_split_on_backpressure_gap(self) -> None:
        frames = list(range(100, 124)) + list(range(300, 348))
        policy = {"name": "automatic_endminf_72"}
        sequences = subject.logical_sequences(frames, policy)
        self.assertEqual([72], [len(row) for row in sequences])

    def test_old_status_retains_legacy_two_burst_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            capture = Path(temporary)
            (capture / "runtime.status.json").write_text(json.dumps({
                "graphicsSequenceMaxFrames": 64,
                "graphicsSequenceFrames": 0,
            }), encoding="utf-8")
            policy = subject.sequence_policy(capture)
            self.assertEqual("legacy_two_burst", policy["name"])
            self.assertEqual(2, policy["expectedSequenceCount"])

    def test_manual_72_package_run_is_rejected_as_nonautomatic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            capture = Path(temporary)
            (capture / "runtime.status.json").write_text(json.dumps({
                "endminfAutoTriggerObserved": True,
                "graphicsSequenceAutomatic": False,
                "graphicsSequenceMaxFrames": 72,
                "graphicsSequenceFrames": 72,
                "graphicsSequenceActive": False,
                "graphicsSequenceCapturePending": False,
                "framePending": False,
                "graphicsDropped": 0,
            }), encoding="utf-8")
            policy = subject.sequence_policy(capture)
            self.assertEqual("automatic_endminf_72", policy["name"])
            self.assertTrue(any("not started automatically" in row
                                for row in policy["errors"]))

    def test_palette_resource_accepts_bounded_blob(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            resource = Path(temporary) / "resources.bin"
            with resource.open("wb") as handle:
                handle.truncate(subject.skinning.PALETTE_BYTES)
            metadata = {"selectedResourceRecords": [{
                "completed": True,
                "byteSize": subject.skinning.PALETTE_BYTES,
                "blobBytes": subject.skinning.PALETTE_BYTES,
                "blobOffset": 0,
            }]}
            self.assertIsNone(subject.palette_resource(metadata, resource))

    def test_palette_resource_rejects_missing_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            resource = Path(temporary) / "resources.bin"
            resource.write_bytes(b"")
            metadata = {"selectedResourceRecords": [{
                "completed": True,
                "byteSize": subject.skinning.PALETTE_BYTES,
                "blobBytes": subject.skinning.PALETTE_BYTES,
                "blobOffset": 0,
            }]}
            self.assertIn("exceeds", subject.palette_resource(metadata, resource))

    def test_ambiguous_palette_pair_is_rejected(self) -> None:
        metadata = {"drawRecords": [
            {
                "indexedInstanced": True,
                "vsCb2RangeValid": True,
                "vsCb2MetadataValid": True,
                "vsCb2NumConstants": subject.skinning.SKINNING_CB_CONSTANTS,
                "count": subject.skinning.MESHES["hair"][0],
                "vsCb2CurrentPaletteRaw": 10,
                "vsCb2PreviousPaletteRaw": 20,
                "vsCb2FirstConstant": 0,
            },
            {
                "indexedInstanced": True,
                "vsCb2RangeValid": True,
                "vsCb2MetadataValid": True,
                "vsCb2NumConstants": subject.skinning.SKINNING_CB_CONSTANTS,
                "count": subject.skinning.MESHES["hair"][0],
                "vsCb2CurrentPaletteRaw": 30,
                "vsCb2PreviousPaletteRaw": 40,
                "vsCb2FirstConstant": 0,
            },
        ]}
        with self.assertRaisesRegex(subject.skinning.CaptureError, "ambiguous"):
            subject.skinning.unique_mesh_draw(metadata, "hair")


if __name__ == "__main__":
    unittest.main()

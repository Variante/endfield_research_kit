#!/usr/bin/env python3

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import verify_endminf_combined_graphics_capture as subject


class CombinedGraphicsCaptureTests(unittest.TestCase):
    @staticmethod
    def m20_draw(*, stride: int = 36, atlas_width: int = 256,
                 atlas_height: int = 128, atlas_format: int = 99,
                 atlas_bytes: int = 32768) -> tuple[dict, dict]:
        vertex, pixel = subject.M20_RETAIL_SHADER_PAIR
        atlas_object = 9001
        draw = {
            "indexedInstanced": True,
            "count": 36,
            "instanceCount": 1,
            "startInstance": 0,
            "shaders": [
                {"stage": 0, "identityHash": vertex},
                {"stage": 4, "identityHash": pixel},
            ],
            "inputAssembler": {
                "vertexBuffers": [
                    {"slot": 0, "stride": stride},
                    {"slot": 1, "stride": 0},
                ],
                "indexBuffer": {"format": 57},
            },
            "resources": [{
                "stage": 4,
                "slot": 1,
                "kind": 3,
                "objectId": atlas_object,
            }],
        }
        metadata = {"selectedResourceRecords": [{
            "captureKind": 3,
            "stage": 4,
            "slot": 1,
            "objectId": atlas_object,
            "completed": True,
            "width": atlas_width,
            "height": atlas_height,
            "format": atlas_format,
            "viewFormat": atlas_format,
            "blobBytes": atlas_bytes,
        }]}
        return draw, metadata

    def test_live_m20_retail_pair_is_admitted(self) -> None:
        self.assertIn(
            (0x62A5CE6C09171DE9, 0x5558DEDDB1EE6188),
            subject.PEAK_SHADER_PAIRS["M20"],
        )

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
            m20_draw, metadata = self.m20_draw()
            m21 = next(iter(subject.PEAK_SHADER_PAIRS["M21"]))
            draws = [m20_draw, {"count": 6, "shaders": [
                {"stage": 0, "identityHash": m21[0]},
                {"stage": 4, "identityHash": m21[1]},
            ]}]
            (frame / "metadata.json").write_text(
                json.dumps({"frame": 1, "drawRecords": draws, **metadata}),
                encoding="utf-8")
            report = subject.audit_peak_owner_presence(capture)
            self.assertEqual("validated_peak_owner_presence", report["status"])
            self.assertEqual([], report["errors"])

            (frame / "metadata.json").write_text(
                json.dumps({"frame": 1, "drawRecords": draws[1:], **metadata}),
                encoding="utf-8")
            report = subject.audit_peak_owner_presence(capture)
            self.assertEqual("rejected", report["status"])
            self.assertTrue(any("M20" in error for error in report["errors"]))

    def test_live_m20_shared_shader_requires_exact_owner_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            capture = Path(temporary)
            frame = capture / "graphics/frames/1"
            frame.mkdir(parents=True)
            for draw, metadata in (
                self.m20_draw(stride=60),
                self.m20_draw(atlas_width=256, atlas_height=256,
                              atlas_bytes=65536),
            ):
                (frame / "metadata.json").write_text(json.dumps({
                    "frame": 1,
                    "drawRecords": [draw],
                    **metadata,
                }), encoding="utf-8")
                report = subject.audit_peak_owner_presence(capture)
                self.assertEqual(0, report["owners"]["M20"]["packetCount"])

    def test_live_m20_exact_owner_shape_is_admitted(self) -> None:
        draw, metadata = self.m20_draw()
        self.assertTrue(subject.is_exact_m20_owner_packet(draw, metadata))

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

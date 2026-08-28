#!/usr/bin/env python3

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import verify_endminf_combined_graphics_capture as subject


class CombinedGraphicsCaptureTests(unittest.TestCase):
    def test_transparent_cape_is_a_required_palette_owner(self) -> None:
        self.assertEqual(subject.skinning.MESHES["cloth_02"], (2_286, 29))
        self.assertIn("cloth_02", subject.MINIMUM_TOTAL)
        self.assertIn("cloth_02", subject.MINIMUM_PER_SEQUENCE)

    def test_split_sequences_uses_large_gap(self) -> None:
        frames = list(range(100, 500, 8)) + list(range(900, 1300, 8))
        sequences = subject.split_sequences(frames)
        self.assertEqual([50, 50], [len(row) for row in sequences])

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

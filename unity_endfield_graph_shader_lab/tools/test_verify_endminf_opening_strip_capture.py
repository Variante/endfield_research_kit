#!/usr/bin/env python3

from __future__ import annotations

import json
import struct
import tempfile
import unittest
from pathlib import Path

import verify_endminf_opening_strip_capture as verifier


class OpeningStripCaptureVerificationTests(unittest.TestCase):
    def make_session(self, root: Path, corrupt_topology: bool = False) -> Path:
        session = root / "session"
        counts = verifier.EXPECTED_INDEX_COUNTS
        for frame_id, count in enumerate(counts, 100):
            frame = session / "graphics" / "frames" / str(frame_id)
            frame.mkdir(parents=True)
            quads = count // 6
            indices: list[int] = []
            vertices = bytearray()
            for quad in range(quads):
                first = quad * 4
                indices.extend((first, first + 1, first + 2,
                                first, first + 2, first + 3))
                y = float(quad) * 0.01
                for x, dy in ((0.0, 0.0), (2.0, 0.0),
                              (2.0, 0.1), (0.0, 0.1)):
                    vertices.extend(struct.pack("<3f", x, y + dy, 0.0))
                    vertices.extend(bytes(verifier.EXPECTED_VERTEX_STRIDE - 12))
            if corrupt_topology and frame_id == 100:
                indices[0] = 7
            vertex_offset = 64
            index_offset = vertex_offset + len(vertices)
            blob = bytearray(index_offset + len(indices) * 2)
            blob[vertex_offset:index_offset] = vertices
            blob[index_offset:] = struct.pack(f"<{len(indices)}H", *indices)
            (frame / "resources.bin").write_bytes(blob)
            metadata = {
                "frame": frame_id,
                "resourcesFile": "resources.bin",
                "selectedResourceRecords": [
                    {"captureKind": 0, "objectId": 10, "blobOffset": 0,
                     "completed": True},
                    {"captureKind": 1, "objectId": 10, "blobOffset": 0,
                     "completed": True},
                ],
                "drawRecords": [{
                    "drawOrdinal": 9,
                    "count": count,
                    "start": 0,
                    "baseVertex": 0,
                    "shaders": [
                        {"stage": 0, "identityHash": verifier.VS_IDENTITY},
                        {"stage": 4, "identityHash": verifier.PS_IDENTITY},
                    ],
                    "inputAssembler": {
                        "vertexBuffers": [{"objectId": 10,
                                           "stride": verifier.EXPECTED_VERTEX_STRIDE,
                                           "offset": vertex_offset}],
                        "indexBuffer": {"objectId": 10, "format": 57,
                                        "offset": index_offset},
                    },
                    "pipelineState": {
                        "target": {"width": 3840, "height": 2160},
                        "blend": {"enabled": True, "source": 5,
                                  "destination": 6},
                    },
                }],
            }
            (frame / "metadata.json").write_text(
                json.dumps(metadata), encoding="utf-8"
            )
        return session

    def test_exact_quad_sequence_validates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = verifier.build_report(
                self.make_session(Path(temporary))
            )
        self.assertEqual(report["status"], "validated")
        self.assertEqual(report["packetCount"], 4)
        self.assertGreater(report["packets"][0]["horizontalQuadFraction"], 0.99)

    def test_missing_owner_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            session = self.make_session(Path(temporary))
            for metadata_path in session.glob("graphics/frames/*/metadata.json"):
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                metadata["drawRecords"] = []
                metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            report = verifier.build_report(session)
        self.assertEqual(report["status"], "rejected")
        self.assertTrue(any("temporal index counts" in row
                            for row in report["errors"]))

    def test_non_quad_topology_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = verifier.build_report(
                self.make_session(Path(temporary), corrupt_topology=True)
            )
        self.assertEqual(report["status"], "rejected")
        self.assertTrue(any("non-independent quad" in row
                            for row in report["errors"]))


if __name__ == "__main__":
    unittest.main()

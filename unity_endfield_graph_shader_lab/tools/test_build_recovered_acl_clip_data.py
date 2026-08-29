#!/usr/bin/env python3

import base64
import json
import struct
import tempfile
import unittest
from pathlib import Path

from unity_endfield_graph_shader_lab.tools.build_recovered_acl_clip_data import build_contract


class BuildRecoveredAclClipDataTests(unittest.TestCase):
    def fixture(self, root: Path):
        acl = struct.pack("<I4s", 0xAC11AC11, b"test")
        acl_path = root / "clip.acl"
        acl_path.write_bytes(acl)
        clip_path = root / "clip.json"
        clip_path.write_text(json.dumps({
            "Name": "generic_clip",
            "m_AclCompressedBuffer": {"TransformBufferData": base64.b64encode(acl).decode()},
        }), encoding="utf-8")
        frames = []
        for index in range(2):
            frames.append({"index": index, "time": index / 60, "tracks": [{
                "translation": [index, 2, 3],
                "rotation": [0, 0, 0, 1],
                "scale": [1, 1, 1],
            }]})
        sample_path = root / "sample.json"
        sample_path.write_text(json.dumps({
            "ok": True, "hash_ok": True, "validation_error": None,
            "clip_name": "generic_clip", "source_json": str(clip_path),
            "source_acl": str(acl_path),
            "num_tracks": 1, "num_samples": 2, "sample_rate": 60,
            "duration": 1 / 60, "frames": frames,
        }), encoding="utf-8")
        binding_path = root / "manifest.json"
        binding_path.write_text(json.dumps({"clips": [{
            "name": "generic_clip", "loop": True,
            "bones": [{
                "matched": True, "path": "Root/Bone", "track_index": 0,
                "pos_animated": True, "rot_animated": True,
                "scale_animated": False,
            }],
        }]}), encoding="utf-8")
        return clip_path, sample_path, binding_path, acl_path

    def test_builds_frame_major_runtime_contract_with_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = self.fixture(Path(temporary))
            result = build_contract(*paths[:3])
        self.assertEqual((2, 1, 1),
                         (result["sampleCount"], result["trackCount"], result["loopingPolicy"]))
        self.assertEqual({"x": 1.0, "y": 2.0, "z": 3.0}, result["translations"][1])
        self.assertEqual([{"transformPath": "Root/Bone", "trackIndex": 0, "components": 3}],
                         result["bindings"])
        for key in ("sourceClipJsonSha256", "sourceAclSha256", "decodedSamplesSha256"):
            self.assertEqual(64, len(result[key]))

    def test_rejects_acl_sidecar_that_differs_from_exported_buffer(self):
        with tempfile.TemporaryDirectory() as temporary:
            clip, sample, binding, acl = self.fixture(Path(temporary))
            acl.write_bytes(struct.pack("<I4s", 0xAC11AC11, b"FAIL"))
            with self.assertRaisesRegex(ValueError, "differs from TransformBufferData"):
                build_contract(clip, sample, binding)

    def test_rejects_nonuniform_frame_time(self):
        with tempfile.TemporaryDirectory() as temporary:
            clip, sample, binding, _ = self.fixture(Path(temporary))
            payload = json.loads(sample.read_text(encoding="utf-8"))
            payload["frames"][1]["time"] = 0.25
            sample.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "uniform time"):
                build_contract(clip, sample, binding)


if __name__ == "__main__":
    unittest.main()

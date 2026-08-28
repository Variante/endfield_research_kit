import importlib.util
import json
import re
import struct
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("decode_endminf_endfield_capture_skinning.py")
SPEC = importlib.util.spec_from_file_location("capture_skinning", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CaptureSkinningTests(unittest.TestCase):
    def test_mesh_contracts_match_generated_unity_assets(self):
        lab = MODULE_PATH.parents[1]
        mesh_root = (
            lab / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Meshes"
        )
        names = {
            "body": "S_actor_endminf_body_01_lod0.asset",
            "cloth_01": "S_actor_endminf_cloth_01_lod0.asset",
            "cloth_02": "S_actor_endminf_cloth_02_lod0.asset",
            "cloth_03": "S_actor_endminf_cloth_03_lod0.asset",
            "cloth_04": "S_actor_endminf_cloth_04_lod0.asset",
            "hair": "S_actor_endminf_hair_01_lod0.asset",
        }
        for mesh, filename in names.items():
            text = (mesh_root / filename).read_text(encoding="utf-8")
            bindposes = text.split("  m_BindPose:", 1)[1].split(
                "  m_BoneNameHashes:", 1
            )[0]
            index_count = int(re.search(r"indexCount: (\d+)", text).group(1))
            bindpose_count = len(re.findall(r"^  - e00:", bindposes, re.MULTILINE))
            self.assertEqual(MODULE.MESHES[mesh], (index_count, bindpose_count))

    def make_frame(self, root: Path, *, ambiguous: bool = False) -> Path:
        frame = root / "graphics" / "frames" / "100"
        frame.mkdir(parents=True)
        palette = bytearray(MODULE.PALETTE_BYTES)
        for row in range(3 * MODULE.MESHES["hair"][1]):
            struct.pack_into(
                "<4f", palette, (23 + row) * 16,
                row + 0.1, row + 0.2, row + 0.3, row + 0.4,
            )
            struct.pack_into(
                "<4f", palette, (53 + row) * 16,
                row + 1.1, row + 1.2, row + 1.3, row + 1.4,
            )
        (frame / "resources.bin").write_bytes(palette)
        draw = {
            "count": MODULE.MESHES["hair"][0],
            "indexedInstanced": True,
            "instanceCount": 1,
            "startInstance": 0,
            "vsCb2RangeValid": True,
            "vsCb2FirstConstant": 100,
            "vsCb2NumConstants": MODULE.SKINNING_CB_CONSTANTS,
            "vsCb2MetadataValid": True,
            "vsCb2CurrentPaletteRaw": 20,
            "vsCb2PreviousPaletteRaw": 50,
        }
        draws = [
            draw,
            {**draw, "vsCb2FirstConstant": 200},
            {
                **draw,
                "vsCb2FirstConstant": 300,
                "vsCb2NumConstants": 16,
                "vsCb2CurrentPaletteRaw": 0,
                "vsCb2PreviousPaletteRaw": 0,
            },
        ]
        if ambiguous:
            draws[1]["vsCb2CurrentPaletteRaw"] = 21
        metadata = {
            "frame": 100,
            "captureIncomplete": False,
            "captureFailed": False,
            "resourcesFile": "resources.bin",
            "selectedResourceRecords": [
                {
                    "byteSize": MODULE.PALETTE_BYTES,
                    "blobOffset": 0,
                    "blobBytes": MODULE.PALETTE_BYTES,
                    "completed": True,
                },
            ],
            "drawRecords": draws,
        }
        (frame / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        return frame

    def test_decodes_shared_palette_pair_across_retail_pass_ranges(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_frame(root)
            result = MODULE.decode_session(root, ["hair"])
        hair = result["frames"][0]["meshes"]["hair"]
        self.assertEqual(hair["matchingDrawRecords"], 2)
        self.assertEqual(len(hair["matchingRanges"]), 2)
        self.assertEqual(hair["currentEffectiveBaseRow"], 23)
        self.assertEqual(hair["previousEffectiveBaseRow"], 53)
        self.assertEqual(
            hair["currentMatrices3x4"][0][0],
            [0.10000000149011612, 0.20000000298023224,
             0.30000001192092896, 0.4000000059604645],
        )

    def test_rejects_ambiguous_palette_pairs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_frame(root, ambiguous=True)
            with self.assertRaisesRegex(MODULE.CaptureError, "ambiguous hair"):
                MODULE.decode_session(root, ["hair"])

    def test_rejects_capture_without_draw_time_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frame = self.make_frame(root)
            metadata_path = frame / "metadata.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            for draw in metadata["drawRecords"]:
                draw.pop("vsCb2MetadataValid")
                draw.pop("vsCb2CurrentPaletteRaw")
                draw.pop("vsCb2PreviousPaletteRaw")
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            with self.assertRaisesRegex(MODULE.CaptureError, "capture again"):
                MODULE.decode_session(root, ["hair"])

    def test_rejects_missing_palette_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frame = self.make_frame(root)
            metadata_path = frame / "metadata.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["selectedResourceRecords"].clear()
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            with self.assertRaisesRegex(MODULE.CaptureError, "8413184-byte resource"):
                MODULE.decode_session(root, ["hair"])

    def test_partial_mode_retains_present_mesh_and_marks_absent_mesh(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_frame(root)
            result = MODULE.decode_session(
                root, ["hair", "cloth_04"], allow_partial=True
            )
        self.assertEqual(
            result["schema"],
            "endfield.charinfo.endminf-partial-captured-skin-palette-sequence.v1",
        )
        self.assertEqual(result["meshObservationCounts"], {"hair": 1, "cloth_04": 0})
        self.assertIn("hair", result["frames"][0]["meshes"])
        self.assertEqual(result["frames"][0]["missingMeshes"], ["cloth_04"])

    def test_partial_mode_still_rejects_ambiguous_present_mesh(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_frame(root, ambiguous=True)
            with self.assertRaisesRegex(MODULE.CaptureError, "ambiguous hair"):
                MODULE.decode_session(root, ["hair"], allow_partial=True)


if __name__ == "__main__":
    unittest.main()

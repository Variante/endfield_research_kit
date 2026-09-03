import json
import struct
import tempfile
import unittest
from pathlib import Path

from scripts import terrain_height


def write_height(path: Path, *, lod: int, value: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = struct.pack("<4225H", *([value] * 4225))
    path.write_bytes(
        b"TRET"
        + struct.pack("<I6H", 1, 65, 65, 1, lod, len(payload), 0)
        + payload
    )


class TerrainHeightTests(unittest.TestCase):
    def test_load_and_index_exact_height_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "terrain"
            path = source / "map02" / "Terrain_6_16_32_H.bytes"
            write_height(path, lod=6, value=1234)
            tiles = terrain_height.load_height_tiles(source)
            self.assertEqual(len(tiles), 1)
            self.assertEqual(tiles[0].world_bounds(), {
                "minX": -512.0, "maxX": -480.0,
                "minZ": 0.0, "maxZ": 32.0,
            })
            output = root / "reports/index.json"
            payload = terrain_height.write_height_index(source, output, relative_to=root)
            self.assertEqual(payload["status"], "complete")
            self.assertEqual(payload["entries"][0]["sampleShape"], [65, 65])
            self.assertEqual(json.loads(output.read_text())["tileCount"], 1)
            first_fingerprint = payload["sourceFingerprint"]
            write_height(path, lod=6, value=1235)  # same encoded length
            changed = terrain_height.write_height_index(source, output, relative_to=root)
            self.assertNotEqual(changed["sourceFingerprint"], first_fingerprint)
            self.assertEqual(changed["entries"][0]["valueRange"], [1235, 1235])

    def test_render_crops_only_intersecting_cells(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "terrain"
            write_height(source / "map02" / "Terrain_6_16_32_H.bytes", lod=6, value=100)
            write_height(source / "map02" / "Terrain_6_17_32_H.bytes", lod=6, value=200)
            write_height(source / "map02" / "Terrain_6_18_32_H.bytes", lod=6, value=300)
            output = root / "render/height.png"
            info = terrain_height.render_height_layer(
                source,
                "map02",
                {"minX": -512.0, "maxX": -448.0, "minZ": 0.0, "maxZ": 32.0},
                output,
                long_edge=64,
                relative_to=root,
            )
            self.assertIsNotNone(info)
            self.assertEqual(info["tileCount"], 2)
            self.assertEqual(info["cellSize"], 32.0)
            self.assertEqual(info["sampleSpacing"], 0.5)
            self.assertTrue(output.is_file())
            sidecar = json.loads(output.with_suffix(".sources.json").read_text())
            self.assertEqual(set(sidecar["sources"]), {"16_32", "17_32"})


if __name__ == "__main__":
    unittest.main()

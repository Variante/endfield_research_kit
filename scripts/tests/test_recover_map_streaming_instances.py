import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import recover_map_streaming_instances as recovery
from scripts.recover_map_streaming_instances import decompress_inverted_lz4, entity_base


class StreamingInstanceRecoveryTests(unittest.TestCase):
    def test_literal_only_inverted_lz4_block(self):
        # Inverted nibble 0x03 decodes to a three-byte literal and no match.
        self.assertEqual(decompress_inverted_lz4(b"\x03abc", 3), b"abc")

    def test_entity_base_strips_instance_suffixes(self):
        self.assertEqual(
            entity_base("P_grass_indie_base+1_001_02 (62)_ECSMerged#0_131DD9"),
            "P_grass_indie_base+1_001_02",
        )

    def test_sphub_prefab_resolves_the_static_tower_and_base_family(self):
        entries = [
            {"Type": "Mesh", "Name": "S_prop_indie_sphub+1_001_02_lod0", "PathID": 2, "Container": "base"},
            {"Type": "Mesh", "Name": "S_prop_indie_sphub+1_001_03_lod0", "PathID": 3, "Container": "tower"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            asset_map = root / "AssetMap.json"
            asset_map.touch()
            (root / "base_p0000000000000002.obj").touch()
            (root / "tower_p0000000000000003.obj").touch()
            with mock.patch.object(recovery, "ROOT", root), \
                    mock.patch.object(recovery, "iter_asset_entries", return_value=iter(entries)):
                rows = recovery._mesh_candidates(
                    {"P_prop_indie_sphub+1_001_04"}, asset_map, root
                )["P_prop_indie_sphub+1_001_04"]

        self.assertEqual([row["name"] for row in rows], [
            "S_prop_indie_sphub+1_001_03_lod0",
            "S_prop_indie_sphub+1_001_02_lod0",
        ])
        self.assertTrue(all(row["match"] == "explicit_static_asset_family_closure" for row in rows))


if __name__ == "__main__":
    unittest.main()

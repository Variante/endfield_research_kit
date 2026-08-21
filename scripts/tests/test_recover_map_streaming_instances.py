import tempfile
import unittest
from collections import Counter
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

    def test_payload_keeps_component_shape_at_group_level(self):
        instances = [{
            "entityId": 1, "sourceFile": "chunk.bytes", "groupIndex": 0,
            "initChunkComponentTypeIds": [18, 21, 67],
            "initChunkComponentStrides": {"18": 64, "21": 64, "67": 16},
            "prefabIdentity": {"status": "unavailableInValidatedInitChunkSchema"},
        }]
        shapes = recovery._compact_component_shapes(instances)
        self.assertEqual(shapes["chunk.bytes#group0"]["componentTypeIds"], [18, 21, 67])
        self.assertEqual(instances[0]["initChunkComponentShapeId"], "chunk.bytes#group0")
        self.assertNotIn("initChunkComponentTypeIds", instances[0])
        self.assertNotIn("initChunkComponentStrides", instances[0])

    def test_prefab_contract_revalidates_exact_identity_fields(self):
        contract = recovery._build_prefab_identity_contract([{
            "entityId": 1,
            "prefabIdentity": {"status": "exact", "source": "", "pathId": True},
        }])
        self.assertEqual(contract["status"], "unavailable")
        self.assertEqual(contract["exactInstanceCount"], 0)
        self.assertEqual(contract["invalidExactIdentityCount"], 1)
        self.assertEqual(contract["diagnostics"][0]["reason"], "exactIdentityRequiresNonEmptySourceAndIntegerPathId")


if __name__ == "__main__":
    unittest.main()

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

    def test_hlod_mesh_join_requires_exact_level_and_cluster_key(self):
        entries = [
            {"Type": "Mesh", "Name": "S_HLOD1_10_9_Cluster_-7", "PathID": 7,
             "Container": "x/map02_lv005_art/hlod_v2/pc/hlod1/mesh"},
            {"Type": "Mesh", "Name": "S_HLOD1_10_9_Cluster_-7", "PathID": 8,
             "Container": "x/map02_lv004_art/hlod_v2/pc/hlod1/mesh"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            asset_map = root / "AssetMap.json"
            asset_map.touch()
            (root / "mesh_p0000000000000007.obj").touch()
            (root / "other_p0000000000000008.obj").touch()
            with mock.patch.object(recovery, "ROOT", root), \
                    mock.patch.object(recovery, "iter_asset_entries", return_value=iter(entries)):
                rows = recovery._hlod_mesh_candidates(
                    {"map02_lv005"}, asset_map, root
                )["map02_lv005"]
        self.assertEqual(list(rows), ["hlod1_10_9_cluster_-7"])
        self.assertEqual(rows["hlod1_10_9_cluster_-7"][0]["pathId"], 7)

    def test_region_hlod_partition_derives_dense_member_suffix_from_unique_keys(self):
        matrix = [1.0] * 16
        core = {
            "levelId": "map02", "sources": [], "duplicates": 0, "componentShapes": {},
            "instances": [
                {"entityId": 1, "name": "HLOD1_10_9_Cluster_-7_250#4_AB", "matrixColumnMajor": matrix},
                {"entityId": 2, "name": "HLOD1_8_9_Cluster_-6_250#4_CD", "matrixColumnMajor": matrix},
                {"entityId": 3, "name": "HLOD1_8_9_Cluster_-6_250#5_EF", "matrixColumnMajor": matrix},
                {"entityId": 4, "name": "HLOD1_9_9_Cluster_-8_250#5_01", "matrixColumnMajor": matrix},
            ],
        }
        meshes = {
            "map02_lv005": {
                "hlod1_10_9_cluster_-7": [{"pathId": 7}],
                "hlod1_8_9_cluster_-6": [{"pathId": 6}],
            },
            "map02_lv006": {
                "hlod1_9_9_cluster_-8": [{"pathId": 8}],
                "hlod1_8_9_cluster_-6": [{"pathId": 9}],
            },
        }
        with mock.patch.object(recovery, "_recover_transform_core", return_value=core), \
                mock.patch.object(recovery, "_hlod_mesh_candidates", return_value=meshes), \
                mock.patch.object(recovery, "sha256_file", return_value="hash"):
            payloads = recovery.recover_hlod_region_levels(
                ["map02_lv005", "map02_lv006"], recovery.ROOT / "cli",
                Path("game"), Path("map"), Path("mesh")
            )
        by_level = {row["levelId"]: row for row in payloads}
        self.assertEqual([row["entityId"] for row in by_level["map02_lv005"]["instances"]], [1, 2])
        self.assertEqual([row["entityId"] for row in by_level["map02_lv006"]["instances"]], [3, 4])
        self.assertEqual(by_level["map02_lv005"]["hlodIdentityContract"]["instanceMemberSuffix"], 4)
        self.assertEqual(by_level["map02_lv006"]["hlodIdentityContract"]["instanceMemberSuffix"], 5)

    def test_batch_recovery_scans_asset_map_once_for_all_levels(self):
        def core(level_id, _cli, _game_root):
            return {
                "levelId": level_id,
                "sources": [{"fileName": f"{level_id}.bytes"}],
                "instances": [],
                "duplicates": 0,
                "bases": {f"P_{level_id}": 1},
            }

        with mock.patch.object(recovery, "_recover_transform_core", side_effect=core), \
                mock.patch.object(recovery, "_mesh_candidates", return_value={}) as mesh_candidates, \
                mock.patch.object(recovery, "_hlod_mesh_candidates", return_value={}), \
                mock.patch.object(recovery, "sha256_file", return_value="hash"):
            payloads = recovery.recover_many(
                ["dung01_cdg001", "indie_dg008"],
                recovery.ROOT / "cli", Path("game"), Path("AssetMap.json"), Path("Mesh"), jobs=2,
            )

        self.assertEqual([row["levelId"] for row in payloads], ["dung01_cdg001", "indie_dg008"])
        mesh_candidates.assert_called_once_with(
            {"P_dung01_cdg001", "P_indie_dg008"}, Path("AssetMap.json"), Path("Mesh")
        )

    def test_ordinary_level_uses_exact_hlod_key_without_prefix_fallback(self):
        matrix = [1.0] * 16
        core = {
            "levelId": "indie_dg002", "sources": [], "duplicates": 0, "componentShapes": {},
            "bases": Counter({"HLOD1_10_9_Cluster_-7": 1}),
            "instances": [{
                "entityId": 1, "entityBase": "HLOD1_10_9_Cluster_-7",
                "name": "HLOD1_10_9_Cluster_-7_100#0_AB", "matrixColumnMajor": matrix,
            }],
        }
        meshes = {"indie_dg002": {"hlod1_10_9_cluster_-7": [{"pathId": 7}]}}
        with mock.patch.object(recovery, "_recover_transform_core", return_value=core), \
                mock.patch.object(recovery, "_mesh_candidates", return_value={}), \
                mock.patch.object(recovery, "_hlod_mesh_candidates", return_value=meshes), \
                mock.patch.object(recovery, "sha256_file", return_value="hash"):
            payload = recovery.recover_many(
                ["indie_dg002"], recovery.ROOT / "cli", Path("game"),
                Path("AssetMap.json"), Path("Mesh"),
            )[0]

        self.assertEqual(payload["hlodIdentityContract"]["status"], "exact")
        self.assertEqual(payload["hlodIdentityContract"]["resolvedInstanceCount"], 1)
        self.assertEqual(payload["instances"][0]["hlodIdentity"]["key"], "hlod1_10_9_cluster_-7")
        self.assertEqual(payload["entityBases"][0]["meshes"], [{"pathId": 7}])

    def test_payload_keeps_component_shape_at_group_level(self):
        core = {
            "levelId": "indie_dg008",
            "sources": [],
            "instances": [{
                "entityId": 1,
                "entityBase": "P_fixture",
                "initChunkComponentShapeId": "chunk.bytes#group0",
                "prefabIdentity": {
                    "status": "unavailableInValidatedInitChunkSchema",
                },
            }],
            "duplicates": 0,
            "bases": Counter({"P_fixture": 1}),
            "componentShapes": {
                "chunk.bytes#group0": {
                    "componentTypeIds": [18, 21, 67],
                    "componentStrides": {"18": 64, "21": 64, "67": 16},
                },
            },
        }
        with mock.patch.object(recovery, "sha256_file", return_value="hash"):
            payload = recovery._finalize_payload(core, {}, recovery.ROOT / "cli")
        self.assertEqual(payload["schemaVersion"], 2)
        self.assertEqual(payload["prefabIdentityContract"]["status"], "unavailable")
        self.assertEqual(payload["initChunkComponentShapes"]["chunk.bytes#group0"]["componentTypeIds"], [18, 21, 67])
        self.assertEqual(payload["instances"][0]["initChunkComponentShapeId"], "chunk.bytes#group0")
        self.assertNotIn("initChunkComponentTypeIds", payload["instances"][0])
        self.assertNotIn("initChunkComponentStrides", payload["instances"][0])

    def test_prefab_contract_revalidates_exact_identity_fields(self):
        core = {
            "levelId": "indie_dg008",
            "sources": [],
            "instances": [{
                "entityId": 1,
                "entityBase": "P_fixture",
                "prefabIdentity": {"status": "exact", "source": "", "pathId": True},
            }],
            "duplicates": 0,
            "bases": Counter({"P_fixture": 1}),
        }
        with mock.patch.object(recovery, "sha256_file", return_value="hash"):
            payload = recovery._finalize_payload(core, {}, recovery.ROOT / "cli")
        contract = payload["prefabIdentityContract"]
        self.assertEqual(contract["status"], "unavailable")
        self.assertEqual(contract["exactInstanceCount"], 0)
        self.assertEqual(contract["invalidExactIdentityCount"], 1)
        self.assertEqual(
            contract["diagnostics"][0]["reason"],
            "exactIdentityRequiresNonEmptySourceAndIntegerPathId",
        )


if __name__ == "__main__":
    unittest.main()

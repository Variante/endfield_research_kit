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
                mock.patch.object(recovery, "sha256_file", return_value="hash"):
            payloads = recovery.recover_many(
                ["dung01_cdg001", "indie_dg008"],
                recovery.ROOT / "cli", Path("game"), Path("AssetMap.json"), Path("Mesh"), jobs=2,
            )

        self.assertEqual([row["levelId"] for row in payloads], ["dung01_cdg001", "indie_dg008"])
        mesh_candidates.assert_called_once_with(
            {"P_dung01_cdg001", "P_indie_dg008"}, Path("AssetMap.json"), Path("Mesh")
        )

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

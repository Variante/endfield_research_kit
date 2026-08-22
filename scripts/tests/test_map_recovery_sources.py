import tempfile
import unittest
from pathlib import Path

from scripts.map_recovery_sources import (
    authored_art_level,
    authored_streaming_scene,
    isolated_art_source,
    projection_streaming_scene,
)


class MapRecoverySourceTests(unittest.TestCase):
    def test_compact_level_config_proves_shared_blackbox_scene(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            level_root = root / "levels"
            level_root.mkdir()
            (level_root / "blackbox_new.json").write_bytes(
                b"\x0f\x03blackbox02_dg001/blackbox02_dg001_art_streaming.asset\x00tail"
            )
            source = authored_streaming_scene("blackbox_new", level_config_root=level_root)
        self.assertEqual(source["sceneId"], "blackbox02_dg001")
        self.assertEqual(source["method"], "level_config_embedded_streaming_path")

    def test_large_region_streaming_path_resolves_without_art_suffix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            level_root = root / "levels"
            level_root.mkdir()
            (level_root / "dung01_bdg001.json").write_bytes(
                b"\x0f\x03map01/map01_streaming.asset\x00map01_lv002_art"
            )
            source = authored_streaming_scene("dung01_bdg001", level_config_root=level_root)
        self.assertEqual(source["sceneId"], "map01")

    def test_nonseamless_danger_map_retains_its_exact_source_art_level(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            level_root = root / "levels"
            level_root.mkdir()
            (level_root / "dung01_bdg001.json").write_bytes(
                b"map01/map01_streaming.asset\x00map01_lv002_art\x00dung01_bdg001"
            )
            source = authored_art_level("dung01_bdg001", level_config_root=level_root)
            isolated = isolated_art_source("dung01_bdg001", level_config_root=level_root)
        self.assertEqual(source["levelId"], "map01_lv002")
        self.assertEqual(isolated, source)

    def test_art_level_relation_is_not_applied_to_non_dungeon_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            level_root = root / "levels"
            level_root.mkdir()
            (level_root / "event_test.json").write_bytes(b"map01_lv002_art")
            self.assertIsNotNone(authored_art_level("event_test", level_config_root=level_root))
            self.assertIsNone(isolated_art_source("event_test", level_config_root=level_root))

    def test_mismatched_streaming_folder_and_asset_name_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            level_root = root / "levels"
            level_root.mkdir()
            (level_root / "bad.json").write_bytes(b"map01/map02_streaming.asset")
            source = authored_streaming_scene("bad", level_config_root=level_root)
        self.assertIsNone(source)

    def test_projection_requires_the_resolved_init_chunk_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            level_root = root / "levels"
            instance_root = root / "instances"
            level_root.mkdir()
            instance_root.mkdir()
            (level_root / "blackbox_basic_1.json").write_bytes(
                b"blackbox01_dg001/blackbox01_dg001_art_streaming.asset"
            )
            self.assertIsNone(projection_streaming_scene(
                "blackbox_basic_1", instance_root=instance_root, level_config_root=level_root,
            ))
            sidecar = instance_root / "blackbox01_dg001.json"
            sidecar.write_text("{}", encoding="utf-8")
            source = projection_streaming_scene(
                "blackbox_basic_1", instance_root=instance_root, level_config_root=level_root,
            )
        self.assertEqual(source["sceneId"], "blackbox01_dg001")
        self.assertEqual(source["instanceSource"], sidecar)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
import base64
import json
import tempfile
from pathlib import Path
from difflib import SequenceMatcher
from unittest.mock import patch

from scripts.story_builder import anime_assets, dialog_tree, language_bundle, level_bindings, mission_recovery


class StoryBuildPerformanceEquivalenceTests(unittest.TestCase):
    def test_fast_sequence_threshold_matches_sequence_matcher(self) -> None:
        samples = [
            ("接受委托", "接受委托"),
            ("查看终端消息", "查看终端里的消息"),
            ("前往枢纽区", "与管理员交谈"),
            ("", ""),
            ("短", "一段明显更长的文本"),
        ]
        for threshold in (-0.1, 0.80, 0.92, 1.1, float("nan")):
            for left, right in samples:
                with self.subTest(threshold=threshold, left=left, right=right):
                    expected = SequenceMatcher(None, left, right).ratio() >= threshold
                    actual = language_bundle._sequence_similarity_at_least(
                        left,
                        right,
                        threshold,
                    )
                    self.assertEqual(expected, actual)

    def test_filtered_anime_tree_lookup_preserves_root_precedence_and_alias_dedup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "first" / "TextAsset"
            second = root / "second" / "MonoBehaviour"
            first.mkdir(parents=True)
            second.mkdir(parents=True)
            preferred = first / "dlg_fixture_p0000000000000001.json"
            alias = second / "dlg_fixture_p0000000000000003.json"
            related = second / "dlg_fixture_extra_p0000000000000002.json"
            preferred.write_text("{}", encoding="utf-8")
            alias.write_text("{}", encoding="utf-8")
            related.write_text("{}", encoding="utf-8")

            anime_assets._anime_tree_files.cache_clear()
            anime_assets._ANIME_TREE_PATH_INDEX = None
            anime_assets._ANIME_TREE_SORTED_STEMS = None
            with patch.object(anime_assets, "ANIME_RESOURCE_DIRS", [first, second]):
                found = anime_assets._find_anime_tree_path("dlg_fixture.json")
                paths = list(anime_assets._iter_related_dialog_tree_paths("dlg_fixture"))
            anime_assets._anime_tree_files.cache_clear()
            anime_assets._ANIME_TREE_PATH_INDEX = None
            anime_assets._ANIME_TREE_SORTED_STEMS = None

            self.assertEqual(preferred, found)
            self.assertEqual([preferred, related], paths)

    def test_mono_asset_uses_exact_lazy_lookup_without_full_directory_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            text_root = root / "TextAsset"
            mono_root = root / "MonoBehaviour"
            text_root.mkdir()
            mono_root.mkdir()
            target = mono_root / "DialogActionFixture_p0000000000000009.json"
            sibling = mono_root / "DialogActionFixtureExtra_p0000000000000010.json"
            target.write_text("{}", encoding="utf-8")
            sibling.write_text("{}", encoding="utf-8")

            calls: list[tuple[str, str]] = []
            real_fast_glob = anime_assets.fast_glob_files

            def recording_fast_glob(directory: Path, pattern: str):
                calls.append((directory.name, pattern))
                return real_fast_glob(directory, pattern)

            anime_assets._anime_tree_files.cache_clear()
            anime_assets._ANIME_TREE_PATH_INDEX = None
            anime_assets._ANIME_TREE_SORTED_STEMS = None
            with (
                patch.object(anime_assets, "ANIME_RESOURCE_DIRS", [text_root, mono_root]),
                patch.object(anime_assets, "fast_glob_files", side_effect=recording_fast_glob),
            ):
                found = anime_assets._find_anime_tree_path(
                    "DialogActionFixture.json"
                )
            anime_assets._anime_tree_files.cache_clear()
            anime_assets._ANIME_TREE_PATH_INDEX = None
            anime_assets._ANIME_TREE_SORTED_STEMS = None

            self.assertEqual(target, found)
            self.assertNotIn(("MonoBehaviour", "*.json"), calls)
            self.assertIn(("MonoBehaviour", "dlg_*.json"), calls)
            self.assertIn(("MonoBehaviour", "DialogActionFixture*.json"), calls)

    def test_complete_dialog_timeline_prefix_miss_does_not_rescan_mono_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            text_root = root / "TextAsset"
            mono_root = root / "MonoBehaviour"
            text_root.mkdir()
            mono_root.mkdir()
            calls: list[tuple[str, str]] = []
            real_fast_glob = anime_assets.fast_glob_files

            def recording_fast_glob(directory: Path, pattern: str):
                calls.append((directory.name, pattern))
                return real_fast_glob(directory, pattern)

            anime_assets._anime_tree_files.cache_clear()
            anime_assets._ANIME_TREE_PATH_INDEX = None
            anime_assets._ANIME_TREE_SORTED_STEMS = None
            with (
                patch.object(anime_assets, "ANIME_RESOURCE_DIRS", [text_root, mono_root]),
                patch.object(anime_assets, "fast_glob_files", side_effect=recording_fast_glob),
            ):
                missing = anime_assets._find_anime_tree_path(
                    "f_dlgtl_missing_sub_1.json"
                )
            anime_assets._anime_tree_files.cache_clear()
            anime_assets._ANIME_TREE_PATH_INDEX = None
            anime_assets._ANIME_TREE_SORTED_STEMS = None

            self.assertFalse(missing.exists())
            self.assertIn(("MonoBehaviour", "f_dlgtl_*.json"), calls)
            self.assertNotIn(
                ("MonoBehaviour", "f_dlgtl_missing_sub_1*.json"),
                calls,
            )

    def test_anime_pattern_cache_does_not_evict_broad_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            calls: list[str] = []

            def recording_fast_glob(_directory: Path, pattern: str):
                calls.append(pattern)
                return []

            anime_assets._anime_tree_files.cache_clear()
            with (
                patch.object(anime_assets, "ANIME_RESOURCE_DIRS", [root]),
                patch.object(
                    anime_assets,
                    "fast_glob_files",
                    side_effect=recording_fast_glob,
                ),
            ):
                anime_assets._anime_tree_files("dlg_*.json")
                for index in range(40):
                    anime_assets._anime_tree_files(f"exact_{index}*.json")
                anime_assets._anime_tree_files("dlg_*.json")
            anime_assets._anime_tree_files.cache_clear()

            self.assertEqual(1, calls.count("dlg_*.json"))

    def test_mission_recovery_report_writer_preserves_payload_in_compact_json(self) -> None:
        payload = {
            "missions": [{"id": "test", "rows": [1, 2, 3]}],
            "summary": {"missionCount": 1},
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "report.json"
            mission_recovery.write_json(path, payload)
            encoded = path.read_text(encoding="utf-8")

        self.assertEqual(payload, json.loads(encoded))
        self.assertNotIn("\n", encoded)
        self.assertNotIn(": ", encoded)

    def test_cached_anime_payload_is_not_mutated_by_dialog_tree_loader(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "dlg_fixture.json"
            decoded = {
                "type": "Beyond.Gameplay.DialogTree",
                "nodes": [{"$type": "Beyond.Gameplay.DialogTreeFinishNode"}],
                "connections": [],
            }
            path.write_text(
                json.dumps({
                    "Name": "dlg_fixture_asset",
                    "m_Script": base64.b64encode(
                        json.dumps(decoded).encode("utf-8")
                    ).decode("ascii"),
                }),
                encoding="utf-8",
            )
            anime_assets._load_anime_resource_payload.cache_clear()
            dialog_tree._DIALOG_TREE_SOURCE_CACHE.clear()
            first = anime_assets._load_anime_resource_payload(path)
            second = anime_assets._load_anime_resource_payload(path)
            self.assertIs(first, second)

            with patch.object(dialog_tree, "_find_anime_tree_path", return_value=path):
                source = dialog_tree._load_dialog_tree_source("dlg_fixture")

            self.assertIsInstance(source, dict)
            cached = anime_assets._load_anime_resource_payload(path)
            self.assertEqual("dlg_fixture_asset", cached.get("_assetName"))
            self.assertNotIn("$id", cached["nodes"][0])

    def test_levelscript_dialog_cache_preserves_embedded_substring_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            level_root = Path(temp_dir)
            level_dir = level_root / "map_test_lv001"
            level_dir.mkdir()
            (level_dir / "7.json").write_bytes(
                b"\x00prefix_dlg_mission_with_parts_12_suffix\x00dlg_other_1\x00"
            )
            level_bindings._LEVELSCRIPT_DIALOG_FILES_BY_LEVEL.clear()
            level_bindings._LEVELSCRIPT_DIALOGS_BY_LEVEL_MISSION.clear()
            level_bindings._MISSION_LEVELSCRIPT_CACHE.clear()
            with patch.object(level_bindings, "LEVELSCRIPT_DIR", level_root):
                rows = level_bindings._load_mission_levelscript_dialogs(
                    "mission_with_parts",
                    ["map_test_lv001"],
                )

            self.assertEqual(1, len(rows))
            self.assertEqual(["dlg_mission_with_parts_12"], rows[0]["dialogs"])
            self.assertEqual((0, 7, "7"), rows[0]["fileOrder"])

    def test_spatial_grid_preserves_cross_cell_match_and_pin_tie_order(self) -> None:
        vectors = [{
            "offset": 7,
            "position": {"x": 25.0, "y": 2.0, "z": 0.0},
        }]
        # Both q1 pins are exactly one unit away and straddle a cell boundary.
        # The former full scan selected the first one, so the indexed scan must
        # retain input order even though it visits neighboring cells.
        pins = [
            {
                "questId": "q1",
                "label": "first",
                "position": {"x": 26.0, "y": 2.0, "z": 0.0},
            },
            {
                "questId": "q1",
                "label": "second",
                "position": {"x": 24.0, "y": 2.0, "z": 0.0},
            },
            {
                "questId": "q2",
                "label": "outside-threshold",
                "position": {"x": 80.0, "y": 2.0, "z": 0.0},
            },
        ]
        script_ref = {
            "levelId": "map_test_lv001",
            "mapId": "map_test_lv001",
            "scriptId": "1",
        }
        with (
            patch.object(
                mission_recovery,
                "script_ref_from_levelscript_source",
                return_value=script_ref,
            ),
            patch.object(
                mission_recovery,
                "extract_levelscript_float_vectors",
                return_value=vectors,
            ),
        ):
            matches = mission_recovery.find_levelscript_spatial_matches(
                "fixture.json",
                pins,
            )

        self.assertEqual(["q1"], [row["questId"] for row in matches])
        self.assertEqual("first", matches[0]["pin"]["label"])
        self.assertEqual(1.0, matches[0]["distanceXZ"])

    def test_scene_key_resolution_cache_isolated_by_resolver(self) -> None:
        anime_assets._resolve_payload_scene_key.cache_clear()
        first_calls = []
        second_calls = []

        def first_resolver(value: str) -> str:
            first_calls.append(value)
            return "dlg_testm1_1" if value == "dlg_testm1_1" else ""

        def second_resolver(value: str) -> str:
            second_calls.append(value)
            return "dlg_testm1_2" if value == "dlg_testm1_1" else ""

        self.assertEqual(
            "dlg_testm1_1",
            anime_assets._resolve_payload_scene_key(
                "dlg_testm1_1", "testm1", first_resolver
            ),
        )
        self.assertEqual(
            "dlg_testm1_1",
            anime_assets._resolve_payload_scene_key(
                "dlg_testm1_1", "testm1", first_resolver
            ),
        )
        self.assertEqual(
            "dlg_testm1_2",
            anime_assets._resolve_payload_scene_key(
                "dlg_testm1_1", "testm1", second_resolver
            ),
        )
        self.assertEqual(["dlg_testm1_1"], first_calls)
        self.assertEqual(["dlg_testm1_1"], second_calls)
        anime_assets._resolve_payload_scene_key.cache_clear()


if __name__ == "__main__":
    unittest.main()

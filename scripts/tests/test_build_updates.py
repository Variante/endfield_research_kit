from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from scripts import build_updates

class CommandLineTests(unittest.TestCase):
    def test_current_scope_flags_map_to_internal_options(self) -> None:
        args = build_updates.parse_args(["--text-only", "--no-audio", "--exact"])

        self.assertTrue(args.skip_asset_updates)
        self.assertTrue(args.skip_audio_updates)
        self.assertTrue(args.hash_asset_updates)

    def test_retired_scope_aliases_are_rejected(self) -> None:
        for flag in (
            "--skip-asset-updates",
            "--skip-audio-updates",
            "--hash-asset-updates",
            "--include-asset-updates",
            "--include-audio-updates",
            "--old-export-root",
            "--game-root",
        ):
            with self.subTest(flag=flag), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    build_updates.parse_args([flag])

    def test_main_compares_exports_through_the_in_process_scanner(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old_root = root / "old"
            current_root = root / "current"
            relative_path = Path("structured/StreamingAssets/Table/Items.json")
            for export_root, value in ((old_root, 1), (current_root, 2)):
                source = export_root / relative_path
                source.parent.mkdir(parents=True)
                source.write_text(f'{{"value": {value}}}\n', encoding="utf-8")

            out_path = root / "webui" / "latest.json"
            with contextlib.redirect_stdout(io.StringIO()):
                result = build_updates.main(
                    [
                        "--previous-export-root",
                        str(old_root),
                        "--export-root",
                        str(current_root),
                        "--state-dir",
                        str(root / "state"),
                        "--out",
                        str(out_path),
                        "--characters-out",
                        str(root / "webui" / "characters.json"),
                        "--report-json",
                        str(root / "reports" / "summary.json"),
                        "--report-md",
                        str(root / "reports" / "summary.md"),
                        "--text-only",
                        "--no-history",
                    ]
                )

            self.assertEqual(result, 0)
            payload = build_updates.read_json(out_path, default={})
            self.assertEqual(payload["textTotals"]["modified"], 1)
            self.assertEqual(payload["assets"]["skipReason"], "skip_asset_updates")


class CharacterUpdateTests(unittest.TestCase):
    @staticmethod
    def write_tables(
        export_root: Path,
        characters: dict[str, object],
        *,
        names: dict[str, str] | None = None,
        language: str = "CN",
    ) -> None:
        records = []
        for key, row in characters.items():
            if not isinstance(row, dict):
                records.append(row)
                continue
            name_node = row.get("name")
            text_id = str(name_node.get("id") or "") if isinstance(name_node, dict) else ""
            primary_name = (names or {}).get(text_id, key)
            source = str(row.get("source") or "CharacterTable")
            records.append({
                "id": key,
                "kind": row.get("kind", "character"),
                "primaryName": primary_name,
                "names": [{"text": primary_name, "source": source, "key": key}],
                "aliases": [row.get("charId", key)],
                "evidence": [{"source": source, "type": "fixture", "key": key}],
                "sourceTypes": [source],
                "fixtureRow": row,
            })
        snapshot = export_root / "recovered/WebUI/characters" / f"{language}.json"
        build_updates.write_json(snapshot, {"language": language, "records": records}, indent=2, compact=False)

    def test_character_diff_covers_add_modify_delete_and_localized_names(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old_root = root / "old"
            new_root = root / "new"
            self.write_tables(
                old_root,
                {
                    "chr_0001_keep": {"charId": "keep", "name": {"id": 1}, "power": 10},
                    "chr_0002_change": {"charId": "change", "name": {"id": 2}, "power": 10},
                    "chr_0003_delete": {"charId": "delete", "name": {"id": 3}},
                    "chr_0004_translate": {"charId": "translate", "name": {"id": 4}},
                },
                names={"1": "保留", "2": "旧值", "3": "删除", "4": "旧译名"},
            )
            self.write_tables(
                new_root,
                {
                    "chr_0001_keep": {"power": 10, "name": {"id": 1}, "charId": "keep"},
                    "chr_0002_change": {"charId": "change", "name": {"id": 2}, "power": 11},
                    "chr_0004_translate": {"charId": "translate", "name": {"id": 4}},
                    "chr_0005_add": {"charId": "add", "name": {"id": 5}},
                },
                names={"1": "保留", "2": "旧值", "4": "新译名", "5": "新增"},
            )

            payload = build_updates.build_character_updates(old_root, new_root)

            self.assertTrue(payload["available"])
            self.assertEqual(payload["totals"], {"added": 1, "modified": 2, "deleted": 1, "changed": 4})
            by_key = {entry["characterKey"]: entry for entry in payload["entries"]}
            self.assertNotIn("chr_0001_keep", by_key)
            self.assertEqual(by_key["chr_0002_change"]["changedFields"], ["finalRecord"])
            self.assertEqual(by_key["chr_0004_translate"]["changedFields"], ["finalRecord"])
            self.assertEqual(by_key["chr_0004_translate"]["oldNames"], {"CN": "旧译名"})
            self.assertEqual(by_key["chr_0004_translate"]["newNames"], {"CN": "新译名"})
            self.assertEqual(by_key["chr_0003_delete"]["oldNames"], {"CN": "删除"})

    def test_character_diff_covers_non_character_table_final_records(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old_root = root / "old"
            new_root = root / "new"
            self.write_tables(old_root, {
                "story_actor": {"kind": "actor", "source": "Story actor registry"},
                "asset_npc": {"kind": "asset_npc", "source": "Exported assets", "assetCount": 1},
            })
            self.write_tables(new_root, {
                "story_actor": {"kind": "actor", "source": "Story actor registry"},
                "asset_npc": {"kind": "asset_npc", "source": "Exported assets", "assetCount": 2},
                "sns_actor": {"kind": "npc", "source": "SNSChatTable"},
            })

            payload = build_updates.build_character_updates(old_root, new_root)

            self.assertTrue(payload["available"])
            by_key = {entry["characterKey"]: entry for entry in payload["entries"]}
            self.assertEqual(by_key["asset_npc"]["status"], "modified")
            self.assertEqual(by_key["sns_actor"]["status"], "added")
            self.assertNotIn("story_actor", by_key)

    def test_missing_character_catalog_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_tables(root / "current", {"chr_0001_new": {"charId": "new"}})

            payload = build_updates.build_character_updates(root / "missing-old", root / "current")

            self.assertFalse(payload["available"])
            self.assertEqual(payload["entries"], [])
            self.assertEqual(payload["totals"]["changed"], 0)
            self.assertEqual(payload["skipReason"], "missing_or_invalid_character_catalog")
            self.assertIn("previous final character catalog missing", payload["diagnostics"])

    def test_empty_or_non_object_character_rows_fail_closed(self) -> None:
        for invalid_rows in ({}, {"chr_0001_bad": "not an object"}):
            with self.subTest(rows=invalid_rows), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                self.write_tables(root / "old", invalid_rows)
                self.write_tables(root / "new", {"chr_0002_new": {"charId": "new"}})

                payload = build_updates.build_character_updates(root / "old", root / "new")

                self.assertFalse(payload["available"])
                self.assertEqual(payload["entries"], [])
                self.assertTrue(any("final character catalog" in item for item in payload["diagnostics"]))

    def test_invalid_character_overlay_is_not_masked_by_valid_base(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_tables(root / "old", {"chr_0001_old": {"charId": "old"}})
            bad_overlay = root / "old/recovered/WebUI/characters/JP.json"
            bad_overlay.parent.mkdir(parents=True, exist_ok=True)
            bad_overlay.write_text("not json", encoding="utf-8")
            self.write_tables(root / "new", {"chr_0002_new": {"charId": "new"}})

            payload = build_updates.build_character_updates(root / "old", root / "new")

            self.assertFalse(payload["available"])
            self.assertIn("previous final character catalog invalid", payload["diagnostics"])
            self.assertEqual(
                payload["invalidSourceFiles"]["previous"],
                ["recovered/WebUI/characters/JP.json"],
            )

    def test_only_common_valid_localizations_are_compared(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            characters = {"chr_0001_keep": {"charId": "keep", "name": {"id": 1}}}
            self.write_tables(root / "old", characters, names={"1": "相同"})
            self.write_tables(root / "new", characters, names={"1": "相同"})
            old_table = root / "old/structured/StreamingAssets/Table"
            new_table = root / "new/structured/StreamingAssets/Table"
            build_updates.write_json(old_table / "I18nTextTable_JP.json", {"1": "旧名"}, indent=2, compact=False)
            build_updates.write_json(new_table / "I18nTextTable_EN.json", {"1": "New"}, indent=2, compact=False)
            (old_table / "I18nTextTable_KR.json").write_text("bad json", encoding="utf-8")
            build_updates.write_json(new_table / "I18nTextTable_KR.json", {"1": "새 이름"}, indent=2, compact=False)

            payload = build_updates.build_character_updates(root / "old", root / "new")

            self.assertTrue(payload["available"])
            self.assertEqual(payload["entries"], [])
            self.assertEqual(payload["localization"]["comparedLanguages"], ["CN"])
            self.assertEqual(payload["localization"]["skippedLanguages"], [])

    def test_main_writes_character_sidecar_in_text_only_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old_root = root / "old"
            new_root = root / "new"
            self.write_tables(old_root, {"chr_0001_old": {"charId": "old"}})
            self.write_tables(new_root, {"chr_0002_new": {"charId": "new"}})
            characters_out = root / "webui/data/updates/characters.json"

            with contextlib.redirect_stdout(io.StringIO()):
                result = build_updates.main(
                    [
                        "--previous-export-root", str(old_root),
                        "--export-root", str(new_root),
                        "--state-dir", str(root / "state"),
                        "--out", str(root / "webui/data/updates/latest.json"),
                        "--characters-out", str(characters_out),
                        "--report-json", str(root / "reports/summary.json"),
                        "--report-md", str(root / "reports/summary.md"),
                        "--text-only",
                        "--no-audio",
                        "--exact",
                        "--no-history",
                    ]
                )

            self.assertEqual(result, 0)
            payload = build_updates.read_json(characters_out, default={})
            self.assertEqual(payload["totals"], {"added": 1, "modified": 0, "deleted": 1, "changed": 2})


class StructuredSourceRelocationTests(unittest.TestCase):
    def test_added_persistent_file_is_suppressed_when_old_streaming_file_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old_root = root / "old"
            current_root = root / "current"
            old_file = old_root / "structured/StreamingAssets/Table/Items.json"
            old_file.parent.mkdir(parents=True)
            old_file.write_text("old contents", encoding="utf-8")

            entries, ignored = build_updates.filtered_game_entries(
                {"added": [{"path": "structured/Persistent/Table/Items.json"}]},
                suppress_changes=False,
                game_root=current_root,
                previous_game_root=old_root,
            )

            self.assertEqual(entries, [])
            self.assertEqual(ignored["added"], 1)
            self.assertEqual(ignored["added_structured_source_relocation"], 1)

    def test_added_file_without_old_counterpart_remains_an_update(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            entries, ignored = build_updates.filtered_game_entries(
                {"added": [{"path": "structured/Persistent/Table/New.json"}]},
                suppress_changes=False,
                game_root=root / "current",
                previous_game_root=root / "old",
            )

            self.assertEqual(len(entries), 1)
            self.assertFalse(ignored)

    def test_deleted_streaming_file_is_suppressed_when_current_persistent_file_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            current_root = root / "current"
            current_file = current_root / "structured/Persistent/Table/Items.json"
            current_file.parent.mkdir(parents=True)
            current_file.write_text("new contents", encoding="utf-8")

            entries, ignored = build_updates.filtered_game_entries(
                {"deleted": [{"path": "structured/StreamingAssets/Table/Items.json"}]},
                suppress_changes=False,
                game_root=current_root,
                previous_game_root=root / "old",
            )

            self.assertEqual(entries, [])
            self.assertEqual(ignored["deleted_structured_source_relocation"], 1)

    def test_asset_diff_suppresses_source_relabeling(self) -> None:
        old = {
            "StreamingAssets/Texture2D/icon.png": {
                "path": "StreamingAssets/Texture2D/icon.png",
                "kind": "image",
                "extension": ".png",
                "digest": "size:10",
            }
        }
        new = {
            "Persistent/Texture2D/icon.png": {
                "path": "Persistent/Texture2D/icon.png",
                "kind": "image",
                "extension": ".png",
                "digest": "size:12",
            }
        }

        diff = build_updates.build_asset_diff(old, new, sample_limit=10)

        self.assertEqual(diff["totals"]["changed"], 0)
        self.assertEqual(
            diff["ignoredStructuredSourceRelocations"],
            {"added": 1, "deleted": 1},
        )


class AnimestudioIndexUpdateTests(unittest.TestCase):
    def test_animestudio_indexes_and_transient_index_files_are_ignored(self) -> None:
        ignored_paths = (
            "recovered/AnimeStudio-cli/StreamingAssets/object_index/objects.jsonl.gz",
            "recovered/AnimeStudio-cli/Persistent/field_index/parts/part-001.jsonl",
            "recovered/AnimeStudio-cli/Persistent/field_index.tmp",
            "recovered/AnimeStudio-cli/Persistent/objects.jsonl.gz",
        )
        for path in ignored_paths:
            self.assertTrue(build_updates.is_ignored_game_update_path(path), path)

        for path in (
            "recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Texture2D/icon.png",
            "recovered/AnimeStudio-cli/Persistent/convert_by_type/AudioClip/voice.flac",
            "structured/StreamingAssets/Table/Items.json",
        ):
            self.assertFalse(build_updates.is_ignored_game_update_path(path), path)

    def test_full_scan_does_not_walk_animestudio_index_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            export_root = root / "export"
            kept = export_root / "recovered/AnimeStudio-cli/Persistent/convert_by_type/Texture2D/icon.png"
            ignored = export_root / "recovered/AnimeStudio-cli/Persistent/object_index/parts/objects.jsonl.gz"
            kept.parent.mkdir(parents=True)
            ignored.parent.mkdir(parents=True)
            kept.write_bytes(b"png")
            ignored.write_bytes(b"index")

            payload = build_updates.scan_export_tree(
                export_root=export_root,
                state_dir=root / "state",
                report_json=root / "report.json",
                report_md=root / "report.md",
                sample_limit=10,
                top_line_limit=10,
                write_history=False,
                include_relative_paths=[],
            )

            self.assertEqual(payload["scanned_files"], 1)
            self.assertEqual(payload["changes"]["added"], 1)
            self.assertEqual(payload["samples"]["added"][0]["path"], kept.relative_to(export_root).as_posix())

    def test_prune_file_inventory_excludes_animestudio_indexes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old_root = root / "old"
            current_root = root / "current"
            kept = old_root / "structured/Table/Items.json"
            ignored = old_root / "recovered/AnimeStudio-cli/Persistent/object_index/objects.jsonl.gz"
            kept.parent.mkdir(parents=True)
            ignored.parent.mkdir(parents=True)
            kept.write_text("same", encoding="utf-8")
            ignored.write_text("same", encoding="utf-8")
            (current_root / "structured/Table").mkdir(parents=True)
            (current_root / "structured/Table/Items.json").write_text("same", encoding="utf-8")

            self.assertEqual(
                build_updates.iter_existing_relative_files(old_root),
                ["structured/Table/Items.json"],
            )


if __name__ == "__main__":
    unittest.main()

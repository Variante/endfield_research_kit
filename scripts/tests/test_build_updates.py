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


if __name__ == "__main__":
    unittest.main()

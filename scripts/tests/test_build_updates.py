from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "build_updates.py"
if str(SCRIPT.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("build_updates", SCRIPT)
assert SPEC and SPEC.loader
build_updates = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = build_updates
SPEC.loader.exec_module(build_updates)


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

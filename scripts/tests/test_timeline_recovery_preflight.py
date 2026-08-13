from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.story_builder import dialog_tree, timeline_recovery


class TimelineRecoveryPreflightTests(unittest.TestCase):
    def test_dialog_timeline_cache_reloads_when_recovery_output_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            timeline_path = Path(temp_dir) / "timeline_line_orders.json"

            def write_lines(*line_ids: str) -> None:
                timeline_path.write_text(
                    json.dumps(
                        {
                            "dlg_test_1": {
                                "timeline": "dlgtl_test_1",
                                "file": "test.json",
                                "lineIds": list(line_ids),
                            }
                        }
                    ),
                    encoding="utf-8",
                )

            with patch.object(dialog_tree, "TIMELINE_LINE_ORDER_PATHS", [timeline_path]):
                dialog_tree.clear_timeline_order_caches()
                write_lines("line_a")
                self.assertEqual(
                    dialog_tree.load_dialog_timeline_line_orders("dlg_test_1")[0]["lineIds"],
                    ["line_a"],
                )
                write_lines("line_b", "line_c")
                self.assertEqual(
                    dialog_tree.load_dialog_timeline_line_orders("dlg_test_1")[0]["lineIds"],
                    ["line_b", "line_c"],
                )
                dialog_tree.clear_timeline_order_caches()

    def test_story_build_uses_current_timeline_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            expected = timeline_recovery.default_order_out(root)
            with (
                patch.object(timeline_recovery, "discover_asset_maps", return_value=[]),
                patch.object(timeline_recovery, "timeline_order_is_current", return_value=True),
                patch.object(timeline_recovery, "recover_timeline_line_orders") as recover,
            ):
                actual = timeline_recovery.ensure_timeline_orders_current(
                    "auto", export_root=root
                )
            self.assertEqual(actual, expected)
            recover.assert_not_called()

    def test_story_build_auto_mode_tolerates_missing_asset_maps(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with (
                patch.object(timeline_recovery, "discover_asset_maps", return_value=[]),
                patch.object(timeline_recovery, "timeline_order_is_current", return_value=False),
                patch.object(timeline_recovery, "recover_timeline_line_orders") as recover,
            ):
                actual = timeline_recovery.ensure_timeline_orders_current(
                    "auto", export_root=root
                )
            self.assertIsNone(actual)
            recover.assert_not_called()

    def test_story_build_always_mode_propagates_recovery_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with (
                patch.object(timeline_recovery, "discover_asset_maps", return_value=[root / "map.json"]),
                patch.object(timeline_recovery, "timeline_order_is_current", return_value=False),
                patch.object(
                    timeline_recovery,
                    "recover_timeline_line_orders",
                    side_effect=RuntimeError("broken timeline source"),
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "broken timeline source"):
                    timeline_recovery.ensure_timeline_orders_current(
                        "always", export_root=root
                    )

    def test_missing_and_empty_sources_fail_before_prior_extract_is_reset(self) -> None:
        for grouped in ({"missing.chk": [{}]}, {}):
            with self.subTest(grouped=bool(grouped)), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                asset_map = root / "map.json"
                asset_map.write_text("[]", encoding="utf-8")
                extract_dir = root / "timeline_extract"
                extract_dir.mkdir()
                sentinel = extract_dir / "keep.json"
                sentinel.write_text("{}", encoding="utf-8")
                config = timeline_recovery.TimelineRecoveryConfig(
                    export_root=root,
                    maps=[asset_map],
                    extract_dir=extract_dir,
                    order_out=root / "timeline_line_orders.json",
                )
                with (
                    patch.object(timeline_recovery, "load_entries", return_value=[]),
                    patch.object(timeline_recovery, "count_timeline_stems", return_value={}),
                    patch.object(
                        timeline_recovery,
                        "select_timeline_filter",
                        return_value=(lambda _entry: True, None, set()),
                    ),
                    patch.object(timeline_recovery, "group_by_source", return_value=grouped),
                    patch.object(
                        timeline_recovery,
                        "discover_full_monobehaviour_dirs",
                        return_value=[],
                    ),
                    patch.object(
                        timeline_recovery,
                        "resolve_cli",
                        side_effect=AssertionError("preflight must run first"),
                    ),
                ):
                    with self.assertRaises(FileNotFoundError):
                        timeline_recovery.recover_timeline_line_orders(config)
                self.assertTrue(sentinel.is_file())


if __name__ == "__main__":
    unittest.main()

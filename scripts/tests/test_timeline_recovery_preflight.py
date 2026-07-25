from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.story_builder import timeline_recovery


class TimelineRecoveryPreflightTests(unittest.TestCase):
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

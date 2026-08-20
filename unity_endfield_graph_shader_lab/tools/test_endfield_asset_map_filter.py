from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from endfield_asset_map_filter import iter_asset_entries  # noqa: E402


class AssetMapFilterTests(unittest.TestCase):
    def test_iter_asset_entries_yields_exact_asset_map_rows(self) -> None:
        rows = [
            {
                "Name": "P_fxui_endminm003_overview_01",
                "Container": "effects/prefabs/p_fxui_endminm003_overview_01.prefab",
                "Type": "Animator",
                "PathID": 101,
            },
            {
                "Name": "A_fx_endminf_ui_overview_02",
                "Container": "effects/prefabs/p_fxui_endminm003_overview_01.prefab",
                "Type": "AnimationClip",
                "PathID": 102,
            },
        ]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "assets.json"
            path.write_text(
                json.dumps({"AssetEntries": rows, "Unrelated": {"ignored": True}}, indent=2)
                + "\n",
                encoding="utf-8",
            )

            self.assertEqual(list(iter_asset_entries(path)), rows)


if __name__ == "__main__":
    unittest.main()

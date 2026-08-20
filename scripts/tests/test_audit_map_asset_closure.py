import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_map_asset_closure import iter_asset_entries


class AuditMapAssetClosureTests(unittest.TestCase):
    def test_streams_asset_entries_across_small_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "assets.json"
            expected = [
                {"Name": "mesh", "Container": "assets/indie/dg002/a.prefab", "PathID": 1},
                {"Name": "other", "Container": "assets/map01/b.prefab", "PathID": 2},
            ]
            path.write_text(json.dumps({"GameType": "test", "AssetEntries": expected}), encoding="utf-8")
            self.assertEqual(list(iter_asset_entries(path, chunk_size=7)), expected)


if __name__ == "__main__":
    unittest.main()

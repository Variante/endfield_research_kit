from __future__ import annotations

import sys
import unittest
from pathlib import Path


TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from verify_roster_item_renderer_bindings import audit  # noqa: E402


class RealItemRendererBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = audit()

    def test_all_generated_item_renderers_keep_exact_owner_paths(self) -> None:
        # The current source-derived Zhuang Fangyi set contains seven exact
        # body/deco renderers (including the separated piaodai Effect clone);
        # Liino adds six exact owner-qualified renderers.
        self.assertEqual(self.result["recovered_item_renderer_count"], 108)
        self.assertEqual(self.result["failures"], [])

    def test_dapan_source_path_ids_and_generated_bindings_are_complete(self) -> None:
        rows = self.result["dapan_bindings"]
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(row["source_root_bone_path_id"] for row in rows))
        self.assertTrue(all(all(row["source_bone_path_ids"]) for row in rows))


if __name__ == "__main__":
    unittest.main()

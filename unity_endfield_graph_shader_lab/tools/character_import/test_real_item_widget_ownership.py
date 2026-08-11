from __future__ import annotations

import sys
import unittest
from pathlib import Path


TOOLS_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = TOOLS_ROOT.parent
REPO_ROOT = LAB_ROOT.parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from character_import.catalog import build_import_plan  # noqa: E402
from character_import.widgets import build_item_widget_additions  # noqa: E402


COMPACT_MAPS = (
    REPO_ROOT
    / "scratch/character_ui_import/compact_asset_maps/StreamingAssets/maps/character_manifest_assets.json",
    REPO_ROOT
    / "scratch/character_ui_import/compact_asset_maps/Persistent/maps/character_manifest_assets.json",
)


class RealItemWidgetOwnershipIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not all(path.is_file() for path in COMPACT_MAPS):
            raise unittest.SkipTest("real compact character manifest maps are unavailable")
        cls.plan = build_import_plan(
            clip_scope="all-ui",
            selected_actor_tokens={"mifu", "tangtang"},
        )

    def manifest_widget_rows(self, actor: str) -> dict[str, dict]:
        character = next(
            item for item in self.plan["characters"] if item["actor_token"] == actor
        )
        additions = build_item_widget_additions(character, COMPACT_MAPS)
        return {str(item["name"]): item for item in additions["clips"]}

    def test_real_mifu_controller_owned_clips_build_under_deco_2(self) -> None:
        rows = self.manifest_widget_rows("mifu")
        for name in (
            "A_item_widget_mifu_01_ui_disappear_01",
            "A_item_widget_mifu_01_ui_idle_to_relax",
            "A_item_widget_mifu_01_ui_react",
            "A_item_widget_mifu_01_ui_relax_loop",
            "A_item_widget_mifu_01_ui_relax_sp_02",
        ):
            self.assertEqual(rows[name]["widget_prefab"], "chr_0031_mifu_deco_2")

    def test_real_tangtang_dragonfly_disappear_preserves_both_deco_owners(self) -> None:
        rows = self.manifest_widget_rows("tangtang")
        self.assertEqual(
            rows[
                "A_npc_animal_dragonfly_tangtang_disappear_01__"
                "chr_0027_tangtang_deco_2"
            ]["widget_prefab"],
            "chr_0027_tangtang_deco_2",
        )
        self.assertEqual(
            rows[
                "A_npc_animal_dragonfly_tangtang_disappear_01__"
                "chr_0027_tangtang_deco_3"
            ]["widget_prefab"],
            "chr_0027_tangtang_deco_3",
        )


if __name__ == "__main__":
    unittest.main()

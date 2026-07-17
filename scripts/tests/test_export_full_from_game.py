from __future__ import annotations

import unittest
import sys
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from export_full_from_game import (
    ANIMESTUDIO_STORY_JSON_TYPES,
    animestudio_stage_options_for_scope,
    should_merge_animestudio_type_jobs,
)


class AnimeStudioStageOptionsTests(unittest.TestCase):
    def test_story_json_is_not_asset_map_filtered(self) -> None:
        options = animestudio_stage_options_for_scope("story")

        self.assertEqual(options["json_by_type"]["types"], ANIMESTUDIO_STORY_JSON_TYPES)
        self.assertFalse(options["json_by_type"]["asset_map_filter"])

    def test_combined_json_keeps_story_sources_outside_asset_map(self) -> None:
        options = animestudio_stage_options_for_scope("all", "full")

        for type_spec in ANIMESTUDIO_STORY_JSON_TYPES:
            self.assertIn(type_spec, options["json_by_type"]["types"])
        self.assertFalse(options["json_by_type"]["asset_map_filter"])

    def test_asset_only_json_can_use_asset_map(self) -> None:
        options = animestudio_stage_options_for_scope("assets", "full")

        self.assertTrue(options["json_by_type"]["asset_map_filter"])

    def test_auto_does_not_merge_broad_story_json(self) -> None:
        items = [{"item_name": name} for name in ("TextAsset", "MonoBehaviour", "PlayableDirector")]

        self.assertFalse(should_merge_animestudio_type_jobs("json_by_type", items, "auto"))
        self.assertTrue(
            should_merge_animestudio_type_jobs(
                "json_by_type",
                items,
                "auto",
                asset_map_filter=True,
            )
        )
        self.assertTrue(should_merge_animestudio_type_jobs("json_by_type", items, "merged"))


if __name__ == "__main__":
    unittest.main()

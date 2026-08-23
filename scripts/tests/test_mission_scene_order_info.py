from __future__ import annotations

import unittest

from scripts.story_builder.mission_recovery import build_scene_order_info


class MissionSceneOrderInfoTests(unittest.TestCase):
    def test_spatial_proximity_cannot_assign_story_order(self) -> None:
        result = build_scene_order_info(
            {},
            [{
                "questId": "e0m0_q#1",
                "questOrder": 0,
                "attachedSceneKeys": ["cutscene_e0m0_13"],
                "spatialSourceMatches": [{"sceneKey": "cutscene_e0m0_13"}],
            }],
            [{"questId": "e0m0_q#1"}],
            {"cutscene_e0m0_13": {
                "spatialQuestCandidates": [{"questOrder": 0}],
                "evidenceKinds": ["sourceBackedLevelScriptSpatialProximity"],
            }},
            {"cutscene_e0m0_13": "cutscene"},
        )

        self.assertIsNone(result["cutscene_e0m0_13"]["questOrder"])
        self.assertEqual(result["cutscene_e0m0_13"]["orderSource"], "numericFallback")
        self.assertEqual(result["cutscene_e0m0_13"]["confidence"], "fallback")

    def test_explicit_scene_placement_quest_remains_source_backed(self) -> None:
        result = build_scene_order_info(
            {},
            [{"questId": "e0m0_q#1", "questOrder": 4, "flowIndex": 7}],
            [],
            {"radio_e0m0_9": {"questIds": ["e0m0_q#1"]}},
            {"radio_e0m0_9": "radio"},
        )

        self.assertEqual(result["radio_e0m0_9"]["questOrder"], 4)
        self.assertEqual(result["radio_e0m0_9"]["orderSource"], "scenePlacementQuest")
        self.assertEqual(result["radio_e0m0_9"]["confidence"], "source-backed")


if __name__ == "__main__":
    unittest.main()

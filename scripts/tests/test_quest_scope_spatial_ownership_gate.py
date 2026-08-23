from __future__ import annotations

import unittest

from scripts.mission_pipeline.quest_scope_projection import (
    classify_spatial_route_mission_ownership_gate,
)


class QuestScopeSpatialOwnershipGateTests(unittest.TestCase):
    def test_complete_context_still_fails_closed_without_activation_contract(self) -> None:
        placement = {
            "storyKey": "dlg_fixture", "missionId": "m1",
            "questId": "m1_q1", "scriptIds": ["100"],
        }
        manifest = {
            "spatialPlaybackRoute": {
                "status": "exact_native_local_trigger_playback",
                "observations": [{
                    "status": "exact_local_trigger_volume", "scriptId": "100",
                }],
            },
            "routes": [{
                "relation": "authoritative_scope_leveldata_mission_context",
                "missionId": "m1", "scriptIds": ["100"],
            }],
        }
        result = classify_spatial_route_mission_ownership_gate(
            placement, manifest, [placement]
        )
        self.assertEqual(
            "questActivatesLocalTriggerContract", result["firstFailedGate"]
        )
        self.assertFalse(result["ownershipPromotion"])
        self.assertTrue(result["gates"]["uniqueAuthoritativeLevelDataMissionHost"])

    def test_reports_ambiguous_quest_scope_before_activation_boundary(self) -> None:
        placement = {
            "storyKey": "dlg_fixture", "missionId": "m1",
            "questId": "m1_q1", "scriptIds": ["100"],
        }
        other = {**placement, "questId": "m1_q2"}
        result = classify_spatial_route_mission_ownership_gate(
            placement,
            {"spatialPlaybackRoute": {
                "status": "exact_native_local_trigger_playback",
                "observations": [{
                    "status": "exact_local_trigger_volume", "scriptId": "100",
                }],
            }},
            [placement, other],
        )
        self.assertEqual("uniqueMissionQuestScope", result["firstFailedGate"])
        self.assertFalse(result["ownershipPromotion"])


if __name__ == "__main__":
    unittest.main()

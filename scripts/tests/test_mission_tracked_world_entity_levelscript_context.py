from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from scripts.story_builder import level_bindings
from scripts.story_builder.context import ROOT
from scripts.story_builder.level_bindings import (
    _exact_local_leader_trigger_volume,
    build_levelscript_native_story_playback_index,
    build_mission_tracked_world_entity_levelscript_contexts,
)


def current_mission_flows() -> dict[str, dict]:
    flows: dict[str, dict] = {}
    for path in sorted((ROOT / "webui/data/lang/CN/mission").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("flow"), dict):
            flows[path.stem] = payload["flow"]
    return flows


class MissionTrackedWorldEntityLevelScriptContextTests(unittest.TestCase):
    def test_trigger_volume_requires_one_local_decoded_leader_shape(self) -> None:
        occurrence = {
            "sourceFile": "fixture.json",
            "scriptId": "901",
        }
        detail = {"triggerSlotIdFilter": 80001}
        volume = {
            "triggerVolumeType": "Leader",
            "unionTag": 1,
            "memberCount": 8,
            "keySlotId": 80001,
            "slotId": 80001,
            "waitSrvRes": False,
            "shapeList": {
                "status": "present",
                "parseStatus": "decoded",
                "shapes": [{"shapeType": "Box"}],
            },
        }
        summary = {
            "triggerVolumesDetails": {
                "status": "present",
                "parseStatus": "decoded",
                "volumes": [volume],
            }
        }
        with patch.object(
            level_bindings,
            "_levelscript_binary_summary",
            return_value=summary,
        ):
            self.assertEqual(
                80001,
                _exact_local_leader_trigger_volume(occurrence, detail)["slotId"],
            )
            volume["waitSrvRes"] = True
            self.assertEqual(
                {},
                _exact_local_leader_trigger_volume(occurrence, detail),
            )

    def test_current_original_data_contains_the_six_residual_candidates(self) -> None:
        rows = build_mission_tracked_world_entity_levelscript_contexts(
            build_levelscript_native_story_playback_index(),
            current_mission_flows(),
        )
        by_key = {row["storyKey"]: row for row in rows}
        expected = {
            "radio_sm2l5m1_2",
            "radio_sm2l5m1_19",
            "radio_sm2l5m1_21",
            "radio_sm2l5m1_22",
            "radio_sm2l5m1_23",
            "radio_sm2l5m1_25",
        }
        self.assertTrue(expected.issubset(by_key))
        self.assertEqual(
            {"sm2l5m1"},
            {by_key[key]["missionId"] for key in expected},
        )
        self.assertEqual(
            {"23200013003", "23200013008", "23200013009", "23200013031"},
            {
                occurrence["scriptId"]
                for key in expected
                for occurrence in by_key[key]["occurrences"]
            },
        )
        self.assertEqual(
            ["23200013030"],
            by_key["radio_sm2l5m1_2"]["worldEntityIds"],
        )
        self.assertEqual(
            ["23200013387"],
            by_key["radio_sm2l5m1_19"]["worldEntityIds"],
        )

    def test_one_unresolved_occurrence_rejects_the_whole_story_key(self) -> None:
        native_index = build_levelscript_native_story_playback_index()
        modified_index = {
            key: list(rows)
            for key, rows in native_index.items()
        }
        target = "radio_sm2l5m1_19"
        modified_index[target] = [
            *modified_index[target],
            {
                **modified_index[target][0],
                "recordOffset": -1,
                "nativeEventOwners": [],
            },
        ]
        rows = build_mission_tracked_world_entity_levelscript_contexts(
            modified_index,
            current_mission_flows(),
        )
        self.assertNotIn(target, {row["storyKey"] for row in rows})

    def test_current_stage_context_recovers_exactly_nine_residual_story_files(self) -> None:
        rows = build_mission_tracked_world_entity_levelscript_contexts(
            build_levelscript_native_story_playback_index(),
            current_mission_flows(),
            receiver_family="stage",
        )
        by_key = {row["storyKey"]: row for row in rows}
        self.assertEqual({
            "cutscene_map02_lv004_lindi_1",
            "cutscene_map02_lv004_lindi_2",
            "radio_e2m3_13",
            "radio_e2m3_14",
            "radio_e2m3_5",
            "radio_e8m2_4",
            "radio_e8m2_6",
            "radio_gm02m14_7",
            "radio_sm2l5m1_5",
        }, set(by_key))
        self.assertEqual(
            {"e2m3", "e8m1", "sm2l5m1"},
            {row["missionId"] for row in rows},
        )
        self.assertEqual(
            2,
            len(by_key["radio_e2m3_13"]["occurrences"]),
        )
        self.assertEqual(
            1,
            len(by_key["cutscene_map02_lv004_lindi_1"]["preloadOccurrences"]),
        )
        self.assertEqual(
            ["23200013030"],
            by_key["radio_gm02m14_7"]["worldEntityIds"],
        )


if __name__ == "__main__":
    unittest.main()

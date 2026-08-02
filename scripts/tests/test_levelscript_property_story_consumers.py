from __future__ import annotations

import copy
import unittest

from scripts.story_builder.language_bundle import (
    select_levelscript_property_story_consumers,
)


class LevelScriptPropertyStoryConsumerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.conditions = {("level_a", "1001"): [{
            "missionId": "mission_a",
            "questId": "mission_a_q#1",
            "conditionType": "CheckLevelScriptPropertyBool",
            "conditionKey": "allTalkFinished",
            "conditionValue": True,
            "sourceFile": "MissionRuntimeAsset/mission_a.json",
        }]}
        self.playback = {"radio_mission_a_1": [{
            "levelId": "level_a",
            "scriptId": "1001",
            "sourceFile": "LevelScriptData/level_a/1001.json",
            "localId": 13,
            "actionName": "PlayRadio",
            "nativeEventOwners": [{
                "status": "exact_serialized_control_path",
                "headerName": "ScriptEvent_OnPropertyChanged",
                "downstreamControlStatus": "exact_serialized_typed_reachability",
                "eventDetail": {
                    "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                    "transport": "local-level-script-variable-event",
                    "propertyKeyFilter": "allTalkFinished",
                    "validateParam": {"constValue": True},
                },
                "path": [{
                    "localId": 13,
                    "recordClass": "play_radio",
                }],
            }],
        }]}

    def test_selects_exact_typed_property_consumer(self) -> None:
        rows = select_levelscript_property_story_consumers(
            self.conditions,
            self.playback,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["questId"], "mission_a_q#1")
        self.assertEqual(rows[0]["storyKey"], "radio_mission_a_1")
        self.assertEqual(rows[0]["conditionKey"], "allTalkFinished")
        self.assertEqual(
            rows[0]["sourceFiles"],
            [
                "LevelScriptData/level_a/1001.json",
                "MissionRuntimeAsset/mission_a.json",
            ],
        )

    def test_rejects_shared_script_without_exact_property_path(self) -> None:
        for mutation in ("condition_key", "event_key", "control_path"):
            with self.subTest(mutation=mutation):
                conditions = copy.deepcopy(self.conditions)
                playback = copy.deepcopy(self.playback)
                if mutation == "condition_key":
                    conditions[("level_a", "1001")][0]["conditionKey"] = "other"
                elif mutation == "event_key":
                    playback["radio_mission_a_1"][0]["nativeEventOwners"][0][
                        "eventDetail"
                    ]["propertyKeyFilter"] = "other"
                else:
                    playback["radio_mission_a_1"][0]["nativeEventOwners"][0][
                        "downstreamControlStatus"
                    ] = "unresolved"
                self.assertEqual(
                    select_levelscript_property_story_consumers(
                        conditions,
                        playback,
                    ),
                    [],
                )

    def test_selects_exact_false_property_consumer_without_special_case(self) -> None:
        conditions = copy.deepcopy(self.conditions)
        playback = copy.deepcopy(self.playback)
        conditions[("level_a", "1001")][0]["conditionValue"] = False
        playback["radio_mission_a_1"][0]["nativeEventOwners"][0][
            "eventDetail"
        ]["validateParam"]["constValue"] = False

        rows = select_levelscript_property_story_consumers(conditions, playback)

        self.assertEqual(len(rows), 1)
        self.assertIs(rows[0]["conditionValue"], False)


if __name__ == "__main__":
    unittest.main()

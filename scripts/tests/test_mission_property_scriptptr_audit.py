from pathlib import Path
import unittest

from scripts.story_recovery import build_mission_property_scriptptr_audit as audit


class MissionPropertyScriptPtrAuditTests(unittest.TestCase):
    def test_tracking_filter_census_keeps_only_tracking_conditions(self):
        condition = {
            "$type": (
                "Beyond.Gameplay.SimpleConditionCheckMissionVariableInt, "
                "Gameplay.Beyond"
            ),
            "missionId": "testm1",
            "missionVarName": "track_1",
            "compareOperator": 0,
            "compareTarget": 1,
        }
        payload = {
            "questDatas": [{
                "questId": "testm1_q#1",
                "objectives": [{
                    "condition": condition,
                    "trackingInfoList": [{
                        "$type": (
                            "Beyond.Gameplay.PosTrackingInfo, Gameplay.Beyond"
                        ),
                        "useFilterCondition": True,
                        "filterCondition": condition,
                    }],
                }],
            }],
        }
        rows = audit.scan_tracking_property_filters(
            payload,
            Path("fixture/testm1.json"),
        )
        self.assertEqual(rows, [{
            "source": "fixture/testm1.json",
            "questId": "testm1_q#1",
            "trackingIndex": 0,
            "trackingType": "PosTrackingInfo",
            "missionId": "testm1",
            "missionVarName": "track_1",
            "compareOperator": 0,
            "compareTarget": 1,
        }])


if __name__ == "__main__":
    unittest.main()

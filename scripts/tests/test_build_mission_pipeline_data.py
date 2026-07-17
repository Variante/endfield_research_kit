import json
import tempfile
import unittest
from pathlib import Path


from scripts import build_mission_pipeline_data as pipeline


def condition(kind, **values):
    return {"$type": f"Beyond.Gameplay.{kind}, Gameplay.Beyond", "uniqueId": f"id_{kind}", **values}


class MissionPipelineBuilderTests(unittest.TestCase):
    def fixture(self):
        return {
            "missionId": "testm1",
            "missionName": {"key": "testm1_name"},
            "missionDescription": {"key": "testm1_desc"},
            "levelId": "map_test",
            "mainPathQuests": ["testm1_q#1", "testm1_q#2"],
            "questDic": {
                "testm1_q#1": {
                    "questId": "testm1_q#1",
                    "flowIndex": 0,
                    "showMode": 1,
                    "prevQuestIdList": [],
                    "objectiveList": [{
                        "description": {"key": "objective_1"},
                        "condition": condition("ReachDestination", _areaId={"constValue": "area"}),
                    }],
                },
                "testm1_q#2": {
                    "questId": "testm1_q#2",
                    "flowIndex": 1,
                    "showMode": 1000,
                    "prevQuestIdList": ["testm1_q#1"],
                    "objectiveList": [{
                        "description": {"key": "objective_2"},
                        "condition": condition(
                            "CheckTalkOptionFinish",
                            _dialogId={"constValue": "dlg_test"},
                            _finishId={"constValue": 0},
                        ),
                    }],
                },
                "testm1_q#3": {
                    "questId": "testm1_q#3",
                    "flowIndex": 0,
                    "showMode": 1,
                    "prevQuestIdList": ["testm1_q#1"],
                    "objectiveList": [{
                        "description": {"key": "objective_3"},
                        "condition": condition(
                            "CombineCondition",
                            conditionEvalString="{0}and{1}",
                            subConditions=[
                                condition("CheckQuestState", _questId={"constValue": "testm1_q#1"}, _targetQuestState={"constValue": 3}),
                                condition("CheckQuestState", _questId={"constValue": "testm1_q#2"}, _targetQuestState={"constValue": 3}),
                            ],
                        ),
                    }],
                },
            },
            "clientActionMapKey": [],
            "clientActionMapValue": [],
        }

    def test_build_mission_preserves_finish_zero_and_condition_dependencies(self):
        payload, summary = pipeline.build_mission(self.fixture(), pipeline.ROOT / "fixture" / "testm1.json")
        nodes = {row["id"]: row for row in payload["nodes"]}
        finish = nodes["testm1_q#2"]["objectives"][0]["dialogFinishes"][0]
        self.assertEqual(finish, {"dialogId": "dlg_test", "finishId": 0})
        self.assertEqual(nodes["testm1_q#1"]["network"]["outbound"], "objective_progress")
        self.assertEqual(nodes["testm1_q#2"]["network"]["outbound"], "dialog_finish")
        dependencies = [edge for edge in payload["edges"] if edge["type"] == "condition_dependency"]
        self.assertEqual({(edge["source"], edge["target"], edge["targetState"]) for edge in dependencies}, {
            ("testm1_q#1", "testm1_q#3", 3),
            ("testm1_q#2", "testm1_q#3", 3),
        })
        self.assertEqual(summary["activeJoinCount"], 1)
        self.assertEqual(summary["exactFinishCount"], 1)

    def test_build_all_writes_lazy_index_and_mission_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mission_root = root / "input"
            output_root = root / "output"
            mission_root.mkdir()
            (mission_root / "testm1.json").write_text(json.dumps(self.fixture()), encoding="utf-8")
            (mission_root / "testm1_meta.json").write_text("{}", encoding="utf-8")
            index = pipeline.build_all(mission_root, output_root)
            self.assertEqual(index["counts"], {"missions": 1, "quests": 3, "caseStudies": 0})
            self.assertTrue((output_root / "index.json").is_file())
            self.assertTrue((output_root / "missions" / "testm1.json").is_file())
            self.assertEqual(index["runtimeContract"]["outbound"][1]["message"], "CS_UPDATE_QUEST_OBJECTIVE")


if __name__ == "__main__":
    unittest.main()

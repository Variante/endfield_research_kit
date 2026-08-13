import unittest

from scripts.story_builder.mission_flow import (
    build_mission_map_pins,
    level_host_type,
    parse_level_ref_name,
)


class MissionMapPinsTests(unittest.TestCase):
    def test_parses_leveldata_mission_host_references(self):
        self.assertEqual(
            parse_level_ref_name("map01_lv005_lv_data_sub_mission_e1m2_v2.json"),
            {"level": "map01_lv005", "kind": "mission", "token": "e1m2"},
        )
        self.assertEqual(
            parse_level_ref_name("base01_lv001_lv_data_sub_task.json"),
            {"level": "base01_lv001", "kind": "plain", "token": "task"},
        )
        self.assertIsNone(parse_level_ref_name("map01_lv005_lv_data.json"))
        self.assertIsNone(parse_level_ref_name("map01_lv005_lv_data_sub_.json"))

    def test_classifies_leveldata_host_types(self):
        self.assertEqual(level_host_type("map01_lv005"), "map")
        self.assertEqual(level_host_type("base01_lv001"), "map")
        self.assertEqual(level_host_type("dung01_lv001"), "dungeon")
        self.assertEqual(level_host_type("indie01_lv001"), "indie")
        self.assertEqual(level_host_type("blackbox_speedlimit"), "blackbox")
        self.assertEqual(level_host_type("rogue01"), "other")

    def test_merges_identical_pins_and_orders_by_flow(self):
        common_pin = {
            "scene": "scene_a",
            "sourceType": "tracking",
            "trackingType": "npc",
            "position": {"x": 1.0004, "y": 2, "z": 3},
            "npcProxyId": "npc_1",
            "radius": 4,
        }
        flow = {
            "quests": [
                {"id": "q2", "flowIndex": 2, "pins": [dict(common_pin)]},
                {"id": "q1", "flowIndex": 1, "pins": [dict(common_pin)]},
                {
                    "id": "q0",
                    "flowIndex": 0,
                    "pins": [
                        {
                            "scene": "scene_b",
                            "sourceType": "area",
                            "position": {"x": 9, "y": 0, "z": 0},
                        }
                    ],
                },
            ]
        }

        pins = build_mission_map_pins(flow)

        self.assertEqual([pin["scene"] for pin in pins], ["scene_b", "scene_a"])
        self.assertEqual(pins[1]["questIds"], ["q2", "q1"])
        self.assertEqual(pins[1]["flowIndices"], [2, 1])
        self.assertEqual(pins[1]["npcProxyId"], "npc_1")
        self.assertEqual(pins[1]["radius"], 4)

    def test_empty_flow_returns_no_pins(self):
        self.assertEqual(build_mission_map_pins(None), [])
        self.assertEqual(build_mission_map_pins({"quests": []}), [])


if __name__ == "__main__":
    unittest.main()

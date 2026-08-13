import unittest

from scripts.story_builder.mission_flow import build_mission_map_pins


class MissionMapPinsTests(unittest.TestCase):
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

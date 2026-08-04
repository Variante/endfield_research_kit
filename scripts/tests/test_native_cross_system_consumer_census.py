import unittest

from scripts.story_recovery import build_native_cross_system_consumer_census as census


def method(type_name, method_name):
    return {"type": type_name, "method": method_name}


class NativeCrossSystemConsumerCensusTests(unittest.TestCase):
    def test_shared_or_mixed_family_pointer_is_rejected(self):
        shared = [method("Beyond.Gameplay.MissionSystem", "GetMissionState")]
        shared.extend(method("Beyond.Gameplay.Other", f"Alias{index}") for index in range(8))
        mixed = [
            method("Beyond.Gameplay.MissionSystem", "GetMissionState"),
            method("Beyond.Gameplay.Core.DynamicScene.DynamicSceneEntitySystem", "GetEntity"),
        ]

        self.assertFalse(census.admissible_pointer_aliases(shared))
        self.assertFalse(census.admissible_pointer_aliases(mixed))

    def test_classification_is_api_shape_based(self):
        self.assertEqual(
            census.classify_candidate(
                ["dynamic_scene", "mission_system"],
                ["Beyond.Gameplay.MissionSystem.GetQuestState"],
            ),
            "mission_state_controls_dynamic_component_availability",
        )
        self.assertEqual(
            census.classify_candidate(
                ["dynamic_scene", "level_script"],
                [
                    "Beyond.Gameplay.Core.DynamicScene.DynamicSceneTrigger.get_position",
                    "Beyond.Gameplay.Core.LevelScriptTriggerVolumeOverlapUnit.get_rotation",
                ],
            ),
            "shared_trigger_geometry_adapter",
        )

    def test_unknown_shape_fails_closed(self):
        self.assertEqual(
            census.classify_candidate(
                ["dynamic_scene", "story"],
                ["Beyond.Gameplay.Core.DynamicScene.Unknown.DoThing"],
            ),
            "unreviewed_cross_system_call_shape",
        )

    def test_validator_names_failed_gate_and_bounded_counts(self):
        rows = [
            {"classification": key}
            for key, count in census.EXPECTED_CLASS_COUNTS.items()
            for _ in range(count)
        ]
        self.assertEqual(census.validate_counts(rows, "GameAssembly.dll"), [])

        rows.pop()
        failures = census.validate_counts(rows, "GameAssembly.dll")

        self.assertEqual(failures[0]["validator"], "nativeCrossSystemConsumerCensus")
        self.assertEqual(failures[0]["gate"], "expectedClassificationCount")
        self.assertEqual(failures[0]["sourceFile"], "GameAssembly.dll")
        self.assertEqual(failures[0]["expected"], 1)
        self.assertEqual(failures[0]["actual"], 0)


if __name__ == "__main__":
    unittest.main()

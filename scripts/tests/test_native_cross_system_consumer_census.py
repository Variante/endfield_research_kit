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

    def test_indirect_class_initializer_guard_is_reviewed_by_shape(self):
        texts = [
            "mov rax, [rcx+0xb0]",
            "cmp [rax+0x20], 0x0",
            "mov rax, [rcx+0xb0]",
            "call [rax]",
        ]
        self.assertEqual(
            census.classify_indirect_call_window(texts, 3),
            "il2cpp_class_initializer_guard",
        )
        self.assertEqual(
            census.classify_indirect_call_window(["mov rax, [rcx]", "call [rax]"], 1),
            "unreviewed_indirect_call_shape",
        )

    def test_closure_validator_fails_closed_on_new_story_reachability(self):
        counts = dict(census.EXPECTED_DIRECT_CLOSURE)
        deferred = {
            "enqueueWriters": 2,
            "scheduledReaders": 1,
            "fieldWriterReferences": 1,
            "fieldReaderReferences": 3,
            "refreshEntityStatusTargets": 1,
            "conditionUpdateTargets": 1,
        }
        self.assertEqual(
            census.validate_closure(
                counts, dict(census.EXPECTED_PENDING_FIELD), deferred, "GameAssembly.dll"
            ),
            [],
        )
        counts["storyMethods"] = 1
        failures = census.validate_closure(
            counts, dict(census.EXPECTED_PENDING_FIELD), deferred, "GameAssembly.dll"
        )
        self.assertEqual(failures[0]["gate"], "directClosure.storyMethods")
        self.assertEqual(failures[0]["expected"], 0)
        self.assertEqual(failures[0]["actual"], 1)

    def test_instance_field_register_is_derived_not_hardcoded(self):
        groups = [{
            "symbols": ["Beyond.Gameplay.System.BeforeTick"],
            "references": [
                {"instruction": "mov rax, [r14+0x58]"},
                {"instruction": "mov rcx, [r14+0x58]"},
                {"instruction": "mov rdx, [rsp+0x58]"},
            ],
        }]
        base, references = census.select_instance_field_references(
            groups, ".BeforeTick", "0x58"
        )
        self.assertEqual(base, "r14")
        self.assertEqual(len(references), 2)

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

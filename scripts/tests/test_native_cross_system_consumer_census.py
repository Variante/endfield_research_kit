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

    def test_broad_mission_runtime_shapes_are_classified_by_api(self):
        self.assertEqual(
            census.classify_mission_runtime_candidate(
                ["level_script", "mission_runtime"],
                [
                    "Beyond.Gameplay.CommonTrackingPointInfoBase..ctor",
                    "Beyond.Gameplay.Core.LevelScriptTaskTracking.get_scriptId",
                ],
            ),
            "levelscript_tracking_context_candidate",
        )
        self.assertEqual(
            census.classify_mission_runtime_candidate(
                ["level_script", "mission_runtime"],
                ["Beyond.Gameplay.Unknown.DoThing"],
            ),
            "unreviewed_mission_runtime_cross_system_shape",
        )

    def test_constructed_field_writes_derive_saved_register(self):
        instructions = [
            {"va": 0x1000, "text": "call 0x9000", "write": None},
            {"va": 0x1005, "text": "mov r14, rax", "write": {"register": "r14", "value": "rax"}},
            {"va": 0x1008, "text": "mov rcx, rax", "write": {"register": "rcx", "value": "rax"}},
            {"va": 0x100B, "text": "call 0xa000", "write": None},
            {"va": 0x1010, "text": "mov [r14+0x30], rcx", "write": None},
        ]
        flow = census.constructed_field_writes(
            instructions, 0xA000, {"missionId": "0x20", "sceneId": "0x30"}
        )
        self.assertEqual(flow["baseRegister"], "r14")
        self.assertEqual(flow["writes"]["missionId"], [])
        self.assertEqual(len(flow["writes"]["sceneId"]), 1)

    def test_broad_surface_validator_names_changed_gate(self):
        counts = dict(census.EXPECTED_MISSION_RUNTIME_SURFACE)
        self.assertEqual(census.validate_mission_runtime_surface(counts, "binary"), [])
        counts["crossFamilyMethodSignatures"] = 1
        failures = census.validate_mission_runtime_surface(counts, "binary")
        self.assertEqual(
            failures[0]["gate"],
            "missionRuntimeSurface.crossFamilyMethodSignatures",
        )

    def test_callable_type_recognition_is_semantic_and_value_agnostic(self):
        for type_name in (
            "System.Action",
            "System.Action`2<bool,Beyond.Gameplay.LevelScriptData>",
            "System.Func`2<Beyond.Gameplay.Entity,bool>",
            "Beyond.Gameplay.MissionAcceptMode+AcceptModeCallback",
            "Beyond.Gameplay.ExampleDelegate",
        ):
            with self.subTest(type_name=type_name):
                self.assertTrue(census.is_callable_type_name(type_name))
        self.assertFalse(census.is_callable_type_name("Beyond.Gameplay.MissionRuntimeAsset"))

    def test_callable_binding_requires_both_runtime_families(self):
        self.assertFalse(census.callable_binding_crosses_mission_levelscript({
            "callerFamilies": ["mission_runtime"],
            "targetFamilies": ["mission_runtime"],
        }))
        self.assertTrue(census.callable_binding_crosses_mission_levelscript({
            "callerFamilies": ["mission_runtime"],
            "targetFamilies": ["level_script"],
        }))

    def test_callable_surface_validator_reports_bounded_drift(self):
        counts = dict(census.EXPECTED_CALLABLE_CARRIER_SURFACE)
        self.assertEqual(census.validate_callable_carrier_surface(counts, "binary"), [])
        counts["directBindingCalls"] += 1
        failures = census.validate_callable_carrier_surface(counts, "binary")
        self.assertEqual(
            failures[0]["gate"], "managedCallableSurface.directBindingCalls"
        )
        self.assertEqual(failures[0]["expected"], 5)
        self.assertEqual(failures[0]["actual"], 6)

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

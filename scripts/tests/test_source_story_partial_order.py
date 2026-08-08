from __future__ import annotations

import unittest

from scripts.story_recovery.build_source_story_partial_order import (
    NATIVE_TYPED_CONTROL_ACTION_NAMES,
    _native_branch_kind,
    _native_serialized_branch_arm_projection,
    _serialized_native_control_arm_slots,
    _native_ordered_sequence_contexts,
)


class NativeOrderedSequenceContextTests(unittest.TestCase):
    def topology(self) -> dict:
        return {
            "actions": [{
                "localId": 10,
                "actionName": "Branch",
                "controlKind": "ordered_sequence",
                "controlRuntimeMappingId": "fixture-branch-runtime",
                "controlDetail": {
                    "branchSequenceActionLocalIds": [20, 30, 40],
                },
                "nextActionLocalId": 50,
            }],
        }

    def path(self, story: str, edge: str, entry: int) -> tuple:
        return (
            (1, "ActionHeader.nextId", "StartDialogAction", "ActionBase", "{}"),
            (10, "ActionBase.nextId", "Branch", "ActionBase", "{}"),
            (entry, edge, "PlayRadio", "ActionBase", "{}"),
        )

    def test_projects_serialized_arms_without_inventing_order(self) -> None:
        signature = ("map", "script", 1, "ScriptEvent_OnCustomEvent")
        contexts = _native_ordered_sequence_contexts(
            self.topology(),
            [
                (signature, "radio_a", self.path("radio_a", "Branch.sequence[1]", 30)),
            ],
        )

        self.assertEqual(len(contexts), 1)
        context = contexts[0]
        self.assertEqual(context["serializedArmCount"], 3)
        self.assertEqual(context["observedSequenceArmCount"], 1)
        self.assertEqual(context["storyBearingArmCount"], 1)
        self.assertEqual(context["storyOrderAdmission"], "not_admitted")
        self.assertEqual(context["arms"][0]["storyKeys"], [])
        self.assertEqual(context["arms"][1]["storyKeys"], ["radio_a"])
        self.assertEqual(context["arms"][2]["entryLocalId"], 40)

    def test_projects_multiple_arm_routes_as_context_only(self) -> None:
        signature = ("map", "script", 1, "ScriptEvent_OnCustomEvent")
        contexts = _native_ordered_sequence_contexts(
            self.topology(),
            [
                (signature, "radio_a", self.path("radio_a", "Branch.sequence[0]", 20)),
                (signature, "radio_b", self.path("radio_b", "Branch.sequence[2]", 40)),
            ],
        )

        self.assertEqual(contexts[0]["storyBearingArmCount"], 2)
        self.assertEqual(contexts[0]["storyOrderAdmission"], "not_admitted")
        self.assertIn(
            "multiple_story_bearing_arms",
            contexts[0]["admissionReason"],
        )

    def test_ignores_story_paths_without_a_serialized_branch(self) -> None:
        signature = ("map", "script", 1, "ScriptEvent_OnCustomEvent")
        path = (
            (1, "ActionHeader.nextId", "StartDialogAction", "ActionBase", "{}"),
            (20, "ActionBase.nextId", "PlayRadio", "ActionBase", "{}"),
        )
        self.assertEqual(
            _native_ordered_sequence_contexts(
                self.topology(),
                [(signature, "radio_a", path)],
            ),
            [],
        )


class NativeSerializedBranchProjectionTests(unittest.TestCase):
    def test_control_families_come_from_binary_mapping(self) -> None:
        self.assertIn("Branch", NATIVE_TYPED_CONTROL_ACTION_NAMES)
        self.assertIn("WhileAction", NATIVE_TYPED_CONTROL_ACTION_NAMES)
        self.assertIn(
            "WaitForSecondsInTriggerVolume",
            NATIVE_TYPED_CONTROL_ACTION_NAMES,
        )
        self.assertIn("SwitchIntLarger", NATIVE_TYPED_CONTROL_ACTION_NAMES)

    def test_integer_switch_variant_uses_shared_family_schema(self) -> None:
        self.assertEqual(
            _native_branch_kind("SwitchIntLarger.case[2]=9"),
            "switchIntLarger",
        )
        slots = _serialized_native_control_arm_slots({
            "actionName": "SwitchIntLarger",
            "controlDetail": {
                "switchIntLargerCaseValues": [0, 9],
                "switchIntLargerCaseActionLocalIds": [12, -1],
                "switchIntLargerDefaultActionLocalId": 30,
            },
        })
        self.assertEqual(
            [slot["edge"] for slot in slots],
            [
                "SwitchIntLarger.case[0]=0",
                "SwitchIntLarger.case[1]=9",
                "SwitchIntLarger.default",
            ],
        )
        self.assertEqual([slot["entryLocalId"] for slot in slots], [12, -1, 30])

    def test_loop_control_uses_family_schema_without_object_override(self) -> None:
        slots = _serialized_native_control_arm_slots({
            "actionName": "WhileAction",
            "controlDetail": {"whileDoActionLocalId": 42},
        })
        self.assertEqual(slots, [{
            "edge": "WhileAction.doAction",
            "entryLocalId": 42,
            "serializedField": "whileDoActionLocalId",
            "serializedFieldPresent": True,
        }])

    def test_wait_trigger_volume_uses_family_schema_without_object_override(self) -> None:
        slots = _serialized_native_control_arm_slots({
            "actionName": "WaitForSecondsInTriggerVolume",
            "controlDetail": {
                "waitSuccessActionLocalId": 11,
                "waitFailActionLocalId": 12,
            },
        })
        self.assertEqual(
            [slot["edge"] for slot in slots],
            [
                "WaitForSecondsInTriggerVolume.successAction",
                "WaitForSecondsInTriggerVolume.failAction",
            ],
        )
        self.assertEqual([slot["entryLocalId"] for slot in slots], [11, 12])

    def test_switch_cardinality_mismatch_is_visible_and_fail_closed(self) -> None:
        slots = _serialized_native_control_arm_slots({
            "actionName": "SwitchInt",
            "controlDetail": {
                "switchCaseValues": [1, 2],
                "switchCaseActionLocalIds": [30],
                "switchDefaultActionLocalId": 40,
            },
        })
        self.assertEqual(slots[0]["entryLocalId"], 30)
        self.assertFalse(slots[1]["serializedFieldPresent"])
        self.assertIsNone(slots[1]["entryLocalId"])

    def topology(self) -> dict:
        return {
            "actions": [
                {
                    "localId": 10,
                    "actionName": "Branch",
                    "controlRuntimeMappingId": "fixture-branch-runtime",
                    "controlDetail": {
                        "branchSequenceActionLocalIds": [20, 30],
                    },
                    "nextActionLocalId": 50,
                },
                {"localId": 20, "actionName": "PlayRadio", "nextActionLocalId": 21},
                {"localId": 21, "actionName": "Wait"},
                {"localId": 30, "actionName": "PlayRadio"},
                {"localId": 50, "actionName": "Finish"},
            ],
            "edges": [
                {"sourceKind": "action", "sourceLocalId": 10, "targetActionLocalId": 20, "relation": "Branch.sequence[0]"},
                {"sourceKind": "action", "sourceLocalId": 10, "targetActionLocalId": 30, "relation": "Branch.sequence[1]"},
                {"sourceKind": "action", "sourceLocalId": 10, "targetActionLocalId": 50, "relation": "ActionBase.nextId"},
                {"sourceKind": "action", "sourceLocalId": 20, "targetActionLocalId": 21, "relation": "ActionBase.nextId"},
            ],
        }

    def test_reaches_exact_playback_only_through_serialized_arm(self) -> None:
        projection = _native_serialized_branch_arm_projection(
            self.topology(),
            self.topology()["actions"][0],
            {21: {"radio_a"}},
        )
        self.assertEqual(projection["serializedArmCount"], 2)
        self.assertEqual(projection["playbackArmCount"], 1)
        self.assertEqual(projection["arms"][0]["playbackStoryKeys"], ["radio_a"])
        self.assertEqual(projection["arms"][1]["playbackStoryKeys"], [])
        self.assertEqual(projection["arms"][0]["targetStatus"], "exact_active_action")
        self.assertEqual(
            projection["arms"][0]["reachableActionNames"],
            ["PlayRadio", "Wait"],
        )
        self.assertEqual(projection["exit"]["entryLocalId"], 50)

    def test_multiple_playback_arms_remain_a_context_measure(self) -> None:
        projection = _native_serialized_branch_arm_projection(
            self.topology(),
            self.topology()["actions"][0],
            {20: {"radio_a"}, 30: {"radio_b"}},
        )
        self.assertEqual(projection["playbackArmCount"], 2)
        self.assertEqual(
            projection["playbackStoryKeys"],
            ["radio_a", "radio_b"],
        )
        self.assertEqual(
            projection["arms"][1]["reachableActionNames"],
            ["PlayRadio"],
        )

    def test_nested_typed_control_keeps_each_serialized_arm(self) -> None:
        topology = {
            "actions": [
                {
                    "localId": 10,
                    "actionName": "Branch",
                    "controlRuntimeMappingId": "fixture-branch-runtime",
                    "controlDetail": {
                        "branchSequenceActionLocalIds": [20],
                    },
                    "nextActionLocalId": 50,
                },
                {
                    "localId": 20,
                    "actionName": "IfElseAction",
                    "controlDetail": {
                        "trueActionLocalId": 30,
                        "falseActionLocalId": 40,
                    },
                },
                {"localId": 30, "actionName": "PlayRadio"},
                {"localId": 40, "actionName": "CallServer"},
                {"localId": 50, "actionName": "Finish"},
            ],
            "edges": [
                {"sourceKind": "action", "sourceLocalId": 10, "targetActionLocalId": 20, "relation": "Branch.sequence[0]"},
                {"sourceKind": "action", "sourceLocalId": 10, "targetActionLocalId": 50, "relation": "ActionBase.nextId"},
                {"sourceKind": "action", "sourceLocalId": 20, "targetActionLocalId": 30, "relation": "IfElseAction.trueAction"},
                {"sourceKind": "action", "sourceLocalId": 20, "targetActionLocalId": 40, "relation": "IfElseAction.falseAction"},
            ],
        }
        projection = _native_serialized_branch_arm_projection(
            topology,
            topology["actions"][0],
            {30: {"radio_nested"}},
            {20: {
                "status": "exact_unique_getter",
                "getterName": "IntCompare",
                "detail": {"comparerName": "Equal", "valueB": {"value": 1}},
            }},
        )
        nested = projection["arms"][0]["nestedControls"]
        self.assertEqual(len(nested), 1)
        self.assertEqual(projection["arms"][0]["reachableControlLocalIds"], [20])
        self.assertEqual(nested[0]["actionName"], "IfElseAction")
        self.assertEqual(nested[0]["predicate"]["getterName"], "IntCompare")
        self.assertEqual(nested[0]["arms"][0]["playbackStoryKeys"], ["radio_nested"])
        self.assertEqual(nested[0]["arms"][1]["reachableActionNames"], ["CallServer"])
        self.assertEqual(nested[0]["arms"][1]["reachableControlLocalIds"], [])
        self.assertEqual(nested[0]["playbackArmCount"], 1)
        self.assertEqual(nested[0]["branchingStatus"], "single_playback_arm")
        self.assertEqual(nested[0]["playbackPredicateStatus"], "exact_unique_getter")

    def test_nested_multi_playback_controls_remain_context_only(self) -> None:
        topology = {
            "actions": [
                {
                    "localId": 10,
                    "actionName": "Branch",
                    "controlDetail": {
                        "branchSequenceActionLocalIds": [20],
                    },
                },
                {
                    "localId": 20,
                    "actionName": "IfElseAction",
                    "controlDetail": {
                        "trueActionLocalId": 30,
                        "falseActionLocalId": 40,
                    },
                },
                {"localId": 30, "actionName": "PlayRadio"},
                {"localId": 40, "actionName": "PlayRadio"},
            ],
            "edges": [
                {"sourceKind": "action", "sourceLocalId": 10, "targetActionLocalId": 20, "relation": "Branch.sequence[0]"},
                {"sourceKind": "action", "sourceLocalId": 20, "targetActionLocalId": 30, "relation": "IfElseAction.trueAction"},
                {"sourceKind": "action", "sourceLocalId": 20, "targetActionLocalId": 40, "relation": "IfElseAction.falseAction"},
            ],
        }
        projection = _native_serialized_branch_arm_projection(
            topology,
            topology["actions"][0],
            {30: {"radio_true"}, 40: {"radio_false"}},
        )
        nested = projection["arms"][0]["nestedControls"][0]
        self.assertEqual(nested["playbackArmCount"], 2)
        self.assertEqual(nested["playbackStoryKeys"], ["radio_false", "radio_true"])
        self.assertEqual(nested["branchingStatus"], "multi_playback_arms")
        self.assertEqual(
            nested["playbackPredicateStatus"],
            "unresolved_playback_predicate",
        )

    def test_parallel_nested_playback_has_no_predicate_gap(self) -> None:
        topology = {
            "actions": [
                {
                    "localId": 10,
                    "actionName": "Branch",
                    "controlDetail": {"branchSequenceActionLocalIds": [20]},
                },
                {
                    "localId": 20,
                    "actionName": "Split",
                    "controlKind": "parallel_fanout",
                    "controlDetail": {"splitActionLocalIds": [30, 40]},
                },
                {"localId": 30, "actionName": "PlayRadio"},
                {"localId": 40, "actionName": "Wait"},
            ],
            "edges": [
                {"sourceKind": "action", "sourceLocalId": 10, "targetActionLocalId": 20, "relation": "Branch.sequence[0]"},
                {"sourceKind": "action", "sourceLocalId": 20, "targetActionLocalId": 30, "relation": "Split.actions[0]"},
                {"sourceKind": "action", "sourceLocalId": 20, "targetActionLocalId": 40, "relation": "Split.actions[1]"},
            ],
        }
        projection = _native_serialized_branch_arm_projection(
            topology,
            topology["actions"][0],
            {30: {"radio_parallel"}},
        )
        nested = projection["arms"][0]["nestedControls"][0]
        self.assertEqual(nested["branchingStatus"], "single_playback_arm")
        self.assertEqual(nested["playbackPredicateStatus"], "not_applicable")


if __name__ == "__main__":
    unittest.main()

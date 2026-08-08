from __future__ import annotations

import unittest

from scripts.story_recovery.build_source_story_partial_order import (
    _native_serialized_branch_arm_projection,
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


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from scripts.story_recovery.build_source_story_partial_order import (
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


if __name__ == "__main__":
    unittest.main()

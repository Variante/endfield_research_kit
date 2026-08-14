from __future__ import annotations

import unittest

from scripts.story_builder.dialog_tree_connection_projection import (
    dialog_tree_narrative_connection,
    dialog_tree_story_playback_connection,
)


class DialogTreeConnectionProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.kinds = {"dlg_child": "dlg", "black_child": "black"}
        self.owners = {"dlg_child": "mission_a", "black_child": "mission_b"}

    def test_story_playback_projects_carriers_and_direct_quest_scope(self) -> None:
        occurrences = [
            {
                "carrierKind": "trunk",
                "trunkId": "dlg_child_001",
                "sourceFile": "tree.json",
                "sourcePathId": "nodes/1",
            },
            {
                "carrierKind": "dialog",
                "dialogId": "dlg_child_002",
                "sourceFile": "tree.json",
                "sourcePathId": "nodes/2",
            },
        ]
        connection = dialog_tree_story_playback_connection(
            "dlg_child",
            "dlg_parent",
            occurrences,
            scope={
                "scopeKind": "quest",
                "questEvidence": "direct",
                "questRows": [{"relation": "mission_accept_dialog"}],
                "candidateQuestIds": ["quest_1"],
            },
            parent_scope_key="misc_dlg_parent",
            story_kind_by_key=self.kinds,
            story_owner_by_key=self.owners,
        )

        self.assertEqual(connection["confidence"], "native_exact_parent_quest")
        self.assertEqual(connection["carrierKinds"], ["dialog", "trunk"])
        self.assertEqual(connection["parentStoryOutKey"], "misc_dlg_parent")
        self.assertEqual(connection["candidateQuestIds"], ["quest_1"])
        self.assertEqual(len(connection["nativeConsumers"]), 9)

    def test_story_playback_preserves_cross_story_quest_state_context(self) -> None:
        carrier_context = {
            "questStateBranchContexts": [
                {
                    "conditions": [
                        {
                            "conditionPath": "conditions/0",
                            "questId": "quest_1",
                            "comparer": "Equal",
                            "targetQuestState": "Finished",
                        }
                    ]
                }
            ]
        }
        connection = dialog_tree_story_playback_connection(
            "dlg_child",
            "dlg_parent",
            [{"carrierKind": "dialog", "dialogId": "dlg_child_001"}],
            scope={"carrierQuestStateContext": carrier_context},
            parent_scope_key="dlg_parent",
            story_kind_by_key=self.kinds,
            story_owner_by_key=self.owners,
        )

        self.assertTrue(connection["dependencyOnly"])
        self.assertEqual(
            connection["missionStateGatePredicates"],
            ["conditions/0._questId=quest_1; _comparer=Equal; _targetQuestState=Finished"],
        )

    def test_narrative_connection_projects_left_subtitle(self) -> None:
        occurrences = [
            {
                "actionKind": "left_subtitle",
                "textId": "subtitle_1",
                "textField": "text1",
                "actionType": "DialogLeftSubtitleActionData",
                "actionPath": "nodes/1/actions/0",
                "sourceFile": "tree.json",
                "sourcePathId": "1",
            }
        ]
        connection = dialog_tree_narrative_connection(
            "black_child",
            "dlg_parent",
            occurrences,
            confidence="native_exact_parent_quest",
            quest_trigger_status="exact_unique_parent_quest",
            evidence_tier="native_direct",
            story_kind_by_key=self.kinds,
            story_owner_by_key=self.owners,
        )

        self.assertEqual(connection["relation"], "dialog_tree_left_subtitle_action")
        self.assertEqual(connection["textFields"], ["text1"])
        self.assertIs(connection["dialogTreeLeftSubtitleActions"], occurrences)

    def test_narrative_connection_classifies_exact_embedded_placement(self) -> None:
        occurrences = [
            {
                "actionKind": "narrative_mask",
                "dialogKey": "dlg_parent",
                "dialogTreeConnectionPlacementStatus": (
                    "exact_unique_adjacent_parent_trunks"
                ),
                "embeddedAfterLineIds": ["dlg_parent_001"],
                "embeddedBeforeLineIds": ["dlg_parent_002"],
            }
        ]
        connection = dialog_tree_narrative_connection(
            "black_child",
            "dlg_parent",
            occurrences,
            confidence="native_derived_exact_parent_quest",
            quest_trigger_status="exact_parent_quest_context_not_playback",
            evidence_tier="derived_exact_quest",
            story_kind_by_key=self.kinds,
            story_owner_by_key=self.owners,
        )

        self.assertEqual(connection["relation"], "dialog_tree_narrative_action")
        self.assertEqual(
            connection["embeddedLinePlacementStatus"],
            "exact_complete_connection_neighbors",
        )
        self.assertEqual(connection["embeddedAfterLineIds"], ["dlg_parent_001"])


if __name__ == "__main__":
    unittest.main()

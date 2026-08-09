from __future__ import annotations

import unittest

from scripts.story_builder.mission_recovery import attach_timeline_evidence


class MissionRecoveryDialogDefinitionTests(unittest.TestCase):
    def test_exact_dialog_tree_closes_missing_timeline_gap(self) -> None:
        refs = [{
            "sceneKey": "dlg_fixture_1",
            "kind": "dlg",
            "source": {"file": "fixture.json", "field": "condition._dialogId"},
        }]
        definition = {
            "sceneKey": "dlg_fixture_1",
            "assetType": "Beyond.Gameplay.DialogTree",
            "evidenceKind": "exact_dialog_tree_definition",
        }

        timeline, dialog_trees, unresolved = attach_timeline_evidence(
            refs,
            {},
            dialog_tree_loader=lambda key: definition if key == "dlg_fixture_1" else None,
        )

        self.assertEqual({}, timeline)
        self.assertEqual(definition, dialog_trees["dlg_fixture_1"])
        self.assertEqual([], unresolved)

    def test_timeline_and_dialog_tree_are_retained_independently(self) -> None:
        refs = [{"sceneKey": "dlg_fixture_1", "kind": "dlg"}]
        timeline_entry = {"timeline": "dlgtl_fixture_1"}
        loader_calls: list[str] = []
        definition = {
            "sceneKey": "dlg_fixture_1",
            "assetType": "Beyond.Gameplay.DialogTree",
            "evidenceKind": "exact_dialog_tree_definition",
        }

        timeline, dialog_trees, unresolved = attach_timeline_evidence(
            refs,
            {"dlg_fixture_1": [timeline_entry]},
            dialog_tree_loader=lambda key: loader_calls.append(key) or definition,
        )

        self.assertEqual([timeline_entry], timeline["dlg_fixture_1"])
        self.assertEqual(definition, dialog_trees["dlg_fixture_1"])
        self.assertEqual([], unresolved)
        self.assertEqual(["dlg_fixture_1"], loader_calls)

    def test_timeline_without_dialog_tree_is_not_reported_as_missing_both(self) -> None:
        refs = [{"sceneKey": "dlg_fixture_1", "kind": "dlg"}]
        timeline_entry = {"timeline": "dlgtl_fixture_1"}

        timeline, dialog_trees, unresolved = attach_timeline_evidence(
            refs,
            {"dlg_fixture_1": [timeline_entry]},
            dialog_tree_loader=lambda _key: None,
        )

        self.assertEqual([timeline_entry], timeline["dlg_fixture_1"])
        self.assertEqual({}, dialog_trees)
        self.assertEqual([], unresolved)

    def test_missing_both_sources_reports_actionable_diagnostic(self) -> None:
        source = {"file": "fixture.json", "field": "condition._dialogId"}
        refs = [{
            "sceneKey": "dlg_fixture_1",
            "kind": "dlg",
            "source": source,
        }]

        timeline, dialog_trees, unresolved = attach_timeline_evidence(
            refs,
            {},
            dialog_tree_loader=lambda _key: None,
        )

        self.assertEqual({}, timeline)
        self.assertEqual({}, dialog_trees)
        self.assertEqual(1, len(unresolved))
        self.assertEqual(
            "missingDialogTimelineAndDialogTreeEvidence",
            unresolved[0]["kind"],
        )
        self.assertEqual("dlg_fixture_1", unresolved[0]["sceneKey"])
        self.assertEqual(source, unresolved[0]["source"])
        self.assertEqual(2, len(unresolved[0]["checkedSources"]))


if __name__ == "__main__":
    unittest.main()

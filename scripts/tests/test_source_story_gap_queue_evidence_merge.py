from __future__ import annotations

import unittest
from pathlib import Path
import tempfile
import hashlib
from unittest.mock import patch

from scripts.tests.story_gap._support import gap_queue


_merge_exact_interaction_trigger_with_native_playback = (
    gap_queue._merge_exact_interaction_trigger_with_native_playback
)


class SourceStoryGapQueueEvidenceMergeTests(unittest.TestCase):
    def test_final_native_closure_applies_interaction_merge(self) -> None:
        source = Path(
            "scripts/story_builder/source_gap/model.py"
        ).read_text(encoding="utf-8")
        closure_start = source.index(
            "for scene_key, row in list(closed_exact_native_isolated_by_key.items())"
        )
        closure_end = source.index(
            "closed_exact_native_isolated = sorted(",
            closure_start,
        )
        block = source[closure_start:closure_end]
        self.assertIn(
            "_merge_exact_interaction_trigger_with_native_playback(",
            block,
        )
        self.assertIn(
            "closed_exact_native_isolated_by_key[scene_key] = merged",
            block,
        )

    def test_exact_interaction_trigger_survives_native_playback_merge(self) -> None:
        prior = {
            "levelId": "indie_dg002",
            "recoveryStatus":
                "exact_current_build_interaction_trigger_recovered",
            "evidenceKind":
                "reading_popup_world_entity_interaction_trigger",
            "worldEntityInteractionTriggers": [{
                "levelId": "indie_dg002",
                "scriptIdGlobal": "8700020018",
                "entitySlotId": 40001,
                "eventName": "readepitaph",
            }],
            "unhostedReadingPopupReceivers": [{
                "readingPopupId": "text_e0m0_1",
            }],
            "consumerBoundary": "exact interaction to popup",
            "graphEffect": "none",
        }
        native = {
            "sceneKey": "text_e0m0_1",
            "missionId": "e0m0",
            "recoveryStatus":
                "deferred_exact_native_playback_without_mission_bridge",
            "evidenceKind":
                "exact_missionless_native_event_playback_path",
            "nativeEventPaths": [{"eventSummary": "custom event readepitaph"}],
            "graphEffect": "none",
        }

        merged, did_merge = (
            _merge_exact_interaction_trigger_with_native_playback(
                prior,
                native,
            )
        )

        self.assertTrue(did_merge)
        self.assertEqual(
            merged["recoveryStatus"],
            "exact_current_build_interaction_trigger_recovered",
        )
        self.assertEqual(
            merged["evidenceKind"],
            "reading_popup_world_entity_interaction_trigger",
        )
        self.assertEqual(merged["levelId"], "indie_dg002")
        self.assertEqual(
            merged["worldEntityInteractionTriggers"][0]["entitySlotId"],
            40001,
        )
        self.assertEqual(
            merged["nativeEventPaths"][0]["eventSummary"],
            "custom event readepitaph",
        )
        self.assertEqual(merged["missionBridgeStatus"], "unresolved")
        self.assertEqual(merged["graphEffect"], "none")


class TrackedProxyFlowValidatorTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[dict, dict]:
        paths = {
            name: root / name
            for name in (
                "MissionRuntimeAsset/e10m3d5.json",
                "GameplayConfig/NpcProxyTable.json",
                "GameplayConfig/NpcProxyExDataTable.json",
                "recovered/dialog_id_table_index.json",
            )
        }
        for path in paths.values():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture", encoding="utf-8")
        proxy_id = "proxy_teacher"
        story_key = "dlg_e10m3_3"
        ex_rows = [{"dialogId": story_key}]
        source_files = sorted(
            path.relative_to(root).as_posix() for path in paths.values()
        )
        sources = {
            "trackingCorpus": {
                "status": "active",
                "rowsByProxy": {
                    proxy_id: [{
                        "qualified": True,
                        "missionId": "e10m3d5",
                        "questId": "e10m3d5_q#2",
                        "objectiveIndex": 0,
                        "trackingIndex": 0,
                        "npcProxyId": proxy_id,
                        "sceneId": "map02_lv002",
                        "tracking": {"useFilterCondition": False},
                        "sourceFile": source_files[2],
                        "sourceSha256": "fixture-runtime-sha",
                    }],
                },
            },
            "npcProxyTablePath": paths["GameplayConfig/NpcProxyTable.json"],
            "npcProxyTable": {
                "dataTable": {
                    proxy_id: {
                        "proxyId": proxy_id,
                        "levelId": "map02_lv002",
                        "subDataParentId": 1,
                    },
                },
            },
            "npcProxyExPath": paths[
                "GameplayConfig/NpcProxyExDataTable.json"
            ],
            "npcProxyEx": {"data": {proxy_id: ex_rows}},
            "dialogIdIndexPath": paths[
                "recovered/dialog_id_table_index.json"
            ],
            "dialogIdIndex": {
                story_key: {
                    "registered": True,
                    "memoryPackRecordKey": True,
                },
            },
        }
        row = {
            "key": story_key,
            "npcProxyId": proxy_id,
            "levelIds": ["map02_lv002"],
            "relation": "unique_mission_tracked_npc_proxy_dialog_context",
            "direction": "context",
            "phase": "server_selected_proxy_state",
            "confidence": "native_exact_mission_context",
            "evidenceTier": "derived_exact_mission",
            "storyOwnerMission": "e10m3",
            "candidateQuestIds": ["e10m3d5_q#2"],
            "configuredDialogIds": [story_key],
            "activeRowIndex": 1,
            "npcProxyTableRow": {
                "proxyId": proxy_id,
                "levelId": "map02_lv002",
                "subDataParentId": 1,
            },
            "npcProxyExRows": ex_rows,
            "sourceFiles": source_files,
            "storyBinding": True,
            "ownership": False,
            "questActivation": False,
            "questPlayback": False,
            "questCompletion": False,
            "nativeMappingId":
                gap_queue.NPC_PROXY_DIALOG_SELECTION_MAPPING_ID,
            "gameAssemblySha256":
                gap_queue.NPC_PROXY_DIALOG_SELECTION_GAMEASSEMBLY_SHA256,
        }
        return sources, row

    def test_accepts_exact_cross_mission_tracking_context(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources, row = self.fixture(root)
            with (
                patch.object(gap_queue, "ROOT", root),
                patch.object(
                    gap_queue,
                    "_current_tracked_proxy_dialog_sources",
                    return_value=sources,
                ),
            ):
                context, failure = (
                    gap_queue._validate_general_tracked_proxy_flow_context(
                        row,
                        "e10m3",
                    )
                )

        self.assertIsNone(failure)
        self.assertEqual(context["missionId"], "e10m3d5")
        self.assertEqual(context["nominalMissionId"], "e10m3")
        self.assertIs(context["crossMission"], True)

    def test_failure_reports_current_context_and_bounded_actuals(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources, row = self.fixture(root)
            row["sourceFiles"] = row["sourceFiles"][:-1]
            with (
                patch.object(gap_queue, "ROOT", root),
                patch.object(
                    gap_queue,
                    "_current_tracked_proxy_dialog_sources",
                    return_value=sources,
                ),
            ):
                context, failure = (
                    gap_queue._validate_general_tracked_proxy_flow_context(
                        row,
                        "e10m3",
                    )
                )

        self.assertIsNone(context)
        self.assertEqual(failure["gate"], "exactCurrentSourceComposition")
        self.assertEqual(
            failure["actual"]["trackingContext"]["missionId"],
            "e10m3d5",
        )
        self.assertIs(failure["actual"]["registeredDialogRoots"], True)
        self.assertNotEqual(
            failure["actual"]["sourceFiles"],
            failure["expected"]["sourceFiles"],
        )


class RegisteredDialogDefinitionValidatorTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[dict, dict]:
        story_key = "dlg_test_1"
        source = root / "recovered" / "TextAsset" / f"{story_key}_p123.json"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("fixture dialog tree", encoding="utf-8")
        definition = {
            "sceneKey": story_key,
            "assetName": story_key,
            "assetType": "Beyond.Gameplay.DialogTree",
            "evidenceKind": "exact_dialog_tree_definition",
            "sourceType": "AnimeStudio TextAsset/DialogTree",
            "lineIds": [],
            "lineConnections": [],
            "entryLineIds": [],
            "terminalLineIds": [],
            "nonLineConnectionCount": 0,
            "optionIds": [],
            "nodeCount": 1,
            "nodeTypeCounts": {"DialogTreeFinishNode": 1},
            "connectionCount": 0,
            "optionGroupCount": 0,
            "branchingOptionGroupCount": 0,
            "sourceFile": source.relative_to(root).as_posix(),
            "sourcePathId": "123",
            "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "optionRouteRecovery": {
                "schemaVersion": "dialogTreeNormalOptionRoutes.v1",
                "counts": {"validatedNormalOptionRoutes": 0},
                "nodes": [{
                    "normalOptionCount": 0,
                    "routes": [],
                    "issues": [{"gate": "nodeIdentity"}],
                }],
                "issues": [{"gate": "nodeIdentity"}],
            },
            "finishEndpointRecovery": {
                "schemaVersion": "dialogTreeFinishEndpoints.v1",
                "counts": {"validatedFinishEndpoints": 0},
                "endpoints": [{
                    "status": "rejected",
                    "nodeOrdinal": 0,
                }],
                "issues": [{"gate": "finishNodeIdentity"}],
            },
        }
        registration = {
            "registered": True,
            "memoryPackRecordKey": True,
            "hasRootKey": True,
        }
        return registration, definition

    def test_non_owning_context_accepts_hash_valid_partial_control_flow(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registration, definition = self.fixture(root)
            with patch.object(gap_queue, "ROOT", root):
                facts, failure = (
                    gap_queue._generic_registered_dialog_tree_definition_facts(
                        "dlg_test_1",
                        registration,
                        definition,
                        require_control_flow=False,
                    )
                )

        self.assertIsNone(failure)
        self.assertEqual(
            facts["controlFlowValidationStatus"],
            "partial_not_required_for_non_owning_context",
        )
        self.assertIs(facts["controlFlowValidationRequired"], False)

    def test_exact_control_flow_gate_rejects_same_partial_definition(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registration, definition = self.fixture(root)
            with patch.object(gap_queue, "ROOT", root):
                facts, failure = (
                    gap_queue._generic_registered_dialog_tree_definition_facts(
                        "dlg_test_1",
                        registration,
                        definition,
                    )
                )

        self.assertIsNone(facts)
        self.assertEqual(failure["gate"], "exactCurrentDialogTreeDefinition")
        self.assertIs(
            failure["expected"]["validatedOptionRouteRecovery"],
            True,
        )
        self.assertEqual(
            failure["actual"]["finishEndpointRecovery"]["issues"][0][
                "gate"
            ],
            "finishNodeIdentity",
        )


if __name__ == "__main__":
    unittest.main()

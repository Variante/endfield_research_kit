from __future__ import annotations

import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts.story_builder import anime_assets, language_bundle


CONNECTION_TYPE = "Beyond.Gameplay.DialogTreeConnection"
TRUNK_TYPE = "Beyond.Gameplay.DialogTreeTrunkNode"


def node(node_id: str, *, node_type: str = "Beyond.Gameplay.DialogTreeStartNode", trunk_id: str = "") -> dict:
    row = {"$id": node_id, "$type": node_type}
    if trunk_id:
        row["_actorNodeData"] = {
            "mfTrunkActionData": {"_trunkId": trunk_id},
        }
    return row


def connection(source: str, target: str, *, type_name: str = CONNECTION_TYPE) -> dict:
    return {
        "$type": type_name,
        "_sourceNode": {"$ref": source},
        "_targetNode": {"$ref": target},
    }


def quest_condition(quest_id: str, state: int = 3) -> dict:
    return {
        "$type": "Beyond.Gameplay.CheckQuestState",
        "_questId": {"constValue": quest_id},
        "_comparer": {},
        "_targetQuestState": {"constValue": state},
    }


def combine_condition(*conditions: dict, expression: str = "{0} and {1}") -> dict:
    return {
        "$type": "Beyond.Gameplay.CombineCondition",
        "subConditions": list(conditions),
        "conditionEvalString": expression,
    }


def payload(*, child_type: str = TRUNK_TYPE, trunk_id: str = "dlg_child_2_001") -> dict:
    return {
        "type": "Beyond.Gameplay.DialogTree",
        "nodes": [
            node("0", node_type=TRUNK_TYPE, trunk_id="dlg_parent_1_001"),
            node("1", node_type=child_type, trunk_id=trunk_id),
        ],
        "connections": [connection("0", "1")],
    }


def prime_sibling_payload(*, prime_id: str = "17", dialog_carrier: bool = False) -> dict:
    child = node("2", node_type=TRUNK_TYPE, trunk_id="dlg_child_2_001")
    if dialog_carrier:
        child = node("2", node_type="Beyond.Gameplay.DialogTreeDialogNode")
        child["_dialogId"] = "dlg_child_2"
    return {
        "type": "Beyond.Gameplay.DialogTree",
        "nodes": [
            node(prime_id),
            node("1", node_type=TRUNK_TYPE, trunk_id="dlg_parent_1_001"),
            child,
        ],
        "connections": [
            connection(prime_id, "1"),
            connection(prime_id, "2"),
        ],
    }


def completion_connection(
    parent_key: str = "dlg_parent_1",
    *,
    relation: str = "objective_condition",
    condition_type: str = "CheckTalkOptionFinish",
    confidence: str = "direct",
    source: str = "MissionRuntimeAsset.questDic[*].objectiveList[0].condition._dialogId",
) -> dict:
    return {
        "key": parent_key,
        "kind": "dialog",
        "relation": relation,
        "direction": "story_to_quest",
        "phase": "progress",
        "confidence": confidence,
        "source": source,
        "objectiveIndex": 1,
        "conditionType": condition_type,
        "finishId": -1,
    }


class DialogTreeStoryTrunkCarrierTests(unittest.TestCase):
    def test_reachable_exact_trunk_is_accepted_with_authored_path(self) -> None:
        rows = anime_assets._extract_dialog_tree_story_trunk_carriers(
            payload(),
            "dlg_parent_1",
            {"dlg_parent_1", "dlg_child_2"},
        )

        self.assertEqual(1, len(rows))
        self.assertEqual("dlg_child_2", rows[0]["storyKey"])
        self.assertEqual("dlg_child_2_001", rows[0]["trunkId"])
        self.assertEqual(["0", "1"], rows[0]["nodePath"])
        self.assertEqual(CONNECTION_TYPE, rows[0]["connectionPath"][0]["type"])

    def test_trunk_view_accepts_only_exact_trunk_field_and_numeric_line_suffix(self) -> None:
        dialog_node = payload(
            child_type="Beyond.Gameplay.DialogTreeDialogNode",
        )
        dialog_node["nodes"][1].pop("_actorNodeData")
        dialog_node["nodes"][1]["_dialogId"] = "dlg_child_2"
        subtitle_node = payload(
            child_type="Beyond.Gameplay.DialogLeftSubtitleActionData",
        )
        subtitle_node["nodes"][1].pop("_actorNodeData")
        subtitle_node["nodes"][1]["text1"] = {"key": "dlg_child_2_001"}

        self.assertEqual([], anime_assets._extract_dialog_tree_story_trunk_carriers(
            dialog_node, "dlg_parent_1", {"dlg_child_2"}
        ))
        self.assertEqual([], anime_assets._extract_dialog_tree_story_trunk_carriers(
            subtitle_node, "dlg_parent_1", {"dlg_child_2"}
        ))
        self.assertEqual([], anime_assets._extract_dialog_tree_story_trunk_carriers(
            payload(trunk_id="dlg_child_2_01x"),
            "dlg_parent_1",
            {"dlg_child_2"},
        ))

    def test_exact_dialog_node_is_a_separate_native_playback_carrier(self) -> None:
        candidate = payload(child_type="Beyond.Gameplay.DialogTreeDialogNode")
        candidate["nodes"][1].pop("_actorNodeData")
        candidate["nodes"][1]["_dialogId"] = "dlg_child_2"

        rows = anime_assets._extract_dialog_tree_story_playback_carriers(
            candidate,
            "dlg_parent_1",
            {"dlg_child_2"},
        )

        self.assertEqual(1, len(rows))
        self.assertEqual("dialog", rows[0]["carrierKind"])
        self.assertEqual("_dialogId", rows[0]["carrierField"])
        self.assertEqual("dlg_child_2", rows[0]["dialogId"])
        self.assertIsNone(rows[0]["lineIndex"])

    def test_parent_and_unknown_story_keys_are_not_emitted(self) -> None:
        self.assertEqual([], anime_assets._extract_dialog_tree_story_trunk_carriers(
            payload(trunk_id="dlg_parent_1_001"),
            "dlg_parent_1",
            {"dlg_parent_1"},
        ))
        self.assertEqual([], anime_assets._extract_dialog_tree_story_trunk_carriers(
            payload(),
            "dlg_parent_1",
            {"dlg_parent_1"},
        ))

    def test_missing_or_duplicate_node_ids_fail_closed(self) -> None:
        missing = payload()
        missing["nodes"][1].pop("$id")
        duplicate = payload()
        duplicate["nodes"][1]["$id"] = "0"

        for candidate in (missing, duplicate):
            self.assertEqual([], anime_assets._extract_dialog_tree_story_trunk_carriers(
                candidate,
                "dlg_parent_1",
                {"dlg_child_2"},
            ))

    def test_malformed_and_dangling_graphs_fail_closed(self) -> None:
        malformed = payload()
        malformed["connections"][0]["$type"] = "WrongConnection"
        dangling = payload()
        dangling["connections"][0]["_targetNode"]["$ref"] = "missing"
        for candidate in (malformed, dangling):
            self.assertEqual([], anime_assets._extract_dialog_tree_story_trunk_carriers(
                candidate,
                "dlg_parent_1",
                {"dlg_child_2"},
            ))

    def test_isolated_missing_id_authoring_node_is_ignored(self) -> None:
        candidate = payload()
        candidate["nodes"].append({
            "$type": "Beyond.Gameplay.DialogTreeFinishNode",
            "_position": {"x": 10.0, "y": 20.0},
        })

        rows = anime_assets._extract_dialog_tree_story_trunk_carriers(
            candidate,
            "dlg_parent_1",
            {"dlg_child_2"},
        )

        self.assertEqual(1, len(rows))

    def test_sibling_branch_is_not_reachable_from_current_parent_anchor(self) -> None:
        candidate = {
            "type": "Beyond.Gameplay.DialogTree",
            "nodes": [
                node("0"),
                node("1", node_type=TRUNK_TYPE, trunk_id="dlg_parent_1_001"),
                node("2", node_type=TRUNK_TYPE, trunk_id="dlg_child_2_001"),
            ],
            "connections": [connection("0", "1"), connection("0", "2")],
        }

        rows = anime_assets._extract_dialog_tree_story_trunk_carriers(
            candidate,
            "dlg_parent_1",
            {"dlg_child_2"},
        )

        self.assertEqual([], rows)

    def test_directed_ancestor_of_current_parent_anchor_is_accepted(self) -> None:
        candidate = {
            "type": "Beyond.Gameplay.DialogTree",
            "nodes": [
                node("0", node_type=TRUNK_TYPE, trunk_id="dlg_child_2_01"),
                node("1", node_type=TRUNK_TYPE, trunk_id="dlg_parent_1_001"),
                node("2"),
            ],
            "connections": [connection("0", "2"), connection("2", "1")],
        }

        rows = anime_assets._extract_dialog_tree_story_trunk_carriers(
            candidate,
            "dlg_parent_1",
            {"dlg_child_2"},
        )

        self.assertEqual(1, len(rows))
        self.assertEqual("child_to_parent", rows[0]["reachDirection"])
        self.assertEqual(["0", "2", "1"], rows[0]["nodePath"])
        self.assertEqual(
            "exact_registered_dialog_tree_current_parent_anchor",
            rows[0]["entryProof"],
        )

    def test_cycle_disconnected_from_unique_authored_root_is_rejected(self) -> None:
        candidate = {
            "type": "Beyond.Gameplay.DialogTree",
            "nodes": [
                node("0", node_type=TRUNK_TYPE, trunk_id="dlg_parent_1_001"),
                node("1", node_type=TRUNK_TYPE, trunk_id="dlg_child_2_001"),
                node("2"),
            ],
            "connections": [connection("1", "2"), connection("2", "1")],
        }

        self.assertEqual([], anime_assets._extract_dialog_tree_story_trunk_carriers(
            candidate,
            "dlg_parent_1",
            {"dlg_child_2"},
        ))

    def test_recovery_requires_exact_memorypack_registration_and_asset_name(self) -> None:
        registry = {
            "dlg_parent_1": {
                "registered": True,
                "memoryPackRecordKey": True,
                "registrationEvidence": ["memorypack_record_key"],
            },
        }
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "dlg_parent_1_p0000000000000001.json"
            path.write_text("{}", encoding="utf-8")
            decoded = {**payload(), "_assetName": "dlg_parent_1"}
            with (
                patch.object(anime_assets, "_iter_anime_tree_files", return_value=[path]),
                patch.object(anime_assets, "_load_anime_resource_payload", return_value=decoded),
            ):
                rows = anime_assets.recover_dialog_tree_story_trunk_carriers(
                    registry,
                    {"dlg_child_2"},
                )
            self.assertEqual(1, len(rows))
            self.assertEqual("0000000000000001", rows[0]["sourcePathId"])

            for bad_registry in (
                {},
                {"dlg_parent_1": {"registered": True}},
            ):
                with (
                    patch.object(anime_assets, "_iter_anime_tree_files", return_value=[path]),
                    patch.object(anime_assets, "_load_anime_resource_payload", return_value=decoded),
                ):
                    self.assertEqual([], anime_assets.recover_dialog_tree_story_trunk_carriers(
                        bad_registry,
                        {"dlg_child_2"},
                    ))

            wrong_name = {**decoded, "_assetName": "dlg_other_1"}
            with (
                patch.object(anime_assets, "_iter_anime_tree_files", return_value=[path]),
                patch.object(anime_assets, "_load_anime_resource_payload", return_value=wrong_name),
            ):
                self.assertEqual([], anime_assets.recover_dialog_tree_story_trunk_carriers(
                    registry,
                    {"dlg_child_2"},
                ))


class DialogTreePrimeReachableCarrierTests(unittest.TestCase):
    def test_sibling_is_prime_reachable_but_not_parent_anchor_reachable(self) -> None:
        candidate = prime_sibling_payload()

        self.assertEqual([], anime_assets._extract_dialog_tree_story_playback_carriers(
            candidate,
            "dlg_parent_1",
            {"dlg_child_2"},
        ))
        rows = anime_assets._extract_dialog_tree_prime_reachable_story_playback_carriers(
            candidate,
            "dlg_parent_1",
            {"dlg_child_2"},
            {"dlg_child_2_001"},
            {"dlg_child_2"},
        )

        self.assertEqual(1, len(rows))
        row = rows[0]
        self.assertEqual("dlg_child_2", row["storyKey"])
        self.assertEqual("trunk", row["carrierKind"])
        self.assertEqual("17", row["primeNodeId"])
        self.assertEqual(0, row["primeNodeIndex"])
        self.assertEqual(["17", "2"], row["nodePath"])
        self.assertEqual("prime_to_carrier", row["reachDirection"])
        self.assertIs(row["reachableFromPrimeNode"], True)
        self.assertEqual(
            "exact_registered_dialog_tree_prime_node_reachability",
            row["entryProof"],
        )
        self.assertEqual(CONNECTION_TYPE, row["connectionPath"][0]["type"])

    def test_prime_is_serialized_first_node_not_numeric_or_structural_root(self) -> None:
        candidate = prime_sibling_payload(prime_id="23")
        candidate["nodes"].append(node("0"))
        candidate["connections"].append(connection("0", "2"))

        rows = anime_assets._extract_dialog_tree_prime_reachable_story_playback_carriers(
            candidate,
            "dlg_parent_1",
            {"dlg_child_2"},
            {"dlg_child_2_001"},
            {"dlg_child_2"},
        )

        self.assertEqual(1, len(rows))
        self.assertEqual("23", rows[0]["primeNodeId"])
        self.assertEqual(["23", "2"], rows[0]["nodePath"])

    def test_only_forward_prime_reachability_is_accepted(self) -> None:
        disconnected = prime_sibling_payload()
        disconnected["connections"] = [
            connection("17", "1"),
            connection("2", "17"),
        ]

        self.assertEqual(
            [],
            anime_assets._extract_dialog_tree_prime_reachable_story_playback_carriers(
                disconnected,
                "dlg_parent_1",
                {"dlg_child_2"},
                {"dlg_child_2_001"},
                {"dlg_child_2"},
            ),
        )

    def test_typed_dialog_carrier_is_accepted_but_generic_text_is_not(self) -> None:
        dialog_candidate = prime_sibling_payload(dialog_carrier=True)
        rows = anime_assets._extract_dialog_tree_prime_reachable_story_playback_carriers(
            dialog_candidate,
            "dlg_parent_1",
            {"dlg_child_2"},
            {"dlg_child_2_001"},
            {"dlg_child_2"},
        )

        self.assertEqual(1, len(rows))
        self.assertEqual("dialog", rows[0]["carrierKind"])
        self.assertEqual("_dialogId", rows[0]["carrierField"])
        self.assertEqual("dlg_child_2", rows[0]["dialogId"])

        generic = prime_sibling_payload()
        generic["nodes"][2] = node(
            "2",
            node_type="Beyond.Gameplay.DialogLeftSubtitleActionData",
        )
        generic["nodes"][2]["text1"] = {"key": "dlg_child_2_001"}
        self.assertEqual(
            [],
            anime_assets._extract_dialog_tree_prime_reachable_story_playback_carriers(
                generic,
                "dlg_parent_1",
                {"dlg_child_2"},
                {"dlg_child_2_001"},
                {"dlg_child_2"},
            ),
        )

    def test_prime_carriers_require_exact_line_or_registered_dialog_identity(self) -> None:
        trunk = prime_sibling_payload()
        self.assertEqual(
            [],
            anime_assets._extract_dialog_tree_prime_reachable_story_playback_carriers(
                trunk,
                "dlg_parent_1",
                {"dlg_child_2"},
                set(),
                {"dlg_child_2"},
            ),
        )
        dialog = prime_sibling_payload(dialog_carrier=True)
        self.assertEqual(
            [],
            anime_assets._extract_dialog_tree_prime_reachable_story_playback_carriers(
                dialog,
                "dlg_parent_1",
                {"dlg_child_2"},
                {"dlg_child_2_001"},
                set(),
            ),
        )

    def test_malformed_prime_graphs_fail_closed(self) -> None:
        missing_prime_id = prime_sibling_payload()
        missing_prime_id["nodes"][0].pop("$id")
        duplicate_id = prime_sibling_payload()
        duplicate_id["nodes"][1]["$id"] = "17"
        wrong_connection = prime_sibling_payload()
        wrong_connection["connections"][1]["$type"] = "WrongConnection"
        dangling = prime_sibling_payload()
        dangling["connections"][1]["_targetNode"]["$ref"] = "missing"

        for candidate in (
            missing_prime_id,
            duplicate_id,
            wrong_connection,
            dangling,
        ):
            with self.subTest(candidate=candidate):
                self.assertEqual(
                    [],
                    anime_assets._extract_dialog_tree_prime_reachable_story_playback_carriers(
                        candidate,
                        "dlg_parent_1",
                        {"dlg_child_2"},
                        {"dlg_child_2_001"},
                        {"dlg_child_2"},
                    ),
                )

    def test_recovery_requires_registration_asset_name_and_parent_eligibility(self) -> None:
        registry = {
            "dlg_parent_1": {
                "registered": True,
                "memoryPackRecordKey": True,
                "registrationEvidence": ["memorypack_record_key"],
            },
        }
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "dlg_parent_1_p0000000000000001.json"
            path.write_text("{}", encoding="utf-8")
            decoded = {
                **prime_sibling_payload(),
                "_assetName": "dlg_parent_1",
            }
            with (
                patch.object(anime_assets, "_iter_anime_tree_files", return_value=[path]),
                patch.object(anime_assets, "_load_anime_resource_payload", return_value=decoded),
            ):
                rows = anime_assets.recover_dialog_tree_prime_reachable_story_playback_carriers(
                    registry,
                    {"dlg_child_2"},
                    {"dlg_child_2_001"},
                    {"dlg_parent_1"},
                )
                excluded = anime_assets.recover_dialog_tree_prime_reachable_story_playback_carriers(
                    registry,
                    {"dlg_child_2"},
                    {"dlg_child_2_001"},
                    {"dlg_other_1"},
                )
                excluded_empty = anime_assets.recover_dialog_tree_prime_reachable_story_playback_carriers(
                    registry,
                    {"dlg_child_2"},
                    {"dlg_child_2_001"},
                    set(),
                )

            self.assertEqual(1, len(rows))
            self.assertEqual("0000000000000001", rows[0]["sourcePathId"])
            self.assertIs(rows[0]["registeredDialogRoot"], True)
            self.assertEqual([], excluded)
            self.assertEqual([], excluded_empty)

            for bad_registry, asset_name in (
                ({}, "dlg_parent_1"),
                ({"dlg_parent_1": {"registered": True}}, "dlg_parent_1"),
                (registry, "dlg_other_1"),
            ):
                with (
                    patch.object(anime_assets, "_iter_anime_tree_files", return_value=[path]),
                    patch.object(
                        anime_assets,
                        "_load_anime_resource_payload",
                        return_value={**decoded, "_assetName": asset_name},
                    ),
                ):
                    self.assertEqual(
                        [],
                        anime_assets.recover_dialog_tree_prime_reachable_story_playback_carriers(
                            bad_registry,
                            {"dlg_child_2"},
                            {"dlg_child_2_001"},
                            {"dlg_parent_1"},
                        ),
                    )


class DialogTreeCompletionParentScopeTests(unittest.TestCase):
    def test_prime_dependency_never_selects_the_first_of_multiple_parents(self) -> None:
        one = {("dlg_child_2", "dlg_parent_1"): [{"nodeId": "2"}]}
        self.assertEqual(
            {"dlg_child_2": ("dlg_parent_1", [{"nodeId": "2"}])},
            language_bundle.unique_dialog_tree_prime_parent_groups(one),
        )
        conflicting = {
            **one,
            ("dlg_child_2", "dlg_parent_2"): [{"nodeId": "7"}],
        }
        self.assertEqual(
            {},
            language_bundle.unique_dialog_tree_prime_parent_groups(conflicting),
        )

    def test_hidden_parent_completion_observer_resolves_without_story_output(self) -> None:
        raw_flows = {
            "m1": {
                "quests": [{
                    "id": "m1_q#1",
                    "storyConnections": [completion_connection()],
                }],
            },
        }

        indexed = language_bundle.collect_dialog_tree_completion_parent_quests(
            raw_flows,
            {"dlg_parent_1"},
        )
        scope = language_bundle.select_dialog_tree_story_carrier_scope(
            indexed["dlg_parent_1"],
            {},
            {},
        )

        self.assertEqual("quest", scope["scopeKind"])
        self.assertEqual("m1", scope["missionId"])
        self.assertEqual("m1_q#1", scope["questId"])
        self.assertEqual("direct", scope["questEvidence"])
        row = scope["questRows"][0]
        self.assertEqual("CheckTalkOptionFinish", row["conditionType"])
        self.assertEqual(-1, row["finishId"])
        self.assertEqual("m1", row["missionId"])
        self.assertEqual("m1_q#1", row["questId"])

    def test_completion_parent_index_rejects_near_match_evidence(self) -> None:
        near_matches = [
            completion_connection(relation="failure_condition"),
            completion_connection(condition_type="CheckQuestState"),
            completion_connection(confidence="derived"),
            completion_connection(
                source="MissionRuntimeAsset.questDic[*].objectiveList[0].condition._finishId",
            ),
            completion_connection(parent_key="dlg_other_1"),
        ]
        raw_flows = {
            "m1": {
                "quests": [{
                    "id": "m1_q#1",
                    "storyConnections": near_matches,
                }],
            },
        }

        self.assertEqual(
            {},
            language_bundle.collect_dialog_tree_completion_parent_quests(
                raw_flows,
                {"dlg_parent_1"},
            ),
        )

    def test_completion_parent_scope_never_selects_a_favorable_quest(self) -> None:
        same_mission = {
            "m1": {
                "quests": [
                    {"id": "m1_q#1", "storyConnections": [completion_connection()]},
                    {"id": "m1_q#2", "storyConnections": [completion_connection()]},
                ],
            },
        }
        indexed = language_bundle.collect_dialog_tree_completion_parent_quests(
            same_mission,
            {"dlg_parent_1"},
        )
        scope = language_bundle.select_dialog_tree_story_carrier_scope(
            indexed["dlg_parent_1"],
            {},
            {},
        )
        self.assertEqual("mission", scope["scopeKind"])
        self.assertEqual(["m1_q#1", "m1_q#2"], scope["candidateQuestIds"])

        cross_mission = {
            **same_mission,
            "m2": {
                "quests": [{
                    "id": "m2_q#1",
                    "storyConnections": [completion_connection()],
                }],
            },
        }
        indexed = language_bundle.collect_dialog_tree_completion_parent_quests(
            cross_mission,
            {"dlg_parent_1"},
        )
        scope = language_bundle.select_dialog_tree_story_carrier_scope(
            indexed["dlg_parent_1"],
            {},
            {},
        )
        self.assertEqual("conflicting_parent_missions", scope["status"])
        self.assertNotIn("scopeKind", scope)


class DialogTreeStoryTrunkScopeTests(unittest.TestCase):
    def test_unique_direct_parent_quest_wins_over_derived_context(self) -> None:
        direct = {("m1", "m1_q#1"): [{"relation": "objective_condition"}]}
        derived = {("other", "other_q#1"): [{"relation": "levelscript_story_sequence"}]}
        scope = language_bundle.select_dialog_tree_story_carrier_scope(
            direct,
            derived,
            {"m1": [{"relation": "npc_proxy_ex_mission_context"}]},
        )

        self.assertEqual("quest", scope["scopeKind"])
        self.assertEqual("m1_q#1", scope["questId"])
        self.assertEqual("direct", scope["questEvidence"])

    def test_unique_derived_parent_quest_is_visible_as_derived(self) -> None:
        scope = language_bundle.select_dialog_tree_story_carrier_scope(
            {},
            {("m1", "m1_q#1"): [{"relation": "npc_proxy_ex_attachment"}]},
            {"m1": [{"relation": "npc_proxy_ex_mission_context"}]},
        )

        self.assertEqual("quest", scope["scopeKind"])
        self.assertEqual("derived", scope["questEvidence"])

    def test_multiple_parent_quests_select_only_the_shared_mission_shell(self) -> None:
        direct = {
            ("m1", "m1_q#1"): [{"relation": "objective_condition"}],
            ("m1", "m1_q#2"): [{"relation": "objective_condition"}],
        }
        scope = language_bundle.select_dialog_tree_story_carrier_scope(
            direct,
            {},
            {"m1": [{"relation": "npc_proxy_ex_mission_context"}]},
        )

        self.assertEqual("mission", scope["scopeKind"])
        self.assertEqual("m1", scope["missionId"])
        self.assertEqual(["m1_q#1", "m1_q#2"], scope["candidateQuestIds"])

    def test_multiple_variant_context_quests_select_only_shared_mission_shell(self) -> None:
        derived = {
            ("m1", "m1_q#1"): [{"relation": "variant_runtime_attachment"}],
            ("m1", "m1_q#2"): [{"relation": "variant_runtime_attachment"}],
        }

        scope = language_bundle.select_dialog_tree_story_carrier_scope(
            {},
            derived,
            {},
        )

        self.assertEqual("mission", scope["scopeKind"])
        self.assertEqual("m1", scope["missionId"])
        self.assertEqual("derived", scope["questEvidence"])

    def test_conflicting_parent_missions_fail_closed(self) -> None:
        scope = language_bundle.select_dialog_tree_story_carrier_scope(
            {("m1", "m1_q#1"): [{"relation": "objective_condition"}]},
            {},
            {"hidden": [{"relation": "npc_proxy_ex_mission_context"}]},
        )

        self.assertEqual("conflicting_parent_missions", scope["status"])
        self.assertNotIn("scopeKind", scope)

    def test_unique_mission_context_without_quest_selects_shell(self) -> None:
        scope = language_bundle.select_dialog_tree_story_carrier_scope(
            {},
            {},
            {"m1": [{"relation": "mission_accept_dialog"}]},
        )

        self.assertEqual("mission", scope["scopeKind"])
        self.assertEqual("m1", scope["missionId"])


class DialogTreeQuestStateCarrierScopeTests(unittest.TestCase):
    def carrier_payload(self) -> dict:
        condition = combine_condition(
            quest_condition("m1_q#1", 2),
            combine_condition(
                quest_condition("m1_q#2", 2),
                quest_condition("m1_q#3", 3),
            ),
            expression="{0} or {1}",
        )
        return {
            "type": "Beyond.Gameplay.DialogTree",
            "nodes": [
                {
                    "$id": "0",
                    "$type": "Beyond.Gameplay.DialogTreeIfNode",
                    "_dialogIfData": {"condition": condition},
                },
                node("1", node_type=TRUNK_TYPE, trunk_id="dlg_child_2_001"),
                node("2", node_type=TRUNK_TYPE, trunk_id="dlg_child_3_001"),
                node("3", node_type=TRUNK_TYPE, trunk_id="dlg_parent_1_001"),
                node("4", node_type="Beyond.Gameplay.DialogTreeFinishNode"),
            ],
            "connections": [
                connection("0", "1"),
                connection("1", "2"),
                connection("2", "3"),
                connection("0", "4"),
            ],
        }

    def test_recursive_all_leaf_gate_yields_only_shared_mission_context(self) -> None:
        rows = anime_assets._extract_dialog_tree_story_playback_carriers(
            self.carrier_payload(),
            "dlg_parent_1",
            {"dlg_child_2", "dlg_child_3"},
        )

        self.assertEqual(2, len(rows))
        for row in rows:
            context = row["questStateBranchContexts"][0]
            self.assertIs(context["noBypass"], True)
            self.assertEqual(["m1_q#1", "m1_q#2", "m1_q#3"], context["questIds"])
            self.assertEqual(3, len(context["conditions"]))
            self.assertEqual(2, len(context["combineConditions"]))

        scope = language_bundle.select_cross_story_quest_state_carrier_scope(
            rows,
            {
                "m1_q#1": ("m1", {}),
                "m1_q#2": ("m1", {}),
                "m1_q#3": ("m1", {}),
            },
        )
        self.assertEqual("mission", scope["scopeKind"])
        self.assertEqual("m1", scope["missionId"])
        self.assertNotIn("questId", scope)
        context = scope["carrierQuestStateContext"]
        self.assertIs(context["ownership"], False)
        self.assertIs(context["dependencyOnly"], True)

    def test_mixed_leaf_or_bypass_path_rejects_carrier_context(self) -> None:
        mixed = self.carrier_payload()
        mixed_condition = mixed["nodes"][0]["_dialogIfData"]["condition"]
        mixed_condition["subConditions"][1]["subConditions"][0]["$type"] = (
            "Beyond.Gameplay.CheckMissionState"
        )
        bypass = self.carrier_payload()
        bypass["nodes"].append(node("5"))
        bypass["connections"].append(connection("5", "1"))

        for candidate in (mixed, bypass):
            with self.subTest(candidate=candidate):
                rows = anime_assets._extract_dialog_tree_story_playback_carriers(
                    candidate,
                    "dlg_parent_1",
                    {"dlg_child_2", "dlg_child_3"},
                )
                self.assertEqual(2, len(rows))
                self.assertTrue(all(
                    not row["questStateBranchContexts"]
                    for row in rows
                ))

    def test_missing_or_cross_mission_quest_resolution_fails_closed(self) -> None:
        rows = anime_assets._extract_dialog_tree_story_playback_carriers(
            self.carrier_payload(),
            "dlg_parent_1",
            {"dlg_child_2", "dlg_child_3"},
        )
        for targets in (
            {
                "m1_q#1": ("m1", {}),
                "m1_q#2": ("m1", {}),
            },
            {
                "m1_q#1": ("m1", {}),
                "m1_q#2": ("m2", {}),
                "m1_q#3": ("m1", {}),
            },
        ):
            with self.subTest(targets=targets):
                self.assertEqual(
                    {},
                    language_bundle.select_cross_story_quest_state_carrier_scope(
                        rows,
                        targets,
                    ),
                )

        self.assertEqual(
            {},
            language_bundle.select_cross_story_quest_state_carrier_scope(
                [*rows, {"storyKey": "unproved"}],
                {
                    "m1_q#1": ("m1", {}),
                    "m1_q#2": ("m1", {}),
                    "m1_q#3": ("m1", {}),
                },
            ),
        )


if __name__ == "__main__":
    unittest.main()

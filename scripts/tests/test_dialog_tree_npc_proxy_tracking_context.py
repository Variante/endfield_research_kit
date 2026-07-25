from __future__ import annotations

from copy import deepcopy
import unittest

from scripts.story_builder import anime_assets, language_bundle


class NpcProxyTrackingDialogNavigationContextTests(unittest.TestCase):
    def fixture(self) -> dict:
        visibility_filter = {
            "role": "tracking_marker_visibility_only",
            "conditionType": "CheckQuestState",
            "serializedCondition": {
                "$type": "Beyond.Gameplay.CheckQuestState",
                "_questId": {"constValue": "m1_q#10"},
            },
        }
        return {
            "npc_tracking_consumers": {
                "proxy_a": [{
                    "type": "NpcProxyTrackingInfo",
                    "missionId": "m1",
                    "questId": "m1_q#10",
                    "scene": "level_a",
                    "trackingVisibilityFilter": visibility_filter,
                }],
            },
            "npc_proxy_rows": {
                "proxy_a": {
                    "proxyId": "proxy_a",
                    "levelId": "level_a",
                    "subDataParentId": 100,
                    "position": {"x": 1, "y": 2, "z": 3},
                },
            },
            "npc_proxy_ex": {
                "data": {
                    "proxy_a": [{
                        "dialogId": "dlg_parent",
                        "missionId": "",
                    }],
                },
            },
            "world_entity_registry": {
                "npcProxyBriefInfos": {
                    "101": {
                        "proxyId": "proxy_a",
                        "segmentIdGlobal": 101,
                        "position": {"x": 1, "y": 2, "z": 3},
                    },
                },
            },
            "dialog_id_registry": {
                "dlg_parent": {
                    "registered": True,
                    "memoryPackRecordKey": True,
                    "registrationEvidence": ["memorypack_record_key"],
                },
            },
            "dialog_tree_story_playback_groups": {
                ("dlg_child", "dlg_parent"): [{
                    "carrierKind": "dialog",
                    "dialogId": "dlg_child",
                    "dialogKey": "dlg_parent",
                    "sourceFile": "fixture.json",
                }],
            },
        }

    def build(self, fixture: dict) -> list[dict]:
        return language_bundle.build_npc_proxy_tracking_dialog_navigation_contexts(
            **fixture,
        )

    def test_exact_chain_retains_visibility_filter_as_non_playback_context(self) -> None:
        fixture = self.fixture()
        rows = self.build(fixture)

        self.assertEqual(1, len(rows))
        row = rows[0]
        self.assertEqual("dlg_parent", row["parentStoryKey"])
        self.assertEqual(["dlg_child"], row["childStoryKeys"])
        self.assertEqual(
            fixture["npc_tracking_consumers"]["proxy_a"][0][
                "trackingVisibilityFilter"
            ],
            row["trackingVisibilityFilter"],
        )
        self.assertIs(row["storyBinding"], True)
        self.assertIs(row["ownership"], False)
        self.assertIs(row["questPlayback"], False)
        self.assertIs(row["questCompletion"], False)
        self.assertIs(row["serverExchange"], False)

    def test_ambiguous_or_inexact_join_components_fail_closed(self) -> None:
        mutations = {
            "duplicate consumer": lambda row: row["npc_tracking_consumers"][
                "proxy_a"
            ].append(deepcopy(row["npc_tracking_consumers"]["proxy_a"][0])),
            "scene mismatch": lambda row: row["npc_proxy_rows"]["proxy_a"].update(
                levelId="other"
            ),
            "registry identity mismatch": lambda row: row[
                "world_entity_registry"
            ]["npcProxyBriefInfos"]["101"].update(segmentIdGlobal=102),
            "registry position mismatch": lambda row: row[
                "world_entity_registry"
            ]["npcProxyBriefInfos"]["101"]["position"].update(x=99),
            "two dialogs": lambda row: row["npc_proxy_ex"]["data"]["proxy_a"].append(
                {"dialogId": "dlg_other", "missionId": ""}
            ),
            "authored mission owner": lambda row: row["npc_proxy_ex"]["data"][
                "proxy_a"
            ][0].update(missionId="other_mission"),
            "unregistered parent": lambda row: row["dialog_id_registry"][
                "dlg_parent"
            ].update(memoryPackRecordKey=False),
            "untyped child route": lambda row: row[
                "dialog_tree_story_playback_groups"
            ][("dlg_child", "dlg_parent")][0].update(carrierKind="trunk"),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                fixture = self.fixture()
                mutate(fixture)
                self.assertEqual([], self.build(fixture))

    def test_tracking_extractor_preserves_exact_visibility_condition(self) -> None:
        condition = {
            "$type": "Beyond.Gameplay.CheckQuestState",
            "_questId": {"constValue": "m1_q#10"},
            "_comparer": {},
            "_targetQuestState": {"constValue": 2},
        }
        payload = {
            "objectiveList": [{
                "trackingInfoList": [{
                    "$type": "Beyond.Gameplay.NpcProxyTrackingInfo",
                    "sceneId": "level_a",
                    "npcProxyId": "proxy_a",
                    "useFilterCondition": True,
                    "filterCondition": condition,
                }],
            }],
        }

        rows = anime_assets._extract_tracking_hints(payload)

        self.assertEqual(1, len(rows))
        self.assertIs(rows[0]["useFilterCondition"], True)
        self.assertEqual(
            "tracking_marker_visibility_only",
            rows[0]["trackingVisibilityFilter"]["role"],
        )
        self.assertEqual(
            condition,
            rows[0]["trackingVisibilityFilter"]["serializedCondition"],
        )
        self.assertIsNot(
            condition,
            rows[0]["trackingVisibilityFilter"]["serializedCondition"],
        )


if __name__ == "__main__":
    unittest.main()

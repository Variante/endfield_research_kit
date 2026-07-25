from __future__ import annotations

import unittest

from scripts.story_builder.language_bundle import (
    build_domain_depot_story_connections,
    build_factory_lock_story_dependencies,
    build_skip_chapter_story_connections,
)


class OriginalSystemStoryBindingTests(unittest.TestCase):
    def test_domain_depot_requires_both_exact_proxy_joins(self) -> None:
        rows = build_domain_depot_story_connections(
            {"depotDeliverMissionId": "system_mission"},
            {
                "npc_exact": {
                    "npcProxyId": "npc_exact",
                    "initialDialogId": "dlg_initial",
                    "repeatDialogId": "dlg_repeat",
                },
                "dialog_key_mismatch": {
                    "npcProxyId": "different_proxy",
                    "initialDialogId": "dlg_rejected_key",
                },
                "npc_without_target": {
                    "npcProxyId": "npc_without_target",
                    "initialDialogId": "dlg_rejected_target",
                },
            },
            {
                "target_row": {
                    "deliverTargetId": "target_row",
                    "targetId": "npc_exact",
                    "domainId": "domain_1",
                    "level": "map01_lv005",
                    "entityType": 1,
                },
            },
            {"system_mission"},
        )

        self.assertEqual(
            [(row["missionId"], row["key"], row["dialogField"]) for row in rows],
            [
                ("system_mission", "dlg_initial", "initialDialogId"),
                ("system_mission", "dlg_repeat", "repeatDialogId"),
            ],
        )
        self.assertEqual(rows[0]["deliverTargets"][0]["targetId"], "npc_exact")

    def test_domain_depot_does_not_infer_an_unavailable_mission(self) -> None:
        self.assertEqual(build_domain_depot_story_connections(
            {"depotDeliverMissionId": "looks_like_a_mission"},
            {
                "npc": {
                    "npcProxyId": "npc",
                    "initialDialogId": "dlg_looks_related",
                },
            },
            {"target": {"targetId": "npc"}},
            {"different_mission"},
        ), [])

    def test_skip_chapter_uses_only_same_row_typed_fields(self) -> None:
        rows = build_skip_chapter_story_connections(
            {
                "skip_1": {
                    "skipChapterConfigId": "skip_1",
                    "missionId": "mission_exact",
                    "bindDlgId": "dlg_unrelated_name",
                    "bindActivityId": "activity_1",
                },
                "wrong_key": {
                    "skipChapterConfigId": "different_config",
                    "missionId": "mission_exact",
                    "bindDlgId": "dlg_rejected",
                },
            },
            {"mission_exact"},
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["missionId"], "mission_exact")
        self.assertEqual(rows[0]["key"], "dlg_unrelated_name")
        self.assertEqual(rows[0]["skipChapterConfigId"], "skip_1")

    def test_factory_lock_resolves_exact_quest_owners_without_name_parsing(self) -> None:
        rows = build_factory_lock_story_dependencies(
            {
                "building_1": {
                    "list": [{
                        "startQuestId": "opaque_start",
                        "endQuestId": "opaque_end",
                        "radioId": "radio_name_suggests_wrong_mission",
                        "lockType": 1,
                        "priority": 1,
                        "args": [],
                    }],
                },
                "building_2": {
                    "list": [{
                        "startQuestId": "prefixm1_q#1",
                        "endQuestId": "",
                        "radioId": "radio_prefixm1_1",
                    }],
                },
            },
            {
                "opaque_start": ("mission_a", {"id": "opaque_start"}),
                "opaque_end": ("mission_b", {"id": "opaque_end"}),
            },
        )

        self.assertEqual(
            [(row["missionId"], row["questGateRoles"][0]["field"]) for row in rows],
            [("mission_a", "startQuestId"), ("mission_b", "endQuestId")],
        )
        self.assertTrue(all(
            row["key"] == "radio_name_suggests_wrong_mission"
            for row in rows
        ))
        self.assertNotIn("prefixm1", {row["missionId"] for row in rows})


if __name__ == "__main__":
    unittest.main()

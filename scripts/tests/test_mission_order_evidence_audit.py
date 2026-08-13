from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.story_recovery.build_mission_order_evidence_audit import (
    collect_npc_proxy_dialog_hits,
    collect_reading_prts_links,
)


class MissionOrderEvidenceAuditTests(unittest.TestCase):
    def test_reading_prts_suffix_match_is_cross_reference_not_link(self) -> None:
        reading_rows = {
            "rp_text_e11m4_3": {
                "contentId": "text_e11m4_3",
                "bgType": 0,
                "iconType": 3,
            },
        }
        with patch(
            "scripts.story_recovery.build_mission_order_evidence_audit.read_json",
            side_effect=[reading_rows, {}, {}],
        ):
            links = collect_reading_prts_links(["dlg_e11m4_3", "text_e11m4_3"])

        dialog_links = links["dlg_e11m4_3"]
        self.assertEqual(dialog_links["readingPopups"], [])
        self.assertEqual(dialog_links["prtsItems"], [])
        self.assertEqual(
            dialog_links["crossReferences"][0]["matchType"],
            "suffix_cross_reference",
        )
        text_links = links["text_e11m4_3"]
        self.assertEqual(
            text_links["readingPopups"][0]["matchType"],
            "exact_content_id",
        )
        self.assertEqual(text_links["crossReferences"], [])

    def test_collects_mission_level_npc_proxy_runtime_context_without_quest(self) -> None:
        entry_report = {"dlg_e11m4_4": {"hits": {}}}
        webui_mission = {
            "flow": {
                "quests": [],
                "missionStoryConnections": [
                    {
                        "key": "dlg_e11m4_4",
                        "relation": "npc_proxy_ex_mission_context",
                        "npcProxyId": "lizy_map02_v1d4d0_006",
                        "npcProxyMissionId": "e11m4",
                        "storyOwnerMission": "e11m4",
                        "source": "NpcProxyExDataTable.data[*].missionId + dialogId",
                        "selectionOrderStatus": (
                            "one_based_active_row_selection_only_no_cross_row_chronology"
                        ),
                        "nativeMappingId": "npc-proxy-dialog-selection-native-v1",
                        "gameAssemblySha256": "binary-hash",
                    }
                ],
            },
        }

        anchored = collect_npc_proxy_dialog_hits(webui_mission, entry_report)

        self.assertEqual(anchored, 1)
        hit = entry_report["dlg_e11m4_4"]["hits"]["npcProxyDialog"]
        self.assertEqual(hit["count"], 1)
        self.assertEqual(hit["quests"], [])
        self.assertEqual(
            hit["missionContexts"][0]["npcProxyId"],
            "lizy_map02_v1d4d0_006",
        )
        self.assertEqual(
            hit["missionContexts"][0]["selectionOrderStatus"],
            "one_based_active_row_selection_only_no_cross_row_chronology",
        )


if __name__ == "__main__":
    unittest.main()

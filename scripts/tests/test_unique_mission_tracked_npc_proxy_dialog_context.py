from __future__ import annotations

from copy import deepcopy
import unittest

from scripts.story_builder import language_bundle


class UniqueMissionTrackedNpcProxyDialogContextTests(unittest.TestCase):
    def fixture(self) -> dict:
        registration = {
            "registered": True,
            "memoryPackRecordKey": True,
            "registrationEvidence": [
                "memorypack_record_key",
                "printable_root_token",
            ],
        }
        return {
            "npc_tracking_consumers": {
                "proxy_a": [{
                    "type": "NpcProxyTrackingInfo",
                    "missionId": "m1",
                    "questId": "m1_q#2",
                    "scene": "level_a",
                    "useFilterCondition": False,
                    "trackingVisibilityFilter": None,
                }, {
                    "type": "NpcProxyTrackingInfo",
                    "missionId": "m1",
                    "questId": "m1_q#7",
                    "scene": "level_a",
                    "useFilterCondition": False,
                    "trackingVisibilityFilter": None,
                }],
            },
            "npc_proxy_rows": {
                "proxy_a": {
                    "proxyId": "proxy_a",
                    "levelId": "level_a",
                    "subDataParentId": 100,
                },
            },
            "npc_proxy_ex": {
                "data": {
                    "proxy_a": [{
                        "missionId": "",
                        "dialogId": "",
                    }, {
                        "missionId": "",
                        "dialogId": "dlg_m1_1",
                    }, {
                        "missionId": "",
                        "dialogId": "dlg_m1_2",
                    }],
                },
            },
            "dialog_id_registry": {
                "dlg_m1_1": deepcopy(registration),
                "dlg_m1_2": deepcopy(registration),
            },
        }

    def build(self, fixture: dict) -> list[dict]:
        return (
            language_bundle
            .build_unique_mission_tracked_npc_proxy_dialog_contexts(
                **fixture,
            )
        )

    def test_shared_proxy_dialogs_keep_one_mission_and_all_quests(self) -> None:
        rows = self.build(self.fixture())

        self.assertEqual(1, len(rows))
        row = rows[0]
        self.assertEqual("m1", row["missionId"])
        self.assertEqual("level_a", row["levelId"])
        self.assertEqual(["m1_q#2", "m1_q#7"], row["questIds"])
        self.assertEqual(["dlg_m1_1", "dlg_m1_2"], row["dialogIds"])
        self.assertEqual([2, 3], [
            item["activeRowIndex"] for item in row["dialogSelections"]
        ])
        self.assertIs(row["storyBinding"], True)
        self.assertIs(row["ownership"], False)
        self.assertIs(row["questActivation"], False)
        self.assertIs(row["questPlayback"], False)
        self.assertIs(row["questCompletion"], False)

    def test_rejects_cross_mission_or_cross_level_tracking(self) -> None:
        for field, value in (
            ("missionId", "m2"),
            ("scene", "level_b"),
        ):
            with self.subTest(field=field):
                fixture = deepcopy(self.fixture())
                fixture["npc_tracking_consumers"]["proxy_a"][1][field] = value
                self.assertEqual([], self.build(fixture))

    def test_discovers_additional_future_proxy_without_an_allowlist(self) -> None:
        fixture = self.fixture()
        fixture["npc_tracking_consumers"]["proxy_future"] = [{
            "type": "NpcProxyTrackingInfo",
            "missionId": "future_mission",
            "questId": "future_mission_q#12",
            "scene": "future_level",
            "useFilterCondition": False,
            "trackingVisibilityFilter": None,
        }]
        fixture["npc_proxy_rows"]["proxy_future"] = {
            "proxyId": "proxy_future",
            "levelId": "future_level",
            "subDataParentId": 200,
        }
        fixture["npc_proxy_ex"]["data"]["proxy_future"] = [{
            "missionId": "",
            "dialogId": "dlg_future_1",
        }]
        fixture["dialog_id_registry"]["dlg_future_1"] = deepcopy(
            fixture["dialog_id_registry"]["dlg_m1_1"]
        )

        rows = self.build(fixture)
        self.assertEqual(
            [(row["npcProxyId"], row["missionId"]) for row in rows],
            [("proxy_a", "m1"), ("proxy_future", "future_mission")],
        )

    def test_rejects_filtered_or_mixed_tracking_rows(self) -> None:
        for mutation in ("filtered", "mixed"):
            with self.subTest(mutation=mutation):
                fixture = deepcopy(self.fixture())
                fixture["npc_tracking_consumers"]["proxy_a"][0][
                    "useFilterCondition"
                ] = True
                fixture["npc_tracking_consumers"]["proxy_a"][0][
                    "trackingVisibilityFilter"
                ] = {"conditionType": "fixture"}
                if mutation == "filtered":
                    fixture["npc_tracking_consumers"]["proxy_a"] = [
                        fixture["npc_tracking_consumers"]["proxy_a"][0]
                    ]
                self.assertEqual([], self.build(fixture))

    def test_rejects_authored_mission_owner_or_level_mismatch(self) -> None:
        owned = deepcopy(self.fixture())
        owned["npc_proxy_ex"]["data"]["proxy_a"][1]["missionId"] = "m1"
        self.assertEqual([], self.build(owned))

        mismatched = deepcopy(self.fixture())
        mismatched["npc_proxy_rows"]["proxy_a"]["levelId"] = "level_b"
        self.assertEqual([], self.build(mismatched))

    def test_rejects_unregistered_duplicate_or_no_dialogs(self) -> None:
        for mutation in ("unregistered", "duplicate", "all_empty"):
            with self.subTest(mutation=mutation):
                fixture = deepcopy(self.fixture())
                if mutation == "unregistered":
                    fixture["dialog_id_registry"]["dlg_m1_2"][
                        "memoryPackRecordKey"
                    ] = False
                elif mutation == "duplicate":
                    fixture["npc_proxy_ex"]["data"]["proxy_a"][1][
                        "dialogId"
                    ] = "dlg_m1_1"
                    fixture["npc_proxy_ex"]["data"]["proxy_a"][2][
                        "dialogId"
                    ] = "dlg_m1_1"
                else:
                    fixture["npc_proxy_ex"]["data"]["proxy_a"][1][
                        "dialogId"
                    ] = ""
                    fixture["npc_proxy_ex"]["data"]["proxy_a"][2][
                        "dialogId"
                    ] = ""
                self.assertEqual([], self.build(fixture))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from copy import deepcopy
import unittest

from scripts.story_builder import language_bundle


class NpcProxyLazyDestroyDialogContextTests(unittest.TestCase):
    def fixture(self) -> dict:
        return {
            "npc_tracking_consumers": {
                "proxy_a": [{
                    "type": "NpcProxyTrackingInfo",
                    "missionId": "m1",
                    "questId": "m1_q#7",
                    "scene": "level_a",
                    "sourceFile": "MissionRuntimeAsset/m1.json",
                }],
            },
            "npc_proxy_rows": {
                "proxy_a": {
                    "proxyId": "proxy_a",
                    "levelId": "level_a",
                    "subDataParentId": 100,
                    "lazyDestroy": True,
                    "lazyDestroyOverrideDialogId": "dlg_m1_7",
                },
            },
            "available_story_keys": {"dlg_m1_7"},
        }

    def build(self, fixture: dict) -> list[dict]:
        return language_bundle.build_npc_proxy_lazy_destroy_dialog_contexts(
            **fixture,
        )

    def test_exact_same_scene_tracked_proxy_is_context_only(self) -> None:
        rows = self.build(self.fixture())

        self.assertEqual(1, len(rows))
        row = rows[0]
        self.assertEqual("m1", row["missionId"])
        self.assertEqual("m1_q#7", row["questId"])
        self.assertEqual("dlg_m1_7", row["storyKey"])
        self.assertEqual(
            "npc_proxy_lazy_destroy_dialog_context",
            row["relation"],
        )
        self.assertIs(row["storyBinding"], True)
        self.assertIs(row["ownership"], False)
        self.assertIs(row["questPlayback"], False)
        self.assertIs(row["questCompletion"], False)
        self.assertIs(row["serverExchange"], True)
        self.assertIs(row["clientRequest"], False)
        self.assertIs(row["expectedClientReply"], False)

    def test_requires_enabled_lazy_destroy_and_exact_proxy_identity(self) -> None:
        for mutation in ("disabled", "wrong_proxy"):
            with self.subTest(mutation=mutation):
                fixture = deepcopy(self.fixture())
                if mutation == "disabled":
                    fixture["npc_proxy_rows"]["proxy_a"]["lazyDestroy"] = False
                else:
                    fixture["npc_proxy_rows"]["proxy_a"]["proxyId"] = "proxy_b"
                self.assertEqual([], self.build(fixture))

    def test_rejects_scene_mismatch_and_reused_tracking_proxy(self) -> None:
        scene_mismatch = deepcopy(self.fixture())
        scene_mismatch["npc_tracking_consumers"]["proxy_a"][0]["scene"] = (
            "level_b"
        )
        self.assertEqual([], self.build(scene_mismatch))

        ambiguous = deepcopy(self.fixture())
        ambiguous["npc_tracking_consumers"]["proxy_a"].append({
            "type": "NpcProxyTrackingInfo",
            "missionId": "m2",
            "questId": "m2_q#1",
            "scene": "level_a",
        })
        self.assertEqual([], self.build(ambiguous))

    def test_requires_one_unambiguous_existing_story_key(self) -> None:
        missing = deepcopy(self.fixture())
        missing["available_story_keys"] = set()
        self.assertEqual([], self.build(missing))

        ambiguous_alias = deepcopy(self.fixture())
        ambiguous_alias["available_story_keys"].add("misc_dlg_m1_7")
        self.assertEqual([], self.build(ambiguous_alias))


if __name__ == "__main__":
    unittest.main()

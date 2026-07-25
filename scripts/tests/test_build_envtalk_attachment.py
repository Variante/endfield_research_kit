from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
if str(ROOT / "scripts" / "story_recovery") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts" / "story_recovery"))

import build_envtalk_attachment as eta  # noqa: E402


def npc_proxy_tracking(proxy_id):
    return {
        "$type": "Beyond.Gameplay.NpcProxyTrackingInfo, Gameplay.Beyond",
        "npcProxyId": proxy_id,
    }


def entity_tracking(proxy_id):
    # A different typed tracking record that happens to carry the same field
    # name must not be accepted.
    return {
        "$type": "Beyond.Gameplay.EntityTrackingInfo, Gameplay.Beyond",
        "npcProxyId": proxy_id,
    }


class Fixture:
    def __init__(self, *, env_talk=None, proxies=None, clusters=None, npcs=None, missions=None):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.table_root = base / "Table"
        self.gameplay_root = base / "GameplayConfig"
        self.mission_root = base / "MissionRuntimeAsset"
        for path in (self.table_root, self.gameplay_root, self.mission_root):
            path.mkdir(parents=True, exist_ok=True)

        write = lambda p, obj: p.write_text(json.dumps(obj), encoding="utf-8")  # noqa: E731
        write(self.table_root / "EnvTalkTable.json", {k: {"envTalkId": k} for k in (env_talk or [])})
        write(self.table_root / "NpcTable.json", npcs or {})
        write(self.gameplay_root / "NpcProxyTable.json", {"dataTable": proxies or {}})
        write(self.gameplay_root / "NpcProxyExDataTable.json", {"dataTable": {}})
        write(
            self.gameplay_root / "AtmosphericNpcClusterDataTable.json",
            {"dataTable": clusters or {}},
        )
        for mission_id, document in (missions or {}).items():
            write(self.mission_root / f"{mission_id}.json", document)
            write(self.mission_root / f"{mission_id}_meta.json", {"missionId": mission_id})

    def build(self):
        return eta.build_report(
            table_root=self.table_root,
            gameplay_root=self.gameplay_root,
            mission_root=self.mission_root,
        )

    def cleanup(self):
        self._tmp.cleanup()


class Base(unittest.TestCase):
    def make(self, **kwargs):
        fixture = Fixture(**kwargs)
        self.addCleanup(fixture.cleanup)
        return fixture


class IdentityTests(Base):
    def test_story_key_is_prefixed_definition_id(self):
        report = self.make(env_talk=["envTalk_a_1"]).build()
        self.assertEqual(report["entries"][0]["storyKey"], "env_envTalk_a_1")

    def test_every_definition_gets_an_entry(self):
        report = self.make(env_talk=["envTalk_a_1", "envTalk_a_2"]).build()
        self.assertEqual(report["counts"]["definitions"], 2)
        self.assertEqual(len(report["entries"]), 2)

    def test_definition_without_consumer_is_reported_as_such(self):
        report = self.make(env_talk=["envTalk_a_1"]).build()
        entry = report["entries"][0]
        self.assertEqual(entry["relation"], eta.RELATION_NONE)
        self.assertEqual(entry["consumers"], [])


class ConsumerScopeTests(Base):
    def test_cluster_supplies_level_scope(self):
        report = self.make(
            env_talk=["envTalk_a_1"],
            clusters={
                "cluster_1": {
                    "clusterId": "cluster_1",
                    "envTalkId": "envTalk_a_1",
                    "levelId": "map01_lv001",
                    "npcIds": ["npc_b"],
                }
            },
        ).build()
        entry = report["entries"][0]
        self.assertEqual(entry["relation"], eta.RELATION_LEVEL_SCOPED)
        self.assertEqual(entry["levelIds"], ["map01_lv001"])
        self.assertEqual(entry["consumers"][0]["npcIds"], ["npc_b"])

    def test_npc_table_row_is_character_scoped(self):
        report = self.make(
            env_talk=["envTalk_a_1"],
            npcs={"npc_b": {"npcId": "npc_b", "envTalkIds": ["envTalk_a_1"]}},
        ).build()
        self.assertEqual(report["entries"][0]["relation"], eta.RELATION_CHARACTER_SCOPED)

    def test_nested_lazy_destroy_env_talk_is_collected(self):
        report = self.make(
            env_talk=["envTalk_a_1"],
            proxies={
                "proxy_1": {
                    "levelId": "map01_lv001",
                    "envTalkIds": [],
                    "lazyDestroyEnvTalkData": {"envTalkIds": ["envTalk_a_1"]},
                }
            },
        ).build()
        self.assertEqual(report["entries"][0]["relation"], eta.RELATION_LEVEL_SCOPED)


class QuestContextTests(Base):
    PROXY = {"proxy_1": {"levelId": "map01_lv001", "envTalkIds": ["envTalk_a_1"]}}

    def test_typed_tracking_creates_quest_context(self):
        report = self.make(
            env_talk=["envTalk_a_1"],
            proxies=self.PROXY,
            missions={
                "alpha": {
                    "questDic": {
                        "alpha_q#1": {
                            "objectiveList": [
                                {"trackingInfoList": [npc_proxy_tracking("proxy_1")]}
                            ]
                        }
                    }
                }
            },
        ).build()
        entry = report["entries"][0]
        self.assertEqual(entry["relation"], eta.RELATION_QUEST_TRACKED_PROXY)
        context = entry["questContexts"][0]
        self.assertEqual(context["missionId"], "alpha")
        self.assertEqual(context["questId"], "alpha_q#1")
        self.assertEqual(context["npcProxyId"], "proxy_1")

    def test_other_tracking_types_are_not_accepted(self):
        report = self.make(
            env_talk=["envTalk_a_1"],
            proxies=self.PROXY,
            missions={
                "alpha": {
                    "questDic": {
                        "alpha_q#1": {
                            "objectiveList": [{"trackingInfoList": [entity_tracking("proxy_1")]}]
                        }
                    }
                }
            },
        ).build()
        entry = report["entries"][0]
        self.assertEqual(entry["questContexts"], [])
        self.assertEqual(entry["relation"], eta.RELATION_LEVEL_SCOPED)

    def test_bare_proxy_name_string_is_not_a_binding(self):
        # The same literal appearing outside a typed tracking record must not
        # attach the envTalk to the mission.
        report = self.make(
            env_talk=["envTalk_a_1"],
            proxies=self.PROXY,
            missions={
                "alpha": {
                    "questDic": {
                        "alpha_q#1": {"descriptionKey": "proxy_1", "someOtherField": "proxy_1"}
                    }
                }
            },
        ).build()
        self.assertEqual(report["entries"][0]["questContexts"], [])

    def test_quest_context_relation_never_claims_ownership(self):
        policy = eta.RELATION_SUMMARY[eta.RELATION_QUEST_TRACKED_PROXY]
        self.assertIn("never playback ownership", policy)


class DanglingReferenceTests(Base):
    def test_undefined_reference_is_reported_not_dropped(self):
        report = self.make(
            env_talk=["envTalk_a_1"],
            proxies={"proxy_1": {"levelId": "L", "envTalkIds": ["envTalk_missing"]}},
        ).build()
        self.assertEqual(report["counts"]["danglingConsumerReferences"], 1)
        item = report["danglingConsumerReferences"][0]
        self.assertEqual(item["reference"], "envTalk_missing")
        self.assertFalse(item["hasSurroundingWhitespace"])
        self.assertFalse(item["trimmedIdIsDefined"])

    def test_whitespace_damaged_reference_is_flagged_but_not_repaired(self):
        report = self.make(
            env_talk=["envTalk_a_1"],
            proxies={"proxy_1": {"levelId": "L", "envTalkIds": ["envTalk_a_1 "]}},
        ).build()
        item = report["danglingConsumerReferences"][0]
        self.assertTrue(item["hasSurroundingWhitespace"])
        self.assertTrue(item["trimmedIdIsDefined"])
        # The defined id must NOT gain an attachment from the damaged reference.
        entry = next(e for e in report["entries"] if e["envTalkId"] == "envTalk_a_1")
        self.assertEqual(entry["relation"], eta.RELATION_NONE)
        self.assertEqual(entry["consumers"], [])

    def test_counts_split_whitespace_from_genuinely_missing(self):
        report = self.make(
            env_talk=["envTalk_a_1"],
            proxies={
                "p1": {"levelId": "L", "envTalkIds": ["envTalk_a_1 "]},
                "p2": {"levelId": "L", "envTalkIds": ["envTalk_gone"]},
            },
        ).build()
        counts = report["counts"]
        self.assertEqual(counts["danglingConsumerReferences"], 2)
        self.assertEqual(counts["danglingWithSurroundingWhitespace"], 1)
        self.assertEqual(counts["danglingRepairableByTrim"], 1)


class RenderTests(Base):
    def test_markdown_renders(self):
        report = self.make(
            env_talk=["envTalk_a_1"],
            proxies={"proxy_1": {"levelId": "map01_lv001", "envTalkIds": ["envTalk_a_1"]}},
        ).build()
        text = eta.render_markdown(report)
        self.assertIn("# envTalk attachment", text)
        self.assertNotIn("Dangling consumer references", text)


if __name__ == "__main__":
    unittest.main()

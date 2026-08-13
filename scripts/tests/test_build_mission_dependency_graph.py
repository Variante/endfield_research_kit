from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
from story_builder import mission_dependency_graph as mdg  # noqa: E402


def check_mission_state(mission_id, state=3, comparer=0, unique_id="u1"):
    return {
        "$type": "Beyond.Gameplay.CheckMissionState, Gameplay.Beyond",
        "uniqueId": unique_id,
        "_missionId": {"constValue": mission_id},
        "_comparer": {"constValue": comparer},
        "_targetMissionState": {"constValue": state},
    }


def check_quest_state(quest_id, state=3, comparer=0, unique_id="u2"):
    return {
        "$type": "Beyond.Gameplay.CheckQuestState, Gameplay.Beyond",
        "uniqueId": unique_id,
        "_questId": {"constValue": quest_id},
        "_comparer": {"constValue": comparer},
        "_targetQuestState": {"constValue": state},
    }


def quest(objectives=None, failed=None, prev=None):
    node = {"objectiveList": [{"condition": c} for c in (objectives or [])]}
    if failed is not None:
        node["failedCondition"] = failed
    if prev is not None:
        node["prevQuestIdList"] = prev
    return node


class MissionRootFixture:
    """Write a throwaway MissionRuntimeAsset directory."""

    def __init__(self, missions):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for mission_id, quest_dic in missions.items():
            (self.root / f"{mission_id}.json").write_text(
                json.dumps({"questDic": quest_dic}), encoding="utf-8"
            )
            # A sibling sidecar must never be parsed as a mission.
            (self.root / f"{mission_id}_meta.json").write_text(
                json.dumps({"missionId": mission_id, "acceptMode": {"mode": 2}}),
                encoding="utf-8",
            )

    def cleanup(self):
        self._tmp.cleanup()


class QuestOwnerTests(unittest.TestCase):
    def test_parses_owning_mission(self):
        self.assertEqual(mdg.quest_owner_mission("e7m4_q#13"), "e7m4")
        self.assertEqual(mdg.quest_owner_mission("db01m1d7_q#18"), "db01m1d7")

    def test_named_quest_suffixes_still_resolve(self):
        # Authored quest ids are not always numeric.
        self.assertEqual(mdg.quest_owner_mission("c31m1_q#Foucsmode"), "c31m1")

    def test_non_quest_id_is_rejected(self):
        self.assertIsNone(mdg.quest_owner_mission("e7m4"))
        self.assertIsNone(mdg.quest_owner_mission(""))


class RelationClassificationTests(unittest.TestCase):
    def test_equal_completed_objective_is_precedence(self):
        relation = mdg.classify_relation(
            json_path=".questDic.a_q#1.objectiveList[0].condition", comparer=0, state=3
        )
        self.assertEqual(relation, mdg.RELATION_REQUIRES_COMPLETED)
        self.assertIn(relation, mdg.PRECEDENCE_RELATIONS)

    def test_equal_processing_is_not_precedence(self):
        relation = mdg.classify_relation(
            json_path=".questDic.a_q#1.objectiveList[0].condition", comparer=0, state=2
        )
        self.assertEqual(relation, mdg.RELATION_REQUIRES_PROCESSING)
        self.assertNotIn(relation, mdg.PRECEDENCE_RELATIONS)

    def test_failed_condition_inverts_meaning(self):
        relation = mdg.classify_relation(
            json_path=".questDic.a_q#1.failedCondition", comparer=0, state=3
        )
        self.assertEqual(relation, mdg.RELATION_ABORTS_ON_COMPLETED)
        self.assertNotIn(relation, mdg.PRECEDENCE_RELATIONS)

    def test_unknown_comparer_is_not_guessed(self):
        # A non-Equal comparer has no pinned meaning in the installed build.
        relation = mdg.classify_relation(
            json_path=".questDic.a_q#1.objectiveList[0].condition", comparer=1, state=3
        )
        self.assertEqual(relation, mdg.RELATION_UNCLASSIFIED)
        self.assertNotIn(relation, mdg.PRECEDENCE_RELATIONS)

    def test_unknown_state_is_not_guessed(self):
        relation = mdg.classify_relation(
            json_path=".questDic.a_q#1.objectiveList[0].condition", comparer=0, state=7
        )
        self.assertEqual(relation, mdg.RELATION_UNCLASSIFIED)


class ExtractionTests(unittest.TestCase):
    def build(self, missions):
        fixture = MissionRootFixture(missions)
        self.addCleanup(fixture.cleanup)
        return mdg.build_report(fixture.root)

    def test_same_mission_reference_is_not_an_edge(self):
        report = self.build(
            {"alpha": {"alpha_q#2": quest([check_quest_state("alpha_q#1")])}}
        )
        self.assertEqual(report["counts"]["sameMissionRows"], 1)
        self.assertEqual(report["counts"]["crossMissionRows"], 0)
        self.assertEqual(report["edges"], [])

    def test_cross_mission_edge_points_from_target_to_declarer(self):
        report = self.build(
            {
                "alpha": {"alpha_q#1": quest()},
                "beta": {"beta_q#1": quest([check_mission_state("alpha")])},
            }
        )
        self.assertEqual(len(report["edges"]), 1)
        edge = report["edges"][0]
        # alpha must complete before beta advances, so the edge runs alpha -> beta.
        self.assertEqual(edge["from"], "alpha")
        self.assertEqual(edge["to"], "beta")
        self.assertTrue(edge["precedence"])
        self.assertEqual(edge["declaringQuestIds"], ["beta_q#1"])

    def test_nested_subconditions_are_reached(self):
        combine = {
            "$type": "Beyond.Gameplay.CombineCondition, Gameplay.Beyond",
            "subConditions": [
                {"$type": "Beyond.Gameplay.CheckSomethingElse, Gameplay.Beyond"},
                check_mission_state("alpha"),
            ],
        }
        report = self.build(
            {"alpha": {"alpha_q#1": quest()}, "beta": {"beta_q#1": quest([combine])}}
        )
        self.assertEqual(len(report["edges"]), 1)
        self.assertIn("subConditions[1]", report["edges"][0]["evidence"][0]["jsonPath"])

    def test_meta_sidecars_are_not_read_as_missions(self):
        report = self.build({"alpha": {"alpha_q#1": quest()}})
        self.assertEqual(report["counts"]["missionsRead"], 1)

    def test_relations_do_not_merge_into_one_edge(self):
        report = self.build(
            {
                "alpha": {"alpha_q#1": quest()},
                "beta": {
                    "beta_q#1": quest([check_mission_state("alpha", state=3)]),
                    "beta_q#2": quest([check_mission_state("alpha", state=2)]),
                },
            }
        )
        relations = sorted(edge["relation"] for edge in report["edges"])
        self.assertEqual(
            relations, [mdg.RELATION_REQUIRES_COMPLETED, mdg.RELATION_REQUIRES_PROCESSING]
        )
        precedence = [edge for edge in report["edges"] if edge["precedence"]]
        self.assertEqual(len(precedence), 1)

    def test_evidence_carries_provenance(self):
        report = self.build(
            {
                "alpha": {"alpha_q#1": quest()},
                "beta": {"beta_q#1": quest([check_mission_state("alpha", unique_id="abc123")])},
            }
        )
        evidence = report["edges"][0]["evidence"][0]
        self.assertEqual(evidence["conditionUniqueId"], "abc123")
        self.assertEqual(evidence["conditionType"], "CheckMissionState")
        self.assertEqual(evidence["comparerName"], "Equal")
        self.assertEqual(evidence["targetStateName"], "Completed")
        self.assertTrue(evidence["sourceFile"].endswith("beta.json"))
        self.assertEqual(
            evidence["jsonPath"], ".questDic.beta_q#1.objectiveList[0].condition"
        )


class GranularityTests(unittest.TestCase):
    def build(self, missions):
        fixture = MissionRootFixture(missions)
        self.addCleanup(fixture.cleanup)
        return mdg.build_report(fixture.root)

    def test_interleaving_is_reported_when_quest_graph_is_acyclic(self):
        # alpha_q#1 -> beta_q#1 -> beta_q#2 -> alpha_q#2: acyclic at quest
        # granularity, cyclic once projected onto missions.
        report = self.build(
            {
                "alpha": {
                    "alpha_q#1": quest(),
                    "alpha_q#2": quest([check_quest_state("beta_q#2")]),
                },
                "beta": {
                    "beta_q#1": quest([check_quest_state("alpha_q#1")]),
                    "beta_q#2": quest(prev=["beta_q#1"]),
                },
            }
        )
        self.assertEqual(report["counts"]["precedenceCycles"], 1)
        self.assertEqual(report["counts"]["missionInterleavings"], 1)
        self.assertEqual(report["counts"]["unexplainedPrecedenceCycles"], 0)
        self.assertEqual(report["counts"]["questGraphCycles"], 0)
        self.assertTrue(report["questGraph"]["acyclic"])
        self.assertEqual(
            sorted(report["missionInterleavings"][0]["missions"]), ["alpha", "beta"]
        )

    def test_genuine_quest_cycle_is_not_explained_away(self):
        report = self.build(
            {
                "alpha": {"alpha_q#1": quest([check_quest_state("beta_q#1")])},
                "beta": {"beta_q#1": quest([check_quest_state("alpha_q#1")])},
            }
        )
        self.assertGreater(report["counts"]["questGraphCycles"], 0)
        self.assertFalse(report["questGraph"]["acyclic"])
        # The interleaving explanation must not be applied here.
        self.assertEqual(report["counts"]["missionInterleavings"], 0)
        self.assertEqual(report["counts"]["unexplainedPrecedenceCycles"], 1)

    def test_quest_graph_includes_intra_mission_chains(self):
        report = self.build(
            {"alpha": {"alpha_q#1": quest(), "alpha_q#2": quest(prev=["alpha_q#1"])}}
        )
        self.assertEqual(report["counts"]["questGraphIntraMissionEdges"], 1)
        self.assertEqual(report["counts"]["questGraphCrossMissionEdges"], 0)

    def test_non_precedence_rows_stay_out_of_the_quest_graph(self):
        # A Processing read is a co-active window and must not create ordering.
        report = self.build(
            {
                "alpha": {"alpha_q#1": quest()},
                "beta": {"beta_q#1": quest([check_quest_state("alpha_q#1", state=2)])},
            }
        )
        self.assertEqual(report["counts"]["questGraphCrossMissionEdges"], 0)


class RenderTests(unittest.TestCase):
    def test_markdown_renders_without_cycles_section(self):
        fixture = MissionRootFixture(
            {
                "alpha": {"alpha_q#1": quest()},
                "beta": {"beta_q#1": quest([check_mission_state("alpha")])},
            }
        )
        self.addCleanup(fixture.cleanup)
        text = mdg.render_markdown(mdg.build_report(fixture.root))
        self.assertIn("# Mission dependency graph", text)
        self.assertIn("`alpha`", text)
        self.assertNotIn("Unexplained precedence cycles", text)


if __name__ == "__main__":
    unittest.main()

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

import build_node_attachment_coverage as nac  # noqa: E402


class Fixture:
    def __init__(self, missions, unlinked=(), pipeline=None):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.flow_root = base / "mission"
        self.flow_root.mkdir(parents=True)
        for mission_id, flow in missions.items():
            (self.flow_root / f"{mission_id}.json").write_text(
                json.dumps({"flow": flow}), encoding="utf-8"
            )
        self.coverage = base / "coverage.json"
        self.coverage.write_text(
            json.dumps({"unlinked": [{"key": k} for k in unlinked]}), encoding="utf-8"
        )
        self.pipeline_root = base / "pipeline"
        self.pipeline_root.mkdir(parents=True)
        for mission_id, payload in (pipeline or {}).items():
            (self.pipeline_root / f"{mission_id}.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )

    def build(self):
        return nac.build_report(self.flow_root, self.coverage, self.pipeline_root)

    def cleanup(self):
        self._tmp.cleanup()


class Base(unittest.TestCase):
    def make(self, missions, unlinked=(), pipeline=None):
        fixture = Fixture(missions, unlinked, pipeline)
        self.addCleanup(fixture.cleanup)
        return fixture.build()


class ClassificationTests(Base):
    def test_quest_attachment_wins_over_shell(self):
        # The same key appears on a quest node and in the mission shell list;
        # it must count as reaching a node, not as shell-only.
        report = self.make({
            "alpha": {
                "quests": [{"id": "alpha_q#1", "storyFiles": [{"key": "dlg_a_1"}]}],
                "missionStoryConnections": [{"key": "dlg_a_1", "relation": "r"}],
            }
        })
        self.assertEqual(report["counts"]["keysOnQuestNodes"], 1)
        self.assertEqual(report["counts"]["keysOnMissionShellOnly"], 0)

    def test_shell_only_key_is_counted(self):
        report = self.make({
            "alpha": {
                "quests": [{"id": "alpha_q#1"}],
                "missionStoryConnections": [{"key": "dlg_a_2", "relation": "r"}],
            }
        })
        self.assertEqual(report["counts"]["keysOnQuestNodes"], 0)
        self.assertEqual(report["counts"]["keysOnMissionShellOnly"], 1)

    def test_quest_attachment_in_another_mission_still_counts(self):
        # A key attached on a quest of mission B must not be reported as
        # shell-only just because mission A lists it at shell level.
        report = self.make({
            "alpha": {
                "quests": [{"id": "alpha_q#1"}],
                "missionStoryConnections": [{"key": "dlg_x", "relation": "r"}],
            },
            "beta": {
                "quests": [{"id": "beta_q#1", "storyConnections": [{"key": "dlg_x"}]}],
            },
        })
        self.assertEqual(report["counts"]["keysOnMissionShellOnly"], 0)
        self.assertEqual(report["counts"]["keysOnQuestNodes"], 1)

    def test_both_quest_story_fields_are_read(self):
        report = self.make({
            "alpha": {
                "quests": [
                    {"id": "alpha_q#1", "storyFiles": [{"key": "a"}]},
                    {"id": "alpha_q#2", "storyConnections": [{"key": "b"}]},
                ]
            }
        })
        self.assertEqual(report["counts"]["keysOnQuestNodes"], 2)
        self.assertEqual(report["counts"]["questNodesWithStoryFiles"], 2)

    def test_unlinked_count_comes_from_coverage_report(self):
        report = self.make({"alpha": {"quests": []}}, unlinked=["dlg_z", "radio_z"])
        self.assertEqual(report["counts"]["keysUnlinked"], 2)


class CandidateQuestTests(Base):
    def shell(self, relation, candidates):
        return {
            "alpha": {
                "quests": [{"id": "alpha_q#1"}],
                "missionStoryConnections": [{
                    "key": "dlg_a_1",
                    "relation": relation,
                    "candidateQuestIds": candidates,
                }],
            }
        }

    def test_single_candidate_is_counted(self):
        report = self.make(self.shell("some_context", ["alpha_q#1"]))
        counts = report["counts"]
        self.assertEqual(counts["missionShellRowsNamingACandidateQuest"], 1)
        self.assertEqual(counts["missionShellRowsNamingExactlyOneQuest"], 1)
        self.assertEqual(counts["singleCandidateRowsNotPolicyBlocked"], 1)

    def test_multi_candidate_is_not_single(self):
        report = self.make(self.shell("some_context", ["alpha_q#1", "alpha_q#2"]))
        counts = report["counts"]
        self.assertEqual(counts["missionShellRowsNamingACandidateQuest"], 1)
        self.assertEqual(counts["missionShellRowsNamingExactlyOneQuest"], 0)

    def test_spatial_relation_is_policy_blocked(self):
        # Spatial proximity never becomes an attachment, however few quests it
        # names. Losing this guard would silently invent placements.
        report = self.make(
            self.shell("pos_tracking_trigger_center_story_context", ["alpha_q#1"])
        )
        counts = report["counts"]
        self.assertEqual(counts["missionShellRowsNamingExactlyOneQuest"], 1)
        self.assertEqual(counts["singleCandidateRowsPolicyBlocked"], 1)
        self.assertEqual(counts["singleCandidateRowsNotPolicyBlocked"], 0)
        self.assertEqual(report["singleCandidateNotBlocked"], {})

    def test_blocked_relation_set_is_explicit(self):
        self.assertIn(
            "pos_tracking_trigger_center_story_context", nac.POLICY_BLOCKED_RELATIONS
        )

    def test_report_states_it_creates_no_attachment(self):
        report = self.make(self.shell("some_context", ["alpha_q#1"]))
        self.assertIn("creates no attachment", report["evidencePolicy"]["noPromotion"])

    def test_candidate_histogram(self):
        report = self.make({
            "alpha": {
                "quests": [{"id": "alpha_q#1"}],
                "missionStoryConnections": [
                    {"key": "a", "relation": "r", "candidateQuestIds": ["q1"]},
                    {"key": "b", "relation": "r", "candidateQuestIds": ["q1", "q2"]},
                    {"key": "c", "relation": "r", "candidateQuestIds": ["q1", "q2"]},
                ],
            }
        })
        self.assertEqual(report["counts"]["candidateCountHistogram"], {1: 1, 2: 2})


def pipeline_mission(mission_id, quests):
    """Pipeline payload whose quest objectives name LevelScript ids."""
    return {
        "mission": {"id": mission_id},
        "nodes": [
            {"id": quest_id, "objectives": [{"levelScriptIds": scripts}]}
            for quest_id, scripts in quests.items()
        ],
    }


class ScriptScopedPlacementTests(Base):
    FLOW = {
        "alpha": {
            "quests": [{"id": "alpha_q#1"}, {"id": "alpha_q#2"}],
            "missionStoryConnections": [{
                "key": "radio_a_1",
                "kind": "radio",
                "relation": "levelscript_mission_context",
                "scriptIds": ["1001"],
            }],
        }
    }

    def test_unique_owning_quest_is_placed(self):
        report = self.make(
            self.FLOW, pipeline={"alpha": pipeline_mission("alpha", {"alpha_q#1": ["1001"]})}
        )
        counts = report["counts"]
        self.assertEqual(counts["scriptScopedQuestPlacementRows"], 1)
        self.assertEqual(counts["scriptScopedQuestPlacementKeys"], 1)
        placement = report["scriptScopedQuestPlacements"][0]
        self.assertEqual(placement["questId"], "alpha_q#1")
        self.assertEqual(placement["storyKey"], "radio_a_1")
        self.assertEqual(placement["sourceRelation"], "levelscript_mission_context")

    def test_script_named_by_two_quests_is_rejected(self):
        report = self.make(
            self.FLOW,
            pipeline={
                "alpha": pipeline_mission(
                    "alpha", {"alpha_q#1": ["1001"], "alpha_q#2": ["1001"]}
                )
            },
        )
        counts = report["counts"]
        self.assertEqual(counts["scriptScopedQuestPlacementRows"], 0)
        self.assertEqual(counts["scriptScopedQuestPlacementAmbiguous"], 1)

    def test_owning_quest_in_another_mission_is_rejected(self):
        # A script owned by a quest of a different mission must never place the
        # row onto that foreign quest.
        report = self.make(
            self.FLOW,
            pipeline={"beta": pipeline_mission("beta", {"beta_q#1": ["1001"]})},
        )
        counts = report["counts"]
        self.assertEqual(counts["scriptScopedQuestPlacementRows"], 0)
        self.assertEqual(counts["scriptScopedQuestPlacementAmbiguous"], 1)

    def test_row_without_script_ids_is_ignored(self):
        flow = {
            "alpha": {
                "quests": [{"id": "alpha_q#1"}],
                "missionStoryConnections": [{"key": "radio_a_1", "relation": "r"}],
            }
        }
        report = self.make(
            flow, pipeline={"alpha": pipeline_mission("alpha", {"alpha_q#1": ["1001"]})}
        )
        self.assertEqual(report["counts"]["scriptScopedQuestPlacementRows"], 0)
        self.assertEqual(report["counts"]["scriptScopedQuestPlacementAmbiguous"], 0)

    def test_row_already_on_a_quest_is_not_reprocessed(self):
        flow = {
            "alpha": {
                "quests": [
                    {"id": "alpha_q#1", "storyFiles": [{"key": "radio_a_1"}]},
                    {"id": "alpha_q#2"},
                ],
                "missionStoryConnections": [{
                    "key": "radio_a_1", "relation": "r", "scriptIds": ["1001"],
                }],
            }
        }
        report = self.make(
            flow, pipeline={"alpha": pipeline_mission("alpha", {"alpha_q#2": ["1001"]})}
        )
        self.assertEqual(report["counts"]["scriptScopedQuestPlacementRows"], 0)

    def test_placement_claim_is_bounded_to_scope_not_playback(self):
        note = self.make(self.FLOW)["evidencePolicy"]["scriptScopedQuestPlacement"]
        self.assertIn("does not prove the quest plays", note)

    def test_missing_pipeline_root_degrades_cleanly(self):
        fixture = Fixture(self.FLOW)
        self.addCleanup(fixture.cleanup)
        report = nac.build_report(fixture.flow_root, fixture.coverage, None)
        self.assertEqual(report["counts"]["scriptScopedQuestPlacementRows"], 0)
        self.assertEqual(report["counts"]["questObjectiveScriptIds"], 0)


class RenderTests(Base):
    def test_markdown_renders(self):
        report = self.make({
            "alpha": {
                "quests": [{"id": "alpha_q#1", "storyFiles": [{"key": "dlg_a_1"}]}],
                "missionStoryConnections": [{"key": "dlg_a_2", "relation": "ctx"}],
            }
        })
        text = nac.render_markdown(report)
        self.assertIn("# Node attachment coverage", text)
        self.assertIn("`ctx`", text)


if __name__ == "__main__":
    unittest.main()

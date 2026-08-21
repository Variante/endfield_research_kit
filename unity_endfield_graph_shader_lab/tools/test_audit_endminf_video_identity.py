"""Focused tests for the exact Endminf video identity/phase evidence."""

from __future__ import annotations

import unittest

import audit_endminf_video_identity as evidence


class EndminfVideoIdentityTests(unittest.TestCase):
    def test_exact_asset_is_only_a_candidate_without_comparable_competitors(self) -> None:
        report = evidence.build_report()
        self.assertEqual(report["identity"]["status"], "candidate")
        self.assertEqual(report["identity"]["characterId"], "chr_0003_endminf")
        self.assertEqual(report["identity"]["visibleVideo"]["visibleAlias"], "endmin")
        self.assertEqual(report["identity"]["visibleVideo"]["visibleTemplateAlias"], "chr_9000_endmin")
        self.assertTrue(report["videoSearch"]["searchedAllReferenceSegments"])
        self.assertTrue(report["videoSearch"]["identityAliasRejected"])
        self.assertGreaterEqual(report["identity"]["visualMatch"]["eccTranslation"], 0.80)
        matrix = report["identity"]["candidateMatrix"]
        self.assertEqual(matrix["comparableCompetitorCount"], 0)
        self.assertFalse(matrix["marginSatisfied"])
        self.assertFalse(report["publication"]["matteCandidateAllowed"])
        endminm = next(row for row in matrix["candidates"] if row["candidateId"] == "chr_0002_endminm")
        self.assertFalse(endminm["render"]["available"])
        self.assertIn("no same-camera/same-render-settings", endminm["rejection"])

    def test_phase_frames_are_contiguous_and_transition_is_not_loop(self) -> None:
        phase = evidence.build_report()["phase"]
        self.assertEqual(phase["start"]["frameRangeInclusive"], [9767, 10028])
        self.assertEqual(phase["transition"]["frameRangeInclusive"], [10029, 10116])
        self.assertEqual(phase["loop"]["frameRangeInclusive"], [10117, 10409])
        self.assertEqual(phase["loop"]["completeRuntimePeriods"], 2)
        self.assertEqual(phase["cleanLoop"]["frameRangeExclusive"], [10117, 10410])
        self.assertEqual(phase["cleanLoop"]["frameCount"], 293)
        self.assertAlmostEqual(phase["cleanLoop"]["durationSeconds"], 293 / 60.0, places=9)
        self.assertEqual(phase["combinedActorWindow"]["frameRangeExclusive"], [9767, 10500])
        self.assertEqual(phase["combinedActorWindow"]["frameCount"], 733)
        self.assertEqual(phase["sourceTransition"]["frameRangesInclusive"], [[9767, 9782], [10410, 10499]])
        tail = phase["tailTransition"]
        self.assertEqual(tail["frameRangeInclusive"], [10410, 10499])
        self.assertEqual(tail["frameCount"], 90)
        self.assertEqual(len(tail["perFrame"]), 90)
        self.assertEqual(tail["classification"], "evidence_bounded_target_window_exit_non_target_transition")
        self.assertEqual(tail["followingActorIdentity"], "not_proven")
        self.assertTrue(all(row["classification"] == "evidence_bounded_target_window_exit_non_target_transition" for row in tail["perFrame"]))

    def test_generic_alias_is_not_exact_identity(self) -> None:
        _boundaries, row, _next = evidence._load_video_evidence()
        self.assertEqual(row["actor"], "endmin")
        self.assertEqual(row["templateId"], "chr_9000_endmin")
        self.assertNotEqual(row["templateId"], "chr_0003_endminf")


if __name__ == "__main__":
    unittest.main()

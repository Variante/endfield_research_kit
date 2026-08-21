"""Focused tests for the exact Endminf video identity/phase evidence."""

from __future__ import annotations

import unittest

import audit_endminf_video_identity as evidence


class EndminfVideoIdentityTests(unittest.TestCase):
    def test_exact_identity_and_composite_phase_are_admitted(self) -> None:
        report = evidence.build_report()
        self.assertEqual(report["identity"]["status"], "proven")
        self.assertEqual(report["identity"]["characterId"], "chr_0003_endminf")
        self.assertEqual(report["identity"]["visibleVideo"]["visibleAlias"], "endmin")
        self.assertEqual(report["identity"]["visibleVideo"]["visibleTemplateAlias"], "chr_9000_endmin")
        self.assertTrue(report["videoSearch"]["searchedAllReferenceSegments"])
        self.assertTrue(report["videoSearch"]["identityAliasRejected"])
        self.assertGreaterEqual(report["identity"]["visualMatch"]["eccTranslation"], 0.80)

    def test_phase_frames_are_contiguous_and_transition_is_not_loop(self) -> None:
        phase = evidence.build_report()["phase"]
        self.assertEqual(phase["start"]["frameRangeInclusive"], [9767, 10028])
        self.assertEqual(phase["transition"]["frameRangeInclusive"], [10029, 10116])
        self.assertEqual(phase["loop"]["frameRangeInclusive"], [10117, 10499])
        self.assertEqual(phase["combinedActorWindow"]["frameRangeExclusive"], [9767, 10500])
        self.assertEqual(phase["combinedActorWindow"]["frameCount"], 733)
        self.assertEqual(phase["sourceTransition"]["frameRangesInclusive"], [[9767, 9782], [10410, 10499]])

    def test_generic_alias_is_not_exact_identity(self) -> None:
        _boundaries, row, _next = evidence._load_video_evidence()
        self.assertEqual(row["actor"], "endmin")
        self.assertEqual(row["templateId"], "chr_9000_endmin")
        self.assertNotEqual(row["templateId"], "chr_0003_endminf")


if __name__ == "__main__":
    unittest.main()

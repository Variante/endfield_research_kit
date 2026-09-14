from __future__ import annotations

import unittest

from scripts.audio_semantics.hirc_named_reach import (
    check_identification,
    fnv1_utf16,
    index_literals,
    markdown,
    named_type_share,
    summarise,
)


def census(**overrides):
    row = {
        "matchedObjects": 2,
        "matchedNamedType": 2,
        "reachingASource": 1,
        "reachingNoSource": 1,
        "reachedSourceIds": 3,
        "walkEdgesLeavingTheBank": 4,
        "matchesByObjectType": {"type04": 2},
        "reachedSourceIdsByIdentity": {"0000000A": 3, "0000000B": 0},
    }
    row.update(overrides)
    return row


class HircNamedReachTests(unittest.TestCase):
    def test_hash_matches_the_shipped_generator(self) -> None:
        # FNV-1 over UTF-16 code units, not bytes and not FNV-1a.
        self.assertEqual(fnv1_utf16(""), 0x811C9DC5)
        self.assertNotEqual(fnv1_utf16("au_a"), fnv1_utf16("au_b"))
        index = index_literals(["au_one", "au_two"])
        self.assertEqual(sum(len(names) for names in index.values()), 2)

    def test_summary_partitions_and_bounds_its_counters(self) -> None:
        summary = summarise([census(), census()])
        self.assertEqual(summary["namedObjectInstances"], 4)
        self.assertEqual(summary["namedObjectsReachingASource"], 2)
        self.assertEqual(summary["namedObjectsReachingNoSource"], 2)
        self.assertEqual(summary["reachedSourceIdTotal"], 6)
        self.assertEqual(summary["walkEdgesLeavingTheBank"], 8)
        # Per-identity reach is a maximum across banks, never a sum.
        self.assertEqual(summary["reachedSourceIdsByIdentity"], {"0000000A": 3, "0000000B": 0})
        self.assertEqual(check_identification(summary), [])

    def test_a_match_outside_the_named_type_dissolves_the_identification(self) -> None:
        # The whole identification rests on every literal hash landing on one type.
        # A single stray match must stop publication, not lower a percentage.
        summary = summarise([census(matchesByObjectType={"type04": 1, "type02": 1})])
        problems = check_identification(summary)
        self.assertTrue(any("dissolves the identification" in problem for problem in problems))

    def test_missing_and_inconsistent_censuses_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid matchedObjects"):
            summarise([census(matchedObjects="x")])
        with self.assertRaisesRegex(ValueError, "negative reachingASource"):
            summarise([census(reachingASource=-1)])
        with self.assertRaisesRegex(ValueError, "match key is not a numeric type"):
            summarise([census(matchesByObjectType={"event": 1})])
        with self.assertRaisesRegex(ValueError, "identity is not a 32-bit hex id"):
            summarise([census(reachedSourceIdsByIdentity={"au_thing": 1})])
        with self.assertRaisesRegex(ValueError, "invalid matchesByObjectType"):
            summarise([census(matchesByObjectType=[])])

        summary = summarise([census(reachingASource=2)])
        self.assertTrue(
            any("do not partition" in problem for problem in check_identification(summary))
        )
        summary = summarise([census(matchedObjects=5)])
        self.assertTrue(
            any("disagree with the per-type" in problem for problem in check_identification(summary))
        )

    def test_identities_may_not_outnumber_the_instances_that_produced_them(self) -> None:
        summary = summarise([census(matchedObjects=1, matchedNamedType=1, reachingNoSource=0)])
        self.assertTrue(
            any("more named identities" in problem for problem in check_identification(summary))
        )
        summary = summarise([census(reachedSourceIdsByIdentity={})])
        self.assertTrue(
            any("no identity was recorded" in problem for problem in check_identification(summary))
        )

    def test_named_type_share_is_measured_not_asserted(self) -> None:
        share = named_type_share([{"0x02": 90}, {"0x04": 10}])
        self.assertEqual(share["hircObjects"], 100)
        self.assertEqual(share["namedTypeObjects"], 10)
        self.assertEqual(share["namedTypeSharePercent"], 10.0)
        with self.assertRaisesRegex(ValueError, "does not occur"):
            named_type_share([{"0x02": 90}])
        with self.assertRaisesRegex(ValueError, "histogram is empty"):
            named_type_share([{"0x04": 0}])
        with self.assertRaisesRegex(ValueError, "key is not numeric"):
            named_type_share([{"event": 1}])

    def test_markdown_states_the_identification_and_refuses_to_go_further(self) -> None:
        summary = summarise([census()])
        summary.update(named_type_share([{"0x02": 90}, {"0x04": 10}]))
        report = {
            "status": "complete",
            "inputSetSha256": "A" * 64,
            "metadata": {"path": "meta.dat", "sha256": "B" * 64, "audioLiteralCount": 221},
            "summary": summary,
            "identifiers": {"au_example": 3},
        }
        text = markdown(report)
        self.assertIn("This table is the identification", text)
        self.assertIn("would dissolve the identification", text)
        # The share and the stray-match expectation must come from the histogram.
        self.assertIn("10.00 percent", text)
        self.assertIn("about 2 of the 2 matches", text)
        self.assertIn("does not establish that posting the identifier", text)
        self.assertIn("Edges that leave the bank are counted above and not followed", text)
        self.assertIn("au_example", text)


if __name__ == "__main__":
    unittest.main()

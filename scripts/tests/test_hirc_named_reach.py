from __future__ import annotations

import unittest

from scripts.audio_semantics.hirc_named_reach import (
    media_attribution,
    media_attribution_is_discriminated,
    source_values_from_audit,
    broad_naming_is_discriminated,
    coincidence_table,
    media_ids_from_audit,
    check_identification,
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
        "walkEdgesLeavingThePackage": 4,
        "matchesByObjectType": {"type04": 2},
        "reachedSourceIdsByIdentity": {"0000000A": 3, "0000000B": 0},
        "reachedSourceIdListByIdentity": {"0000000A": [10, 11, 12], "0000000B": []},
    }
    row.update(overrides)
    return row


class HircNamedReachTests(unittest.TestCase):
    def test_hash_is_the_shipped_generator_and_folds_capitals(self) -> None:
        from scripts.audio_semantics.identifiers import audio_hash_generator_compute

        # This module must not carry its own hash: the shipped generator folds
        # ASCII A-Z, and an unfolded copy silently loses every name with a capital.
        self.assertEqual(
            audio_hash_generator_compute("Au_UI_Button_Close"),
            audio_hash_generator_compute("au_ui_button_close"),
        )
        index = index_literals(["Au_One", "au_one", "au_two"])
        # The two casings are one identity, so the index must fold them together.
        self.assertEqual(len(index), 2)
        self.assertEqual(index[audio_hash_generator_compute("au_one")], {"Au_One", "au_one"})

    def test_summary_partitions_and_bounds_its_counters(self) -> None:
        summary = summarise([census(), census()])
        self.assertEqual(summary["namedObjectInstances"], 4)
        self.assertEqual(summary["namedObjectsReachingASource"], 2)
        self.assertEqual(summary["namedObjectsReachingNoSource"], 2)
        self.assertEqual(summary["reachedSourceIdTotal"], 6)
        self.assertEqual(summary["walkEdgesLeavingThePackage"], 8)
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
            "broadNaming": {
                **coincidence_table(
                    {"type04": 200, "type02": 2}, {"type04": 22910, "type02": 142815}, 24868
                ),
                "populationsWithNoMatch": ["mediaId", "type07"],
            },
            "mediaSummary": {
                "declaredMediaIds": 5,
                "identifiersReachingMedia": 1,
                "distinctMediaReached": 2,
                "reachedIdsNamingNoMedia": 1,
            },
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
        # The chain must be stated end to end, and the ids that name no media must
        # be reported rather than quietly dropped.
        self.assertIn("chain is now complete end to end", text)
        self.assertIn("name no shipped media", text)
        # The coincidence test must be visible in the report, including the type it
        # rejects -- publishing only the accepted types would hide the discrimination.
        self.assertIn("judged against chance", text)
        self.assertIn("Expected by chance", text)
        self.assertIn("Indistinguishable from chance", text)
        # A population that matches nothing is a result too, so it must be named
        # in the report rather than silently absent from the table.
        self.assertIn("never name at all", text)
        self.assertIn("mediaId", text)

    def test_reached_lists_and_counts_must_describe_the_same_walk(self) -> None:
        summary = summarise([census()])
        self.assertEqual(
            summary["reachedSourceIdListByIdentity"], {"0000000A": [10, 11, 12], "0000000B": []}
        )
        self.assertEqual(check_identification(summary), [])

        # A count with no list, or a list shorter than its count, is a reader bug
        # rather than a weaker result, so it must stop publication.
        missing = summarise([census(reachedSourceIdListByIdentity={"0000000A": [10, 11, 12]})])
        self.assertTrue(
            any("cover different identities" in p for p in check_identification(missing))
        )
        short = summarise([census(reachedSourceIdListByIdentity={"0000000A": [10], "0000000B": []})])
        self.assertTrue(
            any("lists fewer source ids" in p for p in check_identification(short))
        )

    def test_media_ids_come_from_every_verified_package(self) -> None:
        audit = {
            "rows": [
                {"status": "verified", "package": {"hircMediaJoin": {"mediaIds": [1, 2]}}},
                {"status": "verified", "package": {"hircMediaJoin": {"mediaIds": [2, 3]}}},
                {"status": "failed", "package": {"hircMediaJoin": {"mediaIds": [99]}}},
            ]
        }
        # A union, because a bank's media usually lives in another package; and an
        # unverified package contributes nothing.
        self.assertEqual(media_ids_from_audit(audit), {1, 2, 3})
        with self.assertRaisesRegex(ValueError, "invalid mediaIds"):
            media_ids_from_audit(
                {"rows": [{"status": "verified", "package": {"hircMediaJoin": {"mediaIds": 7}}}]}
            )

    def test_coincidence_table_separates_names_from_chance(self) -> None:
        # A 32-bit hash makes chance computable: literals * population / 2**32.
        table = coincidence_table(
            {"type15": 4, "type08": 3, "type02": 2},
            {"type15": 5, "type08": 161, "type02": 142815, "type07": 48740},
            24868,
        )
        self.assertEqual(sorted(table["typesNamedAboveChance"]), ["type08", "type15"])
        self.assertEqual(table["typesIndistinguishableFromChance"], ["type02"])
        # A type with no matches is absent rather than reported as a zero claim.
        self.assertNotIn("type07", table["byType"])
        # Type 0x02's two matches sit at its own coincidence rate despite looking
        # like names, which is the case the whole test exists for.
        self.assertLess(table["byType"]["type02"]["ratio"], 10)
        self.assertGreater(table["byType"]["type15"]["ratio"], 1000)
        self.assertTrue(broad_naming_is_discriminated(table))

    def test_broad_naming_requires_the_rule_to_be_applied_to_every_type(self) -> None:
        table = coincidence_table({"type15": 4, "type02": 2}, {"type15": 5, "type02": 142815}, 24868)
        # Claiming a type the rule rejects, or omitting one it accepts, must fail:
        # otherwise the bar could be quietly applied only where convenient.
        self.assertFalse(
            broad_naming_is_discriminated({**table, "typesNamedAboveChance": ["type15", "type02"]})
        )
        self.assertFalse(
            broad_naming_is_discriminated({**table, "typesNamedAboveChance": []})
        )
        # Nothing clearing the bar means the section claims nothing.
        empty = coincidence_table({"type02": 2}, {"type02": 142815}, 24868)
        self.assertFalse(broad_naming_is_discriminated(empty))


if __name__ == "__main__":
    unittest.main()


class MediaAttributionTests(unittest.TestCase):
    """Two numeric types share one 14-byte source record, and it names the media."""

    MEASURED = {
        "mediaIdsDeclared": 61333,
        "mediaIdsNamedBySomeRecord": 61325,
        "mediaIdsNamedByNoRecord": 8,
        "mediaIdsNamedByType": {"type02": 60049, "type0B": 1279},
        "controlMediaIdsNamedByNeighbouringWords": {
            "idValuesAfterByType": 2, "idValuesBeforeByType": 0},
    }

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(media_attribution_is_discriminated(self.MEASURED))

    def test_a_neighbouring_word_that_resolves_as_well_fails(self) -> None:
        # Without this the census would say only that 32-bit values in this region
        # often look like media ids, which is a fact about the id space rather than
        # about the field.
        self.assertFalse(media_attribution_is_discriminated(
            dict(self.MEASURED, controlMediaIdsNamedByNeighbouringWords={
                "idValuesAfterByType": 40000, "idValuesBeforeByType": 0})
        ))

    def test_a_single_contributing_type_fails(self) -> None:
        # One type cannot show that the record is shared, which is the whole content
        # of this census. This is the state the reader was in before numeric type
        # 0x0B was allowed to contribute source ids.
        self.assertFalse(media_attribution_is_discriminated(
            dict(self.MEASURED, mediaIdsNamedBySomeRecord=60049,
                 mediaIdsNamedByType={"type02": 60049})
        ))

    def test_coverage_below_ninety_nine_percent_fails(self) -> None:
        self.assertFalse(media_attribution_is_discriminated(
            dict(self.MEASURED, mediaIdsNamedBySomeRecord=60000)
        ))

    def test_a_type_contributing_nothing_fails(self) -> None:
        self.assertFalse(media_attribution_is_discriminated(
            dict(self.MEASURED, mediaIdsNamedByType={"type02": 60049, "type0B": 0})
        ))

    def test_an_empty_attribution_fails_rather_than_passing_vacuously(self) -> None:
        self.assertFalse(media_attribution_is_discriminated({}))
        self.assertFalse(media_attribution_is_discriminated(
            {"mediaIdsDeclared": 0, "mediaIdsNamedBySomeRecord": 0}
        ))
        self.assertFalse(media_attribution_is_discriminated(None))

    def test_the_join_is_pooled_across_packages(self) -> None:
        # The trap this census fell into first. A source record names media that a
        # DIFFERENT package declares, so a package-local join scored 12 of 147,262.
        # Here package A's records name package B's media and nothing else.
        audit = {"rows": [
            {"status": "verified", "package": {"hircMediaJoin": {
                "hircSourceRecords": {
                    "idValuesByType": {"type02": [10, 11], "type0B": [20]},
                    "idValuesBeforeByType": {"type02": [900]},
                    "idValuesAfterByType": {"type02": [901]},
                }}}},
            {"status": "verified", "package": {"hircMediaJoin": {
                "hircSourceRecords": {
                    "idValuesByType": {"type02": [12]},
                    "idValuesBeforeByType": {"type02": [902]},
                    "idValuesAfterByType": {"type02": [903]},
                }}}},
        ]}
        values = source_values_from_audit(audit)
        self.assertEqual(values["type02"]["idValuesByType"], {10, 11, 12})
        self.assertEqual(values["type0B"]["idValuesByType"], {20})
        out = media_attribution({10, 11, 12, 20}, values)
        self.assertEqual(out["mediaIdsNamedBySomeRecord"], 4)
        self.assertEqual(out["mediaIdsNamedByNoRecord"], 0)
        self.assertEqual(out["mediaIdsNamedByType"], {"type02": 3, "type0B": 1})

    def test_an_unverified_package_contributes_nothing(self) -> None:
        audit = {"rows": [
            {"status": "failed", "package": {"hircMediaJoin": {
                "hircSourceRecords": {"idValuesByType": {"type02": [10]}}}}},
        ]}
        self.assertEqual(source_values_from_audit(audit), {})

    def test_a_malformed_census_fails_closed(self) -> None:
        for bad in ({"idValuesByType": "ten"}, {"idValuesByType": {"type02": 10}}):
            with self.assertRaises(ValueError):
                source_values_from_audit({"rows": [
                    {"status": "verified",
                     "package": {"hircMediaJoin": {"hircSourceRecords": bad}}},
                ]})

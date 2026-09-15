from __future__ import annotations

import unittest

from scripts.audio_semantics.hirc_named_reach import (
    media_attribution,
    stmg_from_audit,
    the_stmg_record_stride_beats_its_rivals,
    the_stmg_tail_run_is_located_by_its_count,
    the_stmg_section_closes_byte_exactly,
    init_from_audit,
    the_init_table_names_the_plugins_the_records_use,
    the_unparsed_sections_name_only_buses,
    music_reach_from_audit,
    the_music_family_is_not_entered_from_the_object_graph,
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


class MusicIsolationTests(unittest.TestCase):
    """A negative result stated as a gate, so its expiry fires rather than passes."""

    MEASURED = {
        "musicObjects": 11656, "entryEdges": 5, "banksWithAnEntry": 5,
        "reachedObjects": 5, "reachedSourceIdCount": 0, "edges": 7305,
        "edgeSources": 4607, "rootsWithNoIncomingEdge": 4351,
        "entriesWithOutgoingEdges": 0, "entriesThatAreRoots": 5,
    }

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(
            the_music_family_is_not_entered_from_the_object_graph(self.MEASURED)
        )

    def test_finding_a_real_entry_point_fails_the_gate(self) -> None:
        # The good-news case, and the reason this is written as a gate at all. If a
        # later reading reaches even one source id through the music family, the
        # isolation claim has expired and must be rewritten rather than relaxed.
        self.assertFalse(the_music_family_is_not_entered_from_the_object_graph(
            dict(self.MEASURED, reachedSourceIdCount=1)
        ))

    def test_a_walk_with_no_edges_fails_rather_than_passing(self) -> None:
        # Without this the gate would pass most loudly when the walk was broken:
        # an empty edge set reaches nothing, which looks exactly like isolation.
        self.assertFalse(the_music_family_is_not_entered_from_the_object_graph(
            dict(self.MEASURED, edges=0, edgeSources=0)
        ))
        self.assertFalse(the_music_family_is_not_entered_from_the_object_graph(
            dict(self.MEASURED, musicObjects=0)
        ))

    def test_entry_edges_on_the_scale_of_the_family_fail(self) -> None:
        self.assertFalse(the_music_family_is_not_entered_from_the_object_graph(
            dict(self.MEASURED, entryEdges=200)
        ))

    def test_an_empty_census_fails_rather_than_passing_vacuously(self) -> None:
        self.assertFalse(the_music_family_is_not_entered_from_the_object_graph({}))
        self.assertFalse(the_music_family_is_not_entered_from_the_object_graph(None))

    def test_the_census_sums_only_verified_packages(self) -> None:
        base = {k: 0 for k in (
            "musicObjects", "entryEdges", "banksWithAnEntry", "reachedObjects",
            "reachedSourceIdCount", "edges", "edgeSources",
            "rootsWithNoIncomingEdge", "entriesWithOutgoingEdges",
            "entriesThatAreRoots")}
        audit = {"rows": [
            {"status": "verified", "package": {"hircType03Targets": {
                "hircMusicReach": dict(base, musicObjects=10, edges=4,
                                       entryKinds={"action_03_to_type0C": 2})}}},
            {"status": "verified", "package": {"hircType03Targets": {
                "hircMusicReach": dict(base, musicObjects=5, edges=1)}}},
            {"status": "failed", "package": {"hircType03Targets": {
                "hircMusicReach": dict(base, musicObjects=999)}}},
        ]}
        out = music_reach_from_audit(audit)
        self.assertEqual(out["musicObjects"], 15)
        self.assertEqual(out["edges"], 5)
        self.assertEqual(out["entryKinds"], {"action_03_to_type0C": 2})

    def test_a_malformed_census_fails_closed(self) -> None:
        for bad in ({"musicObjects": "ten"}, {"musicObjects": -1}, "census"):
            with self.assertRaises(ValueError):
                music_reach_from_audit({"rows": [
                    {"status": "verified",
                     "package": {"hircType03Targets": {"hircMusicReach": bad}}},
                ]})


class StmgFrameTests(unittest.TestCase):
    """One instance in the whole corpus, so the stride carries the evidence."""

    MEASURED = {
        "sections": 1, "sectionBytes": 10118, "sectionsTooShort": 0,
        "countOutOfRange": 0, "runPastTheEnd": 0, "sectionsFramed": 1,
        "declaredRecords": 309, "distinctRecordIds": 309,
        "rivalStridesTested": 12, "rivalStridesWithDistinctIds": 0,
        "runsFollowedByAPlausibleCount": 1, "bytesFramed": 3722,
        "bytesUnframed": 6396,
    }

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(the_stmg_record_stride_beats_its_rivals(self.MEASURED))

    def test_a_rival_stride_that_also_gives_distinct_ids_fails(self) -> None:
        # The whole discrimination. With one instance there is no closure to appeal
        # to, so if another width read the ids as cleanly this says nothing.
        self.assertFalse(the_stmg_record_stride_beats_its_rivals(
            dict(self.MEASURED, rivalStridesWithDistinctIds=1)
        ))

    def test_no_rival_scored_at_all_fails(self) -> None:
        self.assertFalse(the_stmg_record_stride_beats_its_rivals(
            dict(self.MEASURED, rivalStridesTested=0)
        ))

    def test_colliding_record_ids_fail(self) -> None:
        self.assertFalse(the_stmg_record_stride_beats_its_rivals(
            dict(self.MEASURED, distinctRecordIds=308)
        ))

    def test_a_run_followed_by_nothing_plausible_fails(self) -> None:
        self.assertFalse(the_stmg_record_stride_beats_its_rivals(
            dict(self.MEASURED, runsFollowedByAPlausibleCount=0)
        ))

    def test_a_section_that_is_neither_framed_nor_fenced_fails(self) -> None:
        # Fail-closed: every section must be accounted for on one side or the other.
        self.assertFalse(the_stmg_record_stride_beats_its_rivals(
            dict(self.MEASURED, sections=2)
        ))

    def test_an_empty_census_fails_rather_than_passing_vacuously(self) -> None:
        self.assertFalse(the_stmg_record_stride_beats_its_rivals({}))
        self.assertFalse(the_stmg_record_stride_beats_its_rivals(None))

    def test_a_malformed_census_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            stmg_from_audit({"rows": [
                {"status": "verified", "package": {"stmg": {"sections": "one"}}},
            ]})


class UnparsedSectionWordTests(unittest.TestCase):
    """Nothing outside HIRC references a music object either."""

    MEASURED = {
        "sections": 4, "sectionBytes": 10689, "hircObjects": 238807,
        "wordsTested": 10677, "wordsNamingAnObject": 63,
        "typesNamed": {"STMG_type08": 1, "STMG_type12": 62},
    }

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(the_unparsed_sections_name_only_buses(self.MEASURED))

    def test_a_music_type_appearing_fails_the_gate(self) -> None:
        # The good-news case. A music type here would be the entry point the object
        # graph does not have, and the claim that none exists would have expired.
        self.assertFalse(the_unparsed_sections_name_only_buses(
            dict(self.MEASURED, wordsNamingAnObject=64,
                 typesNamed={"STMG_type08": 1, "STMG_type12": 62,
                             "STMG_type0C": 1})
        ))

    def test_a_hit_rate_at_chance_fails(self) -> None:
        # 10,677 words against 238,807 objects over a 32-bit space is 0.59 expected
        # matches. One hit is not a reference, it is a coincidence.
        self.assertFalse(the_unparsed_sections_name_only_buses(
            dict(self.MEASURED, wordsNamingAnObject=1,
                 typesNamed={"STMG_type12": 1})
        ))

    def test_a_histogram_that_does_not_cover_the_hits_fails(self) -> None:
        self.assertFalse(the_unparsed_sections_name_only_buses(
            dict(self.MEASURED, typesNamed={"STMG_type12": 62})
        ))

    def test_no_references_at_all_fails_rather_than_passing_vacuously(self) -> None:
        self.assertFalse(the_unparsed_sections_name_only_buses(
            dict(self.MEASURED, wordsNamingAnObject=0, typesNamed={})
        ))
        self.assertFalse(the_unparsed_sections_name_only_buses({}))
        self.assertFalse(the_unparsed_sections_name_only_buses(None))


class StmgTailTests(unittest.TestCase):
    """The trailing run is bounded by its shape and located by its count."""

    MEASURED = {
        "sectionsFramed": 1, "tailRunsFramed": 1, "tailRecords": 269,
        "tailDistinctIds": 269, "tailFloatsTested": 807, "tailFloatsBounded": 807,
        "tailRivalStridesTested": 7, "tailRivalStridesWithDistinctIds": 0,
        "tailRivalStridesWithTheZeroRun": 0, "tailTrailingBytesNotZero": 0,
        "tailRunNotFound": 0, "tailCountDoesNotMatchTheRun": 0,
    }

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(the_stmg_tail_run_is_located_by_its_count(self.MEASURED))

    def test_a_rival_stride_matching_either_check_fails(self) -> None:
        self.assertFalse(the_stmg_tail_run_is_located_by_its_count(
            dict(self.MEASURED, tailRivalStridesWithDistinctIds=1)))
        self.assertFalse(the_stmg_tail_run_is_located_by_its_count(
            dict(self.MEASURED, tailRivalStridesWithTheZeroRun=1)))

    def test_colliding_ids_fail(self) -> None:
        self.assertFalse(the_stmg_tail_run_is_located_by_its_count(
            dict(self.MEASURED, tailDistinctIds=268)))

    def test_an_unbounded_float_fails(self) -> None:
        self.assertFalse(the_stmg_tail_run_is_located_by_its_count(
            dict(self.MEASURED, tailFloatsBounded=806)))

    def test_an_ambiguous_boundary_is_fenced_not_resolved(self) -> None:
        # If several lengths had a preceding word equal to themselves the run would
        # not be located, and the reader fences rather than preferring one.
        self.assertFalse(the_stmg_tail_run_is_located_by_its_count(
            dict(self.MEASURED, tailRunsFramed=0, tailRecords=0,
                 tailCountDoesNotMatchTheRun=1)))

    def test_a_section_neither_framed_nor_fenced_fails(self) -> None:
        self.assertFalse(the_stmg_tail_run_is_located_by_its_count(
            dict(self.MEASURED, sectionsFramed=2)))

    def test_no_rival_scored_fails(self) -> None:
        self.assertFalse(the_stmg_tail_run_is_located_by_its_count(
            dict(self.MEASURED, tailRivalStridesTested=0)))

    def test_an_empty_census_fails_rather_than_passing_vacuously(self) -> None:
        self.assertFalse(the_stmg_tail_run_is_located_by_its_count({}))
        self.assertFalse(the_stmg_tail_run_is_located_by_its_count(None))


class StmgClosureTests(unittest.TestCase):
    """STMG appears once, so closure is the only check a partial frame cannot fake."""

    MEASURED = {
        "sections": 1, "sectionBytes": 10118, "bytesFramed": 10118,
        "bytesUnframed": 0, "entryBlocks": 1, "entryBlocksFramed": 1,
        "entries": 15, "distinctEntryIds": 15, "entryRecords": 45,
        "entryRecordsCarryingTheMarker": 45,
    }

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(the_stmg_section_closes_byte_exactly(self.MEASURED))

    def test_a_single_unframed_byte_fails(self) -> None:
        self.assertFalse(the_stmg_section_closes_byte_exactly(
            dict(self.MEASURED, bytesFramed=10117, bytesUnframed=1)))

    def test_a_block_that_does_not_close_fails(self) -> None:
        self.assertFalse(the_stmg_section_closes_byte_exactly(
            dict(self.MEASURED, entryBlocksFramed=0, entries=0,
                 distinctEntryIds=0, entryRecords=0,
                 entryRecordsCarryingTheMarker=0)))

    def test_a_record_missing_the_marker_fails(self) -> None:
        # The content check the shape search did not select for. Exhaustion found the
        # shape; the marker is what says the shape is the right one.
        self.assertFalse(the_stmg_section_closes_byte_exactly(
            dict(self.MEASURED, entryRecordsCarryingTheMarker=44)))

    def test_colliding_entry_ids_fail(self) -> None:
        self.assertFalse(the_stmg_section_closes_byte_exactly(
            dict(self.MEASURED, distinctEntryIds=14)))

    def test_an_empty_section_fails_rather_than_passing_vacuously(self) -> None:
        # Zero bytes framed of zero declared is not closure, it is absence.
        self.assertFalse(the_stmg_section_closes_byte_exactly(
            dict(self.MEASURED, sections=0, sectionBytes=0, bytesFramed=0,
                 entryBlocks=0, entryBlocksFramed=0, entries=0,
                 distinctEntryIds=0, entryRecords=0,
                 entryRecordsCarryingTheMarker=0)))
        self.assertFalse(the_stmg_section_closes_byte_exactly({}))
        self.assertFalse(the_stmg_section_closes_byte_exactly(None))


class InitPluginTableTests(unittest.TestCase):
    """INIT names the plugins the source records carry, across a package boundary."""

    MEASURED = {
        "sections": 1, "sectionsFramed": 1, "platSections": 1,
        "platSectionsFramed": 1, "entries": 22, "distinctPluginIds": 22,
        "sourceRecordsJoined": 147262, "sourceRecordsNamingAPlugin": 973,
        "pluginIdsNotInTheTable": {"00040001": 132056, "00080001": 1721,
                                   "00140001": 12512},
    }

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(
            the_init_table_names_the_plugins_the_records_use(self.MEASURED))

    def test_a_company_two_id_missing_from_the_table_fails(self) -> None:
        # The check that tests the decomposition rather than the coverage. Company 1
        # is the built-in codec set and INIT does not list it, so those absences are
        # expected; a company-2 id absent would mean (plugin << 16) | company is the
        # wrong reading of the word.
        self.assertFalse(the_init_table_names_the_plugins_the_records_use(
            dict(self.MEASURED, pluginIdsNotInTheTable={"00040001": 132056,
                                                        "00650002": 833})))

    def test_a_section_that_does_not_close_fails(self) -> None:
        self.assertFalse(the_init_table_names_the_plugins_the_records_use(
            dict(self.MEASURED, sectionsFramed=0)))
        self.assertFalse(the_init_table_names_the_plugins_the_records_use(
            dict(self.MEASURED, platSectionsFramed=0)))

    def test_colliding_plugin_ids_fail(self) -> None:
        self.assertFalse(the_init_table_names_the_plugins_the_records_use(
            dict(self.MEASURED, distinctPluginIds=21)))

    def test_a_table_that_names_nothing_fails(self) -> None:
        # The state a package-local join produced: the table parsed, and joined to
        # almost nothing, because its users are in another file.
        self.assertFalse(the_init_table_names_the_plugins_the_records_use(
            dict(self.MEASURED, sourceRecordsNamingAPlugin=0)))

    def test_an_empty_census_fails_rather_than_passing_vacuously(self) -> None:
        self.assertFalse(the_init_table_names_the_plugins_the_records_use({}))
        self.assertFalse(the_init_table_names_the_plugins_the_records_use(None))

    def test_the_join_pools_across_packages(self) -> None:
        # One package holds INIT, another holds the records. The join must see both.
        base = {k: 0 for k in (
            "sections", "sectionsTooShort", "countOutOfRange",
            "sectionsNotClosing", "sectionsFramed", "entries",
            "distinctPluginIds", "platSections", "platSectionsNotClosing",
            "platSectionsFramed")}
        audit = {"rows": [
            {"status": "verified", "package": {
                "init": dict(base, sections=1, sectionsFramed=1, entries=2,
                             distinctPluginIds=2,
                             pluginNames={"00640002": "AkSineTone",
                                          "00650002": "AkSilenceGenerator"})}},
            {"status": "verified", "package": {"hircMediaJoin": {
                "hircSourceRecords": {"pluginIdsByType": {
                    "type02_plugin_00650002": 833,
                    "type02_plugin_00040001": 100}}}}},
        ]}
        out = init_from_audit(audit)
        self.assertEqual(out["pluginNames"], 2)
        self.assertEqual(out["sourceRecordsNamingAPlugin"], 833)
        self.assertEqual(out["pluginsUsed"], {"AkSilenceGenerator": 833})
        self.assertEqual(out["pluginIdsNotInTheTable"], {"00040001": 100})

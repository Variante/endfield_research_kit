from __future__ import annotations

import copy
import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.audio_semantics.hirc_action_corpus import (
    _read_shared_constant_census,
    TYPE11_ELEMENT_MAPS,
    TYPE11_ELEMENT_SCALARS,
    _rank_shared_constants,
    _read_type11_element_census,
    TYPE11_BODY_MINIMUM_EXACT,
    the_type11_body_frame_covers_most_of_its_corpus,
    TYPE11_HEADER_SCALARS,
    _read_hierarchy_census,
    _read_music_mutuality_census,
    _read_type0a_anchor_census,
    _read_type0a_array_census,
    the_type0a_reference_is_a_counted_array,
    _read_parent_field_census,
    _read_type0c_hierarchy_census,
    the_parent_field_inverts_the_reference_graph,
    the_type0c_parent_relation_repeats_the_same_shape,
    edges_per_distinct_distance,
    end_distance_alignment,
    the_music_types_split_into_located_and_scattered_references,
    the_type0a_end_anchor_beats_every_neighbouring_distance,
    the_type0a_to_type0b_edge_is_aligned_to_the_body_end,
    music_references_resolve_inside_their_own_bank,
    the_music_relation_is_symmetric,
    _read_type11_header_census,
    almost_every_bank_contributes_one_tree,
    numeric_type_12_is_a_leaf,
    the_hierarchy_runs_opposite_to_the_main_reference_graph,
    the_shared_hierarchy_is_a_forest,
    the_type11_curve_records_carry_interpolation_codes,
    the_type11_entry_header_carries_a_bounded_float,
    the_type11_element_count_is_not_yet_a_count,
    the_type11_element_frame_beats_its_rivals,
    the_type11_entry_header_fields_beat_their_controls,
    the_type11_element_frame_is_not_settled_by_empty_elements,
    the_type11_trailer_anchor_beats_its_rivals,
    the_type11_trailer_is_not_settled_by_parsing,
    every_group_reports_the_bodies_behind_it,
    summarise_group_evidence,
    thinly_seen_groups,
    every_shared_constant_beats_its_rivals,
    the_shared_constants_are_not_settled_by_closure,
    type03_targets_cross_bank_boundaries,
    media_join_is_decided_by_the_plugin_id,
    small_types_are_closed,
    type09_is_framed_except_the_second_run,
    type17_is_framed_except_the_tied_block,
    type08_head_words_are_null_or_resolve,
    type11_sources_share_the_type02_plugin_space,
    type11_bodies_share_one_terminator,
    type11_entries_carry_the_shared_curve_record,
    music_tail_words_are_named,
    music_bodies_all_carry_references,
    the_music_partition_edge_is_one_to_one,
    the_music_partition_edge_sits_at_a_few_places,
    the_type0a_head_rule_beats_its_controls,
    the_type0a_head_word_always_names_one_of_two_types,
    the_type0a_head_elements_are_padded_small_values,
    the_type0a_reference_is_an_optional_four_byte_field,
    the_type0a_tail_float_is_an_authored_value,
    the_type0a_tail_word_is_a_fixed_point_fraction,
    the_type0a_head_carries_a_bounded_whole_float,
    the_type0a_word_five_points_outside_its_package,
    _read_type0a_head_census,
    _read_music_reference_census,
    type08_bodies_are_exact_or_named,
    type12_bodies_are_exact_or_named,
    _read_type12_body_frame,
    type08_tail_records_are_located_by_a_unique_count,
    type12_tail_records_are_located_by_a_unique_count,
    _read_type12_tail_census,
    type08_tail_head_names_one_object_type,
    _read_type08_tail_word_census,
    _read_type08_tail_census,
    _read_type08_body_frame,
    type11_tail_entries_are_counted,
    _read_type11_source_census,
    music_head_references_are_closed,
    _capture_cli_output_closure,
    _load_json_with_sha256,
    _body_lane_markdown,
    _type02_markdown,
    _type04_markdown,
    aggregate_current_hirc_actions,
    load_current_outer,
    body_lane_corpus_is_closed,
    reference_graph_is_closed,
    _reference_graph_markdown,
)


def valid_action_fixture():
    outer = {
        "primaryAssets": "D:/Persistent",
        "fallbackAssets": "D:/StreamingAssets",
    }
    expected_files = [
        {
            "block": "Audio",
            "path": "Data/Audio/banks.pck",
            "declaredBytes": 100,
            "fileDataMd5": "A" * 32,
            "chunk": "bank.chk",
            "source": "D:/Persistent/VFS/AA/bank.chk",
        }
    ]
    excluded_files = [
        {
            "block": "AudioJapanese",
            "path": f"Data/Audio/voice_{index}.pck",
            "status": "excluded_missing_voice",
            "chunkFile": f"voice_{index}.chk",
        }
        for index in range(2)
    ]
    frame = {
        "count": 2,
        "exact": 2,
        "unsupported": 0,
        "failed": 0,
        "ambiguous": 0,
        "bodyBytes": 19,
        "exactCursorBytes": 19,
        "operationCounts": {"0x0400": 1, "0x1200": 1},
        "failureCategories": {},
        "nonExactExamples": [],
    }
    type02_prefix = {
        "count": 2,
        "prefixBytes": 36,
        "opaqueTailBytes": 64,
        "minOpaqueTailBytes": 32,
        "maxOpaqueTailBytes": 32,
        "pluginTypeCounts": {"0x1": 1, "0x2": 1},
        "pluginIdCounts": {"plugin_00040001": 1, "plugin_00140001": 1},
    }
    type02_stats = {"count": 2, "declaredLengthBytes": 108}
    type07_stats = {"count": 2, "declaredLengthBytes": 248}
    type05_stats = {"count": 2, "declaredLengthBytes": 148}
    type05_body = {
        "count": 2,
        "exact": 2,
        "unsupported": 0,
        "failed": 0,
        "ambiguous": 0,
        "bodyBytes": 140,
        "exactCursorBytes": 140,
        "nonExactBodyBytes": 0,
        "minExactBodyBytes": 61,
        "maxExactBodyBytes": 79,
        "groupCounts": {
            "referenceEntries": 3,
            "recordEntries": 2,
            "referenceRecordCountMismatch": 1,
            "groupIEntries": 0,
            "groupIKeyBytes": 0,
        },
        "selectorCounts": {
            "groupAFlag_00": 2,
            "groupBFlag_00": 2,
            "groupESelector_00": 2,
            "groupFSelector_00": 2,
        },
        "failureCategories": {},
        "unsupportedCategories": {},
        "nonExactExamples": [],
    }
    type07_body = {
        "count": 2,
        "exact": 2,
        "unsupported": 0,
        "failed": 0,
        "ambiguous": 0,
        "bodyBytes": 240,
        "exactCursorBytes": 240,
        "nonExactBodyBytes": 0,
        "minExactBodyBytes": 110,
        "maxExactBodyBytes": 130,
        "groupCounts": {
            "childEntries": 4,
            "groupIEntries": 2,
            "groupIKeyBytes": 3,
            "groupHStates": 2,
            "groupHStateElements": 3,
        },
        "selectorCounts": {
            "groupAFlag_00": 2,
            "groupBFlag_00": 2,
            "groupESelector_00": 2,
            "groupFSelector_00": 2,
            "groupIKeyWidth_1": 1,
            "groupIKeyWidth_2": 1,
            "groupHStateWidth_12": 1,
            "groupHStateWidth_18": 1,
        },
        "failureCategories": {},
        "unsupportedCategories": {},
        "nonExactExamples": [],
    }
    type02_body = {
        "count": 2,
        "exact": 2,
        "unsupported": 0,
        "failed": 0,
        "ambiguous": 0,
        "bodyBytes": 100,
        "exactCursorBytes": 100,
        "nonExactBodyBytes": 0,
        "minExactBodyBytes": 45,
        "maxExactBodyBytes": 55,
        "groupCounts": {
            "groupAEntries": 0,
            "groupCEntries": 3,
            "groupIEntries": 1,
            "groupIKeyBytes": 1,
            "groupIPoints": 4,
        },
        "selectorCounts": {
            "groupAFlag_00": 2,
            "groupBFlag_00": 2,
            "groupESelector_00": 2,
            "groupFSelector_00": 2,
            "groupIKeyWidth_1": 1,
        },
        "failureCategories": {},
        "unsupportedCategories": {},
        "nonExactExamples": [],
    }
    media_join = {
        "mediaEntries": 3,
        "mediaIds": [10, 11, 12],
        "sourceIdsByPlugin": {
            "plugin_00040001": [10, 11],
            "plugin_00650002": [90, 91],
        },
    }
    small_types = {
        "bodies": 4,
        "exact": 4,
        "failed": 0,
        "exactBytes": 120,
        "bodyBytes": 120,
        "bodiesWithSecondBlock": 2,
        "secondBlockEntries": 3,
        "bodiesByType": {"type13": 1, "type14": 2, "type15": 1},
        "failureCounts": {},
    }
    type03_targets = {
        "objects": 10,
        "zero": 1,
        "sameBank": 6,
        "otherBankInPackage": 2,
        "outsidePackage": 1,
        "sameBankByActionByte": {"action_03": 6},
        "otherBankByActionByte": {"action_02": 2},
        "outsideByActionByte": {"action_04": 1},
    }
    type09_bodies = {
        "bodies": 5,
        "exact": 4,
        "unestablishedSecondRun": 1,
        "failed": 0,
        "exactBytes": 80,
        "bodyBytes": 100,
        "runEntries": 6,
        "failureCounts": {},
        "tailFlagCounts": {"tail_00": 3, "tail_01": 1},
    }
    type17_bodies = {
        "bodies": 5,
        "exact": 4,
        "fenced": 1,
        "failed": 0,
        "exactBytes": 80,
        "bodyBytes": 100,
        "runElements": 3,
        "groupIEntries": 2,
        "failureCounts": {},
        "fenceReasons": {"tiedOptionalBlockWidth": 1},
        "bodiesByType": {"type10": 2, "type11": 3},
    }
    type08_head = {
        "bodies": 3,
        "resolved": 2,
        "null": 1,
        "unresolved": 0,
        "tooShort": 0,
    }
    type08_body = {
        "count": 3,
        "exact": 2,
        "unsupported": 0,
        "failed": 1,
        "ambiguous": 0,
        "bodyBytes": 180,
        "failureCategories": {"trailer_is_not_five_bytes": 1},
        "unsupportedCategories": {},
        "selectorCounts": {"tailBlockSelector_020002": 1},
    }
    type08_tail = {
        "bodies": 3,
        "notWalkable": 0,
        "framedByTheReader": 2,
        "tails": 1,
        "noZeroWordAtTheEnd": 0,
        "noCountBeforeTheRecords": 0,
        "countIsAmbiguous": 0,
        "tailsWithAUniqueCount": 1,
        "records": 2,
        "unexplainedHeadBytes": 15,
        "recordCountCounts": {"records_2": 1},
        "thirdFieldCounts": {"code_4": 1, "code_9": 1},
        "headsOfTheObservedWidth": 1,
        "headIsNotTheObservedWidth": 0,
    }
    type12_body = {
        "count": 4,
        "exact": 3,
        "unsupported": 0,
        "failed": 1,
        "ambiguous": 0,
        "bodyBytes": 240,
        "failureCategories": {"trailer_is_not_five_bytes": 1},
        "unsupportedCategories": {},
        "selectorCounts": {"secondListKey_15": 2, "secondListKey_0A": 1},
    }
    # Numeric type 0x12's tail head resolves nowhere, control included -- the two
    # types share a layout but not this field's meaning.
    type12_tail_words = {
        "heads": 1,
        "packagePopulation": 200,
        "firstWordSameBank": 0,
        "firstWordOtherBankInPackage": 0,
        "firstWordOutsidePackage": 1,
        "secondWordResolves": 0,
        "firstWordTargetTypeCounts": {},
        "secondWordTargetTypeCounts": {},
    }
    type08_tail_words = {
        "heads": 1,
        "packagePopulation": 200,
        "firstWordSameBank": 1,
        "firstWordOtherBankInPackage": 0,
        "firstWordOutsidePackage": 0,
        "secondWordResolves": 0,
        "firstWordTargetTypeCounts": {"type12": 1},
        "secondWordTargetTypeCounts": {},
    }
    type11_sources = {
        "bodies": 2,
        "bodiesWithRecords": 2,
        "records": 3,
        "recordsOutOfRange": 0,
        "tooShort": 0,
        "pluginIdCounts": {"plugin_00040001": 2, "plugin_00140001": 1},
        "streamTypeCounts": {"streamType_02": 3},
        "recordCountCounts": {"records_1": 1, "records_2": 1},
        "endsWithTerminator": 2,
        "terminatorCounts": {"end_00000064": 2},
        "bodiesWithATail": 2,
        "noTailAfterTheRun": 0,
        "tailCountOutOfRange": 0,
        "tailEntriesDeclared": 3,
        "tailEntriesEchoed": 3,
        "tailEchoesMatchTheCount": 2,
        "tailEchoesExceedTheCount": 0,
        "firstTailEntryNamesADeclaredSource": 2,
        "firstTailEntryTooShort": 0,
        "entriesInspected": 2,
        "entriesWithNoRecords": 1,
        "entriesWhoseRecordsFit": 1,
        "entriesWhoseCountIsNotUsable": 0,
        "entriesWhoseRecordsRunPastTheEnd": 0,
        "curveRecords": 2,
        "interpolationCounts": {"interp_1": 1, "interp_9": 1},
        "tailEntryCountCounts": {"tailEntries_1": 1, "tailEntries_2": 1},
        "firstTailEntryLeadingWordCounts": {"lead_00000000": 2},
    }
    type0a_head = {
        "bodies": 10,
        "bodiesWhereTheRuleApplies": 9,
        "namesTheSourceType": {
            "predicted": 9,
            "fixedOffset": 3,
            "predictedPlusFour": 1,
            "predictedMinusFour": 0,
        },
        "namesTheSourceTypeWhereTheRuleApplies": {
            "predicted": 9,
            "fixedOffset": 3,
            "predictedPlusFour": 1,
            "predictedMinusFour": 0,
        },
        "headWordTargets": {"type0D": 7, "type0C": 2},
        "elementTotal": 6,
        "elementLeadingByteNotZero": 0,
        "elementPadNotZero": 0,
        "elementValueCounts": {"value_0": 2, "value_1": 3, "value_2": 1},
        "tailBytesByOutcome": {"withReference_69": 8, "withoutReference_65": 2},
        "tailFloats": 100,
        "tailFloatsInBand": 92,
        "tailFloatsWhole": 99,
        "neighbourFloats": 100,
        "neighbourFloatsWhole": 5,
        "fractionCandidates": 100,
        "fractionsWithASmallDenominator": 78,
        "fractionControls": 200,
        "fractionControlsWithASmallDenominator": 6,
        "decibelBodies": 100,
        "decibelsInRange": 96,
        "decibelsWhole": 50,
        "decibelControlsInRange": 0,
        "wordFiveNonZero": 6,
        "wordFiveInPackage": 0,
        "wordFiveValues": {"word_F1339B46": 4, "word_4106E10A": 2},
    }
    music_refs = {
        "bodies": 4,
        "packagePopulation": 200,
        "wordsOffered": 400,
        "references": 9,
        "bodiesWithNoReference": 0,
        "referencesPerBody": {"refs_2": 3, "refs_3": 1},
        "edgeCounts": {"type0C_to_type0D": 5, "type0A_to_type0B": 4},
        "distinctTargets": {"type0C_to_type0D": 3, "type0A_to_type0B": 4},
        "targetsReachedTwice": {"type0C_to_type0D": 2, "type0A_to_type0B": 0},
        "targetPopulation": {"type0C_to_type0D": 3, "type0A_to_type0B": 4},
        "edgeDistanceFromEnd": {
            "type0A_to_type0B_at-69": 3,
            "type0A_to_type0B_at-73": 1,
            "type0C_to_type0D_at-40": 5,
        },
    }
    music_head = {
        "tailWordsTested": 8,
        "tailWordsNamed": 3,
        "bodiesTooShortForTailWords": 0,
        "tailWordNamedByOffset": {"minus12": 1, "minus24": 2},
        "tailWordTestedByOffset": {"minus12": 4, "minus24": 4},
        "bodies": 4,
        "resolved": 3,
        "unresolved": 0,
        "zero": 0,
        "unknownDiscriminant": 0,
        "tooShort": 0,
        "unknownHeadShape": 1,
        "bodies": 4,
        "bodiesByType": {"type0A": 2, "type0C": 1, "type0D": 1},
        "offsetCounts": {"offset_5": 1, "offset_9": 2},
        "discriminantCounts": {"byte2_00": 2, "byte2_01": 1},
        "headShapeCounts": {"head_00": 3, "head_06": 1},
    }
    type22_body = {
        "count": 2,
        "exact": 2,
        "unsupported": 0,
        "failed": 0,
        "ambiguous": 0,
        "bodyBytes": 49,
        "exactCursorBytes": 49,
        "nonExactBodyBytes": 0,
        "minExactBodyBytes": 9,
        "maxExactBodyBytes": 40,
        "groupCounts": {
            "propertyEntries": 3,
            "groupIEntries": 1,
            "groupIKeyBytes": 1,
            "groupIPoints": 1,
        },
        "selectorCounts": {
            "propertyKey_00": 2,
            "propertyKey_11": 1,
            "groupIKeyWidth_1": 1,
        },
        "failureCategories": {},
        "unsupportedCategories": {},
        "nonExactExamples": [],
    }
    type22_stats = {"count": 2, "declaredLengthBytes": 57}
    type14_body = {
        "count": 2,
        "exact": 2,
        "unsupported": 0,
        "failed": 0,
        "ambiguous": 0,
        "bodyBytes": 137,
        "exactCursorBytes": 137,
        "nonExactBodyBytes": 0,
        "minExactBodyBytes": 51,
        "maxExactBodyBytes": 86,
        "groupCounts": {
            "listEntries": 3,
            "listElements": 5,
            "optionalBlock": 1,
        },
        "selectorCounts": {
            "headByte_00": 1,
            "headByte_01": 1,
            "optionalBlockFlag_00": 1,
            "optionalBlockFlag_01": 1,
            "listEntrySelector_00": 2,
            "listEntrySelector_02": 1,
        },
        "failureCategories": {},
        "unsupportedCategories": {},
        "nonExactExamples": [],
    }
    type14_stats = {"count": 2, "declaredLengthBytes": 145}
    type04_vector = {
        "count": 2,
        "exact": 1,
        "unsupported": 1,
        "failed": 0,
        "ambiguous": 0,
        "bodyBytes": 11,
        "candidatePrefixBytes": 10,
        "unsupportedCandidatePrefixBytes": 5,
        "exactCursorBytes": 5,
        "opaqueTailBytes": 1,
        "failedBodyBytes": 0,
        "candidateEntryCount": 2,
        "exactEntryCount": 1,
        "failureCategories": {},
        "unsupportedCategories": {"opaque_tail_after_candidate_vector": 1},
        "nonExactExamples": [
            {
                "bankId": 123,
                "ordinal": 2,
                "objectId": 456,
                "status": "unsupported",
                "category": "opaque_tail_after_candidate_vector",
                "expectedBytes": 5,
                "actualBytes": 6,
                "opaqueTailBytes": 1,
            }
        ],
    }
    type04_stats = {"count": 2, "declaredLengthBytes": 19}
    reference_census = {
        "references": 8,
        "resolvedSameBank": 8,
        "unresolvedInBank": 0,
        "selfReferences": 0,
        "targetsWithMultipleReferrers": 0,
        "duplicateObjectIds": 0,
        "referencesToDuplicateIds": 0,
        "candidateWords": 0,
        "candidateWordsMatchingAnObject": 0,
        "referenceCycleOrFeedingNodes": 0,
        "distinctDuplicateObjectIds": 0,
        "maximumReferenceDepth": 3,
        "objectCountsByType": {"type02": 20, "type03": 10, "type04": 5, "type05": 8, "type07": 8},
        "edgeCounts": {"type07_to_type02": 4, "type04_to_type03": 1, "type05_to_type02": 3},
    }
    audio_audit = {
        "streamingAssets": "D:/Persistent",
        "fallbackAssets": "D:/StreamingAssets",
        "summary": {
            "packages": 1,
            "verified": 1,
            "failures": 0,
            "missingBlocks": 0,
            "excluded": 1,
        },
        "rows": [
            {
                "block": "Audio",
                "path": "Data/Audio/banks.pck",
                "declaredBytes": 100,
                "verifiedFileDataMd5": "A" * 32,
                "chunk": "bank.chk",
                "source": r"D:\Persistent\VFS\AA\bank.chk",
                "status": "verified",
                "package": {
                    "hircObjectTypeCounts": {"0x02": 2, "0x03": 2, "0x04": 2, "0x05": 2, "0x07": 2, "0x0E": 2, "0x16": 2},
                    "hircObjectTypeStats": {
                        "0x02": copy.deepcopy(type02_stats),
                        "0x04": copy.deepcopy(type04_stats),
                        "0x07": copy.deepcopy(type07_stats),
                        "0x05": copy.deepcopy(type05_stats),
                        "0x0E": copy.deepcopy(type14_stats),
                        "0x16": copy.deepcopy(type22_stats),
                    },
                    "hircType02Prefix": copy.deepcopy(type02_prefix),
                    "hircType02BodyFrame": copy.deepcopy(type02_body),
                    "hircType07BodyFrame": copy.deepcopy(type07_body),
                    "hircType14BodyFrame": copy.deepcopy(type14_body),
                    "hircType22BodyFrame": copy.deepcopy(type22_body),
                    "hircMusicHeadReferences": copy.deepcopy(music_head),
                    "hircMusicReferences": copy.deepcopy(music_refs),
                    "hircType0AHead": copy.deepcopy(type0a_head),
                    "hircType11Sources": copy.deepcopy(type11_sources),
                    "hircType08Head": copy.deepcopy(type08_head),
                    "hircType08BodyFrame": copy.deepcopy(type08_body),
                    "hircType08Tail": copy.deepcopy(type08_tail),
                    "hircType08TailWords": copy.deepcopy(type08_tail_words),
                    "hircType12BodyFrame": copy.deepcopy(type12_body),
                    "hircType12Tail": copy.deepcopy(type08_tail),
                    "hircType12TailWords": copy.deepcopy(type12_tail_words),
                    "hircType17": copy.deepcopy(type17_bodies),
                    "hircType09": copy.deepcopy(type09_bodies),
                    "hircType03Targets": copy.deepcopy(type03_targets),
                    "hircSmallTypes": copy.deepcopy(small_types),
                    "hircMediaJoin": copy.deepcopy(media_join),
                    "hircType05BodyFrame": copy.deepcopy(type05_body),
                    "hircReferenceCensus": copy.deepcopy(reference_census),
                    "hircType03ActionFrame": copy.deepcopy(frame),
                    "hircType04U32VectorFrame": copy.deepcopy(type04_vector),
                    "bnkStructures": [
                        {
                            "version": 150,
                            "hircObjectTypeStats": {
                                "0x02": copy.deepcopy(type02_stats),
                                "0x03": {"count": 2},
                                "0x04": copy.deepcopy(type04_stats),
                                "0x07": copy.deepcopy(type07_stats),
                                "0x05": copy.deepcopy(type05_stats),
                                "0x0E": copy.deepcopy(type14_stats),
                                "0x16": copy.deepcopy(type22_stats),
                            },
                            "hircType02Prefix": copy.deepcopy(type02_prefix),
                            "hircType02BodyFrame": copy.deepcopy(type02_body),
                            "hircType07BodyFrame": copy.deepcopy(type07_body),
                            "hircType14BodyFrame": copy.deepcopy(type14_body),
                            "hircType22BodyFrame": copy.deepcopy(type22_body),
                            "hircMusicHeadReferences": copy.deepcopy(music_head),
                            "hircType11Sources": copy.deepcopy(type11_sources),
                            "hircType08Head": copy.deepcopy(type08_head),
                            "hircType08BodyFrame": copy.deepcopy(type08_body),
                            "hircType08Tail": copy.deepcopy(type08_tail),
                            "hircType17": copy.deepcopy(type17_bodies),
                            "hircType09": copy.deepcopy(type09_bodies),
                            "hircType03Targets": copy.deepcopy(type03_targets),
                            "hircSmallTypes": copy.deepcopy(small_types),
                            "hircMediaJoin": copy.deepcopy(media_join),
                            "hircType05BodyFrame": copy.deepcopy(type05_body),
                            "hircReferenceCensus": copy.deepcopy(reference_census),
                            "hircType03ActionFrame": copy.deepcopy(frame),
                            "hircType04U32VectorFrame": copy.deepcopy(type04_vector),
                        }
                    ],
                },
            },
            {
                "block": "AudioJapanese",
                "status": "excluded_missing_voice",
                "source": "missing_both",
                "declaredChunks": 2,
                "declaredFiles": 2,
            },
        ],
    }
    return outer, expected_files, excluded_files, audio_audit


class HircActionCorpusTests(unittest.TestCase):
    def test_type02_markdown_reports_gate_and_evidence_boundary(self) -> None:
        report = {
            "status": "complete",
            "inputSetSha256": "A" * 64,
            "outer": {
                "ledgerSha256": "B" * 64,
                "animeStudioCliFingerprint": {
                    "matchesOuterAudit": False,
                    "outerAuditSha256": "C" * 64,
                    "currentSha256": "D" * 64,
                },
            },
            "audioAudit": {
                "toolSha256": "D" * 64,
                "toolClosure": {"fileCount": 79, "manifestSha256": "G" * 64},
                "intermediatePath": "tmp/audio-audit.json",
                "sha256": "E" * 64,
            },
            "corpusGate": {"sha256": "F" * 64},
            "corpus": {
                "packageCount": 1,
                "verifiedPackageCount": 1,
                "excludedBlockCount": 0,
                "type02SourcePrefixes": {
                    "wholeBodyCursor": "not-claimed-opaque-tail-remains",
                    "count": 1,
                    "packagesWithObjects": 1,
                    "banksWithObjects": 1,
                    "prefixBytes": 14,
                    "opaqueTailBytes": 8,
                    "bodyBytes": 22,
                    "minOpaqueTailBytes": 8,
                    "maxOpaqueTailBytes": 8,
                    "pluginTypeCounts": {"0x1": 1},
                    "objectCountsByBlock": {"Audio": 1},
                },
            },
        }

        markdown = _type02_markdown(report)

        self.assertIn("not-claimed-opaque-tail-remains", markdown)
        self.assertIn("opaque tail bytes: 8", markdown)
        self.assertIn("Corpus gate SHA-256: `" + "F" * 64, markdown)
        self.assertIn("Low-nibble type", markdown)
        self.assertIn("Remaining body bytes stay opaque", markdown)

    def test_type04_markdown_keeps_vector_values_anonymous(self) -> None:
        report = {
            "status": "complete",
            "inputSetSha256": "A" * 64,
            "outer": {
                "ledgerSha256": "B" * 64,
                "animeStudioCliFingerprint": {
                    "matchesOuterAudit": False,
                    "outerAuditSha256": "C" * 64,
                    "currentSha256": "D" * 64,
                },
            },
            "audioAudit": {
                "toolSha256": "D" * 64,
                "toolClosure": {"fileCount": 79, "manifestSha256": "G" * 64},
                "intermediatePath": "tmp/audio-audit.json",
                "sha256": "E" * 64,
            },
            "corpusGate": {"sha256": "F" * 64},
            "corpus": {
                "packageCount": 1,
                "verifiedPackageCount": 1,
                "excludedBlockCount": 0,
                "type04U32VectorCandidates": {
                    "frameClosure": "all-candidate-vectors-exact",
                    "count": 1,
                    "exact": 1,
                    "unsupported": 0,
                    "failed": 0,
                    "ambiguous": 0,
                    "bodyBytes": 5,
                    "candidatePrefixBytes": 5,
                    "exactCursorBytes": 5,
                    "opaqueTailBytes": 0,
                    "failedBodyBytes": 0,
                    "candidateEntryCount": 1,
                    "packagesWithObjects": 1,
                    "banksWithObjects": 1,
                    "failureCategories": {},
                    "unsupportedCategories": {},
                    "objectCountsByBlock": {"Audio": 1},
                },
            },
        }

        markdown = _type04_markdown(report)

        self.assertIn("all-candidate-vectors-exact", markdown)
        # The entry targets are still unnamed, but the objects holding the vectors
        # are not, and the entries do resolve. The report must keep the narrow
        # statement without implying the broader one.
        self.assertIn("entry targets themselves remain unnamed", markdown)
        self.assertNotIn("Entry values remain unnamed", markdown)
        self.assertIn("named-reach report", markdown)
        self.assertIn("does not establish serialized field ownership", markdown)
        self.assertIn("Corpus gate SHA-256: `" + "F" * 64, markdown)
        self.assertIn("79 files", markdown)
        self.assertIn("G" * 64, markdown)

    def test_cli_output_closure_hash_covers_apphost_and_managed_sidecars(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "cli"
            nested = output / "runtimes" / "win-x64"
            nested.mkdir(parents=True)
            cli = output / "AnimeStudio.CLI.exe"
            cli.write_bytes(b"apphost")
            (output / "AnimeStudio.CLI.dll").write_bytes(b"cli assembly")
            assembly = output / "AnimeStudio.dll"
            assembly.write_bytes(b"parser assembly v1")
            (nested / "native.dll").write_bytes(b"native support")

            first = _capture_cli_output_closure(cli)
            repeated = _capture_cli_output_closure(cli)
            self.assertEqual(first["fileCount"], 4)
            self.assertEqual(first["manifestSha256"], repeated["manifestSha256"])
            self.assertIn("AnimeStudio.dll", {row["path"] for row in first["files"]})

            assembly.write_bytes(b"parser assembly v2")
            changed = _capture_cli_output_closure(cli)
            self.assertNotEqual(first["manifestSha256"], changed["manifestSha256"])

    def test_intermediate_report_hash_uses_the_bytes_that_were_parsed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.json"
            original = b'{"revision":1}\n'
            path.write_bytes(original)

            parsed, digest = _load_json_with_sha256(path)

            path.write_bytes(b'{"revision":2}\n')
            self.assertEqual(parsed, {"revision": 1})
            self.assertEqual(digest, hashlib.sha256(original).hexdigest().upper())

    def test_outer_gate_binds_expected_set_ledger_and_physical_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            primary = root / "Persistent"
            fallback = root / "StreamingAssets"
            primary.mkdir()
            fallback.mkdir()
            metadata = root / "fixture.blc"
            metadata.write_bytes(b"metadata-v1")
            ledger = root / "ledger.jsonl.gz"
            with gzip.open(ledger, "wt", encoding="utf-8") as handle:
                handle.write("{}\n")
            input_set = "A" * 64
            outer = {
                "format": "animestudio-vfs-boundary-audit",
                "schemaVersion": 1,
                "inputSetSha256": input_set,
                "primaryAssets": str(primary),
                "fallbackAssets": str(fallback),
                "summary": {
                    "fullAuditPassed": True,
                    "allAvailableBoundaryVerified": True,
                    "failureCount": 0,
                },
                "publication": {
                    "ledgerSha256": hashlib.sha256(ledger.read_bytes()).hexdigest().upper(),
                },
                "sourceFingerprints": [
                    {
                        "path": str(metadata),
                        "sha256": hashlib.sha256(metadata.read_bytes()).hexdigest().upper(),
                    }
                ],
            }
            outer_path = root / "outer.json"
            outer_path.write_text(json.dumps(outer), encoding="utf-8")

            loaded, evidence = load_current_outer(outer_path, ledger, input_set)
            self.assertEqual(loaded["inputSetSha256"], input_set)
            self.assertEqual(evidence["sourceFingerprintsMatched"], 1)

            with self.assertRaisesRegex(ValueError, "input-set mismatch"):
                load_current_outer(outer_path, ledger, "B" * 64)

            metadata.write_bytes(b"metadata-v2")
            with self.assertRaisesRegex(ValueError, "source fingerprints changed"):
                load_current_outer(outer_path, ledger, input_set)

    def test_action_corpus_aggregate_closes_every_current_body(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        actions = result["type03Objects"]
        self.assertEqual(actions["count"], 2)
        self.assertEqual(actions["exact"], 2)
        self.assertEqual(actions["frameClosure"], "exact")
        self.assertEqual(actions["bodyBytes"], actions["exactCursorBytes"])
        self.assertEqual(result["excludedBlockCount"], 1)
        self.assertTrue(result["identityReconciliation"]["verifiedPackagesMatchedToOuterLedger"])
        self.assertTrue(result["identityReconciliation"]["excludedBlocksMatchedToOuterLedger"])
        self.assertTrue(result["identityReconciliation"]["perBankFramesMatchedToPackageFrames"])
        prefixes = result["type02SourcePrefixes"]
        self.assertEqual(prefixes["count"], 2)
        self.assertEqual(prefixes["prefixBytes"], 36)
        self.assertEqual(prefixes["opaqueTailBytes"], 64)
        self.assertEqual(prefixes["bodyBytes"], 100)
        self.assertEqual(prefixes["pluginTypeCounts"], {"0x1": 1, "0x2": 1})
        self.assertEqual(prefixes["wholeBodyCursor"], "not-claimed-opaque-tail-remains")
        vectors = result["type04U32VectorCandidates"]
        self.assertEqual(vectors["count"], 2)
        self.assertEqual(vectors["exact"], 1)
        self.assertEqual(vectors["unsupported"], 1)
        self.assertEqual(vectors["bodyBytes"], 11)
        self.assertEqual(vectors["candidatePrefixBytes"], 10)
        self.assertEqual(vectors["opaqueTailBytes"], 1)
        self.assertEqual(vectors["candidateEntryCount"], 2)
        self.assertEqual(vectors["frameClosure"], "incomplete")
        self.assertEqual(vectors["unsupportedCategories"], {"opaque_tail_after_candidate_vector": 1})
        self.assertTrue(result["identityReconciliation"]["perBankType04FramesMatchedToPackageFrames"])

    def test_type02_body_frames_close_every_current_body_anonymously(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        bodies = result["type02BodyFrames"]
        self.assertEqual(bodies["count"], 2)
        self.assertEqual(bodies["exact"], 2)
        self.assertEqual(bodies["frameClosure"], "all-bodies-exact")
        self.assertEqual(bodies["bodyBytes"], bodies["exactCursorBytes"])
        self.assertEqual(bodies["nonExactBodyBytes"], 0)
        self.assertEqual(bodies["anonymousGroupCounts"]["groupCEntries"], 3)
        self.assertEqual(bodies["anonymousSelectorCounts"]["groupBFlag_00"], 2)
        # Both lanes publish the shared framer's residuals, so neither can quietly
        # carry a shorter list than the other.
        self.assertEqual(len(bodies["unresolvedWidths"]), 9)
        joined = " ".join(bodies["unresolvedWidths"])
        self.assertIn("group A slot split", joined)
        self.assertIn("group E branch 2", joined)
        self.assertIn("inherited from the type 0x03 Action reader", joined)
        self.assertIn("aborts the whole package", bodies["upstreamAbortsNotCountedHere"])
        self.assertEqual(bodies["minExactBodyBytes"], 45)
        self.assertTrue(
            result["identityReconciliation"]["verifiedPackagesMatchedToOuterLedger"]
        )

    def test_type02_body_gate_rejects_partition_and_byte_mismatches(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()

        bad_partition = copy.deepcopy(audio_audit)
        bad_partition["rows"][0]["package"]["hircType02BodyFrame"]["exact"] = 1
        with self.assertRaisesRegex(ValueError, "type 0x02 body outcome partition mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_partition)

        bad_bytes = copy.deepcopy(audio_audit)
        bad_bytes["rows"][0]["package"]["hircType02BodyFrame"]["nonExactBodyBytes"] = 4
        with self.assertRaisesRegex(ValueError, "exact/non-exact body accounting mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_bytes)

        bad_declared = copy.deepcopy(audio_audit)
        bad_declared["rows"][0]["package"]["hircType02BodyFrame"]["bodyBytes"] = 96
        bad_declared["rows"][0]["package"]["hircType02BodyFrame"]["exactCursorBytes"] = 96
        with self.assertRaisesRegex(ValueError, "body bytes differ from declared HIRC object bodies"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_declared)

        # A single undersized body must be rejected even when the mean is healthy.
        short_bodies = copy.deepcopy(audio_audit)
        for scope in (
            short_bodies["rows"][0]["package"],
            short_bodies["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType02BodyFrame"].update(
                {"minExactBodyBytes": 44, "maxExactBodyBytes": 56}
            )
        with self.assertRaisesRegex(ValueError, "falls below the minimum frame"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, short_bodies)

        unbounded_range = copy.deepcopy(audio_audit)
        for scope in (
            unbounded_range["rows"][0]["package"],
            unbounded_range["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType02BodyFrame"]["maxExactBodyBytes"] = 49
        with self.assertRaisesRegex(ValueError, "exact-length range does not bound its total"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, unbounded_range)

    def test_type02_body_gate_requires_selector_and_bank_reconciliation(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()

        bad_selector = copy.deepcopy(audio_audit)
        bad_selector["rows"][0]["package"]["hircType02BodyFrame"]["selectorCounts"][
            "groupESelector_00"
        ] = 1
        with self.assertRaisesRegex(ValueError, "selector family groupESelector_"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_selector)

        bad_bank = copy.deepcopy(audio_audit)
        bank_body = bad_bank["rows"][0]["package"]["bnkStructures"][0]["hircType02BodyFrame"]
        bank_body["groupCounts"]["groupCEntries"] = 2
        with self.assertRaisesRegex(ValueError, "type 0x02 group inventory mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_bank)

        bad_range = copy.deepcopy(audio_audit)
        bad_range["rows"][0]["package"]["bnkStructures"][0]["hircType02BodyFrame"][
            "minExactBodyBytes"
        ] = 46
        with self.assertRaisesRegex(ValueError, "type 0x02 exact-length range mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_range)

        missing_frame = copy.deepcopy(audio_audit)
        del missing_frame["rows"][0]["package"]["hircType02BodyFrame"]
        with self.assertRaisesRegex(ValueError, "missing type 0x02 body-frame result"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, missing_frame)

    def test_type02_body_gate_preserves_unsupported_and_failed_outcomes(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        held = copy.deepcopy(audio_audit)
        for scope in (
            held["rows"][0]["package"],
            held["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType02BodyFrame"].update(
                {
                    "exact": 0,
                    "unsupported": 1,
                    "failed": 1,
                    "exactCursorBytes": 0,
                    "nonExactBodyBytes": 100,
                    "minExactBodyBytes": 0,
                    "maxExactBodyBytes": 0,
                    "groupCounts": {},
                    "selectorCounts": {},
                    "failureCategories": {"trailing_bytes": 1},
                    "unsupportedCategories": {"unsupported_groupB_nonempty": 1},
                }
            )
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, held)
        bodies = result["type02BodyFrames"]
        self.assertEqual(bodies["exact"], 0)
        self.assertEqual(bodies["frameClosure"], "incomplete")
        self.assertEqual(bodies["nonExactBodyBytes"], 100)
        self.assertEqual(bodies["failureCategories"], {"trailing_bytes": 1})
        self.assertEqual(
            bodies["unsupportedCategories"], {"unsupported_groupB_nonempty": 1}
        )

        miscounted = copy.deepcopy(held)
        miscounted["rows"][0]["package"]["hircType02BodyFrame"]["unsupportedCategories"] = {}
        with self.assertRaisesRegex(ValueError, "unsupportedCategories do not match outcome counts"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, miscounted)

    def test_type02_body_closure_is_enforced_not_just_reported(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        closed = aggregate_current_hirc_actions(
            outer, expected_files, excluded_files, audio_audit
        )["type02BodyFrames"]
        self.assertTrue(body_lane_corpus_is_closed(closed))

        # Every way of not closing must be refused, including a lane that reports
        # itself exact while leaving bytes unaccounted.
        for field, value in (
            ("frameClosure", "incomplete"),
            ("exact", 1),
            ("unsupported", 1),
            ("failed", 1),
            ("ambiguous", 1),
            ("nonExactBodyBytes", 1),
        ):
            regressed = dict(closed)
            regressed[field] = value
            self.assertFalse(
                body_lane_corpus_is_closed(regressed),
                f"{field}={value} must not count as a closed corpus",
            )

    def test_type02_body_markdown_keeps_groups_and_widths_anonymous(self) -> None:
        report = {
            "status": "complete",
            "inputSetSha256": "A" * 64,
            "outer": {
                "ledgerSha256": "B" * 64,
                "animeStudioCliFingerprint": {
                    "matchesOuterAudit": False,
                    "outerAuditSha256": "C" * 64,
                    "currentSha256": "D" * 64,
                },
            },
            "audioAudit": {
                "toolSha256": "D" * 64,
                "toolClosure": {"fileCount": 79, "manifestSha256": "G" * 64},
                "intermediatePath": "tmp/audio-audit.json",
                "sha256": "E" * 64,
            },
            "corpusGate": {"sha256": "F" * 64},
            "corpus": {
                "packageCount": 1,
                "verifiedPackageCount": 1,
                "excludedBlockCount": 0,
                "type02BodyFrames": {
                    "frameClosure": "all-bodies-exact",
                    "count": 1,
                    "exact": 1,
                    "unsupported": 0,
                    "failed": 0,
                    "ambiguous": 0,
                    "bodyBytes": 45,
                    "exactCursorBytes": 45,
                    "nonExactBodyBytes": 0,
                    "packagesWithObjects": 1,
                    "banksWithObjects": 1,
                    "anonymousGroupCounts": {"groupCEntries": 2},
                    "anonymousSelectorCounts": {"groupAFlag_00": 1},
                    "failureCategories": {},
                    "unsupportedCategories": {},
                    "minExactBodyBytes": 45,
                    "maxExactBodyBytes": 45,
                    "minimumPossibleFrameBytes": 45,
                    "frameLayout": "The reader consumes the bounded source prefix and the node groups.",
                    "objectCountsByBlock": {"Audio": 1},
                    "unresolvedWidths": ["group B element width: no nonempty vector"],
                    "upstreamAbortsNotCountedHere": "a malformed source prefix aborts the package",
                },
            },
            "evidenceBoundary": {"nonClaims": ["serialized field ownership or field names", "group, selector, key, or value meanings"]},
        }

        markdown = _body_lane_markdown(report, "type02BodyFrames", "0x02")

        self.assertIn("all-bodies-exact", markdown)
        self.assertIn("What this corpus does not resolve", markdown)
        self.assertIn("group B element width", markdown)
        self.assertIn("Failures this lane cannot count", markdown)
        self.assertIn("aborts the package", markdown)
        self.assertIn("internal consistency assert, not independent evidence", markdown)
        self.assertIn("Closure is enforced", markdown)
        self.assertIn("stays anonymous", markdown)
        self.assertIn("does not establish:", markdown)
        self.assertIn("- serialized field ownership or field names", markdown)
        self.assertIn("Corpus gate SHA-256: `" + "F" * 64, markdown)

    def test_reference_graph_joins_every_reference_to_one_same_bank_object(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        graph = aggregate_current_hirc_actions(
            outer, expected_files, excluded_files, audio_audit
        )["referenceGraph"]
        self.assertEqual(graph["references"], 8)
        self.assertEqual(graph["resolvedSameBank"], 8)
        self.assertEqual(graph["framedVectorEntries"], 8)
        # One type 0x04 body is unsupported, so one framed entry never resolves.
        self.assertEqual(graph["entriesNotReachingCensus"], 1)
        self.assertFalse(reference_graph_is_closed(graph))
        self.assertEqual(graph["semanticStatus"], "structural-only")
        # The edges stay numeric on both sides.
        self.assertEqual(
            sorted(graph["edgeCounts"]),
            ["type04_to_type03", "type05_to_type02", "type07_to_type02"],
        )

    def test_reference_graph_rejects_every_way_of_not_naming_one_object(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()

        for field, value, pattern in (
            ("unresolvedInBank", 1, "reference outcome partition mismatch"),
            ("selfReferences", 99, "self references exceed total references"),
            ("referencesToDuplicateIds", 99, "duplicate-id references exceed total"),
            ("targetsWithMultipleReferrers", 99, "multi-referrer targets exceed total"),
        ):
            broken = copy.deepcopy(audio_audit)
            for scope in (
                broken["rows"][0]["package"],
                broken["rows"][0]["package"]["bnkStructures"][0],
            ):
                scope["hircReferenceCensus"][field] = value
            with self.assertRaisesRegex(ValueError, pattern):
                aggregate_current_hirc_actions(outer, expected_files, excluded_files, broken)

        unaccounted = copy.deepcopy(audio_audit)
        for scope in (
            unaccounted["rows"][0]["package"],
            unaccounted["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircReferenceCensus"]["edgeCounts"]["type04_to_type03"] = 2
        with self.assertRaisesRegex(ValueError, "edges do not account for every resolved"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, unaccounted)

        named = copy.deepcopy(audio_audit)
        for scope in (
            named["rows"][0]["package"],
            named["rows"][0]["package"]["bnkStructures"][0],
        ):
            edges = scope["hircReferenceCensus"]["edgeCounts"]
            del edges["type04_to_type03"]
            edges["event_to_action"] = 2
        with self.assertRaisesRegex(ValueError, "edge is not a numeric type pair"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, named)

        # Drift the bank totals while keeping each census internally consistent, so the
        # per-bank reconciliation is what fires rather than a local partition check.
        bank_drift = copy.deepcopy(audio_audit)
        bank_census = bank_drift["rows"][0]["package"]["bnkStructures"][0]["hircReferenceCensus"]
        bank_census["references"] = 7
        bank_census["resolvedSameBank"] = 7
        bank_census["edgeCounts"] = {"type07_to_type02": 3, "type04_to_type03": 1, "type05_to_type02": 3}
        with self.assertRaisesRegex(ValueError, "per-bank/package HIRC reference census mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bank_drift)

    def test_reference_graph_closure_is_enforced_not_just_reported(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        closed = aggregate_current_hirc_actions(
            outer, expected_files, excluded_files, audio_audit
        )["referenceGraph"]
        closed = dict(closed, entriesNotReachingCensus=0)
        self.assertTrue(reference_graph_is_closed(closed))
        for field, value in (
            ("entriesNotReachingCensus", 1),
            ("references", 0),
            ("unresolvedInBank", 1),
            ("selfReferences", 1),
            ("targetsWithMultipleReferrers", 1),
            ("referencesToDuplicateIds", 1),
            ("resolvedSameBank", 7),
            ("referenceCycleOrFeedingNodes", 1),
        ):
            regressed = dict(closed)
            regressed[field] = value
            self.assertFalse(
                reference_graph_is_closed(regressed),
                f"{field}={value} must not count as a closed reference graph",
            )

    def test_reference_graph_markdown_refuses_to_name_the_relation(self) -> None:
        report = {
            "status": "complete",
            "inputSetSha256": "A" * 64,
            "outer": {
                "ledgerSha256": "B" * 64,
                "animeStudioCliFingerprint": {
                    "matchesOuterAudit": False,
                    "outerAuditSha256": "C" * 64,
                    "currentSha256": "D" * 64,
                },
            },
            "audioAudit": {
                "toolSha256": "D" * 64,
                "toolClosure": {"fileCount": 79, "manifestSha256": "G" * 64},
                "intermediatePath": "tmp/audio-audit.json",
                "sha256": "E" * 64,
            },
            "corpusGate": {"sha256": "F" * 64},
            "corpus": {
                "packageCount": 1,
                "verifiedPackageCount": 1,
                "excludedBlockCount": 0,
                "referenceGraph": {
                    "closure": "every-reference-names-one-same-bank-object",
                    "references": 6,
                    "resolvedSameBank": 6,
                    "unresolvedInBank": 0,
                    "selfReferences": 0,
                    "targetsWithMultipleReferrers": 0,
                    "duplicateObjectIds": 0,
                    "referencesToDuplicateIds": 0,
                    "candidateWords": 0,
                    "candidateWordsMatchingAnObject": 0,
                    "referenceCycleOrFeedingNodes": 0,
                    "distinctDuplicateObjectIds": 0,
                    "entriesNotReachingCensus": 0,
                    "maximumReferenceDepth": 3,
                    "referenceTargetsByType": {"type03": 2},
                    "objectCountsByType": {"type03": 10, "type04": 5},
                    "edgeCounts": {"type04_to_type03": 2},
                },
            },
        }

        markdown = _reference_graph_markdown(report)

        self.assertIn("Resolution is an identity fact and nothing more", markdown)
        self.assertIn("does not establish direction", markdown)
        self.assertIn("The type pairs are numeric on both sides", markdown)
        # The report must not generalise these vectors' same-bank behaviour to the
        # corpus: type 0x03 targets leave their bank, and that over-generalisation
        # was published once already.
        self.assertIn("not about the corpus", markdown.replace("**", ""))
        self.assertIn("Do not generalise the vectors", markdown)
        # It must also not imply endpoints are nameless, since three types are named.
        self.assertIn("names do exist for some endpoints", markdown)
        # No edge may be rendered with a domain name.
        for word in ("event", "action", "parent", "child", "container", "playlist"):
            self.assertNotIn(f"`{word}", markdown.lower())

    def test_histogram_labels_must_be_physically_possible_widths(self) -> None:
        # A sum-only check accepts impossible buckets: width 0, or {12,12} standing in
        # for {6,18}. The label itself has to be a key plus whole six-byte elements.
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()

        impossible = copy.deepcopy(audio_audit)
        for scope in (
            impossible["rows"][0]["package"],
            impossible["rows"][0]["package"]["bnkStructures"][0],
        ):
            selectors = scope["hircType07BodyFrame"]["selectorCounts"]
            del selectors["groupHStateWidth_12"]
            del selectors["groupHStateWidth_18"]
            selectors["groupHStateWidth_0"] = 2
            selectors["groupHStateWidth_30"] = 1
            scope["hircType07BodyFrame"]["groupCounts"]["groupHStates"] = 3
            scope["hircType07BodyFrame"]["groupCounts"]["groupHStateElements"] = 2
        with self.assertRaisesRegex(ValueError, "not a key plus whole elements"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, impossible)

        malformed = copy.deepcopy(audio_audit)
        for scope in (
            malformed["rows"][0]["package"],
            malformed["rows"][0]["package"]["bnkStructures"][0],
        ):
            selectors = scope["hircType07BodyFrame"]["selectorCounts"]
            # Swap, not add: the count check would otherwise fire first.
            del selectors["groupIKeyWidth_1"]
            selectors["groupIKeyWidth_x"] = 1
        with self.assertRaisesRegex(ValueError, "histogram key is not a plain width"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, malformed)

        out_of_range = copy.deepcopy(audio_audit)
        for scope in (
            out_of_range["rows"][0]["package"],
            out_of_range["rows"][0]["package"]["bnkStructures"][0],
        ):
            selectors = scope["hircType07BodyFrame"]["selectorCounts"]
            del selectors["groupIKeyWidth_2"]
            selectors["groupIKeyWidth_9"] = 1
        with self.assertRaisesRegex(ValueError, "key width is outside the reader's range"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, out_of_range)

        bucketed = copy.deepcopy(audio_audit)
        for scope in (
            bucketed["rows"][0]["package"],
            bucketed["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType07BodyFrame"]["selectorCounts"]["groupHStateWidth_over_54"] = 1
        with self.assertRaisesRegex(ValueError, "histogram is bucketed"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bucketed)

    def test_group_h_state_widths_must_reconcile_with_their_elements(self) -> None:
        # The state was read as a fixed twelve bytes until a two-element sample
        # disproved it, so the census must keep the width histogram honest rather
        # than let a degenerate corpus hide the variable part again.
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        bodies = result["type07BodyFrames"]
        self.assertEqual(bodies["anonymousGroupCounts"]["groupHStates"], 2)
        self.assertEqual(bodies["anonymousGroupCounts"]["groupHStateElements"], 3)
        self.assertEqual(bodies["anonymousSelectorCounts"]["groupHStateWidth_18"], 1)

        miscounted = copy.deepcopy(audio_audit)
        for scope in (
            miscounted["rows"][0]["package"],
            miscounted["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType07BodyFrame"]["selectorCounts"]["groupHStateWidth_12"] = 2
        with self.assertRaisesRegex(ValueError, "state width histogram does not match its state count"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, miscounted)

        inconsistent = copy.deepcopy(audio_audit)
        for scope in (
            inconsistent["rows"][0]["package"],
            inconsistent["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType07BodyFrame"]["groupCounts"]["groupHStateElements"] = 4
        with self.assertRaisesRegex(ValueError, "state width histogram does not sum to its element total"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, inconsistent)

    def test_type05_body_lane_frames_two_independent_vectors(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        bodies = result["type05BodyFrames"]
        self.assertEqual(bodies["count"], 2)
        self.assertEqual(bodies["exact"], 2)
        self.assertEqual(bodies["frameClosure"], "all-bodies-exact")
        self.assertEqual(bodies["minimumPossibleFrameBytes"], 61)
        # The two vectors are counted separately and the mismatch count is measured,
        # not asserted in prose.
        self.assertEqual(bodies["anonymousGroupCounts"]["referenceEntries"], 3)
        self.assertEqual(bodies["anonymousGroupCounts"]["recordEntries"], 2)
        self.assertEqual(bodies["anonymousGroupCounts"]["referenceRecordCountMismatch"], 1)
        self.assertTrue(body_lane_corpus_is_closed(bodies))
        self.assertIn("eight-byte anonymous records", bodies["frameLayout"])

    def test_every_lane_publishes_its_own_layout_and_non_claims(self) -> None:
        # The shared publisher must not flatten what each lane actually consumes, and
        # the type 0x02 lane must keep disclaiming source and cross-bank identity.
        from scripts.audio_semantics.hirc_action_corpus import _build_body_lanes

        lanes = _build_body_lanes()
        self.assertEqual(sorted(lanes), ["0x02", "0x05", "0x06", "0x07", "0x0E", "0x16"])
        layouts = {key: lane.layout for key, lane in lanes.items()}
        self.assertEqual(len(set(layouts.values())), len(lanes))
        self.assertIn("counted list of groups", layouts["0x06"])
        self.assertIn("source prefix", layouts["0x02"])
        self.assertIn("four-byte anonymous references.", layouts["0x07"])
        self.assertIn("twenty-four-byte opaque", layouts["0x05"])
        self.assertIn("source, effect, bus, or parent object identity", lanes["0x02"].non_claims)
        self.assertIn("cross-object or cross-bank relationships", lanes["0x02"].non_claims)
        for lane in lanes.values():
            for shared in (
                "serialized field ownership or field names",
                "runtime execution, event selection, or audibility",
            ):
                self.assertIn(shared, lane.non_claims)

    def test_every_counted_element_has_a_declared_byte_width(self) -> None:
        # A lane that forgets to declare its terminal vector would leave that counter
        # unbounded, which is exactly how a reader-side over-count could hide.
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        undeclared = copy.deepcopy(audio_audit)
        for scope in (
            undeclared["rows"][0]["package"],
            undeclared["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType05BodyFrame"]["groupCounts"]["mysteryEntries"] = 4
        with self.assertRaisesRegex(ValueError, "no declared byte width"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, undeclared)

        oversized = copy.deepcopy(audio_audit)
        for scope in (
            oversized["rows"][0]["package"],
            oversized["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType05BodyFrame"]["groupCounts"]["recordEntries"] = 1_000_000
        with self.assertRaisesRegex(ValueError, "anonymous element bytes exceed the framed bodies"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, oversized)

    def test_media_join_is_decided_by_the_plugin_id(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        media = result["type02MediaJoin"]
        self.assertEqual(media["sourceIds"], 4)
        self.assertEqual(media["sourceIdsNamingMedia"], 2)
        self.assertEqual(media["pluginIdsAlwaysNamingMedia"], 1)
        self.assertEqual(media["pluginIdsNeverNamingMedia"], 1)
        self.assertEqual(media["pluginIdsSplitAcrossBothOutcomes"], [])
        self.assertTrue(media_join_is_decided_by_the_plugin_id(media))

        # One plug-in id landing on both sides falsifies the claim outright; a rate
        # would hide exactly that.
        self.assertFalse(
            media_join_is_decided_by_the_plugin_id(
                {**media, "pluginIdsSplitAcrossBothOutcomes": ["plugin_00040001"]}
            )
        )
        # A partition with nothing on one side asserts nothing.
        self.assertFalse(
            media_join_is_decided_by_the_plugin_id({**media, "pluginIdsNeverNamingMedia": 0})
        )
        self.assertFalse(
            media_join_is_decided_by_the_plugin_id({**media, "pluginIdsAlwaysNamingMedia": 0})
        )

    def test_media_join_detects_a_plugin_id_on_both_sides(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        mixed = copy.deepcopy(audio_audit)
        for scope in (
            mixed["rows"][0]["package"],
            mixed["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircMediaJoin"]["sourceIdsByPlugin"]["plugin_00040001"] = [10, 99]
        media = aggregate_current_hirc_actions(
            outer, expected_files, excluded_files, mixed
        )["type02MediaJoin"]
        self.assertEqual(media["pluginIdsSplitAcrossBothOutcomes"], ["plugin_00040001"])
        self.assertFalse(media_join_is_decided_by_the_plugin_id(media))

    def test_media_join_rejects_a_malformed_census(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        for field, value, pattern in (
            ("mediaEntries", 9, "disagrees with the id list"),
            ("sourceIdsByPlugin", {"nonsense": [1]}, "plug-in key is malformed"),
        ):
            broken = copy.deepcopy(audio_audit)
            for scope in (
                broken["rows"][0]["package"],
                broken["rows"][0]["package"]["bnkStructures"][0],
            ):
                scope["hircMediaJoin"][field] = value
            with self.assertRaisesRegex(ValueError, pattern):
                aggregate_current_hirc_actions(outer, expected_files, excluded_files, broken)

    def test_small_types_need_a_real_width_witness_not_just_exact_bodies(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        small = result["smallTypeBodies"]
        self.assertEqual(small["exact"], 4)
        self.assertEqual(small["bodiesByType"], {"type13": 1, "type14": 2, "type15": 1})
        self.assertTrue(small_types_are_closed(small))

        # Consuming every body exactly is weak on a corpus this small. If no body
        # carries a nonempty second block, the eight-byte value width is unwitnessed
        # and the layout is merely fitted, so that must not pass.
        self.assertFalse(
            small_types_are_closed(
                {**small, "bodiesWithSecondBlock": 0, "secondBlockEntries": 0}
            )
        )
        self.assertFalse(small_types_are_closed({**small, "exact": 3, "failed": 1}))

    def test_small_type_counters_must_reconcile(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        for field, value, pattern in (
            ("exact", 3, "do not partition"),
            ("bodiesWithSecondBlock", 9, "witnesses exceed the bodies"),
            ("exactBytes", 900, "exact bytes exceed"),
        ):
            broken = copy.deepcopy(audio_audit)
            for scope in (
                broken["rows"][0]["package"],
                broken["rows"][0]["package"]["bnkStructures"][0],
            ):
                scope["hircSmallTypes"][field] = value
            with self.assertRaisesRegex(ValueError, pattern):
                aggregate_current_hirc_actions(outer, expected_files, excluded_files, broken)

    def test_type03_targets_are_shown_to_cross_bank_boundaries(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        t03 = result["type03Targets"]
        self.assertEqual(t03["sameBank"], 6)
        self.assertEqual(t03["otherBankInPackage"], 2)
        self.assertTrue(type03_targets_cross_bank_boundaries(t03))

        # The reference vectors never leave their bank and that was once recorded as
        # a property of the corpus. If a future reader reports no crossing here, the
        # old conclusion must not quietly come back.
        self.assertFalse(
            type03_targets_cross_bank_boundaries({**t03, "otherBankInPackage": 0})
        )
        self.assertFalse(type03_targets_cross_bank_boundaries({**t03, "sameBank": 0}))

    def test_type03_target_outcomes_must_partition_and_sum(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        for field, value, pattern in (
            ("sameBank", 5, "do not partition"),
            ("sameBankByActionByte", {"action_03": 1}, "does not sum to its outcome"),
        ):
            broken = copy.deepcopy(audio_audit)
            for scope in (
                broken["rows"][0]["package"],
                broken["rows"][0]["package"]["bnkStructures"][0],
            ):
                scope["hircType03Targets"][field] = value
            with self.assertRaisesRegex(ValueError, pattern):
                aggregate_current_hirc_actions(outer, expected_files, excluded_files, broken)

    def test_type09_is_framed_or_fenced_and_flags_match_exact_bodies(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        bodies = result["type09Bodies"]
        self.assertEqual(bodies["exact"], 4)
        self.assertEqual(bodies["unestablishedSecondRun"], 1)
        self.assertTrue(type09_is_framed_except_the_second_run(bodies))
        self.assertFalse(
            type09_is_framed_except_the_second_run({**bodies, "exact": 3, "failed": 1})
        )

        # One tail flag is read per exactly framed body and nowhere else, so the
        # histogram cannot drift from the exact count.
        broken = copy.deepcopy(audio_audit)
        for scope in (
            broken["rows"][0]["package"],
            broken["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType09"]["tailFlagCounts"] = {"tail_00": 9}
        with self.assertRaisesRegex(ValueError, "tail flags do not match"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, broken)

        partition = copy.deepcopy(audio_audit)
        for scope in (
            partition["rows"][0]["package"],
            partition["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType09"]["unestablishedSecondRun"] = 0
        with self.assertRaisesRegex(ValueError, "do not partition"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, partition)

    def test_type17_is_framed_or_fenced_never_failed(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        bodies = result["type17Bodies"]
        self.assertEqual(bodies["exact"], 4)
        # A tied width is its own outcome, not a failure and not a pass.
        self.assertEqual(bodies["fenced"], 1)
        self.assertEqual(bodies["bodiesByType"], {"type10": 2, "type11": 3})
        self.assertTrue(type17_is_framed_except_the_tied_block(bodies))

        # A real failure is never acceptable, even one.
        self.assertFalse(
            type17_is_framed_except_the_tied_block({**bodies, "exact": 3, "failed": 1})
        )
        # Fencing everything would make the claim vacuous.
        self.assertFalse(
            type17_is_framed_except_the_tied_block({**bodies, "exact": 0, "fenced": 5})
        )

    def test_type17_outcomes_must_partition_and_bytes_must_fit(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        for field, value, pattern in (
            ("exact", 3, "do not partition"),
            ("exactBytes", 500, "exact bytes exceed"),
        ):
            broken = copy.deepcopy(audio_audit)
            for scope in (
                broken["rows"][0]["package"],
                broken["rows"][0]["package"]["bnkStructures"][0],
            ):
                scope["hircType17"][field] = value
            with self.assertRaisesRegex(ValueError, pattern):
                aggregate_current_hirc_actions(outer, expected_files, excluded_files, broken)

        mismatched = copy.deepcopy(audio_audit)
        for scope in (
            mismatched["rows"][0]["package"],
            mismatched["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType17"]["failureCounts"] = {"trailing_bytes": 2}
        with self.assertRaisesRegex(ValueError, "do not sum to the failures"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, mismatched)

        # A fenced body without a stated reason is indistinguishable from one that
        # was quietly dropped, so the reasons must account for every fence.
        unreasoned = copy.deepcopy(audio_audit)
        for scope in (
            unreasoned["rows"][0]["package"],
            unreasoned["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType17"]["fenceReasons"] = {}
        with self.assertRaisesRegex(ValueError, "fence reasons do not sum"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, unreasoned)

        wrong_types = copy.deepcopy(audio_audit)
        for scope in (
            wrong_types["rows"][0]["package"],
            wrong_types["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType17"]["bodiesByType"] = {"type11": 3}
        with self.assertRaisesRegex(ValueError, "per-type counts disagree"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, wrong_types)

    def test_type08_head_word_is_null_or_names_one_object(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        head = result["type08HeadWords"]
        self.assertEqual(head["bodies"], 3)
        self.assertEqual(head["resolved"], 2)
        # Null is an allowed outcome; it is what the claim explicitly permits.
        self.assertEqual(head["null"], 1)
        self.assertTrue(type08_head_words_are_null_or_resolve(head))

        # A non-null word that names nothing is the case the claim forbids.
        self.assertFalse(
            type08_head_words_are_null_or_resolve({**head, "resolved": 1, "unresolved": 1})
        )
        self.assertFalse(
            type08_head_words_are_null_or_resolve({**head, "resolved": 1, "tooShort": 1})
        )
        # All-null would make the claim vacuous, so it does not count as closed.
        self.assertFalse(
            type08_head_words_are_null_or_resolve(
                {"bodies": 3, "resolved": 0, "null": 3, "unresolved": 0, "tooShort": 0}
            )
        )

    def test_type08_head_outcomes_must_partition_the_bodies(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        broken = copy.deepcopy(audio_audit)
        for scope in (
            broken["rows"][0]["package"],
            broken["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType08Head"]["null"] = 0
        with self.assertRaisesRegex(ValueError, "do not partition"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, broken)

    def test_type11_sources_must_use_a_plugin_id_type02_also_uses(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        sources = result["type11SourceRecords"]
        known = result["type02SourcePrefixes"]["pluginIdCounts"]
        self.assertEqual(sources["records"], 3)
        self.assertTrue(type11_sources_share_the_type02_plugin_space(sources, known))

        # A plug-in id outside the set means the record stride is wrong, because a
        # correct stride cannot land arbitrary bytes on a sparse 32-bit id.
        self.assertFalse(
            type11_sources_share_the_type02_plugin_space(
                {**sources, "pluginIdCounts": {**sources["pluginIdCounts"], "plugin_DEADBEEF": 1}},
                known,
            )
        )
        for field in ("recordsOutOfRange", "tooShort"):
            self.assertFalse(
                type11_sources_share_the_type02_plugin_space({**sources, field: 1}, known)
            )
        self.assertFalse(type11_sources_share_the_type02_plugin_space(sources, {}))
        self.assertFalse(
            type11_sources_share_the_type02_plugin_space({**sources, "records": 0}, known)
        )

    def test_the_type0a_word_five_never_names_a_local_object(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        head = result["type0AHead"]
        self.assertTrue(the_type0a_word_five_points_outside_its_package(head))

        # One local resolution would make this an ordinary reference rather than the
        # cross-package one the corpus join shows it to be.
        self.assertFalse(
            the_type0a_word_five_points_outside_its_package({**head, "wordFiveInPackage": 1})
        )
        # No nonzero words means nothing was tested, which is not the same as a
        # negative result.
        self.assertFalse(
            the_type0a_word_five_points_outside_its_package(
                {**head, "wordFiveNonZero": 0, "wordFiveValues": {}}
            )
        )
        # The histogram has to account for every nonzero word.
        self.assertFalse(
            the_type0a_word_five_points_outside_its_package({**head, "wordFiveNonZero": 9})
        )

    def test_the_type0a_head_float_beats_an_overlapping_control_window(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        head = result["type0AHead"]
        self.assertTrue(the_type0a_head_carries_a_bounded_whole_float(head))

        # The control window overlaps the field by two bytes, which is the hardest
        # control to pass. If it carried whole values in range too, the reader would
        # be finding a property of the neighbourhood rather than of the field.
        self.assertFalse(
            the_type0a_head_carries_a_bounded_whole_float({**head, "decibelControlsInRange": 40})
        )
        self.assertFalse(
            the_type0a_head_carries_a_bounded_whole_float({**head, "decibelsWhole": 5})
        )
        # Counting more whole values than bodies is incoherent.
        self.assertFalse(
            the_type0a_head_carries_a_bounded_whole_float({**head, "decibelsWhole": 101})
        )
        self.assertFalse(
            the_type0a_head_carries_a_bounded_whole_float({**head, "decibelBodies": 0})
        )

    def test_the_type0a_tail_word_reads_as_a_fraction_and_its_control_does_not(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        head = result["type0AHead"]
        self.assertTrue(the_type0a_tail_word_is_a_fixed_point_fraction(head))

        # A test that accepted any 32-bit value would accept the control too, so the
        # control failing is what makes the result mean anything.
        self.assertFalse(
            the_type0a_tail_word_is_a_fixed_point_fraction(
                {**head, "fractionControlsWithASmallDenominator": 150}
            )
        )
        self.assertFalse(
            the_type0a_tail_word_is_a_fixed_point_fraction(
                {**head, "fractionsWithASmallDenominator": 20}
            )
        )
        # Claiming more hits than candidates is incoherent, not merely wrong.
        self.assertFalse(
            the_type0a_tail_word_is_a_fixed_point_fraction(
                {**head, "fractionsWithASmallDenominator": 101}
            )
        )
        self.assertFalse(
            the_type0a_tail_word_is_a_fixed_point_fraction({**head, "fractionControls": 0})
        )

    def test_the_type0a_tail_float_must_be_whole_far_more_often_than_bounded(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        head = result["type0AHead"]
        self.assertTrue(the_type0a_tail_float_is_an_authored_value(head))

        # Whole numbers are the strong property: a computed float lands on exact
        # integers by accident, so a drop there has to fail even while the band holds.
        self.assertFalse(
            the_type0a_tail_float_is_an_authored_value({**head, "tailFloatsWhole": 80})
        )
        # The band is the weaker property and is checked at a lower bar, because the
        # outliers are real -- but it still has to hold.
        self.assertFalse(
            the_type0a_tail_float_is_an_authored_value({**head, "tailFloatsInBand": 50})
        )
        # A census claiming more whole or in-band values than floats it read is
        # incoherent rather than merely wrong.
        self.assertFalse(
            the_type0a_tail_float_is_an_authored_value({**head, "tailFloatsWhole": 101})
        )
        self.assertFalse(the_type0a_tail_float_is_an_authored_value({**head, "tailFloats": 0}))
        # The neighbour twelve bytes earlier is the control for the offset itself. If
        # it behaved the same way, the reader would be slicing one quantity at two
        # arbitrary places rather than reading two fields.
        self.assertFalse(
            the_type0a_tail_float_is_an_authored_value({**head, "neighbourFloatsWhole": 99})
        )
        self.assertFalse(
            the_type0a_tail_float_is_an_authored_value({**head, "neighbourFloats": 0})
        )

    def test_the_type0a_reference_is_an_optional_four_byte_field(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        head = result["type0AHead"]
        self.assertTrue(the_type0a_reference_is_an_optional_four_byte_field(head))

        # The whole point is the four-byte difference. Any other gap means the bodies
        # without a reference differ in something else as well.
        self.assertFalse(
            the_type0a_reference_is_an_optional_four_byte_field(
                {**head, "tailBytesByOutcome": {"withReference_69": 8, "withoutReference_61": 2}}
            )
        )
        # Bodies with a reference may take many tail lengths -- the tail past the
        # reference is not claimed -- so several must not break it.
        self.assertTrue(
            the_type0a_reference_is_an_optional_four_byte_field(
                {**head, "tailBytesByOutcome":
                    {"withReference_69": 8, "withReference_73": 3, "withoutReference_65": 2}}
            )
        )
        # Bodies without one must concentrate on a single length.
        self.assertFalse(
            the_type0a_reference_is_an_optional_four_byte_field(
                {**head, "tailBytesByOutcome":
                    {"withReference_69": 8, "withoutReference_65": 2, "withoutReference_39": 2}}
            )
        )
        self.assertFalse(
            the_type0a_reference_is_an_optional_four_byte_field(
                {**head, "tailBytesByOutcome": {"withReference_69": 8}}
            )
        )

    def test_the_type0a_head_elements_are_a_zero_byte_a_small_value_and_padding(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        head = result["type0AHead"]
        self.assertEqual(head["elementTotal"], 6)
        self.assertTrue(the_type0a_head_elements_are_padded_small_values(head))

        # One element breaking the shape means the element boundary is wrong, so
        # these are equalities and not rates.
        self.assertFalse(
            the_type0a_head_elements_are_padded_small_values(
                {**head, "elementLeadingByteNotZero": 1}
            )
        )
        self.assertFalse(
            the_type0a_head_elements_are_padded_small_values({**head, "elementPadNotZero": 1})
        )
        # A value outside the small range would mean the field is an id or a length
        # rather than the enumeration it looks like.
        self.assertFalse(
            the_type0a_head_elements_are_padded_small_values(
                {**head, "elementValueCounts": {"value_0": 2, "value_1": 3, "value_46456": 1}}
            )
        )
        # The histogram has to cover every element the census counted.
        self.assertFalse(
            the_type0a_head_elements_are_padded_small_values({**head, "elementTotal": 9})
        )
        self.assertFalse(
            the_type0a_head_elements_are_padded_small_values(
                {**head, "elementTotal": 0, "elementValueCounts": {}}
            )
        )

    def test_the_type0a_head_word_names_exactly_two_types(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        head = result["type0AHead"]
        self.assertTrue(the_type0a_head_word_always_names_one_of_two_types(head))

        # A third target type is a wider finding than this one, so it fails here
        # rather than being absorbed into it.
        self.assertFalse(
            the_type0a_head_word_always_names_one_of_two_types(
                {**head, "headWordTargets": {"type0D": 6, "type0C": 2, "type0B": 1}}
            )
        )
        # Unresolved words are permitted -- the corpus has 1 in 4,000 -- but only at
        # that rate. At this fixture's scale one unresolved body is more than 1%, so
        # the same shape that passes on the corpus fails here, which is the threshold
        # doing its job rather than a quirk.
        self.assertFalse(
            the_type0a_head_word_always_names_one_of_two_types(
                {**head, "headWordTargets": {"type0D": 7, "type0C": 1, "nothing": 1}}
            )
        )
        self.assertTrue(
            the_type0a_head_word_always_names_one_of_two_types(
                {**head, "bodiesWhereTheRuleApplies": 1000,
                 "headWordTargets": {"type0D": 900, "type0C": 99, "nothing": 1}}
            )
        )
        self.assertFalse(
            the_type0a_head_word_always_names_one_of_two_types(
                {**head, "headWordTargets": {"type0D": 3, "nothing": 6}}
            )
        )
        self.assertFalse(
            the_type0a_head_word_always_names_one_of_two_types({**head, "headWordTargets": {}})
        )

    def test_the_type0a_head_rule_must_beat_a_fixed_offset_and_its_neighbours(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        head = result["type0AHead"]
        self.assertTrue(the_type0a_head_rule_beats_its_controls(head))

        # A formula that lands on a reference nine times in ten might just be finding
        # a reference that is always nearby. If ignoring the count scores as well,
        # the count is not what places it.
        self.assertFalse(
            the_type0a_head_rule_beats_its_controls(
                {**head, "namesTheSourceType": {**head["namesTheSourceType"], "fixedOffset": 9}}
            )
        )
        # Same for a neighbour: naming the neighbourhood is not naming the place.
        self.assertFalse(
            the_type0a_head_rule_beats_its_controls(
                {**head, "namesTheSourceType": {**head["namesTheSourceType"], "predictedPlusFour": 8}}
            )
        )
        # And the rule itself has to clear a high bar, not merely beat the controls.
        self.assertFalse(
            the_type0a_head_rule_beats_its_controls(
                {**head, "namesTheSourceType": {**head["namesTheSourceType"], "predicted": 4}}
            )
        )
        self.assertFalse(the_type0a_head_rule_beats_its_controls({**head, "bodies": 0}))
        # The unconditioned rate can clear its bar while the conditioned one does not,
        # and the conditioned one is the claim.
        self.assertFalse(
            the_type0a_head_rule_beats_its_controls(
                {**head, "namesTheSourceTypeWhereTheRuleApplies":
                    {**head["namesTheSourceTypeWhereTheRuleApplies"], "predicted": 4}}
            )
        )
        self.assertFalse(
            the_type0a_head_rule_beats_its_controls({**head, "bodiesWhereTheRuleApplies": 0})
        )

    def test_a_type0a_head_census_scoring_above_its_bodies_is_refused(self) -> None:
        _, _, _, audio_audit = valid_action_fixture()
        census = audio_audit["rows"][0]["package"]["hircType0AHead"]
        with self.assertRaisesRegex(ValueError, "above its bodies"):
            _read_type0a_head_census({**census, "bodies": 2, "bodiesWhereTheRuleApplies": 2}, "unit")
        with self.assertRaisesRegex(ValueError, "applies to more bodies than it has"):
            _read_type0a_head_census({**census, "bodiesWhereTheRuleApplies": 99}, "unit")

    def test_the_music_reference_position_must_be_concentrated_to_be_an_anchor(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        refs = result["musicReferences"]
        self.assertTrue(the_music_partition_edge_sits_at_a_few_places(refs))

        # A reference scattered over dozens of distances is still a reference and
        # still passes every other music check. It is just not an anchor, and an
        # anchor is the only thing this measurement exists to provide.
        scattered = {f"type0A_to_type0B_at-{n}": 1 for n in range(40)}
        self.assertFalse(
            the_music_partition_edge_sits_at_a_few_places(
                {**refs, "edgeDistanceFromEnd": scattered}
            )
        )
        # Positions recorded for other edges must not be counted toward this one.
        self.assertFalse(
            the_music_partition_edge_sits_at_a_few_places(
                {**refs, "edgeDistanceFromEnd": {"type0C_to_type0D_at-40": 5}}
            )
        )

    def test_the_one_to_one_music_edge_needs_all_three_conditions(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        refs = result["musicReferences"]
        self.assertTrue(the_music_partition_edge_is_one_to_one(refs))

        # An edge total equal to a population is not evidence of a bijection -- the
        # 0x0D -> 0x0C edge has exactly that and reaches 578 of 742 objects. Reaching
        # every object still is not enough either: 0x0C -> 0x0D reaches all of its
        # targets and reaches 1,628 of them twice.
        self.assertFalse(
            the_music_partition_edge_is_one_to_one(
                {**refs, "targetsReachedTwice": {"type0A_to_type0B": 1}}
            )
        )
        # Leaving objects unreached breaks it from the other side.
        self.assertFalse(
            the_music_partition_edge_is_one_to_one(
                {**refs, "distinctTargets": {"type0A_to_type0B": 3}}
            )
        )
        # And an edge total above the distinct count means some source named a target
        # twice even if no target was reached twice overall.
        self.assertFalse(
            the_music_partition_edge_is_one_to_one(
                {**refs, "edgeCounts": {"type0A_to_type0B": 5}}
            )
        )
        self.assertFalse(the_music_partition_edge_is_one_to_one({**refs, "edgeCounts": {}}))

    def test_every_music_body_must_carry_at_least_one_reference(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        refs = result["musicReferences"]
        self.assertEqual(refs["bodiesWithNoReference"], 0)
        self.assertTrue(music_bodies_all_carry_references(refs))

        # A total can be carried by a few reference-rich bodies; "every one of them"
        # cannot, and it is the claim.
        self.assertFalse(
            music_bodies_all_carry_references({**refs, "bodiesWithNoReference": 1})
        )
        # Every word of every body is offered, so the chance expectation is not
        # negligible and has to be beaten by a wide margin, not merely exceeded.
        self.assertFalse(
            music_bodies_all_carry_references(
                {**refs, "wordsOffered": 10 ** 9, "packagePopulation": 10 ** 6}
            )
        )
        # Without target types the edges say nothing about the relationships.
        self.assertFalse(music_bodies_all_carry_references({**refs, "edgeCounts": {}}))
        self.assertFalse(music_bodies_all_carry_references({**refs, "references": 0}))

    def test_a_music_reference_census_that_loses_a_body_is_refused(self) -> None:
        _, _, _, audio_audit = valid_action_fixture()
        census = audio_audit["rows"][0]["package"]["hircMusicReferences"]
        with self.assertRaisesRegex(ValueError, "does not cover its bodies"):
            _read_music_reference_census({**census, "bodies": 9}, "unit")
        with self.assertRaisesRegex(ValueError, "edges exceed its references"):
            _read_music_reference_census({**census, "references": 1}, "unit")
        with self.assertRaisesRegex(ValueError, "resolves more words than it offered"):
            _read_music_reference_census({**census, "wordsOffered": 2}, "unit")

    def test_music_tail_words_are_judged_only_when_names_were_supplied(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        music = result["musicHeadReferences"]
        self.assertEqual(music["tailWordsNamed"], 3)
        self.assertTrue(music_tail_words_are_named(music))

        # A census with nothing tested means the question was never asked -- this
        # corpus gate's reader run does not load the metadata literals. That must
        # skip, not fail, and it must not be read as the answer being no either.
        self.assertTrue(
            music_tail_words_are_named(
                {**music, "tailWordsTested": 0, "tailWordsNamed": 0,
                 "tailWordNamedByOffset": {}}
            )
        )
        # Asked and answered no, though, is a failure: name hashes are sparse enough
        # that hundreds of matches cannot be chance, so zero is not the shape of this
        # finding.
        self.assertFalse(
            music_tail_words_are_named(
                {**music, "tailWordsNamed": 0, "tailWordNamedByOffset": {}}
            )
        )
        # A handful of matches in a corpus this size is the one thing chance could
        # produce, so the rate has to be clear of zero rather than merely nonzero.
        self.assertFalse(
            music_tail_words_are_named(
                {**music, "tailWordsTested": 4000, "tailWordsNamed": 3}
            )
        )
        # The per-offset histogram has to account for every match claimed.
        self.assertFalse(
            music_tail_words_are_named({**music, "tailWordNamedByOffset": {"minus12": 1}})
        )

    def test_type11_entries_carry_the_shared_twelve_byte_curve_record(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        sources = result["type11SourceRecords"]
        self.assertEqual(sources["curveRecords"], 2)
        self.assertTrue(type11_entries_carry_the_shared_curve_record(sources))

        # The interpolation code is the discriminator. Read at a wrong offset it
        # would be arbitrary 32-bit noise, so one wild value means the records are
        # not where the reader thinks they are.
        self.assertFalse(
            type11_entries_carry_the_shared_curve_record(
                {**sources, "interpolationCounts": {"interp_1": 1, "interp_305419896": 1}}
            )
        )
        # Nothing read proves nothing about the offset.
        self.assertFalse(
            type11_entries_carry_the_shared_curve_record(
                {**sources, "entriesWhoseRecordsFit": 0, "curveRecords": 0,
                 "interpolationCounts": {}}
            )
        )
        # The histogram has to account for every record the census claims to have read.
        self.assertFalse(
            type11_entries_carry_the_shared_curve_record({**sources, "curveRecords": 9})
        )

    def test_every_type11_body_must_end_on_the_same_word(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        sources = result["type11SourceRecords"]
        self.assertEqual(sources["endsWithTerminator"], sources["bodies"])
        self.assertEqual(sources["terminatorCounts"], {"end_00000064": 2})
        self.assertTrue(type11_bodies_share_one_terminator(sources))

        # One body ending on a different word means the reader is looking at a
        # different layout, so a majority is not enough -- the count must be exact.
        self.assertFalse(
            type11_bodies_share_one_terminator(
                {**sources, "endsWithTerminator": 1,
                 "terminatorCounts": {"end_00000064": 1, "end_00000000": 1}}
            )
        )
        # A second word present alongside the terminator still breaks it, even if
        # every body is somehow counted as terminated.
        self.assertFalse(
            type11_bodies_share_one_terminator(
                {**sources, "terminatorCounts": {"end_00000064": 2, "end_00000001": 1}}
            )
        )
        # An empty corpus must not satisfy the claim vacuously.
        self.assertFalse(
            type11_bodies_share_one_terminator(
                {"bodies": 0, "endsWithTerminator": 0, "terminatorCounts": {}}
            )
        )

    def test_a_type11_census_whose_terminators_miss_bodies_is_refused(self) -> None:
        # Terminator counts that do not cover every body mean some body was walked
        # without being classified, which would let an unread shape pass as closed.
        _, _, _, audio_audit = valid_action_fixture()
        census = audio_audit["rows"][0]["package"]["hircType11Sources"]
        with self.assertRaisesRegex(ValueError, "do not cover every body"):
            _read_type11_source_census(
                {**census, "terminatorCounts": {"end_00000064": 1}}, "unit"
            )
        with self.assertRaisesRegex(ValueError, "more terminators than bodies"):
            _read_type11_source_census({**census, "endsWithTerminator": 9}, "unit")

    def test_type12_tails_are_located_by_the_same_check_as_type08(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        tail = result["type12TailRecords"]
        self.assertTrue(type12_tail_records_are_located_by_a_unique_count(tail))
        # One check, two types, because it is one structure. An ambiguous count has to
        # break it for either type.
        self.assertFalse(
            type12_tail_records_are_located_by_a_unique_count({**tail, "countIsAmbiguous": 1})
        )
        # Sharing a layout does not make the same field mean the same thing: this
        # type's tail-head words resolve nowhere, and the report must say so rather
        # than inherit 0x08's finding.
        words = result["type12TailHeadWords"]
        self.assertEqual(words["firstWordTargetTypeCounts"], {})
        self.assertEqual(words["secondWordResolves"], 0)

    def test_a_type12_tail_census_names_its_own_type_when_it_refuses(self) -> None:
        _, _, _, audio_audit = valid_action_fixture()
        census = audio_audit["rows"][0]["package"]["hircType12Tail"]
        with self.assertRaisesRegex(ValueError, "type 0x12 tail outcomes do not partition"):
            _read_type12_tail_census({**census, "bodies": 9}, "unit")

    def test_the_type08_tail_head_word_must_beat_its_own_control(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        words = result["type08TailHeadWords"]
        self.assertEqual(words["firstWordTargetTypeCounts"], {"type12": 1})
        self.assertTrue(type08_tail_head_names_one_object_type(words))

        # The control is the whole test. A 32-bit value read at an arbitrary offset
        # would resolve at the same rate as the field under test, so the control
        # resolving even once means the hits prove nothing.
        self.assertFalse(
            type08_tail_head_names_one_object_type({**words, "secondWordResolves": 1})
        )
        # No resolution at all is not evidence of a reference.
        self.assertFalse(
            type08_tail_head_names_one_object_type(
                {**words, "firstWordSameBank": 0, "firstWordOutsidePackage": 1,
                 "firstWordTargetTypeCounts": {}}
            )
        )
        # A second target type would be a wider claim than this one, so it must fail
        # rather than be quietly absorbed.
        self.assertFalse(
            type08_tail_head_names_one_object_type(
                {**words, "firstWordTargetTypeCounts": {"type12": 1, "type02": 1}}
            )
        )
        self.assertFalse(type08_tail_head_names_one_object_type({**words, "heads": 0}))

    def test_a_type08_tail_word_census_that_loses_a_word_is_refused(self) -> None:
        _, _, _, audio_audit = valid_action_fixture()
        census = audio_audit["rows"][0]["package"]["hircType08TailWords"]
        with self.assertRaisesRegex(ValueError, "do not partition its heads"):
            _read_type08_tail_word_census({**census, "heads": 4}, "unit")
        with self.assertRaisesRegex(ValueError, "do not cover its resolved words"):
            _read_type08_tail_word_census({**census, "firstWordTargetTypeCounts": {}}, "unit")
        with self.assertRaisesRegex(ValueError, "do not cover its resolved controls"):
            _read_type08_tail_word_census({**census, "secondWordResolves": 2}, "unit")

    def test_the_type08_tail_run_must_be_located_unambiguously(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        tail = result["type08TailRecords"]
        self.assertEqual((tail["tails"], tail["tailsWithAUniqueCount"]), (1, 1))
        self.assertTrue(type08_tail_records_are_located_by_a_unique_count(tail))

        # Two lengths that both fit make the alignment arithmetic rather than
        # evidence, so a single ambiguous tail has to break the claim.
        self.assertFalse(
            type08_tail_records_are_located_by_a_unique_count({**tail, "countIsAmbiguous": 1})
        )
        # The third field is the discriminator: read at a wrong offset it would be
        # arbitrary 32-bit noise, so a large value means the run is not where the
        # reader thinks it is.
        self.assertFalse(
            type08_tail_records_are_located_by_a_unique_count(
                {**tail, "thirdFieldCounts": {"code_4": 1, "code_305419896": 1}}
            )
        )
        # Nothing located proves nothing, and neither does a corpus with no tails.
        self.assertFalse(
            type08_tail_records_are_located_by_a_unique_count(
                {**tail, "tailsWithAUniqueCount": 0, "noCountBeforeTheRecords": 1}
            )
        )
        self.assertFalse(type08_tail_records_are_located_by_a_unique_count({**tail, "tails": 0}))
        # The code histogram has to account for every record it claims to have read.
        self.assertFalse(
            type08_tail_records_are_located_by_a_unique_count({**tail, "records": 9})
        )

    def test_a_type08_tail_census_that_loses_a_tail_is_refused(self) -> None:
        _, _, _, audio_audit = valid_action_fixture()
        census = audio_audit["rows"][0]["package"]["hircType08Tail"]
        with self.assertRaisesRegex(ValueError, "do not partition its bodies"):
            _read_type08_tail_census({**census, "bodies": 9}, "unit")
        with self.assertRaisesRegex(ValueError, "do not partition its tails"):
            _read_type08_tail_census({**census, "tails": 2, "bodies": 4}, "unit")
        with self.assertRaisesRegex(ValueError, "do not cover its tails"):
            _read_type08_tail_census({**census, "recordCountCounts": {}}, "unit")
        with self.assertRaisesRegex(ValueError, "do not cover its records"):
            _read_type08_tail_census({**census, "thirdFieldCounts": {"code_4": 1}}, "unit")

    def test_type12_bodies_must_be_framed_or_named(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        body = result["type12BodyFrames"]
        self.assertEqual((body["count"], body["exact"], body["failed"]), (4, 3, 1))
        self.assertTrue(type12_bodies_are_exact_or_named(body))
        # The second-list keys this type uses are published so the width table is
        # visible in the report rather than only in the reader.
        self.assertEqual(body["selectorCounts"]["secondListKey_0A"], 1)

        # 0x12 shares 0x08's gate because it shares 0x08's layout; it must reject the
        # same three shapes -- a body neither framed nor accounted for, an ambiguous
        # body, and a corpus where nothing framed.
        self.assertFalse(type12_bodies_are_exact_or_named({**body, "count": 5}))
        self.assertFalse(type12_bodies_are_exact_or_named({**body, "ambiguous": 1, "count": 5}))
        self.assertFalse(
            type12_bodies_are_exact_or_named(
                {**body, "exact": 0, "failed": 4,
                 "failureCategories": {"trailer_is_not_five_bytes": 4}}
            )
        )

    def test_a_type12_body_census_that_loses_a_body_is_refused(self) -> None:
        _, _, _, audio_audit = valid_action_fixture()
        census = audio_audit["rows"][0]["package"]["hircType12BodyFrame"]
        # The message has to name the type: two types share this reader, and a failure
        # that does not say which one broke is not actionable.
        with self.assertRaisesRegex(ValueError, "type 0x12 body outcomes do not partition"):
            _read_type12_body_frame({**census, "count": 9}, "unit")
        with self.assertRaisesRegex(ValueError, "type 0x12 failure categories"):
            _read_type12_body_frame({**census, "failureCategories": {}}, "unit")

    def test_type08_bodies_must_be_framed_or_named(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        body = result["type08BodyFrames"]
        self.assertEqual((body["count"], body["exact"], body["failed"]), (3, 2, 1))
        self.assertTrue(type08_bodies_are_exact_or_named(body))

        # This type does not close, so the gate cannot require every body to frame.
        # What it must reject is a body that is neither framed nor accounted for.
        self.assertFalse(type08_bodies_are_exact_or_named({**body, "count": 4}))
        # An all-fenced corpus proves nothing about the layout and must not pass.
        self.assertFalse(
            type08_bodies_are_exact_or_named(
                {**body, "exact": 0, "failed": 3,
                 "failureCategories": {"trailer_is_not_five_bytes": 3}}
            )
        )
        # An ambiguous body means the framer could not decide, which is not the same
        # as a named fence and must not be counted as one.
        self.assertFalse(type08_bodies_are_exact_or_named({**body, "ambiguous": 1, "count": 4}))
        # A fence without a reason hides whatever shape the framer did not handle.
        self.assertFalse(type08_bodies_are_exact_or_named({**body, "failureCategories": {}}))
        self.assertFalse(type08_bodies_are_exact_or_named({"count": 0, "exact": 0}))

    def test_a_type08_body_census_that_loses_a_body_is_refused(self) -> None:
        _, _, _, audio_audit = valid_action_fixture()
        census = audio_audit["rows"][0]["package"]["hircType08BodyFrame"]
        with self.assertRaisesRegex(ValueError, "do not partition"):
            _read_type08_body_frame({**census, "count": 9}, "unit")
        with self.assertRaisesRegex(ValueError, "do not cover its failures"):
            _read_type08_body_frame({**census, "failureCategories": {}}, "unit")
        with self.assertRaisesRegex(ValueError, "negative"):
            _read_type08_body_frame({**census, "exact": -1}, "unit")

    def test_the_type11_tail_count_must_be_carried_by_the_echoes(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        sources = result["type11SourceRecords"]
        self.assertTrue(type11_tail_entries_are_counted(sources))

        # More echoes than the count declares means the field is not a count, so a
        # single such body has to break it.
        self.assertFalse(
            type11_tail_entries_are_counted({**sources, "tailEchoesExceedTheCount": 1})
        )
        # A body whose first entry does not name a declared source leaves the start
        # of the run unfixed; that is the evidence the offset rests on.
        self.assertFalse(
            type11_tail_entries_are_counted(
                {**sources, "firstTailEntryNamesADeclaredSource": 1}
            )
        )
        self.assertFalse(
            type11_tail_entries_are_counted({**sources, "firstTailEntryTooShort": 1})
        )
        self.assertFalse(
            type11_tail_entries_are_counted({**sources, "tailCountOutOfRange": 1})
        )
        # The histogram has to account for every body with a tail, or some body was
        # walked without being classified.
        self.assertFalse(
            type11_tail_entries_are_counted(
                {**sources, "tailEntryCountCounts": {"tailEntries_1": 1}}
            )
        )
        # Fewer echoes than declared is permitted -- later entries are variable-width
        # so their ids need not land on a four-byte boundary -- and must not fail.
        self.assertTrue(
            type11_tail_entries_are_counted({**sources, "tailEntriesEchoed": 2})
        )
        # A corpus where every body declares zero entries proves nothing about where
        # entries begin, so it must not pass vacuously.
        self.assertFalse(
            type11_tail_entries_are_counted(
                {
                    **sources,
                    "tailEntryCountCounts": {"tailEntries_0": 2},
                    "firstTailEntryNamesADeclaredSource": 0,
                }
            )
        )
        self.assertFalse(type11_tail_entries_are_counted({**sources, "bodiesWithATail": 0}))

    def test_a_type11_census_that_echoes_more_than_it_declares_is_refused(self) -> None:
        _, _, _, audio_audit = valid_action_fixture()
        census = audio_audit["rows"][0]["package"]["hircType11Sources"]
        with self.assertRaisesRegex(ValueError, "echoes more tail entries"):
            _read_type11_source_census({**census, "tailEntriesEchoed": 99}, "unit")
        with self.assertRaisesRegex(ValueError, "tail outcomes exceed the body count"):
            _read_type11_source_census({**census, "noTailAfterTheRun": 99}, "unit")

    def test_type11_histograms_must_sum_to_the_record_total(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        for field in ("pluginIdCounts", "streamTypeCounts"):
            broken = copy.deepcopy(audio_audit)
            for scope in (
                broken["rows"][0]["package"],
                broken["rows"][0]["package"]["bnkStructures"][0],
            ):
                scope["hircType11Sources"][field] = {"x_01": 1}
            with self.assertRaisesRegex(ValueError, "do not sum to the record total"):
                aggregate_current_hirc_actions(outer, expected_files, excluded_files, broken)

    def test_music_head_references_resolve_for_every_body(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        head = result["musicHeadReferences"]
        self.assertEqual(head["bodies"], 4)
        self.assertEqual(head["resolved"], 3)
        self.assertEqual(head["unknownHeadShape"], 1)
        self.assertEqual(head["bodiesByType"], {"type0A": 2, "type0C": 1, "type0D": 1})
        # A body outside the claim is excluded from the numerator and kept in the
        # published total, so the shortfall stays visible rather than vanishing.
        self.assertTrue(music_head_references_are_closed(head))
        self.assertFalse(
            music_head_references_are_closed({**head, "unknownHeadShape": 0})
        )

    def test_a_single_unnamed_body_stops_the_music_head_claim(self) -> None:
        # The claim is that every body names a same-bank object. One that does not
        # falsifies it outright, so none of these outcomes may be tolerated.
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        for field in ("unresolved", "zero", "unknownDiscriminant", "tooShort"):
            broken = copy.deepcopy(audio_audit)
            for scope in (
                broken["rows"][0]["package"],
                broken["rows"][0]["package"]["bnkStructures"][0],
            ):
                scope["hircMusicHeadReferences"]["resolved"] = 2
                scope["hircMusicHeadReferences"][field] = (
                    scope["hircMusicHeadReferences"][field] + 1
                )
            head = aggregate_current_hirc_actions(
                outer, expected_files, excluded_files, broken
            )["musicHeadReferences"]
            self.assertFalse(music_head_references_are_closed(head), field)

    def test_music_head_outcomes_must_partition_and_offsets_must_follow_the_byte(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()

        dropped = copy.deepcopy(audio_audit)
        for scope in (
            dropped["rows"][0]["package"],
            dropped["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircMusicHeadReferences"]["resolved"] = 1
        with self.assertRaisesRegex(ValueError, "do not partition"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, dropped)

        # The offset histogram is not free-standing: it must be derivable from the
        # discriminant byte, or the "offset follows from a byte" claim is untested.
        drifted = copy.deepcopy(audio_audit)
        for scope in (
            drifted["rows"][0]["package"],
            drifted["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircMusicHeadReferences"]["offsetCounts"] = {"offset_5": 2, "offset_9": 1}
        with self.assertRaisesRegex(ValueError, "do not follow from the discriminant"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, drifted)

        unobserved = copy.deepcopy(audio_audit)
        for scope in (
            unobserved["rows"][0]["package"],
            unobserved["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircMusicHeadReferences"]["discriminantCounts"] = {"byte2_00": 2, "byte2_07": 1}
        with self.assertRaisesRegex(ValueError, "unobserved discriminant"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, unobserved)

        mismatched = copy.deepcopy(audio_audit)
        for scope in (
            mismatched["rows"][0]["package"],
            mismatched["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircMusicHeadReferences"]["bodiesByType"] = {"type0A": 2}
        with self.assertRaisesRegex(ValueError, "per-type counts disagree"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, mismatched)

    def test_type22_reuses_group_i_and_keeps_only_its_residuals(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        bodies = result["type22BodyFrames"]
        self.assertEqual(bodies["exact"], 2)
        self.assertEqual(bodies["frameClosure"], "all-bodies-exact")
        self.assertTrue(body_lane_corpus_is_closed(bodies))
        residuals = " ".join(bodies["unresolvedWidths"])
        self.assertIn("group I", residuals)
        # It shares only group I, so the rest of the node frame's open questions
        # are not statements about this type.
        self.assertNotIn("group B", residuals)
        self.assertNotIn("group H", residuals)

    def test_type22_per_element_selector_families_must_match_their_counters(self) -> None:
        # These families carry one observation per counted element, not per body, so
        # they reconcile against their own counter rather than the body total.
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        for family, group in (("propertyKey_00", "propertyEntries"), ("groupIKeyWidth_1", "groupIEntries")):
            broken = copy.deepcopy(audio_audit)
            for scope in (
                broken["rows"][0]["package"],
                broken["rows"][0]["package"]["bnkStructures"][0],
            ):
                scope["hircType22BodyFrame"]["selectorCounts"][family] += 1
            with self.assertRaisesRegex(ValueError, f"does not match {group}"):
                aggregate_current_hirc_actions(outer, expected_files, excluded_files, broken)

    def test_type14_body_is_framed_without_the_shared_node_frame(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        bodies = result["type14BodyFrames"]
        self.assertEqual(bodies["count"], 2)
        self.assertEqual(bodies["exact"], 2)
        self.assertEqual(bodies["frameClosure"], "all-bodies-exact")
        self.assertEqual(bodies["bodyBytes"], bodies["exactCursorBytes"])
        self.assertEqual(bodies["anonymousGroupCounts"]["listElements"], 5)
        self.assertEqual(bodies["anonymousGroupCounts"]["optionalBlock"], 1)
        self.assertTrue(body_lane_corpus_is_closed(bodies))

        # This lane must not inherit the node frame's open questions: they are
        # statements about groups its bodies never contain.
        residuals = " ".join(bodies["unresolvedWidths"])
        self.assertNotIn("group B", residuals)
        self.assertNotIn("group E", residuals)
        self.assertIn("optional-block flag", residuals)
        self.assertIn("two closing bytes", residuals)

    def test_type14_closed_form_byte_identity_is_enforced(self) -> None:
        # 24 fixed bytes a body, plus 12 an element, 3 an entry, 20 an optional
        # block. This is an equation, so a miscount cannot hide inside slack.
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        for field, value in (("listElements", 6), ("listEntries", 4), ("optionalBlock", 2)):
            broken = copy.deepcopy(audio_audit)
            for scope in (
                broken["rows"][0]["package"],
                broken["rows"][0]["package"]["bnkStructures"][0],
            ):
                scope["hircType14BodyFrame"]["groupCounts"][field] = value
            with self.assertRaisesRegex(ValueError, "closed-form total"):
                aggregate_current_hirc_actions(outer, expected_files, excluded_files, broken)

    def test_type14_selector_families_must_cover_every_exact_body(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        for family in ("headByte_00", "optionalBlockFlag_00"):
            broken = copy.deepcopy(audio_audit)
            for scope in (
                broken["rows"][0]["package"],
                broken["rows"][0]["package"]["bnkStructures"][0],
            ):
                del scope["hircType14BodyFrame"]["selectorCounts"][family]
            with self.assertRaisesRegex(ValueError, "selector family"):
                aggregate_current_hirc_actions(outer, expected_files, excluded_files, broken)

    def test_type14_closure_is_enforced_not_just_reported(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        leaky = copy.deepcopy(audio_audit)
        for scope in (
            leaky["rows"][0]["package"],
            leaky["rows"][0]["package"]["bnkStructures"][0],
        ):
            frame = scope["hircType14BodyFrame"]
            frame["exact"] = 1
            frame["failed"] = 1
            frame["exactCursorBytes"] = 51
            frame["nonExactBodyBytes"] = 86
            frame["failureCategories"] = {"nonzero_listTerminator": 1}
            frame["groupCounts"] = {"listEntries": 1, "listElements": 2, "optionalBlock": 0}
            frame["selectorCounts"] = {
                "headByte_00": 1,
                "optionalBlockFlag_00": 1,
                "listEntrySelector_00": 1,
            }
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, leaky)
        bodies = result["type14BodyFrames"]
        self.assertEqual(bodies["failed"], 1)
        self.assertNotEqual(bodies["frameClosure"], "all-bodies-exact")
        self.assertFalse(body_lane_corpus_is_closed(bodies))

    def test_type07_body_frames_reuse_the_shared_node_frame(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        bodies = result["type07BodyFrames"]
        self.assertEqual(bodies["count"], 2)
        self.assertEqual(bodies["exact"], 2)
        self.assertEqual(bodies["frameClosure"], "all-bodies-exact")
        self.assertEqual(bodies["bodyBytes"], bodies["exactCursorBytes"])
        self.assertEqual(bodies["nonExactBodyBytes"], 0)
        self.assertEqual(bodies["anonymousGroupCounts"]["childEntries"], 4)
        self.assertEqual(bodies["minExactBodyBytes"], 110)
        self.assertIn("same ones proven on type 0x02", bodies["sharedNodeFrame"])
        self.assertTrue(body_lane_corpus_is_closed(bodies))

    def test_type07_body_gate_rejects_partition_and_byte_mismatches(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()

        bad_partition = copy.deepcopy(audio_audit)
        bad_partition["rows"][0]["package"]["hircType07BodyFrame"]["exact"] = 1
        with self.assertRaisesRegex(ValueError, "type 0x07 body outcome partition mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_partition)

        bad_declared = copy.deepcopy(audio_audit)
        for scope in (
            bad_declared["rows"][0]["package"],
            bad_declared["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType07BodyFrame"]["bodyBytes"] = 236
            scope["hircType07BodyFrame"]["exactCursorBytes"] = 236
        with self.assertRaisesRegex(ValueError, "type 0x07 body bytes differ from declared"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_declared)

        # A single body below the 35-byte floor must be refused even when the mean is fine.
        short_body = copy.deepcopy(audio_audit)
        for scope in (
            short_body["rows"][0]["package"],
            short_body["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType07BodyFrame"].update(
                {"minExactBodyBytes": 34, "maxExactBodyBytes": 130}
            )
        with self.assertRaisesRegex(ValueError, "type 0x07 exact body falls below the minimum frame"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, short_body)

        bad_bank = copy.deepcopy(audio_audit)
        bad_bank["rows"][0]["package"]["bnkStructures"][0]["hircType07BodyFrame"][
            "groupCounts"
        ]["childEntries"] = 3
        with self.assertRaisesRegex(ValueError, "type 0x07 group inventory mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_bank)

        missing = copy.deepcopy(audio_audit)
        del missing["rows"][0]["package"]["hircType07BodyFrame"]
        with self.assertRaisesRegex(ValueError, "missing type 0x07 body-frame result"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, missing)

    def test_body_gate_bounds_every_variable_length_inventory(self) -> None:
        # Outcome counts were already policed; the anonymous inventories are where a
        # reader-side over-consumption could otherwise grow without being noticed.
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()

        for scale, pattern in ((99, "not bounded by their entry count"), (0, "not bounded")):
            inflated = copy.deepcopy(audio_audit)
            for scope in (
                inflated["rows"][0]["package"],
                inflated["rows"][0]["package"]["bnkStructures"][0],
            ):
                scope["hircType07BodyFrame"]["groupCounts"]["groupIKeyBytes"] = scale
            with self.assertRaisesRegex(ValueError, pattern):
                aggregate_current_hirc_actions(outer, expected_files, excluded_files, inflated)

        histogram = copy.deepcopy(audio_audit)
        for scope in (
            histogram["rows"][0]["package"],
            histogram["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType07BodyFrame"]["selectorCounts"]["groupIKeyWidth_2"] = 2
        with self.assertRaisesRegex(ValueError, "key width histogram does not match its entry count"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, histogram)

        mismatched = copy.deepcopy(audio_audit)
        for scope in (
            mismatched["rows"][0]["package"],
            mismatched["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType07BodyFrame"]["selectorCounts"] = {
                "groupAFlag_00": 2,
                "groupBFlag_00": 2,
                "groupESelector_00": 2,
                "groupFSelector_00": 2,
                "groupIKeyWidth_1": 2,
                "groupHStateWidth_12": 1,
                "groupHStateWidth_18": 1,
            }
        with self.assertRaisesRegex(ValueError, "key width histogram does not sum to its byte total"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, mismatched)

        oversized = copy.deepcopy(audio_audit)
        for scope in (
            oversized["rows"][0]["package"],
            oversized["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType07BodyFrame"]["groupCounts"]["childEntries"] = 1_000_000
        with self.assertRaisesRegex(ValueError, "anonymous element bytes exceed the framed bodies"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, oversized)

    def test_type07_body_closure_is_enforced_not_just_reported(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        closed = aggregate_current_hirc_actions(
            outer, expected_files, excluded_files, audio_audit
        )["type07BodyFrames"]
        self.assertTrue(body_lane_corpus_is_closed(closed))
        for field, value in (
            ("frameClosure", "incomplete"),
            ("exact", 1),
            ("unsupported", 1),
            ("failed", 1),
            ("ambiguous", 1),
            ("nonExactBodyBytes", 1),
        ):
            regressed = dict(closed)
            regressed[field] = value
            self.assertFalse(
                body_lane_corpus_is_closed(regressed),
                f"{field}={value} must not count as a closed corpus",
            )

    def test_type07_body_markdown_records_the_shared_frame_and_open_questions(self) -> None:
        report = {
            "status": "complete",
            "inputSetSha256": "A" * 64,
            "outer": {
                "ledgerSha256": "B" * 64,
                "animeStudioCliFingerprint": {
                    "matchesOuterAudit": False,
                    "outerAuditSha256": "C" * 64,
                    "currentSha256": "D" * 64,
                },
            },
            "audioAudit": {
                "toolSha256": "D" * 64,
                "toolClosure": {"fileCount": 79, "manifestSha256": "G" * 64},
                "intermediatePath": "tmp/audio-audit.json",
                "sha256": "E" * 64,
            },
            "corpusGate": {"sha256": "F" * 64},
            "corpus": {
                "packageCount": 1,
                "verifiedPackageCount": 1,
                "excludedBlockCount": 0,
                "type07BodyFrames": {
                    "frameClosure": "all-bodies-exact",
                    "count": 1,
                    "exact": 1,
                    "unsupported": 0,
                    "failed": 0,
                    "ambiguous": 0,
                    "bodyBytes": 35,
                    "exactCursorBytes": 35,
                    "nonExactBodyBytes": 0,
                    "minExactBodyBytes": 35,
                    "maxExactBodyBytes": 35,
                    "minimumPossibleFrameBytes": 35,
                    "frameLayout": "The reader consumes the node groups and one counted reference vector.",
                    "packagesWithObjects": 1,
                    "banksWithObjects": 1,
                    "sharedNodeFrame": "the nine anonymous groups are the same ones proven on type 0x02 bodies",
                    "anonymousGroupCounts": {"childEntries": 0},
                    "anonymousSelectorCounts": {"groupAFlag_00": 1},
                    "failureCategories": {},
                    "unsupportedCategories": {},
                    "objectCountsByBlock": {"Audio": 1},
                    "unresolvedWidths": ["group B element width: no nonempty vector"],
                    "upstreamAbortsNotCountedHere": "every malformed body reaches this lane",
                },
            },
            "evidenceBoundary": {"nonClaims": ["serialized field ownership or field names", "container membership, selection, or ordering behaviour"]},
        }

        markdown = _body_lane_markdown(report, "type07BodyFrames", "0x07")

        self.assertIn("all-bodies-exact", markdown)
        self.assertIn("same ones proven on type 0x02", markdown)
        self.assertIn("What this corpus does not resolve", markdown)
        # The non-claims must come from the lane, so a lane with different limits
        # cannot inherit another lane's disclaimer text.
        self.assertIn("container membership, selection, or ordering behaviour", markdown)
        self.assertIn("stays anonymous", markdown)
        self.assertIn("does not establish:", markdown)
        self.assertIn("- serialized field ownership or field names", markdown)
        self.assertIn("Closure is enforced", markdown)

    def test_type04_candidate_vector_gate_rejects_structural_mismatches(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        bad_prefix_math = copy.deepcopy(audio_audit)
        bad_prefix_math["rows"][0]["package"]["hircType04U32VectorFrame"]["candidateEntryCount"] = 1
        with self.assertRaisesRegex(ValueError, "count-byte/u32-entry arithmetic"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_prefix_math)

        bad_package_bytes = copy.deepcopy(audio_audit)
        bad_package_bytes["rows"][0]["package"]["hircType04U32VectorFrame"]["opaqueTailBytes"] = 2
        with self.assertRaisesRegex(ValueError, "candidate-prefix/tail/failed body accounting"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_package_bytes)

        bad_bank_partition = copy.deepcopy(audio_audit)
        bank_frame = bad_bank_partition["rows"][0]["package"]["bnkStructures"][0]["hircType04U32VectorFrame"]
        bank_frame["exact"] = 2
        bank_frame["unsupported"] = 0
        bank_frame["unsupportedCandidatePrefixBytes"] = 0
        bank_frame["exactCursorBytes"] = 10
        bank_frame["opaqueTailBytes"] = 0
        bank_frame["bodyBytes"] = 10
        bank_frame["unsupportedCategories"] = {}
        bank_stats = bad_bank_partition["rows"][0]["package"]["bnkStructures"][0]["hircObjectTypeStats"]["0x04"]
        bank_stats["declaredLengthBytes"] = 18
        with self.assertRaisesRegex(ValueError, "per-bank/package type 0x04 candidate-vector total mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_bank_partition)

    def test_type04_gate_preserves_a_counted_short_body_failure(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        failed_frame = {
            "count": 2,
            "exactEntryCount": 1,
            "exact": 1,
            "unsupported": 0,
            "failed": 1,
            "ambiguous": 0,
            "bodyBytes": 11,
            "candidatePrefixBytes": 5,
            "unsupportedCandidatePrefixBytes": 0,
            "exactCursorBytes": 5,
            "opaqueTailBytes": 0,
            "failedBodyBytes": 6,
            "candidateEntryCount": 1,
            "failureCategories": {"truncated_entries": 1},
            "unsupportedCategories": {},
            "nonExactExamples": [
                {
                    "bankId": 123,
                    "ordinal": 2,
                    "objectId": 456,
                    "status": "failed",
                    "category": "truncated_entries",
                    "expectedBytes": 9,
                    "actualBytes": 6,
                    "opaqueTailBytes": 0,
                }
            ],
        }
        package = audio_audit["rows"][0]["package"]
        package["hircType04U32VectorFrame"] = copy.deepcopy(failed_frame)
        package["bnkStructures"][0]["hircType04U32VectorFrame"] = copy.deepcopy(failed_frame)

        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)

        vectors = result["type04U32VectorCandidates"]
        self.assertEqual(vectors["exact"], 1)
        self.assertEqual(vectors["failed"], 1)
        self.assertEqual(vectors["failedBodyBytes"], 6)
        self.assertEqual(vectors["failureCategories"], {"truncated_entries": 1})
        self.assertEqual(vectors["frameClosure"], "incomplete")

    def test_type02_prefix_gate_rejects_byte_count_and_bank_mismatches(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        bad_tail = copy.deepcopy(audio_audit)
        bad_tail["rows"][0]["package"]["hircType02Prefix"]["opaqueTailBytes"] = 63
        with self.assertRaisesRegex(ValueError, "prefix-plus-tail body accounting mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_tail)

        bad_plugins = copy.deepcopy(audio_audit)
        bad_plugins["rows"][0]["package"]["hircType02Prefix"]["pluginTypeCounts"]["0x2"] = 0
        with self.assertRaisesRegex(ValueError, "plugin-type count mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_plugins)

        bad_bank = copy.deepcopy(audio_audit)
        bank_prefix = bad_bank["rows"][0]["package"]["bnkStructures"][0]["hircType02Prefix"]
        bank_prefix.update({
            "prefixBytes": 35,
            "opaqueTailBytes": 65,
            "maxOpaqueTailBytes": 33,
        })
        with self.assertRaisesRegex(ValueError, "per-bank/package type 0x02"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_bank)

    def test_package_identity_includes_checksum_chunk_and_physical_source(self) -> None:
        mutations = (
            ("verifiedFileDataMd5", "B" * 32),
            ("chunk", "other.chk"),
            ("source", r"D:\Persistent\VFS\BB\bank.chk"),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
                audio_audit["rows"][0][field] = value
                with self.assertRaisesRegex(ValueError, "verified package identities"):
                    aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)

    def test_excluded_blocks_match_exact_status_and_multiplicity(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        wrong_status = copy.deepcopy(audio_audit)
        wrong_status["rows"][1]["status"] = "excluded_missing_audio"
        with self.assertRaisesRegex(ValueError, "conditional-exclusion identity mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, wrong_status)

        duplicate_row = copy.deepcopy(audio_audit)
        duplicate_row["rows"].append(copy.deepcopy(duplicate_row["rows"][1]))
        with self.assertRaisesRegex(ValueError, "conditional-exclusion identity mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, duplicate_row)

        wrong_multiplicity = copy.deepcopy(audio_audit)
        wrong_multiplicity["rows"][1]["declaredFiles"] = 1
        with self.assertRaisesRegex(ValueError, "conditional-exclusion multiplicity mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, wrong_multiplicity)

    def test_per_bank_outcomes_and_totals_reconcile_with_package(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        per_bank_partition = copy.deepcopy(audio_audit)
        bank_frame = per_bank_partition["rows"][0]["package"]["bnkStructures"][0]["hircType03ActionFrame"]
        bank_frame["failed"] = 1
        with self.assertRaisesRegex(ValueError, "outcome partition mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, per_bank_partition)

        package_total_mismatch = copy.deepcopy(audio_audit)
        bank_frame = package_total_mismatch["rows"][0]["package"]["bnkStructures"][0]["hircType03ActionFrame"]
        bank_frame["exact"] = 1
        bank_frame["failed"] = 1
        with self.assertRaisesRegex(ValueError, "per-bank/package type 0x03 total mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, package_total_mismatch)

    def test_action_corpus_aggregate_rejects_missing_or_unclassified_objects(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        frame = audio_audit["rows"][0]["package"]["hircType03ActionFrame"]
        frame["count"] = 1
        frame["exact"] = 1
        frame["bodyBytes"] = 9
        frame["exactCursorBytes"] = 9
        with self.assertRaisesRegex(ValueError, "type 0x03 audit count mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)


if __name__ == "__main__":
    unittest.main()


class SharedFrameConstantTests(unittest.TestCase):
    """The constants in the shared framer must out-score their alternatives."""

    def census(self, **overrides):
        # Two constants, each with three candidate values. The chosen value wins the
        # zero trailer outright; a rival closes every body but lands nothing there.
        base = {
            "bodies": 412,
            "chosen": {"entryBytes": 6, "middleRunElementBytes": 18},
            "bodiesExercising": {"entryBytes": 267, "middleRunElementBytes": 14},
            "closesByCandidate": {
                "entryBytes_5": 267, "entryBytes_6": 267, "entryBytes_9": 174,
                "middleRunElementBytes_11": 14, "middleRunElementBytes_18": 14,
                "middleRunElementBytes_19": 13,
            },
            "zeroTrailerByCandidate": {
                "entryBytes_5": 0, "entryBytes_6": 203, "entryBytes_9": 0,
                "middleRunElementBytes_11": 0, "middleRunElementBytes_18": 10,
                "middleRunElementBytes_19": 0,
            },
        }
        base.update(overrides)
        return base

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(every_shared_constant_beats_its_rivals(self.census()))
        self.assertTrue(the_shared_constants_are_not_settled_by_closure(self.census()))

    def test_the_ranking_reduces_on_corpus_totals(self) -> None:
        ranked = _rank_shared_constants(self.census())
        self.assertEqual(ranked["entryBytes"]["chosenZeroTrailer"], 203)
        self.assertEqual(ranked["entryBytes"]["bestRivalZeroTrailer"], 0)
        # entryBytes_5 closes all 267 without landing on the trailer: that is the
        # rival that makes closure useless as a discriminator.
        self.assertEqual(ranked["entryBytes"]["rivalsThatCloseEveryBody"], 1)

    def test_a_tie_with_a_rival_is_not_a_win(self) -> None:
        census = self.census()
        census["zeroTrailerByCandidate"]["entryBytes_5"] = 203
        self.assertFalse(every_shared_constant_beats_its_rivals(census))

    def test_a_constant_that_lands_nothing_on_the_trailer_is_untested(self) -> None:
        # Beating every rival by zero to zero is not evidence.
        census = self.census()
        census["zeroTrailerByCandidate"]["middleRunElementBytes_18"] = 0
        self.assertFalse(every_shared_constant_beats_its_rivals(census))

    def test_a_constant_no_body_exercises_is_untested(self) -> None:
        census = self.census()
        census["bodiesExercising"]["middleRunElementBytes"] = 0
        census["zeroTrailerByCandidate"]["middleRunElementBytes_18"] = 0
        self.assertFalse(every_shared_constant_beats_its_rivals(census))

    def test_an_empty_census_fails(self) -> None:
        self.assertFalse(every_shared_constant_beats_its_rivals({}))
        self.assertFalse(every_shared_constant_beats_its_rivals(self.census(bodies=0)))
        self.assertFalse(every_shared_constant_beats_its_rivals(self.census(chosen={})))

    def test_the_control_fails_when_closure_would_have_sufficed(self) -> None:
        # If no rival closes every exercising body then closure discriminates after
        # all, the zero-trailer test is doing no work, and the reasoning recorded
        # around these constants is wrong. That has to fail loudly, not pass quietly.
        census = self.census()
        census["closesByCandidate"] = {
            key: (value if key.endswith(("_6", "_18")) else 1)
            for key, value in census["closesByCandidate"].items()
        }
        self.assertFalse(the_shared_constants_are_not_settled_by_closure(census))
        self.assertFalse(the_shared_constants_are_not_settled_by_closure({}))

    def test_the_reader_rejects_a_malformed_census(self) -> None:
        for bad in ({"bodies": -1}, {"bodies": 4, "chosen": []}, {"bodies": 4}):
            with self.assertRaises(ValueError):
                _read_shared_constant_census(bad, "pkg")

    def test_the_reader_rejects_a_census_that_skips_a_constant(self) -> None:
        census = self.census()
        census["bodiesExercising"] = {"entryBytes": 267}
        with self.assertRaises(ValueError):
            _read_shared_constant_census(census, "pkg")

    def test_the_reader_rejects_a_score_above_its_exercising_set(self) -> None:
        census = self.census()
        census["zeroTrailerByCandidate"]["middleRunElementBytes_18"] = 99
        with self.assertRaises(ValueError):
            _read_shared_constant_census(census, "pkg")

    def test_the_reader_rejects_an_exercising_set_larger_than_the_corpus(self) -> None:
        with self.assertRaises(ValueError):
            _read_shared_constant_census(self.census(bodies=5), "pkg")

    def test_the_reader_rejects_a_score_for_an_unknown_constant(self) -> None:
        census = self.census()
        census["zeroTrailerByCandidate"]["mysteryBytes_3"] = 1
        with self.assertRaises(ValueError):
            _read_shared_constant_census(census, "pkg")

    def test_an_absent_census_reads_as_empty_rather_than_raising(self) -> None:
        self.assertEqual(_read_shared_constant_census(None, "pkg")["bodies"], 0)


class GroupEvidenceTests(unittest.TestCase):
    """An entry total is not evidence until the bodies behind it are counted."""

    def lanes(self, **overrides):
        base = {
            "type07": {
                "anonymousGroupCounts": {"groupEItems": 20, "groupCEntries": 83014},
                "anonymousGroupBodies": {"groupEItems": 4, "groupCEntries": 33202},
                "anonymousGroupMaxInOneBody": {"groupEItems": 9, "groupCEntries": 11},
            },
            "type05": {
                "anonymousGroupCounts": {"groupEItems": 1118, "groupCEntries": 24348},
                "anonymousGroupBodies": {"groupEItems": 165, "groupCEntries": 14653},
                "anonymousGroupMaxInOneBody": {"groupEItems": 19, "groupCEntries": 9},
            },
        }
        base.update(overrides)
        return base

    def test_a_lane_counting_groups_must_count_their_bodies(self) -> None:
        self.assertTrue(every_group_reports_the_bodies_behind_it(self.lanes()))
        stale = self.lanes()
        stale["type07"] = {"anonymousGroupCounts": {"groupEItems": 20}}
        self.assertFalse(every_group_reports_the_bodies_behind_it(stale))

    def test_a_lane_with_no_groups_is_not_required_to_report_bodies(self) -> None:
        lanes = self.lanes(type08={"anonymousGroupCounts": {}})
        self.assertTrue(every_group_reports_the_bodies_behind_it(lanes))

    def test_a_report_with_no_groups_at_all_fails_rather_than_passing_vacuously(self) -> None:
        self.assertFalse(every_group_reports_the_bodies_behind_it({}))
        self.assertFalse(every_group_reports_the_bodies_behind_it(
            {"type08": {"anonymousGroupCounts": {"groupEItems": 0}}}
        ))

    def test_thin_groups_are_named_per_lane(self) -> None:
        # Group E's layout is well established corpus-wide and has been seen four
        # times in type 0x07. Both are true and the second is the one a reader
        # judging that lane needs.
        thin = thinly_seen_groups(self.lanes())
        self.assertEqual(thin, {"type07": {"groupEItems": 4}})

    def test_the_pooled_total_can_be_healthy_while_a_lane_is_thin(self) -> None:
        summary = summarise_group_evidence(self.lanes())
        self.assertEqual(summary["bodiesPerGroupPooled"]["groupEItems"], 169)
        self.assertEqual(summary["thinlySeenPooled"], {})
        self.assertEqual(summary["thinlySeenByLane"], {"type07": {"groupEItems": 4}})

    def test_the_widest_single_body_is_a_maximum_not_a_sum(self) -> None:
        # The number that distinguishes "a hundred bodies with one entry" from
        # "one body with a hundred entries" must not be added up across lanes.
        summary = summarise_group_evidence(self.lanes())
        self.assertEqual(summary["widestSingleBodyPerGroup"]["groupEItems"], 19)

    def test_an_empty_lane_set_summarises_without_raising(self) -> None:
        summary = summarise_group_evidence({})
        self.assertEqual(summary["bodiesPerGroupPooled"], {})
        self.assertEqual(summary["thinlySeenByLane"], {})


class Type11ElementTrailerTests(unittest.TestCase):
    """The element trailer must be established by its residue, not by parsing."""

    def census(self, **overrides):
        base = {
            "elements": 3891,
            "anchorSelectsOneTrailer": {
                "trailer_17_22": 3877, "trailer_18_23": 3875, "trailer_19_24": 3782,
                "trailer_19_25": 3327, "trailer_20_25": 3418, "trailer_21_26": 721,
            },
            "anchorLeavesWholeRecords": {
                "trailer_17_22": 32, "trailer_19_24": 3594, "trailer_19_25": 3108,
                "trailer_20_25": 6, "trailer_21_26": 4,
            },
        }
        base.update(overrides)
        return base

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(the_type11_trailer_anchor_beats_its_rivals(self.census()))
        self.assertTrue(the_type11_trailer_is_not_settled_by_parsing(self.census()))

    def test_a_rival_sharing_an_endpoint_is_not_held_to_the_wide_margin(self) -> None:
        # (19, 25) scores 3,108 only because 19 is right and most elements take the
        # short trailer. Demanding a tenfold margin over it would fail a correct
        # reading -- which is exactly what the first version of this gate did.
        census = self.census()
        self.assertGreater(census["anchorLeavesWholeRecords"]["trailer_19_25"],
                           census["anchorLeavesWholeRecords"]["trailer_19_24"] / 10)
        self.assertTrue(the_type11_trailer_anchor_beats_its_rivals(census))

    def test_an_independent_rival_that_scores_well_fails_the_gate(self) -> None:
        census = self.census()
        census["anchorLeavesWholeRecords"]["trailer_20_25"] = 1000
        self.assertFalse(the_type11_trailer_anchor_beats_its_rivals(census))

    def test_any_rival_beating_the_chosen_anchor_fails(self) -> None:
        census = self.census()
        census["anchorLeavesWholeRecords"]["trailer_19_25"] = 3594
        self.assertFalse(the_type11_trailer_anchor_beats_its_rivals(census))

    def test_an_anchor_that_leaves_nothing_structured_fails(self) -> None:
        census = self.census()
        census["anchorLeavesWholeRecords"]["trailer_19_24"] = 0
        self.assertFalse(the_type11_trailer_anchor_beats_its_rivals(census))
        self.assertFalse(the_type11_trailer_anchor_beats_its_rivals(self.census(elements=0)))
        self.assertFalse(the_type11_trailer_anchor_beats_its_rivals({}))

    def test_the_control_fails_when_parsing_would_have_sufficed(self) -> None:
        # If the chosen anchor also parsed more elements than every rival, parsing
        # would be the discriminator and the residue test would be doing no work.
        census = self.census()
        census["anchorSelectsOneTrailer"] = {
            "trailer_19_24": 3782, "trailer_17_22": 10, "trailer_18_23": 10,
        }
        self.assertFalse(the_type11_trailer_is_not_settled_by_parsing(census))
        self.assertFalse(the_type11_trailer_is_not_settled_by_parsing({}))

    def test_the_reader_rejects_incoherent_counts(self) -> None:
        base = {key: 0 for key in TYPE11_ELEMENT_SCALARS}
        base.update({key: {} for key in TYPE11_ELEMENT_MAPS})
        for field, value in (
            ("elements", 5), ("framed", 5), ("elementsWithRecords", 5),
            ("countFieldAgrees", 5),
        ):
            bad = dict(base, **{field: value})
            bad.update({key: {} for key in TYPE11_ELEMENT_MAPS})
            with self.assertRaises(ValueError):
                _read_type11_element_census(bad, "pkg")

    def test_the_reader_rejects_an_anchor_scoring_above_its_own_selection(self) -> None:
        base = {key: 0 for key in TYPE11_ELEMENT_SCALARS}
        base.update({key: {} for key in TYPE11_ELEMENT_MAPS})
        base["anchorSelectsOneTrailer"] = {"trailer_19_24": 3}
        base["anchorLeavesWholeRecords"] = {"trailer_19_24": 4}
        with self.assertRaises(ValueError):
            _read_type11_element_census(base, "pkg")

    def test_an_absent_census_reads_as_empty(self) -> None:
        self.assertEqual(_read_type11_element_census(None, "pkg")["elements"], 0)


class Type11ElementFrameTests(unittest.TestCase):
    """The element frame must be scored over the elements that exercise it."""

    def census(self, **overrides):
        base = {
            "elementsWithRuns": 1151,
            "frameClosesWithRuns": {
                "frame_5_11_7_12": 1103, "frame_17_11_7_0": 17, "frame_5_11_11_12": 2,
            },
            "frameCloses": {
                "frame_5_11_7_12": 3594, "frame_17_11_7_0": 2508,
                "frame_5_11_11_12": 2493, "frame_5_10_7_12": 2491,
            },
        }
        base.update(overrides)
        return base

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(the_type11_element_frame_beats_its_rivals(self.census()))
        self.assertTrue(
            the_type11_element_frame_is_not_settled_by_empty_elements(self.census())
        )

    def test_scoring_over_every_element_would_hide_the_margin(self) -> None:
        # The whole point of the exercising subset. Over all elements the chosen
        # frame beats its best rival 3,594 to 2,508 -- a ratio of 1.4, which no
        # tenfold margin survives. Over the elements that walk a run it is 1,103 to
        # 17. Same frame, same corpus, completely different strength of claim.
        census = self.census()
        over_all = census["frameCloses"]
        self.assertLess(over_all["frame_5_11_7_12"], over_all["frame_17_11_7_0"] * 10)
        with_runs = census["frameClosesWithRuns"]
        self.assertGreater(with_runs["frame_5_11_7_12"], with_runs["frame_17_11_7_0"] * 10)

    def test_a_rival_closing_the_run_bearing_elements_fails_the_gate(self) -> None:
        census = self.census()
        census["frameClosesWithRuns"]["frame_17_11_7_0"] = 900
        self.assertFalse(the_type11_element_frame_beats_its_rivals(census))

    def test_a_frame_that_closes_a_minority_fails(self) -> None:
        census = self.census()
        census["frameClosesWithRuns"]["frame_5_11_7_12"] = 400
        self.assertFalse(the_type11_element_frame_beats_its_rivals(census))

    def test_an_empty_or_unexercised_census_fails(self) -> None:
        self.assertFalse(the_type11_element_frame_beats_its_rivals({}))
        self.assertFalse(the_type11_element_frame_beats_its_rivals(
            self.census(elementsWithRuns=0)
        ))
        self.assertFalse(the_type11_element_frame_beats_its_rivals(
            self.census(frameClosesWithRuns={"frame_5_11_7_12": 1103})
        ))

    def test_the_control_needs_a_rival_that_is_inflated_by_empty_elements(self) -> None:
        # If no rival closed many elements overall while closing almost none that
        # walk a run, the run walk would not be shown to carry the result.
        census = self.census()
        census["frameCloses"] = {"frame_5_11_7_12": 3594, "frame_17_11_7_0": 20}
        self.assertFalse(
            the_type11_element_frame_is_not_settled_by_empty_elements(census)
        )
        self.assertFalse(the_type11_element_frame_is_not_settled_by_empty_elements({}))

    def test_the_reader_rejects_a_frame_closing_more_than_it_could(self) -> None:
        base = {key: 0 for key in TYPE11_ELEMENT_SCALARS}
        base.update({key: {} for key in TYPE11_ELEMENT_MAPS})
        base["elements"] = 10
        base["elementsWithRuns"] = 4
        base["frameCloses"] = {"frame_5_11_7_12": 8}
        base["frameClosesWithRuns"] = {"frame_5_11_7_12": 6}
        with self.assertRaises(ValueError):
            _read_type11_element_census(base, "pkg")


class Type11BodyLaneTests(unittest.TestCase):
    """Numeric type 0x0B's body frame has a floor, not a closure requirement."""

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(the_type11_body_frame_covers_most_of_its_corpus(
            {"count": 4325, "exact": 3715, "failed": 610, "ambiguous": 0}
        ))

    def test_a_halved_coverage_fails(self) -> None:
        # The regression this gate exists to catch. Nothing else in the report reads
        # this number, so a change that quietly halved it would look like a pass.
        self.assertFalse(the_type11_body_frame_covers_most_of_its_corpus(
            {"count": 4325, "exact": 1800, "failed": 2525, "ambiguous": 0}
        ))

    def test_an_ambiguous_body_fails_outright(self) -> None:
        self.assertFalse(the_type11_body_frame_covers_most_of_its_corpus(
            {"count": 4325, "exact": 3715, "ambiguous": 1}
        ))

    def test_an_empty_lane_fails_rather_than_passing_vacuously(self) -> None:
        self.assertFalse(the_type11_body_frame_covers_most_of_its_corpus({}))
        self.assertFalse(the_type11_body_frame_covers_most_of_its_corpus(
            {"count": 0, "exact": 0}
        ))
        self.assertFalse(the_type11_body_frame_covers_most_of_its_corpus(
            {"count": 100, "exact": 0}
        ))

    def test_the_floor_sits_below_the_measured_rate(self) -> None:
        # A gate set at exactly today's value fails on the next legitimate change to
        # a neighbouring reader and teaches nothing when it does.
        self.assertLess(TYPE11_BODY_MINIMUM_EXACT, 3715 / 4325)


class Type11EntryHeaderTests(unittest.TestCase):
    """Entry-header readings must each beat a neighbouring word."""

    def census(self, **overrides):
        base = {
            "entries": 3715,
            "rangeTested": 1404, "rangeIsSymmetric": 1218, "rangeIsOrdered": 1264,
            "rangeControlTested": 1391, "rangeControlIsSymmetric": 0,
            "rangeControlIsOrdered": 1078,
            "fractionsTested": 2804, "fractionsAreSmall": 2735,
            "fractionControlsTested": 3715, "fractionControlsAreSmall": 0,
            "elementCountValues": {"elements_1": 3715},
        }
        base.update(overrides)
        return base

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(the_type11_entry_header_fields_beat_their_controls(self.census()))
        self.assertTrue(the_type11_element_count_is_not_yet_a_count(self.census()))

    def test_a_control_that_scores_as_well_fails(self) -> None:
        self.assertFalse(the_type11_entry_header_fields_beat_their_controls(
            self.census(rangeControlIsSymmetric=1200)
        ))
        self.assertFalse(the_type11_entry_header_fields_beat_their_controls(
            self.census(fractionControlsAreSmall=3000)
        ))

    def test_a_reading_that_holds_for_a_minority_fails(self) -> None:
        self.assertFalse(the_type11_entry_header_fields_beat_their_controls(
            self.census(rangeIsSymmetric=400)
        ))
        self.assertFalse(the_type11_entry_header_fields_beat_their_controls(
            self.census(fractionsAreSmall=1500)
        ))

    def test_an_untested_reading_fails_rather_than_passing_vacuously(self) -> None:
        self.assertFalse(the_type11_entry_header_fields_beat_their_controls({}))
        self.assertFalse(the_type11_entry_header_fields_beat_their_controls(
            self.census(rangeTested=0, rangeIsSymmetric=0)
        ))
        self.assertFalse(the_type11_entry_header_fields_beat_their_controls(
            self.census(fractionControlsTested=0)
        ))

    def test_the_element_count_gate_states_what_is_untested(self) -> None:
        # It holds while the count is 1 everywhere. When a body finally closes with
        # two elements the gate fails, and that failure is the good news: the
        # reading has been tested for the first time.
        self.assertTrue(the_type11_element_count_is_not_yet_a_count(self.census()))
        self.assertFalse(the_type11_element_count_is_not_yet_a_count(
            self.census(elementCountValues={"elements_1": 3700, "elements_2": 15})
        ))
        self.assertFalse(the_type11_element_count_is_not_yet_a_count({}))

    def test_the_reader_rejects_hits_above_what_was_tested(self) -> None:
        with self.assertRaises(ValueError):
            _read_type11_header_census(self.census(rangeIsSymmetric=9999), "pkg")

    def test_the_reader_rejects_a_histogram_that_misses_entries(self) -> None:
        with self.assertRaises(ValueError):
            _read_type11_header_census(
                self.census(elementCountValues={"elements_1": 3}), "pkg"
            )

    def test_an_absent_census_reads_as_empty(self) -> None:
        self.assertEqual(_read_type11_header_census(None, "pkg")["entries"], 0)


class Type11CurveRecordTests(unittest.TestCase):
    """The run's split is settled by what the records contain, not by length."""

    def census(self, **overrides):
        base = {
            "curveRecords": 4086, "curveCodesInRange": 4086,
            "curveControlsTested": 9376, "curveControlsInRange": 377,
            "curveCodes": {
                "code_0": 77, "code_1": 485, "code_2": 25, "code_3": 8, "code_4": 1003,
                "code_5": 74, "code_6": 14, "code_7": 280, "code_8": 103, "code_9": 2017,
            },
        }
        base.update(overrides)
        return base

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(
            the_type11_curve_records_carry_interpolation_codes(self.census())
        )

    def test_one_record_out_of_range_fails(self) -> None:
        # The enum is contiguous and complete, so a single miss means the boundary
        # is wrong somewhere, not that one record is odd.
        self.assertFalse(the_type11_curve_records_carry_interpolation_codes(
            self.census(curveCodesInRange=4085)
        ))

    def test_codes_piling_on_one_value_fail(self) -> None:
        # A wrong offset over a zero-filled region would put every code on 0 and
        # pass a range test. Spanning the enum is what a real code field does.
        self.assertFalse(the_type11_curve_records_carry_interpolation_codes(
            self.census(curveCodes={"code_0": 4086})
        ))

    def test_a_control_that_scores_as_well_fails(self) -> None:
        self.assertFalse(the_type11_curve_records_carry_interpolation_codes(
            self.census(curveControlsInRange=9000)
        ))

    def test_an_untested_census_fails_rather_than_passing_vacuously(self) -> None:
        self.assertFalse(the_type11_curve_records_carry_interpolation_codes({}))
        self.assertFalse(the_type11_curve_records_carry_interpolation_codes(
            self.census(curveRecords=0, curveCodesInRange=0)
        ))
        self.assertFalse(the_type11_curve_records_carry_interpolation_codes(
            self.census(curveControlsTested=0, curveControlsInRange=0)
        ))

    def test_the_reader_rejects_a_code_histogram_that_misses_records(self) -> None:
        with self.assertRaises(ValueError):
            _read_type11_header_census(
                {key: 0 for key in TYPE11_HEADER_SCALARS}
                | {"elementCountValues": {}, "curveCodes": {"code_0": 3}},
                "pkg",
            )


class SharedHierarchyTests(unittest.TestCase):
    """The parent relation 0x08 and 0x12 declare is a forest with a type discipline."""

    def census(self, **overrides):
        base = {
            "banks": 121, "objects": 412, "cycles": 0,
            "rootsWithNoParent": 4, "rootsNamingOutsideTheBank": 119,
            "rootsPerBank": {"roots_1": 120, "roots_3": 1},
            "rootTypes": {"type08": 4},
            "outsideBankTypes": {"type12": 119},
            "internalTypes": {"type08": 68, "type12": 2},
            "leafTypes": {"type08": 93, "type12": 249},
            "depths": {"depth_0": 123, "depth_2": 126, "depth_3": 64, "depth_4": 32,
                       "depth_5": 23, "depth_6": 21, "depth_1": 18, "depth_7": 5},
        }
        base.update(overrides)
        return base

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(the_shared_hierarchy_is_a_forest(self.census()))
        self.assertTrue(almost_every_bank_contributes_one_tree(self.census()))
        self.assertTrue(numeric_type_12_is_a_leaf(self.census()))

    def test_one_cycle_fails(self) -> None:
        # A cycle would mean the leading word is not a parent at all, so this is
        # equality with zero rather than a rate.
        self.assertFalse(the_shared_hierarchy_is_a_forest(self.census(cycles=1)))

    def test_a_forest_of_isolated_nodes_fails(self) -> None:
        # Acyclicity is free when nothing is connected. The gate demands the
        # relation actually relate things.
        self.assertFalse(the_shared_hierarchy_is_a_forest(
            self.census(depths={"depth_0": 412})
        ))

    def test_scattered_roots_fail(self) -> None:
        self.assertFalse(almost_every_bank_contributes_one_tree(
            self.census(rootsPerBank={"roots_1": 40, "roots_5": 81})
        ))
        self.assertFalse(almost_every_bank_contributes_one_tree({}))

    def test_an_out_of_bank_parent_is_not_a_counterexample_to_the_leaf_claim(self) -> None:
        # The distinction the first version of this gate got wrong. 119 type 0x12
        # objects name a parent outside their bank; that makes them roots of a bank
        # fragment, not internal nodes, and the leaf claim survives.
        census = self.census()
        self.assertEqual(census["outsideBankTypes"], {"type12": 119})
        self.assertTrue(numeric_type_12_is_a_leaf(census))

    def test_type_12_gaining_children_fails(self) -> None:
        self.assertFalse(numeric_type_12_is_a_leaf(
            self.census(internalTypes={"type08": 68, "type12": 200})
        ))

    def test_a_parentless_type_12_fails(self) -> None:
        # Every object with no parent at all is a 0x08. A 0x12 at the top would mean
        # the two types do not occupy fixed positions after all.
        self.assertFalse(numeric_type_12_is_a_leaf(
            self.census(rootTypes={"type08": 4, "type12": 1})
        ))

    def test_an_empty_census_fails_rather_than_passing_vacuously(self) -> None:
        for gate in (the_shared_hierarchy_is_a_forest,
                     almost_every_bank_contributes_one_tree,
                     numeric_type_12_is_a_leaf):
            self.assertFalse(gate({}))

    def test_the_reader_rejects_counts_that_do_not_partition(self) -> None:
        with self.assertRaises(ValueError):
            _read_hierarchy_census(
                self.census(leafTypes={"type08": 93, "type12": 1}), "pkg"
            )
        with self.assertRaises(ValueError):
            _read_hierarchy_census(self.census(rootsWithNoParent=9), "pkg")


class HierarchyDirectionTests(unittest.TestCase):
    """The 0x08/0x12 relation points the opposite way to the main reference graph."""

    def census(self, **overrides):
        base = {
            "parentsWithSeveralChildren": 50,
            "childrenPerParent": {
                "children_1": 20, "children_2": 21, "children_3": 7, "children_4": 9,
                "children_5": 2, "children_6": 2, "children_7": 1, "children_8": 1,
                "children_9": 1, "children_11": 1, "children_13": 3, "children_16": 2,
            },
        }
        base.update(overrides)
        return base

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(
            the_hierarchy_runs_opposite_to_the_main_reference_graph(self.census())
        )

    def test_one_child_per_parent_fails(self) -> None:
        # That is the main reference graph's shape: every target named exactly once.
        # If this relation ever looked like that, the claim that it runs the other
        # way would need re-arguing rather than quietly standing.
        self.assertFalse(the_hierarchy_runs_opposite_to_the_main_reference_graph(
            self.census(parentsWithSeveralChildren=0,
                        childrenPerParent={"children_1": 70})
        ))

    def test_a_thin_majority_with_no_wide_parent_fails(self) -> None:
        self.assertFalse(the_hierarchy_runs_opposite_to_the_main_reference_graph(
            self.census(parentsWithSeveralChildren=40,
                        childrenPerParent={"children_1": 30, "children_2": 40})
        ))

    def test_an_empty_census_fails(self) -> None:
        self.assertFalse(the_hierarchy_runs_opposite_to_the_main_reference_graph({}))
        self.assertFalse(the_hierarchy_runs_opposite_to_the_main_reference_graph(
            self.census(childrenPerParent={})
        ))

    def test_more_wide_parents_than_parents_fails(self) -> None:
        self.assertFalse(the_hierarchy_runs_opposite_to_the_main_reference_graph(
            self.census(parentsWithSeveralChildren=999)
        ))


class MusicMutualityTests(unittest.TestCase):
    """The music relation is the format's third kind: symmetric."""

    def census(self, **overrides):
        base = {
            "sameBankEdges": 24430, "edgesIntoUnscannedObjects": 4598,
            "edgesBetweenScannedObjects": 19832, "mutualEdges": 14652,
            "mutualEdgeKinds": {
                "type0A_with_type0C": 588, "type0A_with_type0D": 3570,
                "type0C_with_type0A": 588, "type0C_with_type0C": 1474,
                "type0C_with_type0D": 2431, "type0D_with_type0A": 3570,
                "type0D_with_type0C": 2431,
            },
        }
        base.update(overrides)
        return base

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(the_music_relation_is_symmetric(self.census()))
        self.assertTrue(music_references_resolve_inside_their_own_bank(
            self.census(), {"references": 24515}
        ))

    def test_a_one_way_relation_fails(self) -> None:
        # That would make it a hierarchy like the format's other two relations, and
        # the reading that these edges cannot be parenthood would need re-arguing.
        self.assertFalse(the_music_relation_is_symmetric(
            self.census(mutualEdges=200)
        ))

    def test_unaskable_edges_are_not_counted_against_the_rate(self) -> None:
        # An edge into an unscanned object cannot carry a reverse edge, so counting
        # it as one-way would mix "not mutual" with "not askable".
        c = self.census()
        self.assertEqual(
            c["edgesIntoUnscannedObjects"] + c["edgesBetweenScannedObjects"],
            c["sameBankEdges"],
        )
        self.assertTrue(the_music_relation_is_symmetric(c))

    def test_mutuality_confined_to_one_type_pair_fails(self) -> None:
        self.assertFalse(the_music_relation_is_symmetric(
            self.census(mutualEdgeKinds={"type0A_with_type0D": 14652})
        ))

    def test_an_empty_census_fails(self) -> None:
        self.assertFalse(the_music_relation_is_symmetric({}))
        self.assertFalse(the_music_relation_is_symmetric(
            self.census(edgesBetweenScannedObjects=0, mutualEdges=0)
        ))

    def test_references_leaving_the_bank_fail_the_closure(self) -> None:
        self.assertFalse(music_references_resolve_inside_their_own_bank(
            self.census(sameBankEdges=12000), {"references": 24515}
        ))
        self.assertFalse(music_references_resolve_inside_their_own_bank({}, {}))

    def test_the_reader_rejects_counts_that_do_not_partition(self) -> None:
        with self.assertRaises(ValueError):
            _read_music_mutuality_census(self.census(sameBankEdges=99), "pkg")
        with self.assertRaises(ValueError):
            _read_music_mutuality_census(self.census(mutualEdges=99999), "pkg")


class Type0AEndAnchorTests(unittest.TestCase):
    """A fixed distance from the end is a rule only if the non-anchors find nothing."""

    def census(self, **overrides):
        base = {
            "bodies": 4158,
            "anchorNamesTheTargetType": 3995,
            "controlsNameTheTargetType": 0,
            "anchorHits": {"minus_69": 3707, "minus_73": 288},
            "controlHits": {},
        }
        base.update(overrides)
        return base

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(
            the_type0a_end_anchor_beats_every_neighbouring_distance(self.census())
        )

    def test_controls_finding_references_fail(self) -> None:
        self.assertFalse(the_type0a_end_anchor_beats_every_neighbouring_distance(
            self.census(controlsNameTheTargetType=900, controlHits={"minus_70": 900})
        ))

    def test_an_anchor_covering_a_minority_fails(self) -> None:
        self.assertFalse(the_type0a_end_anchor_beats_every_neighbouring_distance(
            self.census(anchorNamesTheTargetType=900,
                        anchorHits={"minus_69": 900})
        ))

    def test_an_empty_census_fails(self) -> None:
        self.assertFalse(the_type0a_end_anchor_beats_every_neighbouring_distance({}))
        self.assertFalse(the_type0a_end_anchor_beats_every_neighbouring_distance(
            self.census(bodies=0)
        ))

    def test_the_anchor_total_may_exceed_the_body_count(self) -> None:
        # A body can carry a reference at more than one anchor distance, so the sum
        # is not a per-body total. Each distance individually cannot exceed it, and
        # that is what the reader checks.
        c = self.census()
        self.assertGreater(sum(c["anchorHits"].values()), 0)
        self.assertLess(max(c["anchorHits"].values()), c["bodies"])
        _read_type0a_anchor_census(c, "pkg")

    def test_the_reader_rejects_one_distance_exceeding_the_body_count(self) -> None:
        with self.assertRaises(ValueError):
            _read_type0a_anchor_census(
                self.census(anchorNamesTheTargetType=9000,
                            anchorHits={"minus_69": 9000}), "pkg"
            )

    def test_the_reader_rejects_hits_that_do_not_add_up(self) -> None:
        with self.assertRaises(ValueError):
            _read_type0a_anchor_census(
                self.census(anchorHits={"minus_69": 3707}), "pkg"
            )


class Type0AEdgeAlignmentTests(unittest.TestCase):
    """One edge is aligned to the body end; the rest of the corpus is not."""

    def census(self, **overrides):
        # Two edge kinds: the aligned one, and a scattered one standing in for the
        # rest of the corpus.
        base = {
            "edgeDistanceFromEnd": {
                "type0A_to_type0B_at-69": 3707,
                "type0A_to_type0B_at-73": 288,
                "type0A_to_type0B_at-82": 52,
                "type0C_to_type0D_at-190": 900,
                "type0C_to_type0D_at-163": 800,
                "type0C_to_type0D_at-101": 174,
            },
        }
        base.update(overrides)
        return base

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(
            the_type0a_to_type0b_edge_is_aligned_to_the_body_end(self.census())
        )

    def test_the_alignment_is_read_off_the_published_distances(self) -> None:
        rows = end_distance_alignment(self.census()["edgeDistanceFromEnd"])
        self.assertEqual(rows["type0A_to_type0B"]["total"], 4047)
        self.assertEqual(rows["type0A_to_type0B"]["aligned"], 3995)
        # -190 and -163 are not 1 mod 4; -101 is.
        self.assertEqual(rows["type0C_to_type0D"]["aligned"], 174)

    def test_an_unaligned_edge_fails(self) -> None:
        census = self.census(edgeDistanceFromEnd={
            "type0A_to_type0B_at-70": 3707,
            "type0C_to_type0D_at-190": 900,
        })
        self.assertFalse(
            the_type0a_to_type0b_edge_is_aligned_to_the_body_end(census)
        )

    def test_a_corpus_where_everything_is_aligned_fails(self) -> None:
        # If every reference were aligned, the observation would be vacuous -- it
        # would be a property of the format's field widths, not of this edge.
        census = self.census(edgeDistanceFromEnd={
            "type0A_to_type0B_at-69": 3707,
            "type0C_to_type0D_at-101": 900,
            "type0D_to_type0A_at-97": 800,
        })
        self.assertFalse(
            the_type0a_to_type0b_edge_is_aligned_to_the_body_end(census)
        )

    def test_a_corpus_with_only_this_edge_fails(self) -> None:
        # Nothing to compare against is not evidence.
        self.assertFalse(the_type0a_to_type0b_edge_is_aligned_to_the_body_end(
            {"edgeDistanceFromEnd": {"type0A_to_type0B_at-69": 3707}}
        ))

    def test_an_empty_census_fails(self) -> None:
        self.assertFalse(the_type0a_to_type0b_edge_is_aligned_to_the_body_end({}))
        self.assertEqual(end_distance_alignment({}), {})

    def test_malformed_keys_are_skipped_rather_than_crashing(self) -> None:
        rows = end_distance_alignment({"nonsense": 5, "type0A_to_type0B_at-x": 7})
        self.assertEqual(rows, {})


class MusicEdgeLocationTests(unittest.TestCase):
    """Types 0x0A and 0x0D place their references in fields; 0x0C uses a list."""

    def census(self, **overrides):
        # Three located edge kinds and two scattered ones, at the measured ratios.
        distances = {}
        for i in range(32):
            distances[f"type0A_to_type0B_at-{69 + 4 * i}"] = 135
        for i in range(83):
            distances[f"type0D_to_type0A_at-{163 + i}"] = 43
        for i in range(56):
            distances[f"type0D_to_type0C_at-{190 + i}"] = 43
        for i in range(2131):
            distances[f"type0C_to_type0D_at-{150 + i}"] = 2
        for i in range(2089):
            distances[f"type0C_to_type0A_at-{218 + i}"] = 2
        base = {"edgeDistanceFromEnd": distances}
        base.update(overrides)
        return base

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(
            the_music_types_split_into_located_and_scattered_references(self.census())
        )

    def test_the_ratio_is_read_off_the_published_distances(self) -> None:
        rows = edges_per_distinct_distance(self.census()["edgeDistanceFromEnd"])
        self.assertEqual(rows["type0A_to_type0B"]["distances"], 32)
        self.assertEqual(rows["type0C_to_type0D"]["distances"], 2131)
        self.assertAlmostEqual(
            rows["type0C_to_type0D"]["edges"] / rows["type0C_to_type0D"]["distances"],
            2.0,
        )

    def test_a_located_edge_becoming_scattered_fails(self) -> None:
        census = self.census()
        for key in list(census["edgeDistanceFromEnd"]):
            if key.startswith("type0A_to_type0B"):
                del census["edgeDistanceFromEnd"][key]
        for i in range(2000):
            census["edgeDistanceFromEnd"][f"type0A_to_type0B_at-{69 + i}"] = 2
        self.assertFalse(
            the_music_types_split_into_located_and_scattered_references(census)
        )

    def test_a_scattered_edge_becoming_located_fails(self) -> None:
        census = self.census()
        for key in list(census["edgeDistanceFromEnd"]):
            if key.startswith("type0C_to_type0D"):
                del census["edgeDistanceFromEnd"][key]
        census["edgeDistanceFromEnd"]["type0C_to_type0D_at-150"] = 4429
        self.assertFalse(
            the_music_types_split_into_located_and_scattered_references(census)
        )

    def test_small_edge_kinds_are_excluded_rather_than_forced(self) -> None:
        # The two edges into type 0x11 score about 6 per distance, between the
        # groups. A hundred-odd samples cannot say which side they belong to.
        census = self.census()
        for i in range(19):
            census["edgeDistanceFromEnd"][f"type0A_to_type11_at-{112 + i}"] = 6
        self.assertTrue(
            the_music_types_split_into_located_and_scattered_references(census)
        )

    def test_an_empty_or_one_sided_census_fails(self) -> None:
        self.assertFalse(the_music_types_split_into_located_and_scattered_references({}))
        self.assertEqual(edges_per_distinct_distance({}), {})
        one_sided = {"edgeDistanceFromEnd": {
            f"type0A_to_type0B_at-{69 + 4 * i}": 135 for i in range(32)
        }}
        self.assertFalse(
            the_music_types_split_into_located_and_scattered_references(one_sided)
        )


class Type0CHierarchyTests(unittest.TestCase):
    """A fourth located relation, with the shape the 0x08/0x12 one has."""

    def census(self, **overrides):
        base = {
            "banks": 5, "objects": 7331, "objectsNamingAParent": 7084,
            "rootsWithNoParent": 192, "parentsOutsideTheBank": 55, "cycles": 0,
            "parentsWithSeveralChildren": 1538,
            "depths": {"depth_0": 247, "depth_1": 361, "depth_2": 1006,
                       "depth_3": 1626, "depth_4": 1916, "depth_5": 1560,
                       "depth_6": 485, "depth_7": 96, "depth_8": 24, "depth_9": 10},
            "childrenPerParent": {"children_1": 1528, "children_2": 1014,
                                  "children_3": 285, "children_4": 71,
                                  "children_5": 37, "children_16": 131},
            "edgeTypes": {"type0A_to_type0D": 3461, "type0D_to_type0C": 2321,
                          "type0C_to_type0C": 716, "type0A_to_type0C": 586},
        }
        base.update(overrides)
        return base

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(
            the_type0c_parent_relation_repeats_the_same_shape(self.census())
        )

    def test_one_cycle_fails(self) -> None:
        self.assertFalse(the_type0c_parent_relation_repeats_the_same_shape(
            self.census(cycles=1)
        ))

    def test_a_shallow_relation_fails(self) -> None:
        # Acyclicity is free when nothing is connected, so the relation must reach
        # past depth one for most of its objects.
        self.assertFalse(the_type0c_parent_relation_repeats_the_same_shape(
            self.census(depths={"depth_0": 7000, "depth_1": 331})
        ))

    def test_one_child_per_parent_fails(self) -> None:
        # That would be the main reference graph's direction, not this one's.
        self.assertFalse(the_type0c_parent_relation_repeats_the_same_shape(
            self.census(parentsWithSeveralChildren=0,
                        childrenPerParent={"children_1": 3066})
        ))

    def test_a_relation_most_objects_do_not_use_fails(self) -> None:
        self.assertFalse(the_type0c_parent_relation_repeats_the_same_shape(
            self.census(objectsNamingAParent=100, rootsWithNoParent=7176)
        ))

    def test_an_empty_census_fails(self) -> None:
        self.assertFalse(the_type0c_parent_relation_repeats_the_same_shape({}))
        self.assertFalse(the_type0c_parent_relation_repeats_the_same_shape(
            self.census(objects=0)
        ))

    def test_a_relation_confined_to_one_type_pair_fails(self) -> None:
        # 0x0C nesting inside itself alone would be a far weaker claim than the
        # chain 0x0A -> 0x0D -> 0x0C -> 0x0C that the corpus actually shows.
        self.assertFalse(the_type0c_parent_relation_repeats_the_same_shape(
            self.census(edgeTypes={"type0C_to_type0C": 7084})
        ))

    def test_the_reader_rejects_parent_kinds_that_do_not_partition(self) -> None:
        with self.assertRaises(ValueError):
            _read_type0c_hierarchy_census(self.census(rootsWithNoParent=999), "pkg")

    def test_an_absent_census_reads_as_empty(self) -> None:
        self.assertEqual(_read_type0c_hierarchy_census(None, "pkg")["objects"], 0)


class ParentFieldInverseTests(unittest.TestCase):
    """The parent field and the reference graph must be exact inverses."""

    def census(self, **overrides):
        base = {
            "checkable": 199445, "parentNamesTheChildBack": 199445,
            "parentDoesNotNameTheChild": 0,
            "namesSomethingOutsideTheBank": 1598, "parentDeclaresNoChildren": 10448,
            "edgeTypes": {
                "type02_to_type05": 129413, "type07_to_type07": 28425,
                "type05_to_type06": 17572, "type05_to_type07": 7138,
                "type02_to_type07": 6881, "type06_to_type07": 3653,
                "type09_to_type07": 3308,
            },
            "disagreementTypes": {},
        }
        base.update(overrides)
        return base

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(the_parent_field_inverts_the_reference_graph(self.census()))

    def test_a_single_disagreement_fails(self) -> None:
        # Equality, not a rate: one disagreement means one of the two readings has
        # drifted, and which one is then worth knowing.
        self.assertFalse(the_parent_field_inverts_the_reference_graph(self.census(
            parentNamesTheChildBack=199444, parentDoesNotNameTheChild=1,
            disagreementTypes={"type02_under_type05": 1},
        )))

    def test_a_relation_confined_to_a_few_type_pairs_fails(self) -> None:
        self.assertFalse(the_parent_field_inverts_the_reference_graph(self.census(
            edgeTypes={"type02_to_type05": 199445}
        )))

    def test_an_empty_census_fails(self) -> None:
        self.assertFalse(the_parent_field_inverts_the_reference_graph({}))
        self.assertFalse(the_parent_field_inverts_the_reference_graph(
            self.census(checkable=0, parentNamesTheChildBack=0)
        ))

    def test_the_reader_rejects_outcomes_that_do_not_cover_the_checkable(self) -> None:
        with self.assertRaises(ValueError):
            _read_parent_field_census(
                self.census(parentNamesTheChildBack=5), "pkg"
            )

    def test_the_reader_rejects_disagreement_types_that_do_not_add_up(self) -> None:
        with self.assertRaises(ValueError):
            _read_parent_field_census(
                self.census(disagreementTypes={"type02_under_type05": 3}), "pkg"
            )

    def test_an_absent_census_reads_as_empty(self) -> None:
        self.assertEqual(_read_parent_field_census(None, "pkg")["checkable"], 0)


class Type11BoundedFloatTests(unittest.TestCase):
    """A float field is established by its neighbours failing, not by its own values."""

    def census(self, **overrides):
        base = {
            "boundedFloatsTested": 3715, "boundedFloatsInBand": 3715,
            "floatControlsTested": 4806, "floatControlsInBand": 420,
        }
        base.update(overrides)
        return base

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(
            the_type11_entry_header_carries_a_bounded_float(self.census())
        )

    def test_controls_that_also_look_like_floats_fail(self) -> None:
        # Almost any 32-bit word is a finite float, so the claim rests entirely on
        # the neighbouring words not landing in the band.
        self.assertFalse(the_type11_entry_header_carries_a_bounded_float(
            self.census(floatControlsInBand=4000)
        ))

    def test_a_field_that_often_leaves_the_band_fails(self) -> None:
        self.assertFalse(the_type11_entry_header_carries_a_bounded_float(
            self.census(boundedFloatsInBand=2000)
        ))

    def test_an_untested_census_fails_rather_than_passing_vacuously(self) -> None:
        self.assertFalse(the_type11_entry_header_carries_a_bounded_float({}))
        self.assertFalse(the_type11_entry_header_carries_a_bounded_float(
            self.census(boundedFloatsTested=0, boundedFloatsInBand=0)
        ))
        self.assertFalse(the_type11_entry_header_carries_a_bounded_float(
            self.census(floatControlsTested=0, floatControlsInBand=0)
        ))

    def test_the_reader_rejects_more_in_band_than_tested(self) -> None:
        with self.assertRaises(ValueError):
            _read_type11_header_census(
                {key: 0 for key in TYPE11_HEADER_SCALARS}
                | {"elementCountValues": {}, "curveCodes": {},
                   "boundedFloatsTested": 1, "boundedFloatsInBand": 5},
                "pkg",
            )


class Type0ACountedArrayTests(unittest.TestCase):
    """The reference is a counted array, and the count is right every time."""

    def census(self, **overrides):
        base = {
            "bodies": 4158, "bodiesWithNoReference": 255, "noRoomForACount": 0,
            "checkable": 3903, "countMatchesTheRun": 3903, "countDoesNotMatch": 0,
            "runLengths": {"references_1": 3565, "references_2": 271,
                           "references_3": 58, "references_4": 5, "references_6": 4},
        }
        base.update(overrides)
        return base

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(the_type0a_reference_is_a_counted_array(self.census()))

    def test_a_single_mismatch_fails(self) -> None:
        # A count read from a wrongly chosen offset gives a number unrelated to how
        # many references follow, so one disagreement means the step-back is wrong.
        self.assertFalse(the_type0a_reference_is_a_counted_array(self.census(
            countMatchesTheRun=3902, countDoesNotMatch=1
        )))

    def test_an_all_single_element_corpus_fails(self) -> None:
        # If every array held one element, a count and the constant 1 would be
        # indistinguishable -- which is the degenerate case for this claim.
        self.assertFalse(the_type0a_reference_is_a_counted_array(self.census(
            countMatchesTheRun=3903, runLengths={"references_1": 3903}
        )))

    def test_two_run_lengths_are_not_enough(self) -> None:
        self.assertFalse(the_type0a_reference_is_a_counted_array(self.census(
            countMatchesTheRun=3903,
            runLengths={"references_1": 3600, "references_2": 303},
        )))

    def test_an_empty_census_fails(self) -> None:
        self.assertFalse(the_type0a_reference_is_a_counted_array({}))
        self.assertFalse(the_type0a_reference_is_a_counted_array(
            self.census(checkable=0, countMatchesTheRun=0, runLengths={})
        ))

    def test_the_reader_rejects_a_census_that_does_not_partition_its_bodies(self) -> None:
        with self.assertRaises(ValueError):
            _read_type0a_array_census(self.census(bodies=99), "pkg")

    def test_the_reader_rejects_run_lengths_that_do_not_cover_the_matches(self) -> None:
        with self.assertRaises(ValueError):
            _read_type0a_array_census(
                self.census(runLengths={"references_1": 3}), "pkg"
            )

    def test_an_absent_census_reads_as_empty(self) -> None:
        self.assertEqual(_read_type0a_array_census(None, "pkg")["bodies"], 0)


class Type11EntryCountTests(unittest.TestCase):
    """The entry count is as untested as the element count, and for the same reason."""

    def base(self, **overrides):
        c = {"elementCountValues": {"elements_1": 3715},
             "entryCountValues": {"entries_1": 3715}}
        c.update(overrides)
        return c

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(the_type11_element_count_is_not_yet_a_count(self.base()))

    def test_a_body_closing_with_two_entries_fails_the_gate(self) -> None:
        # The good news case: it would mean the entry count has finally been read at
        # a second value, and the note saying the multi-entry layout is unparsed
        # would need revising.
        self.assertFalse(the_type11_element_count_is_not_yet_a_count(
            self.base(entryCountValues={"entries_1": 3700, "entries_2": 15})
        ))

    def test_an_absent_entry_census_does_not_break_the_gate(self) -> None:
        # Older reports carry no entry census; the element half still applies.
        self.assertTrue(the_type11_element_count_is_not_yet_a_count(
            {"elementCountValues": {"elements_1": 3715}}
        ))

    def test_the_reader_defaults_the_entry_census_when_absent(self) -> None:
        got = _read_type11_header_census(
            {key: 0 for key in TYPE11_HEADER_SCALARS}
            | {"elementCountValues": {}, "curveCodes": {}},
            "pkg",
        )
        self.assertEqual(got["entryCountValues"], {})
        self.assertEqual(_read_type11_header_census(None, "pkg")["entryCountValues"], {})

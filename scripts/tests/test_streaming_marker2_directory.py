from __future__ import annotations

import copy
import unittest

from scripts.game_data import streaming as fmt
from scripts.tests.test_streaming import _packed, _parallel_target_data_root
from scripts.game_data.streaming_marker2_directory import (
    collect_marker2_directory,
)


def fixture(*, first_marker: int = 2, second_marker: int = 17,
            root_marker: int = 2, alias: bool = False):
    data = bytearray(_parallel_target_data_root())
    data[84] = root_marker
    data[236] = first_marker
    data[237] = second_marker
    if alias:
        data[248:252] = (300 - 248).to_bytes(4, "little")
    clear = bytes(data)
    parsed = fmt.parse_streaming_file(
        "streaming", _packed(clear), native_layout_validated=True,
        include_certified_ranges=True,
    )
    return clear, parsed


def collect(data: bytes, parsed: dict):
    return collect_marker2_directory(
        data, source="fixture.bytes", family="streaming", parsed=parsed,
    )


class Marker2DirectoryTests(unittest.TestCase):
    def test_normal_preserves_offsets_key_occurrence_and_occupancy(self):
        data, parsed = fixture()
        result = collect(data, parsed)
        self.assertEqual(result["counts"]["allNestedTargetReferences"], 2)
        self.assertEqual(result["nestedMarkerCounts"], {2: 1, 17: 1})
        self.assertEqual(len(result["rows"]), 1)
        row = result["rows"][0]
        self.assertEqual(
            (row["outerRowIndex"], row["outerRowOffset"], row["rootMarkerOffset"],
             row["rowSelectorU32"], row["rowSelectorOffset"]),
            (0, 144, 84, 6, 156),
        )
        self.assertEqual(
            (row["nestedTableOffset"], row["elementIndex"], row["key"], row["keyOffset"],
             row["keyOccurrenceCountInTable"], row["markerOffset"],
             row["targetSlotOffset"], row["targetStart"]),
            (200, 0, 11, 224, 1, 236, 244, 300),
        )
        self.assertEqual(row["targetWidthStatus"], "unresolved")
        self.assertEqual(row["targetOwnedBytes"], 0)

    def test_unknown_marker_retains_raw_slot_word_but_not_inferred_target(self):
        data, parsed = fixture(first_marker=255, second_marker=2)
        result = collect(data, parsed)
        self.assertEqual(result["nestedMarkerCounts"], {2: 1, 255: 1})
        row = result["rows"][0]
        self.assertFalse(any(item["marker"] == 255 for item in row["gapTargetReferences"]))
        self.assertFalse(row["targetOccupancyComplete"])
        self.assertEqual(row["unresolvedMarkerReferenceCountInFile"], 1)
        self.assertEqual(result["counts"]["unresolvedMarkerRepresentations"], 1)
        unresolved = result["unresolvedMarkerRows"][0]
        self.assertEqual((unresolved["marker"], unresolved["targetSlotOffset"]), (255, 244))
        self.assertEqual(unresolved["rawTargetSlotWordU32"], 56)
        self.assertNotIn("targetStart", unresolved)
        self.assertEqual(result["unknownMarkerDisposition"],
                         "raw marker/key/slot word retained; target representation unresolved; occupancy incomplete")

    def test_unknown_marker_slot_word_is_not_validated_as_uoffset(self):
        data, _parsed = fixture(first_marker=255, second_marker=2)
        for raw_word in (0, 0xFFFFFFFF):
            with self.subTest(raw_word=raw_word):
                changed = bytearray(data)
                changed[244:248] = raw_word.to_bytes(4, "little")
                parsed = fmt.parse_streaming_file(
                    "streaming", _packed(bytes(changed)), native_layout_validated=True,
                    include_certified_ranges=True,
                )
                result = collect(bytes(changed), parsed)
                unresolved = result["unresolvedMarkerRows"][0]
                self.assertEqual(unresolved["rawTargetSlotWordU32"], raw_word)
                self.assertEqual(result["status"],
                                 "exact-marker2-directory-with-incomplete-unknown-marker-occupancy")

    def test_aliases_are_preserved_not_rejected_or_owned(self):
        data, parsed = fixture(first_marker=2, second_marker=2, alias=True)
        result = collect(data, parsed)
        self.assertEqual(result["counts"]["marker2References"], 2)
        self.assertEqual(result["counts"]["uniqueNestedTargetStarts"], 1)
        self.assertEqual([row["targetReferenceCountInFile"] for row in result["rows"]], [2, 2])
        self.assertEqual([len(row["gapTargetReferences"]) for row in result["rows"]], [2, 2])

    def test_duplicate_keys_are_preserved_as_table_local_ambiguity(self):
        data, _parsed = fixture(first_marker=2, second_marker=2)
        changed = bytearray(data)
        changed[228:232] = changed[224:228]
        packed = _packed(bytes(changed))
        parsed = fmt.parse_streaming_file(
            "streaming", packed, native_layout_validated=True,
            include_certified_ranges=True,
        )
        rows = collect(bytes(changed), parsed)["rows"]
        self.assertEqual([row["keyOccurrenceCountInTable"] for row in rows], [2, 2])
        self.assertEqual([row["keyStatus"] for row in rows], ["ambiguous", "ambiguous"])

    def test_absent_selector_stays_absent_not_serialized_zero(self):
        data, _parsed = fixture()
        changed = bytearray(data)
        changed[136:138] = bytes(2)
        parsed = fmt.parse_streaming_file(
            "streaming", _packed(bytes(changed)), native_layout_validated=True,
            include_certified_ranges=True,
        )
        row = collect(bytes(changed), parsed)["rows"][0]
        self.assertIsNone(row["rowSelectorU32"])
        self.assertIsNone(row["rowSelectorOffset"])
        self.assertEqual(row["rowSelectorStatus"], "serialized-field2-absent")

    def test_target_at_final_payload_byte_is_bounded_without_four_byte_width(self):
        data, _parsed = fixture(first_marker=2)
        changed = bytearray(data)
        final = len(changed) - 1
        changed[244:248] = (final - 244).to_bytes(4, "little")
        parsed = fmt.parse_streaming_file(
            "streaming", _packed(bytes(changed)), native_layout_validated=True,
            include_certified_ranges=True,
        )
        row = collect(bytes(changed), parsed)["rows"][0]
        self.assertEqual(row["targetStart"], final)
        self.assertEqual(row["targetWidthStatus"], "unresolved")

    def test_non_marker2_outer_shape_does_not_decode_field2_as_selector(self):
        for marker in (1, 3, 16):
            with self.subTest(marker=marker):
                data, parsed = fixture(root_marker=marker)
                row = collect(data, parsed)["rows"][0]
                self.assertEqual(row["rootMarker"], marker)
                self.assertIsNone(row["rowSelectorU32"])
                self.assertIsNone(row["rowSelectorOffset"])
                self.assertEqual(row["rowSelectorStatus"],
                                 "not-decoded-for-non-marker2-outer-shape")

    def test_truncated_current_bytes_fail_before_traversal(self):
        data, parsed = fixture()
        with self.assertRaisesRegex(ValueError, "decoded length"):
            collect(data[:-1], parsed)

    def test_trailing_current_bytes_fail_against_authenticated_length(self):
        data, parsed = fixture()
        with self.assertRaisesRegex(ValueError, "decoded length"):
            collect(data + b"\xA5", parsed)

    def test_malformed_nested_parallel_count_fails_closed(self):
        data, parsed = fixture()
        changed = bytearray(data)
        changed[232:236] = (3).to_bytes(4, "little")
        changed_parsed = copy.deepcopy(parsed)
        changed_parsed["decodedBytes"] = len(changed)
        with self.assertRaisesRegex(ValueError, "parallel counts differ|outside payload"):
            collect(bytes(changed), changed_parsed)

    def test_zero_and_overflow_target_offsets_fail_closed_without_width_assumption(self):
        data, parsed = fixture()
        for value in (0, 0xFFFFFFFF):
            with self.subTest(value=value):
                changed = bytearray(data)
                changed[244:248] = value.to_bytes(4, "little")
                with self.assertRaisesRegex(ValueError, "expected nonzero forward target"):
                    collect(bytes(changed), {**parsed, "decodedBytes": len(changed)})

    def test_parser_marker_count_omission_fails_closed(self):
        data, parsed = fixture(first_marker=255, second_marker=2)
        forged = copy.deepcopy(parsed)
        forged["anonymousParallelSubgraph"]["nestedElementMarkerCounts"] = {2: 1}
        with self.assertRaisesRegex(ValueError, "nested marker counts"):
            collect(data, forged)

    def test_boolean_parser_counts_do_not_pass_as_integers(self):
        data, parsed = fixture()
        for path, value, message in (
            (("orderedRootWitness", "rowCount"), True, "root row count"),
            ((None, "field5Field3NestedTableCount"), True, "nested table count"),
            (("nestedElementMarkerCounts", 2), True, "marker 2 count"),
        ):
            with self.subTest(path=path):
                forged = copy.deepcopy(parsed)
                graph = forged["anonymousParallelSubgraph"]
                owner = graph if path[0] is None else graph[path[0]]
                owner[path[1]] = value
                with self.assertRaisesRegex(ValueError, message):
                    collect(data, forged)

    def test_certified_overlap_and_unsorted_inputs_fail_closed(self):
        data, parsed = fixture()
        ranges = list(parsed["decodedCertifiedRanges"])
        for broken in (list(reversed(ranges)), ranges + [(0, 4, "root-uoffset")]):
            with self.subTest():
                with self.assertRaisesRegex(ValueError, "sorted duplicate-free"):
                    collect_marker2_directory(
                        data, source="fixture.bytes", family="streaming", parsed=parsed,
                        certified_ranges=broken,
                    )


if __name__ == "__main__":
    unittest.main()

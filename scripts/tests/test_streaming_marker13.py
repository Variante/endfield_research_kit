from __future__ import annotations

import struct
import unittest

from scripts.game_data.streaming_marker13 import (
    parse_marker13_selector9_gaps,
)


def fixture(*, selector=9, selector_present=True, marker=13, key=0xFF000000):
    data = bytearray(80)
    data[4] = 2
    if selector_present:
        struct.pack_into("<I", data, 8, selector)
    struct.pack_into("<I", data, 12, key)
    data[16] = marker
    struct.pack_into("<I", data, 20, 20)  # target 40
    struct.pack_into("<4I", data, 40, 11, 22, 33, 44)
    row = {
        "outerRowIndex": 3,
        "outerRowOffset": 64,
        "rootMarker": 2,
        "rootMarkerOffset": 4,
        "rowSelectorU32": selector if selector_present else None,
        "rowSelectorLowByte": selector & 0xFF if selector_present else None,
        "rowSelectorOffset": 8 if selector_present else None,
        "nestedTableOffset": 68,
        "nestedElementCount": 1,
        "elementIndex": 0,
        "key": key,
        "keyOffset": 12,
        "keyOccurrenceCountInTable": 1,
        "marker": marker,
        "markerOffset": 16,
        "targetSlotOffset": 20,
        "targetStart": 40,
    }
    ranges = [(0, 24, "table"), (24, 40, "width-4-vector"), (56, 64, "table")]
    return bytes(data), row, ranges


def parse(data, row, ranges, **kwargs):
    return parse_marker13_selector9_gaps(
        data,
        source="fixture.bytes",
        family=kwargs.pop("family", "streaming"),
        rows=[row],
        certified_ranges=ranges,
        native_layout_validated=kwargs.pop("native_layout_validated", True),
        **kwargs,
    )


class Marker13Gap16Tests(unittest.TestCase):
    def test_normal_exact_gap_projects_four_anonymous_u32(self):
        data, row, ranges = fixture()
        result = parse(data, row, ranges)
        self.assertEqual(result["status"], "exact-anonymous-physical-gaps")
        self.assertEqual(result["counts"], {"exact": 1, "ambiguous": 0, "unsupportedContext": 0})
        self.assertEqual(result["partitionedBytes"], 16)
        self.assertEqual(result["targetOwnedBytes"], 0)
        parsed = result["rows"][0]
        self.assertEqual(parsed["physicalGapRange"], {"start": 40, "end": 56, "length": 16})
        self.assertEqual(
            [item["anonymousU32"] for item in parsed["anonymousScalar32Projection"]],
            [11, 22, 33, 44],
        )
        self.assertEqual(parsed["previousCertifiedRanges"][0]["kind"], "width-4-vector")
        self.assertEqual(parsed["nextCertifiedRanges"][0]["kind"], "table")
        self.assertEqual(parsed["serializedSizeStatus"], "unknown")

    def test_truncated_target_fails_before_selecting_extent(self):
        data, row, ranges = fixture()
        with self.assertRaisesRegex(ValueError, r"target at 40: expected 16 readable bytes, actual 14"):
            parse(data[:54], row, ranges[:2])

    def test_malformed_target_slot_offset_fails_with_bounded_diagnostic(self):
        data, row, ranges = fixture()
        row["targetSlotOffset"] = -1
        with self.assertRaisesRegex(ValueError, r"target slot at -1: expected 4 readable bytes"):
            parse(data, row, ranges)

    def test_zero_relative_target_fails(self):
        data, row, ranges = fixture()
        changed = bytearray(data)
        struct.pack_into("<I", changed, 20, 0)
        with self.assertRaisesRegex(ValueError, r"expected positive in-bounds uoffset"):
            parse(bytes(changed), row, ranges)

    def test_target_exactly_at_eof_fails_during_uoffset_validation(self):
        data, row, ranges = fixture()
        changed = bytearray(data)
        struct.pack_into("<I", changed, 20, len(changed) - 20)
        row["targetStart"] = len(changed)
        with self.assertRaisesRegex(ValueError, r"expected positive in-bounds uoffset"):
            parse(bytes(changed), row, ranges)

    def test_extra_gap_fails_instead_of_using_native_width(self):
        data, row, ranges = fixture()
        ranges[-1] = (60, 64, "table")
        with self.assertRaisesRegex(ValueError, r"expected following certified start in \[56, 58\], actual 60 .*gap 20"):
            parse(data, row, ranges)

    def test_gap18_keeps_nonzero_residual_opaque_without_extent_claim(self):
        data, row, ranges = fixture()
        changed = bytearray(data)
        changed[56:58] = b"\xA5\x5A"
        ranges[-1] = (58, 64, "vtable")
        result = parse(bytes(changed), row, ranges)
        parsed = result["rows"][0]
        self.assertEqual(parsed["physicalGapRange"], {"start": 40, "end": 58, "length": 18})
        self.assertEqual(parsed["nativeReadWindowRange"], {"start": 40, "end": 56, "length": 16})
        self.assertEqual(parsed["residualOpaqueRange"], {"start": 56, "end": 58, "length": 2})
        self.assertEqual((result["partitionedBytes"], result["targetOwnedBytes"]), (16, 0))
        self.assertEqual(parsed["serializedSizeStatus"], "unknown")

    def test_unobserved_gap17_is_rejected(self):
        data, row, ranges = fixture()
        ranges[-1] = (57, 64, "vtable")
        with self.assertRaisesRegex(ValueError, r"gap 17"):
            parse(data, row, ranges)

    def test_returned_profile_cannot_expand_accepted_gap_lengths(self):
        data, row, ranges = fixture()
        result = parse(data, row, ranges)
        result["profile"]["physicalGapLengths"] += (20,)
        ranges[-1] = (60, 64, "vtable")
        with self.assertRaisesRegex(ValueError, r"gap 20"):
            parse(data, row, ranges)

    def test_short_gap_or_overlap_fails(self):
        data, row, ranges = fixture()
        ranges[-1] = (52, 64, "table")
        with self.assertRaisesRegex(ValueError, r"expected no certified overlap"):
            parse(data, row, ranges)

    def test_missing_following_range_at_trailing_certified_end_fails(self):
        data, row, ranges = fixture()
        with self.assertRaisesRegex(ValueError, r"expected following certified start 56, actual none"):
            parse(data, row, ranges[:2])

    def test_duplicate_key_is_explicit_ambiguous_and_projects_nothing(self):
        data, row, ranges = fixture()
        row["keyOccurrenceCountInTable"] = 2
        result = parse(data, row, ranges)
        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual(result["partitionedBytes"], 0)
        self.assertEqual(result["rows"][0]["status"], "ambiguous")
        self.assertNotIn("physicalGapRange", result["rows"][0])

    def test_missing_zero_or_boolean_occurrence_count_is_malformed_not_ambiguous(self):
        data, row, ranges = fixture()
        for value in (None, 0, True):
            row["keyOccurrenceCountInTable"] = value
            with self.subTest(value=value), self.assertRaisesRegex(
                ValueError, r"expected positive integer"
            ):
                parse(data, row, ranges)

    def test_exact_duplicate_certified_ranges_are_deduplicated(self):
        data, row, ranges = fixture()
        duplicated = [ranges[0], ranges[0], ranges[1], ranges[1], ranges[2], ranges[2]]
        result = parse(data, row, duplicated)
        parsed = result["rows"][0]
        self.assertEqual(len(parsed["previousCertifiedRanges"]), 1)
        self.assertEqual(len(parsed["nextCertifiedRanges"]), 1)

    def test_native_gate_is_mandatory(self):
        data, row, ranges = fixture()
        with self.assertRaisesRegex(ValueError, r"expected exact boolean True, actual False"):
            parse(data, row, ranges, native_layout_validated=False)
        with self.assertRaisesRegex(ValueError, r"expected exact boolean True, actual 1"):
            parse(data, row, ranges, native_layout_validated=1)

    def test_nonstreaming_family_fails_before_row_selection(self):
        data, row, ranges = fixture()
        with self.assertRaisesRegex(ValueError, r"expected selected family 'streaming', actual 'init'"):
            parse(data, row, ranges, family="init")

    def test_wrong_marker_in_selected_context_fails_closed(self):
        data, row, ranges = fixture(marker=12)
        with self.assertRaisesRegex(ValueError, r"expected 13, actual 12"):
            parse(data, row, ranges)

    def test_directory_marker_mismatch_fails(self):
        data, row, ranges = fixture()
        row["marker"] = 12
        with self.assertRaisesRegex(ValueError, r"expected directory 12, actual bytes 13"):
            parse(data, row, ranges)

    def test_selector_absent_is_explicit_unsupported(self):
        data, row, ranges = fixture(selector_present=False)
        result = parse(data, row, ranges)
        self.assertEqual(result["status"], "unsupported-context-only")
        self.assertEqual(result["counts"]["unsupportedContext"], 1)
        self.assertEqual(result["rows"][0]["status"], "unsupported-context")
        self.assertIn("raw row selector None", result["rows"][0]["reason"])

    def test_same_low_byte_but_nonexact_raw_selector_is_unsupported(self):
        data, row, ranges = fixture(selector=0x109)
        result = parse(data, row, ranges)
        self.assertEqual(result["rows"][0]["status"], "unsupported-context")
        self.assertIn("raw row selector 265", result["rows"][0]["reason"])

    def test_other_full_key_is_unsupported(self):
        data, row, ranges = fixture(key=0xFF000001)
        result = parse(data, row, ranges)
        self.assertEqual(result["rows"][0]["status"], "unsupported-context")
        self.assertIn("full key 0xff000001", result["rows"][0]["reason"])

    def test_unsorted_or_overlapping_certified_ranges_fail(self):
        data, row, ranges = fixture()
        with self.assertRaisesRegex(ValueError, r"actual unsorted"):
            parse(data, row, list(reversed(ranges)))
        with self.assertRaisesRegex(ValueError, r"expected no non-identical overlap"):
            parse(data, row, [(0, 24, "table"), (20, 40, "vector"), (56, 64, "table")])

    def test_trailing_payload_bytes_do_not_define_or_extend_gap(self):
        data, row, ranges = fixture()
        result = parse(data + b"unowned trailing bytes", row, ranges)
        parsed = result["rows"][0]
        self.assertEqual(parsed["physicalGapRange"]["end"], 56)
        self.assertEqual(parsed["partitionedBytes"], 16)


if __name__ == "__main__":
    unittest.main()

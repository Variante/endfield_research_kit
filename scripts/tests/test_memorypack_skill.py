from __future__ import annotations

import struct
import subprocess
import sys
import unittest

from scripts.game_data.memorypack.skill import (
    frame_skill_common_prefix,
    frame_skill_memorypack,
)
from scripts.game_data.memorypack.schemas import SKILL_MEMBER_COUNT
from scripts.game_data.memorypack.buff import read_skill_gameplay_tag_record


def _empty_terminal_shape(*, first: bool = False, last: bool = True) -> bytes:
    return b"".join(
        (
            bytes([int(first)]),
            struct.pack("<I", 0),
            struct.pack("<I", 0),
            struct.pack("<I", 0),
            bytes([int(last)]),
        )
    )


class SkillMemoryPackFramingTests(unittest.TestCase):
    def test_legacy_census_cli_cannot_rebind_old_bytes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "scripts.game_data.memorypack.skill",
             "old-census.json", "current-boundary.json",
             "--expected-input-set-sha256", "A" * 64],
            capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(0, completed.returncode)
        self.assertIn("Historical census rebinding is not supported", completed.stderr)
        self.assertEqual("", completed.stdout)

    def test_terminal_rejects_unsupported_record_member_counts(self) -> None:
        for count in (0, 3, 255):
            with self.subTest(count=count):
                record = bytes([count]) + struct.pack("<II", 0x12345678, 0xFFFFFFFF)
                with self.assertRaisesRegex(
                    ValueError, f"offset=0 expected=1\\|2 actual={count}"
                ):
                    read_skill_gameplay_tag_record(record, 0, "anonymous", 0)
                terminal = b"\x01" + struct.pack("<I", 1) + record + b"\x00" * 9
                framed = frame_skill_memorypack(bytes([SKILL_MEMBER_COUNT, 0x7F]) + terminal)
                self.assertEqual("terminal-shape-unresolved", framed["status"])

    def test_supported_record_member_counts_have_exact_bounds(self) -> None:
        for count in (1, 2):
            with self.subTest(count=count):
                record = bytes([count]) + struct.pack("<I", 0x12345678)
                if count == 2:
                    record += struct.pack("<I", 0xFFFFFFFF)
                parsed, end = read_skill_gameplay_tag_record(record, 0, "anonymous", 0)
                self.assertEqual(len(record), end)
                self.assertEqual(len(record), parsed["byteLength"])
                self.assertEqual("0x0", parsed["offset"])

    def test_common_prefix_stops_before_first_record_body_in_first_list(self) -> None:
        data = b"".join((
            bytes([SKILL_MEMBER_COUNT, 2]),
            struct.pack("<I", 1),
            b"\x02",
            b"opaque-union-body",
        ))

        framed = frame_skill_common_prefix(data)

        self.assertEqual("stopped-at-first-opaque-record-body", framed["status"])
        self.assertEqual("0x6", framed["cursorOffset"])
        self.assertEqual(0, framed["stopListIndex"])
        self.assertEqual(2, framed["recordLists"][0]["firstRecordMemberCount"])
        self.assertFalse(framed["wholeSchemaExact"])

    def test_common_prefix_empty_first_list_reaches_second_record_body(self) -> None:
        data = b"".join((
            bytes([SKILL_MEMBER_COUNT, 2]),
            struct.pack("<I", 0),
            struct.pack("<I", 3),
            b"\x04",
            b"opaque-union-body",
        ))

        framed = frame_skill_common_prefix(data)

        self.assertEqual("stopped-at-first-opaque-record-body", framed["status"])
        self.assertEqual("0xa", framed["cursorOffset"])
        self.assertEqual(1, framed["stopListIndex"])
        self.assertEqual([0, 3], [row["count"] for row in framed["recordLists"]])
        self.assertEqual(4, framed["recordLists"][1]["firstRecordMemberCount"])

    def test_common_prefix_two_empty_lists_close_anonymous_envelope(self) -> None:
        data = bytes([SKILL_MEMBER_COUNT, 2]) + struct.pack("<II", 0, 0) + b"opaque"

        framed = frame_skill_common_prefix(data)

        self.assertEqual("anonymous-envelope-count-prefix-consumed", framed["status"])
        self.assertEqual("0xa", framed["cursorOffset"])
        self.assertNotIn("stopListIndex", framed)

    def test_common_prefix_count_requires_minimum_marker_bytes(self) -> None:
        for data, offset in (
            (bytes([SKILL_MEMBER_COUNT, 2]) + struct.pack("<I", 2) + b"\x02", 2),
            (bytes([SKILL_MEMBER_COUNT, 2]) + struct.pack("<II", 0, 2) + b"\x04", 6),
        ):
            with self.subTest(data=data):
                with self.assertRaisesRegex(
                    ValueError, f"offset={offset} expected<=remaining-marker-bytes:1 actual=2"
                ):
                    frame_skill_common_prefix(data)

    def test_common_prefix_rejects_corrupt_counts_markers_and_truncation(self) -> None:
        with self.assertRaisesRegex(ValueError, "nested-member-count expected=2 actual=3"):
            frame_skill_common_prefix(bytes([SKILL_MEMBER_COUNT, 3]) + b"\x00" * 8)
        with self.assertRaisesRegex(ValueError, "record-list-0-count max=256 actual=257"):
            frame_skill_common_prefix(bytes([SKILL_MEMBER_COUNT, 2]) + struct.pack("<I", 257))
        with self.assertRaisesRegex(ValueError, "record-list-0:first-record-member-count"):
            frame_skill_common_prefix(
                bytes([SKILL_MEMBER_COUNT, 2]) + struct.pack("<I", 1) + b"\x03"
            )
        with self.assertRaisesRegex(ValueError, "record-list-1:first-record-member-count"):
            frame_skill_common_prefix(
                bytes([SKILL_MEMBER_COUNT, 2]) + struct.pack("<II", 0, 1) + b"\x03"
            )
        with self.assertRaisesRegex(ValueError, "record-list-1-count:truncated-u32"):
            frame_skill_common_prefix(bytes([SKILL_MEMBER_COUNT, 2]) + struct.pack("<I", 0))

    def test_unique_terminal_shape_keeps_prefix_opaque(self) -> None:
        opaque = b"\x7f\x7e\x7d"
        data = bytes([SKILL_MEMBER_COUNT]) + opaque + _empty_terminal_shape()

        framed = frame_skill_memorypack(data)

        self.assertEqual("unique-exact-terminal-shape", framed["status"])
        self.assertEqual(1, framed["candidateCount"])
        candidate = framed["candidates"][0]
        self.assertEqual("0x4", candidate["startOffset"])
        self.assertEqual(len(_empty_terminal_shape()), candidate["byteLength"])
        self.assertEqual(len(opaque), candidate["opaquePrefix"]["byteLength"])
        self.assertEqual("unresolved", candidate["semanticFieldNamesStatus"])
        self.assertFalse(framed["wholeSchemaExact"])

    def test_ambiguous_candidates_are_preserved(self) -> None:
        # The one-member record-list wrapper begins with 0x01.  With a false
        # leading bool, both the bool and wrapper bytes can satisfy the same
        # exact terminal shape, so the parser must retain both starts.
        ambiguous_terminal = b"".join(
            (
                b"\x00",  # possible leading bool
                b"\x01",  # possible wrapper member count / shifted bool
                struct.pack("<I", 1),
                b"\x01" + struct.pack("<I", 0x8CF01A14),
                struct.pack("<I", 0),
                struct.pack("<I", 0),
                b"\x00",
            )
        )
        data = bytes([SKILL_MEMBER_COUNT]) + ambiguous_terminal

        framed = frame_skill_memorypack(data)

        self.assertEqual("ambiguous-exact-terminal-shape", framed["status"])
        self.assertGreaterEqual(framed["candidateCount"], 2)
        self.assertEqual(
            sorted(candidate["startOffset"] for candidate in framed["candidates"]),
            [candidate["startOffset"] for candidate in framed["candidates"]],
        )
        self.assertEqual(
            "one-byte-bool-vs-counted-wrapper-collision",
            framed["ambiguity"]["kind"],
        )
        self.assertEqual([1, 0, 0], framed["ambiguity"]["sharedCountedRecordCounts"])
        self.assertEqual(
            "unresolved-both-exact-to-eof",
            framed["ambiguity"]["resolutionStatus"],
        )

    def test_empty_wrapper_collision_is_not_misreported_unique(self) -> None:
        data = bytes.fromhex("307f000100000000000000000000000000")
        framed = frame_skill_memorypack(data, source="empty-wrapper.fixture")
        self.assertEqual("ambiguous-exact-terminal-shape", framed["status"])
        self.assertEqual(
            [("0x2", "one-member-wrapper"), ("0x3", "counted")],
            [(row["startOffset"], row["encoding"]) for row in framed["candidates"]],
        )
        self.assertEqual([0, 0, 0], framed["ambiguity"]["sharedCountedRecordCounts"])
        for candidate in framed["candidates"]:
            spans = [member["range"] for member in candidate["members"]]
            self.assertEqual(int(candidate["startOffset"], 0), spans[0]["start"])
            self.assertEqual(len(data), spans[-1]["end"])
            self.assertTrue(all(a["end"] == b["start"] for a, b in zip(spans, spans[1:])))

    def test_ambiguous_counted_record_collision_rejects_corrupt_count(self) -> None:
        terminal = bytearray(b"".join(
            (
                b"\x00",
                b"\x01",
                struct.pack("<I", 1),
                b"\x01" + struct.pack("<I", 0x8CF01A14),
                struct.pack("<I", 0),
                struct.pack("<I", 0),
                b"\x00",
            )
        ))
        struct.pack_into("<I", terminal, 2, 2)

        framed = frame_skill_memorypack(bytes([SKILL_MEMBER_COUNT]) + bytes(terminal))

        self.assertEqual("terminal-shape-unresolved", framed["status"])
        self.assertEqual([], framed["candidates"])

    def test_member_count_drift_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected=48 actual=47"):
            frame_skill_memorypack(bytes([SKILL_MEMBER_COUNT - 1]) + _empty_terminal_shape())

    def test_empty_and_truncated_payloads_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "truncated-member-count"):
            frame_skill_memorypack(b"")
        with self.assertRaisesRegex(ValueError, "truncated-payload"):
            frame_skill_memorypack(bytes([SKILL_MEMBER_COUNT]))

    def test_trailing_non_boolean_prevents_false_exactness(self) -> None:
        data = bytes([SKILL_MEMBER_COUNT, 0x7F]) + _empty_terminal_shape() + b"\x02"

        framed = frame_skill_memorypack(data)

        self.assertEqual("terminal-shape-unresolved", framed["status"])
        self.assertEqual([], framed["candidates"])


if __name__ == "__main__":
    unittest.main()

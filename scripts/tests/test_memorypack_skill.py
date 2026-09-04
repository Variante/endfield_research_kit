from __future__ import annotations

import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path

from scripts.game_data.memorypack.skill import (
    audit_skill_census,
    frame_skill_common_prefix,
    frame_skill_memorypack,
)
from scripts.game_data.memorypack.schemas import SKILL_MEMBER_COUNT


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

    def test_census_audit_rejoins_sources_and_payload_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "current.blc"
            source.write_bytes(b"current metadata")
            payload = root / "skill.bin"
            payload_bytes = bytes([SKILL_MEMBER_COUNT, 0x7F]) + _empty_terminal_shape()
            payload.write_bytes(payload_bytes)
            metadata = root / "global-metadata.dat"
            metadata.write_bytes(b"current native metadata")
            boundary = root / "boundary.json"
            boundary.write_text(
                json.dumps(
                    {
                        "inputSetSha256": "A" * 64,
                        "sourceFingerprints": [
                            {
                                "path": str(source),
                                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            census = root / "census.json"
            census.write_text(
                json.dumps(
                    {
                        "inputs": {
                            "ledger": "fixture-ledger.jsonl.gz",
                            "metadata": {
                                "path": str(metadata),
                                "sha256": hashlib.sha256(metadata.read_bytes()).hexdigest(),
                            },
                        },
                        "summary": {"files": 1, "declaredBytes": len(payload_bytes)},
                        "files": [
                            {
                                "virtualPath": "Data/Json/SkillData/fixture.json",
                                "exportPath": str(payload),
                                "declaredLength": len(payload_bytes),
                                "actualLength": len(payload_bytes),
                                "ledgerSha256": hashlib.sha256(payload_bytes).hexdigest(),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = audit_skill_census(
                census,
                boundary,
                expected_input_set_sha256="a" * 64,
            )

            self.assertEqual(1, result["sourceFingerprintCount"])
            self.assertEqual(1, result["files"])
            self.assertEqual({"unique-exact-terminal-shape": 1}, result["statusCounts"])
            self.assertFalse(result["wholeSchemaExact"])

    def test_census_audit_rejects_stale_source_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "current.blc"
            source.write_bytes(b"changed")
            boundary = root / "boundary.json"
            boundary.write_text(
                json.dumps(
                    {
                        "inputSetSha256": "B" * 64,
                        "sourceFingerprints": [
                            {"path": str(source), "sha256": hashlib.sha256(b"old").hexdigest()}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            census = root / "census.json"
            census.write_text(json.dumps({"summary": {"files": 0}, "files": []}), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, r"sourceFingerprints\[0\]:sha256-mismatch"):
                audit_skill_census(census, boundary)


if __name__ == "__main__":
    unittest.main()

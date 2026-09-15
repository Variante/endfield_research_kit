from __future__ import annotations

import struct
import unittest

from scripts.asset_builder.terrain_stream import (
    MATCH_BASE,
    RECORD_BYTES,
    TerrainStreamError,
    check_decoded,
    decode_stream,
    decoded_payloads_carry_real_data,
    every_decode_agrees_with_its_file,
    every_file_is_accounted_for,
    first_literal_run,
    is_stored,
    payload_period,
    split_token,
    summarise,
)


def record(width: int, height: int, payload: int, *, mips: int = 1, fmt: int = 6) -> bytes:
    return (b"TRET" + struct.pack("<I", 1) + struct.pack("<HH", width, height)
            + struct.pack("<HH", mips, fmt) + struct.pack("<I", payload))


def make_token(literal: int, match: int) -> int:
    """Pack two 4-bit fields the way the format does: interleaved, not nibbled."""
    low_literal, high_literal = literal & 0x03, (literal >> 2) & 0x03
    low_match, high_match = match & 0x03, (match >> 2) & 0x03
    return low_literal | (low_match << 2) | (high_literal << 4) | (high_match << 6)


def extension(value: int) -> bytes:
    """The 0xFF-terminated run that carries whatever a 15 field could not."""
    out = bytearray()
    remaining = value - 15
    while remaining >= 255:
        out.append(255)
        remaining -= 255
    out.append(remaining)
    return bytes(out)


def sequence(literals: bytes, offset: int | None = None, match: int = 0) -> bytes:
    """One sequence; omit the offset for the block's closing literal run."""
    literal_field = min(len(literals), 15)
    match_field = min(match - MATCH_BASE, 15) if offset is not None else 0
    out = bytearray([make_token(literal_field, match_field)])
    if len(literals) >= 15:
        out += extension(len(literals))
    out += literals
    if offset is None:
        return bytes(out)
    out += struct.pack(">H", offset)
    if match - MATCH_BASE >= 15:
        out += extension(match - MATCH_BASE)
    return bytes(out)


def flat_tile(fill: int = 0x04, payload: int = 100) -> bytes:
    """A file whose payload is one byte repeated: one literal run, one long match."""
    head = record(0x22, 0x22, payload)
    body = sequence(head + bytes([fill]), offset=1, match=payload - 1)
    stream = body + sequence(b"")
    return struct.pack("<I", RECORD_BYTES + payload) + stream


class TokenTests(unittest.TestCase):
    def test_the_token_interleaves_its_two_fields(self) -> None:
        # The byte that gave the format away: as nibbles it asks for three
        # literals, which would not reproduce the record the file declares.
        self.assertEqual(split_token(0x3F), (15, 3))
        self.assertNotEqual(split_token(0x3F), (0x3F >> 4, 0x3F & 0x0F))

    def test_only_four_tokens_read_the_same_either_way(self) -> None:
        # Why the wrong reading survived so long. A flat tile is one sequence and
        # a closing run, and its sequence token is 0xFF -- one of the four bytes
        # on which the two readings agree.
        agreeing = [t for t in range(256) if split_token(t) == (t >> 4, t & 0x0F)]
        self.assertEqual(agreeing, [0x00, 0x55, 0xAA, 0xFF])

    def test_the_old_hardcoded_tail_was_one_token_read_correctly(self) -> None:
        # The previous grammar did not read the closing token at all; it assumed
        # five literals. That is exactly what 0x11 means under the interleave,
        # which is why the assumption held for flat tiles and failed elsewhere --
        # real closing runs are five bytes only about four times in five.
        self.assertEqual(split_token(0x11), (5, 0))
        self.assertNotEqual(split_token(0x11), (0x11 >> 4, 0x11 & 0x0F))

    def test_packing_and_splitting_are_inverse(self) -> None:
        for literal in range(16):
            for match in range(16):
                self.assertEqual(split_token(make_token(literal, match)), (literal, match))


class DecodeTests(unittest.TestCase):
    def test_decodes_a_flat_tile_to_the_byte(self) -> None:
        data = flat_tile()
        out = decode_stream(data, struct.unpack_from("<I", data, 0)[0])
        self.assertEqual(out[:4], b"TRET")
        self.assertEqual(out[RECORD_BYTES:], bytes([0x04]) * 100)

    def test_decodes_a_stream_with_several_sequences(self) -> None:
        # The case the old grammar could not reach at all.
        head = record(0x22, 0x22, 40)
        stream = (
            sequence(head + b"\x10\x11\x12\x13", offset=4, match=16)
            + sequence(b"\x20\x21", offset=2, match=16)
            + sequence(b"\x30\x31")
        )
        data = struct.pack("<I", RECORD_BYTES + 40) + stream
        out = decode_stream(data, RECORD_BYTES + 40)
        self.assertEqual(len(out), RECORD_BYTES + 40)
        self.assertEqual(out[:RECORD_BYTES], head)
        self.assertGreater(len(set(out[RECORD_BYTES:])), 4)

    def test_extended_lengths_round_trip(self) -> None:
        head = record(0x22, 0x22, 900)
        literals = head + bytes(range(16))
        stream = sequence(literals, offset=1, match=900 - 16) + sequence(b"")
        data = struct.pack("<I", RECORD_BYTES + 900) + stream
        out = decode_stream(data, RECORD_BYTES + 900)
        self.assertEqual(len(out), RECORD_BYTES + 900)

    def test_a_short_decode_is_refused_rather_than_returned(self) -> None:
        data = flat_tile(payload=100)
        with self.assertRaises(TerrainStreamError):
            decode_stream(data, RECORD_BYTES + 101)

    def test_an_overrun_is_refused(self) -> None:
        data = flat_tile(payload=100)
        with self.assertRaises(TerrainStreamError):
            decode_stream(data, RECORD_BYTES + 99)

    def test_input_left_over_is_refused(self) -> None:
        data = flat_tile() + b"\x00\x00"
        with self.assertRaises(TerrainStreamError):
            decode_stream(data, struct.unpack_from("<I", data, 0)[0])

    def test_a_match_reaching_before_the_output_is_refused(self) -> None:
        head = record(0x22, 0x22, 40)
        stream = sequence(head, offset=4000, match=40) + sequence(b"")
        data = struct.pack("<I", RECORD_BYTES + 40) + stream
        with self.assertRaises(TerrainStreamError):
            decode_stream(data, RECORD_BYTES + 40)

    def test_a_zero_offset_is_refused(self) -> None:
        head = record(0x22, 0x22, 40)
        stream = sequence(head, offset=0, match=40) + sequence(b"")
        data = struct.pack("<I", RECORD_BYTES + 40) + stream
        with self.assertRaises(TerrainStreamError):
            decode_stream(data, RECORD_BYTES + 40)

    def test_truncated_lengths_and_offsets_are_refused(self) -> None:
        data = flat_tile()
        for cut in range(5, len(data)):
            with self.assertRaises(TerrainStreamError):
                decode_stream(data[:cut], struct.unpack_from("<I", data, 0)[0])

    def test_a_stream_ending_on_a_match_is_refused(self) -> None:
        # Without this the truncation case above would pass: dropping the closing
        # literal run leaves a stream that consumes its input exactly and lands on
        # exactly the declared size.
        head = record(0x22, 0x22, 40)
        data = struct.pack("<I", RECORD_BYTES + 40) + sequence(head, offset=1, match=40)
        with self.assertRaises(TerrainStreamError):
            decode_stream(data, RECORD_BYTES + 40)

    def test_shorter_than_the_size_word_is_refused(self) -> None:
        with self.assertRaises(TerrainStreamError):
            decode_stream(b"\x01\x02", 40)

    def test_the_offset_is_big_endian_and_a_swapped_one_does_not_decode(self) -> None:
        data = bytearray(flat_tile(payload=300))
        at = data.index(struct.pack(">H", 1), RECORD_BYTES)
        data[at:at + 2] = struct.pack("<H", 1)
        with self.assertRaises(TerrainStreamError):
            decode_stream(bytes(data), struct.unpack_from("<I", data, 0)[0])

    def test_a_nibble_packed_token_does_not_decode(self) -> None:
        # The control for the finding: repack every token as nibbles and the
        # same stream stops closing.
        data = bytearray(flat_tile(payload=300))
        token = data[4]
        literal, match = split_token(token)
        data[4] = (literal << 4) | match
        if data[4] != token:
            with self.assertRaises(TerrainStreamError):
                decode_stream(bytes(data), struct.unpack_from("<I", data, 0)[0])


class StoredTests(unittest.TestCase):
    def test_a_stored_file_is_recognised_by_two_facts_together(self) -> None:
        data = record(0x400, 0x400, 60) + bytes(60)
        self.assertTrue(is_stored(data))

    def test_the_magic_alone_does_not_make_a_file_stored(self) -> None:
        self.assertFalse(is_stored(record(0x400, 0x400, 999) + bytes(60)))

    def test_a_compressed_file_is_not_mistaken_for_stored(self) -> None:
        self.assertFalse(is_stored(flat_tile()))

    def test_a_stub_is_not_stored(self) -> None:
        self.assertFalse(is_stored(b"TRET"))


class AgreementTests(unittest.TestCase):
    def test_the_legible_prefix_stops_at_the_first_literal_run(self) -> None:
        # A compressor that matches partway through the record leaves the offset
        # field where the rest of the record would be; comparing there reports a
        # disagreement that is really a misread.
        head = record(0x22, 0x22, 40)
        stream = (
            sequence(head[:18], offset=1, match=22)
            + sequence(b"\x07", offset=1, match=19)
            + sequence(b"")
        )
        data = struct.pack("<I", RECORD_BYTES + 40) + stream
        self.assertEqual(first_literal_run(data), 18)

    def test_a_decode_that_disagrees_with_its_file_is_counted_not_accepted(self) -> None:
        data = bytearray(flat_tile(payload=100))
        struct.pack_into("<I", data, 0, RECORD_BYTES + 100)
        out = decode_stream(bytes(data), RECORD_BYTES + 100)
        broken = bytearray(out)
        struct.pack_into("<I", broken, RECORD_PAYLOAD := 16, 999)
        problems = check_decoded(bytes(data), bytes(broken))
        self.assertTrue(problems)

    def test_output_that_is_not_a_record_is_refused_outright(self) -> None:
        self.assertEqual(
            check_decoded(flat_tile(), b"NOPE" + bytes(16)),
            ["decoded output does not begin with TRET"],
        )


class GateTests(unittest.TestCase):
    def test_the_gates_need_decodes_and_reject_a_single_disagreement(self) -> None:
        good = {
            "outcomes": {"decodedAndClosed": 10},
            "decodedPayloadAgreement": {"agreesWithTheFile": 10},
            "decodedPayloadVariety": {"distinctBytes_9": 8, "distinctBytes_1": 2},
        }
        self.assertTrue(every_decode_agrees_with_its_file(good))
        self.assertTrue(every_file_is_accounted_for(good))
        self.assertTrue(decoded_payloads_carry_real_data(good))
        for bad in (
            {"outcomes": {}, "decodedPayloadAgreement": {}},
            {"outcomes": {"decodedAndClosed": 10, "decodedButDisagrees": 1},
             "decodedPayloadAgreement": {"agreesWithTheFile": 9}},
            {"outcomes": {"decodedAndClosed": 10},
             "decodedPayloadAgreement": {"agreesWithTheFile": 9}},
        ):
            self.assertFalse(every_decode_agrees_with_its_file(bad))

    def test_stored_files_count_towards_agreement(self) -> None:
        summary = {
            "outcomes": {"decodedAndClosed": 9, "storedUncompressed": 1},
            "decodedPayloadAgreement": {"agreesWithTheFile": 10},
        }
        self.assertTrue(every_decode_agrees_with_its_file(summary))
        self.assertTrue(every_file_is_accounted_for(summary))

    def test_a_fenced_file_fails_the_accounting_gate(self) -> None:
        # The gate that the old grammar would have failed: it closed a tenth of
        # the corpus and fenced the rest.
        self.assertFalse(every_file_is_accounted_for(
            {"outcomes": {"decodedAndClosed": 10, "fenced": 90}}
        ))

    def test_an_all_flat_corpus_fails_the_real_data_gate(self) -> None:
        # The specific way this module was wrong before: every file it closed was
        # a flat tile, which constrains almost nothing.
        self.assertFalse(decoded_payloads_carry_real_data(
            {"decodedPayloadVariety": {"distinctBytes_1": 90, "distinctBytes_9": 10}}
        ))
        self.assertFalse(decoded_payloads_carry_real_data({}))

    def test_a_fenced_file_is_named_by_reason_and_never_decoded(self) -> None:
        broken = bytearray(flat_tile())
        broken[-1] ^= 0xFF
        summary = summarise([("Terrain_0_0_0_C.bytes", bytes(broken))])
        self.assertEqual(summary["outcomes"].get("decodedAndClosed", 0), 0)
        self.assertTrue(summary["fenceReasons"])

    def test_summarise_separates_stored_from_decoded(self) -> None:
        stored = record(0x400, 0x400, 60) + bytes(60)
        summary = summarise([
            ("Terrain_0_0_0_C.bytes", flat_tile()),
            ("Terrain_0_0_1_C.bytes", stored),
        ])
        self.assertEqual(summary["outcomes"].get("decodedAndClosed"), 1)
        self.assertEqual(summary["outcomes"].get("storedUncompressed"), 1)
        self.assertEqual(summary["decodedPayloadAgreement"].get("agreesWithTheFile"), 2)

    def test_period_detection_does_not_call_noise_regular(self) -> None:
        self.assertEqual(payload_period(bytes([7]) * 40), 1)
        self.assertIsNone(payload_period(bytes(range(40))))


if __name__ == "__main__":
    unittest.main()

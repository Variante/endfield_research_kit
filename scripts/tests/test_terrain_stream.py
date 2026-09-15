from __future__ import annotations

import struct
import unittest

from scripts.asset_builder.terrain_stream import (
    MATCH_BASE,
    RECORD_BYTES,
    TAIL_LITERALS,
    TerrainStreamError,
    check_decoded,
    decode_stream,
    decoded_tiles_are_regular,
    every_decode_agrees_with_its_file,
    payload_period,
    summarise,
)


def record(width: int, height: int, payload: int, *, mips: int = 1, fmt: int = 6) -> bytes:
    return (b"TRET" + struct.pack("<I", 1) + struct.pack("<HH", width, height)
            + struct.pack("<HH", mips, fmt) + struct.pack("<I", payload))


def token(literal: int, match: int) -> bytes:
    """One LZ4 token plus whatever extension bytes its nibbles demand."""
    out = bytearray()
    high = min(literal, 15)
    low = min(match, 15)
    out.append((high << 4) | low)
    if literal >= 15:
        remaining = literal - 15
        while remaining >= 255:
            out.append(255)
            remaining -= 255
        out.append(remaining)
    return bytes(out)


def match_extension(match: int) -> bytes:
    out = bytearray()
    remaining = match - 15
    while remaining >= 255:
        out.append(255)
        remaining -= 255
    out.append(remaining)
    return bytes(out)


def flat_file(width: int, height: int, bytes_per_pixel: int, pattern: bytes) -> bytes:
    """A file whose payload is `pattern` repeated: one literal run, one long match."""
    payload = width * height * bytes_per_pixel
    head = record(width, height, payload)
    literals = head + pattern
    # The match reproduces everything except the closing literals.
    copied = payload - len(pattern) - TAIL_LITERALS
    body = bytearray(struct.pack("<I", payload + RECORD_BYTES))
    body += token(len(literals), 15)
    body += literals
    body += struct.pack(">H", len(pattern))
    body += match_extension(copied - MATCH_BASE)
    whole = head + pattern + bytes(
        pattern[i % len(pattern)] for i in range(len(pattern), payload)
    )
    body += b"\x11"
    body += whole[-TAIL_LITERALS:]
    return bytes(body), whole


class TerrainStreamTests(unittest.TestCase):
    def test_decodes_a_flat_tile_to_the_byte(self) -> None:
        data, expected = flat_file(34, 34, 2, b"\x04\x00")
        out = decode_stream(data, len(expected))
        self.assertEqual(out, expected)
        self.assertEqual(check_decoded(data, out), [])
        self.assertEqual(payload_period(out[RECORD_BYTES:]), 2)

    def test_a_short_decode_is_refused_rather_than_returned(self) -> None:
        # Producing fewer bytes than the file declares is the signature of a
        # desynchronised parse, and returning it would publish garbage as a decode.
        data, expected = flat_file(34, 34, 2, b"\x04\x00")
        with self.assertRaisesRegex(TerrainStreamError, "produced"):
            decode_stream(data, len(expected) + 1)

    def test_input_left_over_is_refused(self) -> None:
        # Trailing bytes move the closing run, so the parse takes a different path
        # and fails elsewhere. Which message comes out does not matter; that the
        # stream is refused rather than decoded up to the junk does.
        data, expected = flat_file(34, 34, 2, b"\x04\x00")
        with self.assertRaises(TerrainStreamError):
            decode_stream(data + b"\x00" * 9, len(expected))

    def test_a_match_reaching_before_the_output_is_refused(self) -> None:
        # This is the failure that fences most of the corpus. It must stay a
        # refusal: silently clamping the offset would invent pixels.
        head = record(8, 8, 64)
        data = bytearray(struct.pack("<I", 84))
        data += token(len(head), 4)
        data += head
        data += struct.pack(">H", 4096)
        data += b"\x00" * 8
        with self.assertRaisesRegex(TerrainStreamError, "reaches before the output"):
            decode_stream(bytes(data), 84)

    def test_truncated_lengths_and_offsets_are_refused(self) -> None:
        head = record(8, 8, 64)
        truncated = struct.pack("<I", 84) + token(len(head) + 40, 4)
        with self.assertRaisesRegex(TerrainStreamError, "runs past the end"):
            decode_stream(truncated + head, 84)
        with self.assertRaisesRegex(TerrainStreamError, "shorter than the size word"):
            decode_stream(b"\x01\x02", 84)

    def test_the_offset_is_big_endian_and_a_swapped_one_does_not_decode(self) -> None:
        # The endianness is the whole deviation from LZ4, so a file built with the
        # other order must fail rather than quietly produce something.
        data, expected = flat_file(34, 34, 2, b"\x04\x00")
        at = data.index(b"TRET") + RECORD_BYTES + 2
        swapped = bytearray(data)
        swapped[at:at + 2] = bytes(reversed(swapped[at:at + 2]))
        with self.assertRaises(TerrainStreamError):
            decode_stream(bytes(swapped), len(expected))

    def test_a_decode_that_disagrees_with_its_file_is_counted_not_accepted(self) -> None:
        # A decode that only agrees with itself proves nothing; the payload size the
        # output carries must match the file's leading word.
        data, expected = flat_file(34, 34, 2, b"\x04\x00")
        lying = bytearray(expected)
        struct.pack_into("<I", lying, 16, 999)
        self.assertIn(
            "decoded payload size disagrees with the leading size word",
            check_decoded(data, bytes(lying)),
        )
        self.assertIn(
            "decoded output does not begin with TRET",
            check_decoded(data, b"XXXX" + bytes(expected[4:])),
        )

    def test_the_gates_need_decodes_and_reject_a_single_disagreement(self) -> None:
        data, _ = flat_file(34, 34, 2, b"\x04\x00")
        other, _ = flat_file(34, 34, 2, b"\x07\x00")
        summary = summarise([
            ("Data/Terrain/PC/s/Terrain_1_1_1_C.bytes", data),
            ("Data/Terrain/PC/s/Terrain_2_2_2_C.bytes", other),
        ])
        self.assertEqual(summary["outcomes"]["decodedAndClosed"], 2)
        self.assertTrue(every_decode_agrees_with_its_file(summary))
        self.assertTrue(decoded_tiles_are_regular(summary))

        # Nothing decoded means the claim is unsupported, not vacuously true.
        empty = summarise([("Data/Terrain/PC/s/Terrain_1_1_1_C.bytes", b"\x00" * 8)])
        self.assertFalse(every_decode_agrees_with_its_file(empty))
        self.assertFalse(decoded_tiles_are_regular(empty))

        # One disagreement breaks it; a rate would bury it.
        broken = dict(summary)
        broken["outcomes"] = dict(summary["outcomes"], decodedButDisagrees=1)
        self.assertFalse(every_decode_agrees_with_its_file(broken))

    def test_a_fenced_file_is_named_by_reason_and_never_decoded(self) -> None:
        head = record(8, 8, 64)
        bad = bytearray(struct.pack("<I", 84))
        bad += token(len(head), 4)
        bad += head
        bad += struct.pack(">H", 4096)
        bad += b"\x00" * 8
        summary = summarise([("Data/Terrain/PC/s/Terrain_3_3_3_C.bytes", bytes(bad))])
        self.assertEqual(summary["outcomes"]["fenced"], 1)
        self.assertEqual(summary["fenceReasons"]["matchOffsetReachesBeforeTheOutput"], 1)
        self.assertNotIn("decodedAndClosed", summary["outcomes"])

    def test_period_detection_does_not_call_noise_regular(self) -> None:
        self.assertEqual(payload_period(b"\x01\x02" * 40), 2)
        self.assertEqual(payload_period(b"\x05" * 40), 1)
        self.assertIsNone(payload_period(bytes(range(40))))


if __name__ == "__main__":
    unittest.main()

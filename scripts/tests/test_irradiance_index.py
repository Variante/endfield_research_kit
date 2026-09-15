from __future__ import annotations

import struct
import unittest

from scripts.asset_builder.irradiance_index import (
    MIDDLE_WORDS,
    parse_index,
    read_name,
    summarise,
    the_index_names_the_volumes_beside_it,
    the_middle_word_count_beats_its_rivals,
)


def name(text: str) -> bytes:
    raw = text.encode("utf-16-le")
    return struct.pack("<I", len(raw)) + raw


def index(volumes: list[str], *, magic: int = 0x03000003,
          states: list[str] | None = None, middle: tuple[int, ...] = (1, 0, 0),
          tail: bytes = b"\x00" * 16) -> bytes:
    states = states or []
    out = struct.pack("<II", magic, len(states))
    for state in states:
        out += name(state)
    out += b"".join(struct.pack("<I", word) for word in middle)
    out += struct.pack("<I", len(volumes))
    for volume in volumes:
        out += name(volume)
    return out + tail


class ReadNameTests(unittest.TestCase):
    """A length that happens to be plausible is not a string."""

    def test_a_name_round_trips(self) -> None:
        self.assertEqual(read_name(name("iv_0_0.bytes"), 0),
                         (28, "iv_0_0.bytes"))

    def test_a_length_running_past_the_end_is_refused(self) -> None:
        self.assertIsNone(read_name(struct.pack("<I", 64) + b"ab", 0))

    def test_an_odd_length_is_refused(self) -> None:
        self.assertIsNone(read_name(struct.pack("<I", 5) + b"abcde", 0))

    def test_bytes_that_are_not_utf16_ascii_are_refused(self) -> None:
        # The shape is required rather than assumed: odd bytes zero, even printable.
        self.assertIsNone(read_name(struct.pack("<I", 4) + b"\x01\x02\x03\x04", 0))
        self.assertIsNone(read_name(struct.pack("<I", 4) + b"a\x00\x01\x00", 0))

    def test_a_zero_length_is_refused(self) -> None:
        self.assertIsNone(read_name(struct.pack("<I", 0), 0))


class ParseIndexTests(unittest.TestCase):
    """A file is framed or fenced, never partially read."""

    def test_a_built_index_frames(self) -> None:
        parsed = parse_index(index(["iv_0_0.bytes", "iv_0_1.bytes"]))
        self.assertEqual(parsed["status"], "exact")
        self.assertEqual(parsed["volumes"], ["iv_0_0.bytes", "iv_0_1.bytes"])
        self.assertEqual(parsed["middleWords"], [1, 0, 0])
        self.assertEqual(parsed["remainingBytes"], 16)

    def test_a_declared_state_list_is_unsupported_not_failed(self) -> None:
        # Six real indexes take this path. The variant is refused rather than guessed
        # at, and it is reported as unsupported so it cannot be mistaken for a defect.
        parsed = parse_index(index(["iv_0_0.bytes"], states=["Afternoon", "Evening"]))
        self.assertEqual(parsed["status"], "unsupported")
        self.assertEqual(parsed["reason"], "index_declares_scene_states")
        self.assertEqual(parsed["states"], ["Afternoon", "Evening"])

    def test_a_truncated_file_fails(self) -> None:
        body = index(["iv_0_0.bytes"])
        self.assertEqual(parse_index(body[:6])["status"], "failed")
        self.assertEqual(parse_index(body[:20])["reason"], "middle_words_past_the_end")

    def test_a_volume_count_out_of_range_fails(self) -> None:
        body = bytearray(index(["iv_0_0.bytes"]))
        struct.pack_into("<I", body, 8 + 4 * MIDDLE_WORDS, 9999)
        self.assertEqual(parse_index(bytes(body))["reason"],
                         "volume_count_out_of_range")

    def test_a_zero_volume_count_fails_rather_than_framing_empty(self) -> None:
        body = bytearray(index(["iv_0_0.bytes"]))
        struct.pack_into("<I", body, 8 + 4 * MIDDLE_WORDS, 0)
        self.assertEqual(parse_index(bytes(body))["reason"],
                         "volume_count_out_of_range")

    def test_a_count_larger_than_the_names_present_fails(self) -> None:
        body = bytearray(index(["iv_0_0.bytes"]))
        struct.pack_into("<I", body, 8 + 4 * MIDDLE_WORDS, 4)
        self.assertEqual(parse_index(bytes(body))["reason"],
                         "volume_name_is_not_a_string")

    def test_repeated_volume_names_fail(self) -> None:
        # A duplicate would mean the cursor did not advance the way the frame thinks.
        self.assertEqual(
            parse_index(index(["iv_0_0.bytes", "iv_0_0.bytes"]))["reason"],
            "volume_names_repeat")

    def test_trailing_bytes_are_reported_not_ignored(self) -> None:
        parsed = parse_index(index(["iv_0_0.bytes"], tail=b"\x7f" * 40))
        self.assertEqual(parsed["remainingBytes"], 40)


class SummaryGateTests(unittest.TestCase):
    """The two things that make this a frame rather than a guess."""

    MEASURED = {
        "indexes": 92, "exact": 86, "unsupported": 6, "failed": 0,
        "volumeNames": 103, "volumeSetsMatchingTheDirectory": 86,
        "rivalMiddleWordsFraming": {"0": 0, "1": 0, "2": 0, "4": 0, "5": 0},
    }

    def test_the_measured_corpus_passes(self) -> None:
        self.assertTrue(the_index_names_the_volumes_beside_it(self.MEASURED))
        self.assertTrue(the_middle_word_count_beats_its_rivals(self.MEASURED))

    def test_one_index_naming_the_wrong_set_fails(self) -> None:
        # Strict on purpose: each index names between one and a few dozen files and
        # gets the whole set right, so a single mismatch means a misread name table.
        self.assertFalse(the_index_names_the_volumes_beside_it(
            dict(self.MEASURED, volumeSetsMatchingTheDirectory=85)))

    def test_an_index_that_is_neither_framed_nor_fenced_fails(self) -> None:
        self.assertFalse(the_index_names_the_volumes_beside_it(
            dict(self.MEASURED, indexes=93)))

    def test_a_rival_width_that_also_frames_fails(self) -> None:
        self.assertFalse(the_middle_word_count_beats_its_rivals(
            dict(self.MEASURED,
                 rivalMiddleWordsFraming={"0": 0, "1": 80, "2": 0, "4": 0, "5": 0})))

    def test_no_rival_scored_fails(self) -> None:
        self.assertFalse(the_middle_word_count_beats_its_rivals(
            dict(self.MEASURED, rivalMiddleWordsFraming={})))

    def test_an_empty_corpus_fails_rather_than_passing_vacuously(self) -> None:
        for gate in (the_index_names_the_volumes_beside_it,
                     the_middle_word_count_beats_its_rivals):
            self.assertFalse(gate(dict(self.MEASURED, exact=0)))
            self.assertFalse(gate({}))
            self.assertFalse(gate(None))

    def test_summarise_counts_every_index_exactly_once(self) -> None:
        samples = [
            ("a/index.bytes", index(["iv_0_0.bytes"]), {"iv_0_0.bytes"}),
            ("b/index.bytes", index(["iv_1_0.bytes"]), {"iv_9_9.bytes"}),
            ("c/index.bytes", index(["iv_0_0.bytes"], states=["Rain"]), set()),
            ("d/index.bytes", b"\x00\x00", set()),
        ]
        out = summarise(samples)
        self.assertEqual(out["indexes"], 4)
        self.assertEqual((out["exact"], out["unsupported"], out["failed"]), (2, 1, 1))
        self.assertEqual(out["volumeSetsMatchingTheDirectory"], 1)
        self.assertEqual(out["reasons"]["index_declares_scene_states"], 1)


if __name__ == "__main__":
    unittest.main()

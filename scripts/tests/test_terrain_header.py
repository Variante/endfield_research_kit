from __future__ import annotations

import struct
import unittest

from scripts.asset_builder.terrain_header import (
    BLOCK_BYTES,
    TerrainHeaderError,
    block_chain,
    channel_decides_the_format,
    channel_of,
    fit_payload,
    linear_chain,
    parse_terrain_header,
    payload_is_the_mip_chain,
    summarise,
)


def record(width: int, height: int, payload: int, *, mips: int = 1, fmt: int = 6,
           one: int = 1) -> bytes:
    out = bytearray(b"TRET")
    out += struct.pack("<I", one)
    out += struct.pack("<HH", width, height)
    out += struct.pack("<HH", mips, fmt)
    out += struct.pack("<I", payload)
    return bytes(out)


def build(width: int, height: int, bytes_per_pixel: int, *, magic_at: int = 6,
          mips: int = 1, fmt: int = 6, payload: int | None = None,
          one: int = 1, total_delta: int = 0) -> bytes:
    """A file: the leading size word, filler standing in for compressed bytes, the record."""
    if payload is None:
        payload = linear_chain(width, height, mips, bytes_per_pixel)
    out = bytearray(struct.pack("<I", payload + 20 + total_delta))
    out += b"\x00" * (magic_at - 4)
    out += record(width, height, payload, mips=mips, fmt=fmt, one=one)
    return bytes(out)


class TerrainHeaderTests(unittest.TestCase):
    def test_locates_the_header_by_its_magic_not_a_fixed_offset(self) -> None:
        # The stream is compressed, so the header floats. A reader that assumed
        # offset 6 would fence every file the compressor happened to shift.
        for magic_at in (4, 6, 7, 11, 31):
            header = parse_terrain_header(build(34, 34, 2, magic_at=magic_at))
            self.assertEqual(header.magic_offset, magic_at)
            self.assertEqual((header.width, header.height), (34, 34))
            self.assertEqual(header.payload_bytes, 34 * 34 * 2)
            self.assertEqual(header.declared_total, 34 * 34 * 2 + 20)

    def test_a_stray_magic_is_skipped_for_the_one_whose_sizes_agree(self) -> None:
        # Four bytes spelling TRET can appear inside compressed data by chance.
        # Taking the first occurrence would read a header out of noise, so the
        # reader must keep looking until the two size words agree.
        real = build(34, 34, 2, magic_at=6)
        noisy = real[:4] + b"TRET" + b"\x00" * 16 + real[4:]
        header = parse_terrain_header(noisy)
        self.assertEqual(header.payload_bytes, 34 * 34 * 2)

    def test_a_header_that_never_agrees_is_refused_rather_than_guessed(self) -> None:
        # The two size words are two statements about the same record; if none of
        # the magic's occurrences makes them agree, the header is not contiguous in
        # the stream and must not be read.
        with self.assertRaisesRegex(TerrainHeaderError, "sizes agree"):
            parse_terrain_header(build(4, 4, 1, total_delta=3))
        with self.assertRaisesRegex(TerrainHeaderError, "sizes agree"):
            parse_terrain_header(build(4, 4, 1)[:-4] + struct.pack("<I", 999))
        # The word after the magic is 1 in every framed file; a stray magic that
        # does not carry it is not this record.
        with self.assertRaisesRegex(TerrainHeaderError, "sizes agree"):
            parse_terrain_header(build(4, 4, 1, one=7))
        with self.assertRaisesRegex(TerrainHeaderError, "shorter than a header"):
            parse_terrain_header(b"TRET")
        # A magic before the leading size word cannot be a header.
        with self.assertRaises(TerrainHeaderError):
            parse_terrain_header(b"TRET" + build(4, 4, 1)[4:][:20])

    def test_an_implausible_mip_count_is_refused(self) -> None:
        # A stray magic followed by noise usually shows itself here first: the mip
        # count is the narrowest field in the header.
        with self.assertRaises(TerrainHeaderError):
            parse_terrain_header(build(8, 8, 1, mips=99, payload=64))

    def test_the_payload_must_be_the_whole_mip_chain(self) -> None:
        # One image is not the claim: eleven levels of a 1024x1024 texture come to
        # four thirds of the base, and the header says so.
        chain = linear_chain(1024, 1024, 11, 1)
        self.assertEqual(chain, 1398101)
        header = parse_terrain_header(build(1024, 1024, 1, mips=11, fmt=5, payload=chain))
        self.assertEqual(fit_payload(header)[0], "linear")

        # A payload sized for a single level must not be accepted as a chain.
        single = parse_terrain_header(build(1024, 1024, 1, mips=11, fmt=5, payload=1024 * 1024))
        self.assertEqual(fit_payload(single)[0], "neither")

    def test_a_block_chain_is_separable_from_a_linear_one_at_1024(self) -> None:
        # The last mip levels cost a whole block each, so a block chain is larger
        # than four thirds of its base. That difference is the only thing in these
        # bytes that tells the two layouts apart.
        blocks = block_chain(1024, 1024, 11, 16)
        self.assertNotEqual(blocks, linear_chain(1024, 1024, 11, 1))
        header = parse_terrain_header(build(1024, 1024, 1, mips=11, fmt=108, payload=blocks))
        verdict, linear, block = fit_payload(header)
        self.assertEqual((verdict, linear, block), ("block", None, 16))

    def test_a_single_level_multiple_of_four_is_reported_ambiguous(self) -> None:
        # At 132x132 one byte per pixel and sixteen-byte blocks predict the same
        # total. Picking either would be inventing a distinction the bytes do not
        # carry, so the outcome is named rather than resolved.
        header = parse_terrain_header(build(132, 132, 1, fmt=100))
        verdict, linear, block = fit_payload(header)
        self.assertEqual((verdict, linear, block), ("ambiguous", 1, 16))
        self.assertIn(16, BLOCK_BYTES)

    def test_the_gate_requires_every_framed_payload_to_be_accounted_for(self) -> None:
        samples = [
            ("Data/Terrain/PC/s/Terrain_1_2_3_C.bytes", build(34, 34, 2, fmt=6)),
            ("Data/Terrain/PC/s/Terrain_1_2_3_S.bytes", build(132, 132, 4, fmt=8)),
            ("Data/Terrain/PC/s/LAYER_D_0.bytes",
             build(1024, 1024, 1, mips=11, fmt=108, payload=block_chain(1024, 1024, 11, 16))),
        ]
        summary = summarise(samples)
        self.assertEqual(summary["outcomes"]["headerFramed"], 3)
        self.assertTrue(payload_is_the_mip_chain(summary))
        self.assertTrue(channel_decides_the_format(summary))

        # A payload that fits neither layout breaks the claim outright; a rate over
        # 45,000 files would bury it.
        broken = summarise(
            samples + [("Data/Terrain/PC/s/Terrain_9_9_9_C.bytes",
                        build(34, 34, 2, fmt=6, payload=34 * 34 * 2 + 1))]
        )
        self.assertEqual(broken["outcomes"]["payload_neither"], 1)
        self.assertFalse(payload_is_the_mip_chain(broken))

        # Nothing framed means the claim is unsupported, not trivially true.
        self.assertFalse(payload_is_the_mip_chain(summarise([])))
        self.assertFalse(channel_decides_the_format(summarise([])))

    def test_two_formats_under_one_channel_break_the_name_join(self) -> None:
        samples = [
            ("Data/Terrain/PC/s/Terrain_1_1_1_C.bytes", build(34, 34, 2, fmt=6)),
            ("Data/Terrain/PC/s/Terrain_2_2_2_C.bytes", build(132, 132, 4, fmt=8)),
        ]
        summary = summarise(samples)
        self.assertEqual(len(summary["formatByChannel"]["C"]), 2)
        self.assertFalse(channel_decides_the_format(summary))

    def test_unreadable_and_unnamed_files_are_fenced_separately(self) -> None:
        summary = summarise(
            [
                ("Data/Terrain/PC/s/Terrain_1_2_3_C.bytes", build(8, 8, 1, total_delta=5)),
                ("Data/Terrain/PC/s/not_terrain.bytes", build(8, 8, 1)),
            ]
        )
        # A header the compressor split is not the same thing as a file whose name
        # says nothing, so the two must not be pooled.
        self.assertEqual(summary["outcomes"]["headerNotLegibleInTheStream"], 1)
        self.assertEqual(summary["outcomes"]["nameNotTerrainShaped"], 1)
        self.assertFalse(payload_is_the_mip_chain(summary))

    def test_both_name_shapes_yield_their_channel(self) -> None:
        # The layer textures end in a layer index, not a channel; reading the last
        # token would turn one channel into nine.
        self.assertEqual(channel_of("x/Terrain_10_2_33_H.bytes"), "H")
        self.assertEqual(channel_of("x/LAYER_D_7.bytes"), "LAYER_D")
        self.assertEqual(channel_of("x/LAYER_N_0.bytes"), "LAYER_N")
        self.assertIsNone(channel_of("x/Terrain_10_2.bytes"))
        self.assertIsNone(channel_of("x/LAYER_D.bytes"))


if __name__ == "__main__":
    unittest.main()

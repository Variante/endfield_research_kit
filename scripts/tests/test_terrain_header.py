from __future__ import annotations

import struct
import unittest

from scripts.asset_builder.terrain_header import (
    CHANNEL_BYTES_PER_PIXEL,
    TerrainHeaderError,
    channel_decides_pixel_width,
    channel_of,
    parse_terrain_header,
    summarise,
)


def build(width: int, height: int, bytes_per_pixel: int, *, magic: bytes = b"TRET",
          selector: int = 6, total_delta: int = 0) -> bytes:
    payload = width * height * bytes_per_pixel
    out = bytearray()
    out += struct.pack("<I", payload + 20 + total_delta)
    out += bytes([0xFF, selector])
    out += magic
    out += struct.pack("<I", 1)
    out += struct.pack("<HH", width, height)
    out += struct.pack("<HH", 1, 6)
    out += struct.pack("<I", payload)
    return bytes(out)


class TerrainHeaderTests(unittest.TestCase):
    def test_parses_the_header_and_derives_pixel_width(self) -> None:
        header = parse_terrain_header(build(34, 34, 2))
        self.assertEqual((header.width, header.height), (34, 34))
        self.assertEqual(header.payload_bytes, 34 * 34 * 2)
        self.assertEqual(header.declared_total, 34 * 34 * 2 + 20)
        self.assertEqual(header.bytes_per_pixel, 2)

    def test_a_missing_magic_or_inconsistent_total_is_refused(self) -> None:
        with self.assertRaisesRegex(TerrainHeaderError, "magic TRET"):
            parse_terrain_header(build(4, 4, 1, magic=b"XXXX"))
        # The two size words are two statements about the same file; if they
        # disagree the header is not the one documented, so it must not be read.
        with self.assertRaisesRegex(TerrainHeaderError, "is not payload"):
            parse_terrain_header(build(4, 4, 1, total_delta=3))
        with self.assertRaisesRegex(TerrainHeaderError, "shorter than a header"):
            parse_terrain_header(b"TRET")

    def test_a_zero_dimension_yields_no_pixel_width_rather_than_dividing(self) -> None:
        self.assertIsNone(parse_terrain_header(build(0, 8, 1)).bytes_per_pixel)

    def test_the_channel_letter_must_predict_the_header(self) -> None:
        samples = [
            ("Data/Terrain/PC/s/Terrain_1_2_3_C.bytes", build(8, 8, 2)),
            ("Data/Terrain/PC/s/Terrain_1_2_3_S.bytes", build(8, 8, 4)),
            ("Data/Terrain/PC/s/Terrain_1_2_3_T.bytes", build(8, 8, 1)),
        ]
        summary = summarise(samples)
        self.assertEqual(summary["outcomes"]["headerFramed"], 3)
        self.assertEqual(summary["disagreements"], [])
        self.assertTrue(channel_decides_pixel_width(summary))

        # One file whose header contradicts its name breaks the join outright; a
        # rate would bury it.
        broken = summarise(samples + [("Data/Terrain/PC/s/Terrain_9_9_9_C.bytes", build(8, 8, 4))])
        self.assertEqual(broken["outcomes"]["channelWidthDisagrees"], 1)
        self.assertFalse(channel_decides_pixel_width(broken))

    def test_unframed_and_unnamed_files_are_fenced_not_counted_as_agreement(self) -> None:
        summary = summarise(
            [
                ("Data/Terrain/PC/s/Terrain_1_2_3_C.bytes", build(8, 8, 1, magic=b"ZZZZ")),
                ("Data/Terrain/PC/s/not_terrain.bytes", build(8, 8, 1)),
            ]
        )
        self.assertEqual(summary["outcomes"]["headerNotAtOffsetSix"], 1)
        self.assertEqual(summary["outcomes"]["nameNotTerrainShaped"], 1)
        # Nothing framed, so the claim is unsupported rather than trivially true.
        self.assertFalse(channel_decides_pixel_width(summary))

    def test_channel_extraction_matches_the_documented_name_shape(self) -> None:
        self.assertEqual(channel_of("x/Terrain_10_2_33_H.bytes"), "H")
        self.assertIsNone(channel_of("x/Terrain_10_2.bytes"))
        self.assertEqual(sorted(CHANNEL_BYTES_PER_PIXEL), ["A", "C", "H", "N", "S", "T"])


if __name__ == "__main__":
    unittest.main()

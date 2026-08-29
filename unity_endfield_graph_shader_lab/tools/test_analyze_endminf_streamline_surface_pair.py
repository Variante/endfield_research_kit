from __future__ import annotations

import math
import struct
import unittest

import analyze_endminf_streamline_surface_pair as subject


class StreamlineSurfaceAnalysisTests(unittest.TestCase):
    def test_unsigned_float_known_values(self) -> None:
        self.assertEqual(0.0, subject.unsigned_float(0, 6))
        self.assertEqual(1.0, subject.unsigned_float(15 << 6, 6))
        self.assertEqual(1.5, subject.unsigned_float((15 << 6) | 32, 6))
        self.assertTrue(math.isinf(subject.unsigned_float(31 << 6, 6)))

    def test_r11g11b10_channel_layout(self) -> None:
        packed = ((15 << 6) | 32) | ((16 << 6) << 11) | ((14 << 5) << 22)
        red, green, blue = subject.decode_r11g11b10(
            struct.pack("<I", packed), 0)
        self.assertEqual((1.5, 2.0, 0.5), (red, green, blue))

    def test_rgba16f_ignores_alpha(self) -> None:
        raw = struct.pack("<4e", 0.25, 0.5, 1.0, 0.125)
        self.assertEqual((0.25, 0.5, 1.0), subject.decode_rgba16f(raw, 0))

    def test_png_writer_emits_valid_structure(self) -> None:
        encoded = subject.png_bytes(1, 1, [b"\x01\x02\x03\xff"])
        self.assertEqual(b"\x89PNG\r\n\x1a\n", encoded[:8])
        self.assertIn(b"IHDR", encoded)
        self.assertTrue(encoded.endswith(b"IEND\xaeB`\x82"))


if __name__ == "__main__":
    unittest.main()

import math
import unittest

from unity_endfield_graph_shader_lab.tools import analyze_endminf_m14_exact_temporal as subject


class ExactM14TemporalTests(unittest.TestCase):
    def test_unsigned_float_decoder(self):
        self.assertEqual(subject.decode_ufloat(0, 6), 0.0)
        self.assertEqual(subject.decode_ufloat(15 << 6, 6), 1.0)
        self.assertTrue(math.isinf(subject.decode_ufloat(31 << 6, 6)))

    def test_b10g11r11_channel_order(self):
        packed = (15 << 6) | ((16 << 6) << 11) | ((14 << 5) << 22)
        self.assertEqual(subject.decode_b10g11r11(packed), (1.0, 2.0, 0.5))


if __name__ == "__main__":
    unittest.main()

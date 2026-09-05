import struct
import unittest
from scripts.game_data.streaming_marker17 import (
    parse_marker17_tag5 as parse, TAG5_RECORD_WIDTHS as WIDTHS,
)

def fixture(counts=(1, 2, 3, 4, 5, 6)):
    data = bytearray(64 + sum(c * w for c, w in zip(counts, WIDTHS)))
    struct.pack_into('<h', data, 28, 5)
    struct.pack_into('<6i', data, 40, *counts)
    return bytes(data)

class Tag5Tests(unittest.TestCase):
    def call(self, data, **kw):
        return parse(data, source='fixture.bytes', native_layout_validated=True, **kw)

    def test_exact_order_ranges_and_empty(self):
        result = self.call(fixture((1,1,1,1,1,1)), base_offset=1000)
        self.assertEqual([(r['start'], r['end']) for r in result['arrays']],
                         [(1064,1088),(1088,1140),(1140,1188),(1188,1216),(1216,1272),(1272,1328)])
        self.assertEqual(result['consumedBytes'], 328)
        self.assertEqual(result['arrays'][0]['kind'], 'optional-record')
        self.assertEqual({r['kind'] for r in result['arrays'][1:]}, {'record-array'})
        self.assertEqual(self.call(fixture((0,0,0,0,0,0)))['consumedBytes'], 64)

    def test_no_semantics_or_reserved_zero_assumption(self):
        data = bytearray(fixture())
        data[30:40] = b'abcdefghij'
        self.assertEqual(self.call(data)['recordFieldMeaning'], 'unresolved')

    def test_gate(self):
        with self.assertRaisesRegex(ValueError, 'fixture.bytes.*offset 0.*validated.*unvalidated'):
            parse(fixture(), source='fixture.bytes')
        for value in (None, 1, 'unvalidated'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse(fixture(), source='fixture.bytes', native_layout_validated=value)

    def test_truncated_header_and_last_record(self):
        for data in (fixture()[:63], fixture()[:-1]):
            with self.assertRaisesRegex(ValueError, 'fixture.bytes.*offset.*expected.*actual'):
                self.call(data)

    def test_count_and_optional_record_domain(self):
        for offset, value in ((40,2),(40,-1),(44,-1),(48,0x7fffffff),(52,-1),(56,-1),(60,0x7fffffff)):
            data = bytearray(fixture())
            struct.pack_into('<i', data, offset, value)
            with self.subTest(offset=offset, value=value), self.assertRaisesRegex(ValueError, 'expected.*actual'):
                self.call(data)

    def test_trailing_and_reduced_count(self):
        data = bytearray(fixture())
        struct.pack_into('<i', data, 60, 5)
        for bad in (fixture() + b'\0', data):
            with self.assertRaisesRegex(ValueError, 'exact body EOF.*trailing'):
                self.call(bad)

    def test_tag_and_absolute_diagnostic(self):
        data = bytearray(fixture())
        struct.pack_into('<h', data, 28, 4)
        with self.assertRaisesRegex(ValueError, 'decoded offset 128.*tag 5.*actual 4'):
            self.call(data, base_offset=100)

    def test_mixed_zero_groups_partition_every_byte_once(self):
        data = fixture((0,2,0,3,1,0))
        result = self.call(data, base_offset=100)
        spans = [(100,128),(128,130),(130,140),(140,164)]
        spans.extend((a['start'] + i * a['recordWidth'], a['start'] + (i+1) * a['recordWidth'])
                     for a in result['arrays'] for i in range(a['count']))
        self.assertEqual(spans[0][0], 100)
        self.assertEqual(spans[-1][1], 100 + len(data))
        self.assertTrue(all(a[1] == b[0] for a,b in zip(spans, spans[1:])))
        with self.assertRaisesRegex(ValueError, 'nonnegative decoded body base.*actual -1'):
            self.call(data, base_offset=-1)

if __name__ == '__main__':
    unittest.main()

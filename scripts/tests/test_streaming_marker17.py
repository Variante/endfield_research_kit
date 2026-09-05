import struct
import unittest
from scripts.game_data.streaming_marker17 import (
    parse_marker17_tag5 as parse, TAG5_RECORD_WIDTHS as WIDTHS,
    parse_marker17_body, FIXED_BODY_PROFILES, TAG5_BODY_KEYS,
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

class FixedBodyTests(unittest.TestCase):
    def body(self, identity):
        tag, length = FIXED_BODY_PROFILES[identity]
        data = bytearray(b'\xA5' * length)
        struct.pack_into('<h', data, 28, tag)
        return bytes(data)

    def call(self, data, identity=(2, 0x04000000), **kw):
        return parse_marker17_body(data, source='fixed.bytes', selector=identity[0],
                                   key=identity[1], native_layout_validated=True, **kw)

    def test_all_fixed_partitions_and_nonzero_unread_gap(self):
        for identity, (tag, size) in FIXED_BODY_PROFILES.items():
            result = self.call(self.body(identity), identity, base_offset=123)
            self.assertEqual((result['tag'], result['bodyEnd']), (tag, 123 + size))
            spans = result['partition']
            self.assertTrue(all(a['end'] == b['start'] for a,b in zip(spans, spans[1:])))
            self.assertEqual(sum(s['end'] - s['start'] for s in spans), size)
            self.assertEqual(result['opaqueUnreadRanges'][0]['start'], 153)
            self.assertEqual(result['recordFieldMeaning'], 'unresolved')
            self.assertIn('not EOF', result['nativeFinalCursorStatus'])

    def test_each_fixed_truncated_trailing_and_wrong_tag(self):
        for identity in FIXED_BODY_PROFILES:
            data = self.body(identity)
            wrong_tag = bytearray(data)
            struct.pack_into('<h', wrong_tag, 28, 5)
            for bad in (data[:0], data[:29], data[:-1], data + b'\0', data + b'\0' * 4, wrong_tag):
                with self.subTest(identity=identity, size=len(bad)), self.assertRaisesRegex(ValueError, 'fixed.bytes.*offset.*expected.*actual'):
                    self.call(bad, identity)

    def test_equal_length_does_not_imply_equal_tag(self):
        with self.assertRaisesRegex(ValueError, 'offset 128.*tag 6.*actual 1'):
            self.call(self.body((2, 0x04000000)), (7, 0x08000000), base_offset=100)

    def test_wrong_key_selector_full_width_and_type(self):
        for identity in ((5, 0x04000000), (2, 0x05000000), (258, 0x04000000),
                         (2, -1), (2, 0x100000000), (True, 0x04000000), (2, None)):
            with self.subTest(identity=identity), self.assertRaisesRegex(ValueError, 'expected.*actual'):
                self.call(self.body((2, 0x04000000)), identity)

    def test_default_and_non_boolean_native_gate(self):
        for identity in list(FIXED_BODY_PROFILES) + list(TAG5_BODY_KEYS.items()):
            for value in (False, None, 1, 'validated'):
                with self.assertRaisesRegex(ValueError, 'unvalidated'):
                    parse_marker17_body(b'', source='fixed.bytes', selector=identity[0], key=identity[1],
                                        native_layout_validated=value)

    def test_base_offset_domain(self):
        for value in (-1, None, True, 0.5):
            with self.assertRaisesRegex(ValueError, 'nonnegative integer body base'):
                self.call(self.body((2, 0x04000000)), base_offset=value)

    def test_tag5_dispatch_is_byte_for_byte_result_equivalent(self):
        data = fixture()
        expected = parse(data, source='fixed.bytes', base_offset=123, native_layout_validated=True)
        for identity in TAG5_BODY_KEYS.items():
            self.assertEqual(self.call(data, identity, base_offset=123), expected)
            with self.assertRaisesRegex(ValueError, 'trailing'):
                self.call(data + b'\0', identity)

if __name__ == '__main__':
    unittest.main()

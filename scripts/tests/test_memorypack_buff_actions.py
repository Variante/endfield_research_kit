"""Anonymous current action prefixes: exact supported fixtures and explicit gaps."""
import struct
import unittest

from scripts.game_data.memorypack.buff_actions import FrameError, Unsupported, event_prefix, sequence_frame


def sequence(*actions,tail=b'\x00\x00'):
    return b'\x03'+struct.pack('<i',len(actions))+b''.join(actions)+tail


def action(*branches):
    return b'\xc9\x08'+bytes(14)+b''.join(branches or [sequence()]*3)


def prefix(seq):
    return b'\x1e'+struct.pack('<i',1)+b'\x02'+bytes(4)+struct.pack('<i',1)+seq


class BuffActionsTests(unittest.TestCase):
    def test_normal_nested_ranges_and_explicit_opaque_tail(self):
        raw=sequence(action(sequence(b'\xff'),sequence(),b'\xff'))
        spans=sequence_frame(raw,source='normal.bin')
        self.assertEqual(spans[0]['start'],0)
        self.assertEqual(spans[-1]['end'],len(raw))
        for a,b in zip(spans,spans[1:]):self.assertEqual(a['end'],b['start'])
        data=prefix(raw);report=event_prefix(data+b'opaque',source='normal.bin',limit=len(data))
        self.assertEqual(report['status'],'supported-prefix')
        self.assertEqual(report['opaqueRemainderRange'],[len(data),len(data)+6])
        self.assertFalse(report['wholeSchemaExact'])
        self.assertTrue(any(r['kind']=='union' and r['tag']==201 for r in report['completedRecords']))

    def test_all_truncations_and_trailing_bytes_fail(self):
        raw=sequence(action())
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError) as caught:sequence_frame(raw[:n],source='cut.bin')
            self.assertEqual(caught.exception.diagnostic['source'],'cut.bin')
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'!',source='tail.bin')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_malformed_counts_headers_and_limits(self):
        for n in (-2,2147483647):
            with self.subTest(n=n),self.assertRaises(FrameError) as caught:
                sequence_frame(b'\x03'+struct.pack('<i',n)+bytes(2),source='count.bin')
            self.assertEqual(caught.exception.diagnostic['offset'],1)
            self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')
        for raw in (b'\x02'+bytes(6),sequence(b'\xc9\x07'+bytes(14))):
            with self.assertRaises(FrameError):sequence_frame(raw)
        for limit in (-1,True,'1',100):
            with self.subTest(limit=limit),self.assertRaises(FrameError):event_prefix(bytes(5),source='limit.bin',limit=limit)

    def test_nulls_and_nonzero_bytes_are_not_strict_booleans(self):
        for raw in (b'\xff',sequence(b'\xff'),sequence(b'\xc9\xff'),b'\x03'+struct.pack('<i',-1)+b'\xfe\x02',sequence(tail=b'\xff\x80')):
            with self.subTest(raw=raw):self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))

    def test_unknown_union_does_not_borrow_legacy_alias_or_search(self):
        for tag in (0xC0,0x40,0x76,0xFA):
            raw=prefix(sequence(bytes([tag])+action()))
            row=event_prefix(raw,source='unknown.bin')
            self.assertEqual(row['status'],'unsupported')
            self.assertEqual(row['diagnostic']['actual'],tag)
            self.assertEqual(row['consumedEnd'],19)
            self.assertEqual(row['opaqueRemainderRange'],[19,len(raw)])
            self.assertEqual(row['completedRecords'],[])
            with self.assertRaises(Unsupported):sequence_frame(sequence(bytes([tag])))

    def test_suffix_cannot_supply_missing_nested_bytes(self):
        raw=prefix(sequence(action()))
        for n in range(1,len(raw)):
            first=event_prefix(raw,source='bounded.bin',limit=n)
            second=event_prefix(raw[:n]+b'\xff'*(len(raw)-n),source='bounded.bin',limit=n)
            self.assertEqual(first,second)

    def test_depth_limit_and_diagnostics(self):
        raw=sequence()
        for _ in range(66):raw=sequence(action(raw,b'\xff',b'\xff'))
        with self.assertRaises(Unsupported) as caught:sequence_frame(raw,source='deep.bin')
        self.assertEqual(caught.exception.diagnostic['category'],'depth-limit')
        row=event_prefix(b'\x1e'+struct.pack('<i',-1),source='map.bin')
        self.assertEqual(row['status'],'failed')
        self.assertEqual(set(row['diagnostic']),{'source','offset','expected','actual','category'})


if __name__=='__main__':unittest.main()

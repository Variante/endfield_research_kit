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


def payload(value):
    return struct.pack('<i',-1 if value is None else len(value))+(value or b'')


def pair(a=b'',b=b'',flag=0):
    return b'\x03'+payload(a)+bytes([flag])+payload(b)


def tag76(*items):
    return b'\x76\x05'+bytes(13)+struct.pack('<i',len(items))+b''.join(items)


def direction():
    return b'\x08\x01\x00'+bytes(4)+b'\x00\xff'+bytes(4)+b'\xff'+bytes(4)


def target(*,selector=b'\x03\xff'+bytes(8),direction_value=None):
    return (b'\x0d'+(direction() if direction_value is None else direction_value)+
            payload(b'center')+b'\x80'+bytes(4)+b'\xfe'+payload(None)+selector+
            bytes(12)+payload(b'\xff\xfe')+payload(b'group')+bytes(4))


def scalar_payload(value=b'value',flag=255,bits=b'\x00\x00\xc0\x7f'):
    return b'\x03'+payload(value)+bytes([flag])+bits


def tag_ec(*,nested=None,value=None,key=b'key'):
    return (b'\xec\x0a\xfe'+bytes(16)+(target() if nested is None else nested)+
            b'\x80'+payload(key)+bytes(4)+(scalar_payload() if value is None else value))


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
        for tag in (0xC0,0x40,0x71,0xFA):
            raw=prefix(sequence(bytes([tag])+action()))
            row=event_prefix(raw,source='unknown.bin')
            self.assertEqual(row['status'],'unsupported')
            self.assertEqual(row['diagnostic']['actual'],tag)
            self.assertEqual(row['consumedEnd'],19)
            self.assertEqual(row['opaqueRemainderRange'],[19,len(raw)])
            self.assertEqual(row['completedRecords'],[])
            with self.assertRaises(Unsupported):sequence_frame(sequence(bytes([tag])))

    def test_tag76_multiple_pairs_nested_in_ifelse_and_record_bounds(self):
        child=tag76(pair(b'skillId',b'',1),pair(b'',b'example'),pair(None,b'\xff\xfe',255))
        raw=prefix(sequence(action(sequence(child),sequence(),b'\xff')))
        row=event_prefix(raw+b'opaque',source='pair.bin',limit=len(raw))
        self.assertEqual(row['status'],'supported-prefix')
        self.assertEqual(row['opaqueRemainderRange'],[len(raw),len(raw)+6])
        unions=[r for r in row['completedRecords'] if r['kind']=='union']
        self.assertEqual([r['tag'] for r in unions],[118,201])
        records=[r for r in row['completedRecords'] if r['kind']=='anonymous-paired-payload']
        self.assertEqual(len(records),3)
        self.assertTrue(all(unions[0]['start']<r['start']<r['end']<=unions[0]['end'] for r in records))
        self.assertTrue(all(a['end']==b['start'] for a,b in zip(row['ranges'],row['ranges'][1:])))

    def test_tag76_every_truncation_trailing_and_hard_limit(self):
        raw=sequence(tag76(pair(b'a',b'bc'),pair(b'def',b'g')))
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError):sequence_frame(raw[:n],source='pair-cut.bin')
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'x',source='pair-tail.bin')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        full=prefix(raw)
        for n in range(len(full)):
            self.assertEqual(event_prefix(full,source='bounded.bin',limit=n),
                event_prefix(full[:n]+b'\xff'*(len(full)-n),source='bounded.bin',limit=n))

    def test_tag76_malformed_counts_lengths_and_headers(self):
        good=bytearray(tag76(pair(b'a',b'bc')))
        for offset in (15,20,26):
            for value in (-2,2147483647):
                bad=bytearray(good);struct.pack_into('<i',bad,offset,value)
                with self.subTest(offset=offset,value=value),self.assertRaises(FrameError) as caught:
                    sequence_frame(sequence(bad),source='bad-pair.bin')
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),
                    ('bad-pair.bin',offset+5,value,'count-bounds'))
        for offset in (1,19):
            bad=bytearray(good);bad[offset]=4
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad))
            self.assertEqual(caught.exception.diagnostic['category'],'member-count')

    def test_tag76_nulls_empty_and_stop_after_complete_record(self):
        for child in (b'\x76\xff',tag76(),tag76(b'\xff'),tag76(pair(None,None)),
                      b'\x76\x05'+bytes(13)+struct.pack('<i',-1)):
            self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))
        row=event_prefix(prefix(sequence(tag76(pair()),b'\xed')),source='next.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['actual'],237)
        self.assertTrue(any(r.get('tag')==118 for r in row['completedRecords']))

    def test_ec_nested_ranges_and_opaque_remainder(self):
        child=tag_ec()
        raw=prefix(sequence(action(sequence(child),sequence(),b'\xff')))
        row=event_prefix(raw+b'opaque',source='ec.bin',limit=len(raw))
        self.assertEqual(row['status'],'supported-prefix')
        self.assertEqual(row['opaqueRemainderRange'],[len(raw),len(raw)+6])
        records=row['completedRecords']
        union=next(r for r in records if r.get('tag')==236)
        self.assertEqual(union['end']-union['start'],len(child))
        for kind in ('direction-profile','target-profile','selector-profile','scalar-payload'):
            record=next(r for r in records if r['kind']=='anonymous-'+kind)
            self.assertTrue(union['start']<record['start']<record['end']<=union['end'])
        self.assertFalse(row['wholeSchemaExact'])
        sequence_frame(sequence(child))  # Includes non-UTF8 bytes and NaN bits.

    def test_ec_every_truncation_trailing_and_hard_limit(self):
        raw=sequence(tag_ec())
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError) as caught:
                sequence_frame(raw[:n],source='ec-cut.bin')
            self.assertEqual(caught.exception.diagnostic['source'],'ec-cut.bin')
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'x',source='ec-tail.bin')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        full=prefix(raw)
        for n in range(len(full)):
            bounded=event_prefix(full,source='ec-bound.bin',limit=n)
            self.assertEqual(bounded['status'],'failed')
            self.assertLessEqual(bounded['consumedEnd'],n)
            self.assertEqual(bounded,
                event_prefix(full[:n]+b'\xff'*(len(full)-n),source='ec-bound.bin',limit=n))

    def test_ec_malformed_lengths_and_member_headers(self):
        raw=prefix(sequence(tag_ec()))
        valid=event_prefix(raw,source='ec-bad.bin')
        lengths=[r['start'] for r in valid['ranges'] if r['kind']=='count-i32']
        for at in lengths:
            for n in (-2,2147483647):
                bad=bytearray(raw);struct.pack_into('<i',bad,at,n)
                row=event_prefix(bad,source='ec-bad.bin')
                with self.subTest(at=at,n=n):
                    self.assertEqual(row['status'],'failed')
                    self.assertEqual(row['diagnostic']['offset'],at)
                    self.assertEqual(row['diagnostic']['actual'],n)
                    self.assertEqual(row['diagnostic']['category'],'count-bounds')
        for r in valid['ranges']:
            if r['kind']!='member-header':continue
            bad=bytearray(raw);bad[r['start']]=42
            row=event_prefix(bad,source='ec-header.bin')
            self.assertEqual(row['status'],'failed')
            self.assertEqual(row['diagnostic']['offset'],r['start'])

    def test_ec_null_variants_and_unproven_profiles(self):
        for child in (b'\xec\xff',tag_ec(nested=b'\xff',value=b'\xff',key=None),
                      tag_ec(nested=target(selector=b'\xff',direction_value=b'\xff'))):
            self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))
        for nested in (target(selector=b'\x03\x00'+bytes(8)),
                       target(selector=b'\x03\xff'+struct.pack('<ii',1,0)),
                       target(selector=b'\x03\xff'+struct.pack('<ii',-1,0)),
                       target(direction_value=direction().replace(b'\xff',b'\x0d',1))):
            row=event_prefix(prefix(sequence(tag_ec(nested=nested))),source='ec-unsupported.bin')
            self.assertEqual(row['status'],'unsupported')
            self.assertEqual(row['diagnostic']['category'],'nested-profile')
            self.assertFalse(any(r.get('tag')==236 for r in row['completedRecords']))
        row=event_prefix(prefix(sequence(tag_ec(),b'\x50')),source='ec-next.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['actual'],80)
        self.assertTrue(any(r.get('tag')==236 for r in row['completedRecords']))

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

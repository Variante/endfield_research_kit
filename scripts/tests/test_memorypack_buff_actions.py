"""Anonymous current action prefixes: exact supported fixtures and explicit gaps."""
import struct
import unittest

from scripts.game_data.memorypack.buff_actions import FrameError, Reader, Unsupported, event_prefix, sequence_frame


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


def tag50(first=None,second=None):
    return (b'\x50\x07\xfe'+struct.pack('<IIII',0xffffffff,1,0x80000000,14)+
            (scalar_payload(b'\xff\x00',128) if first is None else first)+
            (scalar_payload(None,2,b'\x00\x00\x80\xff') if second is None else second))


def tag11f(first=None,value=None,last=None):
    return (b'\xfa\x1f\x01\x08\x80'+struct.pack('<III',0xffffffff,0x80000000,14)+
            (pair(b'key',b'\xff',254) if first is None else first)+
            (scalar_payload(None) if value is None else value)+b'\xfe'+
            (pair(b'',None) if last is None else last))


def tag_b4(*,finder=None):
    if finder is None:
        finder=(b'\x03'+struct.pack('<i',3)+payload(b'\xff\xfe')+payload(b'')+payload(None)+
                struct.pack('<I',0x80000000)+b'\x02'+struct.pack('<IiII',0xffffffff,2,0,0xffffffff))
    return b'\xb4\x0d\xfe'+bytes(12)+b'\xff'+finder+b'\xff\x80\xff\xff\xfe\x02\xff'


def tag56():
    return (b'\x56\x08\xfe'+struct.pack('<III',0xffffffff,0x80000000,1)+payload(b'\xff\x00')+
            struct.pack('<i',3)+b'\x01'+payload(b'a')+b'\xff\x01'+payload(None)+
            struct.pack('<I',0x80000000)+b'\x02'+struct.pack('<IiII',0xffffffff,2,0,0xffffffff))


def tag5b(flag=254,bits=0xffffffffffffffff):
    return b'\x5b\x06'+bytes([flag])+struct.pack('<IIIIQ',0xffffffff,0x80000000,1,0x7fc00000,bits)


def tag57():
    return (b'\x57\x08\xfe'+struct.pack('<III',0xffffffff,0x80000000,1)+payload(b'\xff\x00')+
            struct.pack('<i',3)+pair(b'a',b'\xff\x00',254)+b'\xff'+pair(None,b'',128)+
            struct.pack('<I',0x80000000)+b'\x02'+struct.pack('<IiII',0xffffffff,2,0,0xffffffff))


def tag92():
    assignment=b'\x06'+bytes.fromhex('FFFFFFFF')+payload(b'\xff\x00')+bytes.fromhex('0000C07F')+payload(None)+payload(b'')+b'\xfe'
    item=b'\x05\x80'+struct.pack('<i',2)+assignment+b'\xff'+payload(b'\xff\x00')+payload(None)+b'\xfe'
    return (b'\x92\x13\xfe'+bytes(12)+b'\x80\xfe'+b'\x02'+bytes(4)+payload(b'\xff\x00')+
            struct.pack('<i',2)+item+b'\xff'+bytes(4)+payload(b'k')+scalar_payload(None)+b'\x80'+
            struct.pack('<i',3)+payload(b'\xff\x00')+payload(None)+payload(b'')+b'\x00\x01\x80\xfe\xff'+b'\xff')


class BuffActionsTests(unittest.TestCase):
    def test_tag5b_exact_scalar64_boundary_and_bits(self):
        for flag in (0,1,128,254,255):
            for bits in (0,1,0x8000000000000000,0xffffffffffffffff,0x0102030405060708):
                child=tag5b(flag,bits);self.assertEqual(len(child),27)
                row=event_prefix(prefix(sequence(child,b'\x3c')),source='5b.bin')
                self.assertEqual(row['status'],'unsupported')
                self.assertEqual(row['diagnostic']['actual'],60)
                self.assertEqual(row['consumedEnd'],46)
                self.assertIn(dict(start=19,end=46,kind='union',tag=91),row['completedRecords'])
                self.assertIn(dict(start=38,end=46,kind='anonymous-scalar64'),row['ranges'])
                self.assertEqual(child[19:27],struct.pack('<Q',bits))
                self.assertFalse(row['wholeSchemaExact'])

    def test_tag5b_truncations_trailing_and_hard_limit(self):
        raw=sequence(tag5b())
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError):sequence_frame(raw[:n])
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'x')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        full=prefix(raw)
        for n in range(len(full)):
            first=event_prefix(full,source='5b-limit.bin',limit=n)
            self.assertEqual(first['status'],'failed')
            self.assertLessEqual(first['consumedEnd'],n)
            self.assertEqual(first,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='5b-limit.bin',limit=n))

    def test_tag5b_bad_header_and_enclosing_counts(self):
        bad=bytearray(tag5b());bad[1]=5
        with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad),source='5b-header.bin')
        self.assertEqual(caught.exception.diagnostic,dict(source='5b-header.bin',offset=6,expected=6,actual=5,category='member-count'))
        for value in (-2,2147483647):
            raw=bytearray(sequence(tag5b()));struct.pack_into('<i',raw,1,value)
            with self.assertRaises(FrameError) as caught:sequence_frame(raw,source='5b-count.bin')
            d=caught.exception.diagnostic
            self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),('5b-count.bin',1,value,'count-bounds'))
        raw=bytearray(sequence(tag5b()));struct.pack_into('<i',raw,1,0)
        with self.assertRaises(FrameError) as caught:sequence_frame(raw)
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag5b_null_and_extended_tag(self):
        for child in (b'\x5b\xff',b'\xfa\x5b\x00\xff',b'\xfa\x5b\x00'+tag5b()[1:]):
            raw=sequence(child)
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])

    def test_tag57_paired_record_boundaries_and_later_unknown(self):
        child=tag57();self.assertEqual(len(child),70)
        row=event_prefix(prefix(sequence(child,b'\x5c')),source='57.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['actual'],92)
        self.assertEqual(row['consumedEnd'],89)
        self.assertIn(dict(start=19,end=89,kind='union',tag=87),row['completedRecords'])
        spans=[(r['start']-19,r['end']-19) for r in row['completedRecords'] if r['kind']=='anonymous-paired-payload']
        self.assertEqual(spans,[(25,38),(38,39),(39,49)])
        self.assertIn(dict(start=72,end=89,kind='anonymous-query-profile'),row['completedRecords'])
        self.assertFalse(row['wholeSchemaExact'])

    def test_tag57_truncations_trailing_and_hard_limit(self):
        raw=sequence(tag57())
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError):sequence_frame(raw[:n])
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'x')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        full=prefix(raw)
        for n in range(len(full)):
            first=event_prefix(full,source='57-limit.bin',limit=n)
            self.assertEqual(first['status'],'failed')
            self.assertLessEqual(first['consumedEnd'],n)
            self.assertEqual(first,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='57-limit.bin',limit=n))

    def test_tag57_bad_counts_and_headers(self):
        for at in (15,21,26,32,40,45,58):
            for value in (-2,2147483647):
                bad=bytearray(tag57());struct.pack_into('<i',bad,at,value)
                with self.subTest(at=at,value=value),self.assertRaises(FrameError) as caught:
                    sequence_frame(sequence(bad),source='57-count.bin')
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),
                                 ('57-count.bin',at+5,value,'count-bounds'))
        for at in (1,25,39,53):
            bad=bytearray(tag57());bad[at]=42
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad))
            self.assertEqual(caught.exception.diagnostic['offset'],at+5)
            self.assertEqual(caught.exception.diagnostic['category'],'member-count')
        # The related tag56 has member-one elements; accepting its header here
        # would silently select the wrong current native element profile.
        bad=bytearray(tag57());bad[25]=1
        with self.assertRaises(FrameError):sequence_frame(sequence(bad))

    def test_tag57_nulls_empty_lists_and_extended_tag(self):
        children=[b'\x57\xff',b'\xfa\x57\x00'+tag57()[1:]]
        for count in (-1,0):
            for key in (None,b''):
                for query in (b'\xff',b'\x02'+bytes(4)+struct.pack('<i',count)):
                    children.append(b'\x57\x08'+bytes(13)+payload(key)+struct.pack('<i',count)+bytes(4)+query)
        for child in children:
            raw=sequence(child)
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))

    def test_selector_finder_tag2_zero_members_and_null(self):
        for value in (b'\xff',b'\x02\x00',b'\x02\xff',b'\xfa\x02\x00\x00',b'\xfa\x02\x00\xff'):
            raw=sequence(tag_ec(nested=target(selector=b'\x03'+value+bytes(8))))
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.subTest(value=value,n=n),self.assertRaises(FrameError):sequence_frame(raw[:n])
            with self.assertRaises(FrameError):sequence_frame(raw+b'x')
        for value in (b'\x01',b'\xfa\xff\x00'):
            reader=Reader(value,'finder.bin')
            with self.assertRaises(Unsupported) as caught:reader.selector_finder_profile()
            self.assertEqual(caught.exception.diagnostic['offset'],0)
            self.assertEqual(reader.pos,0)
        for value in (b'\x02\x01',b'\xfa\x02\x00\x03'):
            reader=Reader(value,'finder.bin')
            with self.assertRaises(FrameError) as caught:reader.selector_finder_profile()
            self.assertEqual(caught.exception.diagnostic['category'],'member-count')
        raw=prefix(sequence(tag_ec(nested=target(selector=b'\x03\x02\x00'+bytes(8)))))
        for n in range(len(raw)):
            first=event_prefix(raw,source='finder-limit.bin',limit=n)
            self.assertEqual(first['status'],'failed')
            self.assertEqual(first,event_prefix(raw[:n]+b'\xff'*(len(raw)-n),source='finder-limit.bin',limit=n))

    def test_tag92_nested_boundaries_and_later_unknown(self):
        child=tag92();self.assertEqual(len(child),119)
        row=event_prefix(prefix(sequence(child,b'\x58')),source='92.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['actual'],88)
        self.assertEqual(row['consumedEnd'],138)
        for a,b,kind in ((0,119,'union'),(17,28,'anonymous-scalar-bytes-profile'),
                         (32,74,'anonymous-input-profile'),(74,75,'anonymous-input-profile'),
                         (38,62,'anonymous-assignment-profile'),(62,63,'anonymous-assignment-profile')):
            expected=dict(start=19+a,end=19+b,kind=kind)
            if kind=='union':expected['tag']=146
            self.assertIn(expected,row['completedRecords'])
        self.assertFalse(row['wholeSchemaExact'])

    def test_tag92_truncations_trailing_and_hard_limit(self):
        raw=sequence(tag92())
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError):sequence_frame(raw[:n])
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'x')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        full=prefix(raw)
        for n in range(len(full)):
            first=event_prefix(full,source='92-limit.bin',limit=n)
            self.assertEqual(first['status'],'failed')
            self.assertLessEqual(first['consumedEnd'],n)
            self.assertEqual(first,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='92-limit.bin',limit=n))

    def test_tag92_bad_counts_and_headers(self):
        for at in (22,28,34,43,53,57,63,69,79,85,95,99,105,109):
            for value in (-2,2147483647):
                bad=bytearray(tag92());struct.pack_into('<i',bad,at,value)
                with self.subTest(at=at,value=value),self.assertRaises(FrameError) as caught:
                    sequence_frame(sequence(bad),source='92-count.bin')
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),
                                 ('92-count.bin',at+5,value,'count-bounds'))
        for at in (1,17,32,38):
            bad=bytearray(tag92());bad[at]=42
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad))
            self.assertEqual(caught.exception.diagnostic['offset'],at+5)
            self.assertEqual(caught.exception.diagnostic['category'],'member-count')

    def test_tag92_null_and_empty_profiles(self):
        children=[b'\x92\xff']
        for count in (-1,0):
            children.append(b'\x92\x13'+bytes(15)+b'\xff'+struct.pack('<i',count)+bytes(4)+payload(None)+
                            b'\xff\x80'+struct.pack('<i',count)+bytes(5)+b'\xff')
            item=b'\x05\xfe'+struct.pack('<i',count)+payload(None)+payload(b'')+b'\x80'
            children.append(b'\x92\x13'+bytes(15)+b'\xff'+struct.pack('<i',1)+item+bytes(4)+payload(None)+
                            b'\xff\x80'+struct.pack('<i',count)+bytes(5)+b'\xff')
        for child in children:
            raw=sequence(child)
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))

    def test_tag56_member_one_records_and_later_unknown(self):
        child=tag56();self.assertEqual(len(child),58)
        row=event_prefix(prefix(sequence(child,b'\x58')),source='56.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['actual'],88)
        self.assertEqual(row['consumedEnd'],19+58)
        self.assertIn(dict(start=19,end=77,kind='union',tag=86),row['completedRecords'])
        spans=[(r['start']-19,r['end']-19) for r in row['completedRecords'] if r['kind']=='anonymous-single-payload']
        self.assertEqual(spans,[(25,31),(31,32),(32,37)])
        self.assertIn(dict(start=60,end=77,kind='anonymous-query-profile'),row['completedRecords'])
        self.assertFalse(row['wholeSchemaExact'])

    def test_tag56_truncations_trailing_and_hard_limit(self):
        raw=sequence(tag56())
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError):sequence_frame(raw[:n])
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'x')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        full=prefix(raw)
        for n in range(len(full)):
            first=event_prefix(full,source='56-limit.bin',limit=n)
            self.assertEqual(first['status'],'failed')
            self.assertLessEqual(first['consumedEnd'],n)
            self.assertEqual(first,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='56-limit.bin',limit=n))

    def test_tag56_bad_counts_and_headers(self):
        good=tag56()
        for at in (15,21,26,33,46):
            for value in (-2,2147483647):
                bad=bytearray(good);struct.pack_into('<i',bad,at,value)
                with self.subTest(at=at,value=value),self.assertRaises(FrameError) as caught:
                    sequence_frame(sequence(bad),source='56-count.bin')
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),
                                 ('56-count.bin',at+5,value,'count-bounds'))
        for at in (1,25,32,41):
            bad=bytearray(good);bad[at]=42
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad))
            self.assertEqual(caught.exception.diagnostic['offset'],at+5)
            self.assertEqual(caught.exception.diagnostic['category'],'member-count')

    def test_tag56_nulls_and_empty_lists(self):
        children=[b'\x56\xff']
        for count in (-1,0):
            for key in (None,b''):
                for query in (b'\xff',b'\x02'+bytes(4)+struct.pack('<i',count)):
                    children.append(b'\x56\x08'+bytes(13)+payload(key)+struct.pack('<i',count)+bytes(4)+query)
        children.append(b'\x56\x08'+bytes(13)+payload(None)+struct.pack('<i',1)+b'\x01'+payload(b'')+bytes(4)+b'\xff')
        for child in children:
            raw=sequence(child)
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))

    def test_b4_exact_nested_boundaries_and_later_unknown(self):
        child=tag_b4();self.assertEqual(len(child),63)
        row=event_prefix(prefix(sequence(child,b'\x51')),source='b4.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['actual'],81)
        self.assertEqual(row['consumedEnd'],19+63)
        records=row['completedRecords']
        self.assertIn(dict(start=19,end=82,kind='union',tag=180),records)
        self.assertIn(dict(start=19+16,end=19+56,kind='anonymous-finder-profile'),records)
        self.assertIn(dict(start=19+39,end=19+56,kind='anonymous-query-profile'),records)
        self.assertFalse(row['wholeSchemaExact'])

    def test_b4_truncations_trailing_and_anchor_limit(self):
        raw=sequence(tag_b4())
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError):sequence_frame(raw[:n])
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'x')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        full=prefix(raw)
        for n in range(len(full)):
            first=event_prefix(full,source='b4-limit.bin',limit=n)
            self.assertEqual(first['status'],'failed')
            self.assertLessEqual(first['consumedEnd'],n)
            self.assertEqual(first,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='b4-limit.bin',limit=n))

    def test_b4_bad_counts_and_headers(self):
        good=tag_b4()
        for at in (17,21,27,31,44):
            for value in (-2,2147483647):
                bad=bytearray(good);struct.pack_into('<i',bad,at,value)
                with self.subTest(at=at,value=value),self.assertRaises(FrameError) as caught:
                    sequence_frame(sequence(bad),source='b4-count.bin')
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),
                                 ('b4-count.bin',at+5,value,'count-bounds'))
        for at in (1,16,39):
            bad=bytearray(good);bad[at]=42
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad))
            self.assertEqual(caught.exception.diagnostic['offset'],at+5)
            self.assertEqual(caught.exception.diagnostic['category'],'member-count')

    def test_b4_null_and_empty_nested_collections(self):
        children=[b'\xb4\xff',tag_b4(finder=b'\xff')]
        for count in (-1,0):
            for query in (b'\xff',b'\x02'+bytes(4)+struct.pack('<i',count)):
                children.append(tag_b4(finder=b'\x03'+struct.pack('<i',count)+bytes(4)+query))
        for child in children:
            raw=sequence(child)
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))

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
        for tag in (0xC0,0x40,0x71):
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
        row=event_prefix(prefix(sequence(tag_ec(),b'\x51')),source='ec-next.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['actual'],81)
        self.assertTrue(any(r.get('tag')==236 for r in row['completedRecords']))

    def test_tag50_ordered_pair_and_completed_record(self):
        child=tag50()
        raw=prefix(sequence(action(sequence(child),sequence(tag_ec()),b'\xff')))
        row=event_prefix(raw+b'opaque',source='50.bin',limit=len(raw))
        self.assertEqual(row['status'],'supported-prefix')
        union=next(r for r in row['completedRecords'] if r.get('tag')==80)
        self.assertEqual(union['end']-union['start'],len(child))
        items=[r for r in row['completedRecords'] if r['kind']=='anonymous-scalar-payload'
               and union['start']<r['start']<union['end']]
        self.assertEqual([(r['start'],r['end']) for r in items],
                         [(union['start']+19,union['start']+31),(union['start']+31,union['end'])])
        self.assertEqual(row['opaqueRemainderRange'],[len(raw),len(raw)+6])
        self.assertFalse(row['wholeSchemaExact'])

    def test_tag50_all_truncations_trailing_and_hard_limit(self):
        raw=sequence(tag50())
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError) as caught:
                sequence_frame(raw[:n],source='50-cut.bin')
            self.assertEqual(caught.exception.diagnostic['source'],'50-cut.bin')
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'x',source='50-tail.bin')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        full=prefix(raw)
        for n in range(len(full)):
            row=event_prefix(full,source='50-bound.bin',limit=n)
            self.assertEqual(row['status'],'failed')
            self.assertLessEqual(row['consumedEnd'],n)
            self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='50-bound.bin',limit=n))

    def test_tag50_malformed_lengths_and_headers(self):
        good=tag50()
        # Independently calculated positions, not derived from parser ranges.
        for at in (20,32):
            for n in (-2,2147483647):
                bad=bytearray(good);struct.pack_into('<i',bad,at,n)
                with self.subTest(at=at,n=n),self.assertRaises(FrameError) as caught:
                    sequence_frame(sequence(bad),source='50-length.bin')
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),
                                 ('50-length.bin',at+5,n,'count-bounds'))
        for at in (1,19,31):
            bad=bytearray(good);bad[at]=42
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad),source='50-header.bin')
            self.assertEqual(caught.exception.diagnostic['offset'],at+5)
            self.assertEqual(caught.exception.diagnostic['category'],'member-count')

    def test_tag50_nulls_empty_and_next_unknown(self):
        for child in (b'\x50\xff',tag50(b'\xff',b'\xff'),
                      tag50(scalar_payload(b''),scalar_payload(None)),
                      tag50(b'\xff',scalar_payload()),tag50(scalar_payload(),b'\xff')):
            raw=sequence(child)
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
        child=tag50()
        row=event_prefix(prefix(sequence(child,b'\x51')),source='50-next.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['actual'],81)
        self.assertEqual(row['consumedEnd'],19+len(child))
        self.assertTrue(any(r.get('tag')==80 for r in row['completedRecords']))

    def test_extended_tag_and_member8_record_ranges(self):
        child=tag11f()
        self.assertEqual(len(child),52)
        raw=prefix(sequence(action(sequence(child),b'\xff',sequence())))
        row=event_prefix(raw+b'opaque',source='11f.bin',limit=len(raw))
        self.assertEqual(row['status'],'supported-prefix')
        union=next(r for r in row['completedRecords'] if r.get('tag')==287)
        self.assertEqual(union['end']-union['start'],52)
        tag=next(r for r in row['ranges'] if r['start']==union['start'])
        self.assertEqual(tag,dict(start=union['start'],end=union['start']+3,kind='union-tag'))
        nested=[r for r in row['completedRecords'] if r['kind'] in ('anonymous-paired-payload','anonymous-scalar-payload')
                and union['start']<r['start']<union['end']]
        self.assertEqual([(r['start']-union['start'],r['end']-union['start']) for r in nested],
                         [(17,31),(31,41),(42,52)])
        self.assertEqual(row['opaqueRemainderRange'],[len(raw),len(raw)+6])
        self.assertFalse(row['wholeSchemaExact'])

    def test_extended_tag_truncation_and_unresolved_values(self):
        for wire in (b'\xfa',b'\xfa\x1f'):
            reader=Reader(wire,'tag-cut.bin')
            with self.assertRaises(FrameError) as caught:reader.action(0)
            self.assertEqual(caught.exception.diagnostic['category'],'truncated')
            self.assertEqual(caught.exception.diagnostic['offset'],0)
            self.assertEqual(reader.pos,0)
        for tag in (0,250,255,288,415,416,65535):
            wire=b'\xfa'+struct.pack('<H',tag)
            row=event_prefix(prefix(sequence(wire+tag11f())),source='unknown-u16.bin')
            self.assertEqual(row['status'],'unsupported')
            self.assertEqual(row['diagnostic']['actual'],tag)
            self.assertEqual(row['consumedEnd'],19)
            self.assertEqual(row['completedRecords'],[])
        # The selected helper does not impose a minimum u16 value after FA.
        for child in (tag50(),tag_ec(),tag76(),action()):
            expanded=b'\xfa'+struct.pack('<H',child[0])+child[1:]
            row=event_prefix(prefix(sequence(expanded)),source='wide-short.bin')
            self.assertEqual(row['status'],'supported-prefix')
            self.assertTrue(any(r.get('tag')==child[0] for r in row['completedRecords']))
        for lead in (251,252,253,254):
            row=event_prefix(prefix(sequence(bytes([lead]))),source='reserved.bin')
            self.assertEqual(row['status'],'unsupported')
            self.assertEqual(row['diagnostic']['actual'],lead)

    def test_tag11f_all_truncations_trailing_and_hard_limit(self):
        raw=sequence(tag11f())
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError) as caught:
                sequence_frame(raw[:n],source='11f-cut.bin')
            self.assertEqual(caught.exception.diagnostic['source'],'11f-cut.bin')
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'x',source='11f-tail.bin')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        full=prefix(raw)
        for n in range(len(full)):
            row=event_prefix(full,source='11f-bound.bin',limit=n)
            self.assertEqual(row['status'],'failed')
            self.assertLessEqual(row['consumedEnd'],n)
            self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='11f-bound.bin',limit=n))

    def test_tag11f_malformed_lengths_and_headers(self):
        good=tag11f()
        for at in (18,26,32,43,48):
            for value in (-2,2147483647):
                bad=bytearray(good);struct.pack_into('<i',bad,at,value)
                with self.subTest(at=at,value=value),self.assertRaises(FrameError) as caught:
                    sequence_frame(sequence(bad),source='11f-length.bin')
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),
                                 ('11f-length.bin',at+5,value,'count-bounds'))
        for at in (3,17,31,42):
            bad=bytearray(good);bad[at]=42
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad),source='11f-header.bin')
            self.assertEqual(caught.exception.diagnostic['offset'],at+5)
            self.assertEqual(caught.exception.diagnostic['category'],'member-count')

    def test_tag11f_null_variants_and_later_unknown(self):
        for child in (b'\xfa\x1f\x01\xff',tag11f(b'\xff',b'\xff',b'\xff'),
                      tag11f(pair(None,None),scalar_payload(b''),pair(b'',b''))):
            raw=sequence(child)
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
        child=tag11f()
        row=event_prefix(prefix(sequence(child,b'\xfa\x20\x01')),source='11f-next.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['actual'],288)
        self.assertEqual(row['consumedEnd'],19+len(child))
        self.assertTrue(any(r.get('tag')==287 for r in row['completedRecords']))

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

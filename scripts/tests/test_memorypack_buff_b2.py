"""Finite B2 nested shapes: physical limits, malformed counts and explicit gaps."""
import struct
import unittest

from scripts.game_data.memorypack.buff_actions import Reader, FrameError, Unsupported, event_prefix, sequence_frame
from scripts.tests.test_memorypack_buff_actions import direction, payload, prefix, scalar_payload, sequence, target


def count(items):
    return struct.pack('<i',-1 if items is None else len(items))+(b''.join(items) if items else b'')


def query():
    return b'\x02'+bytes.fromhex('FFFFFFFF')+count([bytes(4),bytes.fromhex('00000080')])


def vector():
    return b'\x03'+scalar_payload(b'long-key')+b'\xff'+scalar_payload(None)


def shape():
    return (b'\x12'+scalar_payload()+bytes(4)+vector()+bytes(8)+b'\xfe'+vector()+
            scalar_payload(None)+bytes(4)+b'\xff\x80'+scalar_payload(b'')+bytes(8)+
            scalar_payload()+bytes(4)+vector()+b'\xff')


def selection():
    return b'\x04\x03'+count([payload(b'k'),payload(None)])+bytes(4)+query()+count([b'\xff',b'\x01'+payload(b'id')])+bytes(4)+query()


def selector(finder=b'\xff',post=(),validators=()):
    return b'\x03'+finder+count(post)+count(validators)


def b2(nested=None):
    return (b'\xb2\x12\xfe'+bytes(12)+direction()+bytes(4)+payload(b'key')+bytes(4)+
            b'\x80'+payload(None)+(selector() if nested is None else nested)+bytes(8)+
            payload(b'\xff\x00')+bytes(4)+payload(b'last')+b'\xfe\xff')


class BuffB2Tests(unittest.TestCase):
    def fixtures(self):
        finders=[b'\x02\x00',b'\x07\x08'+b'\xfe\x80\xff'+bytes(8)+b'\x02'+count([shape(),b'\xff'])+bytes(4),
                 b'\x08\x00',b'\x0c\x01'+query(),b'\x0d\x01'+bytes(4),b'\x13\x04\xfe'+scalar_payload()+selection()+b'\x80']
        post7=b'\x07\x06\x02\x03'+count([payload(b'filter')])+bytes(4)+query()+bytes(4)+bytes(4)+b'\xff'+bytes(4)+b'\x80'+bytes(4)
        return [b2(selector(f,post=[b'\x04\x02'+target()+bytes(4),post7],validators=[b'\x04\x03\xfe'+bytes(4)+scalar_payload(),b'\x05\x00',b'\x09\x00',b'\x0a\x00',b'\x0b\x01'+query()])) for f in finders]

    def test_nested_fixtures_and_atomic_tiling(self):
        for child in self.fixtures():
            full=prefix(sequence(child,b'\x79'))
            row=event_prefix(full,source='b2.bin')
            self.assertEqual(row['status'],'unsupported')
            self.assertEqual(row['diagnostic']['offset'],19+len(child))
            self.assertEqual(row['diagnostic']['actual'],121)
            self.assertIn(dict(start=19,end=19+len(child),kind='union',tag=178),row['completedRecords'])
            self.assertFalse(row['wholeSchemaExact'])
            self.assertEqual(row['evidenceLevel'],'structural-only')
            spans=row['ranges'];self.assertEqual(spans[0]['start'],0)
            for a,b in zip(spans,spans[1:]):self.assertEqual(a['end'],b['start'])
            self.assertEqual(spans[-1]['end'],row['opaqueRemainderRange'][0])

    def test_every_truncation_limit_and_trailing_byte(self):
        for child in self.fixtures():
            raw=sequence(child)
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.subTest(n=n),self.assertRaises(FrameError):sequence_frame(raw[:n])
            with self.assertRaises(FrameError):sequence_frame(raw+b'x')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='b2-limit',limit=n)
                self.assertEqual(row['status'],'failed')
                self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='b2-limit',limit=n))

    def test_null_and_extended_union_tags(self):
        for method,tags,header in [('selector_finder_profile',(2,7,8,12,13,19),None),
                                  ('selector_validator_profile',(4,5,9,10,11),None),
                                  ('selector_postprocessor_profile',(4,7),None)]:
            for raw in [b'\xff']+[bytes([t,255]) for t in tags]+[b'\xfa'+struct.pack('<H',t)+b'\xff' for t in tags]:
                r=Reader(raw,'null');getattr(r,method)();self.assertEqual(r.pos,len(raw))
            for raw in (b'\xfa',b'\xfa\x00',b'\xfa\xff\xff',b'\xfe'):
                r=Reader(raw,'unknown')
                with self.assertRaises(FrameError):getattr(r,method)()
                self.assertEqual(r.pos,0)
        for raw in (b'\xb2\xff',b'\xfa\xb2\x00'+b2()[1:],b2(selector(post=None,validators=None))):
            self.assertEqual(sequence_frame(sequence(raw))[-1]['end'],len(sequence(raw)))
        for method in ('shape_profile','vector_payload','selection_profile','filter_profile'):
            r=Reader(b'\xff','null');getattr(r,method)();self.assertEqual(r.pos,1)

    def test_malformed_counts_headers_and_vector_shape(self):
        for child in self.fixtures():
            raw=prefix(sequence(child));row=event_prefix(raw,source='bounds')
            for span in row['ranges']:
                if span['kind'] not in ('count-i32','member-header'):continue
                for value in ((-2,2147483647) if span['kind']=='count-i32' else (42,)):
                    bad=bytearray(raw);at=span['start']
                    if span['kind']=='count-i32':struct.pack_into('<i',bad,at,value)
                    else:bad[at]=value
                    failed=event_prefix(bad,source='bounds')
                    self.assertEqual(failed['status'],'failed')
                    self.assertEqual(failed['diagnostic']['offset'],at)
        r=Reader(b'\x03'+bytes(12),'not-three-raw-floats')
        with self.assertRaises(FrameError):r.vector_payload()
        self.assertEqual(r.pos,1)

    def test_recursive_postprocessor_stops_before_second_header(self):
        inner=b'\x04\x02'+target()+bytes(4)
        outer=b'\x04\x02'+target(selector=selector(post=[inner]))+bytes(4)
        row=event_prefix(prefix(sequence(b2(selector(post=[outer])))),source='recursive')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['category'],'depth-limit')
        self.assertEqual(row['diagnostic']['actual'],2)
        self.assertFalse(any(r.get('tag')==178 for r in row['completedRecords']))


if __name__=='__main__':unittest.main()

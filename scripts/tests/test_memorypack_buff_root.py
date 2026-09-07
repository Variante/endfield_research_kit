import struct
import unittest

from scripts.game_data.memorypack.buff_actions import FrameError, root_continuation


def i32(value):
    return struct.pack('<i',value)


def scalar(payload=b'abc'):
    return b'\x03'+i32(len(payload))+payload+b'\x80'+b'\x01\x02\x03\x04'


class BuffRootContinuationTests(unittest.TestCase):
    def frame(self,segment,**kwargs):
        return root_continuation(b'P'+segment,source='root-fixture',start=1,**kwargs)

    def test_nested_elements_and_raw_array_have_distinct_boundaries(self):
        child=b'\x04'+bytes(12)+scalar()
        segment=scalar()+i32(2)+b'\xff\x01\x02\x03'*2+b'\x02'+i32(2)+b'\xff'+child+b'\x91'+i32(0)
        result=self.frame(segment)
        self.assertEqual(result['status'],'supported-prefix')
        self.assertEqual(result['consumedEnd'],len(segment)+1)
        cursor=1
        for span in result['ranges']:
            self.assertEqual(span['start'],cursor)
            cursor=span['end']
        self.assertEqual(cursor,len(segment)+1)
        array=next(r for r in result['completedRecords'] if r['kind']=='anonymous-dword-array')
        self.assertEqual(array['end']-array['start'],12)
        elements=[r for r in result['completedRecords'] if r['kind']=='anonymous-modifier-element-profile']
        self.assertEqual([r['end']-r['start'] for r in elements],[1,len(child)])
        self.assertFalse(result['wholeSchemaExact'])

    def test_all_truncations_and_outside_limit_bytes_fail_identically(self):
        segment=scalar()+i32(2)+bytes(8)+b'\x02'+i32(2)+b'\xff\x04'+bytes(12)+scalar()+b'\x01'+i32(1)+b'\x04\x80'+i32(0)+bytes(8)+i32(0)
        physical=b'P'+segment
        for cut in range(1,len(physical)):
            with self.subTest(cut=cut):
                outputs=[root_continuation(data,source='cut',start=1,limit=cut)
                         for data in (physical,physical[:cut],physical[:cut]+b'\xff'*100)]
                for result in outputs:
                    self.assertEqual(result['status'],'failed')
                    self.assertLessEqual(result['consumedEnd'],cut)
                    self.assertFalse(any(r['kind']=='anonymous-data-pair-collection-profile' for r in result['completedRecords']))
                for key in ('diagnostic','consumedEnd','ranges','completedRecords'):
                    self.assertEqual(outputs[0][key],outputs[1][key])
                    self.assertEqual(outputs[0][key],outputs[2][key])

    def test_null_and_empty_arrays_preserve_required_final_byte(self):
        for count in (-1,0):
            segment=b'\xff'+i32(count)+b'\x02'+i32(count)
            self.assertEqual(self.frame(segment)['status'],'failed')
            self.assertEqual(self.frame(segment+b'\x01'+i32(0))['status'],'supported-prefix')
        self.assertEqual(self.frame(b'\xff'+i32(-1)+b'\xff'+i32(0))['status'],'supported-prefix')
        self.assertEqual(self.frame(b'\xff'+i32(0)+b'\x02'+i32(1)+b'\xff\x00'+i32(0))['status'],'supported-prefix')

    def test_malformed_lengths_counts_and_headers_have_actionable_diagnostics(self):
        cases=[(b'\x02','member-count'),
               (b'\x03'+i32(-2),'count-bounds'),
               (b'\xff'+i32(-2),'count-bounds'),
               (b'\xff'+i32(0x7fffffff),'count-bounds'),
               (b'\xff'+i32(0)+b'\x02'+i32(-2)+b'\x00','count-bounds'),
               (b'\xff'+i32(0)+b'\x02'+i32(2)+b'\xff','count-bounds'),
               (b'\xff'+i32(0)+b'\x02'+i32(1)+b'\x03\x00','member-count')]
        for segment,category in cases:
            with self.subTest(segment=segment):
                result=self.frame(segment)
                self.assertEqual(result['status'],'failed')
                diagnostic=result['diagnostic']
                self.assertEqual(diagnostic['source'],'root-fixture')
                self.assertEqual(diagnostic['category'],category)
                self.assertIsInstance(diagnostic['offset'],int)
                self.assertIn('expected',diagnostic)
                self.assertIn('actual',diagnostic)

    def test_tail_stays_explicitly_opaque_and_cannot_satisfy_a_bounded_read(self):
        segment=b'\xff'+i32(0)+b'\xff'+i32(0)
        for tail in (b'\xff',b'\x00'*20):
            result=self.frame(segment+tail,limit=len(segment)+1)
            self.assertEqual(result['status'],'supported-prefix')
            self.assertEqual(result['opaqueRemainderRange'],[len(segment)+1,len(segment+tail)+1])
        for start in (0,-1,True,100):
            with self.assertRaises(FrameError):
                root_continuation(b'abc',source='start',start=start)

    def test_fifth_collection_keeps_eight_raw_bytes_and_independent_payloads(self):
        prefix=b'\xff'+i32(0)+b'\xff'
        pair=b'\x04\xff'+i32(3)+b'key'+b'\xff\x01\x02\x03\x04\x05\x06\x07'+i32(5)+b'value'
        for count,body in ((-1,b''),(0,b''),(2,b'\xff'+pair)):
            with self.subTest(count=count):
                result=self.frame(prefix+i32(count)+body+b'opaque')
                self.assertEqual(result['status'],'supported-prefix')
                self.assertEqual(result['consumedEnd'],1+len(prefix)+4+len(body))
                parent=result['completedRecords'][-1]
                self.assertEqual((parent['kind'],parent['count']),('anonymous-data-pair-collection-profile',count))
                elements=[r for r in result['completedRecords'] if r['kind']=='anonymous-data-pair-profile']
                self.assertEqual([r['end']-r['start'] for r in elements],[] if count<=0 else [1,len(pair)])
        for first in (-1,0):
            for last in (-1,0):
                result=self.frame(prefix+i32(1)+b'\x04\x00'+i32(first)+bytes(8)+i32(last))
                self.assertEqual(result['status'],'supported-prefix')

    def test_fifth_counts_and_both_payload_lengths_fail_closed(self):
        prefix=b'\xff'+i32(0)+b'\xff'
        malformed=[(i32(-2),'count-bounds'),(i32(0x7fffffff),'count-bounds'),
                   (i32(1)+b'\x05','member-count'),
                   (i32(1)+b'\x04\x00'+i32(-2),'count-bounds'),
                   (i32(1)+b'\x04\x00'+i32(0)+bytes(8)+i32(-2),'count-bounds')]
        for fifth,category in malformed:
            with self.subTest(fifth=fifth):
                result=self.frame(prefix+fifth)
                self.assertEqual(result['status'],'failed')
                self.assertEqual(result['diagnostic']['category'],category)
                self.assertGreaterEqual(result['diagnostic']['offset'],1+len(prefix))
                self.assertFalse(any(r['kind']=='anonymous-data-pair-collection-profile' for r in result['completedRecords']))

    def test_incomplete_fifth_element_preserves_only_completed_predecessors(self):
        prefix=b'\xff'+i32(0)+b'\xff'+i32(2)
        complete=b'\x04\x00'+i32(1)+b'a'+bytes(8)+i32(1)+b'b'
        for cut in range(len(complete)):
            result=self.frame(prefix+b'\xff'+complete[:cut])
            self.assertEqual(result['status'],'failed')
            elements=[r for r in result['completedRecords'] if r['kind']=='anonymous-data-pair-profile']
            # With no second element byte, the count gate rejects the entire
            # loop before even the first null element is consumed.
            self.assertEqual(len(elements),0 if cut==0 else 1)
            if elements:self.assertEqual(elements[0]['end']-elements[0]['start'],1)


if __name__=='__main__':
    unittest.main()

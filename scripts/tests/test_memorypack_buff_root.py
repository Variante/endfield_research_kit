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
        segment=scalar()+i32(2)+b'\xff\x01\x02\x03'*2+b'\x02'+i32(2)+b'\xff'+child+b'\x91'
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
        segment=scalar()+i32(2)+bytes(8)+b'\x02'+i32(2)+b'\xff\x04'+bytes(12)+scalar()+b'\x01'
        physical=b'P'+segment
        for cut in range(1,len(physical)):
            with self.subTest(cut=cut):
                outputs=[root_continuation(data,source='cut',start=1,limit=cut)
                         for data in (physical,physical[:cut],physical[:cut]+b'\xff'*100)]
                for result in outputs:
                    self.assertEqual(result['status'],'failed')
                    self.assertLessEqual(result['consumedEnd'],cut)
                    self.assertFalse(any(r['kind']=='anonymous-modifier-collection-profile' for r in result['completedRecords']))
                for key in ('diagnostic','consumedEnd','ranges','completedRecords'):
                    self.assertEqual(outputs[0][key],outputs[1][key])
                    self.assertEqual(outputs[0][key],outputs[2][key])

    def test_null_and_empty_arrays_preserve_required_final_byte(self):
        for count in (-1,0):
            segment=b'\xff'+i32(count)+b'\x02'+i32(count)
            self.assertEqual(self.frame(segment)['status'],'failed')
            self.assertEqual(self.frame(segment+b'\x01')['status'],'supported-prefix')
        self.assertEqual(self.frame(b'\xff'+i32(-1)+b'\xff')['status'],'supported-prefix')
        self.assertEqual(self.frame(b'\xff'+i32(0)+b'\x02'+i32(1)+b'\xff\x00')['status'],'supported-prefix')

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
        segment=b'\xff'+i32(0)+b'\xff'
        for tail in (b'\xff',b'\x00'*20):
            result=self.frame(segment+tail,limit=len(segment)+1)
            self.assertEqual(result['status'],'supported-prefix')
            self.assertEqual(result['opaqueRemainderRange'],[len(segment)+1,len(segment+tail)+1])
        for start in (0,-1,True,100):
            with self.assertRaises(FrameError):
                root_continuation(b'abc',source='start',start=start)


if __name__=='__main__':
    unittest.main()

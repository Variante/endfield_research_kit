import struct
import unittest
from unittest.mock import patch

from scripts.game_data.memorypack.skill_timeline_cursor import (
    _merge_action_reader_ranges,
    _selected_action_reader_candidate,
)


def _self_rotate_action(member_header=18):
    return (
        b'\xFA\x44\x01'
        + bytes((member_header, 0))
        + bytes(12)
        + b'\xFF'  # DirectionSettings null wrapper.
        + bytes(5)
        + struct.pack('<i', -1)  # Null signed-length payload.
        + bytes(12)
        + struct.pack('<I', 0x7FC00001)  # Preserve a non-finite raw float32 bit pattern.
        + bytes(4)
        + b'\xFF'  # TargetSettings null wrapper.
        + b'\x07'
    )


class SelectedActionReaderCandidateTests(unittest.TestCase):
    def setUp(self):
        self.reader_evidence = {
            'tag': 0x144,
            'rootMemberCount': 18,
            'rootReadOrderKey': 'member18',
            'contractFile': 'buff_144_native.json',
            'contractSha256': 'A' * 64,
        }
        self.route = {}

    def read_candidate(self, raw, start, hard_limit):
        with patch(
                'scripts.game_data.memorypack.skill_timeline_cursor.'
                'skilldata_action_union_static_reader_evidence',
                return_value=self.reader_evidence):
            return _selected_action_reader_candidate(
                raw, start, hard_limit, tag=0x144,
                reader_contract={}, routes=self.route, image_base=0x180000000,
                source='test-current-skilldata')

    def test_reader_candidate_maps_ranges_and_stops_before_trailing_byte(self):
        action = _self_rotate_action()
        start = 7
        raw = bytes(start) + action + b'\xAA\xBB'
        candidate = self.read_candidate(raw, start, len(raw))

        self.assertTrue(candidate['complete'])
        self.assertEqual(candidate['recordEndCandidate']['start'], start)
        self.assertEqual(candidate['recordEndCandidate']['end'], start + len(action))
        self.assertEqual(candidate['cursor'], start + len(action))
        cursor = start
        for span in candidate['ranges']:
            self.assertEqual(span['start'], cursor)
            self.assertLessEqual(span['end'], candidate['cursor'])
            self.assertEqual(
                raw[span['start']:span['end']].hex().upper(), span['rawHex'])
            cursor = span['end']
        self.assertEqual(cursor, candidate['cursor'])

    def test_truncated_nested_body_stops_at_hard_limit(self):
        action = _self_rotate_action()
        start = 4
        raw = bytes(start) + action
        hard_limit = start + len(action) - 1
        candidate = self.read_candidate(raw, start, hard_limit)

        self.assertFalse(candidate['complete'])
        self.assertEqual(candidate['failure']['category'], 'truncated')
        self.assertEqual(candidate['cursor'], hard_limit)
        self.assertTrue(all(span['end'] <= hard_limit for span in candidate['ranges']))

    def test_bad_native_member_header_consumes_only_the_known_union_tag(self):
        action = _self_rotate_action(member_header=17)
        start = 3
        raw = bytes(start) + action
        candidate = self.read_candidate(raw, start, len(raw))

        self.assertFalse(candidate['complete'])
        self.assertEqual(candidate['status'], 'stopped-before-selected-action-member-header')
        self.assertEqual(candidate['failure']['category'], 'member-count')
        self.assertEqual(candidate['cursor'], start + 3)
        self.assertEqual(candidate['ranges'], [{
            'start': start, 'end': start + 3,
            'kind': 'AbilityActionData.union-tag', 'rawHex': 'FA4401',
        }])

    def test_unknown_nested_finder_tag_stays_unconsumed_and_parent_stays_open(self):
        # SelfRotateAction -> TargetSettings -> SelectorSettings -> finder tag.
        target_with_unknown_finder = (
            b'\x0D\xFF'                  # TargetSettings header, null direction.
            + struct.pack('<i', -1)        # Null first byte payload.
            + b'\x00' + bytes(4) + b'\x00'
            + struct.pack('<i', -1)        # Null second byte payload.
            + b'\x03\x06'                # SelectorSettings header, unsupported finder tag 6.
        )
        action_prefix = (
            b'\xFA\x44\x01' + b'\x12\x00' + bytes(12) + b'\xFF'
            + bytes(5) + struct.pack('<i', -1) + bytes(12)
            + bytes(8) + target_with_unknown_finder
        )
        candidate = self.read_candidate(action_prefix + b'\x07', 0, len(action_prefix) + 1)

        self.assertFalse(candidate['complete'])
        self.assertEqual(candidate['status'], 'stopped-at-unsupported-action-subreader-tag')
        self.assertEqual(candidate['failure']['sourceCategory'], 'nested-profile')
        self.assertEqual(candidate['failure']['actual'], 6)
        self.assertEqual(candidate['cursor'], len(action_prefix) - 1)
        self.assertIsNone(candidate['recordEndCandidate'])
        self.assertTrue(all(span['end'] <= candidate['cursor'] for span in candidate['ranges']))
        self.assertFalse(any(span['start'] <= candidate['cursor'] < span['end']
                             for span in candidate['ranges']))

    def test_action_reader_extends_only_after_existing_candidate_cursor(self):
        action = _self_rotate_action()
        start = 10
        raw = bytes(start) + action
        old_cursor = start + 5  # Extended tag, root header, first byte member.
        alignment = {
            'candidateStart': start,
            'candidateCursor': old_cursor,
            'hardLimit': len(raw),
            'candidateByteRanges': [
                {'start': start, 'end': start + 3, 'kind': 'tag'},
                {'start': start + 3, 'end': start + 4, 'kind': 'header'},
                {'start': start + 4, 'end': old_cursor, 'kind': 'member0'},
            ],
        }
        candidate = self.read_candidate(raw, start, len(raw))

        accepted, reason = _merge_action_reader_ranges(
            alignment, candidate, source='test-current-skilldata')

        self.assertTrue(accepted, reason)
        self.assertEqual(alignment['candidateCursor'], start + len(action))
        cursor = start
        for span in alignment['candidateByteRanges']:
            self.assertEqual(span['start'], cursor)
            cursor = span['end']
        self.assertEqual(cursor, alignment['candidateCursor'])


if __name__ == '__main__':
    unittest.main()

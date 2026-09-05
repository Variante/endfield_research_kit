from __future__ import annotations

import struct
import unittest
from typing import Any
from unittest.mock import patch

from scripts.game_data.memorypack import skill_terminal as n
from scripts.game_data.memorypack.skill import frame_skill_memorypack


def u32(value: int) -> bytes:
    return struct.pack('<I', value)


def terminal(
    *,
    wrapped: bool = False,
    count: int = 0,
    records: bytes = b'',
    objects_a: tuple[bytes, ...] = (),
    objects_b: tuple[bytes, ...] = (),
    first: int = 0,
    last: int = 0,
) -> bytes:
    return b''.join((
        bytes([first]), b'\x01' if wrapped else b'', u32(count), records,
        u32(len(objects_a)), b''.join(objects_a),
        u32(len(objects_b)), b''.join(objects_b), bytes([last]),
    ))


def hint() -> bytes:
    word = struct.pack('<f', 0)
    string = u32(0xFFFFFFFF)
    pair = word * 2
    shape = b''.join((
        b'\x15', word, string, b'\x00', pair, string * 2, pair, string * 2,
        b'\x00', word, string, b'\x00', u32(0), b'\x00' * 5, word, string,
    ))
    assert len(shape) == 69
    return b'\x03\x00' + shape + u32(0)


class TerminalTests(unittest.TestCase):
    def parse(
        self, data: bytes, start: int = 0, base: int = 0
    ) -> dict[str, Any]:
        return n.frame_skill_terminal_at(
            data, start, source='fixture.skill', base_offset=base
        )

    def test_normal_counted(self) -> None:
        parsed = self.parse(terminal())
        self.assertEqual(parsed['candidateCount'], 1)
        candidate = parsed['candidates'][0]
        self.assertEqual(candidate['encoding'], 'counted')
        self.assertEqual(
            [(m['range']['start'], m['range']['end'])
             for m in candidate['members']],
            [(0, 1), (1, 5), (5, 9), (9, 13), (13, 14)],
        )

    def test_empty_wrapper_preserved_with_adjacent_direct(self) -> None:
        data = b'\x30\x7f' + terminal(wrapped=True)
        parsed = frame_skill_memorypack(data, source='fixture.skill')
        self.assertEqual(
            [(c['startOffset'], c['encoding']) for c in parsed['candidates']],
            [('0x2', 'one-member-wrapper'), ('0x3', 'counted')],
        )
        self.assertEqual(parsed['status'], 'ambiguous-exact-terminal-shape')

    def test_both_legacy_collision_shapes(self) -> None:
        samples = [
            (0x1F1, [0x8CF01A14], 517),
            (0x18A, [0x61F8280C, 0x0BA6F0A8, 0x1A17C9AA], 424),
        ]
        for start, values, end in samples:
            with self.subTest(start=start):
                data = b'\x30' + b'\x7f' * (start - 1) + terminal(
                    wrapped=True, count=len(values),
                    records=b''.join(b'\x01' + u32(v) for v in values),
                )
                self.assertEqual(len(data), end)
                parsed = frame_skill_memorypack(
                    data, source='synthetic-reproduction.skill'
                )
                identities = [
                    (c['startOffset'], c['encoding'])
                    for c in parsed['candidates']
                ]
                self.assertEqual(identities, [
                    (f'0x{start:x}', 'one-member-wrapper'),
                    (f'0x{start + 1:x}', 'counted'),
                ])

    def test_null_collection_is_not_zero(self) -> None:
        for wrapped in (False, True):
            parsed = self.parse(terminal(wrapped=wrapped, count=0xFFFFFFFF))
            encoding = 'one-member-wrapper' if wrapped else 'counted'
            candidate = next(
                c for c in parsed['candidates'] if c['encoding'] == encoding
            )
            self.assertIsNone(candidate['members'][1]['count'])
            self.assertEqual(candidate['members'][1]['records'], [])

    def test_all_records_not_sampled(self) -> None:
        records = b''.join(b'\x01' + u32(0xDEADBEEF) for _ in range(9))
        parsed = self.parse(terminal(
            count=9, records=records,
            objects_a=(b'\x02' + u32(0) * 2,) * 9,
            objects_b=(hint(),) * 9,
        ))
        for member in parsed['candidates'][0]['members'][1:4]:
            self.assertEqual(len(member['records']), 9)
            spans = [record['range'] for record in member['records']]
            self.assertTrue(all(
                a['end'] == b['start'] for a, b in zip(spans, spans[1:])
            ))
            self.assertEqual(spans[-1]['end'], member['range']['end'])

    def test_tag_record_member2_ranges(self) -> None:
        parsed = self.parse(terminal(
            count=1, records=b'\x02' + u32(7) + u32(0xFFFFFFFF)
        ))
        record = parsed['candidates'][0]['members'][1]['records'][0]
        self.assertEqual(record['range'], {'start': 5, 'end': 14, 'byteLength': 9})
        self.assertEqual(
            [m['range']['byteLength'] for m in record['members']], [4, 4]
        )

    def test_strict_utf8_and_no_identifier_semantic_filter(self) -> None:
        with self.assertRaises(n.TerminalError) as caught:
            self.parse(terminal(
                count=1, records=b'\x02' + u32(7) + u32(1) + b'\xff'
            ), base=0x100)
        error = next(
            row for row in caught.exception.diagnostics
            if row['gate'] == 'encoded-string.utf8'
        )
        self.assertEqual(error['offset'], 0x10E)
        text = '\u533f\u540d \u7a7a\u683c'
        raw = text.encode('utf-8')
        parsed = self.parse(terminal(
            count=1, records=b'\x02' + u32(7) + u32(len(raw)) + raw
        ))
        record = parsed['candidates'][0]['members'][1]['records'][0]
        self.assertEqual(record['members'][1]['value'], text)

    def test_nested_minimum_75_bytes_is_exact_fixture(self) -> None:
        # Inner: header1 +7 shortest string prefixes4 +8 bools +8 words4.
        # Outer: header1 +bool1 +inner69 +word4. This is not a fixed size.
        self.assertEqual(1 + 7 * 4 + 8 + 8 * 4, 69)
        self.assertEqual(1 + 1 + 69 + 4, 75)
        data = hint()
        self.assertEqual(len(data), 75)
        record, end = n.buff.read_skill_ui_range_hint_data(data, 0, 0)
        self.assertEqual((record['byteLength'], end), (75, 75))
        with self.assertRaises((ValueError, struct.error)):
            n.buff.read_skill_ui_range_hint_data(data[:-1], 0, 0)

    def test_corrupt_member_count_and_bool(self) -> None:
        for header in (0, 3, 255):
            with self.subTest(header=header), self.assertRaises(n.TerminalError):
                self.parse(terminal(
                    count=1, records=bytes([header]) + u32(7) + u32(0xFFFFFFFF)
                ))
        for first, last in [(2, 0), (0, 2)]:
            with self.assertRaises(n.TerminalError):
                self.parse(terminal(first=first, last=last))

    def test_all_truncations_and_trailing_bytes(self) -> None:
        data = terminal(count=1, records=b'\x01' + u32(0xDEADBEEF))
        for length in range(len(data)):
            with self.subTest(length=length), self.assertRaises(n.TerminalError):
                self.parse(data[:length])
        for extra in (b'\x00', b'\x01', b'\x02', b'\xff'):
            with self.subTest(extra=extra), self.assertRaises(n.TerminalError):
                self.parse(data + extra)

    def test_count_limits_and_minimum_bounds_before_nested_reader(self) -> None:
        malformed_counts = [
            terminal(count=129), terminal(count=0xFFFFFFFE),
            b'\x00' + u32(0) + u32(257) + u32(0) + b'\x00',
            b'\x00' + u32(0) + u32(0) + u32(33) + b'\x00',
        ]
        for data in malformed_counts:
            with self.assertRaises(n.TerminalError):
                self.parse(data)
        insufficient_bytes = [
            terminal(count=128),
            b'\x00' + u32(0) + u32(256) + u32(0) + b'\x00',
            b'\x00' + u32(0) + u32(0) + u32(32) + b'\x00',
        ]
        for data in insufficient_bytes:
            with patch.object(
                n.buff, 'read_skill_toggle_buff_data',
                side_effect=AssertionError('must reject first'),
            ), patch.object(
                n.buff, 'read_skill_ui_range_hint_data',
                side_effect=AssertionError('must reject first'),
            ):
                with self.assertRaises(n.TerminalError) as caught:
                    self.parse(data)
            self.assertTrue(any(
                'minimum-bytes' in row['gate']
                for row in caught.exception.diagnostics
            ))

    def test_bad_offset_and_precise_source_diagnostic(self) -> None:
        for start in (-1, True, 100):
            with self.assertRaises(n.TerminalError):
                self.parse(terminal(), start)
        for base in (-1, True):
            with self.assertRaises(n.TerminalError):
                self.parse(terminal(), base=base)
        with self.assertRaises(n.TerminalError) as caught:
            self.parse(b'\x00\x01', base=0x100)
        diagnostic = caught.exception.diagnostics[0]
        self.assertEqual(diagnostic['source'], 'fixture.skill')
        self.assertEqual(diagnostic['offset'], 0x101)
        self.assertIn('expected', diagnostic)
        self.assertIn('actual', diagnostic)

    def test_search_rejection_is_unresolved_not_malformed(self) -> None:
        parsed = frame_skill_memorypack(b'\x30\x7f\x00', source='fixture.skill')
        self.assertEqual(parsed['status'], 'terminal-shape-unresolved')
        self.assertEqual(parsed['candidates'], [])

    def test_same_start_encodings_not_deduplicated_control_flow(self) -> None:
        # Control-flow fixture, not a naturally occurring same-start layout.
        def branch(
            data: bytes, start: int, source: str, base: int, encoding: str
        ) -> dict[str, Any]:
            return dict(start=start, end=len(data), encoding=encoding)

        with patch.object(n, '_parse_branch', side_effect=branch):
            parsed = self.parse(b'fixture')
        self.assertEqual(parsed['candidateCount'], 2)
        self.assertEqual(parsed['status'], 'ambiguous-exact-terminal-shape')
        self.assertEqual(
            [row['encoding'] for row in parsed['candidates']],
            ['counted', 'one-member-wrapper'],
        )


if __name__ == '__main__':
    unittest.main()

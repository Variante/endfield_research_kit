"""Anonymous SkillData terminal candidate framing; no native/field-order claim."""

from __future__ import annotations

import struct
from typing import Any, NoReturn

from scripts.game_data.memorypack import buff


class TerminalError(ValueError):
    def __init__(self, diagnostics: list[dict[str, Any]]) -> None:
        self.diagnostics = diagnostics
        first = diagnostics[0]
        super().__init__(
            f"{first['source']}@0x{first['offset']:x}: {first['gate']} "
            f"expected={first['expected']!r} actual={first['actual']!r}"
        )

def _span(start: int, end: int, base: int) -> dict[str, int]:
    return {'start': base + start, 'end': base + end, 'byteLength': end - start}


class Cursor:
    def __init__(
        self, data: bytes, start: int, source: str, base: int, encoding: str
    ) -> None:
        self.data = data
        self.pos = start
        self.source = source
        self.base = base
        self.encoding = encoding

    def fail(
        self,
        gate: str,
        expected: Any,
        actual: Any,
        offset: int | None = None,
    ) -> NoReturn:
        raise TerminalError([{
            'source': self.source,
            'offset': self.base + (self.pos if offset is None else offset),
            'gate': gate,
            'expected': expected,
            'actual': actual,
            'encoding': self.encoding,
        }])

    def require(self, n: int, gate: str) -> None:
        if n > len(self.data) - self.pos:
            self.fail(
                gate, f'at least {n} remaining bytes', len(self.data) - self.pos
            )

    def u32(self, gate: str) -> int:
        self.require(4, gate)
        value = struct.unpack_from('<I', self.data, self.pos)[0]
        self.pos += 4
        return value

    def boolean(self, gate: str) -> bool:
        self.require(1, gate)
        value = self.data[self.pos]
        if value not in (0, 1):
            self.fail(gate, [0, 1], value)
        self.pos += 1
        return bool(value)

    def count(
        self,
        gate: str,
        maximum: int,
        minimum: int,
        reserve: int,
        nullable: bool = False,
    ) -> tuple[int | None, dict[str, int]]:
        start = self.pos
        value = self.u32(gate)
        if nullable and value == 0xFFFFFFFF:
            return (None, _span(start, self.pos, self.base))
        if value > maximum:
            self.fail(gate + '.limit', f'0..{maximum}', value, start)
        available = len(self.data) - self.pos - reserve
        if available < 0 or value > available // minimum:
            self.fail(
                gate + '.minimum-bytes',
                {
                    'count': value,
                    'minimumItemBytes': minimum,
                    'reservedTailBytes': reserve,
                    'required': value * minimum + reserve,
                },
                len(self.data) - self.pos,
                start,
            )
        return (value, _span(start, self.pos, self.base))

def _parse_branch(
    data: bytes, start: int, source: str, base: int, encoding: str
) -> dict[str, Any]:
    c = Cursor(data, start, source, base, encoding)
    members = []
    first = c.boolean('member[0].bool')
    members.append({
        'index': 0, 'kind': 'bool', 'value': first,
        'range': _span(start, c.pos, base),
    })
    list_start = c.pos
    wrapper = None
    if encoding == 'one-member-wrapper':
        c.require(1, 'member[1].wrapper')
        if data[c.pos] != 1:
            c.fail('member[1].wrapper', 1, data[c.pos])
        wrapper = _span(c.pos, c.pos + 1, base)
        c.pos += 1
    # Wrapped null is a structural grammar candidate, not runtime legality.
    count, count_range = c.count('member[1].count', 128, 5, 9, nullable=True)
    records = []
    for index in range(count or 0):
        record_start = c.pos
        c.require(1, f'member[1].record[{index}].header')
        header = data[c.pos]
        c.pos += 1
        if header not in (1, 2):
            c.fail(
                f'member[1].record[{index}].member-count',
                [1, 2], header, record_start,
            )
        fields = []
        field_start = c.pos
        value = c.u32(f'member[1].record[{index}].member[0]')
        fields.append({
            'index': 0, 'kind': 'u32', 'value': value,
            'range': _span(field_start, c.pos, base),
        })
        if header == 2:
            field_start = c.pos
            length = c.u32(f'member[1].record[{index}].member[1].string-prefix')
            if length == 0xFFFFFFFF:
                text = None
            else:
                if length > 256:
                    c.fail(
                        'encoded-string.length', '0..256 or null sentinel',
                        length, field_start,
                    )
                c.require(length, 'encoded-string.bytes')
                raw = data[c.pos:c.pos + length]
                try:
                    text = raw.decode('utf-8', errors='strict')
                except UnicodeDecodeError as exc:
                    c.fail(
                        'encoded-string.utf8', 'valid UTF-8 byte sequence',
                        raw[exc.start:exc.end].hex(), c.pos + exc.start,
                    )
                c.pos += length
            fields.append({
                'index': 1, 'kind': 'encoded-string', 'value': text,
                'range': _span(field_start, c.pos, base),
            })
        records.append({
            'index': index,
            'memberCount': header,
            'headerRange': _span(record_start, record_start + 1, base),
            'range': _span(record_start, c.pos, base),
            'members': fields,
        })
    members.append({
        'index': 1,
        'kind': 'counted-member-record-list',
        'encoding': encoding,
        'count': count,
        'wrapperRange': wrapper,
        'countRange': count_range,
        'records': records,
        'range': _span(list_start, c.pos, base),
    })
    # Object A: header1 + two empty counts4+4 =9.
    # Object B: header1 + bool1 + inner69 + i32(4) =75.
    # Inner69: header1 +7 string prefixes(28) +8 bools +8 scalar words(32).
    readers = [
        (2, 256, 9, 5, buff.read_skill_toggle_buff_data),
        (3, 32, 75, 1, buff.read_skill_ui_range_hint_data),
    ]
    for member_index, maximum, minimum, reserve, reader in readers:
        list_start = c.pos
        count, count_range = c.count(
            f'member[{member_index}].count', maximum, minimum, reserve
        )
        assert count is not None
        records = []
        for index in range(count):
            record_start = c.pos
            try:
                record, end = reader(data, record_start, index)
            except (ValueError, struct.error, UnicodeError) as exc:
                c.fail(
                    f'member[{member_index}].record[{index}]',
                    'complete supported anonymous nested record',
                    str(exc), record_start,
                )
            if not record_start < end <= len(data):
                c.fail(
                    'nested-record-cursor', f'{record_start + 1}..{len(data)}',
                    end, record_start,
                )
            if record.get('byteLength') != end - record_start:
                c.fail(
                    'nested-record-byte-length', end - record_start,
                    record.get('byteLength'), record_start,
                )
            c.pos = end
            records.append({
                'index': index,
                'memberCount': record['memberCount'],
                'headerRange': _span(record_start, record_start + 1, base),
                'range': _span(record_start, end, base),
                'internalFieldOwnership': 'unresolved',
            })
        members.append({
            'index': member_index,
            'kind': 'counted-nested-object-list',
            'count': count,
            'countRange': count_range,
            'records': records,
            'range': _span(list_start, c.pos, base),
        })
    final_start = c.pos
    last = c.boolean('member[4].bool')
    members.append({
        'index': 4, 'kind': 'bool', 'value': last,
        'range': _span(final_start, c.pos, base),
    })
    if c.pos != len(data):
        c.fail('terminal-eof', base + len(data), base + c.pos)
    assert members[0]['range']['start'] == base + start
    assert all(
        a['range']['end'] == b['range']['start']
        for a, b in zip(members, members[1:])
    )
    return {
        'start': base + start,
        'end': base + c.pos,
        'byteLength': c.pos - start,
        'encoding': encoding,
        'members': members,
        'exactToEof': True,
        'semanticFieldNamesStatus': 'unresolved',
        'wholeSchemaExact': False,
    }

def frame_skill_terminal_at(
    data: bytes, start: int, *, source: str, base_offset: int = 0
) -> dict[str, Any]:
    """Return all EOF candidates at one explicit start under supported grammar.

    This does not identify the runtime formatter's actual starting cursor.
    Both rejected branch diagnostics are retained when neither can consume EOF.
    """
    if type(base_offset) is not int or base_offset < 0:
        raise TerminalError([{
            'source': source, 'offset': 0, 'gate': 'base-offset',
            'expected': 'nonnegative integer (not bool)',
            'actual': repr(base_offset),
        }])
    if type(start) is not int or not 0 <= start <= len(data):
        raise TerminalError([{
            'source': source, 'offset': base_offset, 'gate': 'start-offset',
            'expected': f'integer 0..{len(data)} (not bool)',
            'actual': repr(start),
        }])
    candidates = []
    diagnostics = []
    for encoding in ('counted', 'one-member-wrapper'):
        try:
            candidates.append(
                _parse_branch(data, start, source, base_offset, encoding)
            )
        except TerminalError as exc:
            diagnostics.extend(exc.diagnostics)
    if not candidates:
        raise TerminalError(diagnostics)
    status = (
        'unique-exact-terminal-shape' if len(candidates) == 1
        else 'ambiguous-exact-terminal-shape'
    )
    return {
        'status': status, 'candidateCount': len(candidates),
        'candidates': candidates, 'branchDiagnostics': diagnostics,
        'wholeSchemaExact': False,
    }

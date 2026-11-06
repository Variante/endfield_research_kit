"""Exact current named action spans under an active source-owned operation."""
from __future__ import annotations

import hashlib
import struct

from scripts.game_data.memorypack.skill_timeline_current_sequence import (
    ATOMIC_KINDS, LIST_METHODS, PROFILE_METHODS, CurrentSequenceReader, encoded_tag, validate_program,
)
from scripts.game_data.skill_timeline_current_sequence_native import prepared_current_sequence


SCHEMA = 'endfield.current-action-receipt.v1'


def _decode_program(data, *, selected, row, source, logical_sha256, start, end, concrete=False):
    validate_program(row)
    actual = hashlib.sha256(data).hexdigest().upper()
    if actual != str(logical_sha256).upper(): raise ValueError('currentAction: logical source SHA256 differs')
    if type(start) is not int or type(end) is not int or not source or not 0 <= start < end <= len(data):
        raise ValueError('currentAction: invalid source bounds')
    reader = CurrentSequenceReader(data, source, end, operation=selected); reader.pos = start
    if not concrete:
        tag = encoded_tag(row['tag'])
        if reader.take(len(tag), 'current-union-tag') != tag:
            raise ValueError('currentAction: physical tag differs from selected wrapper')
    null = reader.peek() == 255; fields = []
    if null:
        if row['wrapperNullAdmitted'] is not True: raise ValueError('currentAction: unproved null wrapper')
        reader.take(1, 'current-null-wrapper')
    else:
        reader.header(row['memberCount'])
        for read in row['reads']:
            at = reader.pos; kind, child = read['kind'], read['childCapability']
            if kind in ATOMIC_KINDS: reader.take(ATOMIC_KINDS[kind], row['wrappedType'] + '.' + read['fieldName'])
            elif kind in PROFILE_METHODS: reader._profile(PROFILE_METHODS[kind], child, 1)
            elif kind in LIST_METHODS: reader._list(LIST_METHODS[kind], child)
            else:
                cap = selected.child(child)
                if reader.peek() == 255 and cap.get('nullAdmitted') is True:
                    reader.take(1, child + '.null')
                elif cap.get('wholeGrammarAdmitted') is True: reader._sequence(1)
                else: raise ValueError('currentAction: unproved positive child ' + str(child))
            fields.append({**read, 'start': at, 'end': reader.pos})
    if reader.pos != end: raise ValueError(f'currentAction: certified span not closed: {reader.pos} != {end}')
    return dict(schema=SCHEMA, source=source, logicalSha256=actual, start=start, end=end,
        wireForm='concrete-EffectActionData' if concrete else 'ability-action-union',
        unionTag=None if concrete else row['tag'], wrapperName=row['wrapperName'], memberCount=row['memberCount'],
        nullWrapper=null, fields=fields, childRecords=reader.records, byteRanges=reader.ranges,
        wholeActionExact=True, wholeBuffDataExact=False, runtimeExecutionProved=False)


def decode_current_action_receipt(data, *, operation, source, logical_sha256, start, end):
    selected = prepared_current_sequence(operation)
    if type(start) is not int or not 0 <= start < len(data): raise ValueError('currentAction: invalid start')
    lead = data[start]
    if lead == 250:
        if start + 3 > len(data): raise ValueError('currentAction: truncated extended tag')
        tag = struct.unpack_from('<H', data, start + 1)[0]
    else: tag = lead
    row = selected.route('AbilityActionData', tag)
    return _decode_program(data, selected=selected, row=row, source=source,
        logical_sha256=logical_sha256, start=start, end=end)


def receipts_from_root(data, *, operation, source, logical_sha256, root):
    if hashlib.sha256(data).hexdigest().upper() != str(logical_sha256).upper():
        raise ValueError('currentAction: root source SHA256 differs')
    ranges = {(r['start'], r['end']) for r in root['records'] if r.get('kind') == 'union' and r.get('tag') != 255}
    result = [decode_current_action_receipt(data, operation=operation, source=source,
        logical_sha256=logical_sha256, start=start, end=end) for start, end in sorted(ranges)]
    # StackBuffEffectData holds concrete EffectActionData records. It does not
    # store the AbilityActionData dispatcher tag in front of each element.
    from scripts.game_data.memorypack.current_effect_action_receipt import TYPE, current_program
    concrete = [r for r in root['records'] if r.get('kind') == TYPE]
    if concrete:
        _selected, program = current_program(operation)
        for record in concrete:
            fields = record['fields']; start, end = record['start'], record['end']
            if (not 0 <= start < end <= len(data) or data[start] != 20 or len(fields) != 20 or fields[0]['start'] != start + 1
                    or fields[-1]['end'] != end or any(a['end'] != b['start'] for a,b in zip(fields,fields[1:]))
                    or [r['fieldName'] for r in fields] != [r['fieldName'] for r in program['reads']]):
                raise ValueError('currentAction: concrete EffectActionData source span differs')
            replay = _decode_program(data, selected=_selected, row=program, source=source,
                logical_sha256=logical_sha256, start=start, end=end, concrete=True)
            if [{key:field[key] for key in ('fieldName','start','end')} for field in replay['fields']] != fields:
                raise ValueError('currentAction: concrete EffectActionData canonical replay differs')
            result.append(replay)
    return sorted(result,key=lambda row:(row['start'],row['end'],row['wireForm']))

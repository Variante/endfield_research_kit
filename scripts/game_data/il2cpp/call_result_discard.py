"""Check a bounded Boolean-call result discard before a loop back edge.

The program is admitted under its reviewed local entry and ordinary call
return. It authenticates instruction bytes and the callee's Boolean ABI,
then requires a complete EAX overwrite before the back edge, with no read of
the returned AL/EAX/RAX. It does not reconstruct the caller's complete CFG.
"""
from __future__ import annotations

import struct
from typing import Any


def validate_boolean_loop_discard(image: Any, section: dict[str, Any]) -> dict[str, Any]:
    caller, callee = section['caller'], section['callee']
    for method in (caller, callee): image.validate_method_row(method, label='booleanLoopDiscard')
    window = section['callerWindow']; image.check_windows([window], label='booleanLoopDiscard')
    if window['startRva'] != caller[3]:
        raise ValueError('booleanLoopDiscard.caller-entry')
    method = image.metadata.methods[callee[0]]
    pointer = image.pe.u64_at_va(int(image.registration['types'], 16) + method.return_type * 8)
    raw = image.pe.bytes_at_va(pointer, 16)
    if len(raw) != 16 or raw[10] != 2 or raw[11] & 0x7F:
        raise ValueError('booleanLoopDiscard.callee-not-plain-bool')
    rows = section['program']; slots = section['loopSlots']
    if (len(rows) != 8 or any(type(s) is not int or not 0 <= s <= 0x7FFFFFFF for s in slots.values())
            or set(slots) != {'receiver', 'source', 'index', 'count'}):
        raise ValueError('booleanLoopDiscard.profile-shape')
    def displacement(name: str) -> str:
        return struct.pack('<i', slots[name]).hex().upper()
    patterns = ['488B9424' + displacement('source'), '488B8C24' + displacement('receiver'), 'call',
                '8BBC24' + displacement('index'), 'FFC7', '89BC24' + displacement('index'),
                '8B8424' + displacement('count'), 'jump']
    image.check_instruction_windows(rows, label='booleanLoopDiscard')
    previous = rows[0][0]
    for row, pattern in zip(rows, patterns, strict=True):
        at, hex_value = row; raw = bytes.fromhex(hex_value)
        if at != previous or not window['startRva'] <= at < at + len(raw) <= window['endRva']:
            raise ValueError('booleanLoopDiscard.program-bounds-or-contiguity')
        if pattern in ('call', 'jump'):
            if len(raw) != 5 or raw[0] != (0xE8 if pattern == 'call' else 0xE9):
                raise ValueError('booleanLoopDiscard.branch-opcode')
            target = at + 5 + struct.unpack_from('<i', raw, 1)[0]
            if pattern == 'call' and target != callee[3]:
                raise ValueError('booleanLoopDiscard.callee-target')
            if pattern == 'jump' and (target != section['backEdgeTargetRva'] or not window['startRva'] <= target < rows[0][0]):
                raise ValueError('booleanLoopDiscard.local-back-edge')
        elif hex_value != pattern:
            raise ValueError('booleanLoopDiscard.result-use-or-profile-drift')
        previous = at + len(raw)
    return {'status': 'validated', 'caller': caller[1] + '.' + caller[2], 'callee': callee[1] + '.' + callee[2],
            'returnedBooleanDiscardedOnSelectedNormalProgram': True,
            'evidenceBoundary': {'direct': 'The named Boolean call returns into a contiguous local program that updates only the loop index and overwrites EAX with the loop count before its checked back edge; the returned AL/EAX/RAX is not read in that program.',
                'conditional': 'Execution enters the reviewed program and the named call returns ordinarily. The caller CFG, runtime receivers and invocation remain unproved.',
                'unresolved': 'Callee acceptance/effects and the caller overall return value; no aggregation of the callee result is inferred.'}}

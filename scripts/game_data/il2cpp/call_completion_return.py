"""Authenticate a void call followed by a constant Boolean return.

This narrow MSVC frame profile checks the full entry save/allocation program,
the named direct call, the AL assignment and direct jump, and the matching
complete return epilogue. It establishes only the selected ordinary call
completion path, never the callee's acceptance or effects.
"""
from __future__ import annotations

import struct
from typing import Any


def validate_void_call_boolean_return(image: Any, section: dict[str, Any]) -> dict[str, Any]:
    label = 'voidCallBooleanReturn'
    caller, callee = section['caller'], section['callee']
    for method in (caller, callee):
        image.validate_method_row(method, label=label)
        if len(method) != 4 or type(method[3]) is not int:
            raise ValueError(f'{label}.method-row-shape')
    for method, kind, role in ((caller, 2, 'caller-bool'), (callee, 1, 'callee-void')):
        declaration = image.metadata.methods[method[0]]
        pointer = image.pe.u64_at_va(int(image.registration['types'], 16) + declaration.return_type * 8)
        raw = image.pe.bytes_at_va(pointer, 16)
        if len(raw) != 16 or raw[10] != kind or raw[11] & 0x7F:
            raise ValueError(f'{label}.not-plain-{role}')
    window = section['callerWindow']
    image.check_windows([window], label=label)
    if window['startRva'] != caller[3]:
        raise ValueError(f'{label}.caller-entry')
    frame, returned = section['frame'], section['returnedBoolean']
    allocation, slots = frame['allocation'], frame['savedEntrySlots']
    if (type(allocation) is not int or not 16 <= allocation <= 127 or allocation % 16
            or type(returned) is not bool or set(slots) != {'rbx', 'rbp', 'rsi', 'rdi'}
            or any(type(v) is not int or not 8 <= v <= 119 or v % 8 for v in slots.values())
            or len(set(slots.values())) != 4):
        raise ValueError(f'{label}.frame-or-return-shape')
    prologue, program, epilogue = section['prologue'], section['program'], section['epilogue']
    if len(prologue) != 7 or len(program) != 3 or len(epilogue) != 8:
        raise ValueError(f'{label}.program-shape')
    for rows in (prologue, program, epilogue):
        image.check_instruction_windows(rows, label=label)
        previous = rows[0][0]
        for at, value in rows:
            raw = bytes.fromhex(value)
            if type(at) is not int or not raw or at != previous or not window['startRva'] <= at < at + len(raw) <= window['endRva']:
                raise ValueError(f'{label}.bounds-or-contiguity')
            previous = at + len(raw)
    def byte(value: int) -> str:
        return bytes([value]).hex().upper()
    registers = ('rbx', 'rbp', 'rsi', 'rdi')
    encoded = ('58', '68', '70', '78')
    expected_entry = ['488BC4', *('4889' + opcode + byte(slots[reg]) for reg, opcode in zip(registers, encoded, strict=True)), '4156', '4883EC' + byte(allocation)]
    expected_exit = ['4C8D5C24' + byte(allocation), *('498B' + opcode + byte(slots[reg] + 8) for reg, opcode in zip(registers, ('5B', '6B', '73', '7B'), strict=True)), '498BE3', '415E', 'C3']
    if [r[1] for r in prologue] != expected_entry or [r[1] for r in epilogue] != expected_exit:
        raise ValueError(f'{label}.frame-restore-or-result-use-drift')
    if (prologue[0][0] != caller[3]
            or prologue[-1][0] + len(bytes.fromhex(prologue[-1][1])) > program[0][0]
            or program[-1][0] + len(bytes.fromhex(program[-1][1])) > epilogue[0][0]
            or epilogue[-1][0] + 1 != window['endRva']):
        raise ValueError(f'{label}.entry-program-exit-order')
    call_at, call_hex = program[0]; call = bytes.fromhex(call_hex)
    if len(call) != 5 or call[0] != 0xE8 or call_at + 5 + struct.unpack_from('<i', call, 1)[0] != callee[3]:
        raise ValueError(f'{label}.callee-target')
    if program[1][1] != 'B0' + byte(int(returned)):
        raise ValueError(f'{label}.constant-al-assignment')
    jump_at, jump_hex = program[2]; jump = bytes.fromhex(jump_hex)
    if len(jump) == 2 and jump[0] == 0xEB:
        target = jump_at + 2 + int.from_bytes(jump[1:], 'little', signed=True)
    elif len(jump) == 5 and jump[0] == 0xE9:
        target = jump_at + 5 + struct.unpack_from('<i', jump, 1)[0]
    else:
        raise ValueError(f'{label}.direct-exit-jump')
    if target != epilogue[0][0] or target <= jump_at:
        raise ValueError(f'{label}.complete-local-exit-target')
    return {'status': 'validated', 'caller': caller[1] + '.' + caller[2], 'callee': callee[1] + '.' + callee[2],
            'calleeReturnsVoid': True, 'callerBooleanOnSelectedOrdinaryCompletion': returned,
            'evidenceBoundary': {
                'direct': 'The named void call is immediately followed by a constant AL assignment and checked direct jump through the matching complete frame restore to RET; the Boolean is preserved.',
                'conditional': 'The compiled local program is entered with the authenticated caller frame and the named call returns ordinarily. Other exits, IFix selection and branch feasibility are separate.',
                'unresolved': 'Callee acceptance, effects and runtime invocation. The constant caller Boolean carries no callee success result.'}}

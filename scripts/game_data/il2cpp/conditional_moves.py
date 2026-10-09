"""Decode complete x64 CMOVcc instructions without inventing branch edges.

The write remains conditional. A consumer must account for the previous
destination and the flags; it cannot treat the source as an unconditional alias.
Other instructions use the selected image's existing decoder.
"""
from __future__ import annotations

from typing import Any

_CONDITIONS = ('o', 'no', 'b', 'ae', 'e', 'ne', 'be', 'a',
               's', 'ns', 'p', 'np', 'l', 'ge', 'le', 'g')
_REGISTERS = ('rax', 'rcx', 'rdx', 'rbx', 'rsp', 'rbp', 'rsi', 'rdi',
              'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15')
_REGISTERS32 = ('eax', 'ecx', 'edx', 'ebx', 'esp', 'ebp', 'esi', 'edi',
                'r8d', 'r9d', 'r10d', 'r11d', 'r12d', 'r13d', 'r14d', 'r15d')


def decode_conditional_move(data: bytes, offset: int, start_va: int) -> tuple[dict, int] | None:
    """Recognize the 32/64-bit, optional single REX, 0F 40..4F grammar.

    Unsupported prefixes return None. A recognized but truncated instruction
    fails closed rather than splitting into apparently valid other operations.
    """
    at = offset
    if not 0 <= at < len(data):
        return None
    rex = 0
    if 0x40 <= data[at] <= 0x4f:
        rex = data[at]; at += 1
    if data[at:at + 1] != b'\x0f' or at + 1 >= len(data) or not 0x40 <= data[at + 1] <= 0x4f:
        return None
    condition = _CONDITIONS[data[at + 1] - 0x40]; at += 2

    def take(size: int) -> bytes:
        nonlocal at
        if at + size > len(data):
            raise ValueError(f'x64.cmov.truncated: offset={offset} requiredEnd={at + size} bytes={len(data)}')
        value = data[at:at + size]; at += size
        return value

    modrm = take(1)[0]; mod, reg, rm = modrm >> 6, (modrm >> 3) & 7, modrm & 7
    width = 64 if rex & 8 else 32
    names = _REGISTERS if width == 64 else _REGISTERS32
    destination = names[reg | ((rex & 4) << 1)]
    if mod == 3:
        source = names[rm | ((rex & 1) << 3)]
    else:
        displacement = 0; parts = []; rip = False
        if rm == 4:
            sib = take(1)[0]; scale, index, base = sib >> 6, (sib >> 3) & 7, sib & 7
            if mod == 0 and base == 5:
                displacement = int.from_bytes(take(4), 'little', signed=True)
            else:
                parts.append(_REGISTERS[base | ((rex & 1) << 3)])
            if index != 4 or rex & 2:
                parts.append(f'{_REGISTERS[index | ((rex & 2) << 2)]}*{1 << scale}')
        elif mod == 0 and rm == 5:
            rip = True; displacement = int.from_bytes(take(4), 'little', signed=True)
        else:
            parts.append(_REGISTERS[rm | ((rex & 1) << 3)])
        if mod in (1, 2):
            displacement = int.from_bytes(take(1 if mod == 1 else 4), 'little', signed=True)
        suffix = ('-0x' + format(-displacement, 'x')) if displacement < 0 else ('+0x' + format(displacement, 'x'))
        if rip:
            source = f'[rip{suffix} => 0x{start_va + at + displacement:x}]'
        elif parts:
            source = '[' + '+'.join(parts) + (suffix if displacement else '') + ']'
        else:
            source = f'[0x{displacement & 0xffffffffffffffff:x}]'
    return {'offset': offset, 'va': hex(start_va + offset),
        'bytes': data[offset:at].hex(' '), 'text': f'cmov{condition} {destination}, {source}',
        'write': {'register': destination, 'value': f'conditional({condition}, {source}, previous({destination}))'},
        'conditionalMove': {'condition': condition, 'destination': destination,
                            'source': source, 'width': width}}, at


def decode_with_conditional_moves(mapper: Any, data: bytes, start_va: int) -> list[dict]:
    rows = []; offset = 0
    while offset < len(data):
        decoded = decode_conditional_move(data, offset, start_va)
        if decoded is None:
            decoded = mapper.decode_one_x64(data, offset, start_va)
        row, stop = decoded
        if not offset < stop <= len(data) or bytes.fromhex(row['bytes']) != data[offset:stop]:
            raise ValueError(f'x64.inventory-span: offset={offset} stop={stop} bytes={len(data)}')
        rows.append(row); offset = stop
    return rows

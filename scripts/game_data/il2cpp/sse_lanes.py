"""Decode complete selected register lane and Single arithmetic operations.

These register forms select lanes without changing the stack or control flow.
The immediate byte belongs to SHUFPS, even when it resembles a PUSH opcode.
Other forms remain outside this subset and cannot establish a program proof.
"""
from __future__ import annotations
from typing import Any
from .wide_immediates import decode_wide_immediate
from .conditional_moves import decode_conditional_move


def decode_sse_lanes(data: bytes, offset: int, start_va: int) -> tuple[dict, int] | None:
    if not 0 <= offset < len(data):
        return None
    at = offset; rex = 0
    if 0x40 <= data[at] <= 0x4f:
        rex = data[at]; at += 1
    if data[at:at+2] not in (b'\x0f\xc6', b'\x0f\x14'):
        return None
    opcode = data[at+1]; at += 2
    if at >= len(data):
        raise ValueError(f'x64.sse-lanes.truncated: offset={offset} requiredEnd={at+1} bytes={len(data)}')
    modrm = data[at]; at += 1
    if modrm >> 6 != 3:
        return None
    destination = f'xmm{((modrm >> 3) & 7) | ((rex & 4) << 1)}'
    source = f'xmm{(modrm & 7) | ((rex & 1) << 3)}'
    if opcode == 0xc6:
        if at >= len(data):
            raise ValueError(f'x64.sse-lanes.truncated: offset={offset} requiredEnd={at+1} bytes={len(data)}')
        immediate = data[at]; at += 1
        lanes = [f'previous({destination})[{immediate & 3}]',
                 f'previous({destination})[{(immediate >> 2) & 3}]',
                 f'{source}[{(immediate >> 4) & 3}]',
                 f'{source}[{(immediate >> 6) & 3}]']
        text = f'shufps {destination}, {source}, {hex(immediate)}'
        operation = 'shufps'
    else:
        lanes = [f'previous({destination})[0]', f'{source}[0]',
                 f'previous({destination})[1]', f'{source}[1]']
        text = f'unpcklps {destination}, {source}'
        operation = 'unpcklps'
    return {'offset':offset, 'va':hex(start_va+offset),
        'bytes':data[offset:at].hex(' '), 'text':text,
        'write':{'register':destination, 'value':'lanes(' + ', '.join(lanes) + ')'},
        'laneOperation':{'operation':operation, 'destination':destination,
                         'source':source, 'resultLanes':lanes}}, at


def decode_sse_numeric(data: bytes, offset: int, start_va: int) -> tuple[dict,int] | None:
    """Register CVTDQ2PS and scalar DIVSS; unsupported memory forms stay open."""
    if not 0 <= offset < len(data): return None
    at = offset; scalar = data[at] == 0xf3
    if scalar: at += 1
    rex = 0
    if at < len(data) and 0x40 <= data[at] <= 0x4f:
        rex = data[at]; at += 1
    opcode = b'\x0f\x5e' if scalar else b'\x0f\x5b'
    if data[at:at+2] != opcode: return None
    at += 2
    if at >= len(data):
        raise ValueError(f'x64.sse-numeric.truncated: offset={offset} requiredEnd={at+1} bytes={len(data)}')
    modrm = data[at]; at += 1
    if modrm >> 6 != 3: return None
    destination = f'xmm{((modrm >> 3)&7)|((rex&4)<<1)}'
    source = f'xmm{(modrm&7)|((rex&1)<<3)}'
    operation = 'divss' if scalar else 'cvtdq2ps'
    value = (f'float32_div(previous({destination})[0], {source}[0]); preserve upper destination lanes'
        if scalar else f'four_lanes(int32_to_float32({source}))')
    return {'offset':offset,'va':hex(start_va+offset),'bytes':data[offset:at].hex(' '),
        'text':f'{operation} {destination}, {source}',
        'write':{'register':destination,'value':value},
        'numericOperation':{'operation':operation,'destination':destination,'source':source,
            'scalarSingle':scalar,'preservesUpperDestinationLanes':scalar}},at


def decode_lane_transfer_instructions(mapper: Any, data: bytes, start_va: int) -> list[dict]:
    rows = []; offset = 0
    while offset < len(data):
        result = decode_sse_lanes(data, offset, start_va)
        if result is None: result = decode_sse_numeric(data, offset, start_va)
        if result is None: result = decode_wide_immediate(data, offset, start_va)
        if result is None: result = decode_conditional_move(data, offset, start_va)
        if result is None: result = mapper.decode_one_x64(data, offset, start_va)
        row, stop = result
        if not isinstance(row.get('bytes'),str):
            raise ValueError(f'x64.lane-transfer-inventory-missing-byte-span: offset={offset} row={row}')
        if not offset < stop <= len(data) or bytes.fromhex(row['bytes']) != data[offset:stop]:
            raise ValueError(f'x64.lane-transfer-inventory-span: offset={offset} stop={stop} bytes={len(data)}')
        rows.append(row); offset = stop
    return rows

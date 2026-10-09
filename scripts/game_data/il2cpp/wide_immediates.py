"""Complete x64 register-immediate moves used in selected native transfer scans.

REX.W B8..BF carries eight immediate bytes. Splitting that value creates
invented subsequent instructions and invalidates register/branch analysis.
"""
from __future__ import annotations
from typing import Any
from .conditional_moves import decode_conditional_move

_REGISTERS=('rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi',
            'r8','r9','r10','r11','r12','r13','r14','r15')


def decode_wide_immediate(data: bytes, offset: int, start_va: int) -> tuple[dict,int] | None:
    if not 0<=offset<len(data) or not 0x48<=data[offset]<=0x4f:
        return None
    if offset+1>=len(data) or not 0xb8<=data[offset+1]<=0xbf:
        return None
    stop=offset+10
    if stop>len(data):
        raise ValueError(f'x64.mov-imm64.truncated: offset={offset} requiredEnd={stop} bytes={len(data)}')
    register=_REGISTERS[data[offset+1]-0xb8+((data[offset]&1)<<3)]
    immediate=int.from_bytes(data[offset+2:stop],'little')
    value=hex(immediate)
    return {'offset':offset,'va':hex(start_va+offset),'bytes':data[offset:stop].hex(' '),
        'text':f'mov {register}, {value}','write':{'register':register,'value':value},
        'immediateWidth':64},stop


def decode_transfer_instructions(mapper: Any, data: bytes, start_va: int) -> list[dict]:
    rows=[];offset=0
    while offset<len(data):
        result=decode_wide_immediate(data,offset,start_va)
        if result is None:result=decode_conditional_move(data,offset,start_va)
        if result is None:result=mapper.decode_one_x64(data,offset,start_va)
        row,stop=result
        if not offset<stop<=len(data) or bytes.fromhex(row['bytes'])!=data[offset:stop]:
            raise ValueError(f'x64.transfer-inventory-span: offset={offset} stop={stop} bytes={len(data)}')
        rows.append(row);offset=stop
    return rows

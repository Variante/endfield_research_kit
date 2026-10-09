"""Authenticate a complete integer memory read by CMP, without a value result.

The caller separately proves the base register's receiver/data ownership and
the selected field's width. Unsupported addressing/prefixes remain unproved.
This helper does not establish flags, branch selection or a forwarded value.
"""
from __future__ import annotations
from typing import Any

REGISTERS = ('rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi',*(f'r{n}' for n in range(8,16)))
DWORD_REGISTERS = ('eax','ecx','edx','ebx','esp','ebp','esi','edi',*(f'r{n}d' for n in range(8,16)))


def reads_cmp_memory_field(row: dict[str, Any], *, base: str, offset: int, width: int) -> bool:
    if width not in (8,32) or base not in REGISTERS or type(offset) is not int or offset<0:
        return False
    try:raw=bytes.fromhex(str(row.get('bytes') or ''))
    except ValueError:return False
    rex=raw[0] if raw and 0x40<=raw[0]<=0x4f else 0
    if rex:raw=raw[1:]
    if len(raw)<3 or rex&8:return False
    opcode,modrm=raw[:2];mode=modrm>>6;rm=modrm&7;reg=(modrm>>3)&7
    if mode not in (1,2) or rm==4 or REGISTERS[rm+(8 if rex&1 else 0)]!=base:return False
    displacement_bytes=1 if mode==1 else 4
    immediate_bytes=1 if opcode in (0x80,0x83) else 4 if opcode==0x81 else 0
    if len(raw)!=2+displacement_bytes+immediate_bytes:return False
    if int.from_bytes(raw[2:2+displacement_bytes],'little',signed=True)!=offset:return False
    memory=f'[{base}+0x{offset:x}]'
    if opcode in (0x38,0x3a,0x39,0x3b):
        if width!=(8 if opcode in (0x38,0x3a) else 32):return False
        register_code=reg+(8 if rex&4 else 0)
        byte_registers=('al','cl','dl','bl',*(('spl','bpl','sil','dil') if rex else ('ah','ch','dh','bh')),
            *(f'r{n}b' for n in range(8,16)))
        register=(byte_registers if width==8 else DWORD_REGISTERS)[register_code]
        operands=(memory,register) if opcode in (0x38,0x39) else (register,memory)
    elif opcode in (0x80,0x81,0x83) and reg==7:
        if width!=(8 if opcode==0x80 else 32):return False
        value=int.from_bytes(raw[-immediate_bytes:],'little',signed=opcode!=0x80)
        immediate=f'-0x{-value:x}' if value<0 else f'0x{value:x}'
        operands=(memory,immediate)
    else:return False
    return row.get('write') is None and row.get('text')==f'cmp {operands[0]}, {operands[1]}'

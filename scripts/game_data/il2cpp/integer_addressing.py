"""Decode selected integer/address forms with their original x64 byte spans.

REX.X extends the SIB index independently of REX.B's base extension. LEA's
destination width does not change its 64-bit address-input registers. This
subset supplies arithmetic/address facts, never array-class field meanings.
"""
from __future__ import annotations
from typing import Any
from .integer_registers import decode_integer_register_instructions, decode_register_add

_REG64 = ('rax', 'rcx', 'rdx', 'rbx', 'rsp', 'rbp', 'rsi', 'rdi')
_REG32 = ('eax', 'ecx', 'edx', 'ebx', 'esp', 'ebp', 'esi', 'edi')


def _reg(number: int, bits: int = 64) -> str:
    return (_REG64 if bits == 64 else _REG32)[number] if number < 8 else f'r{number}' + ('' if bits == 64 else 'd')


def _required(data: bytes, at: int, size: int, offset: int, label: str) -> bytes:
    if at + size > len(data):
        raise ValueError(f'x64.{label}.truncated: offset={offset} requiredEnd={at+size} bytes={len(data)}')
    return data[at:at+size]


def _prefix(data: bytes, offset: int) -> tuple[int, int]:
    at = offset; rex = 0
    if at < len(data) and 0x40 <= data[at] <= 0x4f:
        rex = data[at]; at += 1
    return at, rex


def decode_register_arithmetic(data: bytes, offset: int, start_va: int) -> tuple[dict, int] | None:
    if not 0 <= offset < len(data): return None
    at, rex = _prefix(data, offset)
    operation = 'imul' if data[at:at+2] == b'\x0f\xaf' else {0x03: 'add', 0x2b: 'sub'}.get(data[at] if at < len(data) else -1)
    if operation is None: return None
    if operation == 'add' and not rex & 8:
        return decode_register_add(data, offset, start_va)
    at += 2 if operation == 'imul' else 1
    modrm = _required(data, at, 1, offset, 'integer-register-arithmetic')[0]; at += 1
    if modrm >> 6 != 3: return None
    bits = 64 if rex & 8 else 32
    destination = _reg(((modrm >> 3) & 7) | ((rex & 4) << 1), bits)
    source = _reg((modrm & 7) | ((rex & 1) << 3), bits)
    return {'offset': offset, 'va': hex(start_va + offset), 'bytes': data[offset:at].hex(' '),
        'text': f'{operation} {destination}, {source}',
        'write': {'register': destination, 'value': f'{bits}-bit {operation} modulo 2^{bits}; ' + ('zero upper 32 bits' if bits == 32 else 'full register')},
        'integerOperation': {'operation': operation, 'destination': destination, 'source': source,
            'bits': bits, 'wrapsModulo': 1 << bits, 'zeroExtendsTo64': bits == 32,
            'flags': 'CF/OF indicate signed overflow; other arithmetic flags undefined' if operation == 'imul' else 'arithmetic flags updated'}}, at


def _address(data: bytes, at: int, modrm: int, rex: int, offset: int, label: str) -> tuple[dict, int]:
    mod = modrm >> 6; rm = modrm & 7
    base = None; index = None; scale = 1; rip = False; displacement = 0
    if mod == 3: raise ValueError(f'x64.{label}.register-instead-of-address: offset={offset}')
    if rm == 4:
        sib = _required(data, at, 1, offset, label)[0]; at += 1
        scale = 1 << (sib >> 6)
        index_low = (sib >> 3) & 7
        if index_low != 4 or rex & 2:
            index = _reg(index_low | ((rex & 2) << 2))
        base_low = sib & 7
        if not (mod == 0 and base_low == 5):
            base = _reg(base_low | ((rex & 1) << 3))
        else:
            displacement = int.from_bytes(_required(data, at, 4, offset, label), 'little', signed=True); at += 4
    elif mod == 0 and rm == 5:
        rip = True
        displacement = int.from_bytes(_required(data, at, 4, offset, label), 'little', signed=True); at += 4
    else:
        base = _reg(rm | ((rex & 1) << 3))
    if mod in (1, 2):
        size = 1 if mod == 1 else 4
        displacement = int.from_bytes(_required(data, at, size, offset, label), 'little', signed=True); at += size
    return {'base': base, 'index': index, 'scale': scale, 'displacement': displacement,
        'ripRelative': rip, 'addressBits': 64}, at


def decode_lea_address(data: bytes, offset: int, start_va: int) -> tuple[dict, int] | None:
    if not 0 <= offset < len(data): return None
    at, rex = _prefix(data, offset)
    if data[at:at+1] != b'\x8d': return None
    at += 1; modrm = _required(data, at, 1, offset, 'lea-address')[0]; at += 1
    if modrm >> 6 == 3: return None
    address, at = _address(data, at, modrm, rex, offset, 'lea-address')
    bits = 64 if rex & 8 else 32
    destination = _reg(((modrm >> 3) & 7) | ((rex & 4) << 1), bits)
    if address['ripRelative']:
        target = start_va + at + address['displacement']
        address['ripBase'] = start_va + at; address['absoluteAddress'] = target
        term = f"rip{'+' if address['displacement'] >= 0 else '-'}0x{abs(address['displacement']):x} => 0x{target:x}"
    else:
        term = address['base'] or ''
        if address['index'] is not None:
            term += ('+' if term else '') + f"{address['index']}*{address['scale']}"
        displacement = address['displacement']
        if displacement or not term:
            term += ('+' if term and displacement >= 0 else '-' if displacement < 0 else '') + f'0x{abs(displacement):x}'
    return {'offset': offset, 'va': hex(start_va + offset), 'bytes': data[offset:at].hex(' '),
        'text': f'lea {destination}, [{term}]',
        'write': {'register': destination, 'value': f'address modulo 2^{bits}; no memory read'},
        'addressOperation': {'destination': destination, 'destinationBits': bits,
            'zeroExtendsTo64': bits == 32, 'writesFlags': False, 'readsMemory': False, **address}}, at


def decode_multibyte_nop(data: bytes, offset: int, start_va: int) -> tuple[dict, int] | None:
    if not 0 <= offset < len(data): return None
    at = offset; prefixes = 0
    while data[at:at+1] == b'\x66' and prefixes < 3:
        at += 1; prefixes += 1
    at, rex = _prefix(data, at)
    if data[at:at+2] != b'\x0f\x1f': return None
    at += 2; modrm = _required(data, at, 1, offset, 'multibyte-nop')[0]; at += 1
    if (modrm >> 3) & 7: return None
    if modrm >> 6 != 3:
        _, at = _address(data, at, modrm, rex, offset, 'multibyte-nop')
    return {'offset': offset, 'va': hex(start_va + offset), 'bytes': data[offset:at].hex(' '),
        'text': 'nop', 'write': None, 'paddingOperation': {'readsMemory': False, 'writesFlags': False}}, at


def decode_address_integer_instructions(mapper: Any, data: bytes, start_va: int) -> list[dict]:
    class Fallback:
        def decode_one_x64(self, raw, offset, at):
            for decoder in (decode_register_arithmetic, decode_lea_address, decode_multibyte_nop):
                result = decoder(raw, offset, at)
                if result is not None: return result
            return mapper.decode_one_x64(raw, offset, at)
    return decode_integer_register_instructions(Fallback(), data, start_va)

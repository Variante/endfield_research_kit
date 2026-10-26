"""Selected 66 C7 /0 iw stores with exact instruction-end addressing.

The optional decoder leaves existing instruction readers unchanged. Register
destinations, REX.W overrides and unsupported opcode extensions are excluded.
Register-to-WORD stores are already handled by ``memory_moves``.
"""
from __future__ import annotations

from .integer_addressing import _address, _prefix, _required
from .integer_tag_dispatch import _memory_text, _row
from .enum_underlying_instructions import decode_enum_underlying_instructions


def decode_word_immediate_store(data: bytes, offset: int, start_va: int):
    if not 0 <= offset < len(data) or data[offset] != 0x66:
        return None
    at, rex = _prefix(data, offset + 1)
    if data[at:at + 1] != b'\xc7':
        return None
    if rex & 12:
        raise ValueError(f'x64.word-immediate-store.unsupported-rex: offset={offset} rex={hex(rex)}')
    at += 1
    modrm = _required(data, at, 1, offset, 'word-immediate-store')[0]
    at += 1
    if modrm >> 6 == 3 or (modrm >> 3) & 7:
        raise ValueError(f'x64.word-immediate-store.unsupported-operand: offset={offset} modrm={hex(modrm)}')
    address, at = _address(data, at, modrm, rex, offset, 'word-immediate-store')
    encoded = _required(data, at, 2, offset, 'word-immediate-store')
    at += 2
    signed = int.from_bytes(encoded, 'little', signed=True)
    operand = _memory_text(address, at, start_va, 16)
    return _row(data, offset, at, start_va, f'mov {operand}, {hex(signed)}', write=None,
        immediateMemoryStoreOperation={
            'bits': 16, 'destinationAddress': address, 'memoryWriteBytes': 2,
            'memoryReadBytes': 0, 'encodedImmediateBits': 16,
            'immediateSignedValue': signed,
            'immediateWord': int.from_bytes(encoded, 'little'),
            'signExtendsImmediateTo64': False, 'writesFlags': False,
            'preservesRegisters': True})


def decode_word_store_instructions(mapper, data: bytes, start_va: int):
    class Fallback:
        def decode_one_x64(self, raw, offset, at):
            row = decode_word_immediate_store(raw, offset, at)
            return row if row is not None else mapper.decode_one_x64(raw, offset, at)
    return decode_enum_underlying_instructions(Fallback(), data, start_va)

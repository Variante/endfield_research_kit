"""Optional immediate logical right shifts of one GP byte register.

The imm8 count is masked to five bits. The selected byte write preserves
other parent bits, including high-byte/REX distinctions. This reader does
not infer flags, memory-field meanings, or runtime CPU execution.
"""
from __future__ import annotations
from .integer_addressing import _prefix, _required
from .integer_byte_operations import _destination
from .integer_tag_dispatch import _row
from .initializer_instructions import decode_initializer_instructions


def decode_byte_register_shift(data, offset, start_va):
    if not 0 <= offset < len(data): return None
    at, rex = _prefix(data, offset)
    if rex & 4 or data[at:at+1] != b'\xc0': return None
    at += 1; modrm = _required(data, at, 1, offset, 'byte-register-shift')[0]; at += 1
    if modrm >> 6 != 3 or (modrm >> 3) & 7 != 5: return None
    count = _required(data, at, 1, offset, 'byte-register-shift')[0]; at += 1
    fact = _destination((modrm & 7) | ((rex & 1) << 3), rex)
    fact.update(operation='shr', encodedCount=count, effectiveCount=count & 31,
                countMask=31, logicalZeroFill=True, flagsProved=False)
    return _row(data, offset, at, start_va,
                f'shr {fact["destinationRegister"]}, {hex(count)}', byteRegisterShiftOperation=fact)


def decode_byte_shift_instructions(mapper, data, start_va):
    class Fallback:
        def decode_one_x64(self, raw, offset, at):
            result = decode_byte_register_shift(raw, offset, at)
            return result if result is not None else mapper.decode_one_x64(raw, offset, at)
    return decode_initializer_instructions(Fallback(), data, start_va)

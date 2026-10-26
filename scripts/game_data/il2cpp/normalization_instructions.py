"""Optional GS-based loads and partial WORD masks in normalization frames.

GS addressing reads a runtime segment base, not an absolute image address.
WORD logical operations preserve the other 48 bits of the general register.
Unsupported forms and prefixes remain outside this decoder lane.
"""
from __future__ import annotations

from .integer_addressing import _address, _prefix, _reg, _required
from .integer_tag_dispatch import _row
from .memory_moves import _register
from .method_carrier_instructions import decode_method_carrier_instructions


def decode_gs_absolute_load(data, offset, start_va):
    if not 0 <= offset < len(data) or data[offset] != 0x65:
        return None
    at, rex = _prefix(data, offset+1)
    if data[at:at+1] != b'\x8b' or rex & 2:
        return None
    at += 1
    modrm = _required(data, at, 1, offset, 'normalization-gs-load')[0]
    at += 1
    if modrm >> 6 or modrm & 7 != 4:
        return None
    sib = _required(data, at, 1, offset, 'normalization-gs-load')[0]
    if sib != 0x25:
        return None
    address, at = _address(data, at, modrm, rex, offset, 'normalization-gs-load')
    if address['base'] is not None or address['index'] is not None or address['ripRelative']:
        return None
    address.update(segment='gs', segmentBaseRuntime=True)
    bits = 64 if rex & 8 else 32
    register = _reg(((modrm >> 3) & 7) | ((rex & 4) << 1), bits)
    return _row(data, offset, at, start_va, f'mov {register}, gs:[{hex(address["displacement"])}]',
        write={'register': register, 'value': 'loaded from runtime GS base plus signed disp32'},
        segmentMemoryLoadOperation={'register': register, 'registerBits': bits,
            'memoryReadBytes': bits//8, 'memoryWriteBytes': 0, 'sourceAddress': address,
            'zeroExtendsTo64': bits == 32, 'writesFlags': False})


def decode_word_register_and(data, offset, start_va):
    if not 0 <= offset < len(data) or data[offset] != 0x66:
        return None
    at, rex = _prefix(data, offset+1)
    if rex & 12 or data[at:at+1] != b'\x81':
        return None
    at += 1
    modrm = _required(data, at, 1, offset, 'normalization-word-and')[0]
    at += 1
    if modrm >> 6 != 3 or (modrm >> 3) & 7 != 4:
        return None
    word = int.from_bytes(_required(data, at, 2, offset, 'normalization-word-and'), 'little')
    at += 2
    number = (modrm & 7) | ((rex & 1) << 3)
    register, parent, _ = _register(number, 16, True)
    return _row(data, offset, at, start_va, f'and {register}, {hex(word)}',
        write={'register': register, 'value': 'previous low WORD AND immediate; upper 48 bits preserved'},
        wordRegisterLogicalOperation={'operation': 'and', 'register': register, 'parentRegister': parent,
            'bits': 16, 'immediateWord': word, 'preservesBits16Through63': True,
            'zeroExtendsTo64': False, 'memoryReadBytes': 0, 'memoryWriteBytes': 0,
            'clearsFlags': ['CF', 'OF'], 'resultFlags': ['SF', 'ZF', 'PF'], 'undefinedFlags': ['AF']})


def decode_normalization_instructions(mapper, data, start_va):
    class Fallback:
        def decode_one_x64(self, raw, offset, at):
            for decoder in (decode_gs_absolute_load, decode_word_register_and):
                result = decoder(raw, offset, at)
                if result is not None:
                    return result
            return mapper.decode_one_x64(raw, offset, at)
    return decode_method_carrier_instructions(Fallback(), data, start_va)

"""Optional exact byte XOR and legacy SSE lane forms in carrier resolution.

These instruction facts preserve whole encodings, transfer widths and partial
register effects. They establish no MethodInfo layout, code selection or cache
visibility. Unsupported prefixes and opcode groups remain outside this lane.
"""
from __future__ import annotations

from .generic_creation_instructions import decode_generic_creation_instructions
from .integer_addressing import _address, _prefix, _reg, _required
from .integer_tag_dispatch import _row
from .integer_widths import _byte
from .memory_moves import _finish_address


def decode_memory_byte_xor(data, offset, start_va):
    if not 0 <= offset < len(data):
        return None
    at, rex = _prefix(data, offset)
    if data[at:at+1] != b'\x30':
        return None
    at += 1
    modrm = _required(data, at, 1, offset, 'carrier-byte-memory-xor')[0]
    at += 1
    if modrm >> 6 == 3:
        return None
    source = _byte(((modrm >> 3) & 7) | ((rex & 4) << 1), rex)
    address, at = _address(data, at, modrm, rex, offset, 'carrier-byte-memory-xor')
    operand = _finish_address(address, at, start_va)
    return _row(data, offset, at, start_va, f'xor byte [{operand}], {source}', write=None,
        byteMemoryLogicalOperation={'operation': 'xor', 'bits': 8,
            'sourceRegister': source, 'destinationAddress': address,
            'memoryReadBytes': 1, 'memoryWriteBytes': 1, 'preservesRegisters': True,
            'clearsFlags': ['CF', 'OF'], 'undefinedFlags': ['AF'],
            'writesResultFlags': ['SF', 'ZF', 'PF']})


def decode_register_immediate_dword(data, offset, start_va):
    if not 0 <= offset < len(data):
        return None
    at, rex = _prefix(data, offset)
    if rex & 4 or data[at:at+1] != b'\xc7':
        return None
    at += 1
    modrm = _required(data, at, 1, offset, 'carrier-register-immediate')[0]
    at += 1
    if modrm >> 6 != 3 or (modrm >> 3) & 7:
        return None
    encoded = _required(data, at, 4, offset, 'carrier-register-immediate')
    at += 4
    bits = 64 if rex & 8 else 32
    signed = int.from_bytes(encoded, 'little', signed=True)
    word = signed & ((1 << bits)-1)
    destination = _reg((modrm & 7) | ((rex & 1) << 3), bits)
    value = signed if bits == 64 else word
    return _row(data, offset, at, start_va, f'mov {destination}, {hex(value)}',
        write={'register': destination, 'value': hex(word)},
        immediateRegisterOperation={'register': destination, 'bits': bits,
            'encodedImmediateBits': 32, 'immediateWord': word,
            'signExtendsImmediateTo64': bits == 64, 'zeroExtendsTo64': bits == 32,
            'memoryReadBytes': 0, 'memoryWriteBytes': 0, 'writesFlags': False})


def decode_carrier_vector_transfer(data, offset, start_va):
    if not 0 <= offset < len(data) or data[offset] not in (0x66, 0xf3):
        return None
    prefix = data[offset]
    at, rex = _prefix(data, offset+1)
    opcode = data[at:at+2]
    if prefix == 0xf3 and opcode != b'\x0f\x7e' or prefix == 0x66 and opcode not in (b'\x0f\x7e', b'\x0f\xd6'):
        return None
    at += 2
    modrm = _required(data, at, 1, offset, 'carrier-vector-transfer')[0]
    at += 1
    source_vector = f'xmm{((modrm >> 3) & 7) | ((rex & 4) << 1)}'
    rm = (modrm & 7) | ((rex & 1) << 3)
    vector_destination = prefix == 0xf3
    gp_destination = prefix == 0x66 and opcode == b'\x0f\x7e'
    bits = 64 if not gp_destination or rex & 8 else 32
    mnemonic = 'movq' if bits == 64 else 'movd'
    if modrm >> 6 == 3:
        if gp_destination:
            destination = _reg(rm, bits)
            source = source_vector
            effect = 'zero upper 32 GP bits' if bits == 32 else 'replace full GP register'
        else:
            destination, source = (source_vector, f'xmm{rm}') if vector_destination else (f'xmm{rm}', source_vector)
            effect = 'zero bits 64 through 127; preserve bits above 127'
        return _row(data, offset, at, start_va, f'{mnemonic} {destination}, {source}',
            write={'register': destination, 'value': f'source low {bits} bits; {effect}'},
            vectorLaneTransferOperation={'sourceRegister': source, 'sourceLowBits': bits,
                'destinationRegister': destination, 'destinationIsGeneralRegister': gp_destination,
                'zeroExtendsGp32To64': gp_destination and bits == 32,
                'zeroBitsThrough127From': None if gp_destination else 64,
                'preservesSourceBitsUnlessAliased': True, 'preservesVectorBitsAbove127': True,
                'rexWSelectsGpWidth': gp_destination, 'memoryReadBytes': 0,
                'memoryWriteBytes': 0, 'writesFlags': False})
    address, at = _address(data, at, modrm, rex, offset, 'carrier-vector-transfer')
    operand = _finish_address(address, at, start_va)
    text = f'{mnemonic} {source_vector}, [{operand}]' if vector_destination else f'{mnemonic} [{operand}], {source_vector}'
    return _row(data, offset, at, start_va, text,
        write={'register': source_vector, 'value': 'memory low64; zero bits64..127'} if vector_destination else None,
        memoryOperation={'direction': 'load' if vector_destination else 'store',
            'register': source_vector, 'backingRegister': 'vector'+source_vector[3:],
            'registerBits': 128, 'registerBitOffset': 0, 'memoryBytes': bits//8,
            'address': address, 'valueExtension': None,
            'upperRegisterEffect': 'zero bits64..127; preserve bits above127' if vector_destination else 'preserved',
            'requiredAlignmentBytes': 1, 'nonTemporalHint': False, 'writesFlags': False,
            'rexWSelectsTransferWidth': gp_destination})


def decode_carrier_vector_byte_shift(data, offset, start_va):
    if not 0 <= offset < len(data) or data[offset] != 0x66:
        return None
    at, rex = _prefix(data, offset+1)
    if rex & 4 or data[at:at+2] != b'\x0f\x73':
        return None
    at += 2
    modrm = _required(data, at, 1, offset, 'carrier-vector-byte-shift')[0]
    at += 1
    if modrm >> 6 != 3 or (modrm >> 3) & 7 != 3:
        return None
    count = _required(data, at, 1, offset, 'carrier-vector-byte-shift')[0]
    at += 1
    destination = f'xmm{(modrm & 7) | ((rex & 1) << 3)}'
    return _row(data, offset, at, start_va, f'psrldq {destination}, {hex(count)}',
        write={'register': destination, 'value': f'logical shift of low128 bits right by {min(count, 16)*8} bits'},
        vectorByteShiftOperation={'register': destination, 'vectorBits': 128,
            'encodedByteCount': count, 'effectiveByteCount': min(count, 16),
            'clearsLow128Bits': count >= 16, 'zeroFillsHighBits': True,
            'preservesVectorBitsAbove127': True, 'memoryReadBytes': 0,
            'memoryWriteBytes': 0, 'writesFlags': False})


def decode_method_carrier_instructions(mapper, data, start_va):
    class Fallback:
        def decode_one_x64(self, raw, offset, at):
            for decoder in (decode_memory_byte_xor, decode_register_immediate_dword,
                            decode_carrier_vector_transfer, decode_carrier_vector_byte_shift):
                result = decoder(raw, offset, at)
                if result is not None:
                    return result
            return mapper.decode_one_x64(raw, offset, at)
    return decode_generic_creation_instructions(Fallback(), data, start_va)

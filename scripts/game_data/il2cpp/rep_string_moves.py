"""Selected long-mode REP MOVSB and byte RIP-relative TEST decoding.

Default 64-bit address size supplies RSI/RDI/RCX to F3 A4. Direction and
valid-memory/concurrency conditions belong to the consumer proof, not decoding.
Unsupported prefixes and other string operations receive no claim here.
"""
from __future__ import annotations
from typing import Any
from .integer_addressing import decode_address_integer_instructions


def decode_rep_movsb(data: bytes, offset: int, start_va: int) -> tuple[dict, int] | None:
    if not 0 <= offset < len(data) or data[offset] != 0xf3: return None
    if offset + 1 == len(data):
        raise ValueError(f'x64.rep-movsb.truncated: offset={offset} requiredEnd={offset+2} bytes={len(data)}')
    if data[offset:offset+2] != b'\xf3\xa4': return None
    stop = offset + 2
    return {'offset': offset, 'va': hex(start_va + offset), 'bytes': data[offset:stop].hex(' '),
        'text': 'rep movsb', 'write': None,
        'stringOperation': {'operation': 'rep-movsb', 'elementBytes': 1, 'addressBits': 64,
            'sourceRegister': 'rsi', 'destinationRegister': 'rdi', 'countRegister': 'rcx',
            'countBits': 64, 'directionFlagControlsStep': True, 'terminatesOnCountZero': True,
            'zeroFlagControlsTermination': False, 'modifiesRegisters': ['rcx', 'rsi', 'rdi'],
            'writesArithmeticFlags': False, 'changesDirectionFlag': False}}, stop


def decode_rip_byte_test(data: bytes, offset: int, start_va: int) -> tuple[dict, int] | None:
    if not 0 <= offset < len(data) or data[offset:offset+2] != b'\xf6\x05': return None
    stop = offset + 7
    if stop > len(data):
        raise ValueError(f'x64.rip-byte-test.truncated: offset={offset} requiredEnd={stop} bytes={len(data)}')
    displacement = int.from_bytes(data[offset+2:offset+6], 'little', signed=True)
    target = start_va + stop + displacement; mask = data[offset+6]
    return {'offset': offset, 'va': hex(start_va + offset), 'bytes': data[offset:stop].hex(' '),
        'text': f"test byte [rip{'+' if displacement >= 0 else '-'}0x{abs(displacement):x} => 0x{target:x}], 0x{mask:x}",
        'write': None, 'byteTestOperation': {'bits': 8, 'address': target, 'mask': mask,
            'writesMemory': False, 'zeroFlagExpression': '(memoryByte & mask) == 0',
            'changesDirectionFlag': False}}, stop


def decode_rep_selection_instructions(mapper: Any, data: bytes, start_va: int) -> list[dict]:
    class Fallback:
        def decode_one_x64(self, raw, offset, at):
            for decoder in (decode_rep_movsb, decode_rip_byte_test):
                result = decoder(raw, offset, at)
                if result is not None: return result
            return mapper.decode_one_x64(raw, offset, at)
    return decode_address_integer_instructions(Fallback(), data, start_va)

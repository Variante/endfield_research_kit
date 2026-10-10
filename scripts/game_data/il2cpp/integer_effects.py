"""Selected locked exchanges, unary arithmetic and anonymous memory updates.

Preserve original instruction spans, operand widths and physical writes. These
facts establish no lock, cache, native class, runtime instance or field name.
A failed LOCK CMPXCHG still writes the old value back, so it is recorded as a
write either way; RIP-relative immediate-store addressing is computed from the
instruction end, including the immediate. Semantics follow the Intel SDM
vol. 2A-2C entries for IMUL, CMPXCHG, NEG and XADD.
"""
from __future__ import annotations
from scripts.game_data.il2cpp.integer_addressing import _address, _prefix, _reg, _required
from scripts.game_data.il2cpp.integer_tag_dispatch import _memory_text, _row
from scripts.game_data.il2cpp.integer_decrement import decode_decrement_instructions


def decode_locked_memory_exchange(data: bytes, offset: int, start_va: int):
    if not 0 <= offset < len(data) or data[offset] != 0xf0:
        return None
    at, rex = _prefix(data, offset + 1)
    opcode = data[at:at + 2]
    operation = {b'\x0f\xc1': 'xadd', b'\x0f\xb1': 'cmpxchg'}.get(opcode)
    if operation is None:
        return None
    at += 2
    modrm = _required(data, at, 1, offset, 'locked-memory-exchange')[0]; at += 1
    if modrm >> 6 == 3:
        return None
    bits = 64 if rex & 8 else 32
    register = _reg(((modrm >> 3) & 7) | ((rex & 4) << 1), bits)
    address, at = _address(data, at, modrm, rex, offset, 'locked-memory-exchange')
    operand = _memory_text(address, at, start_va, bits)
    facts = {'operation': operation, 'bits': bits, 'sourceRegister': register,
             'destinationAddress': address, 'memoryReadBytes': bits // 8,
             'memoryWriteBytes': bits // 8, 'locked': True,
             'writesFlags': ['CF', 'OF', 'SF', 'ZF', 'AF', 'PF']}
    if operation == 'xadd':
        facts.update(sourceRegisterResult='previous destination memory value',
                     memoryResult=f'previous memory plus previous source modulo 2^{bits}',
                     sourceWriteZeroExtendsTo64=bits == 32,
                     flagOperation='previous memory plus previous source')
    else:
        facts.update(accumulatorRegister='rax' if bits == 64 else 'eax',
                     successCondition='previous accumulator equals previous destination memory',
                     successMemoryResult='previous source register',
                     failureMemoryResult='previous memory value written back',
                     failureAccumulatorResult='previous destination memory value',
                     failureAccumulatorZeroExtendsTo64=bits == 32,
                     successAccumulatorPreserved=True,
                     flagOperation='previous accumulator minus previous memory',
                     memoryWriteCycleOccursOnBothOutcomes=True)
    return _row(data, offset, at, start_va, f'lock {operation} {operand}, {register}',
                lockedMemoryExchangeOperation=facts)


def decode_memory_step(data: bytes, offset: int, start_va: int):
    if not 0 <= offset < len(data):
        return None
    at, rex = _prefix(data, offset)
    if rex & 4 or data[at:at + 1] != b'\xff':
        return None
    at += 1
    modrm = _required(data, at, 1, offset, 'memory-step')[0]; at += 1
    group = (modrm >> 3) & 7
    if modrm >> 6 == 3 or group not in (0, 1):
        return None
    bits = 64 if rex & 8 else 32
    address, at = _address(data, at, modrm, rex, offset, 'memory-step')
    operand = _memory_text(address, at, start_va, bits)
    operation = 'inc' if group == 0 else 'dec'
    return _row(data, offset, at, start_va, f'{operation} {operand}',
                memoryStepOperation={'operation': operation, 'bits': bits,
                    'destinationAddress': address, 'memoryReadBytes': bits // 8,
                    'memoryWriteBytes': bits // 8, 'locked': False,
                    'delta': 1 if group == 0 else -1, 'wrapsModulo': 1 << bits,
                    'preservesRegisters': True, 'preservesCarryFlag': True,
                    'writesFlags': ['OF', 'SF', 'ZF', 'AF', 'PF']})


def decode_register_unary(data: bytes, offset: int, start_va: int):
    if not 0 <= offset < len(data):
        return None
    at, rex = _prefix(data, offset)
    if rex & 4 or data[at:at + 1] != b'\xf7':
        return None
    at += 1
    modrm = _required(data, at, 1, offset, 'register-unary')[0]; at += 1
    group = (modrm >> 3) & 7
    if modrm >> 6 != 3 or group not in (3, 5):
        return None
    bits = 64 if rex & 8 else 32
    register = _reg((modrm & 7) | ((rex & 1) << 3), bits)
    if group == 3:
        return _row(data, offset, at, start_va, f'neg {register}',
            write={'register': register, 'value': f'zero minus previous operand modulo 2^{bits}'},
            registerNegationOperation={'bits': bits, 'destinationRegister': register,
                'zeroExtendsTo64': bits == 32, 'wrapsModulo': 1 << bits,
                'carryFlagSetUnlessInputIsZero': True,
                'overflowFlagSetOnlyForMinimumSignedInput': True,
                'writesFlags': ['CF', 'OF', 'SF', 'ZF', 'AF', 'PF']})
    low, high = ('rax', 'rdx') if bits == 64 else ('eax', 'edx')
    return _row(data, offset, at, start_va, f'imul {register}',
        implicitSignedMultiplyOperation={'bits': bits, 'sourceRegister': register,
            'accumulatorRegister': low, 'lowResultRegister': low, 'highResultRegister': high,
            'fullProductBits': 2 * bits, 'signedOperands': True,
            'result':'full signed product split into high and low destination words',
            'resultWritesZeroExtendTo64': bits == 32, 'writesMemory': False,
            'overflowFlags': ['CF', 'OF'],
            'overflowCondition':'full signed product differs from sign extension of low result',
            'undefinedFlags': ['SF', 'ZF', 'AF', 'PF']})


def decode_memory_source_subtract(data: bytes, offset: int, start_va: int):
    if not 0 <= offset < len(data):
        return None
    at, rex = _prefix(data, offset)
    if data[at:at + 1] != b'\x2b':
        return None
    at += 1
    modrm = _required(data, at, 1, offset, 'memory-source-subtract')[0]; at += 1
    if modrm >> 6 == 3:
        return None
    bits = 64 if rex & 8 else 32
    destination = _reg(((modrm >> 3) & 7) | ((rex & 4) << 1), bits)
    address, at = _address(data, at, modrm, rex, offset, 'memory-source-subtract')
    operand = _memory_text(address, at, start_va, bits)
    return _row(data, offset, at, start_va, f'sub {destination}, {operand}',
        write={'register': destination, 'value': f'previous destination minus stored source modulo 2^{bits}'},
        memorySourceSubtractOperation={'bits': bits, 'destinationRegister': destination,
            'sourceAddress': address, 'memoryReadBytes': bits // 8, 'writesMemory': False,
            'zeroExtendsTo64': bits == 32, 'wrapsModulo': 1 << bits,
            'writesFlags': ['CF', 'OF', 'SF', 'ZF', 'AF', 'PF']})


def decode_immediate_memory_store(data: bytes, offset: int, start_va: int):
    if not 0 <= offset < len(data):
        return None
    at, rex = _prefix(data, offset)
    if rex & 4 or data[at:at + 1] != b'\xc7':
        return None
    at += 1
    modrm = _required(data, at, 1, offset, 'immediate-memory-store')[0]; at += 1
    if modrm >> 6 == 3 or (modrm >> 3) & 7:
        return None
    address, at = _address(data, at, modrm, rex, offset, 'immediate-memory-store')
    immediate = int.from_bytes(_required(data, at, 4, offset, 'immediate-memory-store'), 'little', signed=True)
    at += 4
    bits = 64 if rex & 8 else 32
    operand = _memory_text(address, at, start_va, bits)
    return _row(data, offset, at, start_va, f'mov {operand}, {hex(immediate)}',
        immediateMemoryStoreOperation={'bits': bits, 'destinationAddress': address,
            'memoryWriteBytes': bits // 8, 'memoryReadBytes': 0, 'encodedImmediateBits': 32,
            'immediateSignedValue': immediate, 'immediateWord': immediate & ((1 << bits) - 1),
            'signExtendsImmediateTo64': bits == 64, 'writesFlags': False,
            'preservesRegisters': True})


def decode_effect_instructions(mapper, data: bytes, start_va: int):
    class Fallback:
        def decode_one_x64(self, raw, offset, at):
            for decoder in (decode_locked_memory_exchange, decode_memory_step,
                            decode_register_unary, decode_memory_source_subtract,
                            decode_immediate_memory_store):
                result = decoder(raw, offset, at)
                if result is not None:
                    return result
            return mapper.decode_one_x64(raw, offset, at)
    return decode_decrement_instructions(Fallback(), data, start_va)

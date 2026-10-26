"""Optional register-only facts the subset decoder leaves as ``db`` rows.

* ``SHL/SHR/SAR r64, CL`` (REX.W ``D3 /4 /5 /7``): count is the pre-instruction
  CL masked to six bits; only the destination register and flags change.
* ``PSRLDQ xmm, imm8`` (``66 [REX] 0F 73 /3 ib``): byte shift right of one
  vector register.
* ``INC/DEC r16`` (``66 [REX] FF /0 /1``): only the low word of one register.
* ``TEST m8, imm8`` (``F6 /0 ib``): reads one byte, writes flags only.
* ``ADD/SUB r64, r64`` in both directions (register operands only).
* ``TEST rax, imm32`` (REX.W ``A9``), ``UNPCKLPD xmm, xmm`` (``66 0F 14``),
  the prefixed multibyte ``NOP`` and ``OR r8, m8`` (``0A``).
* ``MOVQ m64, xmm`` (``66 0F D6``): the only form here that writes memory
  (eight bytes at the decoded address).

None of these transfers control. ``decode_shift_sweep`` is a complete linear
sweep that adds them (plus the existing accumulator ``AND``, SSE lane and
CVTPS2PD helpers) to the base decoder, so a caller can require that a scoped
region contains no unknown ``db`` row. On the installed
``DamageAction._ProcessDamage`` the sweep leaves no ``db`` row and its
instruction boundaries match an independent disassembler. No runtime value is
inferred.
"""
from __future__ import annotations
from typing import Any
from .integer_addressing import _address, _prefix, _reg, _required, decode_register_arithmetic
from .integer_context_memory import decode_accumulator_and
from .integer_tag_dispatch import _memory_text, _row
from .runtime_data_instructions import decode_packed_single_to_double
from .sse_lanes import decode_sse_lanes, decode_sse_numeric

_SHIFTS = {4: 'shl', 5: 'shr', 7: 'sar'}


def decode_register_cl_shift(data: bytes, offset: int, start_va: int):
    if not 0 <= offset < len(data): return None
    at, rex = _prefix(data, offset)
    if not rex & 8 or rex & 4 or data[at:at+1] != b'\xd3': return None
    at += 1; modrm = _required(data, at, 1, offset, 'register-cl-shift')[0]; at += 1
    operation = _SHIFTS.get((modrm >> 3) & 7)
    if modrm >> 6 != 3 or operation is None: return None
    destination = _reg((modrm & 7) | ((rex & 1) << 3), 64)
    return _row(data, offset, at, start_va, f'{operation} {destination}, cl',
        write={'register': destination, 'value': f'{operation} previous QWORD by pre-instruction CL modulo 64'},
        registerClShiftOperation={'operation': operation, 'destinationRegister': destination, 'bits': 64,
            'countRegister': 'cl', 'countMask': 63, 'readsMemory': False, 'writesMemory': False,
            'transfersControl': False})


def decode_vector_byte_shift_right(data: bytes, offset: int, start_va: int):
    if not 0 <= offset < len(data) or data[offset:offset+1] != b'\x66': return None
    at, rex = _prefix(data, offset + 1)
    if rex & 0x0a or data[at:at+2] != b'\x0f\x73': return None
    at += 2; modrm = _required(data, at, 1, offset, 'vector-byte-shift')[0]; at += 1
    if modrm >> 6 != 3 or (modrm >> 3) & 7 != 3: return None
    count = _required(data, at, 1, offset, 'vector-byte-shift')[0]; at += 1
    register = f'xmm{(modrm & 7) | ((rex & 1) << 3)}'
    return _row(data, offset, at, start_va, f'psrldq {register}, {hex(count)}',
        write={'register': register, 'value': 'logical right byte shift of previous 128 bits'},
        vectorByteShiftOperation={'register': register, 'byteCount': count, 'readsMemory': False,
            'writesMemory': False, 'transfersControl': False, 'writesFlags': False})


def decode_word_register_step(data: bytes, offset: int, start_va: int):
    if not 0 <= offset < len(data) or data[offset:offset+1] != b'\x66': return None
    at, rex = _prefix(data, offset + 1)
    if rex & 0x0e or data[at:at+1] != b'\xff': return None
    at += 1; modrm = _required(data, at, 1, offset, 'word-register-step')[0]; at += 1
    operation = {0: 'inc', 1: 'dec'}.get((modrm >> 3) & 7)
    if modrm >> 6 != 3 or operation is None: return None
    number = (modrm & 7) | ((rex & 1) << 3)
    register = _reg(number, 64)
    word = {'rax': 'ax', 'rcx': 'cx', 'rdx': 'dx', 'rbx': 'bx', 'rsp': 'sp', 'rbp': 'bp',
            'rsi': 'si', 'rdi': 'di'}.get(register, f'{register}w')
    return _row(data, offset, at, start_va, f'{operation} {word}',
        write={'register': register, 'value': f'low 16 bits {operation}remented modulo 2^16; upper 48 bits preserved'},
        wordRegisterStepOperation={'operation': operation, 'register': word, 'fullRegister': register,
            'bits': 16, 'readsMemory': False, 'writesMemory': False, 'transfersControl': False,
            'carryFlagPreserved': True})


def decode_byte_memory_immediate_test(data: bytes, offset: int, start_va: int):
    if not 0 <= offset < len(data): return None
    at, rex = _prefix(data, offset)
    if rex & 0x0c or data[at:at+1] != b'\xf6': return None
    at += 1; modrm = _required(data, at, 1, offset, 'byte-memory-immediate-test')[0]; at += 1
    if modrm >> 6 == 3 or (modrm >> 3) & 7: return None
    address, at = _address(data, at, modrm, rex, offset, 'byte-memory-immediate-test')
    immediate = _required(data, at, 1, offset, 'byte-memory-immediate-test')[0]; at += 1
    return _row(data, offset, at, start_va, f'test {_memory_text(address, at, start_va, 8)}, {hex(immediate)}',
        write=None, byteMemoryImmediateTestOperation={'sourceAddress': address, 'immediate': immediate,
            'memoryReadBytes': 1, 'memoryWriteBytes': 0, 'preservesRegisters': True, 'writesResult': False})


def decode_register_reverse_arithmetic(data: bytes, offset: int, start_va: int):
    if not 0 <= offset < len(data): return None
    at, rex = _prefix(data, offset)
    operation = {0x01: 'add', 0x29: 'sub'}.get(data[at] if at < len(data) else -1)
    if not rex & 8 or operation is None: return None
    at += 1; modrm = _required(data, at, 1, offset, 'register-reverse-arithmetic')[0]; at += 1
    if modrm >> 6 != 3: return None
    source = _reg(((modrm >> 3) & 7) | ((rex & 4) << 1), 64)
    destination = _reg((modrm & 7) | ((rex & 1) << 3), 64)
    return _row(data, offset, at, start_va, f'{operation} {destination}, {source}',
        write={'register': destination, 'value': f'64-bit {operation} modulo 2^64; full register'},
        integerOperation={'operation': operation, 'destination': destination, 'source': source,
            'bits': 64, 'wrapsModulo': 1 << 64, 'zeroExtendsTo64': False, 'flags': 'arithmetic flags updated'})


def decode_accumulator_immediate_test(data: bytes, offset: int, start_va: int):
    """``TEST RAX/EAX, imm32`` (``[REX.W] A9 id``): flags only."""
    if not 0 <= offset < len(data): return None
    at, rex = _prefix(data, offset)
    if rex & 0x07 or data[at:at+1] != bytes.fromhex('a9'): return None
    encoded = int.from_bytes(_required(data, at + 1, 4, offset, 'accumulator-immediate-test'), 'little'); at += 5
    bits = 64 if rex & 8 else 32
    immediate = (encoded - (1 << 32) if bits == 64 and encoded >= 1 << 31 else encoded) & ((1 << bits) - 1)
    register = 'rax' if bits == 64 else 'eax'
    return _row(data, offset, at, start_va, f'test {register}, {hex(immediate)}', write=None,
        accumulatorImmediateTestOperation={'register': register, 'immediate': immediate,
            'readsMemory': False, 'writesMemory': False, 'writesResult': False})


def decode_low_quad_store(data: bytes, offset: int, start_va: int):
    """``MOVQ m64, xmm`` (``66 [REX] 0F D6 /r``): writes eight memory bytes."""
    if not 0 <= offset < len(data) or data[offset:offset+1] != bytes.fromhex('66'): return None
    at, rex = _prefix(data, offset + 1)
    if rex & 8 or data[at:at+2] != bytes.fromhex('0fd6'): return None
    at += 2; modrm = _required(data, at, 1, offset, 'low-quad-store')[0]; at += 1
    if modrm >> 6 == 3: return None
    source = f'xmm{((modrm >> 3) & 7) | ((rex & 4) << 1)}'
    address, at = _address(data, at, modrm, rex, offset, 'low-quad-store')
    return _row(data, offset, at, start_va, f'movq {_memory_text(address, at, start_va, 64)}, {source}', write=None,
        memoryWrite={'address': address, 'bytes': 8, 'source': source})


def decode_packed_double_unpack_low(data: bytes, offset: int, start_va: int):
    """``UNPCKLPD xmm, xmm`` (``66 [REX] 0F 14 /r``), register operands only."""
    if not 0 <= offset < len(data) or data[offset:offset+1] != bytes.fromhex('66'): return None
    at, rex = _prefix(data, offset + 1)
    if rex & 0x0a or data[at:at+2] != bytes.fromhex('0f14'): return None
    at += 2; modrm = _required(data, at, 1, offset, 'packed-double-unpack')[0]; at += 1
    if modrm >> 6 != 3: return None
    destination = f'xmm{((modrm >> 3) & 7) | ((rex & 4) << 1)}'; source = f'xmm{(modrm & 7) | ((rex & 1) << 3)}'
    return _row(data, offset, at, start_va, f'unpcklpd {destination}, {source}',
        write={'register': destination, 'value': 'low double of destination, then low double of source'})


def decode_prefixed_multibyte_nop(data: bytes, offset: int, start_va: int):
    """``66...66 0F 1F /0`` padding NOP with repeated operand-size prefixes."""
    at = offset
    while at < len(data) and data[at] == 0x66: at += 1
    if at - offset < 2 or data[at:at+2] != bytes.fromhex('0f1f'): return None
    at += 2; modrm = _required(data, at, 1, offset, 'prefixed-nop')[0]; at += 1
    if modrm >> 6 == 3 or (modrm >> 3) & 7: return None
    _address_row, at = _address(data, at, modrm, 0, offset, 'prefixed-nop')
    return _row(data, offset, at, start_va, 'nop', write=None)


def decode_byte_register_memory_or(data: bytes, offset: int, start_va: int):
    """``OR r8, m8`` (``[REX] 0A /r``): reads one byte, writes one byte register."""
    if not 0 <= offset < len(data): return None
    at, rex = _prefix(data, offset)
    if rex & 8 or data[at:at+1] != bytes.fromhex('0a'): return None
    at += 1; modrm = _required(data, at, 1, offset, 'byte-register-memory-or')[0]; at += 1
    if modrm >> 6 == 3: return None
    number = ((modrm >> 3) & 7) | ((rex & 4) << 1)
    if not rex and 4 <= number < 8: return None  # AH..BH
    register = ('al', 'cl', 'dl', 'bl', 'spl', 'bpl', 'sil', 'dil')[number] if number < 8 else f'r{number}b'
    address, at = _address(data, at, modrm, rex, offset, 'byte-register-memory-or')
    return _row(data, offset, at, start_va, f'or {register}, {_memory_text(address, at, start_va, 8)}',
        write={'register': _reg(number, 64), 'value': 'low byte OR memory byte; upper 56 bits preserved'})


DECODERS = (decode_register_cl_shift, decode_vector_byte_shift_right, decode_word_register_step,
            decode_byte_memory_immediate_test, decode_register_reverse_arithmetic, decode_register_arithmetic, decode_accumulator_and,
            decode_sse_lanes, decode_sse_numeric, decode_packed_single_to_double,
            decode_accumulator_immediate_test, decode_low_quad_store, decode_packed_double_unpack_low,
            decode_prefixed_multibyte_nop, decode_byte_register_memory_or)


def decode_shift_sweep(mapper: Any, data: bytes, start_va: int) -> list[dict]:
    """Complete contiguous sweep; unknown bytes stay ``db`` rows for callers to refuse."""
    rows = []; offset = 0
    while offset < len(data):
        for decoder in DECODERS:
            decoded = decoder(data, offset, start_va)
            if decoded is not None: break
        else:
            decoded = mapper.decode_one_x64(data, offset, start_va)
        row, stop = decoded
        if not offset < stop <= len(data) or bytes.fromhex(row['bytes']) != data[offset:stop]:
            raise ValueError(f'x64.inventory-span: offset={offset} stop={stop} bytes={len(data)}')
        rows.append(row); offset = stop
    return rows

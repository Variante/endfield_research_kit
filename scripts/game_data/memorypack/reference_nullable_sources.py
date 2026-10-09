"""Selected reference-adapter ABI and complete buffered null paths.

An original null reference consumes one marker byte, independently of its
eight-byte runtime output slot. These proofs grant no positive child/list
admission and do not observe initialization, provider selection or execution.
"""
from __future__ import annotations

import struct
from typing import Any, Callable

from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack.buffered_owned_sources import _program


def validate_reference_adapter_abi(image: Any, method_row: list, *,
                                   nonnull: bool, fail: Callable) -> None:
    """Own each VAR ordinal; the nonnull helper's third wrap is by value."""
    image.validate_method_row(method_row[:3], label='referenceNullableSource')
    method = image.metadata.methods[method_row[0]]
    owner = image.metadata.types[method.declaring_type]
    wanted = 'DeserializeNotNull' if nonnull else 'Deserialize'
    section = image.metadata.sections['genericContainers']
    at = section.offset + owner.generic_container_index * 16
    if (owner.generic_container_index < 0
            or not section.offset <= at <= section.offset + section.size - 16):
        fail('adapter-generic-container', 'bounded class generic container', owner.generic_container_index)
    container = struct.unpack_from('<iiii', image.metadata.buf, at)
    if (image.type_name(owner.index) != 'Beyond.MemoryPack.GenericMemoryPackFormatter`2'
            or image.metadata.string(method.name_index) != wanted
            or bool(method.flags & 0x10) != nonnull
            or container[:3] != (owner.index, 2, 0) or container[3] < 0):
        fail('adapter-method-owner', 'two owned class arguments and selected static/instance method', method_row)
    selected = NativeReferenceContext(image)
    parameters = image.metadata.parameters_for(method)
    if selected.type_name(method.return_type) != 'void' or len(parameters) != (3 if nonnull else 2):
        fail('adapter-parameter-count', 'void and exact selected ABI', len(parameters))
    reader = image.pe.bytes_at_va(selected.type_pointer(parameters[0].type_index), 16)
    if selected.type_name(parameters[0].type_index) != 'MemoryPack.MemoryPackReader' or reader[11] != 0x20:
        fail('adapter-reader-byref', 'ref MemoryPackReader', reader.hex())
    for ordinal, parameter in enumerate(parameters[1:]):
        raw = image.pe.bytes_at_va(selected.type_pointer(parameter.type_index), 16)
        expected = container[3] + ordinal
        byref = 0x20 if ordinal == 0 else 0
        if raw[10:12] != bytes((0x13, byref)) or int.from_bytes(raw[:8], 'little') != expected:
            fail('adapter-owned-var', {'ordinal': ordinal, 'byref': byref != 0}, raw.hex())


def validate_buffered_null_reference(image: Any, proof: dict, offsets: dict, *,
                                     fail: Callable) -> dict:
    """Authenticate entry-to-RET FF branch, aliases and all four counters."""
    window, program = proof['window'], proof['program']
    image.check_windows([window], label='referenceNullableSource')
    _program(image, window, program, fail)
    pointer, remaining, advanced, consumed = (offsets[k] for k in
        ('currentPtr', 'bufferLength', 'advancedCount', 'consumed'))
    if any(type(n) is not int or not 0 <= n < 128 for n in offsets.values()):
        fail('null-reader-offsets', 'bounded unboxed metadata fields', offsets)
    # Seven nonvolatile pushes plus the local frame. RBX was saved before
    # the pushes, so its restoration refers to the original entry+8 slot.
    frame = 7 * 8 + 0x90
    expected = ['48895C2408', '4C894C2420', '4C89442418', '4889542410',
        '55', '56', '57', '4154', '4155', '4156', '4157', '4881EC90000000',
        '498BD9', '498BF0', '488BFA', None, None,
        f'837F{remaining:02X}01', None, f'488B47{pointer:02X}', '8038FF', None,
        f'837F{remaining:02X}01', None, f'8B5F{remaining:02X}', '83EB01', None,
        f'895F{remaining:02X}', f'48FF47{pointer:02X}', f'FF47{advanced:02X}',
        f'FF47{consumed:02X}', '33C0', '488906',
        '488B9C24' + struct.pack('<I', frame + 8).hex().upper(),
        '4881C490000000', '415F', '415E', '415D', '415C', '5F', '5E', '5D', 'C3']
    if len(program) != len(expected) or program[0][0] != window['startRva']:
        fail('null-complete-program', len(expected), len(program))
    for n, ((at, raw_hex), wanted) in enumerate(zip(program, expected, strict=True)):
        if wanted is not None and raw_hex != wanted:
            fail('null-owned-transfer-or-cursor', {'position': n, 'bytes': wanted}, [at, raw_hex])
    flag = bytes.fromhex(program[15][1])
    if len(flag) != 7 or flag[:2] != b'\x80\x3d' or flag[-1] != 0:
        fail('null-initialized-guard', 'byte flag compared to zero', program[15])
    for n, opcode in ((16, 0x75), (18, 0x7d), (23, 0x7d), (26, 0x79)):
        at, raw_hex = program[n]; raw = bytes.fromhex(raw_hex)
        if (len(raw) != 2 or raw[0] != opcode
                or at + 2 + int.from_bytes(raw[1:], 'little', signed=True) != program[n + 1][0]):
            fail('null-selected-successor', 'initialized/available/nonnegative taken branch', program[n])
    at, raw_hex = program[21]; raw = bytes.fromhex(raw_hex)
    positive = at + 2 + int.from_bytes(raw[1:], 'little', signed=True) if len(raw) == 2 else -1
    end = program[-1][0] + 1
    if (len(raw) != 2 or raw[0] != 0x75 or program[22][0] != at + 2
            or not end <= positive < window['endRva']):
        fail('null-versus-positive-branch', 'FF falls through; non-FF reaches separate positive body', program[21])
    return {'markerHex': 'FF', 'wireBytes': 1, 'runtimeReferenceBytes': 8,
            'readerRegisters': ['rdi'], 'originalOutputRegister': 'rsi',
            'positiveEntryRva': positive, 'nullReturnRva': program[-1][0]}

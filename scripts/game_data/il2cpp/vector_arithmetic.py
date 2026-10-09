"""Authenticate a complete named Vector3 subtraction leaf and its Win64 ABI.

The straight-line native grammar ends at its own RET. It does not need a
guessed next-method boundary or the subset decoder's fallback instructions.
The caller authenticates its selected NativeImage before and after use.
"""
from __future__ import annotations

import hashlib
from typing import Any
from .reference_layouts import NativeReferenceContext


def validate_vector3_subtraction_leaf(image: Any, pointer: int, *,
                                      type_name: str = 'UnityEngine.Vector3') -> dict[str, Any]:
    """Prove three Single differences, a twelve-byte output and returned buffer."""
    selected = NativeReferenceContext(image)
    metadata = image.metadata

    def fail(check: str, expected: Any, actual: Any) -> None:
        raise ValueError(f'vector3Subtraction.{check}: expected={str(expected)[:512]} actual={str(actual)[:512]}')

    definition = selected.index.types.get(type_name)
    if (definition is None or definition.generic_container_index >= 0
            or selected.parent(type_name) != 'System.ValueType'):
        fail('value-owner', 'one named nongeneric Vector3 value type', type_name)
    fields = [f for f in metadata.fields_for(definition)
              if not selected.field_attributes(f.type_index) & 0x10]
    expected_fields = [('x', 'float', 16), ('y', 'float', 20), ('z', 'float', 24)]
    actual_fields = [(metadata.string(f.name_index), *selected.field(
        type_name + '::' + metadata.string(f.name_index))[1:]) for f in fields]
    if actual_fields != expected_fields:
        fail('value-fields', expected_fields, actual_fields)
    registration = image.registration
    if not 0 <= definition.index < registration['typeDefinitionsSizesCount']:
        fail('value-size-index', 'selected type size table entry', definition.index)
    size_pointer = image.pe.u64_at_va(int(registration['typeDefinitionsSizes'], 16) + definition.index * 8)
    sizes = image.pe.bytes_at_va(size_pointer, 16) if size_pointer else b''
    if (len(sizes) != 16 or int.from_bytes(sizes[:4], 'little') < 28
            or int.from_bytes(sizes[4:8], 'little', signed=True) != 12):
        fail('native-value-size', 'boxed xyz extent and twelve native bytes', sizes.hex().upper())
    methods = [m for m in metadata.methods_for(definition)
               if metadata.string(m.name_index) == 'op_Subtraction'
               and m.parameter_count == 2 and selected.type_name(m.return_type) == type_name
               and [selected.type_name(p.type_index) for p in metadata.parameters_for(m)] == [type_name] * 2]
    if len(methods) != 1:
        fail('named-method', 'one selected binary subtraction declaration', len(methods))
    method = methods[0]
    parameters = list(metadata.parameters_for(method))
    if (method.declaring_type != definition.index or method.generic_container_index >= 0
            or not method.flags & 0x10 or image.method_pointer_va(method) != pointer):
        fail('static-method-identity', 'selected nongeneric static subtraction entry', pointer)
    for role, type_index in [('return', method.return_type), *[(f'argument{n}', p.type_index)
                                   for n, p in enumerate(parameters)]]:
        record = image.pe.bytes_at_va(selected.type_pointer(type_index), 16)
        if (len(record) != 16 or record[10] != 0x11 or record[11] & 0x7f
                or int.from_bytes(record[:8], 'little') != definition.index):
            fail('value-signature:' + role, 'selected undecorated Vector3 value', record.hex().upper())
    # MOVSS/SUBSS independently compute x, y and z. UNPCKLPS packs x/y
    # into the low eight bytes before MOVSD; MOVSS stores z separately.
    program = [
        ('F30F1002', 'load left.x into xmm0'),
        ('F30F104A04', 'load left.y into xmm1'),
        ('F3410F5C00', 'subtract right.x from xmm0'),
        ('F3410F5C4804', 'subtract right.y from xmm1'),
        ('F30F105208', 'load left.z into xmm2'),
        ('F3410F5C5008', 'subtract right.z from xmm2'),
        ('0F14C1', 'pack result.x/result.y into low xmm0'),
        ('F20F1101', 'store result.x/result.y at output+0'),
        ('F30F115108', 'store result.z at output+8'),
        ('488BC1', 'return the incoming output pointer in rax'),
        ('C3', 'complete leaf return'),
    ]
    expected = b''.join(bytes.fromhex(code) for code, _meaning in program)
    actual = image.pe.bytes_at_va(pointer, len(expected))
    if actual != expected:
        fail('complete-leaf-program', expected.hex().upper(), actual.hex().upper())
    offset = 0; instructions = []
    for code, meaning in program:
        instructions.append({'offset': offset, 'rawHex': code, 'operation': meaning})
        offset += len(bytes.fromhex(code))
    return {'schema': 'endfield.vector3-subtraction-leaf-proof.v1',
        'methodIndex': method.index, 'typeDefinition': definition.index,
        'method': type_name + '.op_Subtraction', 'entryRva': pointer - image.pe.image_base,
        'programBytes': len(expected), 'programSha256': hashlib.sha256(actual).hexdigest().upper(),
        'program': instructions, 'nativeValueBytes': 12,
        'abi': {'output': 'rcx', 'left': 'rdx', 'right': 'r8', 'returnedOutput': 'rax'},
        'operation': 'componentwise-Single-left-minus-right',
        'completeStraightLineReturn': True, 'observedValues': False,
        'evidenceBoundary': 'Selected static value signature, current xyz layout and the complete native leaf establish the compiled operation and buffers; callers and executed values require separate evidence.'}

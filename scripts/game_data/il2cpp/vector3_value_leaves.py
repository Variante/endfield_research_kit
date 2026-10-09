"""Prove complete Vector3 value leaves, their buffers and register effects.

These byte grammars finish at a checked RET. They never use a guessed next
method to delimit a leaf. The caller must authenticate its selected native
image; this module does not choose an installed build or record addresses.
"""
from __future__ import annotations
import hashlib
from typing import Any
from .reference_layouts import NativeReferenceContext


def validate_vector3_value_leaf(image: Any, pointer: int, *, operation: str,
                                type_name: str = 'UnityEngine.Vector3') -> dict:
    selected = NativeReferenceContext(image)
    metadata = image.metadata

    def fail(check, expected, actual):
        raise ValueError(f'vector3ValueLeaf.{check}: expected={str(expected)[:384]} '
                         f'actual={str(actual)[:512]}')

    signatures = {
        'addition': ('op_Addition', [type_name, type_name]),
        'vector-times-scalar': ('op_Multiply', [type_name, 'float']),
        'right': ('get_right', []),
        'forward': ('get_forward', []),
    }
    if operation not in signatures:
        fail('operation', list(signatures), operation)
    method_name, argument_names = signatures[operation]
    definition = selected.index.types.get(type_name)
    if (definition is None or definition.generic_container_index >= 0
            or selected.parent(type_name) != 'System.ValueType'):
        fail('value-owner', 'named nongeneric Vector3 value', type_name)
    fields = [f for f in metadata.fields_for(definition)
              if not selected.field_attributes(f.type_index) & 0x10]
    actual_fields = [(metadata.string(f.name_index), *selected.field(
        type_name + '::' + metadata.string(f.name_index))[1:]) for f in fields]
    if actual_fields != [('x', 'float', 16), ('y', 'float', 20), ('z', 'float', 24)]:
        fail('value-fields', 'three consecutive named Singles', actual_fields)
    registration = image.registration
    if not 0 <= definition.index < registration['typeDefinitionsSizesCount']:
        fail('value-size-index', 'selected type-size entry', definition.index)
    size_pointer = image.pe.u64_at_va(int(registration['typeDefinitionsSizes'], 16) + definition.index * 8)
    sizes = image.pe.bytes_at_va(size_pointer, 16) if size_pointer else b''
    if (len(sizes) != 16 or int.from_bytes(sizes[:4], 'little') < 28
            or int.from_bytes(sizes[4:8], 'little', signed=True) != 12):
        fail('native-value-size', 'boxed xyz extent and twelve native bytes', sizes.hex())
    methods = [m for m in metadata.methods_for(definition)
               if metadata.string(m.name_index) == method_name
               and m.parameter_count == len(argument_names)
               and selected.type_name(m.return_type) == type_name
               and [selected.type_name(p.type_index) for p in metadata.parameters_for(m)] == argument_names]
    if len(methods) != 1:
        fail('named-method', 'one selected typed declaration', len(methods))
    method = methods[0]
    if (method.declaring_type != definition.index or method.generic_container_index >= 0
            or not method.flags & 0x10 or image.method_pointer_va(method) != pointer):
        fail('static-method-identity', 'selected nongeneric static entry', pointer)
    parameters = list(metadata.parameters_for(method))
    for role, index, name in [('return', method.return_type, type_name),
            *[(f'argument{n}', p.type_index, name) for n, (p, name) in enumerate(zip(parameters, argument_names))]]:
        record = image.pe.bytes_at_va(selected.type_pointer(index), 16)
        kind = 0x11 if name == type_name else 0x0c
        if (len(record) != 16 or record[10] != kind or record[11] & 0x7f
                or kind == 0x11 and int.from_bytes(record[:8], 'little') != definition.index):
            fail('value-signature:' + role, 'undecorated selected value or Single', record.hex())

    if operation == 'addition':
        grammar = [('F30F1002', 'load left.x'), ('F30F104A04', 'load left.y'),
            ('F3410F5800', 'add right.x'), ('F3410F584804', 'add right.y'),
            ('F30F105208', 'load left.z'), ('F3410F585008', 'add right.z'),
            ('0F14C1', 'pack x/y'), ('F20F1101', 'write output.x/y'),
            ('F30F115108', 'write output.z'), ('488BC1', 'return output pointer'), ('C3', 'return')]
        abi = {'output': 'rcx', 'left': 'rdx', 'right': 'r8', 'returnedOutput': 'rax'}
        xmm_writes = ['xmm0', 'xmm1', 'xmm2']
    elif operation == 'vector-times-scalar':
        grammar = [('0F28C2', 'copy scalar to x carrier'), ('0F28CA', 'copy scalar to y carrier'),
            ('F30F5902', 'scalar times vector.x'), ('F30F594A04', 'scalar times vector.y'),
            ('F30F595208', 'scalar times vector.z'), ('0F14C1', 'pack x/y'),
            ('F20F1101', 'write output.x/y'), ('F30F115108', 'write output.z'),
            ('488BC1', 'return output pointer'), ('C3', 'return')]
        abi = {'output': 'rcx', 'vector': 'rdx', 'scalarLowLane': 'xmm2', 'returnedOutput': 'rax'}
        xmm_writes = ['xmm0', 'xmm1', 'xmm2']
    else:
        # Only the RIP displacement varies. The scalar literal must be exactly
        # IEEE-754 +1.0; XORPS supplies positive zero for the other components.
        head = image.pe.bytes_at_va(pointer, 8)
        opcode = bytes.fromhex('F30F1005' if operation == 'right' else 'F30F1015')
        if len(head) != 8 or head[:4] != opcode:
            fail('axis-literal-load', opcode.hex(), head.hex())
        literal = pointer + 8 + int.from_bytes(head[4:], 'little', signed=True)
        raw_literal = image.pe.bytes_at_va(literal, 4)
        if raw_literal != bytes.fromhex('0000803F'):
            fail('axis-literal', 'IEEE-754 positive one', raw_literal.hex())
        grammar = [(head.hex().upper(), 'load exact positive one')]
        grammar += ([('0F57D2', 'positive zero in y/z'), ('0F14C2', 'pack x/y')]
                    if operation == 'right' else
                    [('0F57C9', 'positive zero in y'), ('0F57C0', 'positive zero in x'), ('0F14C1', 'pack x/y')])
        grammar += [('F20F1101', 'write output.x/y'), ('F30F115108', 'write output.z'),
                    ('488BC1', 'return output pointer'), ('C3', 'return')]
        abi = {'output': 'rcx', 'returnedOutput': 'rax'}
        xmm_writes = ['xmm0', 'xmm2'] if operation == 'right' else ['xmm0', 'xmm1', 'xmm2']
    expected = b''.join(bytes.fromhex(raw) for raw, _ in grammar)
    actual = image.pe.bytes_at_va(pointer, len(expected))
    if actual != expected:
        fail('complete-leaf-program', expected.hex().upper(), actual.hex().upper())
    offset = 0
    program = []
    for raw, meaning in grammar:
        program.append({'offset': offset, 'rawHex': raw, 'operation': meaning})
        offset += len(bytes.fromhex(raw))
    result = {'schema': 'endfield.vector3-value-leaf-proof.v1', 'operation': operation,
        'methodIndex': method.index, 'typeDefinition': definition.index,
        'method': type_name + '.' + method_name, 'entryRva': pointer-image.pe.image_base,
        'programBytes': len(expected), 'programSha256': hashlib.sha256(actual).hexdigest().upper(),
        'program': program, 'nativeValueBytes': 12, 'abi': abi,
        'generalRegistersWritten': ['rax'], 'simdRegistersWritten': xmm_writes,
        'preservedHeldPointers': ['r8', 'r9', 'r10'],
        'memoryWrites': ['incoming output+0..7', 'incoming output+8..11'],
        'completeStraightLineReturn': True, 'observedValues': False,
        'evidenceBoundary': 'Complete selected leaf and typed value layout establish component operations, output identity and register preservation. Operand buffers must not alias unread inputs; calls and values require separate evidence.'}
    if operation in ('right', 'forward'):
        result.update(axisComponents=[1.0, 0.0, 0.0] if operation == 'right' else [0.0, 0.0, 1.0],
            literalRva=literal-image.pe.image_base, literalRawHex=raw_literal.hex().upper())
    return result

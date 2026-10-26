"""Prove a complete Vector3 Single square/sum leaf and its selected ABI.

The caller authenticates its NativeImage before and after use. A named folded
entry does not identify a live MethodInfo, and floating results retain the
machine's actual Single rounding and exception environment.
"""
from __future__ import annotations

import hashlib
from typing import Any
from .reference_layouts import NativeReferenceContext


def prove_squared_magnitude_program(program: bytes, *, leading_nop: bool = False) -> dict:
    """Require every instruction through RET; never scan a guessed boundary."""
    if not isinstance(program, bytes) or type(leading_nop) is not bool:
        raise ValueError('vector3-square.program: bytes and explicit Boolean mode required')
    grammar = [('F30F104904', 'load y into low xmm1'),
               ('F30F1001', 'load x into low xmm0'),
               ('F30F105108', 'load z into low xmm2'),
               ('F30F59C0', 'Single x times x'),
               ('F30F59C9', 'Single y times y'),
               ('F30F59D2', 'Single z times z'),
               ('F30F58C1', 'Single x-square plus y-square'),
               ('F30F58C2', 'Single previous sum plus z-square'),
               ('C3', 'complete leaf return')]
    if leading_nop:
        grammar.insert(0, ('6690', 'explicit two-byte nop'))
    expected = b''.join(bytes.fromhex(raw) for raw, _ in grammar)
    if program != expected:
        raise ValueError(f'vector3-square.program: expected={expected.hex().upper()} actual={program.hex().upper()[:192]}')
    instructions = [];offset = 0
    for raw, operation in grammar:
        instructions.append({'offset':offset,'rawHex':raw,'operation':operation})
        offset += len(bytes.fromhex(raw))
    return {'schema':'endfield.vector3-square-program-proof.v1','programBytes':len(program),
            'programSha256':hashlib.sha256(program).hexdigest().upper(),'program':instructions,
            'operation':'Single-(x*x+y*y)+z*z','nativeValueBytes':12,
            'abi':{'vector':'rcx','returnedScalarLowLane':'xmm0'},
            'generalRegistersWritten':[],'simdRegistersWritten':['xmm0','xmm1','xmm2'],
            'memoryWrites':[],'completeStraightLineReturn':True,'observedValues':False,
            'evidenceBoundary':'Exact complete byte grammar reads three four-byte components from a valid incoming twelve-byte buffer and returns the ordered Single arithmetic in low xmm0. Other general registers and xmm4 are preserved. Actual values, floating environment and caller-buffer identity require separate evidence.'}


def validate_vector3_squared_magnitude_leaf(image: Any, pointer: int, *,
                                          leading_nop: bool = False,
                                          type_name: str = 'UnityEngine.Vector3') -> dict:
    """Join the selected static SqrMagnitude declaration, layout and raw leaf."""
    def require(condition, check, actual):
        if not condition:
            raise ValueError(f'vector3-square.{check}: {str(actual)[:384]}')
    require(type(pointer) is int and 0 < pointer < 1 << 64, 'entry-coordinate', pointer)
    require(type(leading_nop) is bool, 'explicit-nop-mode', leading_nop)
    selected = NativeReferenceContext(image);metadata = image.metadata
    definition = selected.index.types.get(type_name)
    require(definition is not None and definition.generic_container_index < 0
            and selected.parent(type_name) == 'System.ValueType', 'value-owner', type_name)
    fields = [field for field in metadata.fields_for(definition)
              if not selected.field_attributes(field.type_index) & 0x10]
    actual_fields = [(metadata.string(field.name_index), *selected.field(
        type_name+'::'+metadata.string(field.name_index))[1:]) for field in fields]
    require(actual_fields == [('x','float',16),('y','float',20),('z','float',24)],
            'value-fields', actual_fields)
    registration = image.registration
    require(0 <= definition.index < registration['typeDefinitionsSizesCount'],
            'value-size-index', definition.index)
    sizes_pointer = image.pe.u64_at_va(int(registration['typeDefinitionsSizes'],16)+definition.index*8)
    sizes = image.pe.bytes_at_va(sizes_pointer,16) if sizes_pointer else b''
    require(len(sizes)==16 and int.from_bytes(sizes[:4],'little')>=28
            and int.from_bytes(sizes[4:8],'little',signed=True)==12, 'value-size', sizes.hex())
    methods = [method for method in metadata.methods_for(definition)
               if metadata.string(method.name_index)=='SqrMagnitude'
               and method.parameter_count==1 and selected.type_name(method.return_type)=='float'
               and [selected.type_name(p.type_index) for p in metadata.parameters_for(method)]==[type_name]]
    require(len(methods)==1, 'unique-static-declaration', len(methods))
    method = methods[0];parameters = list(metadata.parameters_for(method))
    require(method.declaring_type==definition.index and method.generic_container_index<0
            and method.flags & 0x10 and image.method_pointer_va(method)==pointer,
            'static-method-identity', pointer)
    value_record = image.pe.bytes_at_va(selected.type_pointer(parameters[0].type_index),16)
    require(len(value_record)==16 and value_record[10]==0x11 and not value_record[11]&0x7f
            and int.from_bytes(value_record[:8],'little')==definition.index,
            'undecorated-vector-argument', value_record.hex())
    scalar_record = image.pe.bytes_at_va(selected.type_pointer(method.return_type),16)
    require(len(scalar_record)==16 and scalar_record[10]==0x0c and not scalar_record[11]&0x7f,
            'undecorated-Single-return', scalar_record.hex())
    length = 35 + (2 if leading_nop else 0)
    proof = prove_squared_magnitude_program(image.pe.bytes_at_va(pointer,length),leading_nop=leading_nop)
    return {**proof,'schema':'endfield.vector3-squared-magnitude-leaf-proof.v1',
            'methodIndex':method.index,'typeDefinition':definition.index,
            'method':type_name+'.SqrMagnitude','entryRva':pointer-image.pe.image_base,
            'selectedStaticDeclarationProved':True,'liveMethodInfoIdentityProved':False}

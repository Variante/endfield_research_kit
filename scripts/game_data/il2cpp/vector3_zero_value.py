"""Prove a complete twelve-byte Vector3 zero leaf with a selected declaration."""
from __future__ import annotations

import hashlib
from typing import Any

from .reference_layouts import NativeReferenceContext


def prove_vector3_zero_program(program: bytes) -> dict:
    """Check every byte through RET, including unpack and both output stores."""
    grammar = [('0F57D2', 'clear all XMM2 bits'),
               ('0F57C0', 'clear all XMM0 bits'),
               ('0F14C2', 'interleave zero low lanes in XMM0'),
               ('F20F1101', 'store eight zero bytes through RCX'),
               ('F30F115108', 'store four zero bytes through RCX+8'),
               ('488BC1', 'return incoming output pointer in RAX'),
               ('C3', 'complete leaf return')]
    expected = b''.join(bytes.fromhex(code) for code, _ in grammar)
    if not isinstance(program, bytes) or program != expected:
        raise ValueError('vector3-zero.program: exact complete zero/unpack/8+4-store/return grammar required')
    rows=[];offset=0
    for code, operation in grammar:
        rows.append({'offset':offset, 'rawHex':code, 'operation':operation})
        offset += len(bytes.fromhex(code))
    return {'schema':'endfield.vector3-zero-program-proof.v1', 'programBytes':len(program),
        'programSha256':hashlib.sha256(program).hexdigest().upper(), 'program':rows,
        'abi':{'outputPointer':'rcx', 'returnedOutputPointer':'rax'},
        'outputRawHex':'00'*12, 'nativeValueBytes':12, 'memoryReads':[],
        'memoryWrites':[{'base':'rcx', 'offset':0, 'bytes':8}, {'base':'rcx', 'offset':8, 'bytes':4}],
        'generalRegistersWritten':['rax'], 'simdRegistersWritten':['xmm0','xmm2'],
        'floatingArithmeticOrComparison':False, 'completeStraightLineReturn':True,
        'runtimeExecutionKnown':False,
        'evidenceBoundary':'The complete leaf clears bits, packs zero lanes, writes exactly twelve zero bytes and returns the output pointer. Pointer validity and caller-buffer ownership remain conditions; a folded pointer does not identify a live MethodInfo.'}


def validate_vector3_zero_leaf(image: Any, pointer: int, *, type_name: str = 'UnityEngine.Vector3') -> dict:
    """Join a unique selected static get_zero value signature and complete body.

    The caller authenticates its selected image before and after this check.
    Other logical names may fold onto the same physical entry.
    """
    def require(condition, check, actual):
        if not condition:
            raise ValueError(f'vector3-zero.{check}: {str(actual)[:384]}')
    require(type(pointer) is int and 0 < pointer < 1 << 64, 'entry-coordinate', pointer)
    selected=NativeReferenceContext(image);metadata=image.metadata
    definition=selected.index.types.get(type_name)
    require(definition is not None and definition.generic_container_index < 0
            and selected.parent(type_name)=='System.ValueType', 'value-owner', type_name)
    fields=[f for f in metadata.fields_for(definition) if not selected.field_attributes(f.type_index) & 0x10]
    actual=[(metadata.string(f.name_index), *selected.field(type_name+'::'+metadata.string(f.name_index))[1:]) for f in fields]
    require(actual==[('x','float',16),('y','float',20),('z','float',24)], 'value-fields', actual)
    registration=image.registration
    require(0 <= definition.index < registration['typeDefinitionsSizesCount'], 'value-size-index', definition.index)
    size_pointer=image.pe.u64_at_va(int(registration['typeDefinitionsSizes'],16)+definition.index*8)
    sizes=image.pe.bytes_at_va(size_pointer,16) if size_pointer else b''
    require(len(sizes)==16 and int.from_bytes(sizes[:4],'little')>=28
            and int.from_bytes(sizes[4:8],'little',signed=True)==12, 'value-size', sizes.hex())
    methods=[m for m in metadata.methods_for(definition) if metadata.string(m.name_index)=='get_zero'
             and m.parameter_count==0 and selected.type_name(m.return_type)==type_name]
    require(len(methods)==1, 'unique-static-declaration', len(methods))
    method=methods[0]
    require(method.declaring_type==definition.index and method.generic_container_index<0
            and method.flags & 0x10 and image.method_pointer_va(method)==pointer,
            'static-method-identity', pointer)
    require(not list(metadata.parameters_for(method)), 'no-parameters', method.index)
    value=image.pe.bytes_at_va(selected.type_pointer(method.return_type),16)
    require(len(value)==16 and value[10]==0x11 and not value[11] & 0x7f
            and int.from_bytes(value[:8],'little')==definition.index,
            'undecorated-vector-return', value.hex())
    proof=prove_vector3_zero_program(image.pe.bytes_at_va(pointer,22))
    return {**proof, 'schema':'endfield.vector3-zero-leaf-proof.v1', 'methodIndex':method.index,
        'typeDefinition':definition.index, 'method':type_name+'.get_zero',
        'entryRva':pointer-image.pe.image_base, 'selectedStaticDeclarationProved':True,
        'liveMethodInfoIdentityProved':False}

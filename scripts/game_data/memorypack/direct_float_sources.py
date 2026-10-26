"""Explicit Single source -> preserved XMM6 -> typed instance getter -> field.

This normal-return profile proves a stored operand transfer, conditional on
ordinary Win64 nonvolatile preservation. It does not prove refill, error,
allocation, getter slow paths or execution.
"""
from __future__ import annotations
from typing import Any, Callable
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import setter_output_sources as outputs
from scripts.game_data.memorypack import struct_output_sources as programs

LABEL = 'directFloatSource'


def validate_direct_float_source(image: Any, source: dict, record: dict, member: dict,
        *, fail: Callable) -> dict:
    proof = member.get('directFloatSource') or {}
    assignment = member['assignment']
    if (proof.get('mode') != 'reader-rbx-ref-wrapper-rdi-single-return-through-getter'
            or member['declaredType'] != 'float' or member['kind'] != 'raw-float32-bits'
            or assignment.get('kind') != 'direct-store'
            or (member.get('primitiveSource') or {}).get('mode') != 'single-return'):
        fail('direct-float-scope', 'explicit Single normal-return/getter/direct-field-store profile', proof)
    normal = next(w for w in source['codeWindows'] if w['startRva'] == record['readerMethod'][3])
    programs.check_reader_ref_wrapper_abi(image, record, fail=fail)
    # RDI is a reference to the wrapper until this final dereference; RBX is the reader.
    prefix = proof.get('parentProgram')
    if not isinstance(prefix, list) or not prefix or prefix[0][0] != normal['startRva']:
        fail('direct-float-parent-program', 'complete incoming aliases through final wrapper dereference', prefix)
    args = proof.get('argumentProgram')
    if not isinstance(args, list) or len(args) != 2:
        fail('direct-float-arguments', 'final wrapper dereference and reader argument', args)
    if prefix[-1][0] + len(bytes.fromhex(prefix[-1][1])) != args[0][0]:
        fail('direct-float-parent-extent', args[0][0], prefix[-1])
    programs._check_pointer_aliases(image, normal, prefix, label=LABEL, fail=fail)
    programs._program(image, normal, args, [b'\x48\x8b\x3f', b'\x48\x8b\xcb'], label=LABEL, fail=fail)
    call = member['sourceCall']
    if args[-1][0] + len(bytes.fromhex(args[-1][1])) != call['rva']:
        fail('direct-float-source-order', 'source immediately after declared arguments', call)
    named.check_call(image, call, label=LABEL, fail=fail)
    outputs.validate_primitive_source(image, source, member, fail=fail)
    selected = NativeReferenceContext(image)
    getter = proof['getter']
    outputs._getter(image, record, getter, source, selected, fail)
    getter_call = proof['getterCall']
    named.check_call(image, getter_call, label=LABEL, fail=fail)
    if getter_call['targetRva'] != getter['getterMethod'][3]:
        fail('direct-float-getter-identity', getter['getterMethod'], getter_call)
    owner, declared, offset = selected.field(record['runtimeTypeName'] + '::' + member['fieldName'])
    wanted = b'\xf3\x0f\x11\x70' + bytes((offset,)) if type(offset) is int and 0 <= offset < 128 else None
    if (owner != record['runtimeTypeName'] or declared != 'float' or wanted is None
            or assignment.get('fieldOwnerTypeDefinition') != record['runtimeTypeDefinition']
            or assignment.get('baseRegister') != 0 or assignment.get('fieldOffset') != offset
            or assignment.get('rawHex') != wanted.hex().upper()):
        fail('direct-float-owned-field', [record['runtimeTypeName'], 'float', offset], assignment)
    bridge = proof.get('bridgeProgram')
    if not isinstance(bridge, list) or len(bridge) != 9:
        fail('direct-float-bridge-count', 9, bridge)
    branches = []
    for index in (2, 7):
        raw = bytes.fromhex(bridge[index][1])
        if len(raw) != 6 or raw[:2] != b'\x0f\x84':
            fail('direct-float-null-guard', 'complete JE rel32', bridge[index])
        target = bridge[index][0] + 6 + int.from_bytes(raw[2:], 'little', signed=True)
        if normal['startRva'] <= target < normal['endRva']:
            fail('direct-float-null-target', 'failure target outside selected normal source window', target)
        branches.append(raw)
    getter_bytes = image.pe.bytes_at_va(image.pe.image_base + getter_call['rva'], 5)
    programs._program(image, normal, bridge,
        [b'\x0f\x28\xf0', b'\x48\x85\xff', branches[0], b'\x33\xd2', b'\x48\x8b\xcf',
         getter_bytes, b'\x48\x85\xc0', branches[1], wanted], label=LABEL, fail=fail)
    if (bridge[0][0] != call['rva'] + 5 or bridge[5][0] != getter_call['rva']
            or bridge[-1][0] != assignment['rva']
            or member['sourceToDestinationHex'] != ''.join(row[1] for row in bridge[:-1])):
        fail('direct-float-source-to-store', 'uninterrupted Single result through typed instance getter', bridge)
    return {'storedFloatTransferProved': True, 'evidenceBoundary': 'conditional',
        'condition': 'normal buffered source and getter returns with coherent references and ordinary Win64 XMM6 preservation',
        'runtimeExecutionKnown': False, 'refillOrFailureParityKnown': False}

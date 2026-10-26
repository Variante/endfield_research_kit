"""Owned reference stores followed by one deliberate final wrapper load.

The physical source result is followed through complete null guards to its
declared Data slot. Typed MethodSpec declarations and physical call targets
are separate evidence: this profile does not identify a generic provider or
infer a child's serialized width from its reference store.
"""
from __future__ import annotations

import struct
from typing import Any, Callable
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import reference_output_sources as references
from scripts.game_data.memorypack import setter_output_sources as primitives
from scripts.game_data.memorypack import struct_output_sources as structs

LABEL = 'directDataSource'
MODE = 'reader-rbx-wrapper-ref-rdi-reference-stores-final-dword'


def _dword_definition(image: Any, context: dict, fail: Callable) -> None:
    method = image.metadata.methods[context['methodSpec'][0]]
    section = image.metadata.sections['genericContainers']
    at = section.offset + method.generic_container_index * 16
    if method.generic_container_index < 0 or not section.offset <= at <= section.offset + section.size - 16:
        fail('direct-data-dword-container', 'bounded method container', method.generic_container_index)
    container = struct.unpack_from('<iiii', image.metadata.buf, at)
    pointer = image.pe.u64_at_va(int(image.registration['types'], 16) + method.return_type * 8)
    raw = image.pe.bytes_at_va(pointer, 16)
    if (image.type_name(method.declaring_type) != 'MemoryPack.MemoryPackReader'
            or image.metadata.string(method.name_index) != 'ReadUnmanaged'
            or method.flags & 0x10 or method.parameter_count != 0
            or container[:3] != (method.index, 1, 1)
            or raw[10:12] != b'\x1e\0' or int.from_bytes(raw[:8], 'little') != container[3]):
        fail('direct-data-dword-definition', 'instance ReadUnmanaged<T>() returns its sole MVAR', context)


def _parent(image: Any, normal: dict, record: dict, proof: dict, fail: Callable) -> None:
    structs.check_reader_ref_wrapper_abi(image, record, fail=fail)
    rows = proof.get('parentProgram')
    references._program(image, normal, rows, fail)
    last = record['members'][-1]
    args = last['directDataStore']['argumentProgram']
    dereferences = [row for row in args if row[1] == '488B3F']
    if (len(dereferences) != 1 or rows[0][0] != normal['startRva']
            or rows[-1] != [last['assignment']['rva'], last['assignment']['rawHex']]
            or dereferences[0] not in rows):
        fail('direct-data-parent-extent', 'entry through final store and one final ref-wrapper load', proof)
    seen = set(); aliases = {'rbx': '488BD9', 'rdi': '488BFA'}
    for at, value in rows:
        raw = bytes.fromhex(value)
        decoded = image.mapper.decode_x64_subset(raw, image.pe.image_base + at, stop_offset=len(raw))
        if len(decoded) != 1 or decoded[0]['text'].startswith('db'):
            fail('direct-data-parent-instruction', 'one understood instruction', [at, value, decoded])
        register = (decoded[0].get('write') or {}).get('register')
        if register in {'rbx', 'ebx', 'bx', 'bl', 'bh', 'rdi', 'edi', 'di', 'dil'}:
            if [at, value] == dereferences[0] and seen == set(aliases):
                continue
            if register not in aliases or register in seen or value != aliases[register]:
                fail('direct-data-parent-clobber', aliases, [at, value, register])
            seen.add(register)
        if raw[:1] == b'\xe8' and seen != set(aliases):
            fail('direct-data-parent-late-alias', sorted(aliases), sorted(seen))
    if seen != set(aliases):
        fail('direct-data-parent-aliases', sorted(aliases), sorted(seen))


def _null_branch(normal: dict, row: list, fail: Callable) -> bytes:
    raw = bytes.fromhex(row[1])
    if not (len(raw) == 6 and raw[:2] == b'\x0f\x84' or len(raw) == 2 and raw[:1] == b'\x74'):
        fail('direct-data-null-branch', 'complete JE rel8/rel32', row)
    target = row[0] + len(raw) + int.from_bytes(raw[2:] if len(raw) == 6 else raw[1:], 'little', signed=True)
    if normal['startRva'] <= target < normal['endRva']:
        fail('direct-data-null-target', 'unproved failure path outside normal source window', target)
    return raw


def validate_direct_data_sources(image: Any, source: dict, record: dict, *,
                                 source_string_helpers: list[int], fail: Callable) -> dict:
    proof = record.get('directDataSource') or {}
    members = record['members']
    if (proof.get('mode') != MODE or record.get('inheritedMemberCount') != 0
            or len(members) < 2 or members[-1]['kind'] != 'scalar32'
            or any(m.get('directDataStore', {}).get('mode') != 'reference-return' for m in members[:-1])
            or members[-1].get('directDataStore', {}).get('mode') != 'dword-return'):
        fail('direct-data-scope', 'owned reference stores followed by final DWORD', proof)
    selected = NativeReferenceContext(image)
    owner = record['runtimeTypeName']; wrapper = record['wrapperTypeName']
    if (selected.is_value_type(owner) or selected.is_value_type(wrapper)
            or selected.index.types[owner].index != record['runtimeTypeDefinition']
            or selected.index.types[wrapper].index != record['wrapperTypeDefinition']):
        fail('direct-data-owner-types', 'exact named reference wrapper and Data', [wrapper, owner])
    field_owner, declared, instance = selected.field(wrapper + '::' + proof['instanceFieldName'])
    if field_owner != wrapper or declared != owner or not 0 <= instance < 128:
        fail('direct-data-instance', [wrapper, owner, 'disp8 reference'], [field_owner, declared, instance])
    normal = next(w for w in source['codeWindows'] if w['startRva'] == record['readerMethod'][3])
    _parent(image, normal, record, proof, fail)
    previous = normal['startRva']; results = []
    for ordinal, member in enumerate(members):
        final = ordinal == len(members) - 1
        field = member['fieldName']; transfer = member['directDataStore']
        actual_owner, actual_type, offset = selected.field(owner + '::' + field)
        if actual_owner != owner or actual_type != member['declaredType'] or not 0 <= offset < 128:
            fail('direct-data-field', [owner, field, member['declaredType'], 'disp8'], [actual_owner, actual_type, offset])
        definition = selected.index.types[owner]
        declared_fields = [f for f in image.metadata.fields_for(definition)
                           if image.metadata.string(f.name_index) == field]
        if len(declared_fields) != 1:
            fail('direct-data-declared-field', 'one declared Data field', field)
        raw_type = image.pe.bytes_at_va(selected.type_pointer(declared_fields[0].type_index), 16)
        if (len(raw_type) != 16 or raw_type[11] & 0x7f
                or not final and raw_type[10] not in (0x12, 0x0e)
                or final and actual_type != 'int' and not selected.is_enum(actual_type)):
            fail('direct-data-representation', 'undecorated reference or final DWORD enum/int', raw_type.hex())
        assignment = member['assignment']
        store = (b'\x89\x41' if final else b'\x48\x89\x41') + bytes((offset,))
        if (assignment.get('kind') != 'direct-store' or assignment.get('baseRegister') != 1
                or assignment.get('fieldOwnerTypeDefinition') != record['runtimeTypeDefinition']
                or assignment.get('fieldOffset') != offset or assignment.get('rawHex') != store.hex().upper()):
            fail('direct-data-store', [owner, field, store.hex().upper()], assignment)
        context = next((c for c in source['nestedContexts']
                        if c['instructionRva'] == member.get('sourceContextInstructionRva')), None)
        call = member['sourceCall']
        if final:
            if context is None or (member.get('primitiveSource') or {}).get('mode') != 'scalar32-return':
                fail('direct-data-dword-source', 'closed DWORD with explicit buffered program', member)
            named.check_typed_context(image, context, actual_type, label=LABEL, fail=fail)
            _dword_definition(image, context, fail)
            primitives.validate_primitive_source(image, source, member, fail=fail)
        elif actual_type == 'string':
            if context is not None or call['targetRva'] not in source_string_helpers:
                fail('direct-data-string-source', 'independently validated physical string helper', call)
        else:
            if context is None:
                fail('direct-data-reference-context', 'actual selected typed source context', member)
            named.check_typed_context(image, context, actual_type, label=LABEL, fail=fail)
            references._return_type(image, context, fail)
        args = transfer['argumentProgram']
        reader = b'\x48\x8b\xcb'; load = b'\x48\x8b\x3f' if final else b'\x48\x8b\x37'
        expected_args = [bytes.fromhex(context['instructionHex']), reader, load] if context else [load, reader]
        structs._program(image, normal, args, expected_args, label=LABEL, fail=fail)
        if (args[0][0] < previous or args[-1][0] + len(expected_args[-1]) != call['rva']
                or context is not None and args[0][0] != context['instructionRva']):
            fail('direct-data-argument-order', 'closed context and incoming pointers immediately before source', args)
        named.check_call(image, call, label=LABEL, fail=fail)
        bridge = transfer['bridgeProgram']
        if not isinstance(bridge, list) or len(bridge) != 6:
            fail('direct-data-bridge-count', 'six complete guard/load/store instructions', bridge)
        nulls = [_null_branch(normal, bridge[i], fail) for i in (1, 4)]
        expected = [b'\x48\x85\xff' if final else b'\x48\x85\xf6', nulls[0],
                    (b'\x48\x8b\x4f' if final else b'\x48\x8b\x4e') + bytes((instance,)),
                    b'\x48\x85\xc9', nulls[1], store]
        structs._program(image, normal, bridge, expected, label=LABEL, fail=fail)
        if (bridge[0][0] != call['rva'] + 5 or bridge[-1][0] != assignment['rva']
                or member['sourceToDestinationHex'] != ''.join(row[1] for row in bridge[:-1])):
            fail('direct-data-return-to-store', 'uninterrupted returned bits reach exact owned field', bridge)
        previous = assignment['rva'] + len(store)
        if not final:
            after = transfer['postStoreProgram']; helper = transfer['postStoreCall']
            expected_after = [b'\x48\x83\xc1' + bytes((offset,)),
                              image.pe.bytes_at_va(image.pe.image_base + helper['rva'], 5)]
            structs._program(image, normal, after, expected_after, label=LABEL, fail=fail)
            named.check_call(image, helper, label=LABEL, fail=fail)
            if (after[0][0] != previous or after[1][0] != helper['rva']
                    or helper['targetRva'] != proof['postStoreHelperRva']):
                fail('direct-data-post-store', 'immediate owned slot address and selected physical helper call', after)
            previous = helper['rva'] + 5
        results.append({'fieldName': field, 'declaredType': actual_type,
                        'returnRegister': 'eax' if final else 'rax', 'fieldOffset': offset})
    return {'fields': results, 'evidenceBoundary': 'conditional',
            'condition': 'coherent declared references and ordinary Win64 returning calls; selected buffered DWORD path',
            'typedMethodSpecIdentifiesPhysicalGenericCallee': False,
            'postStoreHelperEffectsProved': False, 'failureOrRefillParityKnown': False,
            'childSchemaAdmitted': False, 'wholeActionAdmitted': False, 'runtimeExecutionKnown': False}

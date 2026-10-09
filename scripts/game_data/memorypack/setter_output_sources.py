"""Reviewed reader outputs carried through generated setters to owned Data.

These profiles prove selected ordinary paths, with explicit Win64 nonvolatile
preservation across calls. A reference transfer has no serialized width;
independent child readers own its grammar. Cold paths and live provider choice
are outside this proof.
"""
from __future__ import annotations

from typing import Any, Callable
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import reference_output_sources as references
from scripts.game_data.memorypack import struct_output_sources as structs

LABEL = 'setterOutputSource'


def _program(image: Any, window: dict, rows: list, expected: list[bytes], fail: Callable) -> None:
    references._program(image, window, rows, fail)
    actual = [bytes.fromhex(r[1]) for r in rows]
    if actual != expected:
        fail('setter-output-program', [v.hex().upper() for v in expected], rows)


def validate_primitive_source(image: Any, source: dict, member: dict, *, fail: Callable) -> None:
    """Check complete ordinary byte/Single reads and explicit cursor accounting.

    Reader is a byref value type. Selected boxed metadata offsets include its
    two-pointer object header; these programs address its unboxed fields.
    The source byte is normalized with TEST/SETNE before reaching AL.
    """
    proof = member['primitiveSource']; rows = proof['program']; mode = proof['mode']
    selected = NativeReferenceContext(image); definition = proof['readerTypeDefinition']
    if image.type_name(definition) != 'MemoryPack.MemoryPackReader' or not selected.is_value_type(image.type_name(definition)):
        fail('setter-primitive-reader-type', 'MemoryPackReader value type', definition)
    offsets = runtime_type_field_offsets(image.metadata, image.pe, image.registration, definition)
    if offsets != proof['readerFieldOffsets']:
        fail('setter-primitive-reader-layout', proof['readerFieldOffsets'], offsets)
    names = ('currentPtr', 'bufferLength', 'advancedCount', 'consumed')
    values = [offsets[name] - 16 for name in names]
    if any(type(n) is not int or not 0 <= n < 128 for n in values) or len(set(values)) != 4:
        fail('setter-primitive-reader-fields', 'four distinct unboxed disp8 fields', values)
    pointer, remaining, advanced, consumed = values
    actual = [bytes.fromhex(r[1]) for r in rows]
    call = member['sourceCall']; window = next(w for w in source['codeWindows'] if w['startRva'] == call['targetRva'])
    if mode == 'normalized-byte-return':
        if len(actual) != 23:
            fail('setter-primitive-count', 23, rows)
        expected = [b'\x48\x89\x5c\x24\x08', b'\x48\x89\x74\x24\x10', b'\x57', b'\x48\x83\xec\x20',
            b'\x83\x79' + bytes((remaining, 1)), b'\x48\x8b\xd9', _branch(actual[6], condition=12, fail=fail),
            b'\x48\x8b\x43' + bytes((pointer,)), b'\x0f\xb6\x30', b'\x8b\x7b' + bytes((remaining,)),
            b'\x83\xef\x01', _branch(actual[11], condition=8, fail=fail), b'\x48\xff\x43' + bytes((pointer,)),
            b'\xff\x43' + bytes((advanced,)), b'\xff\x43' + bytes((consumed,)), b'\x89\x7b' + bytes((remaining,)),
            b'\x48\x8b\x5c\x24\x30', b'\x40\x84\xf6', b'\x48\x8b\x74\x24\x38', b'\x0f\x95\xc0',
            b'\x48\x83\xc4\x20', b'\x5f', b'\xc3']
    elif mode == 'single-return':
        if len(actual) != 22:
            fail('setter-primitive-count', 22, rows)
        expected = [b'\x48\x89\x5c\x24\x08', b'\x57', b'\x48\x83\xec\x30',
            b'\x83\x79' + bytes((remaining, 4)), b'\x48\x8b\xd9', b'\x0f\x29\x74\x24\x20',
            _branch(actual[6], condition=12, fail=fail), b'\x48\x8b\x43' + bytes((pointer,)), b'\xf3\x0f\x10\x30',
            b'\x8b\x7b' + bytes((remaining,)), b'\x83\xef\x04', _branch(actual[11], condition=8, fail=fail),
            b'\x48\x83\x43' + bytes((pointer, 4)), b'\x83\x43' + bytes((advanced, 4)),
            b'\x83\x43' + bytes((consumed, 4)), b'\x89\x7b' + bytes((remaining,)), b'\x48\x8b\x5c\x24\x40',
            b'\x0f\x28\xc6', b'\x0f\x28\x74\x24\x20', b'\x48\x83\xc4\x30', b'\x5f', b'\xc3']
    else:
        fail('setter-primitive-mode', 'explicit byte/Single source', mode)
    _program(image, window, rows, expected, fail)
    if rows[0][0] != call['targetRva']:
        fail('setter-primitive-entry', call['targetRva'], rows[0])


def _branch(raw: bytes, *, condition: int, fail: Callable) -> bytes:
    if not (len(raw) == 6 and raw[:2] == bytes((0x0f, 0x80 + condition))
            or len(raw) == 2 and raw[0] == 0x70 + condition):
        fail('setter-output-branch', f'complete condition {condition} rel8/rel32', raw.hex())
    return raw


def _typed_field(selected: Any, owner: str, name: str, declared: str, fail: Callable) -> int:
    actual_owner, actual_type, offset = selected.field(owner + '::' + name)
    if actual_owner != owner or actual_type != declared or not 0 <= offset < 128:
        fail('setter-output-field', [owner, name, declared, 'disp8'], [actual_owner, actual_type, offset])
    return offset


def _parent(image: Any, normal: dict, record: dict, proof: dict, fail: Callable) -> None:
    """Keep each incoming alias until the deliberate final wrapper load."""
    structs.check_reader_ref_wrapper_abi(image, record, fail=fail)
    rows = proof['parentProgram']; references._program(image, normal, rows, fail)
    last = record['members'][-1]; final = last['setterTransfer']['argumentProgram']
    dereferences = [r for r in final if r[1] == '488B1B']
    if (len(dereferences) != 1 or rows[0][0] != normal['startRva']
            or rows[-1][0] != last['assignment']['rva'] or len(bytes.fromhex(rows[-1][1])) != 5):
        fail('setter-output-parent-extent', 'entry through final setter and one final ref-wrapper dereference', proof)
    seen = set(); aliases = {'rbx': '488BDA', 'rdi': '488BF9'}
    for at, value in rows:
        raw = bytes.fromhex(value)
        decoded = image.mapper.decode_x64_subset(raw, image.pe.image_base + at, stop_offset=len(raw))
        if len(decoded) != 1 or decoded[0]['text'].startswith('db'):
            fail('setter-output-parent-instruction', 'one understood instruction', [at, value, decoded])
        register = (decoded[0].get('write') or {}).get('register')
        if register in {'rbx', 'ebx', 'bx', 'bl', 'bh', 'rdi', 'edi', 'di', 'dil'}:
            if [at, value] == dereferences[0] and seen == set(aliases):
                continue
            if register not in aliases or register in seen or value != aliases[register]:
                fail('setter-output-parent-clobber', aliases, [at, value, register])
            seen.add(register)
        if raw[:1] == b'\xe8' and seen != set(aliases):
            fail('setter-output-parent-late-alias', sorted(aliases), sorted(seen))
    if seen != set(aliases):
        fail('setter-output-parent-aliases', sorted(aliases), sorted(seen))


def _bridge(image: Any, normal: dict, member: dict, *, final: bool, context: dict | None, fail: Callable) -> None:
    proof = member['setterTransfer']; args = proof['argumentProgram']; rows = proof['transferProgram']
    wrapper = b'\x48\x8b\x1b' if final else b'\x48\x8b\x33'
    reader = b'\x48\x8b\xcf'
    expected_args = ([bytes.fromhex(context['instructionHex']), reader, wrapper]
                     if context is not None else [wrapper, reader])
    _program(image, normal, args, expected_args, fail)
    call = member['sourceCall']; named.check_call(image, call, label=LABEL, fail=fail)
    if args[-1][0] + len(expected_args[-1]) != call['rva'] or rows[0][0] != call['rva'] + 5:
        fail('setter-output-source-extent', 'arguments immediately precede read and complete bridge', proof)
    actual = [bytes.fromhex(r[1]) for r in rows]
    if len(actual) != 5:
        fail('setter-output-bridge-count', 5, rows)
    mode = proof['mode']
    move = {'reference-return': b'\x48\x8b\xd0', 'normalized-byte-return': b'\x0f\xb6\xd0',
            'single-return': b'\x0f\x28\xc8', 'int32-return': b'\x8b\xd0'}.get(mode)
    if move is None:
        fail('setter-output-mode', 'reviewed return transfer', mode)
    expected = [b'\x48\x85\xdb' if final else b'\x48\x85\xf6',
                _branch(actual[1], condition=4, fail=fail), b'\x45\x33\xc0', move,
                b'\x48\x8b\xcb' if final else b'\x48\x8b\xce']
    _program(image, normal, rows, expected, fail)
    if (rows[-1][0] + len(expected[-1]) != member['assignment']['rva']
            or b''.join(actual).hex().upper() != member['sourceToDestinationHex']):
        fail('setter-output-assignment-extent', member['assignment'], proof)


def _getter(image: Any, record: dict, proof: dict, source: dict, selected: Any, fail: Callable) -> None:
    method_row = proof['getterMethod']; image.validate_method_row(method_row, label=LABEL)
    method = image.metadata.methods[method_row[0]]
    pointer = selected.type_pointer(method.return_type)
    raw = image.pe.bytes_at_va(pointer, 16)
    if (method_row[1:3] != [record['wrapperTypeName'], 'get___instance'] or method.flags & 0x10
            or method.parameter_count != 0 or raw[10:12] != b'\x12\0'
            or int.from_bytes(raw[:8], 'little') != record['runtimeTypeDefinition']):
        fail('setter-output-getter-type', 'exact reference Data instance getter', method_row)
    parent = selected.parent(record['wrapperTypeName'])
    _owner, base_type, instance = selected.field(parent + '::' + proof['baseInstanceField'])
    if selected.parent(record['runtimeTypeName']) != base_type or not 0 <= instance < 128:
        fail('setter-output-base-instance-type', 'exact immediate base Data and disp8 slot', [base_type, instance])
    cached = _typed_field(selected, record['wrapperTypeName'],
        proof['cachedInstanceField'], record['runtimeTypeName'], fail)
    rows = proof['getterProgram']; window = next(w for w in source['codeWindows'] if w['startRva'] == method_row[3])
    actual = [bytes.fromhex(r[1]) for r in rows]
    if len(actual) != 14:
        fail('setter-output-getter-count', 14, rows)
    if len(actual[2]) != 7 or actual[2][:2] != b'\x80\x3d' or actual[2][-1] != 0:
        fail('setter-output-getter-init', 'bounded native initialization test', rows[2])
    expected = [b'\x40\x53', b'\x48\x83\xec\x20', actual[2], b'\x48\x8b\xd9',
        _branch(actual[4], condition=4, fail=fail), b'\x48\x83\x7b' + bytes((cached, 0)),
        _branch(actual[6], condition=4, fail=fail), b'\x48\x8b\x43' + bytes((instance,)),
        b'\x48\x39\x43' + bytes((cached,)), _branch(actual[9], condition=5, fail=fail),
        b'\x48\x8b\x43' + bytes((cached,)), b'\x48\x83\xc4\x20', b'\x5b', b'\xc3']
    _program(image, window, rows, expected, fail)
    if rows[0][0] != method_row[3]:
        fail('setter-output-getter-entry', method_row[3], rows[0])


def _setter(image: Any, record: dict, member: dict, source: dict, getter: list, selected: Any, fail: Callable) -> None:
    proof = member['setterTransfer']; rows = proof['setterProgram']; call = proof['getterCall']
    method = image.metadata.methods[member['setterMethodIndex']]
    parameters = list(image.metadata.parameters_for(method))
    if (method.declaring_type != record['wrapperTypeDefinition'] or method.flags & 0x10
            or len(parameters) != 1 or selected.type_name(parameters[0].type_index) != member['declaredType']
            or selected.type_name(method.return_type) != 'void'):
        fail('setter-output-setter-type', 'instance void setter with exact declared parameter', member['fieldName'])
    mode = proof['mode']; parameter_raw = image.pe.bytes_at_va(selected.type_pointer(parameters[0].type_index), 16)
    if (mode == 'reference-return' and parameter_raw[10] not in (0x12, 0x0e)
            or mode == 'normalized-byte-return' and member['declaredType'] != 'bool'
            or mode == 'single-return' and member['declaredType'] != 'float'):
        fail('setter-output-parameter-representation', mode, parameter_raw.hex())
    offset = _typed_field(selected, record['runtimeTypeName'], member['fieldName'], member['declaredType'], fail)
    window = next(w for w in source['codeWindows'] if w['startRva'] == member['assignment']['targetRva'])
    if call['targetRva'] != getter[3]:
        fail('setter-output-getter-call', getter, call)
    named.check_call(image, call, label=LABEL, fail=fail)
    actual = [bytes.fromhex(r[1]) for r in rows]
    if mode == 'reference-return':
        count = 12
        if len(actual) != count:
            fail('setter-output-setter-count', count, rows)
        expected = [b'\x40\x53', b'\x48\x83\xec\x20',
            b'\x48\x8b\xda',
            b'\x33\xd2', actual[4], b'\x48\x85\xc0', _branch(actual[6], condition=4, fail=fail)]
        expected += [b'\x48\x8d\x48' + bytes((offset,)), b'\x48\x89\x58' + bytes((offset,)),
                         b'\x48\x83\xc4\x20', b'\x5b', actual[11]]
        if len(actual[11]) != 5 or actual[11][0] != 0xe9:
            fail('setter-output-reference-tail', 'complete tail after owned reference store', rows[11])
    elif mode == 'normalized-byte-return':
        if len(actual) != 11:
            fail('setter-output-setter-count', 11, rows)
        expected = [b'\x40\x53', b'\x48\x83\xec\x20', b'\x0f\xb6\xda', b'\x33\xd2',
            actual[4], b'\x48\x85\xc0', _branch(actual[6], condition=4, fail=fail),
            b'\x88\x58' + bytes((offset,)), b'\x48\x83\xc4\x20', b'\x5b', b'\xc3']
    elif mode == 'single-return':
        if len(actual) != 11:
            fail('setter-output-setter-count', 11, rows)
        expected = [b'\x48\x83\xec\x38', b'\x0f\x29\x74\x24\x20', b'\x33\xd2',
            b'\x0f\x28\xf1', actual[4], b'\x48\x85\xc0', _branch(actual[6], condition=4, fail=fail),
            b'\xf3\x0f\x11\x70' + bytes((offset,)), b'\x0f\x28\x74\x24\x20',
            b'\x48\x83\xc4\x38', b'\xc3']
    else:
        fail('setter-output-mode', 'reviewed setter profile', mode)
    _program(image, window, rows, expected, fail)
    if rows[0][0] != window['startRva'] or rows[4][0] != call['rva']:
        fail('setter-output-setter-entry', 'entry and actual getter call', rows)


def validate_setter_outputs(image: Any, source: dict, record: dict, *, fail: Callable) -> dict:
    """Prove explicit receiver, return-value and typed owned-field transfers."""
    proof = record['setterOutputSource']
    if proof.get('mode') != 'reader-rdi-ref-wrapper-rbx':
        fail('setter-output-parent-mode', 'reviewed incoming ABI profile', proof.get('mode'))
    normal = next(w for w in source['codeWindows'] if w['startRva'] == record['readerMethod'][3])
    image.check_windows(source['codeWindows'], label=LABEL)
    selected = NativeReferenceContext(image)
    _parent(image, normal, record, proof, fail)
    _getter(image, record, proof, source, selected, fail)
    for index, member in enumerate(record['members']):
        context = next((c for c in source['nestedContexts'] if c['instructionRva'] == member.get('sourceContextInstructionRva')), None)
        if context is not None:
            named.check_typed_context(image, context, member['declaredType'], label=LABEL, fail=fail)
            references._return_type(image, context, fail)
        if member['setterTransfer']['mode'] in ('normalized-byte-return', 'single-return'):
            validate_primitive_source(image, source, member, fail=fail)
        _bridge(image, normal, member, final=index == len(record['members'])-1, context=context, fail=fail)
        _setter(image, record, member, source, proof['getterMethod'], selected, fail)
    return {'fieldsForwardedToOwnedData': len(record['members']), 'evidenceBoundary': 'conditional',
        'condition': 'selected normal branches and ordinary returns preserving Win64 nonvolatile registers',
        'liveExecutionKnown': False, 'sourceWireGrammarProvedByThisTransfer': False}

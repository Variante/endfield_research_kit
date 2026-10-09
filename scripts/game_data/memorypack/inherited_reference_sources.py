"""Prove inherited reference-wrapper sources without inventing generic offsets.

This bounded profile covers a key/flag/int/custom-flag wrapper. Closed generic
carriers and metadata-owned VAR ordinals establish field types. Actual setter
programs establish destinations; the generic definition offset table does not.
Only the ordinary buffered source and coherent cached-instance getter path are
proved. Provider, allocation, cast, refill and error execution stay conditional.
"""
from __future__ import annotations

import struct
from typing import Any, Callable

from scripts.game_data.il2cpp.context import type_parameter_owner
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, runtime_type_name
from scripts.game_data.memorypack.wrapper_members import derive_from_image


def _type_row(image: Any, index: int) -> dict[str, Any]:
    pointer = image.pe.u64_at_va(int(image.registration['types'], 16) + index * 8)
    raw = image.pe.bytes_at_va(pointer, 16); kind = raw[10]
    row = {'index': index, 'pointerRva': pointer - image.pe.image_base,
           'rawHex': raw.hex().upper(), 'kind': kind,
           'name': runtime_type_name(image.pe, image.metadata, pointer)}
    if kind in (0x11, 0x12):
        row['definition'] = int.from_bytes(raw[:8], 'little')
    elif kind == 0x15:
        definition, instance = struct.unpack('<QQ', image.pe.bytes_at_va(int.from_bytes(raw[:8], 'little'), 16))
        definition_raw = image.pe.bytes_at_va(definition, 16)
        if definition_raw[10] not in (0x11, 0x12):
            raise ValueError('inheritedReferenceSource.generic-definition-kind')
        inst = image.instantiations.resolve_pointer(instance)
        row.update(definition=int.from_bytes(definition_raw[:8], 'little'),
            definitionRawHex=definition_raw.hex().upper(), instanceIndex=inst.index,
            arguments=[{'pointerRva': a.type_pointer_va - image.pe.image_base,
                        'rawHex': a.raw_type_record_hex,
                        'name': runtime_type_name(image.pe, image.metadata, a.type_pointer_va)} for a in inst.arguments])
    return row


def _ancestry(image: Any, first: int) -> list[dict[str, Any]]:
    result = []; seen = set(); owner = image.metadata.types[first]
    for _ in range(32):
        if owner.index in seen:
            raise ValueError('inheritedReferenceSource.ancestry-cycle')
        seen.add(owner.index)
        parent = None if owner.parent_index < 0 else _type_row(image, owner.parent_index)
        try:
            offsets = runtime_type_field_offsets(image.metadata, image.pe, image.registration, owner.index)
        except RuntimeError:
            offsets = None
        result.append({'definition': owner.index, 'name': image.type_name(owner.index),
            'fields': [{'index': f.index, 'name': image.metadata.string(f.name_index),
                        'type': _type_row(image, f.type_index)} for f in image.metadata.fields_for(owner)],
            'offsets': offsets, 'parent': parent})
        if parent is None or 'definition' not in parent:
            return result
        owner = image.metadata.types[parent['definition']]
    raise ValueError('inheritedReferenceSource.ancestry-depth')


def _program(image: Any, rows: Any, patterns: list[str], *, fail: Callable[..., None]) -> None:
    if (not isinstance(rows, list) or len(rows) != len(patterns)
            or any(not isinstance(r, list) or len(r) != 2 or type(r[0]) is not int
                   or not isinstance(r[1], str) for r in rows)):
        fail('program-shape', len(patterns), rows)
    image.check_instruction_windows(rows, label='inheritedReferenceSource')
    for i, ((at, raw_hex), pattern) in enumerate(zip(rows, patterns, strict=True)):
        raw = bytes.fromhex(raw_hex)
        if i and rows[i - 1][0] + len(bytes.fromhex(rows[i - 1][1])) != at:
            fail('program-contiguity', rows[i - 1], rows[i])
        match = (len(raw) == 5 and raw[0] == 0xE8 if pattern == 'call'
                 else len(raw) == 2 and raw[0] == 0x74 if pattern == 'je8'
                 else len(raw) == 6 and raw[:2] == b'\x0f\x84' if pattern == 'je32'
                 else len(raw) == 6 and raw[:2] == b'\x0f\x8c' if pattern == 'jl32'
                 else len(raw) == 6 and raw[:2] == b'\x0f\x88' if pattern == 'js32'
                 else raw_hex == pattern)
        if not match:
            fail('program-instruction', pattern, rows[i])


def _target(row: list[Any]) -> int:
    at, raw_hex = row; raw = bytes.fromhex(raw_hex)
    width = 1 if len(raw) == 2 else 4
    return at + len(raw) + int.from_bytes(raw[-width:], 'little', signed=True)


def _call(row: list[Any], target: int, *, fail: Callable[..., None]) -> None:
    if bytes.fromhex(row[1])[:1] != b'\xe8' or _target(row) != target:
        fail('call-target', target, row)


def _ancestry_matches(actual: list[dict], expected: list[dict], fail: Callable[..., None]) -> None:
    expected = [{**r, 'offsets': None if 'unresolvedRuntimeOffsets' in r['offsets'] else r['offsets']}
                for r in expected]
    if actual != expected:
        fail('closed-ancestry', expected, actual)


def validate_key_flag_int_flag(image: Any, source: dict[str, Any], record: dict[str, Any],
                              proof: dict[str, Any], *, string_helpers: list[int],
                              fail: Callable[..., None]) -> list[dict[str, str]]:
    """Authenticate one reviewed normal program and its inherited destinations."""
    if proof.get('mode') != 'closed-generic-reference-wrapper':
        fail('profile', 'closed-generic-reference-wrapper', proof.get('mode'))
    image.check_windows(proof['codeWindows'], label='inheritedReferenceSource')
    wrapper = derive_from_image(image).get(record['wrapperTypeDefinition'])
    members = record['members']
    if (wrapper is None or wrapper.name != record['wrapperTypeName'] or wrapper.wrapped_type != record['runtimeTypeName']
            or image.type_name(record['runtimeTypeDefinition']) != record['runtimeTypeName']
            or record['readerMethod'] not in source['methods']
            or len(wrapper.inherited_members) != record['inheritedMemberCount']
            or [(m.name, m.method_index, m.declared_type) for m in wrapper.members] !=
                [(m['fieldName'], m['setterMethodIndex'], m['declaredType']) for m in members]
            or [m['declaredType'] for m in members] != ['string', 'bool', 'int', 'bool']
            or [m['kind'] for m in members] != source['anonymousReadOrder'][record['sourceReadOrder']]
            or [m['kind'] for m in members] != ['byte-payload', 'byte', 'scalar32', 'byte']):
        fail('wrapper-members', record, None if wrapper is None else wrapper.row())
    runtime_owners = _ancestry(image, record['runtimeTypeDefinition'])
    wrapper_owners = _ancestry(image, record['wrapperTypeDefinition'])
    _ancestry_matches(runtime_owners, proof['runtimeAncestry'], fail)
    _ancestry_matches(wrapper_owners, proof['wrapperAncestry'], fail)
    closed_rows = [r['parent'] for r in runtime_owners if r['parent'] and r['parent']['kind'] == 0x15]
    base_slots = [(r, f) for r in wrapper_owners for f in r['fields'] if f['type']['kind'] == 0x15]
    if len(closed_rows) != 1 or len(base_slots) != 1:
        fail('unique-closed-base', [1, 1], [len(closed_rows), len(base_slots)])
    closed = closed_rows[0]; base_owner, base_field = base_slots[0]; wrapped = base_field['type']
    if (bytes.fromhex(closed['rawHex'])[:8] != bytes.fromhex(wrapped['rawHex'])[:8]
            or any(closed[k] != wrapped[k] for k in ('definition', 'instanceIndex', 'arguments'))):
        fail('closed-carrier-and-arguments', closed, wrapped)
    slot = base_owner['offsets'][base_field['name']]
    if not 16 <= slot <= 127:
        fail('base-instance-slot', 'owned reference slot with disp8', slot)
    owner = image.metadata.types[closed['definition']]
    section = image.metadata.sections['genericContainers']
    at = section.offset + owner.generic_container_index * 16
    if owner.generic_container_index < 0 or not section.offset <= at <= section.offset + section.size - 16:
        fail('generic-container-bound', 'owned bounded container', at)
    container = list(struct.unpack_from('<iiii', image.metadata.buf, at))
    if container != proof['genericContainer'] or container[:3] != [owner.index, len(closed['arguments']), 0]:
        fail('generic-container', proof['genericContainer'], container)
    fields = [(r, f) for r in runtime_owners for f in r['fields'] if f['name'] == members[2]['fieldName']]
    if len(fields) != 1 or fields[0][0]['definition'] != owner.index or fields[0][1]['type']['kind'] != 0x13:
        fail('owned-value-VAR', owner.index, fields)
    parameter = int.from_bytes(bytes.fromhex(fields[0][1]['type']['rawHex'])[:8], 'little')
    parameter_owner = type_parameter_owner(image.metadata.buf, parameter,
        [t.generic_container_index for t in image.metadata.types], source='inheritedReferenceSource')
    if parameter_owner != proof['valueParameterOwner'] or parameter_owner['typeIndex'] != owner.index:
        fail('owned-VAR-ordinal', proof['valueParameterOwner'], parameter_owner)
    for i, member in enumerate(members):
        image.validate_method_row(member['setterMethod'], label='inheritedReferenceSource')
        setter = image.metadata.methods[member['setterMethodIndex']]
        if setter.parameter_count != 1 or member['setterMethod'][0] != setter.index or setter.flags & 0x10:
            fail('instance-setter-ABI', 'one instance parameter', member['setterMethod'])
        parameter_type = _type_row(image, image.metadata.parameters[setter.parameter_start].type_index)
        candidates = [(r, f) for r in runtime_owners for f in r['fields'] if f['name'] == member['fieldName']]
        if len(candidates) != 1:
            fail('unique-owned-field', member['fieldName'], candidates)
        field_type = candidates[0][1]['type']
        if i == 2:
            argument = closed['arguments'][parameter_owner['ordinal']]
            if parameter_type['pointerRva'] != argument['pointerRva']:
                fail('concrete-VAR-setter', argument, parameter_type)
        elif field_type['kind'] != parameter_type['kind'] or field_type['name'] != parameter_type['name']:
            fail('field-setter-type', field_type, parameter_type)
        if image.type_name(setter.declaring_type) not in {r['name'] for r in wrapper_owners}:
            fail('setter-ancestry', 'owned wrapper setter', member['setterMethod'])
    layout = proof['readerLayout']
    offsets = runtime_type_field_offsets(image.metadata, image.pe, image.registration, layout['typeDefinition'])
    reader_owner = image.metadata.types[layout['typeDefinition']]
    if (image.type_name(reader_owner.index) != layout['typeName'] or offsets != layout['fieldOffsets']
            or image.metadata.metadata_type_name(reader_owner.parent_index) != 'System.ValueType'):
        fail('reader-value-layout', layout, offsets)
    buffer, remaining, advanced, consumed = [offsets[n] - 16 for n in ('currentPtr', 'bufferLength', 'advancedCount', 'consumed')]
    if any(not 0 <= v <= 127 for v in (buffer, remaining, advanced, consumed)):
        fail('reader-payload-offsets', 'boxed value projection, disp8', offsets)
    b, r, a, c, s = [f'{v:02X}' for v in (buffer, remaining, advanced, consumed, slot)]
    field_offsets = [proof['setterFieldOffsets'][m['fieldName']] for m in members]
    cache_offset = proof['customCacheOffset']
    if any(type(v) is not int or not 16 <= v <= 127 for v in [*field_offsets, cache_offset]):
        fail('setter-store-declarations', 'reviewed disp8 runtime/cache slots', field_offsets)
    key_slot, flag_slot, value_slot, custom_slot, cache_slot = [f'{v:02X}' for v in [*field_offsets, cache_offset]]
    _program(image, proof['readerArgumentProgram'], ['488BFA', '488BD9'], fail=fail)
    for kind, width in (('bool', 1), ('int', 4)):
        helper = proof['primitiveReaders'][kind]
        if helper['width'] != width:
            fail('primitive-source-width', width, helper['width'])
        tail = (['488B5C2430','4084F6','488B742438','0F95C0','4883C420','5F','C3'] if kind == 'bool'
                else ['488B5C2430','8BC6','488B742438','4883C420','5F','C3'])
        increments = ([f'48FF43{b}',f'FF43{a}',f'FF43{c}'] if width == 1
                      else [f'488343{b}04',f'8343{a}04',f'8343{c}04'])
        expected = ['48895C2408','4889742410','57','4883EC20',f'8379{r}{width:02X}',
                    '488BD9','jl32',f'488B43{b}', '0FB630' if width == 1 else '8B30',
                    f'8B7B{r}',f'83EF{width:02X}','js32',*increments,f'897B{r}',*tail]
        _program(image, helper['program'], expected, fail=fail)
        if helper['program'][0][0] != helper['targetRva']:
            fail('primitive-entry', helper['targetRva'], helper['program'][0])
    normal = next(w for w in source['codeWindows'] if w['startRva'] == record['readerMethod'][3])
    source_patterns = [
        ['488B37','488BCB','call','4885F6','je32','4533C0','488BD0','488BCE','call'],
        ['488B37','488BCB','call','4885F6','je32',f'488B4E{s}','4885C9','je32',f'8841{flag_slot}'],
        ['488BCB','488B37','call','4885F6','je32',f'488B4E{s}','4885C9','je8',f'8941{value_slot}'],
        ['488BCB','488B3F','call','4885FF','je8','4533C0','0FB6D0','488BCF','call']]
    previous = normal['startRva']; failures = []
    for i, (member, patterns) in enumerate(zip(members, source_patterns, strict=True)):
        program = member['sourceProgram']; _program(image, program, patterns, fail=fail)
        end = program[-1][0] + len(bytes.fromhex(program[-1][1]))
        if not previous <= program[0][0] < end <= normal['endRva'] or i and program[0][0] != previous:
            fail('source-member-order', [previous, normal['endRva']], program)
        previous = end; source_call = member['sourceCall']
        if source_call['rva'] != program[2][0]:
            fail('source-callsite', source_call, program[2])
        _call(program[2], source_call['targetRva'], fail=fail)
        expected_helper = string_helpers if i == 0 else [proof['primitiveReaders']['int' if i == 2 else 'bool']['targetRva']]
        if source_call['targetRva'] not in expected_helper:
            fail('authenticated-primitive-source', expected_helper, source_call)
        failures.extend(_target(row) for row, pattern in zip(program, patterns) if pattern in ('je8', 'je32'))
        if i in (0, 3):
            _call(program[-1], member['setterMethod'][3], fail=fail)
    if len(set(failures)) != 1 or normal['startRva'] <= failures[0] < normal['endRva']:
        fail('nonnull-source-exit', 'one out-of-normal null failure target', failures)
    # These stores are derived from the concrete emitted setter programs. They
    # deliberately do not consult the generic runtime definition offset table.
    setter_patterns = [
        ['4883EC28',f'488B49{s}','4885C9','je8',f'488951{key_slot}',f'4883C1{key_slot}','4883C428','tail','call','CC'],
        ['4883EC28',f'488B41{s}','4885C0','je8',f'8850{flag_slot}','4883C428','C3','call','CC'],
        ['4883EC28',f'488B41{s}','4885C0','je8',f'8950{value_slot}','4883C428','C3','call','CC'],
        ['4053','4883EC20','0FB6DA','33D2','call','4885C0','je8',f'8858{custom_slot}','4883C420','5B','C3','call','CC']]
    for member, patterns in zip(members, setter_patterns, strict=True):
        program = member['setterProgram']
        if program[0][0] != member['setterMethod'][3]:
            fail('setter-entry', member['setterMethod'], program[0])
        if 'tail' in patterns:
            index = patterns.index('tail')
            raw = bytes.fromhex(program[index][1])
            if len(raw) != 5 or raw[0] != 0xE9:
                fail('reference-writeback-tail', 'E9 tail', program[index])
            patterns = [program[index][1] if p == 'tail' else p for p in patterns]
        _program(image, program, patterns, fail=fail)
    getter = proof['customInstanceGetter']; image.validate_method_row(getter['method'], label='inheritedReferenceSource')
    custom = members[-1]; _call(custom['setterProgram'][4], getter['method'][3], fail=fail)
    custom_owner, custom_field = next((r, f) for r in runtime_owners for f in r['fields'] if f['name'] == custom['fieldName'])
    cache_owner = next(r for r in wrapper_owners if r['name'] == getter['method'][1])
    cache = next(f for f in cache_owner['fields'] if f['name'] == '__realInstance')
    method = image.metadata.methods[getter['method'][0]]
    if (method.parameter_count != 0 or method.flags & 0x10 or _type_row(image, method.return_type) != getter['returnType']
            or cache['type']['definition'] != custom_owner['definition']
            or custom_owner['offsets'][custom_field['name']] != field_offsets[-1]
            or cache_owner['offsets'][cache['name']] != cache_offset
            or getter['returnType']['definition'] != custom_owner['definition']):
        fail('custom-instance-field', 'current concrete runtime and cache slots', [custom_owner, cache_owner])
    # Coherent non-null cache returns the identical underlying base instance.
    main = getter['program']; fragments = getter['ownedFragments']
    image.check_instruction_windows(main, label='inheritedReferenceSource')
    for fragment in fragments: image.check_instruction_windows(fragment['program'], label='inheritedReferenceSource')
    if (len(main) != 7 or main[3][1] != '488BD9' or main[-2][1] != f'48837B{cache_slot}00'
            or bytes.fromhex(main[-1][1])[:2] != b'\x0f\x85'):
        fail('getter-coherent-cache-branch', 'owned instance alias and non-null cache branch', main)
    coherent = next((f['program'] for f in fragments if f['program'][0][0] == _target(main[-1])), None)
    returns = next((f['program'] for f in fragments if f['program'][0][1] == f'488B43{cache_slot}'), None)
    if coherent is None or returns is None:
        fail('getter-owned-return-fragments', 'coherent comparison and return fragments', fragments)
    _program(image, coherent[:2], [f'488B43{s}',f'483943{cache_slot}'], fail=fail)
    if len(coherent) != 4 or bytes.fromhex(coherent[2][1])[:2] != b'\x0f\x84' or _target(coherent[2]) != returns[0][0]:
        fail('getter-identical-base-return', returns, coherent)
    _program(image, returns, [f'488B43{cache_slot}','4883C420','5B','C3'], fail=fail)
    return [{'fieldName': m['fieldName'], 'kind': m['kind']} for m in members]

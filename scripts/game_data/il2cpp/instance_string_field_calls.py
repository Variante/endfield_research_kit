"""Prove an instance's ordered, null/length-guarded String call arguments.

This deliberately narrow Win64 program requires complete instruction boundaries,
an incoming-this alias, a false named patch guard, a named constructor receiver,
and contiguous guarded blocks. Offsets and method pointers come from the selected
metadata. It proves arguments at calls; generic context, callee effects and live
branch selection remain separate obligations.
"""
from __future__ import annotations

import hashlib
from typing import Any

from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.protocol import runtime_type_name

MODE = "ordered-instance-string-fields-to-guarded-reference-calls"


def _require(condition: bool, check: str, expected: Any, actual: Any) -> None:
    if not condition:
        raise ValueError(f"instanceStringFieldCalls.{check}: expected={str(expected)[:600]}; actual={str(actual)[:600]}")


def _raw(row: dict) -> bytes:
    return bytes.fromhex(row['bytes'])


def _at(row: dict) -> int:
    return int(row['va'], 16)


def _branch(row: dict, *, opcode: bytes, target: int | None = None) -> int:
    raw = _raw(row)
    width = 1 if len(opcode) == 1 else 4
    _require(len(raw) == len(opcode) + width and raw.startswith(opcode),
             'branch-opcode', opcode.hex(), row)
    result = _at(row) + len(raw) + int.from_bytes(raw[-width:], 'little', signed=True)
    if target is not None:
        _require(result == target, 'branch-target', hex(target), row)
    return result


def _disp(prefix: bytes, offset: int, suffix: bytes = b'') -> bytes:
    _require(type(offset) is int and 0 <= offset < 128, 'disp8', 'nonnegative disp8', offset)
    return prefix + bytes([offset]) + suffix


def _call(row: dict) -> int:
    raw = _raw(row)
    _require(len(raw) == 5 and raw[0] == 0xe8, 'direct-call', 'E8 rel32', row)
    return _at(row) + 5 + int.from_bytes(raw[1:], 'little', signed=True)


def validate_program(rows: list[dict], *, source_offsets: list[tuple[str, int]],
                     string_length_offset: int, destination_offset: int,
                     guard_pointer: int, constructor_pointer: int, call_pointers: set[int]) -> dict:
    """Check the whole physical body and the selected native field-to-call path."""
    _require(bool(rows) and all(_raw(r) and not r['text'].startswith('db ') for r in rows),
             'decoded-body', 'complete supported instruction boundaries', 'empty or unsupported')
    for a, b in zip(rows, rows[1:]):
        _require(_at(a) + len(_raw(a)) == _at(b), 'contiguity', a, b)
    raw = [_raw(r) for r in rows]
    lookup = {_at(r): i for i, r in enumerate(rows)}
    aliases = [i for i, r in enumerate(raw) if r == b'\x48\x8b\xd9']
    _require(len(aliases) == 1, 'this-alias', 'one MOV RBX, incoming RCX', aliases)
    alias = aliases[0]
    _require(all((r.get('write') or {}).get('register') not in ('rcx', 'ecx', 'cx', 'cl', 'ch')
                 and not r['text'].startswith(('call ', 'j')) for r in rows[:alias]),
             'incoming-this', 'RCX unmodified before its saved alias', rows[:alias])
    guards = [i for i, r in enumerate(rows) if raw[i][:1] == b'\xe8' and _call(r) == guard_pointer]
    _require(len(guards) == 1, 'patch-check', 'one selected direct guard call', guards)
    guard = guards[0]
    _require(alias < guard and raw[guard+1] == b'\x84\xc0', 'patch-result', 'owned alias, TEST AL immediately after call', guard)
    patch = _branch(rows[guard+2], opcode=b'\x0f\x85')
    normal = guard+3
    # The normal allocation/constructor sequence saves and passes the same
    # RAX object in nonvolatile RDI. No allocator meaning is assumed here.
    prefix = raw[normal:normal+8]
    _require(len(prefix) == 8 and len(prefix[0]) == 7 and prefix[0][:3] == b'\x48\x8b\x0d'
             and prefix[2] == b'\x48\x8b\xf8' and prefix[3] == b'\x48\x85\xc0'
             and prefix[5:7] == [b'\x33\xd2', b'\x48\x8b\xc8'],
             'constructor-alias-program', 'class-cell load, call, RDI=RAX, null guard, RCX=RAX, constructor', prefix)
    _call(rows[normal+1])
    failure = _branch(rows[normal+4], opcode=b'\x0f\x84')
    _require(_call(rows[normal+7]) == constructor_pointer, 'constructor-target', hex(constructor_pointer), rows[normal+7])
    # There are eight allocation/constructor instructions, then the first
    # source-field load. Read names and offsets only from independent metadata.
    cursor = normal+8
    blocks = []
    _require(bool(source_offsets) and len(set(source_offsets)) == len(source_offsets),
             'source-fields', 'distinct declared fields', source_offsets)
    contexts = set()
    for field, offset in source_offsets:
        start = cursor
        expected = [_disp(b'\x48\x8b\x43', offset), b'\x48\x85\xc0']
        _require(raw[cursor:cursor+2] == expected, 'typed-source-load', [field, expected], raw[cursor:cursor+2])
        skip = _branch(rows[cursor+2], opcode=b'\x74')
        _require(raw[cursor+3] == _disp(b'\x83\x78', string_length_offset, b'\x00'),
                 'string-length', 'DWORD length compare with zero', rows[cursor+3])
        _branch(rows[cursor+4], opcode=b'\x76', target=skip)
        _require(raw[cursor+5:cursor+7] == [_disp(b'\x48\x8b\x4f', destination_offset), b'\x48\x85\xc9'],
                 'constructor-field-receiver', 'RCX=constructed receiver field, TEST RCX', raw[cursor+5:cursor+7])
        null_row = rows[cursor+7]
        _branch(null_row, opcode=b'\x74' if len(_raw(null_row)) == 2 else b'\x0f\x84', target=failure)
        context = raw[cursor+8]
        _require(len(context) == 7 and context[:3] == b'\x4c\x8b\x05', 'context-argument', 'R8 from actual RIP-relative cell', context.hex())
        cell = _at(rows[cursor+8])+7+int.from_bytes(context[3:], 'little', signed=True)
        contexts.add(cell)
        _require(raw[cursor+9] == b'\x48\x8b\xd0', 'string-argument', 'RDX=unchanged field reference in RAX', rows[cursor+9])
        pointer = _call(rows[cursor+10])
        _require(pointer in call_pointers, 'reference-call-target', sorted(call_pointers), hex(pointer))
        cursor += 11
        _require(skip == _at(rows[cursor]), 'guarded-block-end', 'both skip branches reach next field block', hex(skip))
        blocks.append({'field': field, 'fieldOffset': offset, 'startVa': _at(rows[start]),
            'endVa': _at(rows[cursor]), 'callVa': _at(rows[cursor-1]), 'targetVa': pointer,
            'stringArgumentRegister': 'rdx', 'destinationReceiverRegister': 'rcx',
            'contextCellVa': cell, 'nullOrZeroUnsignedLengthSkipsCall': True})
    _require(len(contexts) == 1 and len({b['targetVa'] for b in blocks}) == 1,
             'shared-call', 'one physical callee and one context cell', [contexts, blocks])
    _require(raw[cursor] == b'\x48\x8b\xc7', 'returned-constructor-alias', 'RAX=RDI', rows[cursor])
    epilogue = _branch(rows[cursor+1], opcode=b'\xeb')
    _require(patch == _at(rows[cursor+2]), 'patch-excludes-normal-path', 'patched edge after normal return jump', hex(patch))
    _require(epilogue in lookup and failure in lookup, 'owned-destinations', 'owned failure and return entries', [failure, epilogue])
    ep = lookup[epilogue]
    _require(raw[ep:] == [b'\x48\x8b\x5c\x24\x30', b'\x48\x83\xc4\x20', b'\x5f', b'\xc3'],
             'epilogue', 'complete nonvolatile restore and RET', raw[ep:])
    fi = lookup[failure]
    _call(rows[fi])
    _require(raw[fi+1] == b'\xcc', 'failure-entry', 'direct call followed by INT3', rows[fi:fi+2])
    # Prove that the incoming-this nonvolatile alias cannot be silently
    # overwritten before or between the loads. The typed field name alone is
    # insufficient. Calls preserve RBX/RDI under the stated Win64 condition.
    for i in range(alias+1, cursor+1):
        write = rows[i].get('write') or {}
        _require(write.get('register') not in ('rbx', 'ebx', 'bx', 'bl', 'bh'),
                 'this-alias-preserved', 'RBX unchanged until normal return', rows[i])
        if i > normal+2:
            _require(write.get('register') not in ('rdi', 'edi', 'di', 'dil'),
                     'constructed-alias-preserved', 'RDI unchanged after constructor alias', rows[i])
    # Every direct branch entering the selected blocks must be one of their
    # own two skips to the next block. No unguarded alternate entry is admitted.
    first, end = _at(rows[normal]), _at(rows[cursor])
    legal_edges = {(b['startVa'], b['endVa']) for b in blocks}
    for i, row in enumerate(rows):
        b = raw[i]
        _require(not row['text'].startswith('jmp ') or (len(b) == 2 and b[0] == 0xeb)
                 or (len(b) == 5 and b[0] == 0xe9), 'direct-control', 'direct owned JMP only', row)
        if len(b) == 2 and (0x70 <= b[0] <= 0x7f or b[0] == 0xeb):
            target = _at(row)+2+int.from_bytes(b[1:], 'little', signed=True)
        elif len(b) == 6 and b[0] == 0x0f and 0x80 <= b[1] <= 0x8f:
            target = _at(row)+6+int.from_bytes(b[2:], 'little', signed=True)
        elif len(b) == 5 and b[0] == 0xe9:
            target = _at(row)+5+int.from_bytes(b[1:], 'little', signed=True)
        else:
            continue
        if first <= target < end:
            containing = next((block for block in blocks if block['startVa'] <= _at(row) < block['endVa']), None)
            _require(containing is not None and (containing['startVa'], target) in legal_edges
                     and b[0] in (0x74, 0x76), 'guard-dominance', 'owned skips only, no bypass entry', row)
    return {'blocks': blocks, 'patchCheckVa': _at(rows[guard]), 'patchResultCondition': False,
            'returnVa': _at(rows[cursor]), 'constructedReceiverAlias': 'rdi',
            'sourceThisAlias': 'rbx', 'calleeEffectProved': False,
            'liveGenericContextSelected': False, 'runtimeExecutionKnown': False}


def _type(image: Any, type_index: int) -> tuple[int, str, bool]:
    _require(type(type_index) is int and 0 <= type_index < image.registration['typesCount'],
             'registered-type-index', 'selected registration type', type_index)
    pointer = image.pe.u64_at_va(int(image.registration['types'], 16)+type_index*8)
    raw = image.pe.bytes_at_va(pointer, 16)
    return raw[10], runtime_type_name(image.pe, image.metadata, pointer), bool(raw[11] & 0x20)


def _instance_field_type(image: Any, type_index: int) -> tuple[int, str, bool]:
    result = _type(image, type_index)
    pointer = image.pe.u64_at_va(int(image.registration['types'], 16)+type_index*8)
    attributes = int.from_bytes(image.pe.bytes_at_va(pointer, 16)[8:10], 'little')
    _require(not attributes & 0x10, 'instance-field-attributes', 'nonstatic field', attributes)
    return result


def _reference_call_targets(index: BodyIndex, callee: str, *, declaring_type: int | None = None) -> set[int]:
    """Select Add(T) definitions; shared names never stand in for a signature."""
    image = index.image
    selected = set()
    for target in index.pointers_by_name.get(callee, ()):
        definitions = [r.get('methodIndex') for r in index.names_by_pointer[target]
                       if f"{r.get('type')}.{r.get('method')}" == callee]
        if not definitions or not all(type(i) is int and 0 <= i < len(image.metadata.methods) for i in definitions):
            continue
        valid = True
        for i in definitions:
            definition = image.metadata.methods[i]
            params = image.metadata.parameters_for(definition)
            if ((declaring_type is not None and definition.declaring_type != declaring_type)
                    or definition.flags & 0x10 or definition.generic_container_index >= 0
                    or _type(image, definition.return_type) != (1, 'void', False)
                    or len(params) != 1 or _type(image, params[0].type_index)[0] != 0x13
                    or _type(image, params[0].type_index)[2]):
                valid = False
                break
        if valid:
            selected.add(target)
    return selected


def _owner(image: Any, name: str, *, assembly: str | None = None):
    candidates = [t for t in image.metadata.types if image.type_name(t.index) == name]
    if assembly is not None:
        candidates = [t for t in candidates if image.metadata.string(
            image.metadata.images[image.owners[t.index]].name_index) == assembly]
    _require(len(candidates) == 1, 'type-owner', {'type': name, 'image': assembly},
             [t.index for t in candidates])
    return candidates[0]


def _generic_definition(image: Any, type_index: int) -> int:
    pointer = image.pe.u64_at_va(int(image.registration['types'], 16)+type_index*8)
    raw = image.pe.bytes_at_va(pointer, 16)
    _require(raw[10] == 0x15, 'generic-field-type', 'closed generic instance', raw.hex())
    definition_pointer = int.from_bytes(image.pe.bytes_at_va(int.from_bytes(raw[:8], 'little'), 16)[:8], 'little')
    definition = image.pe.bytes_at_va(definition_pointer, 16)
    result = int.from_bytes(definition[:8], 'little')
    _require(definition[10] == 0x12 and 0 <= result < len(image.metadata.types),
             'generic-definition', 'actual generic class definition identity', definition.hex())
    return result


def prove(index: BodyIndex, claim: dict) -> dict:
    """Resolve named definitions afresh, then check the reviewed program shape."""
    _require(claim.get('mode') == MODE, 'claim-mode', MODE, claim.get('mode'))
    image = index.image
    owner = _owner(image, claim['type'])
    _require(_type(image, owner.byval_type_index) == (0x12, claim['type'], False),
             'reference-this-type', 'declared nongeneric class receiver', owner.index)
    methods = [m for m in image.metadata.methods_for(owner)
               if image.metadata.string(m.name_index) == claim['method']]
    _require(len(methods) == 1, 'method-definition', 'one named definition', len(methods))
    method = methods[0]
    _require(not method.flags & 0x10 and method.generic_container_index < 0
             and not image.metadata.parameters_for(method) and _type(image, method.return_type) == (0x1c, 'object', False),
             'typed-entry', 'nongeneric reference-instance/no-argument object return', method.index)
    pointer = image.method_pointer_va(method)
    _require(pointer in index.extents and not index.chained_fragments.get(pointer),
             'exact-unwind', 'one exact primary unwind-owned body', hex(pointer))
    size = index.extents[pointer]-pointer
    _require(0 < size <= 4096, 'bounded-body', 'positive bounded primary body', size)
    rows = index._decode(pointer, size)
    _require(sum(len(_raw(r)) for r in rows) == size, 'full-body-coverage', size, len(rows))
    fields = {image.metadata.string(f.name_index): f for f in image.metadata.fields_for(owner)}
    offsets = []
    for name in claim['fields']:
        _require(name in fields and _instance_field_type(image, fields[name].type_index) == (0x0e, 'string', False),
                 'declared-string', name, None if name not in fields else _type(image, fields[name].type_index))
        offsets.append((name, index.field_offset(claim['type']+'::'+name)))
    string_field = next(f for f in image.metadata.fields_for(_owner(image, 'System.String'))
                        if image.metadata.string(f.name_index) == claim['lengthField'])
    _require(_instance_field_type(image, string_field.type_index) == (0x08, 'int', False), 'string-length-type', 'Int32', string_field.type_index)
    destination = claim['destination']
    dest_owner = _owner(image, destination['type'])
    _require(_type(image, dest_owner.byval_type_index) == (0x12, destination['type'], False),
             'reference-constructor-type', 'declared nongeneric class receiver', dest_owner.index)
    dest_field = next(f for f in image.metadata.fields_for(dest_owner)
                      if image.metadata.string(f.name_index) == destination['field'])
    _require(_instance_field_type(image, dest_field.type_index) == (0x15, destination['declaredType'], False),
             'destination-type', destination['declaredType'], _type(image, dest_field.type_index))
    ctor = [m for m in image.metadata.methods_for(dest_owner)
            if image.metadata.string(m.name_index) == '.ctor' and not image.metadata.parameters_for(m)]
    _require(len(ctor) == 1 and not ctor[0].flags & 0x10 and _type(image, ctor[0].return_type) == (1, 'void', False),
             'constructor-definition', 'one parameterless instance constructor', len(ctor))
    guard = claim['guard']
    _require(isinstance(guard.get('image'), str) and bool(guard['image']), 'guard-image', 'explicit owning assembly', guard)
    guards = [m for m in image.metadata.methods_for(_owner(image, guard['type'], assembly=guard['image']))
              if image.metadata.string(m.name_index) == guard['method']]
    _require(len(guards) == 1 and guards[0].flags & 0x10 and _type(image, guards[0].return_type) == (2, 'bool', False)
             and [_type(image, p.type_index) for p in image.metadata.parameters_for(guards[0])] == [(8, 'int', False)],
             'guard-signature', 'static Boolean(Int32)', len(guards))
    callee = claim['callee']['type']+'.'+claim['callee']['method']
    targets = set(index.pointers_by_name.get(callee, ()))
    _require(bool(targets), 'callee-definition', callee, targets)
    callee_definition = _generic_definition(image, dest_field.type_index)
    _require(image.type_name(callee_definition) == claim['callee']['type'],
             'callee-field-owner', 'same native generic class definition as the destination field', callee_definition)
    selected_targets = _reference_call_targets(index, callee, declaring_type=callee_definition)
    _require(bool(selected_targets), 'generic-reference-call-signature', 'instance void Add(T), by-value generic parameter', callee)
    result = validate_program(rows, source_offsets=offsets,
        string_length_offset=index.field_offset('System.String::'+claim['lengthField']),
        destination_offset=index.field_offset(destination['type']+'::'+destination['field']),
        guard_pointer=image.method_pointer_va(guards[0]), constructor_pointer=image.method_pointer_va(ctor[0]),
        call_pointers=selected_targets)
    result.update(method=[method.index, claim['type'], claim['method'], pointer-image.pe.image_base],
        codeWindow={'startRva': pointer-image.pe.image_base, 'endRva': pointer+size-image.pe.image_base,
                    'sha256': hashlib.sha256(image.pe.bytes_at_va(pointer, size)).hexdigest().upper()},
        destination=destination, lengthField='System.String::'+claim['lengthField'],
        guardImage=guard['image'], guardMethod=[guards[0].index, guard['type'], guard['method'],
                                             image.method_pointer_va(guards[0])-image.pe.image_base],
        calleeClassDefinition=callee_definition,
        declaredStringFieldsProved=True, nativeBranchFieldToArgumentFlowProved=True,
        calleeStaticAliases=index.names_of(result['blocks'][0]['targetVa']),
        condition='Coherent declared instances, ordinary returning Win64 calls and false patch check',
        evidenceBoundary='conditional')
    return result

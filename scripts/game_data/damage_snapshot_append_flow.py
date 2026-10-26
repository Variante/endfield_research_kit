"""Check a snapshot producer's simple-value transfer into an append request.

The compiled helper target is not equated with a registered generic Add entry.
Only a selected straight-line fragment is proved, under its explicit incoming
register, live-context and normal-call conditions. No list mutation follows.
"""
from __future__ import annotations

from scripts.game_data.damage_snapshot_abi import (require_ordinary_type, require_ordinary_signature, require_ordinary_pointer, require_ordinary_field, require_ordinary_value_type, require_ordinary_type_var)

import re
import struct

from scripts.game_data.damage_snapshot_cache_flow import _address, _require
from scripts.game_data.il2cpp.context import (
    method_spec_record, method_spec_usage_index, relative_branch_target,
    rip_qword_load_target, type_parameter_owner,
)
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.stack_argument_flow import _edge


def check_simple_append_program(rows, *, start, cache_offset, simple_offset,
                                scale_offset, blackboard_pointer, value_pointer,
                                attack_pointer, append_pointer):
    """Check the chosen true-simpleCalculation, nonnull-cache fallthrough.

    Incoming RDI is the action, RBX its selected unit, RBP the chosen attribute
    source and R13B zero. Those fragment-entry roles are conditions, not a proof
    of the complete producer loop or its enclosing guards.
    """
    positions = {_address(row): n for n, row in enumerate(rows)}
    _require(start in positions, 'append-start', 'instruction boundary', hex(start))
    for value in (cache_offset, simple_offset, scale_offset):
        _require(type(value) is int and 0 <= value < 128, 'append-field-offset', 'positive disp8', value)
    expected = [
        ('xor edx, edx', b'\x33\xd2'), ('mov rcx, rdi', b'\x48\x8b\xcf'),
        (f'cmp [rbx+{simple_offset:#x}], r13b', b'\x44\x38\x6b' + bytes([simple_offset])),
        ('branch-simple', b'\x0f\x84'),
        (f'mov rbx, [rbx+{scale_offset:#x}]', b'\x48\x8b\x5b' + bytes([scale_offset])),
        (f'call {blackboard_pointer:#x}', 'call'), ('xor r8d, r8d', b'\x45\x33\xc0'),
        ('mov rdx, rax', b'\x48\x8b\xd0'), ('mov rcx, rbx', b'\x48\x8b\xcb'),
        (f'call {value_pointer:#x}', 'call'),
        (f'mov rbx, [rdi+{cache_offset:#x}]', b'\x48\x8b\x5f' + bytes([cache_offset])),
        ('xor edx, edx', b'\x33\xd2'), ('mov rcx, rbp', b'\x48\x8b\xcd'),
        ('movaps xmm6, xmm0', b'\x0f\x28\xf0'), (f'call {attack_pointer:#x}', 'call'),
        ('test rbx, rbx', b'\x48\x85\xdb'), ('branch-cache', b'\x74'),
        ('xorps xmm1, xmm1', b'\x0f\x57\xc9'), ('mov rcx, rbx', b'\x48\x8b\xcb'),
        ('cvtss2sd xmm1, xmm6', b'\xf3\x0f\x5a\xce'),
        ('mulsd xmm1, xmm0', b'\xf2\x0f\x59\xc8'), ('usage-load', b'\x4c\x8b\x05'),
        (f'call {append_pointer:#x}', 'call'), ('branch-continuation', b'\xe9'),
    ]
    selected = rows[positions[start]:positions[start] + len(expected)]
    _require(len(selected) == len(expected), 'append-program-length', len(expected), len(selected))
    address = start; edges = {}
    for row, (text, encoding) in zip(selected, expected):
        _require(_address(row) == address, 'append-contiguity', hex(address), row['va'])
        raw = bytes.fromhex(row['bytes'])
        if text.startswith('branch-'):
            edge = _edge(row)
            _require(edge is not None and raw.startswith(encoding), 'append-edge-condition', encoding.hex(), raw.hex())
            _require(re.fullmatch(r'j(?:cc|e|mp) 0x[0-9a-f]+', row['text']) is not None
                     and int(row['text'].split()[1], 16) == edge[0], 'append-edge-text', edge, row['text'])
            edges[text] = edge[0]
        elif text == 'usage-load':
            target = rip_qword_load_target(raw, address, source='damageSnapshotAppend')
            _require(raw.startswith(encoding) and row['text'].startswith('mov r8, [rip')
                     and row['text'].endswith(f'=> {target:#x}]'), 'append-usage-load', hex(target), row)
        else:
            _require(row['text'] == text, 'append-instruction', text, row['text'])
            if encoding == 'call':
                target = relative_branch_target(raw, address, source='damageSnapshotAppend')
                _require(raw[0] == 0xe8 and target == int(text.split()[1], 16), 'append-call-target', text, hex(target))
            else:
                _require(raw == encoding, 'append-encoding', encoding.hex(), raw.hex())
        address += len(raw)
    for name, target in edges.items():
        _require(not start <= target < address, 'append-external-edge', 'outside selected fragment', [name, hex(target)])
    return {'fragmentEntry': hex(start), 'selectedInstructionCount': len(selected),
            'appendCall': selected[22]['va'], 'compiledAppendTarget': hex(append_pointer),
            'usageLoad': selected[21], 'continuation': hex(edges['branch-continuation']),
            'excludedTargets': [hex(edges['branch-simple']), hex(edges['branch-cache'])],
            'scalarExpression': 'Double(resolved Single atkScale) * Double(selected source get_atk)',
            'receiverRegister': 'rcx', 'valueRegister': 'xmm1'}


def _check_named_provider(index, pointer, symbol, parameters, result, *, is_static):
    selected = NativeReferenceContext(index.image, index=index)
    matches = [row for row in index.names_by_pointer.get(pointer, ())
               if f"{row.get('type')}.{row.get('method')}" == symbol]
    _require(bool(matches), 'append-provider-identity', symbol, hex(pointer))
    for row in matches:
        method = index.metadata.methods[row['methodIndex']]
        actual = [selected.type_name(p.type_index) for p in index.metadata.parameters_for(method)]
        _require(bool(method.flags & 0x10) == is_static and actual == parameters
                 and selected.type_name(method.return_type) == result,
                 'append-provider-signature', [parameters, result], [actual, selected.type_name(method.return_type)])
        require_ordinary_signature(selected, method, parameters, result, symbol)


def check_simple_append(index, spec):
    body = index.body(spec['type'], spec['method'])
    selected = NativeReferenceContext(index.image, index=index)
    cache_owner, cache_type, cache_offset = selected.field(spec['cacheField'])
    unit_owner, simple_type, simple_offset = selected.field(spec['simpleField'])
    scale_owner, scale_type, scale_offset = selected.field(spec['scaleField'])
    _require(cache_owner == spec['type'] and cache_type == 'System.Collections.Generic.List`1<double>',
             'append-cache-type', [spec['type'], 'List<double>'], [cache_owner, cache_type])
    _require(unit_owner == scale_owner == spec['unitType'] and simple_type == 'bool'
             and scale_type == 'Beyond.Blackboard+BlackboardDouble',
             'append-unit-fields', [spec['unitType'], 'bool', 'Beyond.Blackboard+BlackboardDouble'],
             [unit_owner, scale_owner, simple_type, scale_type])
    require_ordinary_field(selected,spec['cacheField'],cache_type,'append.cacheField')
    require_ordinary_field(selected,spec['simpleField'],'bool','append.simpleField')
    require_ordinary_field(selected,spec['scaleField'],scale_type,'append.scaleField')
    candidates = [n - 2 for n, row in enumerate(body.rows)
                  if row['text'] == f'cmp [rbx+{simple_offset:#x}], r13b' and n >= 2]
    _require(len(candidates) == 1, 'append-fragment-selection', 'one simple branch', len(candidates))
    fragment = body.rows[candidates[0]:]
    _require(len(fragment) >= 24, 'append-fragment-extent', 'at least 24 complete instructions', len(fragment))
    pointers = [int(fragment[n]['text'].split()[1], 16) for n in (5, 9, 14, 22)
                if re.fullmatch(r'call 0x[0-9a-f]+', fragment[n]['text'])]
    _require(len(pointers) == 4, 'append-provider-calls', 'four direct calls', pointers)
    blackboard, value, attack, append = pointers
    _check_named_provider(index, blackboard, spec['blackboardGetter'], [], 'Beyond.ActionBlackboard', is_static=False)
    _check_named_provider(index, value, spec['scalarGetter'],
                          [scale_type, 'Beyond.ActionBlackboard'], 'float', is_static=True)
    _check_named_provider(index, attack, spec['attackGetter'], [], 'double', is_static=False)
    proof = check_simple_append_program(body.rows, start=_address(fragment[0]),
        cache_offset=cache_offset, simple_offset=simple_offset, scale_offset=scale_offset,
        blackboard_pointer=blackboard, value_pointer=value, attack_pointer=attack, append_pointer=append)
    usage = proof.pop('usageLoad')
    cell = rip_qword_load_target(bytes.fromhex(usage['bytes']), _address(usage), source='damageSnapshotAppend')
    registration = index.image.registration
    spec_index = method_spec_usage_index(index.pe.bytes_at_va(cell, 8), registration['methodSpecsCount'],
                                        source='damageSnapshotAppend', offset=cell)
    spec_va = int(registration['methodSpecs'], 16) + spec_index * 12
    definition, class_inst, method_inst = method_spec_record(index.pe.bytes_at_va(spec_va, 12),
        len(index.metadata.methods), registration['genericInstsCount'], source='damageSnapshotAppend', offset=spec_va)
    method = index.metadata.methods[definition]
    method_owner = index.metadata.type_full_name(index.metadata.types[method.declaring_type])
    arguments = [runtime_type_name(index.pe, index.metadata, arg.type_pointer_va)
                 for arg in index.image.instantiations.resolve(class_inst).arguments]
    _require(method_owner == 'System.Collections.Generic.List`1'
             and index.metadata.string(method.name_index) == 'Add' and not method.flags & 0x10
             and selected.type_name(method.return_type) == 'void'
             and arguments == ['double'] and method_inst == -1,
             'append-method-spec', 'instance void List<Double>.Add', [method_owner, arguments, method_inst])
    require_ordinary_type(selected, method.return_type, 'void', 'append.return')
    for arg in index.image.instantiations.resolve(class_inst).arguments:
        require_ordinary_pointer(selected, arg.type_pointer_va, runtime_type_name(index.pe, index.metadata, arg.type_pointer_va), 'double', 'append.classArg0')
    parameters = index.metadata.parameters_for(method)
    _require(len(parameters) == 1, 'append-parameter-count', 1, len(parameters))
    record = index.pe.bytes_at_va(selected.type_pointer(parameters[0].type_index), 16)
    _require(record[10] == 0x13 and record[11] == 0, 'append-generic-parameter', 'ordinary type VAR', record.hex())
    owner = type_parameter_owner(index.metadata.buf, struct.unpack_from('<Q', record)[0],
        [td.generic_container_index for td in index.metadata.types], source='damageSnapshotAppend')
    _require(owner['typeIndex'] == method.declaring_type and owner['ordinal'] == 0,
             'append-generic-parameter-owner', [method.declaring_type, 0], [owner['typeIndex'], owner['ordinal']])
    registered = sorted({pointer for pointer, aliases in index.names_by_pointer.items()
                         if any(row.get('methodSpecIndex') == spec_index for row in aliases)})
    return {**proof, 'symbol': body.symbol, 'claim': 'snapshotSimpleValueToAppendRequest',
            'cacheField': spec['cacheField'], 'cacheType': cache_type,
            'appendUsageCell': hex(cell), 'appendMethodSpecIndex': spec_index,
            'registeredAddEntries': [hex(pointer) for pointer in registered],
            'compiledTargetIsRegisteredAddEntry': append in registered,
            'fragmentEntryConditions': {'rdi': spec['type'], 'rbx': spec['unitType'],
                                        'rbp': 'selected AbilitySystem source', 'r13b': 0},
            'listMutationProved': False, 'producerConsumerIndexJoinProved': False,
            'boundary': 'The selected simple branch passes the stored scale and action Blackboard to the Single getter, preserves its result across the normally returning Double attack getter, widens/multiplies it, and sends the Double in XMM1 with the same action cache in RCX and static List<Double>.Add MethodSpec in R8 to the compiled helper. Fragment-entry roles, provider behavior, resolved live contexts and Win64 preservation are conditions; compiled helper semantics, cache mutation/order and consumer index correspondence remain unproved.'}

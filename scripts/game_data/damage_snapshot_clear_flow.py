"""Check the producer entry's guarded, incoming-this cache reset program.

Selection carrier reads remain opaque. Only the target return ABI, entry alias,
zero source and physical anonymous stores are admitted; selector behavior and
closed generic List layout are not inferred.
"""
from __future__ import annotations

from scripts.game_data.damage_snapshot_abi import (require_ordinary_type, require_ordinary_signature, require_ordinary_pointer, require_ordinary_field, require_ordinary_value_type, require_ordinary_type_var)

import re

from scripts.game_data.damage_snapshot_cache_flow import _address, _require
from scripts.game_data.il2cpp.context import relative_branch_target
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.reference_result_flow import named_reference_type
from scripts.game_data.il2cpp.stack_argument_flow import _edge


def check_clear_program(rows, *, pointer, end, cache_offset, opaque_offsets, slots, calls):
    offsets = [cache_offset, opaque_offsets['reference'], opaque_offsets['selectorDword'],
               slots['counterDword'], slots['countDword']]
    _require(all(type(value) is int and 0 <= value < 128 for value in offsets),
             'snapshot-clear-displacements', 'positive disp8 declarations', offsets)
    cache, reference, selector, counter, count = offsets
    expected = [
        b'\x48\x89\x5c\x24\x08', b'\x48\x89\x6c\x24\x10', b'\x48\x89\x74\x24\x18',
        b'\x57', b'\x41\x54', b'\x41\x55', b'\x41\x56', b'\x41\x57',
        b'\x48\x83\xec\x70', b'\x48\x8b\xf9', b'\x0f\x29\x74\x24\x60', 'guard-index',
        b'\x33\xd2', ('call', calls['patch']), b'\x84\xc0', ('edge', b'\x0f\x85', 'patch'),
        b'\x48\x8b\x47' + bytes([reference]), b'\x48\x85\xc0', ('edge', b'\x0f\x84', 'carrier'),
        b'\x8b\x70' + bytes([selector]), b'\x33\xd2', b'\x48\x8b\xcf', ('call', calls['owner']),
        b'\x48\x85\xc0', ('edge', b'\x0f\x84', 'owner'), b'\x33\xd2', b'\x48\x8b\xc8',
        ('call', calls['handle']), b'\x33\xd2', b'\x48\x8b\xcf', b'\x48\x8b\xd8', ('call', calls['owner']),
        b'\x45\x33\xed', b'\x4c\x8b\xc8', b'\x4c\x89\x6c\x24\x28', b'\x4c\x8b\xc3',
        b'\x8b\xd6', b'\x4c\x89\x6c\x24\x20', b'\x48\x8b\xcf', ('call', calls['target']),
        b'\x48\x8b\xe8', b'\x48\x85\xc0', ('edge', b'\x0f\x84', 'target'),
        b'\x48\x8b\x57' + bytes([cache]), b'\x48\x85\xd2', ('edge', b'\x0f\x84', 'cache'),
        b'\xff\x42' + bytes([counter]), b'\x44\x89\x6a' + bytes([count]),
    ]
    _require(len(rows) >= len(expected), 'snapshot-clear-length', len(expected), len(rows))
    address = pointer; edges = {}
    for row, encoding in zip(rows, expected):
        raw = bytes.fromhex(row['bytes'])
        _require(_address(row) == address and address + len(raw) <= end,
                 'snapshot-clear-contiguity', hex(address), row['va'])
        if encoding == 'guard-index':
            _require(len(raw) == 5 and raw[:1] == b'\xb9', 'snapshot-clear-guard-index', 'MOV ECX imm32', raw.hex())
        elif isinstance(encoding, tuple) and encoding[0] == 'call':
            target = relative_branch_target(raw, address, source='snapshotCacheClear')
            _require(raw[:1] == b'\xe8' and target == encoding[1], 'snapshot-clear-call', hex(encoding[1]), hex(target))
        elif isinstance(encoding, tuple):
            edge = _edge(row)
            _require(len(raw) == 6 and raw.startswith(encoding[1]) and edge is not None,
                     'snapshot-clear-condition', encoding[1].hex(), raw.hex())
            edges[encoding[2]] = edge[0]
        else:
            _require(raw == encoding, 'snapshot-clear-instruction', encoding.hex(), raw.hex())
        address += len(raw)
    positions = {_address(row): n for n, row in enumerate(rows)}
    return_start = edges['target']
    _require(return_start in positions, 'snapshot-clear-null-target-return', 'owned instruction boundary', hex(return_start))
    epilogue = [b'\x0f\x28\x74\x24\x60', b'\x4c\x8d\x5c\x24\x70',
        b'\x49\x8b\x5b\x30', b'\x49\x8b\x6b\x38', b'\x49\x8b\x73\x40',
        b'\x49\x8b\xe3', b'\x41\x5f', b'\x41\x5e', b'\x41\x5d', b'\x41\x5c', b'\x5f', b'\xc3']
    returned = rows[positions[return_start]:positions[return_start] + len(epilogue)]
    _require(len(returned) == len(epilogue), 'snapshot-clear-return-length', len(epilogue), len(returned))
    at = return_start
    for row, raw in zip(returned, epilogue):
        _require(_address(row) == at and bytes.fromhex(row['bytes']) == raw and at + len(raw) <= end,
                 'snapshot-clear-return-program', raw.hex(), row['bytes'])
        at += len(raw)
    normal = {_address(row) for row in rows[:len(expected)]}
    for name, target in edges.items():
        _require(target not in normal, 'snapshot-clear-excluded-edge', 'outside cache reset path', [name, hex(target)])
    return {'entry': hex(pointer), 'selectedInstructionCount': len(expected),
            'nullTargetReturnInstructionCount': len(epilogue), 'nullTargetReturn': hex(return_start),
            'resetStore': rows[len(expected) - 1]['va'], 'resetWidthBytes': 4,
            'zeroSource': 'R13D explicit XOR retained across normally returning Win64 target call',
            'receiverSource': 'incoming this RCX saved in RDI, then named cache reference in RDX',
            'excludedTargets': {name: hex(target) for name, target in edges.items()},
            'namedListClearProved': False, 'producerConsumerIndexJoinProved': False}


def check_cache_clear(index, writer_proof, spec):
    _require(writer_proof.get('claim') == 'snapshotCompiledHelperRawStore',
             'snapshot-clear-writer-proof', 'fresh physical writer proof', writer_proof.get('claim'))
    body = index.body(spec['type'], spec['method'])
    _require(body.pointer in index.extents, 'snapshot-clear-pdata-entry', 'exact owned entry', hex(body.pointer))
    end = index.extents[body.pointer]
    _require(0 < end - body.pointer <= 4096, 'snapshot-clear-pdata-extent', 'bounded exact owned extent', [body.pointer, end])
    raw = index.pe.bytes_at_va(body.pointer, end - body.pointer)
    rows = index._decode(body.pointer, end - body.pointer)
    _require(b''.join(bytes.fromhex(row['bytes']) for row in rows) == raw,
             'snapshot-clear-byte-coverage', 'complete owned partition', len(raw))
    selected = NativeReferenceContext(index.image, index=index)
    owner, cache_type, cache_offset = selected.field(writer_proof['cacheField'])
    _require(owner == spec['type'] and cache_type == 'System.Collections.Generic.List`1<double>',
             'snapshot-clear-owner-field', [spec['type'], 'List<double>'], [owner, cache_type])
    _require(index.parameter_location(body.pointer, body.symbol, 'this') == ('register', 'rcx'),
             'snapshot-clear-this-abi', ['register', 'rcx'], index.parameter_location(body.pointer, body.symbol, 'this'))
    call_rows = [row for row in rows if re.fullmatch(r'call 0x[0-9a-f]+', row['text'])]
    _require(len(call_rows) >= 5, 'snapshot-clear-call-count', 'five prefix calls', len(call_rows))
    prefix_pointers = [relative_branch_target(bytes.fromhex(row['bytes']), _address(row), source='snapshotCacheClear')
                       for row in call_rows[:5]]
    calls = dict(zip(('patch', 'owner', 'handle', 'ownerAgain', 'target'), prefix_pointers))
    _require(calls['owner'] == calls['ownerAgain'], 'snapshot-clear-owner-call', calls['owner'], calls['ownerAgain'])
    for role, symbol in spec['calls'].items():
        _require(symbol in index.names_of(calls[role]), 'snapshot-clear-call-identity', symbol, index.names_of(calls[role]))
    _require(named_reference_type(index, calls['target'], spec['calls']['target']) == 'Beyond.Gameplay.Core.AbilitySystem',
             'snapshot-clear-target-return-abi', 'ordinary AbilitySystem reference',
             named_reference_type(index, calls['target'], spec['calls']['target']))
    patch_methods = [index.metadata.methods[row['methodIndex']] for row in index.names_by_pointer[calls['patch']]
                     if f"{row.get('type')}.{row.get('method')}" == spec['calls']['patch']]
    _require(bool(patch_methods) and all(method.flags & 0x10 and selected.type_name(method.return_type) == 'bool'
             and [selected.type_name(p.type_index) for p in index.metadata.parameters_for(method)] == ['int']
             for method in patch_methods), 'snapshot-clear-patch-signature', 'static bool IsPatched(int)', len(patch_methods))
    for method in patch_methods:
        require_ordinary_signature(selected,method,['int'],'bool','clear.IFix')
    proof = check_clear_program(rows, pointer=body.pointer, end=end, cache_offset=cache_offset,
        opaque_offsets=spec['opaqueSelectionLoads'], slots=writer_proof['anonymousSlots'], calls=calls)
    return {**proof, 'symbol': body.symbol, 'claim': 'snapshotIncomingThisCacheReset',
            'cacheField': writer_proof['cacheField'], 'cacheType': cache_type,
            'boundary': 'On the checked false-patch, nonnull opaque selection carrier/owner and nonnull target-reference/cache path, the incoming action cache receives an anonymous DWORD increment and a four-byte zero in the same count slot used by the physical writer/getter. The zero is sourced from a full R13D XOR and Win64 preservation across the target call. A null target reference instead reaches a completely checked restoring RET without those stores. Selection semantics, valid unchanged live carriers/contexts, callee memory noninterference and generic List layout remain conditions or unresolved.'}

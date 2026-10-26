"""Prove constructor ClassInfo/context requests and cache pointer transfer.

Allocation, folded constructor entries and the final slot-address helper keep
their own unresolved semantics. A physical field store before that tail helper
is not a final heap/class-state assertion.
"""
from __future__ import annotations

from scripts.game_data.damage_snapshot_abi import (require_ordinary_type, require_ordinary_signature, require_ordinary_pointer, require_ordinary_field, require_ordinary_value_type, require_ordinary_type_var)

import struct

from scripts.game_data.damage_snapshot_cache_flow import _address, _require
from scripts.game_data.il2cpp.context import (
    generic_type_carrier, method_spec_record, method_spec_usage_index,
    relative_branch_target, rip_qword_load_target, unresolved_usage_index,
)
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.stack_argument_flow import _edge


def check_constructor_program(rows, *, pointer, end, field_offsets):
    _require(len(field_offsets) == 2 and all(type(value) is int and 0 <= value < 128 for value in field_offsets),
             'cache-constructor-fields', 'two positive disp8 reference fields', field_offsets)
    _require(len(rows) >= 28, 'cache-constructor-length', 'complete two allocation/store blocks', len(rows))
    expected = [b'\x48\x89\x5c\x24\x08', b'\x57', b'\x48\x83\xec\x20', b'\x48\x8b\xd9']
    for n, offset in enumerate(field_offsets):
        expected.extend(['class-load', 'allocate-call', b'\x48\x8b\xf8', b'\x48\x85\xc0', 'null-edge',
                         'method-load', b'\x48\x8b\xc8', 'constructor-call',
                         b'\x48\x8d\x4b' + bytes([offset]), b'\x48\x89\x7b' + bytes([offset])])
        if n == 0:
            expected.append('slot-call')
    expected.extend([b'\x48\x8b\x5c\x24\x30', b'\x48\x83\xc4\x20', b'\x5f', 'slot-tail'])
    _require(len(rows) >= len(expected), 'cache-constructor-program-length', len(expected), len(rows))
    address = pointer; calls = {}; blocks = []; current = None; null_edges = []
    for row, encoding in zip(rows, expected):
        raw = bytes.fromhex(row['bytes'])
        _require(_address(row) == address and address + len(raw) <= end,
                 'cache-constructor-contiguity', hex(address), row['va'])
        if encoding == 'class-load':
            _require(len(raw) == 7 and raw[:3] == b'\x48\x8b\x0d', 'cache-constructor-class-load', 'RCX RIP qword', raw.hex())
            current = {'classLoad': row}; blocks.append(current)
        elif encoding == 'method-load':
            _require(len(raw) == 7 and raw[:3] == b'\x48\x8b\x15', 'cache-constructor-context-load', 'RDX RIP qword', raw.hex())
            current['methodLoad'] = row
        elif encoding == 'null-edge':
            edge = _edge(row)
            _require(len(raw) == 2 and raw[:1] == b'\x74' and edge is not None,
                     'cache-constructor-null-condition', 'JE returned RAX null', raw.hex())
            null_edges.append(edge[0])
        elif isinstance(encoding, str):
            target = relative_branch_target(raw, address, source='damageCacheConstructor')
            _require(raw[:1] == (b'\xe9' if encoding == 'slot-tail' else b'\xe8'),
                     'cache-constructor-call-kind', encoding, raw.hex())
            if encoding in ('allocate-call', 'constructor-call'):
                current[encoding] = hex(target)
            else:
                calls[encoding] = target
        else:
            _require(raw == encoding, 'cache-constructor-instruction', encoding.hex(), raw.hex())
            if raw[:3] == b'\x48\x89\x7b':
                current['fieldStore'] = row['va']
        address += len(raw)
    _require(len(set(null_edges)) == 1 and null_edges[0] not in {_address(row) for row in rows[:len(expected)]}
             and null_edges[0] in {_address(row) for row in rows},
             'cache-constructor-null-boundary', 'shared owned failure boundary outside normal path', null_edges)
    _require(blocks[0]['allocate-call'] == blocks[1]['allocate-call'],
             'cache-constructor-allocation-entry', blocks[0]['allocate-call'], blocks[1]['allocate-call'])
    _require(calls['slot-call'] == calls['slot-tail'], 'cache-constructor-slot-helper', calls['slot-call'], calls['slot-tail'])
    return {'blocks': blocks, 'selectedInstructionCount': len(expected),
            'allocationHelper': blocks[1]['allocate-call'], 'slotAddressHelper': hex(calls['slot-tail']),
            'excludedNullTarget': hex(null_edges[0]), 'cacheStore': blocks[1]['fieldStore'],
            'pointerWidthBytes': 8, 'finalFieldStateProved': False, 'liveHeapClassParityProved': False}


def _request_context(index, block, expected_type):
    image = index.image; registration = image.registration
    load = block['classLoad']
    class_cell = rip_qword_load_target(bytes.fromhex(load['bytes']), _address(load), source='cacheConstructorClass')
    type_index = unresolved_usage_index(index.pe.bytes_at_va(class_cell, 8), registration['typesCount'],
        tag=1, source='cacheConstructorClass', offset=class_cell)
    type_pointer = index.pe.u64_at_va(int(registration['types'], 16) + type_index * 8)
    type_raw = index.pe.bytes_at_va(type_pointer, 16)
    _require(type_raw[10] == 0x15 and not type_raw[11] & 0x20,
             'cache-constructor-class-record', 'ordinary generic instance', type_raw.hex())
    carrier_pointer = struct.unpack_from('<Q', type_raw)[0]
    carrier_raw = index.pe.bytes_at_va(carrier_pointer, 32)
    base_pointer = struct.unpack_from('<Q', carrier_raw)[0]
    carrier = generic_type_carrier(type_raw, carrier_raw, index.pe.bytes_at_va(base_pointer, 16),
        type_pointer=type_pointer, type_count=len(index.metadata.types), source='cacheConstructorClass')
    actual_type = runtime_type_name(index.pe, index.metadata, type_pointer)
    _require(actual_type == expected_type, 'cache-constructor-allocation-type', expected_type, actual_type)
    load = block['methodLoad']
    method_cell = rip_qword_load_target(bytes.fromhex(load['bytes']), _address(load), source='cacheConstructorMethod')
    method_spec = method_spec_usage_index(index.pe.bytes_at_va(method_cell, 8), registration['methodSpecsCount'],
        source='cacheConstructorMethod', offset=method_cell)
    spec_address = int(registration['methodSpecs'], 16) + method_spec * 12
    definition, class_inst, method_inst = method_spec_record(index.pe.bytes_at_va(spec_address, 12),
        len(index.metadata.methods), registration['genericInstsCount'], source='cacheConstructorMethod', offset=spec_address)
    method = index.metadata.methods[definition]
    _require(method.declaring_type == carrier['baseDefinitionIndex'] and index.metadata.string(method.name_index) == '.ctor'
             and not method.flags & 0x10 and not index.metadata.parameters_for(method) and method_inst == -1,
             'cache-constructor-method-owner', 'same allocation generic owner instance .ctor()',
             [method.declaring_type, carrier['baseDefinitionIndex'], method_inst])
    selected = NativeReferenceContext(image, index=index)
    require_ordinary_type(selected,type_index,expected_type,'constructor.ClassInfo',reference_kind=0x15)
    require_ordinary_signature(selected,method,[],'void','constructor.closedCtor')
    _require(selected.type_name(method.return_type) == 'void', 'cache-constructor-return-abi', 'void', selected.type_name(method.return_type))
    arguments = [runtime_type_name(index.pe, index.metadata, arg.type_pointer_va)
                 for arg in image.instantiations.resolve(class_inst).arguments]
    closed_method_type = f"{index.metadata.type_full_name(index.metadata.types[method.declaring_type])}<{','.join(arguments)}>"
    _require(closed_method_type == expected_type, 'cache-constructor-context-class', expected_type, closed_method_type)
    target = int(block['constructor-call'], 16)
    aliases = index.names_by_pointer.get(target, [])
    _require(any(row.get('methodIndex') == definition for row in aliases),
             'cache-constructor-physical-owner', definition, aliases)
    # A folded physical body may have other owning method definitions. Their
    # identity is recorded, never removed because the selected context fits.
    return {'requestedType': actual_type, 'allocationClassCell': hex(class_cell),
            'constructorMethodCell': hex(method_cell), 'constructorMethodSpecIndex': method_spec,
            'constructorPhysicalTarget': hex(target), 'constructorAliases': sorted({
                f"{row.get('type')}.{row.get('method')}" for row in aliases}),
            'registeredContextEntries': [hex(pointer) for pointer, names in index.names_by_pointer.items()
                                         if any(row.get('methodSpecIndex') == method_spec for row in names)]}


def check_cache_constructor(index, writer_proof, spec):
    _require(writer_proof.get('claim') == 'snapshotCompiledHelperRawStore',
             'cache-constructor-writer-proof', 'fresh writer owner-field proof', writer_proof.get('claim'))
    selected = NativeReferenceContext(index.image, index=index)
    fields = [selected.field(spec['otherField']), selected.field(writer_proof['cacheField'])]
    _require(all(owner == spec['type'] for owner, _, _ in fields),
             'cache-constructor-field-owner', spec['type'], [owner for owner, _, _ in fields])
    for qualified,field in zip((spec['otherField'],writer_proof['cacheField']),fields):
        require_ordinary_field(selected,qualified,field[1],'constructor.destination')
    _require(not selected.is_value_type(spec['type']), 'cache-constructor-receiver-class', 'ordinary action class', spec['type'])
    body = index.body(spec['type'], '.ctor')
    _require(index.parameter_location(body.pointer, body.symbol, 'this') == ('register', 'rcx'),
             'cache-constructor-this-abi', ['register', 'rcx'], index.parameter_location(body.pointer, body.symbol, 'this'))
    methods = [index.metadata.methods[row['methodIndex']] for row in index.names_by_pointer.get(body.pointer, ())
               if f"{row.get('type')}.{row.get('method')}" == body.symbol]
    _require(bool(methods) and all(not method.flags & 0x10 and selected.type_name(method.return_type) == 'void'
             and not index.metadata.parameters_for(method) for method in methods),
             'cache-constructor-instance-abi', 'instance void no-argument constructor', body.symbol)
    for method in methods:
        require_ordinary_signature(selected,method,[],'void','constructor.entry')
    _require(body.pointer in index.extents, 'cache-constructor-pdata-entry', 'exact owned entry', hex(body.pointer))
    end = index.extents[body.pointer]
    _require(0 < end - body.pointer <= 2048, 'cache-constructor-owned-range', 'bounded exact owned extent', [body.pointer, end])
    raw = index.pe.bytes_at_va(body.pointer, end - body.pointer); rows = index._decode(body.pointer, end - body.pointer)
    _require(b''.join(bytes.fromhex(row['bytes']) for row in rows) == raw,
             'cache-constructor-byte-coverage', 'complete owned byte partition', len(raw))
    proof = check_constructor_program(rows, pointer=body.pointer, end=end, field_offsets=[field[2] for field in fields])
    requests = [_request_context(index, block, field[1]) for block, field in zip(proof.pop('blocks'), fields)]
    _require(requests[1]['requestedType'] == 'System.Collections.Generic.List`1<double>',
             'cache-constructor-cache-type', 'List<double>', requests[1]['requestedType'])
    return {**proof, 'symbol': body.symbol, 'claim': 'snapshotConstructorCachePointerStore',
            'cacheField': writer_proof['cacheField'], 'requests': requests,
            'boundary': 'The complete selected constructor path requests the same closed class named by each destination field and passes a matching instance-void constructor MethodSpec. Full allocator RAX bits survive in RDI through normal Win64 constructor returns and reach the incoming action reference fields; the cache store is followed by a slot-address tail helper with the original frame restored. Allocation/class resolution, folded constructor behavior and that helper final effect remain conditional or unresolved; the pre-helper store does not prove final cache state or heap-class parity.'}

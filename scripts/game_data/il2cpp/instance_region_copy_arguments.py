"""Prove a selected owned-instance region copied to a stack call receiver.

This admits one complete warm-initialization/false-Boolean-guard grammar.
It derives field offsets, frames, byte counts, call targets and copying from
the selected image. Region bytes are not promoted to generic member meaning,
and a copied value can still contain references to shared runtime objects.
"""
from __future__ import annotations

from .fixed_vector_copy import prove_fixed_vector_copy
from .integer_addressing import decode_lea_address
from .reference_layouts import NativeReferenceContext


def prove_instance_region_copy_argument(index, body, *, field: str, end_field: str,
                                        field_type: str, callee: str, guard: str) -> dict:
    """Authenticate incoming this, raw nonzero field byte and copied receiver.

    ``end_field`` supplies an independently named upper region bound. The
    selected false guard leaves AL zero; the following byte compare must take
    its nonzero fallthrough. The internal member/flag identity stays unresolved.
    """
    def require(condition, check, actual):
        if not condition:
            raise ValueError(f'instance-region-copy.{check}: {str(actual)[:384]}')

    context = NativeReferenceContext(index.image, index=index)
    owner = body.symbol.rpartition('.')[0]
    owner_definition = index.types.get(owner)
    require(owner_definition is not None and owner_definition.generic_container_index < 0
            and not context.is_value_type(owner), 'reference-owner', owner)

    def declaration(pointer, symbol):
        declarations = [row for row in index.names_by_pointer.get(pointer, [])
                        if row['type'] + '.' + row['method'] == symbol]
        require(len(declarations) == 1, 'declaration', symbol)
        method = index.metadata.methods[declarations[0]['methodIndex']]
        require(method.generic_container_index < 0, 'nongeneric-method', symbol)
        return method

    caller = declaration(body.pointer, body.symbol)
    require(index.names_of(body.pointer) == [body.symbol]
            and not caller.flags & 0x10 and caller.parameter_count == 0
            and context.type_name(caller.return_type) == 'void'
            and index.parameter_location(body.pointer, body.symbol, 'this') == ('register', 'rcx'),
            'caller-abi', body.symbol)
    field_owner, actual_type, field_offset = context.field(field)
    bound_owner, _, region_end = context.field(end_field)
    require(field_owner == bound_owner == owner and actual_type == field_type
            and field_offset < region_end, 'field-region', (field, actual_type, end_field))
    rows = body.rows
    raw = index.pe.bytes_at_va(body.pointer, body.size)
    require(len(raw) == body.size and len(rows) >= 18, 'entry-bytes', body.size)
    selected_raw = []
    previous_end = body.pointer
    for row in rows:
        code = bytes.fromhex(row['bytes'])
        address = int(row['va'], 16)
        require(code and address == previous_end
                and raw[address - body.pointer:address - body.pointer + len(code)] == code,
                'original-inventory', row)
        selected_raw.append(code)
        previous_end = address + len(code)
    code = selected_raw

    def branch(at, opcode):
        value = code[at]
        require(len(value) == 6 and value[:2] == opcode, 'branch-encoding', rows[at])
        return int(rows[at]['va'], 16) + 6 + int.from_bytes(value[2:], 'little', signed=True)

    def call(at):
        value = code[at]
        require(len(value) == 5 and value[0] == 0xe8, 'call-encoding', rows[at])
        return int(rows[at]['va'], 16) + 5 + int.from_bytes(value[1:], 'little', signed=True)

    def lea(at, destination, base):
        value = code[at]
        result = decode_lea_address(value, 0, 0)
        require(result is not None and result[1] == len(value), 'complete-lea', rows[at])
        operation = result[0]['addressOperation']
        require(operation['destinationBits'] == 64 and operation['destination'] == destination
                and operation['base'] == base and operation['index'] is None
                and not operation['ripRelative'], 'lea-alias', operation)
        return operation['displacement']

    require(code[0] in (b'\x53', b'\x40\x53') and len(code[1]) == 7
            and code[1][:3] == b'\x48\x81\xec', 'frame-prefix', code[:2])
    frame_bytes = int.from_bytes(code[1][3:], 'little', signed=True)
    require(frame_bytes > 0 and frame_bytes % 8 == 0, 'frame-size', frame_bytes)
    require(len(code[2]) == 7 and code[2][:2] == b'\x80\x3d' and code[2][-1] == 0
            and code[3] in (b'\x48\x8b\xd9', b'\x48\x89\xcb'), 'incoming-this', code[2:4])
    warm_target = branch(4, b'\x0f\x84')
    require(code[5] == b'\x33\xd2', 'initializer-zero', code[5])
    stack_offset = lea(6, 'rcx', 'rsp')
    require(len(code[7]) == 6 and code[7][:2] == b'\x41\xb8', 'initializer-size', code[7])
    initializer_bytes = int.from_bytes(code[7][2:], 'little')
    initializer_pointer = call(8)
    require(code[9] == b'\x33\xd2' and len(code[10]) == 5 and code[10][0] == 0xb9,
            'guard-input-prefix', code[9:11])
    guard_pointer = call(11)
    require(guard in index.names_of(guard_pointer), 'named-guard', guard)
    guard_method = declaration(guard_pointer, guard)
    require(context.type_name(guard_method.return_type) == 'bool', 'Boolean-guard', guard)
    require(code[12] == b'\x84\xc0', 'guard-result-test', code[12])
    patch_target = branch(13, b'\x0f\x85')
    require(len(code[14]) == 6 and code[14][:2] == b'\x38\x83'
            and int.from_bytes(code[14][2:], 'little', signed=True) == field_offset,
            'owned-field-byte', (field_offset, code[14].hex()))
    skip_target = branch(15, b'\x0f\x84')
    region_start = lea(16, 'rcx', 'rbx')
    byte_count = region_end - region_start
    require(field_offset <= region_start < region_end and 0 < byte_count <= 4096,
            'owned-source-range', (field_offset, region_start, region_end))
    stops = [at for at in range(17, len(rows))
             if len(code[at]) == 5 and code[at][0] == 0xe8
             and callee in index.names_of(call(at))]
    require(len(stops) == 1, 'selected-call', stops)
    stop = stops[0]
    stop_pointer = call(stop)
    stop_address = int(rows[stop]['va'], 16)
    require(skip_target == stop_address + 5 and warm_target > stop_address
            and patch_target > stop_address, 'selected-branch-scope', (warm_target, patch_target, skip_target))
    sink = declaration(stop_pointer, callee)
    sink_owner = callee.rpartition('.')[0]
    sink_definition = index.types.get(sink_owner)
    require(sink_definition is not None and sink_definition.generic_container_index < 0
            and context.is_value_type(sink_owner) and not sink.flags & 0x10
            and sink.parameter_count == 0 and context.type_name(sink.return_type) == 'void'
            and index.names_of(stop_pointer) == [callee]
            and index.parameter_location(stop_pointer, callee, 'this') == ('register', 'rcx'),
            'value-receiver-abi', callee)
    require(stack_offset >= 32 and stack_offset + byte_count <= frame_bytes
            and initializer_bytes == byte_count, 'local-stack-region', (stack_offset, byte_count, frame_bytes, initializer_bytes))
    begin = int(rows[16]['va'], 16) - body.pointer
    end = stop_address - body.pointer
    proof = prove_fixed_vector_copy(raw[begin:end],
        initial_pointers={'rbx': ('incoming-instance', 0), 'rsp': ('local-stack', 0)},
        source=('incoming-instance', region_start, byte_count),
        destination=('local-stack', stack_offset, byte_count))
    require(proof['finalPointerRegisters'].get('rcx') == {'identity': 'local-stack', 'offset': stack_offset},
            'copied-call-receiver', proof['finalPointerRegisters'].get('rcx'))
    return {'status': 'proved', 'method': body.symbol, 'field': field, 'fieldType': actual_type,
        'fieldOffset': field_offset, 'regionStart': region_start, 'regionEnd': region_end,
        'copiedBytes': byte_count, 'callee': callee, 'callReceivesLocalStackCopy': True,
        'rawFieldBytePredicate': 'nonzero', 'copyProgram': proof,
        'initializerPointer': initializer_pointer, 'guardPointer': guard_pointer,
        'sourceValueMemberMeaningProved': False, 'runtimeExecutionObserved': False,
        'conditionalSelection': 'Nonzero entry RIP-relative byte, normally returning ABI-conforming initializer, false Boolean guard, nonzero owned field byte, valid nonwrapping incoming reference/stack addresses and callee-saved RBX.',
        'unresolved': 'Closed value/Nullable internal members, actual IFix and predicate selection, helper and callee internals, copied reference identities, writes and final state.'}

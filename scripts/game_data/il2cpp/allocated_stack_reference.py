"""Conditional caller proof for a typed factory result and incoming stack reference."""
import struct
from scripts.game_data.il2cpp import protocol
from scripts.game_data.il2cpp.consumer_reference_origins import check_reference_origins
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.memory_moves import decode_memory_move
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions


def check_allocated_stack_store(index, body, spec):
    image = index.image
    base = image.pe.image_base
    selected = NativeReferenceContext(image)
    owner, field_type, field_offset = selected.field(spec['field'])
    if selected.is_value_type(owner) or protocol.canonical_type_name(field_type) != 'System.String':
        raise ValueError('allocatedStackStore.reference-string-field')
    definition, = [image.metadata.methods[row['methodIndex']] for row in index.names_by_pointer[body.pointer]
                   if row['type']+'.'+row['method'] == body.symbol]
    parameter, = [p for p in image.metadata.parameters_for(definition)
                  if image.metadata.string(p.name_index) == spec['fromParameter']]
    if protocol.canonical_type_name(selected.type_name(parameter.type_index)) != 'System.String':
        raise ValueError('allocatedStackStore.string-parameter')
    parameter_type = image.pe.bytes_at_va(selected.type_pointer(parameter.type_index),16)
    if len(parameter_type) != 16 or parameter_type[10] not in (0x0e,0x12) or parameter_type[11] & 0x7f:
        raise ValueError('allocatedStackStore.undecorated-reference-parameter')
    location, slot = index.parameter_location(body.pointer, body.symbol, spec['fromParameter'])
    if location != 'stack':
        raise ValueError('allocatedStackStore.stack-parameter')
    family = image.unwind_index.family(body.pointer-base)
    ranges = [(base+r['runtimeTriple'][0], base+r['runtimeTriple'][1]) for r in family['ranges']]
    rows = []
    for start, end in sorted(ranges):
        rows.extend(decode_type_data_initialization_instructions(image.mapper, image.pe.bytes_at_va(start,end-start), start))
    entries = GenericEntries(image)
    candidates = []
    for i, row in enumerate(rows):
        if not i or not row['text'].startswith('call 0x'):
            continue
        target = int(row['text'][5:],16)
        if not any(alias['type'] == spec['allocatorType'] and alias['method'] == spec['allocatorMethod']
                   for alias in index.names_by_pointer.get(target, [])):
            continue
        previous = rows[i-1]
        if not previous['text'].startswith('mov rcx, [rip') or int(previous['va'],16)+len(bytes.fromhex(previous['bytes'])) != int(row['va'],16):
            continue
        context = derive_typed_usage_context(image, int(previous['va'],16)-base, label='allocatedStackStore')
        if (context.get('typeName'), context.get('methodName')) != (spec['allocatorType'], spec['allocatorMethod']):
            continue
        if context.get('classArguments') != [] or context.get('methodArguments') != [owner] or context.get('tag') != 6:
            raise ValueError('allocatedStackStore.closed-factory-context')
        factory = image.metadata.methods[context['methodSpec'][0]]
        if not factory.flags & 16 or factory.parameter_count or factory.generic_container_index < 0:
            raise ValueError('allocatedStackStore.static-zero-argument-factory')
        section = image.metadata.sections['genericContainers']
        at = section.offset+factory.generic_container_index*16
        if not section.offset <= at <= section.offset+section.size-16:
            raise ValueError('allocatedStackStore.generic-container-boundary')
        container = struct.unpack_from('<iiii', image.metadata.buf, at)
        raw = image.pe.bytes_at_va(selected.type_pointer(factory.return_type),16)
        if container[:3] != (factory.index,1,1) or len(raw) != 16 or raw[10:12] != b'\x1e\0' or int.from_bytes(raw[:8],'little') != container[3]:
            raise ValueError('allocatedStackStore.return-is-sole-method-argument')
        observed = entries.observe(factory.index, [], ['object'])
        if len(observed) != 1 or observed[0]['pointer'] != target or not observed[0]['uniqueMethodDefinitionForPointer']:
            raise ValueError('allocatedStackStore.shared-reference-entry')
        candidates.append({'site':int(row['va'],16), 'context':context, 'registration':observed[0]})
    if len(candidates) != 1:
        raise ValueError('allocatedStackStore.unique-typed-factory')
    source = candidates[0]
    origins = check_reference_origins(rows, entry=body.pointer, owned_ranges=ranges,
        incoming_registers={}, incoming_stack_slots={slot:'incoming-string'},
        selected_call_returns={source['site']:'typed-factory-result'})
    stores = []
    for row in rows:
        raw = bytes.fromhex(row['bytes'])
        decoded = decode_memory_move(raw,0,int(row['va'],16))
        if not decoded or decoded[1] != len(raw):
            continue
        operation = decoded[0]['memoryOperation']
        address = operation['address']
        if (operation['direction'],operation['memoryBytes'],operation['registerBits'],address.get('index'),address.get('ripRelative'),address.get('displacement')) != ('store',8,64,None,False,field_offset):
            continue
        state = origins['registerOrigins'][int(row['va'],16)]
        if state.get(address.get('base')) == ['typed-factory-result'] and state.get(operation['backingRegister']) == ['incoming-string']:
            stores.append(row)
    if not stores:
        raise ValueError('allocatedStackStore.no-typed-receiver-and-unchanged-source-store')
    return {'factory':source,'stores':stores,'referenceControl':origins,
        'evidenceBoundary':'conditional',
        'condition':'matching initialized closed factory MethodInfo; ordinary returning Win64 callees respect the declared generic reference return; incoming stack storage is stable under indirect writes and opaque callees; storage is disjoint',
        'allocatorInternalsProved':False,'runtimeReceiverObserved':False,'runtimeExecutionKnown':False}

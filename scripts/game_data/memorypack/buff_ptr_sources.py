"""Selected BuffPtr/ObjectPtr hidden16 transfers and nested Buff null source.

Exact typed caller requests and independently checked source bodies constrain
supplied coherent initialized contexts. They do not select or observe runtime
inflation, provider/cache overrides, a Buff object, or an enclosing action.
"""
import json
import struct

from scripts.game_data.il2cpp.formatter_composition import (
    derive_typed_usage_context, validate_typed_usage_context,
)
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath, deserialize_slot
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.memorypack import (
    animation_mask_sources as adapter16, pointer_param as pointer,
    pooled_global_buff_id_sources as provider_programs,
    reference_adapter_sources as reference_programs, scalar_param_native as scalar,
)
from scripts.game_data.memorypack.modelview_reference_sources import read_value as reference_read
from scripts.game_data.memorypack.read_value_reference_sources import validate_read_value_context
from scripts.game_data.memorypack.reference_conversion_sources import validate_conversion_context
from scripts.game_data.memorypack.wrapper_members import derive_from_image

LABEL = 'buffPtrSources'
BUFF_PTR = 'Beyond.Gameplay.Core.BuffPtr'
OBJECT_PTR = 'Beyond.ObjectPtr`1<Beyond.Gameplay.Core.Buff>'
BUFF = 'Beyond.Gameplay.Core.Buff'


def read16_program(regions, entry, s, *, canonical=False):
    g = BytesPath(regions, entry)
    g.take('48895c2408', '4889742410', '57', '4883ec20', '4983783800')
    g.take('498bd8' if canonical else '498bf8', '488bf2', '488bf9' if canonical else '488bd9')
    g.branch('75' if canonical else '74', canonical, 1)
    g.take('0f57c0', '0f1107' if canonical else '0f1103')
    cell = g.relative('488b0d')
    if canonical:
        g.call(s['classInit'])
    else:
        g.take('83b9e000000000'); g.branch('74', False, 1)
    g.take('488b4b38' if canonical else '488b4f38', '488b09')
    g.call(s['provider']); g.take('4885c0'); g.branch('74', False, 1)
    g.take('4c8bcf' if canonical else '4c8bcb', '4c8bc6', '488bd0')
    g.call(s['dispatch'])
    if canonical:
        g.take('488b5c2430', '488bc7', '488b742438')
    else:
        g.take('488bc3', '488b5c2430', '488b742438')
    g.take('4883c420', '5f', 'c3')
    return dict(selectedBytes=g.seen, classCell=cell, outputBytes=16,
        hiddenOutputRegister='rcx', readerRegister='rdx', methodInfoRegister='r8',
        zeroedCompleteOutput=True, sameOutputReturnedInRax=True,
        providerContextSlot=0, dispatchOutputRegister='r9', canonical=canonical,
        condition='Coherent initialized exact closed ReadValue MethodInfo and selected compatible formatter; ordinary noninterfering provider and slot5 callback ABI; valid disjoint reader/output/frame.')


def nonnull16_program(regions, entry, s, *, null=False):
    g = BytesPath(regions, entry)
    g.take('48895c2408', '4889742410', '4c89442418', '57', '4883ec30')
    provider_programs.flag(g); g.take('498bf9', '488bf2', '488bd9'); g.branch('0f84', False)
    cell = g.relative('488b0d'); g.take('83b9e000000000'); g.branch('0f84', False)
    g.take('488b4f20'); g.call(s['resolve'])
    g.take('488b88c0000000', '488b4920'); g.call(s['wrapperProvider'])
    g.take('4885c0'); g.branch('0f84', False)
    g.take('b905000000', '4c8d4c2450', '4c8bc3', '488bd0'); g.call(s['wrapperInvoke'])
    g.take('488b5c2450', '4885db'); g.branch('74', null, 1)
    if null:
        g.take('0f57c0', '0f1106'); g.jump('eb', 1)
    else:
        g.take('488b4f20'); g.call(s['resolve'])
        g.take('ba08000000', '488b88c0000000'); g.call(s['indexed'])
        g.take('4c8bc0', '488d4c2420', '33d2', '4c8bcb'); g.call(s['conversion'])
        g.take('488bce', '0f1000', '0f1106'); g.call(s['barrier'])
    g.take('488b5c2440', '488b742448', '4883c430', '5f', 'c3')
    return dict(selectedBytes=g.seen, wrapperNull=null, classCell=cell,
        outputBytes=16, getterSelector=0, referenceLaneOffset=0,
        sameReaderAndOriginalOutput=True, normalReturn=True)


def conversion16_program(regions, entry, prepare, *, ordinal):
    scalar.need(LABEL, 'boundedInterfaceOrdinal', True, type(ordinal) is int and 0 <= ordinal <= 8)
    g = BytesPath(regions, entry)
    g.take('48895c2408', '48896c2410', '4889742418', '48897c2420', '4156', '4883ec30',
           '498b39', '488be9', '488bcf', '440fb7f2', '498bf1', '498bd8')
    g.call(prepare); g.take('440fb78730010000', '33c0', '66413bc0'); g.branch('73', False, 1)
    g.take('488b97b0000000')
    for index in range(ordinal + 1):
        g.take('0fb7c8', '4803c9', '48391cca'); g.branch('74', index == ordinal, 1)
        if index < ordinal:
            g.take('66ffc0', '66413bc0'); g.branch('72', True, 1)
    g.take('0fb7d0', '488b87b0000000', '4803d2', '8b44d008', '4103c6', '4898',
           '4883c014', '48c1e004', '4803c7', '4c8b08', '488d4c2420', '4c8b4008',
           '488bd6', '41ffd1', '488b5c2440', '488b742450', '488b7c2458', '0f1000',
           '488bc5', '0f114500', '488b6c2448', '4883c430', '415e', 'c3')
    return dict(selectedBytes=g.seen, interfaceOrdinal=ordinal,
        selector='incoming UInt16 DX; caller explicitly zero',
        hiddenOutput='incoming RCX preserved RBP and returned RAX',
        wrapper='incoming R9 preserved RSI and forwarded RDX',
        interface='incoming R8 preserved RBX', getterMethodInfo='selected slot R8',
        completeCopiedBytes=16, normalReturn=True)


def _definition(image, owner, name):
    md = image.metadata
    selected = [m for td in image.named_type_definitions[owner] for m in md.methods_for(td)
                if md.string(m.name_index) == name
                and (name not in ('ReadValue', 'GetFormatter') or m.parameter_count == 0 and m.generic_container_index >= 0)]
    scalar.need(LABEL, 'oneDefinition:' + name, 1, len(selected))
    return selected[0]


def _call(source, offset):
    row, = [r for r in source['rows'] if int(r['va'], 16) == source['pointer'] + offset]
    raw = bytes.fromhex(row['bytes'])
    scalar.need(LABEL, 'directCall', (5, 232), (len(raw), raw[0]))
    return control_transfer(row)['target']


def _typed_context(image, usage, value, entries):
    validate_typed_usage_context(image, usage, label=LABEL)
    scalar.need(LABEL, 'exactTypedRead', ('MemoryPack.MemoryPackReader', 'ReadValue', [], [value]),
        tuple(usage[k] for k in ('typeName', 'methodName', 'classArguments', 'methodArguments')))
    symbols = ContextSymbols(image)
    arguments = image.instantiations.resolve(usage['methodSpec'][2]).arguments
    scalar.need(LABEL, 'oneClosedArgument', 1, len(arguments))
    closed = symbols.type(arguments[0].type_pointer_va)
    scalar.need(LABEL, 'closedArgument', value, closed['name'])
    scalar.ordinary(image, arguments[0].type_pointer_va,
        21 if value == OBJECT_PTR else 18 if value == BUFF else 17, LABEL + '.closed', reference=value == BUFF)
    provider = _definition(image, 'MemoryPack.MemoryPackFormatterProvider', 'GetFormatter')
    contexts = [symbols.context(usage['methodSpec'][0], is_method=True), symbols.context(provider.index, is_method=True)]
    typed = validate_read_value_context(image, *contexts, entries,
        fail=lambda k, e, a: scalar.need(LABEL + '.context', k, e, a))
    return dict(contexts=contexts, closedArgument=closed, typedContext=typed)


def _adapter_context(image, entries):
    method = _definition(image, 'Beyond.MemoryPack.GenericMemoryPackFormatter`2', 'Deserialize')
    context = ContextSymbols(image).context(method.declaring_type)
    proof = validate_conversion_context(image, context, entries,
        fail=lambda k, e, a: scalar.need(LABEL + '.adapter', k, e, a))
    slots = {r['relativeSlot']: r for r in context['entries']}
    scalar.need(LABEL, 'factoryWrapperIdentity', (2, 1, True),
        (slots[7]['kind'], slots[10]['kind'], slots[7]['index'] == slots[10]['index']))
    for slot, owner, name, ordinals in ((0, context['typeName'], 'ReadIsNull', [0, 1]),
            (3, context['typeName'], 'DeserializeNotNull', [0, 1]), (11, 'System.Activator', 'CreateInstance', [1])):
        row = slots[slot]; args = row['methodArguments'] if slot == 11 else row['classArguments']
        scalar.need(LABEL, 'ownedAdapterMethod:' + name,
            (3, owner, name, ordinals, True), (row['kind'], row['typeName'], row['methodName'],
            [a['parameterOwner']['ordinal'] for a in args],
            all(a['parameterOwner']['typeIndex'] == context['definition'] for a in args)))
    return context, proof


def _value_sources(image, profile, owner, value, parent, entries, adapter_context):
    base = image.pe.image_base; md = image.metadata
    typed = _typed_context(image, owner['typedRead'], value, entries)
    sources = {}; s = {}; registrations = {}
    def add(role, target):
        sources[role] = pointer.owned(image, target); s[role] = target; return sources[role]
    add('value', base + owner['valueReadTargetRva'])
    add('provider', _call(sources['value'], 60)); add('dispatch', _call(sources['value'], 79))
    row, = [r for r in sources['dispatch']['rows'] if int(r['va'], 16) == s['dispatch'] + 40]
    raw = bytes.fromhex(row['bytes']); scalar.need(LABEL, 'adapterCompareLoad', (7, '488d0d'), (len(raw), raw[:3].hex()))
    add('adapter', s['dispatch'] + 47 + int.from_bytes(raw[3:], 'little', signed=True))
    add('nonnull', _call(sources['dispatch'], 217)); add('readNull', _call(sources['dispatch'], 100))
    s['prepare'] = _call(sources['dispatch'], 32)
    for offset, role in ((108, 'typeHandle'), (128, 'creationTest'), (152, 'activate'), (181, 'notNull')):
        s[role] = _call(sources['adapter'], offset)
    scalar.need(LABEL, 'sameNonnullTarget', s['nonnull'], s['notNull'])
    for offset, role in ((66, 'resolve'), (82, 'wrapperProvider'), (112, 'wrapperInvoke'),
                         (131, 'resolve'), (148, 'indexed'), (166, 'conversion'), (180, 'barrier')):
        target = _call(sources['nonnull'], offset)
        if role in s: scalar.need(LABEL, 'sameHelper:' + role, s[role], target)
        s[role] = target
    scalar.need(LABEL, 'sameOwnedBarrier', base + parent['barrierRva'], s['barrier'])
    s['peek'] = _call(sources['readNull'], 14); s['header'] = base + parent['parentHeader']['pointerRva']
    for role in ('conversion', 'wrapperInvoke', 'peek'): add(role, s[role])
    # The actual provider is independently checked byte-for-byte, rather than
    # assigning it a canonical entry or borrowing another nominal type.
    for offset, role in ((52, 'typeHandle'), (79, 'backend'), (96, 'indexed'), (107, 'cast')):
        target = _call(sources['provider'], offset)
        if role in s: scalar.need(LABEL, 'sameProviderHelper:' + role, s[role], target)
        s[role] = target
    provider_read = provider_programs.compared_provider(sources['provider']['regions'], s['provider'], s)
    pair = profile['child' if value == BUFF_PTR else 'objectPtr']
    wrapper, = [w for w in derive_from_image(image).values() if w.wrapped_type == value]
    registered_pair = pointer.registered_pair(image, pair, wrapper, label=LABEL + '.registered:' + value)
    scalar.need(LABEL, 'namedTypeFromHandle', base + pair['registration']['helperMethods']['typeFromHandle'][3], s['typeHandle'])
    getter = pointer.methods(image, wrapper)['GetValue']
    scalar.owned_method_abi(image, NativeReferenceContext(image), getter.index, wrapper.type_definition,
        (value, 21 if value == OBJECT_PTR else 17, False), [], LABEL + '.getter')
    getter_proof = pointer.leaf(image, image.method_pointer_va(getter), ['0F104210', '488BC1', '0F1101', 'C3'])
    face, = pair['composition']['interfaces']; td = md.types[face['wrapperDefinition']]
    section = md.sections['interfaceOffsets']; start = section.offset + td.interface_offsets_start * 8
    pairs = list(struct.iter_unpack('<ii', md.buf[start:start + td.interface_offsets_count * 8]))
    ordinal = pairs.index((face['interfaceTypeIndex'], face['interfaceOffset']))
    actual_read = read16_program(sources['value']['regions'], s['value'], s)
    paths = {role: [adapter16.adapter_program(sources[role]['regions'], s[role], s, inline=role == 'dispatch', create=create)
                    for create in (False, True)] + [adapter16.adapter_program(sources[role]['regions'], s[role], s, inline=role == 'dispatch', null=True)]
             for role in ('adapter', 'dispatch')}
    paths['nonnull'] = [nonnull16_program(sources['nonnull']['regions'], s['nonnull'], s, null=null) for null in (False, True)]
    paths['readNull'] = [provider_programs.read_null_program(sources['readNull']['regions'], s['readNull'], s, null=null) for null in (False, True)]
    paths['conversion'] = conversion16_program(sources['conversion']['regions'], s['conversion'], s['prepare'], ordinal=ordinal)
    for role in ('backend', 'cast'): add(role, s[role])
    jumps = [control_transfer(r)['target'] for r in sources['backend']['rows']
        if len(bytes.fromhex(r['bytes'])) == 5 and bytes.fromhex(r['bytes'])[0] == 233]
    scalar.need(LABEL, 'oneBackendTail', 1, len(jumps)); s['backendTail'] = jumps[0]
    s['assignable'] = pointer.calls(sources['cast'])[0]
    paths['backend'] = provider_programs.backend_bridge(sources['backend']['regions'], s['backend'], s['backendTail'])
    paths['cast'] = [provider_programs.successful_cast(sources['cast']['regions'], s['cast'], s['assignable'], null=null)
                     for null in (False, True)]
    from scripts.game_data.memorypack import event_args_paths
    paths['peek'] = event_args_paths.peek(sources['peek']['regions'], s['peek'], scalar.reader_offsets(image, LABEL))
    paths['wrapperInvoke'] = deserialize_slot(sources['wrapperInvoke']['regions'], s['wrapperInvoke'],
        prepare=s['prepare'], callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]))
    if value == BUFF_PTR:
        # This selected closed type has registered canonical bodies. Their
        # different physical entries are independently compared, never aliased.
        for role, owner_name, name, classes, methods_ in (
            ('canonicalValue', 'MemoryPack.MemoryPackReader', 'ReadValue', [], [value]),
            ('canonicalProvider', 'MemoryPack.MemoryPackFormatterProvider', 'GetFormatter', [], [value]),
            ('canonicalAdapter', 'Beyond.MemoryPack.GenericMemoryPackFormatter`2', 'Deserialize', [value, 'object'], []),
            ('canonicalNonnull', 'Beyond.MemoryPack.GenericMemoryPackFormatter`2', 'DeserializeNotNull', [value, 'object'], []),
            ('canonicalReadNull', 'Beyond.MemoryPack.GenericMemoryPackFormatter`2', 'ReadIsNull', [value, 'object'], [])):
            method = _definition(image, owner_name, name); entry = entries.resolve(method.index, classes, methods_)
            registrations[role] = dict(definition=method.index, classArguments=classes, methodArguments=methods_, registration=entry)
            add(role, entry['pointer'])
        for actual, canonical in (('adapter', 'canonicalAdapter'), ('nonnull', 'canonicalNonnull'), ('readNull', 'canonicalReadNull')):
            scalar.need(LABEL, 'actualCanonical:' + actual, s[canonical], s[actual])
        s['classInit'] = _call(sources['canonicalValue'], 71)
        for offset, role in ((83, 'provider'), (102, 'dispatch')):
            scalar.need(LABEL, 'canonicalReadCall:' + role, s[role], _call(sources['canonicalValue'], offset))
        canonical = read16_program(sources['canonicalValue']['regions'], s['canonicalValue'], s, canonical=True)
        scalar.need(LABEL, 'sameReaderClassCell', canonical['classCell'], actual_read['classCell'])
        s['context'] = _call(sources['canonicalProvider'], 127)
        paths['canonicalProvider'] = provider_programs.compared_provider(sources['canonicalProvider']['regions'], s['canonicalProvider'], s, canonical=True)
        for key in ('typeClassCell', 'providerClassCell'):
            scalar.need(LABEL, 'sameProviderClass:' + key, paths['canonicalProvider'][key], provider_read[key])
        add('classInit', s['classInit']); paths['classInit'] = provider_programs.ready_class_init(sources['classInit']['regions'], s['classInit'])
        paths['canonicalRead'] = canonical
    return dict(valueType=value, typedRead=owner['typedRead'], typedContext=typed,
        adapterContext=adapter_context, registrations=registrations, registeredPair=registered_pair,
        getter=getter_proof, interfaceOrdinal=ordinal, symbolRvas={k: v - base for k, v in s.items()},
        windows={k: r['windows'] for k, r in sources.items()}, sourceRead=actual_read,
        providerRead=provider_read, paths=paths, runtimeSelectionObserved=False,
        canonicalClosedEntryRequired=value == BUFF_PTR)


def _buff_null(image, entries):
    base = image.pe.image_base; md = image.metadata
    wrapper, = [w for w in derive_from_image(image).values() if w.wrapped_type == OBJECT_PTR]
    caller = pointer.owned(image, image.method_pointer_va(pointer.methods(image, wrapper)['Deserialize']))
    usage = derive_typed_usage_context(image, caller['pointer'] - base + 107, label=LABEL + '.nestedBuff')
    typed = _typed_context(image, usage, BUFF, entries)
    source = pointer.owned(image, _call(caller, 117))
    s = {role: _call(source, offset) for role, offset in (
        ('classFromType', 142), ('hash', 199), ('compare', 246), ('backend', 438),
        ('indexed', 455), ('assignable', 471), ('dispatch', 499))}
    dispatch = pointer.owned(image, s['dispatch']); s['prepare'] = _call(dispatch, 35)
    method = _definition(image, 'Beyond.MemoryPack.GenericMemoryPackFormatter`2', 'Deserialize')
    canonical = entries.resolve(method.index, ['object', 'object'], []); s['main'] = canonical['pointer']
    main = pointer.owned(image, s['main'])
    read = reference_read(source['regions'], source['pointer'], s)
    nulls = dict(dispatch=reference_programs.dispatch(dispatch['regions'], s['dispatch'], s, null=True),
        main=reference_programs.main(main['regions'], s['main'], s, null=True))
    scalar.need(LABEL, 'readerOffsets', dict(currentPtr=80, bufferLength=48, advancedCount=64, consumed=68),
        scalar.reader_offsets(image, LABEL))
    scalar.need(LABEL, 'nestedBuffReferenceType', False, NativeReferenceContext(image).is_value_type(BUFF))
    return dict(typedRead=usage, typedContext=typed, canonicalNullAdapter=canonical,
        symbolRvas={k: v - base for k, v in s.items()},
        windows=dict(caller=caller['windows'], reader=source['windows'], dispatch=dispatch['windows'], main=main['windows']),
        reader=read, nullPaths=nulls, admittedHeader=255, consumedBytes=1,
        result='null full reference', positiveBuffClassAdmitted=False,
        condition='Buffered FF and coherent initialized typed ReadValue<Buff>/provider MethodInfo; selected canonical reference adapter at slot5; matching first cache probe and normal helper/lock/backend/predicate effects. Positive Buff deserialization and runtime provider choice remain unproved.')


def derive_value_sources(image, pins, profile, parent, child):
    """Join already authenticated owning parent/child transfers to exact sources."""
    entries = GenericEntries(image)
    context, context_proof = _adapter_context(image, entries)
    values = [_value_sources(image, profile, owner, value, parent, entries, context)
              for owner, value in ((parent, BUFF_PTR), (child, OBJECT_PTR))]
    scalar.need(LABEL, 'distinctActualDispatches', True,
        values[0]['symbolRvas']['dispatch'] != values[1]['symbolRvas']['dispatch'])
    scalar.need(LABEL, 'sameValueManagedWidth', [16, 16], [r['sourceRead']['outputBytes'] for r in values])
    return json.loads(json.dumps(dict(values=values, adapterContextProof=context_proof,
        nestedBuffNull=_buff_null(image, entries), nativeInputs=pins,
        evidenceBoundary=dict(direct='Exact closed BuffPtr and ObjectPtr<Buff> requests, two independently checked hidden16 sources and distinct slot5 dispatch/nullable adapters, registered own wrappers, own hidden16 getters and selected interface conversion. Nested Buff reference source admits buffered FF only.',
            conditional='Supplied coherent initialized closed Reader/provider/adapter/conversion MethodInfos and selected matching formatter/slot; stable disjoint reader/output/frame, sufficient contiguous bytes, ready class/interface contexts and normal Win64 helper/preparation/barrier/backend/cache/lock/activation effects. Live provider/default/cache/override/inflation selection is unobserved.',
            unresolved=['positive Buff object grammar', 'live formatter/provider/default/override/inflation selection', 'cold refill/malformed/initialization paths', 'whole-owner execution']))))

"""Independent closed ObjectPtr<GlobalBuff> hidden16 callback composition.

Only exact instruction algorithms are shared with other value16 owners. Own
closed nominal argument, eager registration, wrapper/interface/getter and every
actual source target are authenticated here. No missing closed pointer row is
invented and no Buff/ObjectPtr<Buff> identity supplies this component.
"""
import struct

from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
from scripts.game_data.memorypack import pointer_param as pointer
from scripts.game_data.memorypack import buff_ptr_sources as algorithms
from scripts.game_data.memorypack import pooled_global_buff_id_sources as programs
from scripts.game_data.memorypack import animation_mask_sources as adapter16
from scripts.game_data.memorypack import scalar_param_native as scalar

VALUE = 'Beyond.ObjectPtr`1<Beyond.Gameplay.Core.GlobalBuff>'


def need(check, condition):
    if not condition:
        raise ValueError('globalBuffValue.' + check)


def derive(image, pins, *, typed_request, target, pair, wrapper, header, barrier):
    from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack.read_value_reference_sources import validate_read_value_context
    from scripts.game_data.memorypack import event_args_paths
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    base = image.pe.image_base; md = image.metadata; entries = GenericEntries(image)
    validate_typed_usage_context(image, typed_request, label='globalBuffValue.actual')
    need('own-closed-value-request', (typed_request['tag'], typed_request['typeName'], typed_request['methodName'],
         typed_request['classArguments'], typed_request['methodArguments']) ==
         (6, 'MemoryPack.MemoryPackReader', 'ReadValue', [], [VALUE]))
    argument, = image.instantiations.resolve(typed_request['methodSpec'][2]).arguments
    scalar.ordinary(image, argument.type_pointer_va, 21, 'globalBuffValue.argument')
    ctx = NativeReferenceContext(image)
    need('own-closed-value-not-reference', ctx.is_value_type(VALUE))
    provider_def = algorithms._definition(image, 'MemoryPack.MemoryPackFormatterProvider', 'GetFormatter')
    symbols = ContextSymbols(image)
    contexts = [symbols.context(typed_request['methodSpec'][0], is_method=True), symbols.context(provider_def.index, is_method=True)]
    typed = validate_read_value_context(image, *contexts, entries,
        fail=lambda k, e, a: need(k, e == a))
    adapter_context, adapter_context_proof = algorithms._adapter_context(image, entries)
    sources = {}; s = {}
    def add(role, at):
        sources[role] = pointer.owned(image, at); s[role] = at
    call = algorithms._call
    add('value', target)
    add('provider', call(sources['value'], 60)); add('dispatch', call(sources['value'], 79))
    row, = [r for r in sources['dispatch']['rows'] if int(r['va'], 16) == s['dispatch']+40]
    raw = bytes.fromhex(row['bytes'])
    need('own-actual-adapter-compare', len(raw) == 7 and raw[:3] == bytes.fromhex('488d0d'))
    add('adapter', s['dispatch']+47+int.from_bytes(raw[3:], 'little', signed=True))
    add('nonnull', call(sources['dispatch'], 217)); add('readNull', call(sources['dispatch'], 100))
    s['prepare'] = call(sources['dispatch'], 32)
    for offset, role in ((108, 'typeHandle'), (128, 'creationTest'), (152, 'activate'), (181, 'notNull')):
        s[role] = call(sources['adapter'], offset)
    need('same-own-nonnull-target', s['nonnull'] == s['notNull'])
    for offset, role in ((66, 'resolve'), (82, 'wrapperProvider'), (112, 'wrapperInvoke'),
                         (131, 'resolve'), (148, 'indexed'), (166, 'conversion'), (180, 'barrier')):
        at = call(sources['nonnull'], offset)
        if role in s:
            need('same-own-helper.'+role, s[role] == at)
        s[role] = at
    need('own-actual-barrier', s['barrier'] == barrier)
    s['peek'] = call(sources['readNull'], 14); s['header'] = header
    for role in ('conversion', 'wrapperInvoke', 'peek'):
        add(role, s[role])
    for offset, role in ((52, 'typeHandle'), (79, 'backend'), (96, 'indexed'), (107, 'cast')):
        at = call(sources['provider'], offset)
        if role in s:
            need('same-own-provider-helper.'+role, s[role] == at)
        s[role] = at
    provider = programs.compared_provider(sources['provider']['regions'], s['provider'], s)
    registered = pointer.registered_pair(image, pair, wrapper, label='globalBuffValue.pair')
    need('same-own-Type-handle', pair['registration']['helperMethods']['typeFromHandle'][3]+base == s['typeHandle'])
    getter = pointer.methods(image, wrapper)['GetValue']
    scalar.owned_method_abi(image, ctx, getter.index, wrapper.type_definition, (VALUE, 21, False), [], 'globalBuffValue.getter')
    getter_source = pointer.leaf(image, image.method_pointer_va(getter), ['0F104210', '488BC1', '0F1101', 'C3'])
    face, = pair['composition']['interfaces']; td = md.types[face['wrapperDefinition']]
    section = md.sections['interfaceOffsets']; start = section.offset+td.interface_offsets_start*8
    faces = list(struct.iter_unpack('<ii', md.buf[start:start+td.interface_offsets_count*8]))
    ordinal = faces.index((face['interfaceTypeIndex'], face['interfaceOffset']))
    read = algorithms.read16_program(sources['value']['regions'], target, s)
    paths = {role: [adapter16.adapter_program(sources[role]['regions'], s[role], s,
                inline=role == 'dispatch', create=create) for create in (False, True)] +
                [adapter16.adapter_program(sources[role]['regions'], s[role], s, inline=role == 'dispatch', null=True)]
             for role in ('adapter', 'dispatch')}
    paths['nonnull'] = [algorithms.nonnull16_program(sources['nonnull']['regions'], s['nonnull'], s, null=null) for null in (False, True)]
    paths['readNull'] = [programs.read_null_program(sources['readNull']['regions'], s['readNull'], s, null=null) for null in (False, True)]
    paths['conversion'] = algorithms.conversion16_program(sources['conversion']['regions'], s['conversion'], s['prepare'], ordinal=ordinal)
    for role in ('backend', 'cast'):
        add(role, s[role])
    jumps = [control_transfer(r)['target'] for r in sources['backend']['rows']
             if len(bytes.fromhex(r['bytes'])) == 5 and bytes.fromhex(r['bytes'])[0] == 233]
    need('one-own-backend-tail', len(jumps) == 1); s['backendTail'] = jumps[0]
    s['assignable'], = pointer.calls(sources['cast'])
    paths['backend'] = programs.backend_bridge(sources['backend']['regions'], s['backend'], s['backendTail'])
    paths['cast'] = [programs.successful_cast(sources['cast']['regions'], s['cast'], s['assignable'], null=null) for null in (False, True)]
    paths['peek'] = event_args_paths.peek(sources['peek']['regions'], s['peek'], scalar.reader_offsets(image, 'globalBuffValue'))
    paths['wrapperInvoke'] = deserialize_slot(sources['wrapperInvoke']['regions'], s['wrapperInvoke'],
        prepare=s['prepare'], callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]))
    return dict(typeName=VALUE, typedRequest=typed_request, typedContexts=contexts, typedContext=typed,
                adapterContext=adapter_context, adapterContextProof=adapter_context_proof,
                registeredPair=registered, pair=pair, getter=getter_source, interfaceOrdinal=ordinal,
                valueRead=read, providerRead=provider, paths=paths, symbolRvas={k: v-base for k, v in s.items()},
                sourceWindows={k: v['windows'] for k, v in sources.items()},
                sourceRegions={k: [(a, b.hex().upper()) for a, b in v['regions']] for k, v in sources.items()},
                actualCallbackEqualsProvedValueRequired=True, canonicalPointerEquivalenceClaimed=False,
                runtimeFormatterSelectionObserved=False, closedCanonicalRegistrationRequired=False)

"""Current bounded reference lists and the exact generated CostData child.

The reusable list component proves the selected ReadPackable reference source,
owned ListFormatter VAR contexts, signed count and complete callback/Add loop.
It admits neither an element grammar nor an enclosing caller. CostData adds its
own typed DamageUnit field transfer, registered reference wrapper/adapter and
MC3 float32/CostType-int32/float32 child, including null and fresh-wrapper paths.

Counts -1..17 are explicit. Existing lists require initial count zero and enough
capacity; fresh allocations must be zeroed and normally return the selected
typed objects. Initialized coherent closed reference-sharing contexts, matching
successful provider/cache probes, normal helper/collector ABI and disjoint
buffered storage remain conditions. Runtime provider/default/override choice,
inflation, malformed/refill paths and whole DamageUnit/action ownership are
unproved. A named typed List request alone never enables a positive child.
"""
import copy
import json
import struct

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.formatter_composition import (
    _vtable, derive_typed_usage_context, validate_generic_contexts,
    validate_typed_usage_context,
)
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.reference_layouts import (
    NativeReferenceContext, closed_generic_reference_extent,
    closed_generic_reference_pointer_extent,
)
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.memorypack import (
    int_list_sources, modelview_packable_sources, pooled_string_list_sources,
    primitive_param, reference_adapter_sources, scalar_param_native as scalar,
    lang_key_list_sources,
)
from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context
from scripts.game_data.memorypack.new_list_reference_sources import validate_capacity_constructor_context
from scripts.game_data.memorypack.pointer_param import calls, leaf, methods, owned, registered_pair
from scripts.game_data.memorypack.record_sources import return_field_source, typed_source_context
from scripts.game_data.memorypack.reference_param_profile import derive_pair
from scripts.game_data.memorypack.vector_layout import vector_recorder
from scripts.game_data.memorypack.wrapper_members import derive_from_image

LABEL = 'skillCostDataList'
VALUE = 'Beyond.Gameplay.Core.CastData+CostData'
PARENT = 'Beyond.Gameplay.Core.DamageAction+DamageUnit'
ENUM = 'Beyond.GEnums.CostType'
LIST = 'System.Collections.Generic.List`1<' + VALUE + '>'


def need(key, expected, actual):
    scalar.need(LABEL, key, expected, actual)


def _load(name, pins):
    fact = json.loads((CONTRACTS_DIR / name).read_bytes())
    need('dependency-native-inputs:' + name, pins, fact['nativeInputs'])
    return fact


def reference_clear_zero(regions, entry, *, canonical=False):
    """The actual reference Clear path when its initial count is exactly zero."""
    g = BytesPath(regions,entry)
    g.take('4057','4883ec30','8b7918','33d2','ff411c','895118','85ff')
    if canonical:g.branch('0f8e',True)
    else:g.branch('7f',False,1)
    g.take('4883c430','5f','c3')
    return dict(selectedBytes=g.seen,initialCount=0,countSlot=24,versionSlot=28,
                countZeroed=True,itemsUnchanged=True,normalReturn=True,
                positiveInitialCountAdmitted=False)


def require_reference_element(raw,*,element_type,definition=None):
    """Exact CLASS or built-in STRING source ABI; this admits no callback."""
    need('complete-reference-element-record',16,len(raw))
    if element_type=='string':
        need('exact-built-in-STRING-element',b'\x0e\x00',raw[10:12])
    else:
        need('concrete-reference-element',b'\x12\x00',raw[10:12])
        need('literal-reference-definition',True,type(definition)is int and definition>=0)
        need('element-definition',definition,int.from_bytes(raw[:8],'little'))


def derive_reference_list_component(image, pins, *, typed_request, call_target,
                                    element_type, count_limit=17):
    """Selected generic list source only; caller and child require own proofs.

    call_target is a VA, matching the actual native call. typed_request is the
    freshly derived usage record at that independently authenticated caller.
    """
    need('bounded-count', True, type(count_limit) is int and 0 <= count_limit <= 17)
    base = image.pe.image_base
    ctx = NativeReferenceContext(image)
    md = image.metadata
    entries = GenericEntries(image)
    declared = 'System.Collections.Generic.List`1<' + element_type + '>'
    validate_typed_usage_context(image, typed_request, label=LABEL + '.caller')
    need('typed-list-request', ('MemoryPack.MemoryPackReader', 'ReadPackable', [], [declared]),
         tuple(typed_request[k] for k in ('typeName', 'methodName', 'classArguments', 'methodArguments')))
    method = md.methods[typed_request['methodSpec'][0]]
    need('request-ABI', (False, 0), (bool(method.flags & 16), method.parameter_count))
    arguments = image.instantiations.resolve(typed_request['methodSpec'][2]).arguments
    need('request-arity', 1, len(arguments))
    raw = image.pe.bytes_at_va(arguments[0].type_pointer_va, 16)
    need('closed-list-reference-flags', b'\x15\x00', raw[10:12])
    selected = ContextSymbols(image).type(arguments[0].type_pointer_va)
    need('closed-list-type', declared, selected['name'])
    element, = selected['classArguments']
    element_raw = bytes.fromhex(element['rawHex'])
    if element_type=='string':
        need('actual-built-in-string-name','string',element['name'])
        require_reference_element(element_raw,element_type=element_type)
        scalar.ordinary(image,element['typePointerVa'],14,LABEL+'.stringElement',reference=True)
    elif element_raw[10:12]==b'\x15\x00':
        need('actual-closed-reference-element-name',element_type,element['name'])
        scalar.ordinary(image,element['typePointerVa'],21,LABEL+'.closedReferenceElement',reference=True)
        extent=closed_generic_reference_pointer_extent(ctx,element['typePointerVa'])
        need('actual-closed-reference-element-extent',(element_type,8),(extent['type'],extent['bytes']))
    else:
        require_reference_element(element_raw,element_type=element_type,definition=ctx.index.types[element_type].index)
        need('element-not-value-type', False, ctx.is_value_type(element_type))

    # These are generic source declarations; no Patrol or string child facts
    # are transferred. All selected byte programs and contexts run again.
    core_fact = _load('npc_runtime_native.json', pins)['readPackable']
    generic = _load('leveldata_npc_patrol_native.json', pins)['declarations']
    routes = copy.deepcopy(generic['adapters']['referenceRoutes'])
    routes['wrappers'] = []
    need('actual-reference-caller-target', base + core_fact['entryRva'], call_target)
    reference = modelview_packable_sources.validate_components(image, pins, core_fact, routes)

    td = ctx.index.types['MemoryPack.Formatters.ListFormatter`1']
    deserialize, = [m for m in md.methods_for(td) if md.string(m.name_index) == 'Deserialize']
    context = ContextSymbols(image).context(td.index)
    list_context = ContextSymbols(image).context(ctx.index.types['System.Collections.Generic.List`1'].index)
    validate_generic_contexts(image, [context, list_context], label=LABEL + '.list')
    typed = validate_list_formatter_base_context(image, context, entries, fail=need)
    capacity = validate_capacity_constructor_context(image, context, list_context, entries, fail=need)
    entry = entries.resolve(deserialize.index, ['object'], [])
    fact = _load('levelscript_pooled_string_list_native.json', pins)
    need('canonical-reference-list-registration', fact['listEntry']['registration'], json.loads(json.dumps(entry)))
    source = owned(image, entry['pointer'])
    symbols = {k: base + v for k, v in fact['listSymbols'].items()}
    offsets = scalar.reader_offsets(image, LABEL)
    offsets['totalLength'] = ctx.field('MemoryPack.MemoryPackReader::totalLength')[2] - 16
    programs = [pooled_string_list_sources.list_source(
        source['regions'], source['pointer'], offsets, symbols, count=count,
        new=new, grow=False, count_limit=count_limit)
        for count in range(-1, count_limit + 1) for new in (True, False)]
    for program in programs:
        need('exact-element-callback-count', max(0, program['countWitness']), len(program['elementCallbackSites']))
    need('list-slot-ABI', (False, 5, 2, 'void'),
         (bool(deserialize.flags & 16), deserialize.slot, deserialize.parameter_count, ctx.type_name(deserialize.return_type)))
    _vtable(image, td.index, 5, deserialize.index, LABEL)
    params = list(md.parameters_for(deserialize))
    reader = ctx.index.types['MemoryPack.MemoryPackReader']
    byval = image.pe.bytes_at_va(ctx.type_pointer(reader.byval_type_index), 16)
    formal = image.pe.bytes_at_va(ctx.type_pointer(params[0].type_index), 16)
    need('reader-flags', (b'\x11\x80', b'\x11\x20'), (byval[10:12], formal[10:12]))
    need('same-reader-definition', byval[:8], formal[:8])
    need('reader-parent', 'System.ValueType', ctx.parent('MemoryPack.MemoryPackReader'))
    slot0 = next(r for r in context['entries'] if r['relativeSlot'] == 0)
    carrier = image.pe.bytes_at_va(ctx.type_pointer(slot0['index']), 16)
    formal = image.pe.bytes_at_va(ctx.type_pointer(params[1].type_index), 16)
    need('list-output-flags', (b'\x15\x00', b'\x15\x20'), (carrier[10:12], formal[10:12]))
    need('same-list-output-carrier', carrier[:8], formal[:8])

    slots = {r['relativeSlot']:r for r in context['entries']}
    clear_entry = entries.resolve(slots[2]['methodSpec'][0], ['object'], [])
    clear_source = owned(image, symbols['clear'])
    try:
        clear_program = reference_clear_zero(clear_source['regions'], symbols['clear'])
    except ValueError as error:
        raise ValueError(LABEL+'.actual-reference-clear:'+image.pe.bytes_at_va(symbols['clear'],96).hex()+':'+str(error)) from error
    canonical_clear = owned(image, clear_entry['pointer'])
    try:
        canonical_clear_program = reference_clear_zero(canonical_clear['regions'],clear_entry['pointer'],canonical=True)
    except ValueError as error:
        raise ValueError(LABEL+'.canonical-reference-clear:'+image.pe.bytes_at_va(clear_entry['pointer'],96).hex()+':'+str(error)) from error
    provider_context = ContextSymbols(image).context(slots[3]['methodSpec'][0], is_method=True)
    validate_generic_contexts(image, [provider_context], label=LABEL+'.provider')
    ps = {r['relativeSlot']:r for r in provider_context['entries']}
    need('provider-own-slots', [0,1], sorted(ps))
    need('provider-owned-element', provider_context['definition'], ps[0]['type']['parameterOwner']['methodIndex'])
    need('provider-owned-formatter', provider_context['definition'], ps[1]['type']['classArguments'][0]['parameterOwner']['methodIndex'])
    provider_symbols = {k:base+v for k,v in generic['referenceProviderSymbols'].items()}
    need('same-hot-reference-provider', routes['symbolRvas']['hotProvider'], fact['listSymbols']['provider'])
    provider_source = owned(image, symbols['provider'])
    provider_program = lang_key_list_sources.wrapper_provider_program(provider_source['regions'], symbols['provider'], provider_symbols)
    provider_factory = lang_key_list_sources.generic_provider_factory(image, pins, provider_symbols, need)
    need('provider-same-Type-key-dictionary', provider_program['providerClassCell'], provider_factory['providerClassCell'])

    factory = _load('levelscript_int_list_native.json', pins)['factory']
    for usage in factory['usages']:
        validate_typed_usage_context(image, usage, label=LABEL + '.factory')
    need('generic-list-factory-pair', ['System.Collections.Generic.List`1', 'MemoryPack.Formatters.ListFormatter`1'],
         [u['typeName'] for u in factory['usages'][:2]])
    image.check_windows(factory['windows'], label=LABEL + '.factory')
    image.check_instruction_windows(factory['instructions'], label=LABEL + '.factory')
    mapping = int_list_sources.factory_pair(
        [(base + w['startRva'], image.window_bytes(w)) for w in factory['windows']],
        base + factory['entryRva'], type_handle=base + factory['typeHandleRva'], add=base + factory['addRva'])
    need('factory-typed-cells', [base + u['usageCellRva'] for u in factory['usages']],
         [mapping[k] for k in ('keyTypeCell', 'valueTypeCell', 'addMethodInfoCell')])
    return dict(status='validated-conditional-reference-list-component', nativeInputs=pins,
                elementType=element_type, typedRequest=typed_request, callTargetRva=call_target-base,
                closedCarrier=selected, referenceSource=reference, entry=entry,
                windows=source['windows'], instructions=[[int(r['va'],16)-base,r['bytes']] for r in source['rows']],
                symbols=fact['listSymbols'], context=context,
                listContext=list_context, typedContext=typed, capacityContext=capacity,
                programs=programs, factory=factory, factoryProof=mapping, countLimit=count_limit,
                providerContext=provider_context, providerWindows=provider_source['windows'],
                providerProgram=provider_program, providerSymbols=generic['referenceProviderSymbols'],
                providerFactory=provider_factory,
                clearEntry=clear_entry, clearWindows=clear_source['windows'], clearProgram=clear_program,
                canonicalClearWindows=canonical_clear['windows'], canonicalClearProgram=canonical_clear_program,
                clearInstructions=[[int(r['va'],16)-base,r['bytes']] for r in clear_source['rows']],
                canonicalClearInstructions=[[int(r['va'],16)-base,r['bytes']] for r in canonical_clear['rows']],
                headerBytes=4, elementRuntimeBytes=8, elementGrammarAdmitted=False,
                parentFieldAdmitted=False, wholeOwnerAdmitted=False,
                boundary=__doc__)


def cost_child_program(regions, entry, offsets, slots, symbols, *, null=False, new=False):
    """Complete selected MC3/null/new paths, without fabricating cold gap bytes."""
    need('child-mode-types', (bool, bool), (type(null), type(new)))
    g = BytesPath(regions, entry)
    b = lambda n: bytes((n,)).hex()
    cur, rem, adv, used = (b(offsets[n]) for n in ('currentPtr', 'bufferLength', 'advancedCount', 'consumed'))
    g.take('48895c2408', '48896c2410', '4889742418', '57', '4883ec20')
    g.relative('803d'); g.take('00', '488bfa', '488bd9'); g.branch('0f84', False)
    g.take('837b'+rem+'01'); g.branch('0f8c', False)
    g.take('488b43'+cur, '0fb630', '8b6b'+rem, '83ed01'); g.branch('0f88', False)
    g.take('48ff43'+cur, 'ff43'+adv, 'ff43'+used, '896b'+rem, '4080feff')
    g.branch('0f84', null)
    allocation = context = None
    if null:
        g.take('488bcf', '48c70700000000'); g.call(symbols['barrier']); g.jump('eb', 1)
    else:
        g.take('48833f00'); g.branch('0f84', new)
        if new:
            allocation = dict(site=g.at, cell=g.relative('488b0d'))
            g.call(symbols['allocate']); g.take('488be8', '4885c0'); g.branch('0f84', False)
            g.take('33d2', '488bc8'); g.call(symbols['constructor'])
            g.take('488bcf', '48892f'); g.call(symbols['barrier']); g.take('90'); g.jump('e9')
        g.take('4080fe03'); g.branch('0f85', False)
        guards = []
        def guard():
            target = g.relative('74', 1)
            need('owned-null-failure', True, target in g.bytes)
            guards.append(target)
        g.take('488b37', '488bcb'); g.call(symbols['single'])
        g.take('4885f6'); guard(); g.take('488b4610', '4885c0'); guard()
        g.take('488b37', '488bcb', 'f30f1140'+b(slots['atbValueThreshold']))
        context = dict(site=g.at, cell=g.relative('488b15'))
        g.call(symbols['integer']); g.take('4885f6'); guard()
        g.take('488b4e10', '4885c9'); guard(); g.take('8941'+b(slots['costType']))
        g.take('488bcb', '488b3f'); g.call(symbols['single'])
        g.take('4885ff'); guard(); g.take('488b4710', '4885c0'); guard()
        g.take('f30f1140'+b(slots['costValue']))
        need('same-throw-path', 1, len(set(guards)))
    g.take('488b5c2430', '488b6c2438', '488b742440', '4883c420', '5f', 'c3')
    return dict(selectedBytes=g.seen, null=null, newWrapper=new, headerBytes=1,
                memberCount=None if null else 3, fieldWireBytes=[] if null else [4,4,4],
                allocation=allocation, enumContext=context, normalReturn=True,
                unchangedFloat32Bits=True, sameIncomingReader=True,
                boundary='Ready metadata, buffered disjoint Reader/output, exact nonnull typed original or normally allocated wrapper/original; normal Win64 scalar/barrier/allocator effects. Null is FF, positive is exactly MC3. No refill/malformed/initializer execution or whole-owner claim.')


def cost_factory_program(regions, entry, symbols, *, create=False):
    g = BytesPath(regions, entry)
    g.take('4053', '4883ec20'); g.relative('803d'); g.take('00', '488bd9')
    g.branch('75' if create else '74', create, 1)
    usage = dict(site=g.at, cell=g.relative('488b0d'))
    g.call(symbols['allocate']); g.take('4885c0'); g.branch('75' if create else '74', create, 1)
    g.take('488d4b10', '48894310', '4883c420', '5b')
    need('factory-barrier-tail', symbols['barrier'], g.relative('e9'))
    return dict(selectedBytes=g.seen, usage=usage, allocatedOriginalStoredUnchanged=True,
                holderOffset=16, normalReturnViaBarrier=True, requiresNormallyReturningZeroedTypedAllocation=True)


def _damage_field(image):
    base = image.pe.image_base
    ctx = NativeReferenceContext(image)
    wrapper, = [w for w in derive_from_image(image).values() if w.wrapped_type == PARENT]
    need('parent-holder', (wrapper.name, PARENT, 16), ctx.field(wrapper.name+'::__instance'))
    need('parent-original-reference', False, ctx.is_value_type(PARENT))
    need('current-parent-member-count', 34, len(wrapper.members))
    member = wrapper.members[5]
    need('parent-sixth-declaration', ('costDataList', LIST, 'list'), (member.name, member.declared_type, member.kind))
    field = ctx.field(PARENT+'::'+member.name)
    method = methods(image, wrapper)['Deserialize']
    source = owned(image, image.method_pointer_va(method))
    transfer = return_field_source(image, source['rows'], member.name, field[2])
    ordinal = next(i for i,r in enumerate(source['rows']) if int(r['va'],16)-base == transfer['callRva'])
    usage = typed_source_context(image, source['rows'][max(0,ordinal-5):ordinal],
                                 field=member.name, method='ReadPackable', argument=LIST)
    store = next(i for i,r in enumerate(source['rows']) if int(r['va'],16)-base == transfer['storeRva'])
    following = source['rows'][store+1:store+3]
    need('field-address-for-barrier', 'add rcx, '+hex(field[2]), following[0]['text'])
    need('field-barrier-direct-call', 'call', control_transfer(following[1])['kind'])
    declared, = [f for f in image.metadata.fields_for(ctx.index.types[PARENT]) if image.metadata.string(f.name_index)==member.name]
    carrier = closed_generic_reference_extent(ctx, declared.type_index)
    need('declared-element', [VALUE], carrier['argumentTypes'])
    return dict(typedRead=usage, valueReadTargetRva=transfer['targetRva'], memberName=member.name,
                memberIndex=5), dict(wrapper=wrapper.name, memberCount=34, transfer=transfer,
                closedCarrier=carrier, windows=source['windows'],
                barrierRva=control_transfer(following[1])['target']-base,
                wholeOwnerAdmitted=False)


def derive_profile(image):
    parent, _ = _damage_field(image)
    return dict(damageUnit=parent, child=derive_pair(image, VALUE))


def derive(image, pins, profile):
    need('profile-shape', {'damageUnit','child'}, set(profile))
    parent, parent_proof = _damage_field(image)
    need('fresh-parent-binding', parent, profile['damageUnit'])
    collection = derive_reference_list_component(image, pins, typed_request=parent['typedRead'],
        call_target=image.pe.image_base+parent['valueReadTargetRva'], element_type=VALUE)
    ctx = NativeReferenceContext(image)
    base = image.pe.image_base
    md = image.metadata
    wrapper, = [w for w in derive_from_image(image).values() if w.wrapped_type==VALUE]
    need('child-declarations', [('atbValueThreshold','float','float32'),('costType',ENUM,'enum'),('costValue','float','float32')],
         [(m.name,m.declared_type,m.kind) for m in wrapper.members])
    need('child-is-reference', False, ctx.is_value_type(VALUE))
    need('child-holder', (wrapper.name,VALUE,16), ctx.field(wrapper.name+'::__instance'))
    slots = {m.name:ctx.field(VALUE+'::'+m.name)[2] for m in wrapper.members}
    need('child-disjoint-value-storage', 12, len({p for slot in slots.values() for p in range(slot,slot+4)}))
    pair = registered_pair(image, profile['child'], wrapper, label=LABEL+'.child')
    mm = methods(image, wrapper)
    primitive_param.reader_abi(image, ctx, mm['Deserialize'], wrapper)
    for name in ('.ctor','CreateInstance','GetValue'):
        scalar.owned_method_abi(image,ctx,mm[name].index,wrapper.type_definition,
            (VALUE,18,True) if name=='GetValue' else ('void',1,False),[],LABEL+'.'+name)
    getter = leaf(image,image.method_pointer_va(mm['GetValue']),['488B4110','C3'])
    source = owned(image,image.method_pointer_va(mm['Deserialize']))
    by_offset = {int(r['va'],16)-source['pointer']:r for r in source['rows']}
    def target(offset):
        row = by_offset[offset]
        need('direct-call-shape', (232,5), (bytes.fromhex(row['bytes'])[0],len(bytes.fromhex(row['bytes']))))
        return control_transfer(row)['target']
    symbols = dict(single=target(117),integer=target(154),barrier=target(237),
                   constructor=image.method_pointer_va(mm['.ctor']))
    need('same-single-source', symbols['single'], target(182))
    constructor = owned(image,symbols['constructor'])
    allocate = next(control_transfer(r)['target'] for r in constructor['rows'] if r['text'].startswith('call '))
    symbols['allocate'] = allocate
    offsets = scalar.reader_offsets(image,LABEL)
    programs = [cost_child_program(source['regions'],source['pointer'],offsets,slots,symbols,**option)
                for option in ({},{'new':True},{'null':True})]
    enum_usage = derive_typed_usage_context(image,programs[0]['enumContext']['site']-base,label=LABEL+'.enum')
    need('enum-typed-read', ('MemoryPack.MemoryPackReader','ReadUnmanaged',[],[ENUM]),
         tuple(enum_usage[k] for k in ('typeName','methodName','classArguments','methodArguments')))
    from scripts.game_data.levelscript_family_regenerate import Build
    enum = Build(image,pins).derive_enum(dict(typeName=ENUM,backingType='System.Int32',width=4))
    record = vector_recorder(image)
    single = record(symbols['single']-base)
    primitive_param.single_source(image,single,offsets)
    integer = record(symbols['integer']-base)
    scalar.integer_source(image,integer,offsets,LABEL+'.integer')
    factories = []
    for name in ('.ctor','CreateInstance'):
        s = owned(image,image.method_pointer_va(mm[name]))
        program = cost_factory_program(s['regions'],s['pointer'],symbols,create=name=='CreateInstance')
        usage = derive_typed_usage_context(image,program['usage']['site']-base,label=LABEL+'.factory')
        need('allocated-original-type', (1,VALUE), (usage['tag'],usage['typeName']))
        scalar.ordinary(image,ctx.type_pointer(usage['typeIndex']),18,LABEL+'.allocatedOriginal',reference=True)
        factories.append(dict(method=name,windows=s['windows'],usage=usage,program=program))
    allocation = derive_typed_usage_context(image,programs[1]['allocation']['site']-base,label=LABEL+'.wrapperAllocation')
    need('allocated-wrapper-type', (1,wrapper.name), (allocation['tag'],allocation['typeName']))
    scalar.ordinary(image,ctx.type_pointer(allocation['typeIndex']),18,LABEL+'.allocatedWrapper',reference=True)

    # Bind the same selected generic reference adapters to this concrete pair.
    routes = copy.deepcopy(_load('leveldata_npc_patrol_native.json',pins)['declarations']['adapters']['referenceRoutes'])
    composition = profile['child']['composition']
    interface, = composition['interfaces']
    td = md.types[wrapper.type_definition]
    section = md.sections['interfaceOffsets']
    start = section.offset+td.interface_offsets_start*8
    pairs = list(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8]))
    ordinal = pairs.index((interface['interfaceTypeIndex'],interface['interfaceOffset']))
    forward = composition['methods'][1]
    forward_source = owned(image,base+forward[3])
    forward_calls = calls(forward_source)
    routes['wrappers'] = [dict(original=VALUE,wrapper=wrapper.name,getter=composition['methods'][0],
        forwarder=forward,reader=pair['readerMethod'],interfaceOrdinal=ordinal,
        forwarderSymbolRvas=dict(metadataInit=forward_calls[0]-base,classInit=forward_calls[1]-base))]
    routes['ownedPrograms'].append(dict(entryRva=forward[3],windows=forward_source['windows'],leaf=False))
    adapter = reference_adapter_sources.validate_reference_routes(image,routes,[composition])
    return json.loads(json.dumps(dict(schema='endfield.skill-cost-data-list-source.v1',nativeInputs=pins,
        status='validated-conditional-components',parent=parent_proof,collection=collection,
        child=dict(original=VALUE,wrapper=wrapper.name,memberCount=3,fields=[dict(name=m.name,type=m.declared_type,
            offset=slots[m.name],wireBytes=4) for m in wrapper.members],windows=source['windows'],
            programs=programs,enumUsage=enum_usage,enum=enum,singleSource=single,integerSource=integer,
            getter=getter,registeredPair=pair,factories=factories,wrapperAllocation=allocation,
            referenceRoutes=routes,adapter=adapter),countLimit=17,wholeOwnerAdmitted=False,boundary=__doc__)))

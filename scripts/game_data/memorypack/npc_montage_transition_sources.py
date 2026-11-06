"""Own MC5 transition child, value20 adapter, positive list and parent join.

Every program is derived from the selected image. A ready coherent closed
Original/wrapper context and matching canonical callbacks are conditions;
neither runtime formatter selection nor animation playback is claimed.
"""
import json
import struct

from scripts.game_data.memorypack import npc_montage_transition_programs as programs

TYPE='Beyond.Montage.FMontageTransitionOverrideInfo'
FIELDS=(('from','Beyond.Gameplay.Core.GameplayTag',16),('to','Beyond.Gameplay.Core.GameplayTag',20),
    ('transistionOffset','float',24),('transitionDuration','float',28),('transitionExitTime','float',32))


def need(check,condition,detail=None):
    if not condition:raise ValueError('npcMontageTransitionSource.'+check+':'+str(detail)[:1500])


def derive(image,pins,parent):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_generic_contexts
    from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack import pointer_param as pointer,primitive_param,scalar_param_native as scalar
    from scripts.game_data.memorypack import buff_ptr_sources,event_args_paths,pooled_global_buff_id_sources as cast
    from scripts.game_data.memorypack import utf8_source_helper,montage_sources
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.skill_value_list_context import derive as list_context,bind_list_add_abi
    from scripts.game_data.memorypack import float_list_sources
    from scripts.game_data.memorypack import skill_shared_sequence_sources as shared,int_list_sources
    from scripts.game_data.memorypack.leveldata_tracking_list_sources import resolver_prefix
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.memorypack.levelscript_module_value_transfer_programs import null_program
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image)
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
    need('own-five-member-wrapper',[(m.name,m.declared_type)for m in wrapper.members]==[(n,t)for n,t,_ in FIELDS])
    td=ctx.index.types[TYPE];instance=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    need('own-value20-layout',ctx.is_value_type(TYPE)and ctx.parent(TYPE)=='System.ValueType'
        and [(md.string(f.name_index),*ctx.field(TYPE+'::'+md.string(f.name_index))[1:])for f in instance]==list(FIELDS)
        and ctx.field(wrapper.name+'::__instance')==(wrapper.name,TYPE,16))
    sizes=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*td.index)
    need('exact-managed-and-native20',image.pe.u32_at_va(sizes)==36 and image.pe.u32_at_va(sizes+4)==20)
    mm=pointer.methods(image,wrapper);source=pointer.owned(image,image.method_pointer_va(mm['Deserialize']))
    primitive_param.reader_abi(image,ctx,mm['Deserialize'],wrapper)
    child_paths=[programs.reader(source['regions'],source['pointer'],**kw)for kw in({},dict(new=True),dict(ff=True))]
    child_symbols={}
    for path in child_paths:
        for role,target in path['symbols'].items():
            need('same-complete-child-source:'+role,role not in child_symbols or child_symbols[role]==target)
            child_symbols[role]=target
    offsets=scalar.reader_offsets(image,'npcMontageTransition');record=vector_recorder(image)
    header=record(child_symbols['header']-base,fragments=True);primitive_param.object_header_source(image,header,offsets)
    montage_sources.unmanaged4(image,record(child_symbols['tag']-base,fragments=True),offsets)
    single=record(child_symbols['single']-base,fragments=True);primitive_param.single_source(image,single,offsets)
    typed=[]
    for item in child_paths[0]['contexts']:
        usage=derive_typed_usage_context(image,item['site']-base,label='npcMontageTransition.tag')
        need('actual-own-unmanaged-GameplayTag',usage['typeName']=='MemoryPack.MemoryPackReader'
            and usage['methodName']=='ReadUnmanaged'and usage['methodArguments']==['Beyond.Gameplay.Core.GameplayTag'])
        typed.append(usage)
    allocation=child_paths[1]['allocation'];allocated=derive_typed_usage_context(image,allocation['site']-base,label='npcMontageTransition.new')
    need('own-fresh-wrapper-allocation',allocated['tag']==1 and allocated['typeName']==wrapper.name)
    pair=derive_pair(image,TYPE,wrapper.name);forwarding=pointer.registered_pair(image,pair,wrapper,label='npcMontageTransition.pair')
    getter=mm['GetValue'];need('exact-own-complete-hidden-GetValue',image.pe.bytes_at_va(image.method_pointer_va(getter),17)
        ==bytes.fromhex('8b42200f1042100f1101894110488bc1c3'))
    face,=pair['composition']['interfaces'];need('same-owned-interface-getter',face['getValueMethodIndex']==getter.index)
    owner=md.types[wrapper.type_definition];section=md.sections['interfaceOffsets'];start=section.offset+owner.interface_offsets_start*8
    faces=list(struct.iter_unpack('<ii',md.buf[start:start+owner.interface_offsets_count*8]))
    ordinal=faces.index((face['interfaceTypeIndex'],face['interfaceOffset']))
    adapter_context,context_proof=buff_ptr_sources._adapter_context(image,ge)
    sources={};registrations={};targets={}
    for role,name in(('canonical','Deserialize'),('nonnull','DeserializeNotNull')):
        method=buff_ptr_sources._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2',name)
        reg=ge.resolve(method.index,[TYPE,'object'],[]);registrations[role]=reg;targets[role]=reg['pointer'];sources[role]=pointer.owned(image,reg['pointer'])
    canonical=[programs.canonical(sources['canonical']['regions'],targets['canonical'],**kw)for kw in({},dict(null=True),dict(create=False))]
    nonnull=[programs.nonnull(sources['nonnull']['regions'],targets['nonnull'],wrapper_null=n)for n in(False,True)]
    symbols={}
    for p in canonical+nonnull:
        for k,v in p['symbols'].items():need('same-helper:'+k,k not in symbols or symbols[k]==v);symbols[k]=v
    need('actual-nonnull-and-indexed-context',symbols['nonnull']==targets['nonnull'])
    for role in('readNull','conversion','wrapperInvoke'):sources[role]=pointer.owned(image,symbols[role])
    conversion_calls=[control_transfer(r)['target']for r in sources['conversion']['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8']
    need('own-preparation-entry',bool(conversion_calls));symbols['prepare']=conversion_calls[0]
    converted=programs.conversion(sources['conversion']['regions'],symbols['conversion'],prepare=symbols['prepare'],ordinal=ordinal)
    invoked=deserialize_slot(sources['wrapperInvoke']['regions'],symbols['wrapperInvoke'],prepare=symbols['prepare'],
        callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]))
    nulls=[null_program(sources['readNull']['regions'],symbols['readNull'],null=n,near=True)for n in(False,True)]
    null_symbols=nulls[0]['symbolTargets']|nulls[1]['symbolTargets']
    peek_source=pointer.owned(image,null_symbols['peek']);peek=event_args_paths.peek(peek_source['regions'],null_symbols['peek'],offsets)
    need('same-own-object-header',null_symbols['header']==child_symbols['header'])
    type_usage=derive_typed_usage_context(image,canonical[0]['typeSite']-base,label='npcMontageTransition.SystemType')
    provider_usage=derive_typed_usage_context(image,nonnull[0]['providerSite']-base,label='npcMontageTransition.provider')
    need('actual-canonical-helper-class-owners',(type_usage['tag'],type_usage['typeName'])==(1,'System.Type')
        and(provider_usage['tag'],provider_usage['typeName'])==(1,'MemoryPack.MemoryPackFormatterProvider'))
    need('same-registered-TypeFromHandle',symbols['typeHandle']==base+pair['registration']['helperMethods']['typeFromHandle'][3])
    field,=[f for f in parent['fields']if f['name']=='montageOverrideTransitions'];usage=field['typedContext']
    actual=derive_typed_usage_context(image,usage['instructionRva'],label='npcMontageTransition.parent')
    need('same-actual-parent-list-request',actual==usage and usage['methodArguments']==['System.Collections.Generic.List`1<'+TYPE+'>'])
    context,body=list_context(image,pins,typed_request=actual,call_target=base+field['targetRva'],element_type=TYPE)
    paths=[programs.listing(body['regions'],body['pointer'],count=n,new=new)for n in(-1,0,1,2,3)for new in(False,True)]
    loop=programs.induction(paths);ls={}
    for p in paths:
        for k,v in p['symbols'].items():need('same-list-helper:'+k,k not in ls or ls[k]==v);ls[k]=v
    slots={r['relativeSlot']:r for r in context['context']['entries']}
    need('actual-own-closed-capacity',ge.resolve(slots[1]['methodSpec'][0],[TYPE],[])['pointer']==ls['constructor'])
    # Add's named MethodInfo and its actual optimized body are separate proofs.
    # A populated generic registration never establishes pointer equivalence.
    add_abi=bind_list_add_abi(image,slots[6]['methodSpec'][0])
    definitions=dict(list=context['registration']['methodDefinitionIndices'][0],
        callback=registrations['canonical']['methodDefinitionIndices'][0],capacity=slots[1]['methodSpec'][0],
        Add=slots[6]['methodSpec'][0],Clear=slots[2]['methodSpec'][0])
    abis=float_list_sources._method_abis(image,ctx,definitions,context['context'])
    capacities_body=pointer.owned(image,ls['constructor'])
    capacities=[programs.capacity(capacities_body['regions'],ls['constructor'],positive=n)for n in(False,True)]
    need('own-capacity-context-and-barrier',all(p['symbolTargets']['context']==ls['context']
        and p['symbolTargets']['barrier']==ls['barrier']for p in capacities))
    provider_body=pointer.owned(image,ls['provider']);provider=programs.provider(provider_body['regions'],ls['provider'])
    ps=provider['symbolTargets'];need('own-provider-context-and-type',ps['context']==ls['context']and ps['typeHandle']==symbols['typeHandle'])
    provider_context=ContextSymbols(image).context(slots[3]['methodSpec'][0],is_method=True);validate_generic_contexts(image,[provider_context],label='npcMontageTransition.provider')
    pcs={r['relativeSlot']:r for r in provider_context['entries']};pm=md.methods[provider_context['definition']]
    need('exact-nominal-value-provider-context',sorted(pcs)==[0,1]
        and(image.type_name(pm.declaring_type),md.string(pm.name_index),bool(pm.flags&16),pm.parameter_count)==
        ('MemoryPack.MemoryPackFormatterProvider','GetFormatter',True,0)
        and ctx.type_pointer(pm.return_type)==ctx.type_pointer(pcs[1]['index'])
        and pcs[1]['type']['definition']['name']=='MemoryPack.MemoryPackFormatter`1')
    for t in(pcs[0]['type'],pcs[1]['type']['classArguments'][0]):
        owner=t.get('parameterOwner',{});need('same-owned-provider-MVAR',
            (owner.get('methodIndex'),owner.get('ordinal'))==(pm.index,0))
    resolver_fact=json.loads((CONTRACTS_DIR/'levelscript_int_list_native.json').read_bytes())
    need('same-context-resolver-build',resolver_fact['nativeInputs']==pins)
    resolver=resolver_prefix(resolver_fact['bodies']['contextResolver'],ls['context']-base)
    image.check_windows(resolver['windows'],label='npcMontageTransition.context')
    rr=[(base+w['startRva'],image.window_bytes(w))for w in resolver['windows']]
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    g=BytesPath(rr,ls['context']);g.take('488bc1','4863ca','488b0cc8');delegated=g.relative('e9')
    need('context-forwarder-is-not-an-alias',delegated!=ls['context'])
    ready=resolver_prefix(resolver_fact['bodies']['contextResolver'],delegated-base)
    image.check_windows(ready['windows'],label='npcMontageTransition.readyContext')
    rr.extend((base+w['startRva'],image.window_bytes(w))for w in ready['windows'])
    resolved=int_list_sources.initialized_class(rr,ls['context'],indexed=True)
    need('same-selected-indexed-resolver',ls['context']==symbols['indexed'])
    barrier,barrier_program,_=shared._fast_barrier(image,ls['barrier'])
    need('same-wrapper-and-list-barrier',ls['barrier']==child_symbols['barrier'])
    provider_classes=[]
    for site,name in((provider['typeSite'],'System.Type'),(provider['providerSite'],'MemoryPack.MemoryPackFormatterProvider')):
        usage=derive_typed_usage_context(image,site-base,label='npcMontageTransition.providerClass')
        need('actual-provider-class-owner',usage['tag']==1 and usage['typeName']==name);provider_classes.append(usage)
    cast_body=pointer.owned(image,ps['cast']);cast_calls=[control_transfer(r)['target']for r in cast_body['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8']
    need('provider-cast-predicate',bool(cast_calls));cast_proof=cast.successful_cast(cast_body['regions'],ps['cast'],cast_calls[0])
    backend=pointer.owned(image,ps['backend']);tails=[control_transfer(r)['target']for r in backend['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe9']
    need('one-exact-provider-backend-tail',len(tails)==1);backend_proof=cast.backend_bridge(backend['regions'],ps['backend'],tails[0])
    dispatch_body=pointer.owned(image,ls['dispatch'])
    dispatch=[programs.canonical(dispatch_body['regions'],ls['dispatch'],dispatch=True,canonical_target=targets['canonical'],**kw)
        for kw in({},dict(null=True),dict(create=False))]
    need('same-full-canonical-inline-sources',all(all(symbols.get(k)==v for k,v in p['symbols'].items())for p in dispatch))
    add_body=pointer.owned(image,ls['Add']);added=programs.add(add_body['regions'],ls['Add'])
    collection_header=utf8_source_helper._contract();need('selected-collection-header',collection_header['nativeInputs']==pins
        and ls['header']==base+collection_header['bodies']['header']['entryRva'])
    header_proof=utf8_source_helper._validate_native(image,collection_header)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.npc-montage-transition-sources.v1',nativeInputs=pins,typeName=TYPE,
        memberCount=5,managedBytes=20,positiveWireBytes=21,nullWireBytes=1,nullReturnsDefaultValue=True,
        countRange=[-1,4096],positiveCountsAdmitted=True,actualCallbackEqualsCanonicalRequired=True,
        layout=[dict(name=n,type=t,wire='i32'if i<2 else'f32')for i,(n,t,_)in enumerate(FIELDS)],
        proof=dict(parent=field,pair=pair,forwarding=forwarding,typed=typed,allocation=allocated,sourceWindows=source['windows'],
            childPaths=child_paths,header=header,single=single,adapterContext=adapter_context,contextProof=context_proof,
            registrations=registrations,canonical=canonical,nonnull=nonnull,conversion=converted,invoked=invoked,
            nulls=nulls,peek=peek,context=context,paths=paths,induction=loop,capacities=capacities,provider=provider,
            providerContext=provider_context,providerClasses=provider_classes,contextResolver=resolved,
            barrier=dict(source=barrier,program=barrier_program),cast=cast_proof,backend=backend_proof,
            dispatch=dispatch,add=added,addAbi=add_abi,methodAbis=abis,collectionHeader=header_proof),
        evidenceBoundary=dict(exact='MC5 transition fields and raw GameplayTag sources, default20 FF, complete hidden GetValue20, selected canonical adapter and actual compared list dispatch, signed count and full Add/store20 loop.',
            conditional='Ready coherent nominal Original/wrapper and List contexts, normal helper ABI, matching proved callbacks and zeroed typed allocations; reused lists start empty with sufficient capacity; buffered disjoint source/output/frame and compatible collectors.',
            unresolved=['runtime provider and formatter selection','growth/refill/error execution','runtime animation playback']))))

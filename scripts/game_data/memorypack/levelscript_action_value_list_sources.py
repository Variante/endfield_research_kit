"""Ordinary list-valued Params joined to their independent positive sources.

GlobalBuffId uses its existing nominal managed8/MC1 pooled-string source.
Boolean proves a separate byte callback, closed list loop and byte Add. An
element's managed size never supplies a wire grammar. All runtime formatter
selection remains conditional on the independently proved callback.
"""
import json
from scripts.game_data.memorypack import levelscript_action_value_list_programs as programs

BOOL='System.Collections.Generic.List`1<bool>'
GLOBAL='System.Collections.Generic.List`1<Beyond.Gameplay.Core.GlobalBuffId>'
LANG='System.Collections.Generic.List`1<Beyond.LangKey>'
TYPES=(BOOL,GLOBAL,LANG)
SCHEMA='endfield.actionmap-value-list-constant.v1'
LIMIT=4096


def need(check,condition):
    if not condition:raise ValueError('actionValueList.'+check)


def specification(value):
    need('finite-own-domain',value in TYPES)
    element,encoding={BOOL:('bool','raw-byte'),GLOBAL:('Beyond.Gameplay.Core.GlobalBuffId','MC1-pooled-id'),
        LANG:('Beyond.LangKey','MC1-pooled-key')}[value]
    return dict(schema=SCHEMA,typeName=value,countLimit=LIMIT,countRange=[-1,LIMIT],
        elementType=element,elementEncoding=encoding,positiveCountsAdmitted=True,
        constantSourceAdmitted=True,liveCallbackSelectionObserved=False)


def validate_constant(cap,value):
    expected=specification(value)
    need('exact-finite-constant',isinstance(cap,dict)and set(cap)==set(expected)
        and all(type(cap.get(k))is type(v)and cap[k]==v for k,v in expected.items())
        and all(type(n)is int for n in cap['countRange']))
    return cap


def parent_source(image,pins,value):
    from scripts.game_data.memorypack.current_reference_param_sources import derive_reference_parent
    parent=derive_reference_parent(image,pins,value_type=value,reader_method='ReadPackable')
    request=parent['typedRead']
    calls=[r for r in parent['parent']['instructions']if r[0]>request['instructionRva']and bytes.fromhex(r[1])[:1]==b'\xe8']
    need('actual-parent-const-call',bool(calls))
    at,encoded=calls[0];raw=bytes.fromhex(encoded)
    need('actual-E8-size',len(raw)==5)
    target=image.pe.image_base+at+5+int.from_bytes(raw[1:],'little',signed=True)
    return parent,request,target


def boolean_source(image,pins,request,target):
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts,derive_typed_usage_context
    from scripts.game_data.memorypack import scalar_param_native as scalar,utf8_source_helper
    from scripts.game_data.memorypack.skill_value_list_context import derive as listing
    from scripts.game_data.memorypack.levelscript_param_graph_sources import _body_target
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    from scripts.game_data.memorypack import float_list_sources,lang_key_list_sources,numeric_list_sources,pooled_global_buff_id_sources
    from scripts.game_data.memorypack.value_callback_slot_sources import program as dispatch_program
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image)
    context,body=listing(image,pins,typed_request=request,call_target=target,element_type='bool')
    s={role:_body_target(body,text,before=before)for role,text,before in(
        ('header','test al, al',True),('context','mov rcx, [rcx+0xc0]',False),('allocate','mov rcx, rax',False),
        ('constructor','mov r8, [r8+0x8]',False),('barrier','mov [rbx], r14',False),
        ('provider','mov rcx, [rcx+0x18]',False),('dispatch','mov rdx, r14',False),('add','mov r8, [r8+0x30]',False))}
    paths=[programs.boolean(body['regions'],body['pointer'],s,count=n)for n in(-1,0,1,2,3)]
    loop=prove_induction(paths,initial='33ff',increment='ffc7',comparison='3b7c2420',counter='edi',saved_count='stack-count32',max_count=LIMIT,
        backedge_sites=[paths[2]['backedge']])
    slots={r['relativeSlot']:r for r in context['context']['entries']}
    callback_td=ctx.index.types['MemoryPack.Formatters.UnmanagedFormatter`1']
    callback_method,=[m for m in md.methods_for(callback_td)if md.string(m.name_index)=='Deserialize']
    callback_reg=json.loads(json.dumps(ge.resolve(callback_method.index,['bool'],[])))
    need('same-Boolean-closed-registration',context['registration']['classInstantiation']['arguments']==callback_reg['classInstantiation']['arguments'])
    cb=owned(image,callback_reg['pointer']);offsets=scalar.reader_offsets(image,'actionBooleanList')
    headers=utf8_source_helper._contract();need('header-build',headers['nativeInputs']==pins)
    header=utf8_source_helper._validate_native(image,headers)
    need('actual-signed-collection-header',s['header']==base+headers['bodies']['header']['entryRva'])
    callback=programs.boolean_callback(cb['regions'],cb['pointer'],offsets,base+headers['bodies']['advance']['entryRva'])
    dispatch=owned(image,s['dispatch']);prepare=_body_target(dispatch,'mov rcx, [rdx]')
    invoked=dispatch_program(dispatch['regions'],dispatch['pointer'],prepare=prepare)
    ctor_reg=ge.resolve(slots[1]['methodSpec'][0],['bool'],[])
    need('actual-capacity-entry',s['constructor']==ctor_reg['pointer'])
    ctor=owned(image,s['constructor']);s['arrayAllocate']=_body_target(ctor,'mov rcx, rax')
    capacities=[programs.capacity(ctor['regions'],ctor['pointer'],s,boolean=True,positive=p)for p in(False,True)]
    add=owned(image,s['add']);added=programs.boolean_add(add['regions'],add['pointer'])
    add_reg=ge.resolve(slots[6]['methodSpec'][0],['bool'],[])
    definitions=dict(list=context['registration']['methodDefinitionIndex']if 'methodDefinitionIndex'in context['registration']else
        next(m.index for m in md.methods_for(ctx.index.types['MemoryPack.Formatters.ListFormatter`1'])if md.string(m.name_index)=='Deserialize'),
        callback=callback_method.index,capacity=slots[1]['methodSpec'][0],Clear=slots[2]['methodSpec'][0],Add=slots[6]['methodSpec'][0])
    abis=float_list_sources._method_abis(image,ctx,definitions,context['context'])
    pc=ContextSymbols(image).context(slots[3]['methodSpec'][0],is_method=True);validate_generic_contexts(image,[pc],label='actionBooleanList.provider')
    pcs={r['relativeSlot']:r for r in pc['entries']};pm=md.methods[pc['definition']]
    need('provider-static-return-ABI',sorted(pcs)==[0,1]and image.type_name(pm.declaring_type)=='MemoryPack.MemoryPackFormatterProvider'
        and md.string(pm.name_index)=='GetFormatter'and bool(pm.flags&16)and pm.parameter_count==0
        and ctx.type_pointer(pm.return_type)==ctx.type_pointer(pcs[1]['index'])
        and pcs[1]['type']['definition']['name']=='MemoryPack.MemoryPackFormatter`1')
    for child in(pcs[0]['type'],pcs[1]['type']['classArguments'][0]):
        need('provider-owned-MVAR',child['parameterOwner']['methodIndex']==pm.index and child['parameterOwner']['ordinal']==0)
    provider=owned(image,s['provider'])
    # Two same text sites have distinct roles; exact call-site bytes below bind
    # their actual order and all arguments, without a saved RVA inventory.
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    normal_start=next(i for i,r in enumerate(provider['rows'])if r['text']=='mov rbx, [rdi+0x38]'and i>6)
    calls=[control_transfer(r)['target']for r in provider['rows'][normal_start:]if bytes.fromhex(r['bytes'])[:1]==b'\xe8'][:6]
    need('six-provider-normal-calls',len(calls)==6)
    ps=dict(zip(('classInit','typeHandle','classInitAgain','backend','context','cast'),calls,strict=True))
    need('same-ready-class-helper',ps['classInit']==ps.pop('classInitAgain'))
    need('same-owned-context-helper',ps['context']==s['context'])
    provided=programs.provider(provider['regions'],provider['pointer'],ps,boolean=True)
    ready=owned(image,ps['classInit']);class_ready=pooled_global_buff_id_sources.ready_class_init(ready['regions'],ready['pointer'])
    cast=owned(image,ps['cast']);predicate=_body_target(cast,'mov rcx, [rcx]')
    casted=pooled_global_buff_id_sources.successful_cast(cast['regions'],cast['pointer'],predicate)
    path=CONTRACTS_DIR/'levelscript_int_list_native.json';raw=path.read_bytes();fact=json.loads(raw)
    need('generic-backend-selected-build',fact['nativeInputs']==pins)
    backend=owned(image,ps['backend']);backend_target=base+fact['bodies']['providerBackend']['entryRva']
    forwarded=numeric_list_sources.uint_backend_forward_program(backend['regions'],backend['pointer'],backend_target)
    factory=lang_key_list_sources.generic_provider_factory(image,pins,dict(backend=backend_target,context=s['context']),
        lambda k,e,a:scalar.need('actionBooleanList',k,e,a))
    classes=[]
    for source,cell,name in((body,paths[1]['providerClassCell'],'MemoryPack.MemoryPackFormatterProvider'),
        (provider,provided['typeClassCell'],'System.Type'),(provider,provided['providerClassCell'],'MemoryPack.MemoryPackFormatterProvider'),
        (backend,forwarded['providerOwnerCell'],'MemoryPack.MemoryPackFormatterProvider')):
        matches=[r for r in source['rows']if bytes.fromhex(r['bytes'])[:3]==b'\x48\x8b\x0d'
            and int(r['va'],16)+7+int.from_bytes(bytes.fromhex(r['bytes'])[3:],'little',signed=True)==cell]
        need('one-actual-class-cell',len(matches)==1)
        usage=derive_typed_usage_context(image,int(matches[0]['va'],16)-base,label='actionBooleanList.class')
        need('actual-nominal-class-cell',usage['tag']==1 and usage['typeName']==name);classes.append(usage)
    need('same-backend-provider-class',factory['providerClassCell']==paths[1]['providerClassCell']==forwarded['providerOwnerCell'])
    barrier,barrier_program,_=_fast_barrier(image,s['barrier'])
    need('source-contract-bookend',path.read_bytes()==raw)
    return dict(context=context,programs=paths,induction=loop,header=header,callbackRegistration=callback_reg,callback=callback,
        dispatch=invoked,capacities=capacities,constructorRegistration=ctor_reg,addRegistration=add_reg,add=added,
        actualAddTargetRva=s['add']-base,actualCanonicalAddPointerEqualityInferred=False,
        methodAbis=abis,providerContext=pc,provider=provided,readyClass=class_ready,cast=casted,backend=forwarded,
        factory=factory,classUsages=classes,barrier=dict(source=barrier,proof=barrier_program),
        windows={k:v['windows']for k,v in dict(list=body,callback=cb,dispatch=dispatch,constructor=ctor,add=add,
            provider=provider,readyClass=ready,cast=cast,backend=backend).items()})


def derive_wire(image,pins,*,value_type):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    need('finite-own-domain',value_type in TYPES);_publication_gate(image,pins)
    if value_type==LANG:
        from scripts.game_data.contracts import CONTRACTS_DIR
        from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
        from scripts.game_data.memorypack import lang_key_list_sources as lang
        path=CONTRACTS_DIR/'levelscript_lang_key_list_param_native.json';raw=path.read_bytes();fact=json.loads(raw)
        need('own-current-LangKey-list-declaration',fact['nativeInputs']==pins
            and(fact['schema'],fact['status'],fact['codecKind'],fact['collectionCounts'])==
            ('endfield.levelscript-lang-key-list-param-native.v1','exact-current-build','Param<List<LangKey>>',[-1,0,1])
            and all(type(n)is int for n in fact['collectionCounts']))
        actual=lang.derive(image,pins,fact['profile'])
        for name in('proof','evidenceBoundary'):
            value=actual if name=='proof'else actual[name]
            validate_claims(fact[name],value,label='actionValueList.LangKey.'+name)
            validate_claims(value,fact[name],label='actionValueList.LangKey.declaration.'+name)
        bounded=lang.derive_bounded(image,pins,fact['profile'],actual,count_limit=LIMIT)
        need('own-complete-positive-LangKey-list',bounded['countLimit']==LIMIT and bounded['elementRuntimeBytes']==16
            and bounded['elementWireEncoding']=='MC1/int32-pool-index-or-default'
            and bounded['induction']['maxCount']==LIMIT and bounded['wholeOwnerAdmitted']is False)
        need('LangKey-list-source-bookend',path.read_bytes()==raw);_publication_gate(image,pins)
        return json.loads(json.dumps(dict(parent=actual['parent'],listSource=actual,boundedSource=bounded,
            reviewedSource=fact,constantCapability=specification(value_type))))
    parent,request,target=parent_source(image,pins,value_type)
    if value_type==GLOBAL:
        from scripts.game_data.memorypack.skill_global_buff_id_lists import derive,CAPABILITY
        source=derive(image,pins,typed_request=request,call_target=target,count_limit=LIMIT)
        cap=source['capabilities'][CAPABILITY]
        need('own-complete-GlobalBuffId-list',source['status']=='validated-conditional-global-buff-id-list'
            and cap['positiveCountsAdmitted']is True and cap['elementGrammarAdmitted']is True
            and cap['closedListType']==value_type and cap['countLimit']==LIMIT)
    else:source=boolean_source(image,pins,request,target)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(parent=parent,listSource=source,constantCapability=specification(value_type))))

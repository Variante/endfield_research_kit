"""Positive closed EntityPtr lists with an independently proved hidden40 child.

The exact selected list loop, complete 40-byte temporary/argument transfer and
actual Add stores own the element ABI. Neither managed size nor a typed parent
request supplies a wire grammar. Growth and runtime provider selection remain
separate from these bounded normal source programs.
"""
import json
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import type_parameter_owner
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import (
    entity_ptr_param, float_list_sources, null_list_param, numeric_list_sources,
    pointer_param as ptr, scalar_param_native as scalar,
)
from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context
from scripts.game_data.memorypack.new_list_reference_sources import validate_capacity_constructor_context

TYPE='Beyond.Gameplay.Core.EntityPtr'
LIST='System.Collections.Generic.List`1<'+TYPE+'>'
LABEL='entityListSource'


def need(k,e,a):scalar.need(LABEL,k,e,a)


def list_program(regions,entry,s,*,count,new=True):
    if type(count)is not int or not 0<=count<=3 or type(new)is not bool:
        raise ValueError(LABEL+'.witness-domain')
    g=BytesPath(regions,entry)
    g.take('4c8bdc','53','55','56','57','4881eca8000000','488bf2','0f57c0','33c0','498d5310',
        '0f11442440','33db','488bce','0f11442450','49894398','498be9','498bf8','41895b10')
    g.call(s['header']);g.take('84c0');g.branch('75',True,1)
    g.take('4c89a424d0000000','4c89b424e0000000','4c89bc24a0000000','448ba424d8000000','48391f')
    g.branch('0f85',not new)
    if new:
        g.take('488b4d20','33d2','488b89c0000000');g.call(s['context'])
        g.take('488bc8');g.call(s['allocate']);g.take('4c8bf0','4885c0');g.branch('0f84',False)
        g.take('488b4d20','488b91c0000000','488b4a08','48395920');g.branch('0f84',False)
        g.take('488b4520','418bd4','498bce','4c8b80c0000000','4d8b4008');g.call(s['constructor'])
        g.take('488bcf','4c8937');g.call(s['barrier'])
    else:
        g.take('488b4520','4c8b37','488b90c0000000','488b4210','48395820');g.branch('75',True,1)
        g.take('488b4520','498bce','488b90c0000000','488b5210');g.call(s['clear']);g.take('90');g.jump('e9')
    provider=g.relative('488b0d');g.take('3999e0000000');g.branch('0f84',False)
    g.take('488b4520','488b88c0000000','488b4918');g.call(s['provider'])
    g.take('4c8bf0','4585e4');g.branch('0f8e',count==0)
    loop=g.at
    for index in range(count):
        need('same-loop-entry',loop,g.at)
        g.take('33c0','0f57c0','4889442460','0f11442440','0f11442450','4d85f6');g.branch('0f84',False)
        g.take('4c8d4c2440','4c8bc6','498bd6');g.call(s['dispatch'])
        g.take('0f10442440','4c8b3f','f20f10542460','f20f119424d8000000','0f104c2450',
            '0f11442420','0f114c2430','4d85ff');g.branch('74',False,1)
        g.take('488b4520','488b88c0000000','488b4130','4883782000');g.branch('0f84',False)
        g.take('488b4520','488d542470','498bcf','0f29442470','0f298c2480000000',
            'f20f11942490000000','4c8b80c0000000','4d8b4030');g.call(s['add'])
        g.take('ffc3','413bdc');g.branch('0f8c',index+1<count)
    g.take('4c8bb424e0000000','4c8bbc24a0000000','4c8ba424d0000000');g.jump('e9')
    g.take('4881c4a8000000','5f','5e','5d','5b','c3')
    return dict(selectedBytes=g.seen,countWitness=count,newList=new,providerClassCell=provider,
        headerBytes=4,elementCallbacks=count,elementOutputBytes=40,elementOutputFrameOffset=64,
        addArgumentFrameOffset=112,completeElementTransfer=[16,16,8],reader='incoming RDX preserved RSI',
        output='incoming R8 preserved RDI',formatterMethodInfo='incoming R9 preserved RBP',
        elementDispatch=dict(receiver='R14->RDX',reader='RSI->R8',output='RSP+64->R9',slot=5),
        addArgument='exact 16+16+8 byte child output copied unchanged to RSP+112 then RDX',
        counter='EBX initialized0, increment once per Add; signed compare to saved R12D count; exact back edge',
        nonvolatilesRestored=['rbx','rbp','rsi','rdi','r12','r14','r15'],normalReturn=True,
        condition='Initialized exact closed EntityPtr list/provider/child contexts; nonnegative signed count, fresh capacity=count or cleared reused capacity>=count, normal child/Add/helper effects and disjoint frame/buffer.')


def add_program(regions,entry,barrier):
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec50','ff411c','498bf0','4c8b4910','488bfa',
        '4c635118','488bd9','4d85c9');g.branch('0f84',False)
    g.take('453b5118');g.branch('73',False,1)
    g.take('418d4201','894118','453b5118');g.branch('0f83',False)
    g.take('0f1002','4b8d0c92','0f104a10','410f1144c920','f20f104220','410f114cc930',
        'f2410f1144c940','4a8d0c9507000000','4903ca','498d0cc9','488b5c2460','488b742468',
        '4883c450','5f')
    need('actual-add-barrier',barrier,g.relative('e9'))
    return dict(selectedBytes=g.seen,arrayStride=40,arrayDataOffset=32,storedBytes=40,
        source='incoming RDX',copies=[16,16,8],countOffset=24,versionOffset=28,
        countIncrement=1,versionIncrement=1,barrierElementOffset=24,
        returnedViaBarrier=True,restoredNonvolatiles=['rbx','rsi','rdi'],
        condition='Matching exact EntityPtr typed List and array, initial count nonnegative and below capacity; growth is excluded.')


def derive(image,pins):
    """Re-prove the selected parent, positive loop and independent child source."""
    return _derive(image,pins)


def derive_collection(image,pins,*,typed_request,call_target,count_limit=4096):
    """Fresh actual value-list caller and source; derive no Param parent."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import skill_value_list_context,utf8_source_helper
    need('explicit-finite-count-limit',True,type(count_limit)is int and 3<=count_limit<=10000)
    paths=[CONTRACTS_DIR/name for name in('levelscript_entity_ptr_param_native.json','levelscript_int_list_native.json',
        'npc_runtime_native.json','leveldata_npc_patrol_native.json')]+[utf8_source_helper.CONTRACT_PATH]
    before=[path.read_bytes()for path in paths]
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    context,body=skill_value_list_context.derive(image,pins,typed_request=typed_request,call_target=call_target,element_type=TYPE)
    empty=null_list_param.derive_empty_entity(image,ctx,body,context['registration'])
    symbols={k:base+v for k,v in empty['helperRvas'].items()};headers=utf8_source_helper._contract()
    need('own-current-header-inputs',pins,headers['nativeInputs'])
    need('own-actual-collection-header',base+headers['bodies']['header']['entryRva'],symbols['header'])
    header=utf8_source_helper._validate_native(image,headers)
    parent=dict(listRegistration=context['registration'],emptyList=empty,collectionHeader=header,
        nullListProgram=null_list_param.null_list_program(body['regions'],body['pointer'],symbols['header'],symbols['barrier']),
        context=context,parentFieldAdmitted=False,wholeOwnerAdmitted=False)
    result=_derive(image,pins,parent=parent,count_limit=count_limit)
    need('selected-declaration-bookends',before,[path.read_bytes()for path in paths])
    _publication_gate(image,pins);return result


def _derive(image,pins,*,parent=None,count_limit=10000):
    base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);entries=GenericEntries(image)
    default_parent=parent is None
    entity_fact=json.loads((CONTRACTS_DIR/'levelscript_entity_ptr_param_native.json').read_bytes())
    int_fact=json.loads((CONTRACTS_DIR/'levelscript_int_list_native.json').read_bytes())
    for name,fact in(('child',entity_fact),('provider',int_fact)):
        need('dependency-build.'+name,pins,fact['nativeInputs'])
    if default_parent:
        null_fact=json.loads((CONTRACTS_DIR/'levelscript_null_list_param_native.json').read_bytes())
        need('dependency-build.parent',pins,null_fact['nativeInputs'])
        row,=[r for r in null_fact['components']if r['codecKind']=='Param<List<EntityPtr>>']
        parent=null_list_param.derive(image,pins,row['profile'],LIST,collection_counts=[-1,0])
        child=entity_ptr_param.derive(image,pins,entity_fact['profile'])
    else:child=entity_ptr_param.derive_value(image,pins,entity_fact['profile'])
    from scripts.game_data import levelscript_int_list_native
    levelscript_int_list_native._validate_native(image,int_fact)
    selected=parent['listRegistration'];argument,=selected['classInstantiation']['arguments']
    scalar.ordinary(image,argument['type_pointer_va'],17,LABEL+'.closedEntityPtr')
    need('closed-entity-definition',ctx.index.types[TYPE].index,int.from_bytes(bytes.fromhex(argument['raw_type_record_hex'])[:8],'little'))
    body=ptr.owned(image,selected['pointer']);empty=parent['emptyList'];s={k:base+v for k,v in empty['helperRvas'].items()}
    for role,previous in(('dispatch','mov rdx, r14'),('add','mov r8, [r8+0x30]')):
        s[role]=numeric_list_sources._call_after(body,previous)
    dispatch,=[r for r in entity_fact['profile']['actualAdapter']['records']if r['role']=='actual-dispatch']
    need('actual-child-dispatch',base+dispatch['entryRva'],s['dispatch'])
    programs=[list_program(body['regions'],body['pointer'],s,count=count,new=new)
        for new in(False,True)for count in range(4)]
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    induction=prove_induction(programs,initial='33db',increment='ffc3',comparison='413bdc',
        counter='ebx',saved_count='R12D loaded once from the collection header output; preserved nonvolatile through callbacks.',max_count=count_limit)
    actual_add=ptr.owned(image,s['add']);addition=add_program(actual_add['regions'],s['add'],s['barrier'])
    context=empty['context'];slots={e['relativeSlot']:e for e in context['entries']}
    base_context=validate_list_formatter_base_context(image,context,entries,fail=need)
    list_context=ContextSymbols(image).context(ctx.index.types['System.Collections.Generic.List`1'].index)
    capacity_context=validate_capacity_constructor_context(image,context,list_context,entries,fail=need)
    spec=slots[6]['methodSpec'];canonical_add=entries.resolve(spec[0],[TYPE],[])
    method=md.methods[spec[0]];parameter,=md.parameters_for(method)
    need('add-declaration',(False,'void','System.Collections.Generic.List`1','Add'),
        (bool(method.flags&16),ctx.type_name(method.return_type),image.type_name(method.declaring_type),md.string(method.name_index)))
    raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16);need('add-owned-var-kind',b'\x13\x00',raw[10:12])
    owner=type_parameter_owner(md.buf,int.from_bytes(raw[:8],'little'),[t.generic_container_index for t in md.types],source=LABEL)
    need('add-owned-var',(method.declaring_type,0),(owner['typeIndex'],owner['ordinal']))
    constructor=ptr.owned(image,s['constructor']);s['arrayAllocate']=base+int_fact['calls']['arrayAllocate']
    constructors=[float_list_sources.capacity_program(constructor['regions'],s['constructor'],s,positive=p)for p in(False,True)]
    provider=ptr.owned(image,s['provider']);pcalls=ptr.calls(provider)[:4]
    need('provider-first-four-calls',4,len(pcalls));ps=dict(zip(('typeFromHandle','backend','type','assignable'),pcalls))
    provider_program=float_list_sources.provider_program(provider['regions'],s['provider'],ps)
    for role,key in(('typeFromHandle','typeFromHandle'),('type','resolveClass'),('assignable','assignable')):
        need('exact-common-provider-helper.'+role,base+int_fact['calls'][key],ps[role])
    backend=ptr.owned(image,ps['backend'])
    backend_program=numeric_list_sources.uint_backend_forward_program(backend['regions'],ps['backend'],base+int_fact['calls']['backend'])
    provider_entry=entries.resolve(slots[3]['methodSpec'][0],[],[TYPE])
    pc=ContextSymbols(image).context(slots[3]['methodSpec'][0],is_method=True);pcs={r['relativeSlot']:r for r in pc['entries']}
    need('provider-owned-slots',[0,1],sorted(pcs));pm=md.methods[pc['definition']]
    need('provider-static-noargs',(True,0),(bool(pm.flags&16),pm.parameter_count))
    need('provider-formatter-result','MemoryPack.MemoryPackFormatter`1',pcs[1]['type']['definition']['name'])
    need('provider-return-context',ctx.type_pointer(pm.return_type),ctx.type_pointer(pcs[1]['index']))
    for i,args in((0,[pcs[0]['type']]),(1,pcs[1]['type']['classArguments'])):
        need('provider-owned-mvar.'+str(i),[(pm.index,0)],[(a['parameterOwner']['methodIndex'],a['parameterOwner']['ordinal'])for a in args])
    usages=[]
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    for source,cell,name in((provider,provider_program['providerClassCell'],'System.Type'),
        (provider,provider_program['rootClassCell'],'MemoryPack.MemoryPackFormatterProvider'),
        (backend,backend_program['providerOwnerCell'],'MemoryPack.MemoryPackFormatterProvider')):
        row,=[r for r in source['rows']if bytes.fromhex(r['bytes'])[:3]==b'\x48\x8b\x0d'and
            int(r['va'],16)+7+int.from_bytes(bytes.fromhex(r['bytes'])[3:],'little',signed=True)==cell]
        usage=derive_typed_usage_context(image,int(row['va'],16)-base,label=LABEL+'.provider')
        need('typed-class-cell',(1,name),(usage['tag'],usage['typeName']));usages.append(usage)
    result=dict(schema='endfield.entity-ptr-list-source.v1',nativeInputs=pins,
        typeName=LIST,elementType=TYPE,codecKind='Param<List<EntityPtr>>',nullAdmitted=True,
        emptyAdmitted=True,positiveAdmitted=True,maxCount=induction['maxCount'],managedElementBytes=40,wireCountBytes=4,
        elementGrammar=dict(nullMarker=255,memberCount=3,fields=['uint64','uint32','bool-byte']),
        parent=parent,child=child,listPrograms=programs,countInduction=induction,actualAdd=addition,
        canonicalAddRegistration=canonical_add,addParameterOwner=owner,
        typedBase=base_context,capacityContext=capacity_context,constructorPrograms=constructors,
        providerEntry=provider_entry,providerContext=pc,providerProgram=provider_program,
        backendForward=backend_program,classUsages=usages,symbolRvas={k:v-base for k,v in s.items()},
        sourceWindows={role:b['windows']for role,b in(('list',body),('actualAdd',actual_add),('provider',provider),('backend',backend))},
        actualCanonicalAddPointerEquivalenceClaimed=False,liveProviderSelectionObserved=False,
        evidenceBoundary=dict(exact='Current closed typed EntityPtr-list Param and registered list source; complete count0 and selected positive count induction, exact hidden40 child callback, 16+16+8 temporary/argument transfer, actual stride40 array stores and full frame returns. EntityPtr independently proves FF/default or MC3 UInt64 logicId, UInt32 slotId and one bool byte; managed40 is not wire40.',
            conditional='Initialized coherent exact closed list/provider/adapter contexts and selected matching current EntityPtr canonical callback/wrapper, sufficient buffered disjoint storage and normal helpers/allocation/barrier. Fresh list capacity=count or cleared reused list capacity>=count; actual Add uses spare capacity only. Runtime provider choice is conditional.',
            unresolved=['list growth or reused capacity<count','live formatter/provider/cache/default/override/inflation choice','runtime entity resolution','cold initialization/refill/malformed paths','whole enclosing owner']))
    if not default_parent:
        result.update(schema='endfield.entity-ptr-list-source.v3',codecKind='List<EntityPtr>',
            actualContext=parent['context'],parentDerived=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
            sourceRegions={role:[[a-base,raw.hex().upper()]for a,raw in b['regions']]for role,b in
                (('list',body),('actualAdd',actual_add),('provider',provider),('backend',backend),('constructor',constructor))})
        result['sourceWindows']['constructor']=constructor['windows']
        # Capture-only additions for the independent collection validator. The
        # legacy Param result above deliberately retains its exact old shape.
        from scripts.game_data.il2cpp.string_source_instructions import decode_utf8_decoder_instructions
        from scripts.game_data.memorypack import utf8_source_helper
        headers=json.loads(utf8_source_helper.CONTRACT_PATH.read_bytes())
        need('replay-header-selected-pins',pins,headers['nativeInputs'])
        def packet(at,*,header=False):
            b=ptr.owned(image,at)
            rows=b['rows'] if not header else [r for a,raw in b['regions'] for r in decode_utf8_decoder_instructions(image.mapper,raw,a)]
            return dict(entryRva=at-base,windows=b['windows'],regions=[[a-base,raw.hex().upper()]for a,raw in b['regions']],rows=rows,
                boundary='complete-native-owned-family')
        clear_fact=parent['emptyList']['helperProofs'];clear_at=clear_fact['registeredClearEntry']['pointer']
        clear_raw=bytes.fromhex(clear_fact['registeredClearProgramBytes'])
        import hashlib
        registered_clear=dict(entryRva=clear_at-base,
            windows=[dict(startRva=clear_at-base,endRva=clear_at-base+len(clear_raw),sha256=hashlib.sha256(clear_raw).hexdigest().upper())],
            regions=[[clear_at-base,clear_raw.hex().upper()]],rows=image.body_index._decode(clear_at,len(clear_raw)),
            boundary='declared-selected-Clear-span-no-unwind-extent-claim')
        header_symbols=dict(headers['opaqueCalls'])
        for role in('getNextSpan','insufficient'):header_symbols[role]=headers['methods'][role][3]
        header_symbols['advanceFallback']=headers['opaqueCalls']['advanceFallback']
        generic=json.loads((CONTRACTS_DIR/'leveldata_npc_patrol_native.json').read_bytes())
        reference_symbols=dict(generic['declarations']['adapters']['referenceRoutes']['symbolRvas'])
        reference_symbols['backend']=ps['backend']-base
        result['replay']=dict(sources=dict(clear=packet(s['clear']),registeredClear=registered_clear,header=packet(s['header'],header=True),frontend=packet(base+parent['context']['callTargetRva'])),
            headerReaderOffsets=headers['readerFieldOffsets'],headerSymbolRvas=header_symbols,
            providerSymbolRvas={k:v-base for k,v in ps.items()},backendTargetRva=int_fact['calls']['backend'],
            referenceSymbolRvas=reference_symbols)
        result['evidenceBoundary']['exact']='Fresh actual closed EntityPtr-list request/E8 and own registered source; complete nullable/count induction, hidden40 callback/temporary/argument/Add transfer and independent EntityPtr value grammar/adapter. No Param parent is derived or admitted.'
    return json.loads(json.dumps(result))

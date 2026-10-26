"""Current Vector2 list/count/raw callback/Add programs for air-wall geometry."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def list_program(regions,entry,s,*,count):
    if type(count)is not int or count not in(-1,0,1,2,3):raise ValueError('Vector2List.literal-count')
    g=BytesPath(regions,entry);loop=backedge=None;callback=provider=None
    g.take('4053','55','57','4154','4156','4883ec30','33c0','498be9','837a3004',
        '4d8be0','488bda','4889442468');g.branch('0f8c',False)
    g.take('488b4350','4c6330','8b7b30','83c7fc');g.branch('0f88',False)
    g.take('4883435004','83434004','83434404','897b30','48634344','488b4b18','482bc8','493bce')
    g.branch('0f8c',False);g.take('4c897c2478','4533ff','4183feff');g.branch('0f84',count==-1)
    if count==-1:
        g.take('498bcc','4d893c24');g.call(s['barrier']);g.take('4c8b7c2478')
    else:
        g.take('4889742460','4c896c2470','0f29742420','4d393c24');g.branch('0f85',False)
        g.take('488b4d20','33d2','488b89c0000000');g.call(s['context'])
        g.take('488bc8');g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('0f84',False)
        g.take('488b4d20','488b91c0000000','488b4a08','4c397920');g.branch('0f84',False)
        g.take('488b4520','418bd6','488bcf','4c8b80c0000000','4d8b4008');g.call(s['constructor'])
        g.take('498bcc','49893c24');g.call(s['barrier'])
        provider=g.relative('488b0d');g.take('4439b9e0000000');g.branch('0f84',False)
        g.take('488b4520','488b88c0000000','488b4918');g.call(s['provider'])
        g.take('488bf0','4585f6');g.branch('0f8e',count==0)
        if count:
            callback=g.relative('4c8d2d')
            if callback!=s['callback']:raise ValueError('Vector2List.exact-canonical-callback')
            g.take('0f1f840000000000');loop=g.at
            for index in range(count):
                if g.at!=loop:raise ValueError('Vector2List.same-loop-head')
                g.take('33c0','4889442468','4885f6');g.branch('0f84',False)
                g.take('488b0e');g.call(s['prepare'])
                g.take('488b06','4c8b9090010000','4c8b8898010000','4d3bd5');g.branch('0f85',False)
                g.take('837b3008');g.branch('0f8c',False)
                g.take('488b4350','f20f1000','f20f11442468','8b7b30','83c7f8');g.branch('0f88',False)
                g.take('4883435008','83434008','83434408','897b30','498b3c24','f20f10742468','4885ff')
                g.branch('74',False,1)
                g.take('488b4520','488b88c0000000','488b4130','4883782000');g.branch('0f84',False)
                g.take('488b4520','66480f7ef2','488bcf','4c8b80c0000000','4d8b4030');g.call(s['add'])
                g.take('41ffc7','453bfe');backedge=g.at;g.branch('0f8c',index+1<count)
            if g.at==loop:raise ValueError('Vector2List.positive-count-must-exit')
        g.take('488b742460','4c8b6c2470','0f28742420','4c8b7c2478')
    g.take('4883c430','415e','415c','5f','5d','5b','c3')
    return dict(selectedBytes=g.seen,countWitness=count,loopHead=loop,backedge=backedge,
        headerBytes=4,elementWireBytes=8,managedElementBytes=8,newOutput=True,newList=True,
        elementCallbacks=max(count,0),normalReturn=True,
        providerClassCell=provider,selectedCallback=callback,
        countInvariant='Saved signed R14 count is unchanged. R15 starts0, increments once after one exact raw8 read and same raw8 Add, then signed JL repeats the identical body. Constructor receives unchanged nonnegative count and the selected Add increments size once while preserving payload/SIMD/frame. Stable nonwrapping storage and normal selected matching callbacks remain conditions.',
        elementGrammarAdmitted=False,wholeOwnerAdmitted=False)


def prove_loop(programs,*,count_limit=4096):
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    selected=[p for p in programs if p.get('countWitness')in(0,1,2,3)]
    one,=[p for p in selected if p['countWitness']==1]
    return prove_induction(selected,initial='4533ff',increment='41ffc7',comparison='453bfe',
        counter='r15d',saved_count='immutable R14D copied once from signed Int32 header output',
        max_count=count_limit,backedge_sites=[one['backedge']])


def _list_programs(regions,entry,s,*,count_limit):
    if count_limit is not None and(type(count_limit)is not int or not 3<=count_limit<=10000):
        raise ValueError('Vector2List.literal-strict-induction-limit')
    programs=[list_program(regions,entry,s,count=n)for n in((-1,0,1,2)if count_limit is None else(-1,0,1,2,3))]
    if count_limit is not None:return programs,prove_loop(programs,count_limit=count_limit)
    for program in programs:
        for key in('newList','elementCallbacks'):program.pop(key)
    return programs,None


def formatter_program(regions,entry):
    g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec20','837a3008','498bf8','488bda');g.branch('0f8c',False)
    g.take('488b4250','f30f104804','f30f1000','f30f1107','f30f114f04','8b7b30','83c7f8')
    g.branch('0f88',False)
    g.take('4883435008','83434008','83434408','897b30','488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,wireBytes=8,resultBytes=8,rawSingleOffsets=[0,4],
        incomingReader='rdx',incomingOutput='r8',normalReturn=True)


def add_program(regions,entry,*,canonical=False):
    if type(canonical)is not bool:raise ValueError('Vector2List.Add-literal-profile')
    g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec40','ff411c','498bf8',
        '4c634918'if canonical else'48634118','488bd9',
        '0f29742430','66480f6ef2','488b5110','f20f11742420','4885d2')
    g.branch('75',True,1)if canonical else g.branch('74',False,1)
    g.take('443b4a18'if canonical else'3b4218')
    g.branch('72',True,1)if canonical else g.branch('73',False,1)
    g.take('418d4101','894118','443b4a18')if canonical else g.take('8d4801','894b18','3b4218')
    g.branch('72',True,1)if canonical else g.branch('73',False,1)
    g.take('f30f10442420','f30f104c2424',
        'f3420f1144ca20'if canonical else'f30f1144c220',
        'f3420f114cca24'if canonical else'f30f114cc224',
        '488b5c2450','0f28742430','4883c440','5f','c3')
    return dict(selectedBytes=g.seen,elementStrideBytes=8,rawSingleStores=[0,4],sizeIncrement=1,
        fullPayloadFromIncomingRdx=True,originalXmm6Restored=True,entryFrameRestored=True,
        canonicalRegistration=canonical,normalReturn=True,
        condition='Nonnull fresh count-sized Vector2 array with size strictly below capacity; growth/throw paths remain outside this normal selected source. Actual called and canonical registered sources have independent complete programs; no pointer alias is asserted.')


def _derive(image,pins,parent,*,count_limit=None):
    """Fresh nominal Vector2 parent, generic contexts and complete wire proof."""
    import json
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack import scalar_param_native as scalar,float_list_sources,lang_key_list_sources,numeric_list_sources
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.levelscript_param_graph_sources import _body_target
    from scripts.game_data.memorypack.skill_value_list_context import derive as list_context
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    if count_limit is not None and(type(count_limit)is not int or not 3<=count_limit<=10000):
        raise ValueError('Vector2List.literal-strict-induction-limit')
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image)
    need=lambda k,e,a:scalar.need('airwallVector2List',k,e,a)
    element_type='UnityEngine.Vector2'
    context,body=list_context(image,pins,typed_request=parent['typedRequest'],
        call_target=parent['source']['sourceTarget'],element_type=element_type)
    td=ctx.index.types['MemoryPack.Formatters.UnmanagedFormatter`1']
    callback,=[m for m in md.methods_for(td)if md.string(m.name_index)=='Deserialize']
    registration=json.loads(json.dumps(ge.resolve(callback.index,[element_type],[])))
    element=owned(image,registration['pointer'])
    need('exact-same-value-element-instantiation',context['registration']['classInstantiation']['arguments'],
        registration['classInstantiation']['arguments'])
    # A collection's nominal layout is independent of a sibling record's
    # ReadUnmanaged call. The actual callback/Add programs below own raw8 wire
    # and payload transfers; these metadata checks grant no wire grammar.
    definition=ctx.index.types[element_type]
    need('nominal-Vector2-value-parent',(True,'System.ValueType',-1),
        (ctx.is_value_type(element_type),ctx.parent(element_type),definition.generic_container_index))
    fields=[f for f in md.fields_for(definition)if not ctx.field_attributes(f.type_index)&16]
    layout=[list(ctx.field(element_type+'::'+md.string(f.name_index)))[1:]for f in fields]
    need('nominal-Vector2-two-Single-layout',[['float',16],['float',20]],layout)
    need('nominal-Vector2-field-names',['x','y'],[md.string(f.name_index)for f in fields])
    for field in fields:scalar.ordinary(image,ctx.type_pointer(field.type_index),12,'airwallVector2List.field')
    need('nominal-Vector2-size-table-range',True,0<=definition.index<image.registration['typeDefinitionsSizesCount'])
    size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+definition.index*8)
    need('nominal-Vector2-boxed-and-native-bytes',(24,8),(image.pe.u32_at_va(size),image.pe.u32_at_va(size+4)))
    s={role:_body_target(body,text)for role,text in(
        ('context','mov rcx, [rcx+0xc0]'),('allocate','mov rcx, rax'),
        ('constructor','mov r8, [r8+0x8]'),('barrier','mov [r12], rdi'),
        ('provider','mov rcx, [rcx+0x18]'),('prepare','mov rcx, [rsi]'),('add','mov r8, [r8+0x30]'))}
    s['callback']=element['pointer']
    programs,loop_induction=_list_programs(body['regions'],body['pointer'],s,count_limit=count_limit)
    callback_program=formatter_program(element['regions'],element['pointer']);add=owned(image,s['add'])
    add_proof=add_program(add['regions'],add['pointer']);constructor=owned(image,s['constructor'])
    slots={r['relativeSlot']:r for r in context['context']['entries']}
    list_method,=[m for m in md.methods_for(ctx.index.types['MemoryPack.Formatters.ListFormatter`1'])if md.string(m.name_index)=='Deserialize']
    definitions=dict(list=list_method.index,callback=callback.index,
        capacity=slots[1]['methodSpec'][0],Clear=slots[2]['methodSpec'][0],Add=slots[6]['methodSpec'][0])
    abis=float_list_sources._method_abis(image,ctx,definitions,context['context'])
    registrations={role:ge.resolve(definition,[element_type],[])for role,definition in definitions.items()}
    need('actual-closed-capacity-constructor',s['constructor'],registrations['capacity']['pointer'])
    canonical_add=owned(image,registrations['Add']['pointer'])
    canonical_add_proof=add_program(canonical_add['regions'],canonical_add['pointer'],canonical=True)
    cs=dict(context=s['context'],barrier=s['barrier'],arrayAllocate=_body_target(constructor,'mov rcx, rax'))
    constructors=[float_list_sources.capacity_program(constructor['regions'],constructor['pointer'],cs,positive=p)for p in(False,True)]
    for proof in constructors:proof['condition']='Exact current closed List<Vector2> array context; nonnegative unchanged capacity, typed zeroed allocation or ready static empty array, normal context/barrier ABI. Raw8 element width comes only from independent nominal Vector2/callback/Add programs.'
    provider_context=ContextSymbols(image).context(slots[3]['methodSpec'][0],is_method=True)
    validate_generic_contexts(image,[provider_context],label='airwallVector2List.provider')
    provider_slots={r['relativeSlot']:r for r in provider_context['entries']}
    need('owned-provider-slots',[0,1],sorted(provider_slots))
    provider_method=md.methods[provider_context['definition']]
    need('provider-static-no-arguments',(True,0),(bool(provider_method.flags&16),provider_method.parameter_count))
    need('provider-owned-return',ctx.type_pointer(provider_method.return_type),ctx.type_pointer(provider_slots[1]['index']))
    need('provider-formatter-result','MemoryPack.MemoryPackFormatter`1',provider_slots[1]['type']['definition']['name'])
    for child in(provider_slots[0]['type'],provider_slots[1]['type']['classArguments'][0]):
        owner=child['parameterOwner'];need('provider-same-owned-MVAR',(provider_method.index,0),(owner['methodIndex'],owner['ordinal']))
    provider=owned(image,s['provider']);calls=[control_transfer(r)['target']for r in provider['rows']if control_transfer(r)['kind']=='call'][:4]
    need('four-provider-calls',4,len(calls));ps=dict(zip(('typeFromHandle','backend','type','assignable'),calls,strict=True))
    provider_program=float_list_sources.provider_program(provider['regions'],provider['pointer'],ps)
    provider_program['condition']='Exact current Vector2 GetFormatter closed context; ready Type/provider, normal TypeFromHandle/backend/indexed returns and actual compatible formatter predicate. No live/default provider selection is observed.'
    from scripts.game_data.contracts import CONTRACTS_DIR
    int_path=CONTRACTS_DIR/'levelscript_int_list_native.json';int_raw=int_path.read_bytes();int_fact=json.loads(int_raw)
    need('shared-Type-key-dependency-pins',pins,int_fact['nativeInputs'])
    backend=owned(image,ps['backend']);backend_target=base+int_fact['bodies']['providerBackend']['entryRva']
    backend_forward=numeric_list_sources.uint_backend_forward_program(backend['regions'],backend['pointer'],backend_target)
    factory=lang_key_list_sources.generic_provider_factory(image,pins,
        dict(backend=backend_target,context=s['context']),need)
    need('same-indexed-provider-context',s['context'],ps['type'])
    # Bind each RIP class cell to the actual named metadata, rather than infer
    # type or provider ownership from an equal target or generic method name.
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    usages=[]
    for source,cell,name in((body,programs[1]['providerClassCell'],'MemoryPack.MemoryPackFormatterProvider'),
            (provider,provider_program['providerClassCell'],'System.Type'),
            (provider,provider_program['rootClassCell'],'MemoryPack.MemoryPackFormatterProvider'),
            (backend,backend_forward['providerOwnerCell'],'MemoryPack.MemoryPackFormatterProvider')):
        rows=[r for r in source['rows']if len(bytes.fromhex(r['bytes']))==7 and bytes.fromhex(r['bytes'])[:3]==b'\x48\x8b\x0d'
            and int(r['va'],16)+7+int.from_bytes(bytes.fromhex(r['bytes'])[3:],'little',signed=True)==cell]
        row,=rows;usage=derive_typed_usage_context(image,int(row['va'],16)-base,label='airwallVector2List.providerCell')
        need('actual-named-provider-cell',(1,name),(usage['tag'],usage['typeName']));usages.append(usage)
    need('same-Type-key-provider',factory['providerClassCell'],programs[1]['providerClassCell'])
    need('same-actual-wrapper-provider-owner',factory['providerClassCell'],backend_forward['providerOwnerCell'])
    need('Type-key-dependency-bookend',int_raw,int_path.read_bytes())
    barrier,barrier_proof,_=_fast_barrier(image,s['barrier'])
    result=dict(nativeInputs=pins,elementType=element_type,parent=parent,context=context,
        listPrograms=programs,callback=callback_program,callbackRegistration=registration,methodAbis=abis,
        registrations=registrations,Add=add_proof,canonicalAdd=canonical_add_proof,
        actualAddTargetRva=s['add']-base,constructors=constructors,provider=provider_program,
        providerContext=provider_context,providerUsages=usages,genericProviderFactory=factory,
        actualBackendForward=backend_forward,canonicalBackendTargetRva=backend_target-base,
        barrier=dict(source=barrier,proof=barrier_proof),symbolRvas={k:v-base for k,v in s.items()},
        sourceWindows=dict(list=body['windows'],callback=element['windows'],Add=add['windows'],canonicalAdd=canonical_add['windows'],
            constructor=constructor['windows'],provider=provider['windows'],backendForward=backend['windows']),
        capability=dict(closedListType=context['closedListType'],countLimit=65536 if count_limit is None else count_limit,headerBytes=4,
            counts='-1-or-nonnegative',managedElementBytes=8,elementWireBytes=8,
            recordHeaderBytes=0,wholeGrammarAdmitted=True),wholeOwnerAdmitted=False,
        liveFormatterSelectionObserved=False)
    if loop_induction is not None:result['loopInduction']=loop_induction
    return json.loads(json.dumps(result))


def derive_collection(image,pins,*,typed_request,call_target,count_limit=None):
    """Own a fresh exact Vector2 collection without borrowing a host field.

    The caller must independently prove the supplied actual request/E8/store.
    This component revalidates its selected closed request, actual helper,
    nominal layout and complete callback/count/constructor/Add source joins.
    """
    return _derive(image,pins,dict(typedRequest=typed_request,source=dict(sourceTarget=call_target),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False),count_limit=count_limit)


def derive(image,pins,geometry):
    """Preserve the separately owned AirWall parent and two value-source joins."""
    from scripts.game_data.memorypack.vector2_source import validate_vector2_source
    from scripts.game_data.memorypack import scalar_param_native as scalar
    need=lambda k,e,a:scalar.need('airwallVector2List',k,e,a)
    need('same-current-geometry-pins',pins,geometry['nativeInputs']);base=image.pe.image_base
    children=geometry['records']['Beyond.Gameplay.PolyLineWall']['children']
    parent,=[c for c in children if c['fieldName']=='posList']
    vectors=[c for c in children if c['typeName']=='UnityEngine.Vector2']
    need('both-independent-Vector2-fields',2,len(vectors))
    for vector in vectors:
        need('same-nominal-Vector2-source','validated',vector['sourceProof']['status'])
        need('nominal-Vector2-argument',['UnityEngine.Vector2'],vector['typedRequest']['methodArguments'])
        fresh=validate_vector2_source(image,vector['typedRequest'],vector['source']['sourceTarget']-base)
        need('fresh-complete-nominal-Vector2-source',vector['sourceProof'],fresh)
    return _derive(image,pins,parent)

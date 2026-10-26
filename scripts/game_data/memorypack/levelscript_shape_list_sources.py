"""Exact current Shape44 list loop and Add; wire grammar stays child-owned."""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.levelscript_shape_sources import TYPE


def list_program(regions,entry,s,*,count=-1):
    if type(count)is not int or count not in(-1,0,1,2):raise ValueError('levelScriptShapeList.count-witness')
    g=BytesPath(regions,entry);loops=[];loop=None;backedge=None
    g.take('4c8bdc','53','55','56','57','4881eca8000000','0f57c0','488bea','33c0',
        '498d5310','0f11442440','33ff','488bcd','0f11442450','49894398','498bf1',
        '89442468','498bd8','41897b10');g.call(s['header']);g.take('84c0');g.branch('0f84',count==-1)
    if count==-1:
        g.take('488bcb','48893b');g.call(s['barrier'])
    else:
        g.take('4c89bc24a0000000','4c89a424d0000000','4c89ac24e0000000','4c89b424e8000000',
            '448bbc24d8000000','48393b');g.branch('0f85',False)
        g.take('488b4e20','33d2','488b89c0000000');g.call(s['context'])
        g.take('488bc8');g.call(s['allocate']);g.take('4c8bf0','4885c0');g.branch('0f84',False)
        g.take('488b4e20','488b91c0000000','488b4a08','48397920');g.branch('0f84',False)
        g.take('488b4620','418bd7','498bce','4c8b80c0000000','4d8b4008');g.call(s['constructor'])
        g.take('488bcb','4c8933');g.call(s['barrier'])
        provider=dict(instruction=g.at,cell=g.relative('488b0d'))
        g.take('39b9e0000000');g.branch('0f84',False)
        g.take('488b4620','488b88c0000000','488b4918');g.call(s['provider'])
        g.take('4c8bf0','4585ff');g.branch('0f8e',count==0)
        if count:
            loop=g.at
            for index in range(count):
                if g.at!=loop:raise ValueError('levelScriptShapeList.same-loop-entry')
                before=len(g.seen)
                g.take('33c0','0f57c0','4889442460','89442468','0f11442440','0f11442450','4d85f6')
                g.branch('0f84',False)
                g.take('4c8d4c2440','4c8bc5','498bd6');g.call(s['dispatch'])
                g.take('0f10442440','4c8b23','f20f10542460','448b6c2468','f20f119424d8000000',
                    '0f104c2450','0f11442420','0f114c2430','4d85e4');g.branch('0f84',False)
                g.take('488b4620','488b88c0000000','488b4130','4883782000');g.branch('0f84',False)
                g.take('488b4620','488d542470','498bcc','0f29442470','0f298c2480000000',
                    'f20f11942490000000','4c8b80c0000000','4489ac2498000000','4d8b4030')
                g.call(s['add']);g.take('ffc7','413bff');backedge=g.at;g.branch('0f8c',index+1<count)
                loops.append(g.seen[before:])
        g.take('4c8bb424e8000000','4c8bac24e0000000','4c8ba424d0000000','4c8bbc24a0000000')
    g.take('4881c4a8000000','5f','5e','5d','5b','c3')
    if count==2 and loops[0]!=loops[1]:raise ValueError('levelScriptShapeList.identical-repeated-loop')
    return dict(selectedBytes=g.seen,countWitness=count,newList=count!=-1,
        headerBytes=4,callbackManagedBytes=44,wireElementBytes=None,loopBodies=loops,
        loopEntry=loop,loopBackEdge=backedge,normalReturn=True,entryFrameRestored=True,
        typedCapacityFromSameCount=True,callbackOutputStackOffset=64,AddInputStackOffset=112,
        completeCallbackToAddBytes=44,positiveGrowthAdmitted=False,
        savedCount='signed R15D loaded once from collection helper output RSP+216',
        counter='EDI starts zero before header/helper calls, increments exactly once after Add, signed compares unchanged R15D',
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)


def add_program(regions,entry):
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec50','ff411c','488bd9','4c8b4910',
        '498bf0','48634918','488bfa','4d85c9');g.branch('0f84',False)
    g.take('413b4918');g.branch('72',True,1)
    g.take('8d4101','894318','413b4918');g.branch('73',False,1)
    g.take('0f1002','8b4228','0f104a10','486bc92c','420f11440920','f20f104220',
        '420f114c0930','f2420f11440940','4289440948');g.jump('eb',1)
    g.take('488b5c2460','488b742468','4883c450','5f','c3')
    return dict(selectedBytes=g.seen,arrayStride=44,arrayDataOffset=32,
        input='incoming RDX pointer to unchanged caller-owned value44',completeCopiedBytes=44,
        itemsOffset=16,countOffset=24,versionOffset=28,countIncrement=1,versionIncrement=1,
        initialCountLessThanCapacity=True,growthAdmitted=False,normalReturn=True,entryFrameRestored=True)


def provider_program(regions,entry,s):
    """Actual initialized provider returns the same checked backend reference."""
    g=BytesPath(regions,entry)
    g.take('48895c2410','57','4883ec20','4883793800','488bf9');g.branch('74',False,1)
    type_class=g.relative('488b0d');g.take('488b5f38','83b9e000000000','488b1b');g.branch('0f84',False)
    g.take('33d2','488bcb');g.call(s['typeHandle']);provider_class=g.relative('488b0d')
    g.take('488bd8','83b9e000000000');g.branch('0f84',False)
    g.take('488bcb');g.call(s['backend']);g.take('488b4f38','ba01000000','488bd8');g.call(s['indexed'])
    g.take('488bd0','488bcb');g.call(s['cast']);g.take('4885c0');g.branch('74',False,1)
    g.take('488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,typeClassCell=type_class,providerClassCell=provider_class,
        typeContextSlot=0,formatterContextSlot=1,nonnullCompatibleReferenceReturned=True,
        normalReturn=True,runtimeProviderSelectionObserved=False)


def derive(image,pins,owners,record,transfer):
    """Bind exact current active/start parents to this nominal value44 list."""
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_generic_contexts
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.levelscript_param_graph_sources import _body_target
    from scripts.game_data.memorypack.skill_value_list_context import derive as list_context,bind_list_add_abi,require_value_element
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack import scalar_param_native as scalar,pooled_global_buff_id_sources
    from scripts.game_data.memorypack.float_list_sources import capacity_program
    from scripts.game_data.memorypack.levelscript_interactive_sources import dictionary_header_program
    from scripts.game_data.memorypack.levelscript_owner_sources import ROOT
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image)
    need=lambda k,e,a:scalar.need('levelScriptShapeList',k,e,a)
    need('same-record-transfer',(TYPE,TYPE,pins,pins,44,44),
        (record['typeName'],transfer['typeName'],record['nativeInputs'],transfer['nativeInputs'],
         record['managedBytes'],transfer['managedBytes']))
    parent=owners['owners'][ROOT];parents=[]
    for field,read in zip(parent['fields'],parent['program']['orderedReads'],strict=True):
        if field['name']not in('activeShapeList','startShapeList'):continue
        usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='levelScriptShapeList.parent')
        parents.append(dict(field=field,source=read,typedRequest=usage))
    need('exact-two-shape-parents',2,len(parents))
    context,body=list_context(image,pins,typed_request=parents[0]['typedRequest'],
        call_target=parents[0]['source']['sourceTarget'],element_type=TYPE)
    for parent in parents:
        need('same-actual-parent-source',context['callTargetRva'],parent['source']['sourceTarget']-base)
        need('same-closed-list-request',[context['closedListType']],parent['typedRequest']['methodArguments'])
        request=parent['typedRequest']
        bind_typed_read(image,request,method_name='ReadPackable',argument=context['closedListType'],kind=21,reference=True)
        argument,=image.instantiations.resolve(request['methodSpec'][2]).arguments
        carrier=ContextSymbols(image).type(argument.type_pointer_va);element,=carrier['classArguments']
        require_value_element(bytes.fromhex(element['rawHex']),ctx.index.types[TYPE].index)
    need('same-current-list-registration',context['registration'],transfer['listRegistration'])
    slots={r['relativeSlot']:r for r in context['context']['entries']}
    s=dict(header=_body_target(body,'test al, al',before=True),context=_body_target(body,'mov rcx, [rcx+0xc0]'),
        allocate=_body_target(body,'mov rcx, rax'),constructor=_body_target(body,'mov r8, [r8+0x8]'),
        barrier=_body_target(body,'mov [rbx], r14'),provider=_body_target(body,'mov rcx, [rcx+0x18]'),
        dispatch=_body_target(body,'mov rdx, r14'),add=_body_target(body,'mov r8, [r8+0x30]'))
    sources={name:owned(image,target)for name,target in s.items()if name not in('context','barrier')}
    programs=[list_program(body['regions'],body['pointer'],s,count=n)for n in(-1,0,1,2)]
    need('actual-child-dispatch',transfer['symbolRvas']['dispatch'],s['dispatch']-base)
    add=add_program(sources['add']['regions'],s['add']);abi=bind_list_add_abi(image,slots[6]['methodSpec'][0])
    constructor=sources['constructor'];constructor_symbols=dict(context=s['context'],barrier=s['barrier'],
        arrayAllocate=_body_target(constructor,'mov rcx, rax'))
    constructors=[capacity_program(constructor['regions'],constructor['pointer'],constructor_symbols,positive=x)for x in(False,True)]
    for proof in constructors:proof['condition']='Exact current closed List<LevelScriptShape> owned array context; nonnegative capacity, typed zeroed allocation or initialized static empty array and normal compatible context/barrier helpers. Managed/wire sizes come only from independent Shape/GetValue/Add/source proofs.'
    ctor_definition=slots[1]['methodSpec'][0];registered_ctor=ge.resolve(ctor_definition,[TYPE],[])
    need('exact-closed-capacity-constructor',registered_ctor['pointer'],s['constructor'])
    offsets=scalar.reader_offsets(image,'levelScriptShapeList')
    offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    header=dictionary_header_program(sources['header']['regions'],s['header'],offsets)
    calls=[control_transfer(r)['target']for r in sources['provider']['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8'][:4]
    need('four-normal-provider-calls',4,len(calls));ps=dict(zip(('typeHandle','backend','indexed','cast'),calls,strict=True))
    provider=provider_program(sources['provider']['regions'],s['provider'],ps)
    need('same-selected-type-handle',transfer['symbolRvas']['typeHandle'],ps['typeHandle']-base)
    need('same-indexed-context-helper',s['context'],ps['indexed'])
    cast=owned(image,ps['cast']);predicate=_body_target(cast,'mov rcx, [rcx]')
    cast_proof=pooled_global_buff_id_sources.successful_cast(cast['regions'],cast['pointer'],predicate)
    backend=owned(image,ps['backend']);tails=[control_transfer(r)['target']for r in backend['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe9']
    need('one-provider-backend-tail',1,len(tails))
    backend_proof=pooled_global_buff_id_sources.backend_bridge(backend['regions'],backend['pointer'],tails[0])
    provider_context=ContextSymbols(image).context(slots[3]['methodSpec'][0],is_method=True)
    validate_generic_contexts(image,[provider_context],label='levelScriptShapeList.provider')
    pcs={r['relativeSlot']:r for r in provider_context['entries']};need('provider-context-slots',[0,1],sorted(pcs))
    for child in(pcs[0]['type'],pcs[1]['type']['classArguments'][0]):
        owner=child['parameterOwner'];need('same-provider-MVAR',(provider_context['definition'],0),(owner['methodIndex'],owner['ordinal']))
    barrier,barrier_proof,_=_fast_barrier(image,s['barrier'])
    return json.loads(json.dumps(dict(nativeInputs=pins,elementType=TYPE,parents=parents,context=context,
        programs=programs,Add=add,AddDeclaration=abi,constructors=constructors,constructorRegistration=registered_ctor,
        header=header,provider=provider,providerContext=provider_context,cast=cast_proof,backend=backend_proof,
        barrier=dict(source=barrier,proof=barrier_proof),symbolRvas={k:v-base for k,v in s.items()},
        sourceWindows=dict(list=body['windows'],**{k:v['windows']for k,v in sources.items()},cast=cast['windows'],backend=backend['windows']),
        capability=dict(closedListType=context['closedListType'],countLimit=64,headerBytes=4,
            nullable=True,counts='-1-or-nonnegative',managedElementBytes=44,recordWireBytes=45,
            nullElementBytes=1,nullReturnsZero44=True,wholeGrammarAdmitted=True),
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))

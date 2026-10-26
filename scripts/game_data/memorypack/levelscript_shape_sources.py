"""Exact current LevelScriptShape44 record, transfer and collection sources."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag

TYPE='Beyond.Gameplay.Core.LevelScriptShape'
FIELDS=(('eulerAngles','UnityEngine.Vector3',32),('offset','UnityEngine.Vector3',20),
    ('radius','float',56),('size','UnityEngine.Vector3',44),
    ('type','Beyond.GEnums.LevelScriptShapeType',16))


def record_program(regions,entry,o,s,*,null=False,new=False):
    if type(null)is not bool or type(new)is not bool:raise ValueError('levelScriptShape.literal-profile')
    if o!={'currentPtr':80,'bufferLength':48,'advancedCount':64,'consumed':68}:
        raise ValueError('levelScriptShape.reader-layout')
    g=BytesPath(regions,entry);allocation=None;reads=[]
    def guard():
        prefix=bytes(g.bytes.get(g.at+i,0)for i in range(2))
        if prefix==b'\x0f\x84':g.branch('0f84',False)
        else:g.branch('74',False,1)
    def vector(field):
        site=g.at;g.call(s['vector3']);g.take('4885f6');guard()
        reads.append(dict(fieldName=field,sourceCall=site,kind='vector3'))
    def usage():return dict(instruction=g.at,cell=g.relative('4c8b05'))
    g.take('48895c2418','57','4883ec30');ready=flag(g)
    g.take('488bda','488bf9');g.branch('0f84',False)
    g.take('488d542440','c644244000','488bcf');g.call(s['header'])
    g.take('84c0');g.branch('0f84',null)
    if null:
        g.take('488bcb','48c70300000000');g.call(s['barrier']);g.take('90');g.jump('e9')
    else:
        g.take('4889742448','48833b00');g.branch('0f84',new)
        if new:
            allocation=dict(instruction=g.at,cell=g.relative('488b0d'));g.call(s['allocate'])
            g.take('4885c0');g.branch('0f84',False)
            g.take('33c9','0f57c0','0f114010','0f114020','48894830','894838',
                '488bcb','488903');g.call(s['barrier']);g.take('90');g.jump('e9')
        g.take('0fb6742440','4080fe05');g.branch('0f85',False)
        context=usage();g.take('488d4c2420','488b33','488bd7');vector('eulerAngles')
        reads[-1]['typedUsage']=context
        g.take('f20f10442420','488d4c2420','8b442428','488bd7','f20f114620','894628')
        context=usage();g.take('488b33');vector('offset');reads[-1]['typedUsage']=context
        g.take('f20f10442420','488bcf','8b442428','f20f114614','89461c','488b33')
        site=g.at;g.call(s['single']);g.take('4885f6');guard();g.take('f30f114638')
        reads.append(dict(fieldName='radius',sourceCall=site,kind='single'))
        g.take('488d4c2420');context=usage();g.take('488bd7','488b33');vector('size')
        reads[-1]['typedUsage']=context
        g.take('f20f10442420','488bcf','8b442428','f20f11462c','894634')
        context=dict(instruction=g.at,cell=g.relative('488b15'));g.take('488b1b')
        site=g.at;g.call(s['enum32']);g.take('4885db');guard()
        g.take('488b742448','894310')
        reads.append(dict(fieldName='type',sourceCall=site,kind='enum32',typedUsage=context))
    g.take('488b5c2450','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,null=null,newWrapper=None if null else new,
        typedAllocation=allocation,orderedReads=reads,wrapperHeaderBytes=1,
        wireBytes=1 if null else 45,managedBytes=44,normalReturn=True,entryFrameRestored=True,
        originalDefaultFromWrapperFFAdmitted=False,liveFormatterSelectionObserved=False)


def derive_record(image,pins):
    import json
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.protocol import native_enum_members
    from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    from scripts.game_data.memorypack.pointer_param import owned,methods,leaf,registered_pair
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.memorypack.vector3_source import validate_vector3_source
    from scripts.game_data.memorypack.levelscript_param_graph_sources import _body_target
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    need=lambda k,e,a:scalar.need('levelScriptShape',k,e,a)
    wrapper,=[w for w in derive_from_image(image).values()if w.wrapped_type==TYPE]
    need('value-original',True,ctx.is_value_type(TYPE))
    need('members',[(n,t)for n,t,_ in FIELDS],[(m.name,m.declared_type)for m in wrapper.members])
    need('fields',[(TYPE,t,o)for _,t,o in FIELDS],[ctx.field(TYPE+'::'+n)for n,_,_ in FIELDS])
    need('inline-wrapper-holder',(wrapper.name,TYPE,16),ctx.field(wrapper.name+'::__instance'))
    size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+ctx.index.types[TYPE].index*8)
    need('boxed-extent',60,image.pe.u32_at_va(size))
    mm=methods(image,wrapper);method=mm['Deserialize'];primitive_param.reader_abi(image,ctx,method,wrapper)
    source=owned(image,image.method_pointer_va(method));o=scalar.reader_offsets(image,'levelScriptShape')
    s=dict(header=_body_target(source,'test al, al',before=True),
        vector3=_body_target(source,'movsd [rsi+0x20], xmm0',before=True),
        single=_body_target(source,'movss [rsi+0x38], xmm0',before=True),
        enum32=_body_target(source,'mov [rbx+0x10], eax',before=True),
        barrier=_body_target(source,'mov [rbx], 0x0'),
        allocate=_body_target(source,'test rax, rax',before=True))
    programs=[record_program(source['regions'],source['pointer'],o,s,**kw)
        for kw in(dict(null=True),dict(new=True),dict(new=False))]
    pair=derive_pair(image,TYPE);forwarding=registered_pair(image,pair,wrapper,label='levelScriptShape.pair')
    scalar.owned_method_abi(image,ctx,mm['GetValue'].index,wrapper.type_definition,(TYPE,17,False),[],
        'levelScriptShape.getter')
    getter=leaf(image,image.method_pointer_va(mm['GetValue']),[
        '0F104210','8B4238','0F104A20','0F1101','F20F104230','0F114910','F20F114120','894128','488BC1','C3'])
    constructors={name:leaf(image,image.method_pointer_va(mm[name]),[
        '0F57C0','33C0','0F114110','0F114120','48894130','894138','C3'])for name in('.ctor','CreateInstance')}
    allocation=programs[1]['typedAllocation'];typed=derive_typed_usage_context(image,allocation['instruction']-base,
        label='levelScriptShape.wrapper-allocation')
    need('typed-wrapper-allocation',(1,wrapper.name),(typed['tag'],typed['typeName']))
    rec=vector_recorder(image);header=rec(s['header']-base);primitive_param.object_header_source(image,header,o)
    single=rec(s['single']-base);primitive_param.single_source(image,single,o)
    enum=rec(s['enum32']-base);scalar.integer_source(image,enum,o,'levelScriptShape.enum',width=4)
    need('int32-enum-backing','int',ctx.field(FIELDS[-1][1]+'::value__')[1])
    requests=[]
    for read in programs[-1]['orderedReads']:
        if read.get('typedUsage')is None:continue
        usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='levelScriptShape.member')
        expected='UnityEngine.Vector3'if read['kind']=='vector3'else FIELDS[-1][1]
        need('exact-typed-read',('ReadUnmanaged',[expected]),(usage['methodName'],usage['methodArguments']))
        requests.append(dict(fieldName=read['fieldName'],typedRequest=usage,
            source=validate_vector3_source(image,usage,s['vector3']-base)if read['kind']=='vector3'else None))
    barrier,barrier_proof,_=_fast_barrier(image,s['barrier'])
    enums=native_enum_members(md,image.body_index.enum_defaults,image.pe,image.registration,FIELDS[-1][1])
    return json.loads(json.dumps(dict(nativeInputs=pins,typeName=TYPE,managedBytes=44,
        profile=pair,forwarding=forwarding,sourceWindows=source['windows'],programs=programs,
        constructors=constructors,getter=getter,typedAllocation=typed,typedMembers=requests,
        header=header,single=single,enum32=enum,shapeTypeMembers=enums,
        barrier=dict(source=barrier,proof=barrier_proof),symbolRvas={k:v-base for k,v in s.items()},
        childGrammarAdmitted=True,positiveCollectionAdmitted=False,wholeOwnerAdmitted=False,
        liveFormatterSelectionObserved=False)))


def getter_invoke_program(regions,entry,prepare,*,ordinal):
    if type(ordinal)is not int or not 0<=ordinal<=16:raise ValueError('levelScriptShape.interface-ordinal')
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','48897c2418','4156','4883ec50','498b39',
        '488bf1','488bcf','4d8bf1','498bd8');g.call(prepare)
    g.take('440fb78730010000','33c0','66413bc0');g.branch('73',False,1)
    g.take('488b97b0000000')
    for index in range(ordinal+1):
        g.take('0fb7c8','4803c9','48391cca');g.branch('74',index==ordinal,1)
        if index<ordinal:g.take('66ffc0','66413bc0');g.branch('72',True,1)
    g.take('0fb7c8','4803c9','486344ca08','4883c014','48c1e004','4803c7',
        '4c8b08','488d4c2420','4c8b4008','498bd6','41ffd1','488b5c2460','488b7c2470',
        '0f1000','0f104810','0f1106','f20f104020','8b4028','0f114e10','f20f114620',
        '894628','488bc6','488b742468','4883c450','415e','c3')
    return dict(selectedBytes=g.seen,interfaceOrdinal=ordinal,conversionMethodSlot=0,
        incomingSelectorUsed=False,hiddenOutput='incoming RCX -> preserved RSI -> returned RAX',
        wrapper='incoming R9 -> preserved R14 -> getter RDX',completeCopiedBytes=44,
        getterReturnsSameOutputPointerRequired=True,normalReturn=True,entryFrameRestored=True)


def conversion_program(regions,entry,s,*,wrapper_null=False):
    if type(wrapper_null)is not bool:raise ValueError('levelScriptShape.wrapper-null-profile')
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','4c89442418','57','4883ec50');ready=flag(g)
    g.take('498bf9','488bf2','488bd9');g.branch('0f84',False)
    provider= g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
    g.take('488b4f20');g.call(s['resolve']);g.take('488b88c0000000','488b4920');g.call(s['wrapperProvider'])
    g.take('4885c0');g.branch('0f84',False)
    g.take('b905000000','4c8d4c2470','4c8bc3','488bd0');g.call(s['wrapperInvoke'])
    g.take('488b5c2470','4885db');g.branch('0f84',wrapper_null)
    if wrapper_null:
        g.take('0f57c0','33c0','0f1106','0f114610','48894620','894628');g.jump('e9')
    else:
        g.take('488b4f20');g.call(s['resolve'])
        g.take('ba08000000','488b88c0000000');g.call(s['indexed'])
        g.take('4c8bc0','488d4c2420','4c8bcb');g.call(s['getterInvoke'])
        g.take('0f1008','8b4828','0f105010','f20f104020','0f110e','0f115610',
            'f20f114620','894e28')
    g.take('488b5c2460','488b742468','4883c450','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,providerClassCell=provider,
        wrapperNull=wrapper_null,wrapperProviderContextSlot=4,conversionInterfaceContextSlot=8,
        wrapperReadOutput='local reference RSP+112',sameIncomingReaderAndOutput=True,
        completeCopiedBytes=0 if wrapper_null else 44,defaultZeroBytes=44 if wrapper_null else 0,
        normalReturn=True,entryFrameRestored=True)


def adapter_program(regions,entry,s,*,dispatch=False,null=False,skip_activation=False):
    if any(type(x)is not bool for x in(dispatch,null,skip_activation)):
        raise ValueError('levelScriptShape.adapter-profile')
    g=BytesPath(regions,entry)
    if dispatch:
        g.take('48895c2408','48896c2410','4889742418','57','4883ec20','488b0a',
            '498be9','498bf0','488bda');g.call(s['prepare'])
        g.take('488b3b')
        if g.relative('488d0d')!=s['adapter']:raise ValueError('levelScriptShape.canonical-compared-pointer')
        g.take('488b8790010000','488bbf98010000','483bc1');g.branch('0f85',False)
        ready=flag(g);g.branch('0f84',False)
    else:
        g.take('48896c2410','4889742418','57','4883ec20');ready=flag(g)
        g.take('498bf9','498be8','488bf2');g.branch('0f84',False)
    g.take('488b4720','488bce','488b90c0000000','488b12');g.call(s['peek'])
    g.take('84c0');g.branch('0f85',null)
    if null:
        g.take('0f57c0','33c0','0f114500','0f114510','48894520','894528');g.jump('e9')
    else:
        if not dispatch:g.take('48895c2430')
        g.take('488b4720');type_class=g.relative('488b0d')
        g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('74',False,1)
        g.take('33d2','488bcb');g.call(s['typeHandle'])
        if not dispatch:g.take('488b5c2430')
        g.take('4885c0');g.branch('74',False,1)
        g.take('33d2','488bc8');g.call(s['creationTest'])
        g.take('84c0');g.branch('75',skip_activation,1)
        if skip_activation:g.take('33c0');g.jump('eb',1)
        else:
            g.take('488b4720','488b88c0000000','488b4958');g.call(s['activate'])
        g.take('488b4f20','4c8bc0','488bd5','4c8b89c0000000','488bce','4d8b4918');g.call(s['conversion'])
    if dispatch:g.take('488b5c2430','488b6c2438','488b742440')
    else:g.take('488b6c2438','488b742440')
    g.take('4883c420','5f','c3')
    return dict(selectedBytes=g.seen,dispatch=dispatch,null=null,skipActivation=None if null else skip_activation,
        metadataReadyFlag=ready,managedOutputBytes=44,wireBytes=1 if null else None,
        defaultZeroBytes=44 if null else 0,normalReturn=True,entryFrameRestored=True,
        actualFixedSlot=5 if dispatch else None,selectorUsed=False if dispatch else None,
        sameIncomingReaderAndOutput=True,liveCallbackSelectionObserved=False)


def derive_transfer(image,pins,record):
    """Own this nominal managed44 pair and its actual selected list dispatcher."""
    import json,struct
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
    from scripts.game_data.memorypack import scalar_param_native as scalar,animation_mask_sources,event_args_paths,primitive_param
    from scripts.game_data.memorypack.buff_ptr_sources import _adapter_context,_definition
    from scripts.game_data.memorypack.pointer_param import owned,methods
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.memorypack.levelscript_param_graph_sources import _body_target
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image)
    need=lambda k,e,a:scalar.need('levelScriptShape.transfer',k,e,a)
    need('record-type-and-build',(TYPE,pins,44),(record['typeName'],record['nativeInputs'],record['managedBytes']))
    wrapper,=[w for w in derive_from_image(image).values()if w.wrapped_type==TYPE]
    pair=record['profile'];face,=pair['composition']['interfaces'];td=md.types[face['wrapperDefinition']]
    section=md.sections['interfaceOffsets'];start=section.offset+td.interface_offsets_start*8
    offsets=list(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8]))
    ordinal=offsets.index((face['interfaceTypeIndex'],face['interfaceOffset']))
    canonical=ge.resolve(_definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2','Deserialize').index,[TYPE,'object'],[])
    list_entry=ge.resolve(_definition(image,'MemoryPack.Formatters.ListFormatter`1','Deserialize').index,[TYPE],[])
    body=owned(image,canonical['pointer']);list_body=owned(image,list_entry['pointer'])
    dispatch_target=_body_target(list_body,'mov rdx, r14')
    s=dict(adapter=canonical['pointer'],dispatch=dispatch_target,
        peek=_body_target(body,'test al, al',before=True),
        typeHandle=_body_target(body,'test rax, rax',before=True),
        creationTest=_body_target(body,'mov rcx, rax'),
        activate=_body_target(body,'mov rcx, [rcx+0x58]'),
        conversion=_body_target(body,'mov r9, [r9+0x18]'))
    sources=dict(adapter=body,list=list_body,dispatch=owned(image,dispatch_target),conversion=owned(image,s['conversion']))
    conv=sources['conversion'];s.update(resolve=_body_target(conv,'mov rcx, [rdi+0x20]'),
        wrapperProvider=_body_target(conv,'mov rcx, [rcx+0x20]'),
        wrapperInvoke=_body_target(conv,'mov rdx, rax'),indexed=_body_target(conv,'mov edx, 0x8'),
        getterInvoke=_body_target(conv,'mov r9, rbx'))
    sources['getterInvoke']=owned(image,s['getterInvoke'])
    s['prepare']=_body_target(sources['getterInvoke'],'mov rbx, r8')
    paths={name:[adapter_program(source['regions'],source['pointer'],s,dispatch=name=='dispatch',**kw)
        for kw in(dict(null=True),dict(skip_activation=False),dict(skip_activation=True))]
        for name,source in sources.items()if name in('adapter','dispatch')}
    conversions=[conversion_program(conv['regions'],conv['pointer'],s,wrapper_null=x)for x in(False,True)]
    getter=getter_invoke_program(sources['getterInvoke']['regions'],sources['getterInvoke']['pointer'],s['prepare'],ordinal=ordinal)
    invocation=owned(image,s['wrapperInvoke']);sources['wrapperInvoke']=invocation
    callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']])
    invoked=deserialize_slot(invocation['regions'],invocation['pointer'],prepare=s['prepare'],callback=callback)
    peek=owned(image,s['peek']);sources['peek']=peek
    null_symbols=dict(peek=_body_target(peek,'test al, al',before=True),
        objectHeader=_body_target(peek,'mov rcx, rbx'))
    null_paths=[animation_mask_sources.null_program(peek['regions'],peek['pointer'],null_symbols,null=n)for n in(False,True)]
    offsets=scalar.reader_offsets(image,'levelScriptShape.transfer')
    peek_helper=owned(image,null_symbols['peek']);peek_proof=event_args_paths.peek(peek_helper['regions'],peek_helper['pointer'],offsets)
    header=vector_recorder(image)(null_symbols['objectHeader']-base);primitive_param.object_header_source(image,header,offsets)
    context,context_proof=_adapter_context(image,ge)
    need('same-nominal-type-handle',base+pair['registration']['helperMethods']['typeFromHandle'][3],s['typeHandle'])
    return json.loads(json.dumps(dict(nativeInputs=pins,typeName=TYPE,managedBytes=44,
        canonicalRegistration=canonical,listRegistration=list_entry,paths=paths,conversions=conversions,
        getterInvoke=getter,wrapperInvocation=invoked,interfaceOrdinal=ordinal,
        adapterContext=context,adapterContextProof=context_proof,nullSourcePrograms=null_paths,
        peek=peek_proof,peekWindows=peek_helper['windows'],header=header,
        symbolRvas={k:v-base for k,v in s.items()},sourceWindows={k:v['windows']for k,v in sources.items()},
        callbackBinding=dict(actualComparedCanonicalTargetRva=canonical['pointer']-base,
            actualSelectedCallbackEqualsCanonicalRequired=True,runtimeSelectionObserved=False),
        positiveCollectionAdmitted=False,wholeOwnerAdmitted=False)))

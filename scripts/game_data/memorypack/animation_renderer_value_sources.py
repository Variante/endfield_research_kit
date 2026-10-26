"""Own managed8 renderer-prefix value; its String array wire is separate."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Gameplay.View.Animation.AnimationConfigExtraData+AnimationEventRendererVisibilityEntry'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_View_Animation_AnimationConfigExtraData_AnimationEventRendererVisibilityEntryForMemoryPack'
SCHEMA='endfield.animation-renderer-value-source.v1'


def need(check,condition):
    if not condition:raise ValueError('animationRendererValue.'+check)


def getter_program(regions,entry):
    g=BytesPath(regions,entry);g.take('488b4110','c3')
    return dict(selectedBytes=g.seen,managedBytes=8,sourceSlices=[[0,8]],referenceLaneOffsets=[0],
        fullPayloadReturnedRax=True,normalReturn=True,entryRspRestored=True,calleeCalls=0)


def getter_entry(image,owner,getter):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    need('own-metadata-getter',image.type_name(owner.index)==WRAPPER and getter.declaring_type==owner.index)
    scalar.owned_method_abi(image,NativeReferenceContext(image),getter.index,owner.index,(TYPE,17,False),[],'animationRenderer.GetValue')
    at=image.method_pointer_va(getter);return getter_program([(at,image.pe.bytes_at_va(at,5))],at)


def zero_program(regions,entry):
    g=BytesPath(regions,entry);g.take('33c0','48894110','c3')
    return dict(selectedBytes=g.seen,managedBytes=8,zeroedSlices=[[0,8]],normalReturn=True,entryRspRestored=True)


def layout(image,ctx):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    td=ctx.index.types[TYPE];md=image.metadata
    need('own-ordinary-value',ctx.is_value_type(TYPE)and not ctx.is_enum(TYPE)
        and ctx.parent(TYPE)=='System.ValueType'and td.generic_container_index<0)
    fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    actual=[[md.string(f.name_index),*ctx.field(TYPE+'::'+md.string(f.name_index))[1:]]for f in fields]
    need('one-owned-string-array-field',actual==[['rendererNamePrefixes','string[]',16]])
    scalar.ordinary(image,ctx.type_pointer(fields[0].type_index),29,'animationRenderer.arrayField',reference=True)
    at=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
    need('boxed24-without-marshaled-size',(image.pe.u32_at_va(at),image.pe.u32_at_va(at+4))==(24,0xffffffff))
    return dict(typeName=TYPE,typeDefinition=td.index,fields=actual,boxedBytes=24,managedBytes=8,
        marshaledNativeBytes=0xffffffff,marshaledSizeUsedForManagedWidth=False,referenceLaneOffsets=[0],
        paddingByteRanges=[],wireGrammarAdmitted=False)


def adapter_program(regions,entry,s=None,*,null=False,create=True):
    need('literal-canonical-case',type(null)is bool and type(create)is bool)
    g=BytesPath(regions,entry);s={}if s is None else dict(s)
    def call(role):
        target=g.relative('e8');need('same-own-helper:'+role,role not in s or s[role]==target);s[role]=target
    g.take('488bc4','48895808','48896810','48897018','48897820','4156','4883ec20','33ff','498bf1')
    flag=g.relative('40383d');g.take('4d8bf0','488bea');g.branch('75',True,1)
    g.take('488b4620','488bcd','488b90c0000000','488b12');call('readNull');g.take('84c0');g.branch('75',null,1)
    cell=None
    if null:g.take('33c0','498906')
    else:
        g.take('488b4620');cell=g.relative('488b0d');g.take('488b98c0000000','488b5b50');call('classReady')
        g.take('33d2','488bcb');call('typeHandle');g.take('4885c0');g.branch('75',True,1)
        g.take('33d2','488bc8');call('creationTest');g.take('84c0');g.branch('75',not create,1)
        if create:g.take('488b4620','488b88c0000000','488b4958');call('activate');g.take('488bf8')
        g.take('488b4e20','4c8bc7','498bd6','4c8b89c0000000','488bcd','4d8b4918');call('nonnull');g.jump('eb',1)
    g.take('488b5c2430','488b6c2438','488b742440','488b7c2448','4883c420','415e','c3')
    return dict(selectedBytes=g.seen,symbols=s,originalNull=null,createWrapper=None if null else create,
        managedBytes=8,defaultZeroBytes=8 if null else 0,typeClassCell=cell,metadataReadyFlag=flag,
        sameIncomingReaderAndOutput=True,entryRspRestored=True,normalReturn=True)


def nonnull_program(regions,entry,s=None,*,wrapper_null=False,ordinal=0):
    need('literal-interface-case',type(wrapper_null)is bool and type(ordinal)is int and 0<=ordinal<=16)
    g=BytesPath(regions,entry);s={}if s is None else dict(s)
    def call(role):
        target=g.relative('e8');need('same-own-helper:'+role,role not in s or s[role]==target);s[role]=target
    g.take('48895c2408','48896c2410','4c89442418','56','57','4156','4883ec20','33db','498be9')
    flag=g.relative('381d');g.take('488bf2','488bf9');g.branch('75',True,1)
    provider=g.relative('488b0d');call('classReady');g.take('488b4d20');call('resolve')
    g.take('488b88c0000000','488b4920');call('wrapperProvider');g.take('4885c0');g.branch('75',True,1)
    g.take('b905000000','4c8d4c2450','4c8bc7','488bd0');call('wrapperInvoke')
    g.take('488b7c2450','4885ff');g.branch('75',not wrapper_null,1)
    if wrapper_null:g.take('33c0','488906');g.jump('eb',1)
    else:
        g.take('488b4d20');call('resolve');g.take('488b88c0000000','488b4940');call('resolve')
        g.take('488b2f','4c8bf0','488bcd');call('prepare')
        g.take('0fb79530010000','663bda');g.branch('73',False,1);g.take('488b8db0000000')
        for index in range(ordinal+1):
            g.take('0fb7c3','4803c0','4c3934c1');g.branch('74',index==ordinal,1)
            if index<ordinal:g.take('66ffc3','663bda');g.branch('72',True,1)
        g.take('488b85b0000000','0fb7cb','4803c9','486344c808','4883c014','48c1e004','4803c5');g.jump('eb',1)
        g.take('4c8b00','488bcf','488b5008','41ffd0','488bce','488906');call('barrier')
    g.take('488b5c2440','488b6c2448','4883c420','415e','5f','5e','c3')
    return dict(selectedBytes=g.seen,symbols=s,wrapperNull=wrapper_null,interfaceOrdinal=ordinal,
        metadataReadyFlag=flag,providerClassCell=provider,wrapperProviderContextSlot=4,conversionInterfaceContextSlot=8,
        getterReceiver='same wrapper RCX',getterMethodInfo='same exact interface RDX',getterResult='unchanged QWORD RAX',
        managedBytes=8,referenceBarrierOffsets=[]if wrapper_null else[0],
        sameIncomingReaderAndOutput=True,entryRspRestored=True,normalReturn=True)


def wrapper_program(regions,entry,*,new=False,null=False):
    need('literal-wrapper-case',type(new)is bool and type(null)is bool and not(new and null))
    g=BytesPath(regions,entry);s={}
    def call(role):
        target=g.relative('e8');need('same-wrapper-helper:'+role,role not in s or s[role]==target);s[role]=target
    g.take('48895c2410','57','4883ec20');flag=g.relative('803d');g.take('00','488bda','488bf9');g.branch('75',True,1)
    g.take('488d542430','c644243000','488bcf');call('header');g.take('84c0');g.branch('0f84',null)
    allocation=None;request=None
    if null:g.take('488bcb','48c70300000000');call('barrier')
    else:
        g.take('48833b00');g.branch('75',not new,1)
        if new:
            at=g.at;cell=g.relative('488b0d');call('allocate');g.take('4885c0');g.branch('74',False,1)
            g.take('33c9','48894810','488bcb','488903');call('barrier');allocation=dict(instructionVa=at,cellVa=cell,zeroedSlices=[[0,8]])
        g.take('807c243001');g.branch('75',False,1)
        at=g.at;cell=g.relative('488b15');g.take('488bcf','488b1b');site=g.at;call('array')
        g.take('4885db');g.branch('75',True,1);g.take('4533c0','488bd0','488bcb');call('setter');g.jump('eb',1)
        request=dict(instructionVa=at,cellVa=cell,sourceInstructionVa=site,sourceTargetVa=s['array'])
    g.take('488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,symbols=s,newWrapper=new,wrapperNull=null,metadataReadyFlag=flag,
        allocation=allocation,actualTypedRequest=request,memberCount=None if null else 1,
        orderedFields=[]if null else['rendererNamePrefixes'],managedBytes=8,entryRspRestored=True,normalReturn=True)


def setter_program(regions,entry,barrier):
    g=BytesPath(regions,entry);g.take('4883c110','488911');need('own-setter-barrier-tail',g.relative('e9')==barrier)
    return dict(selectedBytes=g.seen,fieldOffset=16,receiver='same wrapper RCX',value='unchanged string[] RDX',
        sameReferenceStored=True,barrierTarget=barrier,entryRspRestored=True,normalReturn=True)


def derive(image,pins):
    import json,struct
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack import pointer_param as pointer,buff_ptr_sources as bp,scalar_param_native as scalar
    from scripts.game_data.memorypack import pooled_global_buff_id_sources as neutral,event_args_paths,primitive_param
    from scripts.game_data.memorypack import animation_extra_value32_sources as value32,leveldata_string_array_sources as strings,pooled_source_helper
    from scripts.game_data.memorypack.pooled_string_list_sources import pooled_string
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    _publication_gate(image,pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);ge=GenericEntries(image)
    nominal=layout(image,ctx);wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==WRAPPER]
    need('own-generated-MC1',wrapper.wrapped_type==TYPE and ctx.field(WRAPPER+'::__instance')==(WRAPPER,TYPE,16)
        and[(m.name,m.declared_type)for m in wrapper.members]==[('rendererNamePrefixes','string[]')])
    mm=pointer.methods(image,wrapper);primitive_param.reader_abi(image,ctx,mm['Deserialize'],wrapper)
    pair=derive_pair(image,TYPE,WRAPPER,getter_entry_prover=getter_entry);forward=pointer.registered_pair(image,pair,wrapper,label='animationRenderer.pair')
    getter=getter_entry(image,md.types[wrapper.type_definition],mm['GetValue']);zeros=[]
    for name in('.ctor','CreateInstance'):
        m=mm[name];scalar.owned_method_abi(image,ctx,m.index,wrapper.type_definition,('void',1,False),[],'animationRenderer.zero')
        at=image.method_pointer_va(m);zeros.append(dict(method=[m.index,WRAPPER,name,at-base],program=zero_program([(at,image.pe.bytes_at_va(at,7))],at)))
    symbols={};sources={};registrations={}
    def merge(values):
        for role,target in values.items():need('same-complete-own-helper:'+role,role not in symbols or symbols[role]==target);symbols[role]=target
    for role,name in(('adapter','Deserialize'),('nonnull','DeserializeNotNull'),('readNull','ReadIsNull')):
        method=bp._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2',name)
        registrations[role]=ge.resolve(method.index,[TYPE,'object'],[]);merge({role:registrations[role]['pointer']});sources[role]=pointer.owned(image,symbols[role])
    face,=pair['composition']['interfaces'];td=md.types[wrapper.type_definition];section=md.sections['interfaceOffsets'];at=section.offset+td.interface_offsets_start*8
    ordinal=list(struct.iter_unpack('<ii',md.buf[at:at+td.interface_offsets_count*8])).index((face['interfaceTypeIndex'],face['interfaceOffset']))
    paths=dict(adapter=[adapter_program(sources['adapter']['regions'],symbols['adapter'],**case)for case in({},dict(create=False),dict(null=True))])
    for p in paths['adapter']:merge(p['symbols'])
    paths['nonnull']=[nonnull_program(sources['nonnull']['regions'],symbols['nonnull'],symbols,wrapper_null=n,ordinal=ordinal)for n in(False,True)]
    for p in paths['nonnull']:merge(p['symbols'])
    paths['readNull']=[value32.read_null_program(sources['readNull']['regions'],symbols['readNull'],null=n)for n in(False,True)]
    for p in paths['readNull']:merge(p['symbols'])
    for role in('classReady','wrapperInvoke','header','peek'):sources[role]=pointer.owned(image,symbols[role])
    paths['classReady']=neutral.ready_class_init(sources['classReady']['regions'],symbols['classReady'])
    paths['wrapperInvocation']=deserialize_slot(sources['wrapperInvoke']['regions'],symbols['wrapperInvoke'],prepare=symbols['prepare'],
        callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]))
    sources['wrapper']=pointer.owned(image,image.method_pointer_va(mm['Deserialize']));entry=sources['wrapper']['pointer']
    paths['wrapper']=[wrapper_program(sources['wrapper']['regions'],entry,**case)for case in({},dict(new=True),dict(null=True))]
    for p in paths['wrapper']:merge(p['symbols'])
    usage=derive_typed_usage_context(image,paths['wrapper'][0]['actualTypedRequest']['instructionVa']-base,label='animationRenderer.stringArray')
    allocation=derive_typed_usage_context(image,paths['wrapper'][1]['allocation']['instructionVa']-base,label='animationRenderer.allocation')
    need('own-wrapper-allocation',allocation.get('tag')==1 and allocation.get('typeName')==WRAPPER)
    array=strings.derive(image,pins,typed_request=usage,call_target=symbols['array']);sources['array']=pointer.owned(image,symbols['array'])
    provider=base+array['proof']['helperRvas']['provider'];sources['arrayProvider']=pointer.owned(image,provider)
    provider_symbols={}
    for role,offset in dict(classFromType=88,hash=145,compare=238,backend=376,indexedType=393,assignable=409).items():
        row,=[r for r in sources['arrayProvider']['rows']if int(r['va'],16)==provider+offset]
        raw=bytes.fromhex(row['bytes']);need('actual-provider-E8:'+role,len(raw)==5 and raw[0]==232)
        provider_symbols[role]=control_transfer(row)['target']
    pool_fact=pooled_source_helper._contract();pool=pooled_source_helper.validate_on_image(image,base+pool_fact['targetRva'],pins)
    pool_symbols=dict(pool=base+pool_fact['inlineSymbols']['pool'],empty=base+pool_fact['inlineSymbols']['empty'],lookup=base+pool_fact['lookupRva'])
    callback=base+array['proof']['pooledCallback']['entryRva'];sources['stringCallback']=pointer.owned(image,callback)
    string_callback=dict(entryRva=callback-base,symbols=pool_symbols,programs=[pooled_string(sources['stringCallback']['regions'],callback,pool_symbols,mode=mode)for mode in('lookup','empty','null')])
    setter=mm['set___rendererNamePrefixes__'];scalar.owned_method_abi(image,ctx,setter.index,wrapper.type_definition,('void',1,False),[('string[]',29,False)],'animationRenderer.setter')
    at=image.method_pointer_va(setter);need('same-actual-named-setter',at==symbols['setter'])
    setter_proof=dict(method=[setter.index,WRAPPER,'set___rendererNamePrefixes__',at-base],program=setter_program([(at,image.pe.bytes_at_va(at,12))],at,symbols['barrier']))
    offsets=scalar.reader_offsets(image,'animationRenderer');array_offsets=dict(offsets,totalLength=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16)
    header=primitive_param.object_header_source(image,vector_recorder(image)(symbols['header']-base),offsets)
    peek=event_args_paths.peek(sources['peek']['regions'],symbols['peek'],offsets);barrier=_fast_barrier(image,symbols['barrier']);context,context_proof=bp._adapter_context(image,ge)
    need('own-TypeFromHandle',symbols['typeHandle']==base+pair['registration']['helperMethods']['typeFromHandle'][3])
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-renderer-value8-source',nativeInputs=pins,
        typeName=TYPE,wrapperName=WRAPPER,managedBytes=8,ordinaryOriginalCallbackAdmitted=True,
        ordinaryOriginalReadValueAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(layout=nominal,pair=pair,forwarding=forward,getter=getter,zeroLeaves=zeros,registrations=registrations,
            paths=paths,interfaceOrdinal=ordinal,allocationUsage=allocation,array=array,arrayReaderOffsets=array_offsets,arrayProviderSymbols=provider_symbols,
            setter=setter_proof,pool=pool,stringCallback=string_callback,
            adapterContext=context,adapterContextProof=context_proof,readerOffsets=offsets,header=header,peek=peek,barrier=barrier,
            symbolRvas={k:v-base for k,v in symbols.items()},sourceWindows={k:v['windows']for k,v in sources.items()},
            sourceRegions={k:[[a-base,r.hex()]for a,r in v['regions']]for k,v in sources.items()}),
        evidenceBoundary=dict(exact='Own managed8 reference lane, eager pair, complete initialized canonical/interface/default paths, generated MC1 and independently pooled STRING14 array reader.',
            conditional='Initialized coherent selected own contexts, matched pooled callback, fresh bounded arrays, normal helpers and disabled barriers; live selection unobserved.',
            unresolved=['enclosing array/parent field and frame','whole owner EOF','runtime renderer behavior']))))

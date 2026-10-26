"""Own ShaderPropertyEntry padded24 representation and selected MC4 sources.

The string lane and padding are managed ABI facts. The canonical formatter,
its hidden output and the generated four-member wire remain separate proofs.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath,deserialize_slot

TYPE='Beyond.Gameplay.View.Animation.AnimationConfigExtraData+ShaderPropertyEntry'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_View_Animation_AnimationConfigExtraData_ShaderPropertyEntryForMemoryPack'
FIELDS=[['mask','Beyond.Rendering.EntityVFXRendererMask',16],['type','UnityEngine.Rendering.ShaderPropertyType',20],
    ['name','string',24],['blendMode','Beyond.Gameplay.Core.EShaderParamBlendMode',32]]
ORDER=['blendMode','mask','name','type']
SCHEMA='endfield.shader-property-value-source.v1'


def need(check,condition):
    if not condition:raise ValueError('shaderPropertyValue.'+check)


def getter_program(regions,entry):
    g=BytesPath(regions,entry);g.take('0f104210','488bc1','f20f104a20','0f1101','f20f114910','c3')
    return dict(selectedBytes=g.seen,managedBytes=24,sourceSlices=[[0,16],[16,8]],referenceLaneOffsets=[8],
        sourceWrapperRegister='rdx',hiddenOutputRegister='rcx',returnsSameHiddenOutputRax=True,
        completePayloadBitsCopied=True,normalReturn=True,entryRspRestored=True,calleeCalls=0)


def getter_entry(image,owner,getter):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    need('own-metadata-getter',image.type_name(owner.index)==WRAPPER and getter.declaring_type==owner.index)
    scalar.owned_method_abi(image,NativeReferenceContext(image),getter.index,owner.index,(TYPE,17,False),[],'shaderProperty.GetValue')
    at=image.method_pointer_va(getter)
    return getter_program([(at,image.pe.bytes_at_va(at,21))],at)


def zero_program(regions,entry):
    g=BytesPath(regions,entry);g.take('0f57c0','33c0','0f114110','48894120','c3')
    return dict(selectedBytes=g.seen,managedBytes=24,zeroedSlices=[[0,16],[16,8]],
        allManagedBytesZeroed=True,normalReturn=True,entryRspRestored=True,calleeCalls=0)


def wrapper_program(regions,entry,*,new=False,null=False):
    need('literal-wrapper-case',type(new)is bool and type(null)is bool and not(new and null))
    g=BytesPath(regions,entry);s={};requests=[]
    def call(role):
        at=g.at;target=g.relative('e8');need('same-own-wrapper-helper:'+role,role not in s or s[role]==target)
        s[role]=target;return at
    g.take('48895c2418','57','4883ec20');flag=g.relative('803d');g.take('00','488bda','488bf9');g.branch('0f84',False)
    g.take('488d542430','c644243000','488bcf');call('header');g.take('84c0');g.branch('0f84',null)
    allocation=None
    if null:g.take('488bcb','48c70300000000');call('barrier');g.take('90');g.jump('e9')
    else:
        g.take('4889742438','48833b00');g.branch('0f84',new)
        if new:
            at=g.at;cell=g.relative('488b0d');call('allocate');g.take('4885c0');g.branch('0f84',False)
            g.take('33c9','0f57c0','0f114010','48894820','488bcb','488903');call('barrier');g.take('90');g.jump('e9')
            allocation=dict(instructionVa=at,cellVa=cell,zeroedSlices=[[0,16],[16,8]])
        g.take('0fb6742430','4080fe04');g.branch('0f85',False)
        for index,role,store in ((0,'blendMode','894620'),(1,'mask','894610')):
            if index:g.take('488bcf')
            at=g.at;cell=g.relative('488b15')
            if index==0:g.take('488bcf')
            g.take('488b33');site=call('enum');g.take('4885f6');g.branch('74',False,1);g.take(store)
            requests.append(dict(fieldName=role,memberIndex=index,instructionVa=at,cellVa=cell,sourceInstructionVa=site,sourceTargetVa=s['enum']))
        g.take('488bcf','488b33');call('pool');g.take('4885f6');g.branch('74',False,1)
        g.take('488d4e18','48894618');call('barrier')
        at=g.at;cell=g.relative('488b15');g.take('488bcf','488b1b');site=call('enum');g.take('4885db');g.branch('74',False,1)
        g.take('488b742438','894314')
        requests.append(dict(fieldName='type',memberIndex=3,instructionVa=at,cellVa=cell,sourceInstructionVa=site,sourceTargetVa=s['enum']))
    g.take('488b5c2440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,newWrapper=new,wrapperNull=null,metadataReadyFlag=flag,
        symbols=s,actualTypedRequests=requests,allocation=allocation,memberCount=None if null else 4,
        orderedFields=[]if null else ORDER,wireBytes=1 if null else 17,
        managedBytes=24,entryRspRestored=True,allIntegerNonvolatilesRestored=True,normalReturn=True)


def adapter_program(regions,entry,s=None,*,dispatch=False,null=False,create=True):
    need('literal-canonical-path',all(type(v)is bool for v in(dispatch,null,create)))
    g=BytesPath(regions,entry);symbols={}if s is None else dict(s)
    def call(role):
        target=g.relative('e8');need('same-owned-canonical-helper:'+role,role not in symbols or symbols[role]==target)
        symbols[role]=target
    if dispatch:
        g.take('48895c2408','48896c2410','4889742418','57','4883ec20','488b0a','498be9','498bf0','488bda')
        call('prepare');g.take('488b3b');canonical=g.relative('488d0d')
        need('own-compared-canonical-adapter','adapter'not in symbols or symbols['adapter']==canonical);symbols['adapter']=canonical
        g.take('488b8790010000','488bbf98010000','483bc1');g.branch('0f85',False)
        flag=g.relative('803d');g.take('00');g.branch('0f84',False)
    else:
        g.take('48896c2410','4889742418','57','4883ec20');flag=g.relative('803d')
        g.take('00','498bf9','498be8','488bf2');g.branch('0f84',False)
    g.take('488b4720','488bce','488b90c0000000','488b12');call('readNull');g.take('84c0');g.branch('0f85',null)
    if null:g.take('0f57c0','33c0','0f114500','48894510');g.jump('e9')
    else:
        if not dispatch:g.take('48895c2430')
        g.take('488b4720');g.relative('488b0d');g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('74',False,1)
        g.take('33d2','488bcb');call('typeHandle')
        if not dispatch:g.take('488b5c2430')
        g.take('4885c0');g.branch('74',False,1);g.take('33d2','488bc8');call('creationTest')
        g.take('84c0');g.branch('75',not create,1)
        if create:g.take('488b4720','488b88c0000000','488b4958');call('activate')
        else:g.take('33c0');g.jump('eb',1)
        g.take('488b4f20','4c8bc0','488bd5','4c8b89c0000000','488bce','4d8b4918');call('nonnull')
    if dispatch:g.take('488b5c2430')
    g.take('488b6c2438','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,symbols=symbols,dispatch=dispatch,originalNull=null,createWrapper=None if null else create,
        managedBytes=24,defaultZeroBytes=24 if null else 0,zeroSlices=[[0,16],[16,8]]if null else [],
        sameHiddenOutput=True,metadataReadyFlag=flag,normalReturn=True,entryRspRestored=True)


def nonnull_program(regions,entry,s=None,*,wrapper_null=False):
    need('literal-nonnull-case',type(wrapper_null)is bool)
    g=BytesPath(regions,entry);symbols={}if s is None else dict(s)
    def call(role):
        target=g.relative('e8');need('same-owned-nonnull-helper:'+role,role not in symbols or symbols[role]==target)
        symbols[role]=target
    g.take('48895c2408','4889742410','4c89442418','57','4883ec40');flag=g.relative('803d')
    g.take('00','498bf9','488bf2','488bd9');g.branch('0f84',False)
    provider=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
    g.take('488b4f20');call('resolve');g.take('488b88c0000000','488b4920');call('wrapperProvider')
    g.take('4885c0');g.branch('0f84',False);g.take('b905000000','4c8d4c2460','4c8bc3','488bd0');call('wrapperInvoke')
    g.take('488b5c2460','4885db');g.branch('0f84',wrapper_null)
    if wrapper_null:g.take('0f57c0','33c0','0f1106','48894610');g.jump('e9')
    else:
        g.take('488b4f20');call('resolve');g.take('ba08000000','488b88c0000000');call('indexed')
        g.take('4c8bc0','488d4c2420','4c8bcb');call('conversion')
        g.take('488d4e08','0f1008','f20f104010','0f110e','f20f114610');call('barrier')
    g.take('488b5c2450','488b742458','4883c440','5f','c3')
    return dict(selectedBytes=g.seen,symbols=symbols,wrapperNull=wrapper_null,managedBytes=24,
        defaultZeroBytes=24 if wrapper_null else 0,copiedSlices=[]if wrapper_null else[[0,16],[16,8]],
        referenceBarrierOffsets=[]if wrapper_null else[8],metadataReadyFlag=flag,providerClassCell=provider,
        wrapperProviderContextSlot=4,conversionInterfaceContextSlot=8,
        sameIncomingReaderAndHiddenOutput=True,entryRspRestored=True,normalReturn=True)


def conversion_program(regions,entry,*,ordinal,prepare=None):
    need('finite-owned-interface-ordinal',type(ordinal)is int and 0<=ordinal<=16)
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','48897c2418','4156','4883ec40','498b39','488bf1','488bcf','4d8bf1','498bd8')
    actual=g.relative('e8');need('same-interface-preparation',prepare is None or actual==prepare)
    g.take('440fb78730010000','33c0','66413bc0');g.branch('73',False,1);g.take('488b97b0000000')
    for index in range(ordinal+1):
        g.take('0fb7c8','4803c9','48391cca');g.branch('74',index==ordinal,1)
        if index<ordinal:g.take('66ffc0','66413bc0');g.branch('72',True,1)
    g.take('0fb7c8','4803c9','486344ca08','4883c014','48c1e004','4803c7',
        '4c8b08','488d4c2420','4c8b4008','498bd6','41ffd1','488b5c2450','488b7c2460',
        '0f1000','f20f104810','488bc6','0f1106','f20f114e10','488b742458','4883c440','415e','c3')
    return dict(selectedBytes=g.seen,interfaceOrdinal=ordinal,methodSlot=0,prepareTarget=actual,
        getterArguments=dict(rcx='local24',rdx='same wrapper',r8='exact own interface MethodInfo'),
        copiedSlices=[[0,16],[16,8]],getterReturnsSameHiddenOutputRax=True,outputBytes=24,
        sameIncomingOutputReturnedRax=True,entryRspRestored=True,normalReturn=True)


def layout(image,ctx):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    td=ctx.index.types[TYPE];md=image.metadata
    need('own-ordinary-value',ctx.is_value_type(TYPE)and not ctx.is_enum(TYPE)
        and ctx.parent(TYPE)=='System.ValueType'and td.generic_container_index<0)
    fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    actual=[[md.string(f.name_index),*ctx.field(TYPE+'::'+md.string(f.name_index))[1:]]for f in fields]
    need('own-exact-physical-fields',actual==FIELDS)
    enums=[]
    for field,(_,typ,_)in zip(fields,FIELDS,strict=True):
        scalar.ordinary(image,ctx.type_pointer(field.type_index),14 if typ=='string'else 17,'shaderProperty.field',reference=typ=='string')
        if typ=='string':continue
        definition=ctx.index.types[typ];backing,=[f for f in md.fields_for(definition)if not ctx.field_attributes(f.type_index)&16]
        value=ctx.field(typ+'::value__')
        need('own-four-byte-enum',ctx.is_enum(typ)and definition.generic_container_index<0
            and md.string(backing.name_index)=='value__'and value[1]in('int','uint')and value[2]==16)
        scalar.ordinary(image,ctx.type_pointer(backing.type_index),8 if value[1]=='int'else 9,'shaderProperty.enumBacking')
        enums.append(dict(typeName=typ,typeDefinition=definition.index,backingType=value[1],backingBytes=4))
    at=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
    need('own-boxed40-managed24',(image.pe.u32_at_va(at),image.pe.u32_at_va(at+4))==(40,24))
    return dict(typeName=TYPE,typeDefinition=td.index,fields=actual,boxedBytes=40,managedBytes=24,
        enums=enums,referenceLaneOffsets=[8],paddingByteRanges=[[20,4]],paddingRangeEncoding='start,length',
        serializedFieldNames=ORDER,wireGrammarAdmitted=False)


def derive(image,pins,*,dispatch_target=None):
    """Prove the own canonical callback; an actual array helper is optional."""
    import json,struct
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import pointer_param as pointer,buff_ptr_sources as bp
    from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param,generated_primitive_sources as primitive
    from scripts.game_data.memorypack import pooled_source_helper,pooled_global_buff_id_sources as neutral,event_args_paths
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    _publication_gate(image,pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);ge=GenericEntries(image)
    nominal=layout(image,ctx);wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==WRAPPER]
    field_types={n:t for n,t,o in FIELDS}
    need('own-four-generated-members',wrapper.wrapped_type==TYPE and ctx.field(WRAPPER+'::__instance')==(WRAPPER,TYPE,16)
        and[(m.name,m.declared_type)for m in wrapper.members]==[(n,field_types[n])for n in ORDER])
    mm=pointer.methods(image,wrapper);primitive_param.reader_abi(image,ctx,mm['Deserialize'],wrapper)
    pair=derive_pair(image,TYPE,WRAPPER,getter_entry_prover=getter_entry)
    forwarding=pointer.registered_pair(image,pair,wrapper,label='shaderProperty.pair')
    getter=getter_entry(image,md.types[wrapper.type_definition],mm['GetValue']);zeros=[]
    for name in('.ctor','CreateInstance'):
        method=mm[name];scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),[],'shaderProperty.zero')
        at=image.method_pointer_va(method);zeros.append(dict(method=[method.index,WRAPPER,name,at-base],
            program=zero_program([(at,image.pe.bytes_at_va(at,128))],at)))
    sources={'wrapper':pointer.owned(image,image.method_pointer_va(mm['Deserialize']))};at=sources['wrapper']['pointer']
    wrapper_paths=[wrapper_program(sources['wrapper']['regions'],at,**case)for case in({},dict(new=True),dict(null=True))]
    symbols={}
    def merge(values):
        for role,target in values.items():need('same-actual-owned-helper:'+role,role not in symbols or symbols[role]==target);symbols[role]=target
    for p in wrapper_paths:merge(p['symbols'])
    allocation=derive_typed_usage_context(image,wrapper_paths[1]['allocation']['instructionVa']-base,label='shaderProperty.allocation')
    need('own-exact-wrapper-allocation',allocation.get('tag')==1 and allocation.get('typeName')==WRAPPER)
    registrations={}
    for role,name in(('adapter','Deserialize'),('nonnull','DeserializeNotNull'),('readNull','ReadIsNull')):
        method=bp._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2',name)
        registrations[role]=ge.resolve(method.index,[TYPE,'object'],[]);merge({role:registrations[role]['pointer']})
        sources[role]=pointer.owned(image,symbols[role])
    paths={}
    paths['adapter']=[adapter_program(sources['adapter']['regions'],symbols['adapter'],symbols,**case)
        for case in({},dict(create=False),dict(null=True))]
    for p in paths['adapter']:merge(p['symbols'])
    paths['nonnull']=[nonnull_program(sources['nonnull']['regions'],symbols['nonnull'],symbols,wrapper_null=n)for n in(False,True)]
    for p in paths['nonnull']:merge(p['symbols'])
    face,=pair['composition']['interfaces'];td=md.types[wrapper.type_definition];section=md.sections['interfaceOffsets']
    start=section.offset+td.interface_offsets_start*8
    ordinal=list(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8])).index((face['interfaceTypeIndex'],face['interfaceOffset']))
    for role in('conversion','wrapperInvoke','header','enum','pool'):sources[role]=pointer.owned(image,symbols[role])
    paths['conversion']=conversion_program(sources['conversion']['regions'],symbols['conversion'],ordinal=ordinal)
    merge({'prepare':paths['conversion']['prepareTarget'],'peek':bp._call(sources['readNull'],14)})
    paths['readNull']=[neutral.read_null_program(sources['readNull']['regions'],symbols['readNull'],symbols,null=n)for n in(False,True)]
    paths['wrapperInvocation']=deserialize_slot(sources['wrapperInvoke']['regions'],symbols['wrapperInvoke'],prepare=symbols['prepare'],
        callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]))
    offsets=scalar.reader_offsets(image,'shaderProperty');record=vector_recorder(image)
    header=primitive_param.object_header_source(image,record(symbols['header']-base),offsets)
    enum=primitive.derive(image,symbols['enum'],'int32',offsets)
    requests=[]
    for event in wrapper_paths[0]['actualTypedRequests']:
        usage=derive_typed_usage_context(image,event['instructionVa']-base,label='shaderProperty.enum')
        name=field_types[event['fieldName']]
        need('own-exact-enum-request',tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
            ==(6,'MemoryPack.MemoryPackReader','ReadUnmanaged',[],[name]))
        binding=bind_typed_read(image,usage,method_name='ReadUnmanaged',argument=name,kind=17)
        requests.append(dict(typedRequest=usage,typedBinding=binding,**event))
    pool=pooled_source_helper.validate_on_image(image,symbols['pool'],pins)
    sources['peek']=pointer.owned(image,symbols['peek']);peek=event_args_paths.peek(sources['peek']['regions'],symbols['peek'],offsets)
    barrier=_fast_barrier(image,symbols['barrier']);context,context_proof=bp._adapter_context(image,ge)
    need('own-TypeFromHandle',symbols['typeHandle']==base+pair['registration']['helperMethods']['typeFromHandle'][3])
    if dispatch_target is not None:
        need('literal-actual-dispatch-target',type(dispatch_target)is int and dispatch_target>0)
        sources['actualDispatch']=pointer.owned(image,dispatch_target);merge({'actualDispatch':dispatch_target})
        paths['actualDispatch']=[adapter_program(sources['actualDispatch']['regions'],dispatch_target,symbols,dispatch=True,**case)
            for case in({},dict(create=False),dict(null=True))]
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-shader-property-canonical-value24',nativeInputs=pins,
        typeName=TYPE,wrapperName=WRAPPER,managedBytes=24,referenceLaneOffsets=[8],paddingByteRanges=[[20,4]],
        ordinaryOriginalCallbackAdmitted=True,ordinaryOriginalReadValueAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(layout=nominal,pair=pair,forwarding=forwarding,getter=getter,zeroLeaves=zeros,wrapperPaths=wrapper_paths,
            paths=paths,registrations=registrations,interfaceOrdinal=ordinal,allocationUsage=allocation,requests=requests,
            adapterContext=context,adapterContextProof=context_proof,readerOffsets=offsets,header=header,enum=enum,pool=pool,peek=peek,barrier=barrier,
            symbolRvas={k:v-base for k,v in symbols.items()},sourceWindows={k:v['windows']for k,v in sources.items()},
            sourceRegions={k:[[a-base,r.hex()]for a,r in v['regions']]for k,v in sources.items()}),
        evidenceBoundary=dict(exact='Own padded24/string-lane layout, eager pair, hidden getter/default24, canonical/default/non-null/interface and generated MC4 sources.',
            conditional='Coherent selected nominal formatter/MethodInfo, initialized contexts, normal ABI-preserving helpers and disabled barriers; live selection unobserved.',
            unresolved=['enclosing array/parent fields and frames','physical raw owner EOF','runtime material/shader behavior']))))

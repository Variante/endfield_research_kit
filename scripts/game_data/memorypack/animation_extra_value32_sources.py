"""Two independently named ExtraData managed32 callback representations.

StatePerform and PlayEffect share neutral copy instructions, while their
fields, reference lanes, generated members and marshaled sizes stay distinct.
No generated member wire, array or containing field is admitted here.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

PREFIX='Beyond.Gameplay.View.Animation.'
STATE=PREFIX+'StatePerformConfig'
PLAY=PREFIX+'AnimationConfigExtraData+AnimationEventPlayEffectEntry'
FIELDS={STATE:[['stateName','string',16],['stateHash','int',24],['performId','string',32],
    ['interruptType',PREFIX+'StatePerformInterruptConditionType',40]],
    PLAY:[['eventName','string',16],['effectName','string',24],['targetBonePath','string',32],
        ['followPosition','bool',40],['followRotation','bool',41],['stopWithState','bool',42]]}
WRAPPERS={STATE:'Beyond.MemoryPack.Beyond_Gameplay_View_Animation_StatePerformConfigForMemoryPack',
    PLAY:'Beyond.MemoryPack.Beyond_Gameplay_View_Animation_AnimationConfigExtraData_AnimationEventPlayEffectEntryForMemoryPack'}
SCHEMA='endfield.animation-extra-value32-source.v1'


def need(check,condition):
    if not condition:raise ValueError('animationExtraValue32.'+check)


def getter_program(regions,entry):
    from scripts.game_data.memorypack.char_perform_action_sources import value_leaf
    proof=value_leaf(regions,entry,getter=True)
    return dict(proof,managedBytes=32,completePayloadBitsCopied=True,sourceSlices=[[0,16],[16,16]],
        entryRspRestored=True,calleeCalls=0)


def getter_entry(image,owner,getter):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    ctx=NativeReferenceContext(image);wrapper=image.type_name(owner.index)
    need('own-finite-metadata-getter',wrapper in WRAPPERS.values()and getter.declaring_type==owner.index)
    name,=[k for k,v in WRAPPERS.items()if v==wrapper]
    scalar.owned_method_abi(image,ctx,getter.index,owner.index,(name,17,False),[],'animationExtraValue32.GetValue')
    at=image.method_pointer_va(getter);return getter_program([(at,image.pe.bytes_at_va(at,128))],at)


def zero_program(regions,entry):
    g=BytesPath(regions,entry);g.take('0f57c0','0f114110','0f114120','c3')
    return dict(selectedBytes=g.seen,managedBytes=32,zeroedSlices=[[0,16],[16,16]],
        allManagedBytesZeroed=True,normalReturn=True,entryRspRestored=True,calleeCalls=0)


def adapter_program(regions,entry,s=None,*,null=False,create=True):
    need('literal-adapter-case',type(null)is bool and type(create)is bool)
    g=BytesPath(regions,entry);symbols={}if s is None else dict(s)
    def call(role):
        target=g.relative('e8');need('same-own-adapter-helper:'+role,role not in symbols or symbols[role]==target)
        symbols[role]=target
    g.take('488bc4','48895808','48896810','48897018','48897820','4156','4883ec20','33ff','498be9')
    flag=g.relative('40383d');g.take('498bf0','4c8bf2');g.branch('75',True,1)
    g.take('488b4520','498bce','488b90c0000000','488b12');call('readNull');g.take('84c0');g.branch('75',null,1)
    type_cell=None
    if null:g.take('0f57c0','0f1106','0f114610')
    else:
        g.take('488b4520');type_cell=g.relative('488b0d');g.take('488b98c0000000','488b5b50');call('classReady')
        g.take('33d2','488bcb');call('typeHandle');g.take('4885c0');g.branch('75',True,1)
        g.take('33d2','488bc8');call('creationTest');g.take('84c0');g.branch('75',not create,1)
        if create:g.take('488b4520','488b88c0000000','488b4958');call('activate');g.take('488bf8')
        g.take('488b4d20','4c8bc7','488bd6','4c8b89c0000000','498bce','4d8b4918');call('nonnull');g.jump('eb',1)
    g.take('488b5c2430','488b6c2438','488b742440','488b7c2448','4883c420','415e','c3')
    return dict(selectedBytes=g.seen,symbols=symbols,originalNull=null,createWrapper=None if null else create,
        managedBytes=32,defaultZeroBytes=32 if null else 0,sameIncomingReaderAndHiddenOutput=True,
        metadataReadyFlag=flag,typeClassCell=type_cell,entryRspRestored=True,normalReturn=True)


def nonnull_program(regions,entry,s=None,*,wrapper_null=False):
    need('literal-nonnull-case',type(wrapper_null)is bool)
    g=BytesPath(regions,entry);symbols={}if s is None else dict(s)
    def call(role):
        target=g.relative('e8');need('same-own-nonnull-helper:'+role,role not in symbols or symbols[role]==target)
        symbols[role]=target
    g.take('48895c2408','4889742410','4c89442418','57','4883ec40');flag=g.relative('803d')
    g.take('00','498bf1','488bda','488bf9');g.branch('75',True,1)
    provider=g.relative('488b0d');call('classReady')
    g.take('488b4e20');call('resolve');g.take('488b88c0000000','488b4920');call('wrapperProvider')
    g.take('4885c0');g.branch('75',True,1)
    g.take('b905000000','4c8d4c2460','4c8bc7','488bd0');call('wrapperInvoke')
    g.take('488b7c2460','4885ff');g.branch('75',not wrapper_null,1)
    if wrapper_null:g.take('0f57c0','0f1103','0f114310');g.jump('eb',1)
    else:
        g.take('488b4e20');call('resolve');g.take('488b88c0000000','488b4940');call('resolve')
        g.take('4c8bcf','488d4c2420','4c8bc0');call('conversion')
        g.take('488bcb','0f1000','0f104810','0f1103','0f114b10');call('barrier')
    g.take('488b5c2450','488b742458','4883c440','5f','c3')
    return dict(selectedBytes=g.seen,symbols=symbols,wrapperNull=wrapper_null,managedBytes=32,
        defaultZeroBytes=32 if wrapper_null else 0,copiedSlices=[]if wrapper_null else[[0,16],[16,16]],
        selectedBarrierValueOffsets=[]if wrapper_null else[0],metadataReadyFlag=flag,providerClassCell=provider,
        wrapperProviderContextSlot=4,conversionInterfaceContextSlot=8,interfaceContextResolverUsed=True,
        sameIncomingReaderAndHiddenOutput=True,entryRspRestored=True,normalReturn=True)


def conversion_program(regions,entry,*,ordinal,prepare=None):
    need('finite-own-interface-ordinal',type(ordinal)is int and 0<=ordinal<=16)
    g=BytesPath(regions,entry)
    g.take('48895c2408','48896c2410','4889742418','57','4883ec40','498b19','488be9','488bcb','498bf9','498bf0')
    actual=g.relative('e8');need('same-interface-preparation',prepare is None or actual==prepare)
    g.take('440fb78330010000','33d2','66413bd0');g.branch('73',False,1);g.take('488b8bb0000000')
    for index in range(ordinal+1):
        g.take('0fb7c2','4803c0','483934c1');g.branch('74',index==ordinal,1)
        if index<ordinal:g.take('66ffc2','66413bd0');g.branch('72',True,1)
    g.take('488b83b0000000','0fb7ca','4803c9','486344c808','4883c014','48c1e004','4803c3');g.jump('eb',1)
    g.take('4c8b08','488d4c2420','4c8b4008','488bd7','41ffd1','488b5c2450','488b742460',
        '0f1000','0f104810','488bc5','0f114500','0f114d10','488b6c2458','4883c440','5f','c3')
    return dict(selectedBytes=g.seen,interfaceOrdinal=ordinal,prepareTarget=actual,methodSlot=0,
        hiddenGetterArguments=dict(rcx='local32',rdx='same wrapper',r8='own exact interface MethodInfo'),
        copiedSlices=[[0,16],[16,16]],getterReturnsSameHiddenOutputRax=True,
        sameIncomingOutputReturnedRax=True,entryRspRestored=True,normalReturn=True)


def read_null_program(regions,entry,s=None,*,null=False):
    need('literal-null-case',type(null)is bool);g=BytesPath(regions,entry);symbols={}if s is None else dict(s)
    def call(role):
        target=g.relative('e8');need('same-owned-null-helper:'+role,role not in symbols or symbols[role]==target)
        symbols[role]=target
    g.take('4053','4883ec20','488bd9','c644243000');call('peek');g.take('84c0');g.branch('75',null,1)
    if null:g.take('488d542430','488bcb');call('header');g.take('b001')
    else:g.jump('eb',1)
    g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,symbols=symbols,originalNull=null,consumedBytes=int(null),
        sameReader=True,entryRspRestored=True,normalReturn=True)


def layout(image,ctx,name):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    need('finite-own-value32',name in FIELDS);td=ctx.index.types[name];md=image.metadata
    need('own-ordinary-value',ctx.is_value_type(name)and not ctx.is_enum(name)
        and ctx.parent(name)=='System.ValueType'and td.generic_container_index<0)
    fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    actual=[[md.string(f.name_index),*ctx.field(name+'::'+md.string(f.name_index))[1:]]for f in fields]
    need('exact-own-nominal-fields',actual==FIELDS[name])
    enums=[]
    for field,(_,typ,_)in zip(fields,actual,strict=True):
        kind={'string':14,'int':8,'bool':2}.get(typ,17)
        scalar.ordinary(image,ctx.type_pointer(field.type_index),kind,'animationExtraValue32.field',reference=kind==14)
        if kind!=17:continue
        enum=ctx.index.types[typ];backing,=[f for f in md.fields_for(enum)if not ctx.field_attributes(f.type_index)&16]
        stored=ctx.field(typ+'::value__')
        need('own-int32-enum-backing',ctx.is_enum(typ)and enum.generic_container_index<0
            and md.string(backing.name_index)=='value__'and stored[1]in('int','uint')and stored[2]==16)
        scalar.ordinary(image,ctx.type_pointer(backing.type_index),8 if stored[1]=='int'else 9,'animationExtraValue32.enum')
        enums.append(dict(typeName=typ,typeDefinition=enum.index,backingType=stored[1],backingBytes=4))
    at=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
    boxed,native=image.pe.u32_at_va(at),image.pe.u32_at_va(at+4)
    need('own-boxed-and-separate-marshaled-sizes',(boxed,native)==(48,32 if name==STATE else 40))
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==WRAPPERS[name]]
    generated=[m.name for m in wrapper.members]
    need('own-generated-member-declarations',generated==(['interruptType','performId','stateHash']if name==STATE else
        ['effectName','eventName','followPosition','followRotation','stopWithState','targetBonePath']))
    return dict(typeName=name,typeDefinition=td.index,fields=actual,boxedBytes=48,managedBytes=32,
        marshaledNativeBytes=native,marshaledSizeUsedForManagedWidth=False,enums=enums,
        referenceLaneOffsets=[0,16]if name==STATE else[0,8,16],
        paddingByteRanges=[[12,4],[28,4]]if name==STATE else[[27,5]],paddingRangeEncoding='start,length',
        generatedMemberNames=generated,physicalFieldsAbsentFromGeneratedMembers=['stateName']if name==STATE else[],
        wireFieldSelectionAdmitted=False,wireGrammarAdmitted=False)


def derive(image,pins,*,type_name):
    import json,struct
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
    from scripts.game_data.memorypack import pointer_param as pointer,buff_ptr_sources as bp,scalar_param_native as scalar
    from scripts.game_data.memorypack import pooled_global_buff_id_sources as neutral,primitive_param,event_args_paths
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    _publication_gate(image,pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);ge=GenericEntries(image)
    nominal=layout(image,ctx,type_name);wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==WRAPPERS[type_name]]
    need('own-inline-holder',wrapper.wrapped_type==type_name and ctx.field(wrapper.name+'::__instance')==(wrapper.name,type_name,16))
    mm=pointer.methods(image,wrapper);pair=derive_pair(image,type_name,wrapper.name,getter_entry_prover=getter_entry)
    forward=pointer.registered_pair(image,pair,wrapper,label='animationExtraValue32.pair')
    getter=getter_entry(image,md.types[wrapper.type_definition],mm['GetValue']);zeros=[]
    for name in('.ctor','CreateInstance'):
        method=mm[name];scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),[],'animationExtraValue32.zero')
        at=image.method_pointer_va(method);zeros.append(dict(method=[method.index,wrapper.name,name,at-base],
            program=zero_program([(at,image.pe.bytes_at_va(at,128))],at)))
    symbols={};sources={};registrations={}
    def merge(values):
        for role,target in values.items():need('same-complete-owned-helper:'+role,role not in symbols or symbols[role]==target);symbols[role]=target
    for role,name in(('adapter','Deserialize'),('nonnull','DeserializeNotNull'),('readNull','ReadIsNull')):
        method=bp._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2',name)
        registrations[role]=ge.resolve(method.index,[type_name,'object'],[]);merge({role:registrations[role]['pointer']})
        sources[role]=pointer.owned(image,symbols[role])
    paths=dict(adapter=[adapter_program(sources['adapter']['regions'],symbols['adapter'],symbols,**case)
        for case in({},dict(create=False),dict(null=True))])
    for p in paths['adapter']:merge(p['symbols'])
    paths['nonnull']=[nonnull_program(sources['nonnull']['regions'],symbols['nonnull'],symbols,wrapper_null=n)for n in(False,True)]
    for p in paths['nonnull']:merge(p['symbols'])
    paths['readNull']=[read_null_program(sources['readNull']['regions'],symbols['readNull'],symbols,null=n)for n in(False,True)]
    for p in paths['readNull']:merge(p['symbols'])
    face,=pair['composition']['interfaces'];td=md.types[wrapper.type_definition];section=md.sections['interfaceOffsets']
    start=section.offset+td.interface_offsets_start*8
    ordinal=list(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8])).index((face['interfaceTypeIndex'],face['interfaceOffset']))
    for role in('conversion','wrapperInvoke','classReady','header','peek'):sources[role]=pointer.owned(image,symbols[role])
    paths['conversion']=conversion_program(sources['conversion']['regions'],symbols['conversion'],ordinal=ordinal)
    merge({'prepare':paths['conversion']['prepareTarget']})
    paths['wrapperInvocation']=deserialize_slot(sources['wrapperInvoke']['regions'],symbols['wrapperInvoke'],prepare=symbols['prepare'],
        callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]))
    paths['classReady']=neutral.ready_class_init(sources['classReady']['regions'],symbols['classReady'])
    offsets=scalar.reader_offsets(image,'animationExtraValue32')
    header=primitive_param.object_header_source(image,vector_recorder(image)(symbols['header']-base),offsets)
    peek=event_args_paths.peek(sources['peek']['regions'],symbols['peek'],offsets)
    barrier=_fast_barrier(image,symbols['barrier']);context,context_proof=bp._adapter_context(image,ge)
    need('own-TypeFromHandle',symbols['typeHandle']==base+pair['registration']['helperMethods']['typeFromHandle'][3])
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-extra-value32-canonical-source',nativeInputs=pins,
        typeName=type_name,wrapperName=wrapper.name,managedBytes=32,canonicalCallbackAbiProved=True,
        wireGrammarAdmitted=False,ordinaryOriginalReadValueAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(layout=nominal,pair=pair,forwarding=forward,getter=getter,zeroLeaves=zeros,registrations=registrations,
            paths=paths,interfaceOrdinal=ordinal,adapterContext=context,adapterContextProof=context_proof,
            readerOffsets=offsets,header=header,peek=peek,barrier=barrier,symbolRvas={k:v-base for k,v in symbols.items()},
            sourceWindows={k:v['windows']for k,v in sources.items()},sourceRegions={k:[[a-base,r.hex()]for a,r in v['regions']]for k,v in sources.items()}),
        evidenceBoundary=dict(exact='Own nominal managed32 fields/padding and marshaled-size distinction, pair, complete hidden getter/zero32 and registered canonical/default/non-null/interface source paths.',
            conditional='Coherent initialized own contexts and selected slot5/MethodInfo, successful helpers and disabled barriers; runtime selection is unobserved.',
            unresolved=['own generated member wire','containing array/source/field/frame','physical owner EOF','runtime animation behavior']))))


def verify(actual,pins):
    import json
    from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack import pooled_global_buff_id_sources as neutral,event_args_paths
    from scripts.game_data.memorypack.animation_enemy_shake_value_sources import primitive_program
    def norm(value):return json.loads(json.dumps(value))
    name=actual.get('typeName')
    need('own-current-callback-source',name in FIELDS and actual.get('schema')==SCHEMA and actual.get('nativeInputs')==pins
        and actual.get('status')=='validated-conditional-extra-value32-canonical-source'and actual.get('wrapperName')==WRAPPERS[name]
        and actual.get('managedBytes')==32 and actual.get('canonicalCallbackAbiProved')is True
        and all(actual.get(k)is False for k in('wireGrammarAdmitted','ordinaryOriginalReadValueAdmitted','parentFieldAdmitted','wholeOwnerAdmitted')))
    p=actual['proof'];nominal=p['layout'];pair=p['pair'];faces=pair.get('composition',{}).get('interfaces',[])
    need('own-nominal-layout',nominal.get('typeName')==name and nominal.get('fields')==FIELDS[name]
        and type(nominal.get('typeDefinition'))is int and nominal['typeDefinition']>=0 and nominal.get('boxedBytes')==48
        and nominal.get('managedBytes')==32 and nominal.get('marshaledNativeBytes')==(32 if name==STATE else 40)
        and nominal.get('marshaledSizeUsedForManagedWidth')is False and nominal.get('paddingRangeEncoding')=='start,length'
        and nominal.get('referenceLaneOffsets')==([0,16]if name==STATE else[0,8,16])
        and nominal.get('paddingByteRanges')==([[12,4],[28,4]]if name==STATE else[[27,5]])
        and nominal.get('generatedMemberNames')==(['interruptType','performId','stateHash']if name==STATE else
            ['effectName','eventName','followPosition','followRotation','stopWithState','targetBonePath'])
        and nominal.get('physicalFieldsAbsentFromGeneratedMembers')==(['stateName']if name==STATE else[])
        and nominal.get('wireFieldSelectionAdmitted')is False
        and nominal.get('wireGrammarAdmitted')is False)
    enums=nominal.get('enums',[])
    need('own-enum-layout-without-wire-promotion',
        [row.get('typeName')for row in enums]==([FIELDS[STATE][3][1]]if name==STATE else[])
        and all(type(row.get('typeDefinition'))is int and row['typeDefinition']>=0
            and row.get('backingType')in('int','uint')and row.get('backingBytes')==4 for row in enums))
    need('own-independent-pair-and-full-getter',pair['registration'].get('originalType')==name
        and pair['registration'].get('wrapperType')==WRAPPERS[name]and len(faces)==1
        and faces[0].get('originalType')==name and faces[0].get('wrapperType')==WRAPPERS[name]
        and pair.get('getterEntryProof',{}).get('entryProgram')==p['getter']
        and pair['getterEntryProof']['entryMethod'][0]==faces[0]['getValueMethodIndex']
        and p['forwarding']['readerMethod'][1:3]==[WRAPPERS[name],'Deserialize'])
    base=p['registrations']['adapter']['pointer']-p['symbolRvas']['adapter'];need('selected-image-base',type(base)is int and base>=2**32)
    raw={k:regions(p['sourceWindows'][k],rows,base,'extra-value32-'+k)for k,rows in p['sourceRegions'].items()}
    symbols={k:base+v for k,v in p['symbolRvas'].items()}
    def leaf(program,fn):
        selected=program.get('selectedBytes',[]);need('bounded-own-leaf',bool(selected))
        need('same-exact-full-leaf',norm(fn([(a,bytes.fromhex(h))for a,h in selected],selected[0][0]))==program)
    leaf(p['getter'],getter_program);need('both-own-zero32-factories',len(p.get('zeroLeaves',[]))==2)
    for row,role in zip(p['zeroLeaves'],('.ctor','CreateInstance'),strict=True):
        need('own-named-zero32',row['method'][1:3]==[WRAPPERS[name],role]);leaf(row['program'],zero_program)
    for role,fn,cases in(('adapter',adapter_program,({},dict(create=False),dict(null=True))),
        ('nonnull',nonnull_program,({'wrapper_null':False},{'wrapper_null':True})),('readNull',read_null_program,({'null':False},{'null':True}))):
        previous=p['paths'][role];need('complete-own-case-inventory:'+role,len(previous)==len(cases))
        for prior,options in zip(previous,cases,strict=True):
            own_symbols=prior.get('symbols',{});need('own-helper-identities',all(symbols.get(k)==v for k,v in own_symbols.items()))
            need('same-full-own-'+role,norm(fn(raw[role],symbols[role],own_symbols,**options))==prior)
    need('full-hidden32-interface-copy',norm(conversion_program(raw['conversion'],symbols['conversion'],
        ordinal=p['interfaceOrdinal'],prepare=symbols['prepare']))==p['paths']['conversion'])
    need('full-initialized-class-helper',norm(neutral.ready_class_init(raw['classReady'],symbols['classReady']))==p['paths']['classReady'])
    need('own-wrapper-slot-five',norm(deserialize_slot(raw['wrapperInvoke'],symbols['wrapperInvoke'],prepare=symbols['prepare'],
        callback=base+next(m[3]for m in pair['composition']['methods']if m[0]==faces[0]['formatterDeserializeMethodIndex'])))==p['paths']['wrapperInvocation'])
    for role in('adapter','nonnull','readNull'):
        reg=p['registrations'][role];args=reg.get('classInstantiation',{}).get('arguments',[])
        need('own-canonical-registration:'+role,len(args)==2 and reg.get('pointer')==symbols[role])
        carrier=bytes.fromhex(args[0].get('raw_type_record_hex',''))
        need('own-nominal-value-carrier',len(carrier)==16 and carrier[10:12]==b'\x11\x80'
            and int.from_bytes(carrier[:8],'little')==nominal['typeDefinition'])
    primitive_program(raw['header'],symbols['header'],p['readerOffsets'],single=False)
    need('own-complete-peek-source',norm(event_args_paths.peek(raw['peek'],symbols['peek'],p['readerOffsets']))==p['peek'])
    return dict(typeName=name,wrapperName=WRAPPERS[name],originalTypeDefinition=nominal['typeDefinition'],managedBytes=32,
        canonicalAdapterTargetRva=p['symbolRvas']['adapter'],formatterDeserializeMethodDefinition=faces[0]['formatterDeserializeMethodIndex'],
        referenceLaneOffsets=nominal['referenceLaneOffsets'],paddingByteRanges=nominal['paddingByteRanges'],paddingRangeEncoding='start,length',
        canonicalCallbackAbiProved=True,wireGrammarAdmitted=False)

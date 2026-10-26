"""AlphaBlend's own hidden56 Reader, canonical adapter and interface copies.

The 56-byte managed payload includes unserialized state. These exact programs
preserve that whole payload, while its MC3 wrapper and Beyond curve child own
the variable wire grammar separately. Provider and callback selection remain
conditional; no live closed MethodInfo or pointer alias is inferred.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.alpha_blend_value_sources import TYPE,WRAPPER,need
from scripts.game_data.memorypack.pooled_string_list_sources import flag


def adapter_program(regions,entry,s,*,dispatch=False,null=False,create=True):
    need('literal-adapter-paths',all(type(v)is bool for v in(dispatch,null,create)))
    g=BytesPath(regions,entry)
    if dispatch:
        g.take('48895c2408','48896c2410','4889742418','57','4883ec20','488b0a','498be9','498bf0','488bda')
        g.call(s['prepare']);g.take('488b3b')
        need('own-compared-canonical-adapter',g.relative('488d0d')==s['adapter'])
        g.take('488b8790010000','488bbf98010000','483bc1');g.branch('0f85',False)
        ready=flag(g);g.branch('0f84',False)
    else:
        g.take('48896c2410','4889742418','57','4883ec20');ready=flag(g)
        g.take('498bf9','498be8','488bf2');g.branch('0f84',False)
    g.take('488b4720','488bce','488b90c0000000','488b12');g.call(s['readNull']);g.take('84c0');g.branch('0f85',null)
    type_cell=None
    if null:
        g.take('0f57c0','33c0','0f114500','0f114510','0f114520','48894530');g.jump('e9')
    else:
        if not dispatch:g.take('48895c2430')
        g.take('488b4720');type_cell=g.relative('488b0d')
        g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('0f84',False)
        g.take('33d2','488bcb');g.call(s['typeHandle'])
        if not dispatch:g.take('488b5c2430')
        g.take('4885c0');g.branch('74',False,1)
        g.take('b944000000','488bd0');g.call(s['creationTest']);g.take('a980000000');g.branch('77',not create,1)
        if create:
            g.take('488b4720','488b88c0000000','488b4958');g.call(s['activate'])
        else:g.take('33c0');g.jump('eb',1)
        g.take('488b4f20','4c8bc0','488bd5','4c8b89c0000000','488bce','4d8b4918');g.call(s['nonnull'])
    if dispatch:g.take('488b5c2430')
    g.take('488b6c2438','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,typeClassCell=type_cell,dispatch=dispatch,ff=null,
        createWrapper=None if null else create,managedBytes=56,defaultZeroBytes=56 if null else 0,
        nullConsumptionDelegatedToOwnedReadIsNull=True,wrapperTypeSlot=10,activatorContextSlot=11,nonnullContextSlot=3,
        sameIncomingReaderAndHiddenOutput=True,entryRspRestored=True,normalReturn=True,
        callbackSelectionConditional=True,wholeOwnerAdmitted=False)


def read_program(regions,entry,s):
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec20','4983783800','498bf8','488bf2','488bd9');g.branch('74',False,1)
    g.take('0f57c0','33c0','0f1103','0f114310','0f114320','48894330');provider=g.relative('488b0d')
    g.take('3981e0000000');g.branch('74',False,1)
    g.take('488b4f38','488b09');g.call(s['provider']);g.take('4885c0');g.branch('74',False,1)
    g.take('4c8bcb','4c8bc6','488bd0');g.call(s['dispatch'])
    g.take('488bc3','488b5c2430','488b742438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,providerClassCell=provider,managedBytes=56,
        zeroedOutputSlices=[[0,16],[16,16],[32,16],[48,8]],sameIncomingReaderAndHiddenOutput=True,
        sameOutputReturnedInRax=True,initializedClosedContextRequired=True,matchingNonnullFormatterRequired=True,
        normalReturn=True,entryRspRestored=True,allIntegerNonvolatilesRestored=True,
        wireWidthAdmitted=False,wholeOwnerAdmitted=False)


def nonnull_program(regions,entry,s,*,wrapper_null=False):
    need('literal-wrapper-null-path',type(wrapper_null)is bool)
    g=BytesPath(regions,entry);g.take('48895c2408','4889742410','4c89442418','57','4883ec60');ready=flag(g)
    g.take('498bf9','488bf2','488bd9');g.branch('0f84',False)
    provider=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
    g.take('488b4f20');g.call(s['resolve']);g.take('488b88c0000000','488b4920');g.call(s['wrapperProvider'])
    g.take('4885c0');g.branch('0f84',False)
    g.take('b905000000','4c8d8c2480000000','4c8bc3','488bd0');g.call(s['wrapperInvoke'])
    g.take('488b9c2480000000','4885db');g.branch('0f84',wrapper_null)
    if wrapper_null:
        g.take('0f57c0','33c0','0f1106','0f114610','0f114620','48894630');g.jump('e9')
    else:
        g.take('488b4f20');g.call(s['resolve']);g.take('ba08000000','488b88c0000000');g.call(s['indexed'])
        g.take('4c8bc0','488d4c2420','33d2','4c8bcb');g.call(s['conversion'])
        g.take('488d4e08','0f1008','0f105010','0f105820','f20f104030',
            '0f110e','0f115610','0f115e20','f20f114630');g.call(s['barrier'])
    g.take('488b5c2470','488b742478','4883c460','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,providerClassCell=provider,wrapperNull=wrapper_null,
        managedBytes=56,defaultZeroBytes=56 if wrapper_null else 0,copiedSlices=[]if wrapper_null else[[0,16],[16,16],[32,16],[48,8]],
        referenceBarrierOffset=8,referenceLaneOffsets=[8],wrapperProviderContextSlot=4,conversionInterfaceContextSlot=8,
        conversionSelectorDxZero=True,wrapperOutputLocal=128,conversionOutputLocal=32,
        sameIncomingReaderAndHiddenOutput=True,normalReturn=True,entryRspRestored=True,
        allIntegerNonvolatilesRestored=True,wireWidthAdmitted=False,wholeOwnerAdmitted=False)


def conversion_program(regions,entry,prepare,*,ordinal):
    need('bounded-owned-interface-ordinal',type(ordinal)is int and 0<=ordinal<=16)
    g=BytesPath(regions,entry)
    g.take('48895c2408','48896c2410','4889742418','48897c2420','4156','4883ec60',
        '498b39','488bf1','488bcf','0fb7ea','4d8bf1','498bd8');g.call(prepare)
    g.take('440fb78730010000','33c0','66413bc0');g.branch('73',False,1);g.take('488b97b0000000')
    for index in range(ordinal+1):
        g.take('0fb7c8','4803c9','48391cca');g.branch('74',index==ordinal,1)
        if index<ordinal:g.take('66ffc0','66413bc0');g.branch('72',True,1)
    g.take('0fb7d0','488b87b0000000','4803d2','8b44d008','03c5','4898','4883c014','48c1e004','4803c7',
        '4c8b08','488d4c2420','4c8b4008','498bd6','41ffd1','4c8d5c2460','498b5b10','498b6b18',
        '0f1000','498b7b28','0f104810','0f1106','0f104020','0f114e10','f20f104830','488bc6',
        '0f114620','f20f114e30','498b7320','498be3','415e','c3')
    return dict(selectedBytes=g.seen,interfaceOrdinal=ordinal,methodSlot=0,requiresIncomingDxZero=True,
        getterArguments=dict(rcx='local56',rdx='same wrapper',r8='exact interface GetValue MethodInfo'),
        copiedSlices=[[0,16],[16,16],[32,16],[48,8]],managedBytes=56,
        getterReturnsSameOutputPointer=True,returnsSameIncomingHiddenOutput=True,normalReturn=True,
        entryRspRestored=True,allIntegerNonvolatilesRestored=True,fallbackInterfaceResolverAdmitted=False,
        wireWidthAdmitted=False,wholeOwnerAdmitted=False)


def request_shape(usage):
    need('own-hidden-ReadValue-request',tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
        ==(6,'MemoryPack.MemoryPackReader','ReadValue',[],[TYPE]))
    raw=bytes.fromhex(usage.get('instructionHex',''))
    need('literal-R8-context-load',len(raw)==7 and raw[:3]==bytes.fromhex('4c8b05'))
    method=usage.get('methodSpec')
    need('literal-closed-MethodSpec',isinstance(method,list)and len(method)==3
        and all(type(n)is int for n in method)and method[0]>0)


def _derive_on_child(image,pins,child,*,typed_request,source_target):
    import json
    import struct
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
    from scripts.game_data.memorypack import pointer_param as pointer,buff_ptr_sources as bp,primitive_param,event_args_paths
    from scripts.game_data.memorypack import scalar_param_native as scalar,pooled_global_buff_id_sources as providers
    from scripts.game_data.memorypack.alpha_blend_value_sources import getter_program
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.skill_nominal_value_read_sources import _provider,_selected_classes
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _selected_wrapper
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    _publication_gate(image,pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);ge=GenericEntries(image)
    request_shape(typed_request);need('literal-actual-source',type(source_target)is int and source_target>base)
    typed=bp._typed_context(image,typed_request,TYPE,ge)
    need('fresh-own-wrapper-source',child.get('schema')=='endfield.alpha-blend-wrapper-source.v1'
        and child.get('status')=='proved-conditional-alpha-blend-wrapper-source'and child.get('nativeInputs')==pins
        and child.get('typeName')==TYPE and child.get('wrapperName')==WRAPPER and child.get('managedBytes')==56
        and child.get('referenceLaneOffsets')==[8]and child.get('paddingByteRanges')==[[52,56]]
        and child.get('completeStaticWrapperPathsProved')is True)
    image.check_windows(child['proof']['codeWindows'],label='alphaTransfer.child')
    wrapper=_selected_wrapper(image,WRAPPER);pair=derive_pair(image,TYPE,WRAPPER)
    forwarding=pointer.registered_pair(image,pair,wrapper,label='alphaTransfer.pair')
    face,=pair['composition']['interfaces'];need('own-conversion-interface',face['wrapperDefinition']==wrapper.type_definition)
    getter=md.methods[face['getValueMethodIndex']]
    scalar.owned_method_abi(image,ctx,getter.index,wrapper.type_definition,(TYPE,17,False),[],'alphaTransfer.GetValue')
    at=image.method_pointer_va(getter);actual_getter=getter_program([(at,image.pe.bytes_at_va(at,128))],at)
    own_getters=[r for r in child['proof']['leaves']if r['method'][2]=='GetValue']
    need('same-whole56-own-getter',len(own_getters)==1 and own_getters[0]['method'][0]==getter.index
        and own_getters[0]['program']==json.loads(json.dumps(actual_getter)))
    td=md.types[wrapper.type_definition];section=md.sections['interfaceOffsets'];start=section.offset+td.interface_offsets_start*8
    ordinal=list(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8])).index((face['interfaceTypeIndex'],face['interfaceOffset']))
    context,context_proof=bp._adapter_context(image,ge);sources={};registrations={};s={}
    for role,name in(('adapter','Deserialize'),('nonnull','DeserializeNotNull')):
        method=bp._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2',name)
        registrations[role]=ge.resolve(method.index,[TYPE,'object'],[]);s[role]=registrations[role]['pointer'];sources[role]=pointer.owned(image,s[role])
    sources['read']=pointer.owned(image,source_target)
    s.update(provider=bp._call(sources['read'],73),dispatch=bp._call(sources['read'],92))
    for role,offset in dict(readNull=54,typeHandle=112,creationTest=135,activate=162,nonnull=191).items():
        target=bp._call(sources['adapter'],offset)
        if role in s:need('same-own-canonical-target:'+role,s[role]==target)
        s[role]=target
    method=bp._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2','ReadIsNull')
    registrations['readNull']=ge.resolve(method.index,[TYPE,'object'],[])
    need('own-closed-ReadIsNull',registrations['readNull']['pointer']==s['readNull'])
    sources['readNull']=pointer.owned(image,s['readNull']);s['peek']=bp._call(sources['readNull'],14)
    ff=BytesPath(sources['readNull']['regions'],s['readNull']+21).relative('0f85')
    s['header']=BytesPath(sources['readNull']['regions'],ff+8).relative('e8')
    s.update({role:bp._call(sources['nonnull'],offset)for role,offset in
        dict(resolve=66,wrapperProvider=82,wrapperInvoke=115,indexed=158,conversion=176,barrier=217).items()})
    need('same-nonnull-context-resolver',s['resolve']==bp._call(sources['nonnull'],141))
    need('same-own-wrapper-disabled-barrier',s['barrier']==base+child['proof']['barrierSource']['actualEntryRva'])
    for role in('provider','dispatch','conversion','wrapperInvoke','peek','header'):sources[role]=pointer.owned(image,s[role])
    s['prepare']=bp._call(sources['dispatch'],32)
    need('same-interface-preparation',s['prepare']==bp._call(sources['conversion'],44))
    paths={role:[adapter_program(sources[role]['regions'],s[role],s,dispatch=role=='dispatch',**p)
        for p in({},{'create':False},{'null':True})]for role in('adapter','dispatch')}
    paths['nonnull']=[nonnull_program(sources['nonnull']['regions'],s['nonnull'],s,wrapper_null=n)for n in(False,True)]
    paths['readNull']=[providers.read_null_program(sources['readNull']['regions'],s['readNull'],s,null=n)for n in(False,True)]
    paths['conversion']=conversion_program(sources['conversion']['regions'],s['conversion'],s['prepare'],ordinal=ordinal)
    reader=read_program(sources['read']['regions'],source_target,s)
    provider=_provider(image,sources['provider'],s)
    need('named-TypeFromHandle',s['typeHandle']==base+pair['registration']['helperMethods']['typeFromHandle'][3])
    need('same-provider-TypeFromHandle',s['typeHandle']==provider['symbols']['typeHandle'])
    need('same-provider-context-indexer',s['indexed']==provider['symbols']['indexed'])
    if provider['profile']=='called-cast':
        sources['cast']=pointer.owned(image,provider['symbols']['cast'])
        targets={control_transfer(r)['target']for r in sources['cast']['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8'}
        need('one-actual-cast-predicate',len(targets)==1);predicate,=targets
        provider['castPrograms']=[providers.successful_cast(sources['cast']['regions'],sources['cast']['pointer'],predicate,null=n)for n in(False,True)]
    read_classes=_selected_classes(image,sources['read'],reader)
    need('actual-reader-provider-class',[(r['tag'],r['typeName'])for r in read_classes]==[(1,'MemoryPack.MemoryPackFormatterProvider')])
    provider_classes=_selected_classes(image,sources['provider'],provider['program'])
    need('actual-provider-classes',[(r['tag'],r['typeName'])for r in provider_classes]==[(1,'System.Type'),(1,'MemoryPack.MemoryPackFormatterProvider')])
    invocation=deserialize_slot(sources['wrapperInvoke']['regions'],s['wrapperInvoke'],prepare=s['prepare'],
        callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]))
    offsets=scalar.reader_offsets(image,'alphaTransfer');peek=event_args_paths.peek(sources['peek']['regions'],s['peek'],offsets)
    header=vector_recorder(image)(s['header']-base);primitive_param.object_header_source(image,header,offsets)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.alpha-blend-value-transfer.v1',status='proved-conditional-alpha-blend-value56-read',
        nativeInputs=pins,typeName=TYPE,wrapperName=WRAPPER,managedBytes=56,resultAbi='hidden-local',actualSourceProved=True,
        sourceTargetRva=source_target-base,readerMethodDefinition=typed_request['methodSpec'][0],referenceLaneOffsets=[8],paddingByteRanges=[[52,56]],
        wireGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(typedRequest=typed_request,typedContext=typed,childSource=child,registeredPair=pair,wrapperForwarding=forwarding,
            adapterContext=context,adapterContextProof=context_proof,registrations=registrations,interfaceOrdinal=ordinal,
            readerProgram=reader,paths=paths,providerProgram=provider,readClasses=read_classes,providerClasses=provider_classes,
            wrapperInvocation=invocation,peek=peek,header=header,symbolRvas={k:v-base for k,v in s.items()},
            sourceWindows={k:v['windows']for k,v in sources.items()},
            actualSourceRegions={k:[[at-base,raw.hex()]for at,raw in v['regions']]for k,v in sources.items()},
            actualComparedCanonicalAdapterRva=s['adapter']-base,closedWrapperPointerEqualityInferred=False,runtimeSelectionObserved=False,
            condition='Exact AlphaBlend/object canonical callback equality with coherent closed contexts and own wrapper/interface GetValue. Initialized metadata, compatible provider results, successful ordinary helper effects, stable disjoint storage and disabled barriers remain conditions. No raw56 wire, runtime provider choice, parent field/frame or physical EOF follows.'))))


def derive(image,pins,*,typed_request,source_target,count_limit=10000):
    from scripts.game_data.memorypack.alpha_blend_value_sources import derive_wrapper
    return _derive_on_child(image,pins,derive_wrapper(image,pins,count_limit=count_limit),typed_request=typed_request,source_target=source_target)

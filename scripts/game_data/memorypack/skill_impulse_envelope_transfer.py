"""Selected Envelope managed32 Reader and canonical value adapter transfers.

The nominal seven-member wrapper source and managed layout are independent
inputs freshly derived here. The actual Reader's dispatcher must compare its
slot-five callback against this value's independently registered canonical
adapter. Its interface conversion copies both sixteen-byte chunks unchanged.
This proves conditional source and ABI transfers, not a serialized raw32 width,
an enclosing parent, runtime provider choice or callback invocation.
"""
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath,deserialize_slot
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.skill_impulse_envelope_sources import TYPE,WRAPPER,need


def adapter_program(regions,entry,s,*,dispatch=False,null=False,create=True):
    need('literal-adapter-paths',all(type(v)is bool for v in(dispatch,null,create)))
    g=BytesPath(regions,entry)
    if dispatch:
        g.take('48895c2410','48896c2418','4889742420','66894c2408','57','4883ec20',
            '488b0a','498be9','498bf0','488bda');g.call(s['prepare'])
        g.take('488b03','4c8b9090010000','488bb898010000')
        need('actual-compared-canonical-adapter',g.relative('488d05')==s['adapter'])
        g.take('4c3bd0');g.branch('0f85',False);ready=flag(g);g.branch('0f84',False)
    else:
        g.take('48896c2418','4889742420','57','4883ec20');ready=flag(g)
        g.take('498bf9','498be8','488bf2');g.branch('0f84',False)
    g.take('488bce','c64424'+('30'if dispatch else'38')+'00');g.call(s['peek'])
    g.take('84c0');g.branch('0f85',null)
    type_cell=None
    if null:
        g.take('488d5424'+('30'if dispatch else'38'),'488bce');g.call(s['header'])
        g.take('0f57c0','0f114500','0f114510');g.jump('e9')
    else:
        if not dispatch:g.take('48895c2430')
        g.take('488b4720');type_cell=g.relative('488b0d')
        g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('0f84',False)
        g.take('33d2','488bcb');g.call(s['typeHandle'])
        if not dispatch:g.take('488b5c2430')
        g.take('4885c0');g.branch('74',False,1)
        g.take('b944000000','488bd0');g.call(s['creationTest'])
        g.take('a980000000');g.branch('77',not create,1)
        if create:
            g.take('488b4720','488b88c0000000','488b4958');g.call(s['activate'])
        else:g.take('33c0');g.jump('eb',1)
        g.take('488b4f20','4c8bc0','488bd5','4c8b89c0000000','488bce','4d8b4918')
        g.call(s['nonnull'])
    if dispatch:g.take('488b5c2438')
    g.take('488b6c2440','488b742448','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,dispatch=dispatch,ff=null,
        createWrapper=None if null else create,typeClassCell=type_cell,managedOutputBytes=32,
        ffDefaultOutputBytes=32 if null else 0,wireBytes=1 if null else None,
        nonnullContextSlot=3,wrapperTypeSlot=10,activatorContextSlot=11,
        sameIncomingReaderAndHiddenOutput=True,normalReturn=True,entryRspRestored=True,
        allIntegerNonvolatilesRestored=True,callbackSelectionConditional=True)


def read_program(regions,entry,s):
    g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20',
        '4983783800','498bf8','488bf2','488bd9');g.branch('74',False,1)
    g.take('0f57c0','0f1103','0f114310');provider=g.relative('488b0d')
    g.take('83b9e000000000');g.branch('74',False,1)
    g.take('488b4f38','488b09');g.call(s['provider']);g.take('4885c0');g.branch('74',False,1)
    g.take('4c8bcb','4c8bc6','488bd0');g.call(s['dispatch'])
    g.take('488bc3','488b5c2430','488b742438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,providerClassCell=provider,managedBytes=32,zeroedOutputBytes=32,
        sameIncomingReaderAndHiddenOutput=True,sameOutputReturnedInRax=True,
        initializedClosedContextRequired=True,matchingNonnullFormatterRequired=True,
        normalReturn=True,entryRspRestored=True,allIntegerNonvolatilesRestored=True)


def nonnull_program(regions,entry,s,*,wrapper_null=False):
    need('literal-wrapper-null-path',type(wrapper_null)is bool)
    g=BytesPath(regions,entry);g.take('48895c2408','4889742410','4c89442418','57','4883ec40');ready=flag(g)
    g.take('498bf9','488bf2','488bd9');g.branch('0f84',False)
    provider=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
    g.take('488b4f20');g.call(s['resolve']);g.take('488b88c0000000','488b4920');g.call(s['wrapperProvider'])
    g.take('4885c0');g.branch('0f84',False)
    g.take('b905000000','4c8d4c2460','4c8bc3','488bd0');g.call(s['wrapperInvoke'])
    g.take('488b5c2460','4885db');g.branch('0f84',wrapper_null)
    if wrapper_null:
        g.take('0f57c0','0f1106','0f114610');g.jump('e9')
    else:
        g.take('488b4f20');g.call(s['resolve']);g.take('ba08000000','488b88c0000000');g.call(s['indexed'])
        g.take('4c8bc0','488d4c2420','4c8bcb');g.call(s['conversion'])
        g.take('488bce','0f1000','0f104810','0f1106','0f114e10');g.call(s['barrier'])
    g.take('488b5c2450','488b742458','4883c440','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,providerClassCell=provider,
        returnedWrapperNull=wrapper_null,outputBytes=32,defaultOutputBytes=32 if wrapper_null else 0,
        wrapperProviderContextSlot=4,conversionInterfaceContextSlot=8,
        copiedChunkBytes=[]if wrapper_null else[16,16],referenceLaneOffsets=[0,8],
        referenceBarrierOffset=0,sameIncomingReaderAndHiddenOutput=True,
        entryRspRestored=True,normalReturn=True,allIntegerNonvolatilesRestored=True)


def conversion_program(regions,entry,prepare,*,ordinal):
    need('bounded-owned-interface-ordinal',type(ordinal)is int and 0<=ordinal<=16)
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','48897c2418','4156','4883ec40','498b39','488bf1','488bcf','4d8bf1','498bd8')
    g.call(prepare);g.take('440fb78730010000','33c0','66413bc0');g.branch('73',False,1)
    g.take('488b97b0000000')
    for index in range(ordinal+1):
        g.take('0fb7c8','4803c9','48391cca');g.branch('74',index==ordinal,1)
        if index<ordinal:g.take('66ffc0','66413bc0');g.branch('72',True,1)
    g.take('0fb7c8','4803c9','486344ca08','4883c014','48c1e004','4803c7',
        '4c8b08','488d4c2420','4c8b4008','498bd6','41ffd1','488b5c2450','488b7c2460',
        '0f1000','0f104810','488bc6','0f1106','0f114e10','488b742458','4883c440','415e','c3')
    return dict(selectedBytes=g.seen,interfaceOrdinal=ordinal,methodSlot=0,
        getterArguments=dict(rcx='local32',rdx='same wrapper',r8='exact interface GetValue MethodInfo'),
        getterReturnsSameOutputPointer=True,copiedChunkBytes=[16,16],outputBytes=32,
        returnValue='same incoming hidden32 output address',normalReturn=True,entryRspRestored=True,
        allIntegerNonvolatilesRestored=True,fallbackInterfaceResolverAdmitted=False)


def request_shape(usage):
    need('exact-envelope-ReadValue-request',tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
        ==(6,'MemoryPack.MemoryPackReader','ReadValue',[],[TYPE]))
    raw=bytes.fromhex(usage.get('instructionHex',''))
    need('exact-hidden-R8-context-load',len(raw)==7 and raw[:3]==bytes.fromhex('4c8b05'))
    method=usage.get('methodSpec')
    need('literal-MethodSpec-definition',isinstance(method,list)and len(method)==3
        and all(type(n)is int for n in method)and method[0]>0)


def _derive_on_child(image,pins,child,*,typed_request,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack import pointer_param as pointer,buff_ptr_sources as bp,primitive_param,event_args_paths
    from scripts.game_data.memorypack import scalar_param_native as scalar,pooled_global_buff_id_sources as providers
    from scripts.game_data.memorypack.skill_nominal_value_read_sources import _provider,_selected_classes
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _selected_wrapper
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    _publication_gate(image,pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);ge=GenericEntries(image)
    request_shape(typed_request);need('literal-actual-source-pointer',type(source_target)is int and source_target>base)
    typed=bp._typed_context(image,typed_request,TYPE,ge)
    need('fresh-exact-wrapper-child',(child['nativeInputs'],child['typeName'],child['wrapperName'],child['layout']['managedBytes'],child['layout']['referenceLaneOffsets'])
        ==(pins,TYPE,WRAPPER,32,[0,8]))
    image.check_windows(child['sourceWindows'],label='envelopeTransfer.child')
    wrapper=_selected_wrapper(image,WRAPPER);pair=child['registeredPair'];pointer.registered_pair(image,pair,wrapper,label='envelopeTransfer.pair')
    face,=pair['composition']['interfaces'];need('own-interface-wrapper',face['wrapperDefinition']==wrapper.type_definition)
    getter=md.methods[face['getValueMethodIndex']]
    scalar.owned_method_abi(image,ctx,getter.index,wrapper.type_definition,(TYPE,17,False),[],'envelopeTransfer.GetValue')
    actual_getter=pointer.leaf(image,image.method_pointer_va(getter),['0F104210','488BC1','0F104A20','0F1101','0F114910','C3'])
    need('same-own-getter-program',child['getter']==actual_getter)
    td=md.types[wrapper.type_definition];section=md.sections['interfaceOffsets'];start=section.offset+td.interface_offsets_start*8
    ordinal=list(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8])).index((face['interfaceTypeIndex'],face['interfaceOffset']))
    context,context_proof=bp._adapter_context(image,ge);sources={};registrations={};s={}
    for role,name in(('adapter','Deserialize'),('nonnull','DeserializeNotNull')):
        method=bp._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2',name)
        registrations[role]=ge.resolve(method.index,[TYPE,'object'],[]);s[role]=registrations[role]['pointer'];sources[role]=pointer.owned(image,s[role])
    sources['read']=pointer.owned(image,source_target)
    s.update(provider=bp._call(sources['read'],64),dispatch=bp._call(sources['read'],83))
    for role,offset in dict(peek=45,typeHandle=103,creationTest=126,activate=153,nonnull=182).items():
        actual=bp._call(sources['adapter'],offset)
        if role in s:need('same-actual-closed-canonical-target:'+role,s[role]==actual)
        s[role]=actual
    ff=BytesPath(sources['adapter']['regions'],s['adapter']+52).relative('0f85')
    s['header']=BytesPath(sources['adapter']['regions'],ff+8).relative('e8')
    s.update({role:bp._call(sources['nonnull'],offset)for role,offset in dict(resolve=66,wrapperProvider=82,wrapperInvoke=112,indexed=152,conversion=168,barrier=190).items()})
    need('same-context-resolver',s['resolve']==bp._call(sources['nonnull'],135))
    need('same-wrapper-barrier',s['barrier']==base+child['symbolRvas']['barrier'])
    for role in('provider','dispatch','conversion','wrapperInvoke','peek','header'):sources[role]=pointer.owned(image,s[role])
    s['prepare']=bp._call(sources['dispatch'],37)
    need('same-conversion-prepare',s['prepare']==bp._call(sources['conversion'],36))
    paths={role:[adapter_program(sources[role]['regions'],s[role],s,dispatch=role=='dispatch',**p)
        for p in({},{'create':False},{'null':True})]for role in('adapter','dispatch')}
    paths['nonnull']=[nonnull_program(sources['nonnull']['regions'],s['nonnull'],s,wrapper_null=n)for n in(False,True)]
    paths['conversion']=conversion_program(sources['conversion']['regions'],s['conversion'],s['prepare'],ordinal=ordinal)
    actual_read=read_program(sources['read']['regions'],source_target,s)
    provider=_provider(image,sources['provider'],s)
    need('named-TypeFromHandle',s['typeHandle']==base+pair['registration']['helperMethods']['typeFromHandle'][3])
    need('same-provider-TypeFromHandle',s['typeHandle']==provider['symbols']['typeHandle'])
    need('same-provider-context-indexer',s['indexed']==provider['symbols']['indexed'])
    if provider['profile']=='called-cast':
        sources['cast']=pointer.owned(image,provider['symbols']['cast'])
        targets={control_transfer(r)['target']for r in sources['cast']['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8'}
        need('one-actual-compatible-cast-predicate',len(targets)==1);predicate,=targets
        provider['castPrograms']=[providers.successful_cast(sources['cast']['regions'],sources['cast']['pointer'],predicate,null=n)for n in(False,True)]
    read_classes=_selected_classes(image,sources['read'],actual_read)
    need('actual-reader-provider-class',[(c['tag'],c['typeName'])for c in read_classes]==[(1,'MemoryPack.MemoryPackFormatterProvider')])
    provider_classes=_selected_classes(image,sources['provider'],provider['program'])
    need('actual-provider-static-classes',[(c['tag'],c['typeName'])for c in provider_classes]==[(1,'System.Type'),(1,'MemoryPack.MemoryPackFormatterProvider')])
    invocation=deserialize_slot(sources['wrapperInvoke']['regions'],s['wrapperInvoke'],prepare=s['prepare'],
        callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]))
    offsets=scalar.reader_offsets(image,'envelopeTransfer')
    peek=event_args_paths.peek(sources['peek']['regions'],s['peek'],offsets)
    header=vector_recorder(image)(s['header']-base);primitive_param.object_header_source(image,header,offsets)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.impulse-envelope-value-transfer.v1',status='proved-conditional-envelope-value32-read',
        nativeInputs=pins,typeName=TYPE,wrapperName=WRAPPER,managedBytes=32,resultAbi='hidden-local',actualSourceProved=True,
        sourceTargetRva=source_target-base,readerMethodDefinition=typed_request['methodSpec'][0],referenceLaneOffsets=[0,8],
        wireGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(typedRequest=typed_request,typedContext=typed,childSource=child,adapterContext=context,adapterContextProof=context_proof,
            registrations=registrations,interfaceOrdinal=ordinal,readerProgram=actual_read,paths=paths,providerProgram=provider,
            readClasses=read_classes,providerClasses=provider_classes,wrapperInvocation=invocation,peek=peek,header=header,
            symbolRvas={k:v-base for k,v in s.items()},sourceWindows={k:b['windows']for k,b in sources.items()},
            actualComparedCanonicalAdapterRva=s['adapter']-base,closedWrapperPointerEqualityInferred=False,
            runtimeSelectionObserved=False,condition='The selected runtime callback equals the freshly resolved Envelope/object canonical adapter, with coherent exact Envelope/wrapper closed MethodInfo, selected conversion interface/GetValue and normal compatible provider/allocator/barrier effects. Runtime provider/callback choice and closed-wrapper pointer equality are not inferred. Disjoint buffered storage and initialized contexts are required.'))))


def derive(image,pins,*,typed_request,source_target):
    """Derive the own nominal wrapper and selected actual transfer afresh."""
    from scripts.game_data.memorypack.skill_impulse_envelope_sources import derive_wrapper
    return _derive_on_child(image,pins,derive_wrapper(image,pins),typed_request=typed_request,source_target=source_target)

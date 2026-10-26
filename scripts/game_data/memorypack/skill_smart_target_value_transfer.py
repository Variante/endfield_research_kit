"""Actual SmartTarget hidden40 Reader and canonical value transfer programs.

Own nominal fields, contexts and closed canonical entries are mandatory. The
fixed40 interface-copy byte program is a reusable ABI lemma; it supplies no
AssignPair identity or wire grammar. The actual dispatcher must compare its
callback with this value's independently selected canonical adapter. Normal
matching callbacks, initialized contexts, compatible disjoint storage and the
disabled collector remain conditions; live provider selection is unobserved.
"""
import json,struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath,deserialize_slot
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.skill_root_child_bindings import need
from scripts.game_data.memorypack.skill_smart_target_value_sources import TYPE,WRAPPER
from scripts.game_data.memorypack.skill_root_assign_pair_transfer import conversion40_program


def adapter_program(regions,entry,s,*,dispatch=False,null=False,create=True):
    need('smart-target-literal-adapter-paths',True,all(type(v)is bool for v in(dispatch,null,create)))
    g=BytesPath(regions,entry)
    if dispatch:
        g.take('48895c2408','48896c2410','4889742418','57','4883ec20','488b0a','498be9','498bf0','488bda')
        g.call(s['prepare']);g.take('488b3b')
        need('smart-target-actual-compared-canonical-adapter',s['adapter'],g.relative('488d0d'))
        g.take('488b8790010000','488bbf98010000','483bc1');g.branch('0f85',False)
        ready=flag(g);g.branch('0f84',False)
    else:
        g.take('48896c2410','4889742418','57','4883ec20');ready=flag(g)
        g.take('498bf9','498be8','488bf2');g.branch('0f84',False)
    g.take('488b4720','488bce','488b90c0000000','488b12');g.call(s['readNull']);g.take('84c0');g.branch('0f85',null)
    type_cell=None
    if null:
        g.take('0f57c0','33c0','0f114500','0f114510','48894520');g.jump('e9')
    else:
        if not dispatch:g.take('48895c2430')
        g.take('488b4720');type_cell=g.relative('488b0d')
        g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('74',False,1)
        g.take('33d2','488bcb');g.call(s['typeHandle'])
        if not dispatch:g.take('488b5c2430')
        g.take('4885c0');g.branch('74',False,1);g.take('33d2','488bc8');g.call(s['creationTest'])
        g.take('84c0');g.branch('75',not create,1)
        if create:g.take('488b4720','488b88c0000000','488b4958');g.call(s['activate'])
        else:g.take('33c0');g.jump('eb',1)
        g.take('488b4f20','4c8bc0','488bd5','4c8b89c0000000','488bce','4d8b4918');g.call(s['nonnull'])
    if dispatch:g.take('488b5c2430')
    g.take('488b6c2438','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,typeClassCell=type_cell,dispatch=dispatch,ff=null,
        createWrapper=None if null else create,managedBytes=40,defaultZeroBytes=40 if null else 0,
        nullConsumptionDelegatedToOwnedReadIsNull=True,wrapperTypeSlot=10,activatorContextSlot=11,nonnullContextSlot=3,
        sameIncomingReaderAndHiddenOutput=True,entryRspRestored=True,normalReturn=True)


def read_program(regions,entry,s):
    g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20',
        '4983783800','498bf8','488bf2','488bd9');g.branch('74',False,1)
    g.take('0f57c0','33c0','0f1103','0f114310','48894320');provider=g.relative('488b0d')
    g.take('3981e0000000');g.branch('74',False,1)
    g.take('488b4f38','488b09');g.call(s['provider']);g.take('4885c0');g.branch('74',False,1)
    g.take('4c8bcb','4c8bc6','488bd0');g.call(s['dispatch'])
    g.take('488bc3','488b5c2430','488b742438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,providerClassCell=provider,managedBytes=40,zeroedOutputBytes=40,
        sameIncomingReaderAndHiddenOutput=True,sameOutputReturnedInRax=True,
        initializedClosedContextRequired=True,matchingNonnullFormatterRequired=True,
        normalReturn=True,entryRspRestored=True,allIntegerNonvolatilesRestored=True)


def nonnull_program(regions,entry,s,*,wrapper_null=False):
    need('smart-target-literal-wrapper-null',bool,type(wrapper_null))
    g=BytesPath(regions,entry);g.take('48895c2408','4889742410','4c89442418','57','4883ec50');ready=flag(g)
    g.take('498bf9','488bf2','488bd9');g.branch('0f84',False)
    provider=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
    g.take('488b4f20');g.call(s['resolve']);g.take('488b88c0000000','488b4920');g.call(s['wrapperProvider'])
    g.take('4885c0');g.branch('0f84',False)
    g.take('b905000000','4c8d4c2470','4c8bc3','488bd0');g.call(s['wrapperInvoke'])
    g.take('488b5c2470','4885db');g.branch('0f84',wrapper_null)
    if wrapper_null:
        g.take('0f57c0','33c0','0f1106','0f114610','48894620');g.jump('e9')
    else:
        g.take('488b4f20');g.call(s['resolve']);g.take('ba08000000','488b88c0000000');g.call(s['indexed'])
        g.take('4c8bc0','488d4c2420','4c8bcb');g.call(s['conversion'])
        g.take('488d4e08','0f1008','0f105010','f20f104020','0f110e','0f115610','f20f114620');g.call(s['barrier'])
    g.take('488b5c2460','488b742468','4883c450','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,providerClassCell=provider,wrapperNull=wrapper_null,
        managedBytes=40,defaultZeroBytes=40 if wrapper_null else 0,copiedBytes=0 if wrapper_null else 40,
        referenceBarrierOffset=8,referenceLaneOffsets=[8,24,32],wrapperProviderContextSlot=4,conversionInterfaceContextSlot=8,
        sameIncomingReaderAndHiddenOutput=True,normalReturn=True,entryRspRestored=True,allIntegerNonvolatilesRestored=True)


def _derive_on_child(image,pins,child,*,typed_request,source_target):
    """Internal composition; caller freshly derives this own child on image."""
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
    need('smart-target-exact-ReadValue-request',(6,'MemoryPack.MemoryPackReader','ReadValue',[],[TYPE]),
        tuple(typed_request.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments')))
    raw=bytes.fromhex(typed_request.get('instructionHex',''));need('smart-target-hidden-context-register',True,len(raw)==7 and raw[:3]==bytes.fromhex('4c8b05'))
    need('smart-target-actual-source-pointer',True,type(source_target)is int and source_target>base)
    typed=bp._typed_context(image,typed_request,TYPE,ge)
    need('smart-target-own-child-and-layout',(pins,TYPE,WRAPPER,40,[8,24,32]),
        tuple(child[k]for k in('nativeInputs','typeName','wrapperName'))+(child['layout']['managedBytes'],child['layout']['referenceLaneOffsets']))
    image.check_windows(child['sourceWindows'],label='smartTargetTransfer.child')
    wrapper=_selected_wrapper(image,WRAPPER);pair=child['registeredPair'];pointer.registered_pair(image,pair,wrapper,label='smartTargetTransfer.pair')
    face,=pair['composition']['interfaces'];need('smart-target-own-conversion-wrapper',wrapper.type_definition,face['wrapperDefinition'])
    getter=md.methods[face['getValueMethodIndex']];scalar.owned_method_abi(image,ctx,getter.index,wrapper.type_definition,(TYPE,17,False),[],'smartTargetTransfer.GetValue')
    actual_getter=pointer.leaf(image,image.method_pointer_va(getter),['0F104210','488BC1','0F104A20','0F1101','F20F104230','0F114910','F20F114120','C3'])
    need('smart-target-same-own-getter',child['getter'],actual_getter)
    td=md.types[wrapper.type_definition];section=md.sections['interfaceOffsets'];at=section.offset+td.interface_offsets_start*8
    ordinal=list(struct.iter_unpack('<ii',md.buf[at:at+td.interface_offsets_count*8])).index((face['interfaceTypeIndex'],face['interfaceOffset']))
    context,context_proof=bp._adapter_context(image,ge);sources={};registrations={};s={}
    for role,name in(('adapter','Deserialize'),('nonnull','DeserializeNotNull')):
        method=bp._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2',name)
        registrations[role]=ge.resolve(method.index,[TYPE,'object'],[]);s[role]=registrations[role]['pointer'];sources[role]=pointer.owned(image,s[role])
    sources['read']=pointer.owned(image,source_target)
    def call(body,offset):
        rows=[r for r in body['rows']if int(r['va'],16)==body['pointer']+offset]
        need('smart-target-actual-callsite:'+str(body['pointer']-base)+'+'+str(offset),1,len(rows))
        row,=rows;encoded=bytes.fromhex(row['bytes'])
        need('smart-target-owned-actual-E8',(5,232),(len(encoded),encoded[0]));return control_transfer(row)['target']
    s.update(provider=call(sources['read'],69),dispatch=call(sources['read'],88))
    for role,offset in dict(readNull=54,typeHandle=108,creationTest=128,activate=152,nonnull=181).items():
        target=call(sources['adapter'],offset)
        if role in s:need('smart-target-own-closed-canonical-target:'+role,s[role],target)
        s[role]=target
    method=bp._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2','ReadIsNull')
    registrations['readNull']=ge.resolve(method.index,[TYPE,'object'],[])
    need('smart-target-own-closed-ReadIsNull',registrations['readNull']['pointer'],s['readNull'])
    sources['readNull']=pointer.owned(image,s['readNull']);s['peek']=call(sources['readNull'],14)
    ff=BytesPath(sources['readNull']['regions'],s['readNull']+21).relative('0f85')
    s['header']=BytesPath(sources['readNull']['regions'],ff+8).relative('e8')
    s.update({role:call(sources['nonnull'],offset)for role,offset in dict(resolve=66,wrapperProvider=82,wrapperInvoke=112,indexed=152,conversion=168,barrier=201).items()})
    need('smart-target-same-context-resolver',s['resolve'],call(sources['nonnull'],135))
    need('smart-target-same-wrapper-barrier',base+child['symbolRvas']['barrier'],s['barrier'])
    for role in('provider','dispatch','conversion','wrapperInvoke','peek','header'):sources[role]=pointer.owned(image,s[role])
    s['prepare']=call(sources['dispatch'],32);need('smart-target-same-interface-prepare',s['prepare'],call(sources['conversion'],36))
    paths={role:[adapter_program(sources[role]['regions'],s[role],s,dispatch=role=='dispatch',**p)
        for p in({},{'create':False},{'null':True})]for role in('adapter','dispatch')}
    paths['nonnull']=[nonnull_program(sources['nonnull']['regions'],s['nonnull'],s,wrapper_null=n)for n in(False,True)]
    paths['readNull']=[providers.read_null_program(sources['readNull']['regions'],s['readNull'],s,null=n)for n in(False,True)]
    paths['conversion']=conversion40_program(sources['conversion']['regions'],s['conversion'],s['prepare'],ordinal=ordinal)
    actual_read=read_program(sources['read']['regions'],source_target,s)
    provider=_provider(image,sources['provider'],s)
    need('smart-target-named-TypeFromHandle',base+pair['registration']['helperMethods']['typeFromHandle'][3],s['typeHandle'])
    need('smart-target-same-provider-TypeFromHandle',s['typeHandle'],provider['symbols']['typeHandle'])
    need('smart-target-same-provider-indexed-helper',s['indexed'],provider['symbols']['indexed'])
    if provider['profile']=='called-cast':
        sources['cast']=pointer.owned(image,provider['symbols']['cast'])
        targets={control_transfer(r)['target']for r in sources['cast']['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8'}
        need('smart-target-one-actual-cast-predicate',1,len(targets));predicate,=targets
        provider['castPrograms']=[providers.successful_cast(sources['cast']['regions'],sources['cast']['pointer'],predicate,null=n)for n in(False,True)]
    read_classes=_selected_classes(image,sources['read'],actual_read)
    need('smart-target-actual-reader-provider-class',[(1,'MemoryPack.MemoryPackFormatterProvider')],[(c['tag'],c['typeName'])for c in read_classes])
    provider_classes=_selected_classes(image,sources['provider'],provider['program'])
    need('smart-target-actual-provider-static-classes',[(1,'System.Type'),(1,'MemoryPack.MemoryPackFormatterProvider')],[(c['tag'],c['typeName'])for c in provider_classes])
    invocation=deserialize_slot(sources['wrapperInvoke']['regions'],s['wrapperInvoke'],prepare=s['prepare'],callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]))
    offsets=scalar.reader_offsets(image,'smartTargetTransfer');peek=event_args_paths.peek(sources['peek']['regions'],s['peek'],offsets)
    header=vector_recorder(image)(s['header']-base);primitive_param.object_header_source(image,header,offsets)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-smart-target-value-transfer.v1',status='proved-conditional-smart-target-value40-read',
        nativeInputs=pins,typeName=TYPE,wrapperName=WRAPPER,managedBytes=40,resultAbi='hidden-local',actualSourceProved=True,
        sourceTargetRva=source_target-base,readerMethodDefinition=typed_request['methodSpec'][0],referenceLaneOffsets=[8,24,32],
        wireGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(typedRequest=typed_request,typedContext=typed,childSource=child,adapterContext=context,adapterContextProof=context_proof,
            registrations=registrations,interfaceOrdinal=ordinal,readerProgram=actual_read,paths=paths,providerProgram=provider,
            readClasses=read_classes,providerClasses=provider_classes,wrapperInvocation=invocation,peek=peek,header=header,
            symbolRvas={k:v-base for k,v in s.items()},sourceWindows={k:v['windows']for k,v in sources.items()},
            actualComparedCanonicalAdapterRva=s['adapter']-base,closedWrapperPointerEqualityInferred=False))))


def derive(image,pins,*,typed_request,source_target):
    """Fresh public source proof; saved child declarations cannot replace it."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_smart_target_value_sources import derive_wrapper
    _publication_gate(image,pins)
    return _derive_on_child(image,pins,derive_wrapper(image,pins),typed_request=typed_request,source_target=source_target)

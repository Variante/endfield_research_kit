"""Selected AssignPair value40 adapter, dispatcher and conversion programs.

The actual closed list dispatcher compares slot5 to the independently selected
canonical AssignPair/object adapter. Its canonical branch forwards the original
Reader, exact hidden40 output and owned nonnull MethodInfo. The nonnull path
reads the registered wrapper and copies the hidden getter result16+16+8; FF and
a null wrapper default all40 bytes. Closed callback/MethodInfo selection remains
conditional, with no static pointer equality invented for an absent concrete
wrapper registration. Managed storage never supplies a serialized element width.
Runtime provider/cache/inflation choice and enclosing collection/owner/EOF are
unresolved. Ready coherent contexts, disjoint buffered storage and ordinary
noninterfering helper/barrier effects remain explicit conditions.
"""
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath,deserialize_slot
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.skill_root_assign_pair_sources import need,VALUE,WRAPPER


def adapter40_program(regions,entry,s,*,dispatch=False,null=False,create=True):
    need('literal-adapter-switches',True,all(type(x)is bool for x in(dispatch,null,create)))
    g=BytesPath(regions,entry)
    if dispatch:
        g.take('48895c2410','48896c2418','4889742420','66894c2408','57','4883ec20',
            '488b0a','498be9','498bf0','488bda');g.call(s['prepare'])
        g.take('488b03','4c8b9090010000','488bb898010000')
        need('actual-compared-canonical-adapter',s['adapter'],g.relative('488d05'))
        g.take('4c3bd0');g.branch('0f85',False);ready=flag(g);g.branch('0f84',False)
    else:
        g.take('48896c2418','4889742420','57','4883ec20');ready=flag(g)
        g.take('498bf9','498be8','488bf2');g.branch('0f84',False)
    g.take('488bce','c64424'+('30'if dispatch else'38')+'00');g.call(s['peek'])
    g.take('84c0');g.branch('0f85',null)
    type_cell=None
    if null:
        g.take('488d5424'+('30'if dispatch else'38'),'488bce');g.call(s['header'])
        g.take('0f57c0','33c0','0f114500','0f114510','48894520');g.jump('e9')
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
        createWrapper=None if null else create,typeClassCell=type_cell,managedOutputBytes=40,
        ffDefaultOutputBytes=40 if null else 0,wireBytes=1 if null else None,
        nonnullContextSlot=3,wrapperTypeSlot=10,activatorContextSlot=11,
        nonnullArguments=dict(rcx='same Reader',rdx='same hidden40 output',r8='created or zero wrapper',r9='owned closed nonnull context'),
        rcxSelectorUsed=False if dispatch else None,entryRspRestored=True,normalReturn=True)


def nonnull40_program(regions,entry,s,*,wrapper_null=False):
    need('literal-wrapper-null',True,type(wrapper_null)is bool)
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','4c89442418','57','4883ec50');ready=flag(g)
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
        g.take('488bce','0f1008','0f105010','f20f104020','0f110e','0f115610','f20f114620')
        g.call(s['barrier'])
    g.take('488b5c2460','488b742468','4883c450','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,providerClassCell=provider,
        returnedWrapperNull=wrapper_null,outputBytes=40,defaultOutputBytes=40 if wrapper_null else 0,
        wrapperProviderContextSlot=4,conversionInterfaceContextSlot=8,
        wrapperOutputLocalFromFrame=112,conversionOutputLocalFromFrame=32,
        hiddenConversionArguments=dict(rcx='local40',r8='exact owned conversion interface',r9='returned wrapper'),
        copiedChunkBytes=[]if wrapper_null else[16,16,8],sameReaderAndOutput=True,
        entryRspRestored=True,normalReturn=True)


def conversion40_program(regions,entry,prepare,*,ordinal):
    need('bounded-owned-interface-ordinal',True,type(ordinal)is int and 0<=ordinal<=16)
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','48897c2418','4156','4883ec50','498b39','488bf1','488bcf','4d8bf1','498bd8')
    g.call(prepare);g.take('440fb78730010000','33c0','66413bc0');g.branch('73',False,1)
    g.take('488b97b0000000')
    for index in range(ordinal+1):
        g.take('0fb7c8','4803c9','48391cca');g.branch('74',index==ordinal,1)
        if index<ordinal:g.take('66ffc0','66413bc0');g.branch('72',True,1)
    g.take('0fb7c8','4803c9','486344ca08','4883c014','48c1e004','4803c7',
        '4c8b08','488d4c2420','4c8b4008','498bd6','41ffd1',
        '488b5c2460','488b7c2470','0f1000','0f104810','0f1106','f20f104020',
        '488bc6','0f114e10','f20f114620','488b742468','4883c450','415e','c3')
    return dict(selectedBytes=g.seen,interfaceOrdinal=ordinal,methodSlot=0,
        getterArguments=dict(rcx='local40',rdx='same wrapper',r8='exact interface GetValue MethodInfo'),
        getterReturnsSameOutputPointer=True,copiedChunkBytes=[16,16,8],outputBytes=40,
        returnValue='same incoming hidden40 output address',normalReturn=True,entryRspRestored=True,
        fallbackInterfaceResolverAdmitted=False)


def derive(image,pins,child=None):
    """Fresh canonical/context and actual selected list-dispatch composition."""
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack import pointer_param as pointer,buff_ptr_sources,primitive_param,event_args_paths
    from scripts.game_data.memorypack import pooled_global_buff_id_sources as providers
    from scripts.game_data.memorypack.skill_shared_sequence_sources import selected_inputs,_selected_wrapper
    from scripts.game_data.memorypack.skill_root_assign_pair_sources import derive as child_source
    from scripts.game_data.memorypack.skill_root_value_dispatch import provider_inline_cast_program
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context
    from scripts.game_data.memorypack import scalar_param_native as scalar
    selected_inputs(pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);ge=GenericEntries(image)
    child=child_source(image,pins)if child is None else child
    need('same-child-pins',pins,child['nativeInputs']);need('exact-nominal-managed-value',(VALUE,WRAPPER,40),
        (child['typeName'],child['wrapperName'],child['layout']['managedBytes']))
    wrapper=_selected_wrapper(image,WRAPPER);pair=child['registeredPair']
    pointer.registered_pair(image,pair,wrapper,label='assignPairTransfer.registered')
    image.check_windows(child['sourceWindows'],label='assignPairTransfer.child')
    face,=pair['composition']['interfaces'];need('same-interface-wrapper',wrapper.type_definition,face['wrapperDefinition'])
    getter=md.methods[face['getValueMethodIndex']]
    scalar.owned_method_abi(image,ctx,getter.index,wrapper.type_definition,(VALUE,17,False),[],'assignPairTransfer.getter')
    need('named-getter','GetValue',md.string(getter.name_index))
    pointer.leaf(image,image.method_pointer_va(getter),['0F104210','488BC1','0F104A20','0F1101','F20F104230','0F114910','F20F114120','C3'])
    td=md.types[wrapper.type_definition];section=md.sections['interfaceOffsets'];at=section.offset+td.interface_offsets_start*8
    ordinal=list(struct.iter_unpack('<ii',md.buf[at:at+td.interface_offsets_count*8])).index((face['interfaceTypeIndex'],face['interfaceOffset']))
    context,context_proof=buff_ptr_sources._adapter_context(image,ge)
    registrations={};sources={};s={}
    for role,name in(('adapter','Deserialize'),('nonnull','DeserializeNotNull')):
        method=buff_ptr_sources._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2',name)
        registration=ge.resolve(method.index,[VALUE,'object'],[])
        registrations[role]=registration;s[role]=registration['pointer'];sources[role]=pointer.owned(image,s[role])
    list_td=ctx.index.types['MemoryPack.Formatters.ListFormatter`1']
    lm,=[m for m in md.methods_for(list_td)if md.string(m.name_index)=='Deserialize']
    registrations['list']=ge.resolve(lm.index,[VALUE],[]);sources['list']=pointer.owned(image,registrations['list']['pointer'])
    def call(body,offset):
        row,=[r for r in body['rows']if int(r['va'],16)==body['pointer']+offset]
        raw=bytes.fromhex(row['bytes']);need('exact-owned-E8',(5,232),(len(raw),raw[0]));return control_transfer(row)['target']
    s.update({name:call(sources['adapter'],offset)for name,offset in
        dict(peek=45,typeHandle=103,creationTest=126,activate=153).items()})
    need('same-canonical-nonnull',s['nonnull'],call(sources['adapter'],182))
    ff=BytesPath(sources['adapter']['regions'],s['adapter']+52).relative('0f85')
    s['header']=BytesPath(sources['adapter']['regions'],ff+8).relative('e8')
    s.update({name:call(sources['nonnull'],offset)for name,offset in
        dict(resolve=66,wrapperProvider=82,wrapperInvoke=112,indexed=152,conversion=168,barrier=200).items()})
    need('same-context-resolver',s['resolve'],call(sources['nonnull'],135))
    s['dispatch']=call(sources['list'],440);s['provider']=call(sources['list'],356)
    for role in('dispatch','provider','conversion','wrapperInvoke','peek','header'):sources[role]=pointer.owned(image,s[role])
    s['prepare']=call(sources['dispatch'],37)
    need('same-interface-prepare',s['prepare'],call(sources['conversion'],36))
    paths={role:[adapter40_program(sources[role]['regions'],s[role],s,dispatch=role=='dispatch',**path)
        for path in({},{'create':False},{'null':True})]for role in('adapter','dispatch')}
    paths['nonnull']=[nonnull40_program(sources['nonnull']['regions'],s['nonnull'],s,wrapper_null=null)for null in(False,True)]
    paths['conversion']=conversion40_program(sources['conversion']['regions'],s['conversion'],s['prepare'],ordinal=ordinal)
    list_context=ContextSymbols(image).context(list_td.index)
    typed_list=validate_list_formatter_base_context(image,list_context,ge,fail=need)
    ps={name:call(sources['provider'],offset)for name,offset in dict(typeHandle=52,backend=79,indexed=96,assignable=116).items()}
    need('same-TypeFromHandle',s['typeHandle'],ps['typeHandle']);need('same-indexed-context',s['indexed'],ps['indexed'])
    provider=provider_inline_cast_program(sources['provider']['regions'],s['provider'],ps)
    need('same-type-static-cell',provider['typeClassCell'],paths['adapter'][0]['typeClassCell'])
    need('same-provider-static-cell',provider['providerClassCell'],paths['nonnull'][0]['providerClassCell'])
    need('named-TypeFromHandle',base+pair['registration']['helperMethods']['typeFromHandle'][3],s['typeHandle'])
    sources['backend']=pointer.owned(image,ps['backend'])
    tails=[control_transfer(r)['target']for r in sources['backend']['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe9']
    need('single-backend-tail',1,len(tails));backend=providers.backend_bridge(sources['backend']['regions'],ps['backend'],tails[0])
    invocation=deserialize_slot(sources['wrapperInvoke']['regions'],s['wrapperInvoke'],prepare=s['prepare'],
        callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]))
    offsets=scalar.reader_offsets(image,'assignPairTransfer')
    peek=event_args_paths.peek(sources['peek']['regions'],s['peek'],offsets)
    header=vector_recorder(image)(s['header']-base);primitive_param.object_header_source(image,header,offsets)
    return json.loads(json.dumps(dict(schema='endfield.skill-root-assign-pair-transfer.v1',nativeInputs=pins,
        status='proved-selected-value40-transfer',typeName=VALUE,managedBytes=40,wireBytes=None,
        registrations=registrations,adapterContext=context,adapterContextProof=context_proof,
        listContext=list_context,listContextProof=typed_list,interfaceOrdinal=ordinal,paths=paths,
        providerProgram=provider,backendProgram=backend,wrapperInvocation=invocation,peek=peek,header=header,
        symbolRvas={k:v-base for k,v in s.items()},sourceWindows={k:v['windows']for k,v in sources.items()},
        callbackBinding=dict(actualDispatcherComparedAdapterRva=s['adapter']-base,
            exactClosedWrapperPointerEqualityInferred=False,
            condition='Actual slot5 and coherent exact closed AssignPair/wrapper MethodInfo select the independently proved canonical program; no concrete-wrapper pointer equality is inferred.'),
        runtimeSelectionObserved=False,positiveCollectionAdmitted=False,
        evidenceBoundary=dict(exact='Selected nominal AssignPair canonical value40 adapter and actual compared dispatcher, FF/default zero40, registered wrapper read, typed hidden getter conversion and full selected normal returns.',
            conditional=__doc__,structuralOnly='Stored blackboard assignment value.',
            unresolved=['enclosing count/loop/Add composition','runtime selection','whole owner/physical EOF']))))

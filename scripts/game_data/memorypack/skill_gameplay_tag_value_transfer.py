"""GameplayTag canonical managed4 callback, distinct from raw unmanaged4.

The actual List dispatcher compares its selected slot5 to the unique nominal
Tag/object canonical adapter. It reads the exact generated MC1 wrapper and
returns its tagId bits through owned interface slot0/GetValue. Canonical FF or
a null wrapper writes zero4. The separate Query bulk-array raw4 source is never
used as this callback. Concrete wrapper inflation/slot selection remains a
condition; no absent exact-wrapper registration is assigned a canonical pointer.
Normal compatible typed helpers, coherent contexts and disjoint buffered/frame
storage remain conditions. Counts/Add, runtime meaning and owner/EOF are open.
"""
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath,deserialize_slot
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.skill_gameplay_tag_value_sources import need,VALUE,WRAPPER


def adapter4_program(regions,entry,s,*,dispatch=False,null=False,create=True):
    need('literal-adapter-switches',True,all(type(v)is bool for v in(dispatch,null,create)))
    g=BytesPath(regions,entry)
    if dispatch:
        g.take('48895c2408','4889742410','48897c2418','4156','4883ec20','488b0a','4d8bf1','498bf0','488bda')
        g.call(s['prepare']);g.take('488b3b')
        need('actual-compared-nominal-adapter',s['adapter'],g.relative('488d0d'))
        g.take('488b8790010000','488bbf98010000','483bc1');g.branch('0f85',False)
        ready=flag(g);g.branch('0f84',False)
    else:
        g.take('4889742410','48897c2418','4156','4883ec20');ready=flag(g)
        g.take('498bf9','4d8bf0','488bf2');g.branch('0f84',False)
    g.take('488b4720','488bce','488b90c0000000','488b12');g.call(s['readNull']);g.take('84c0');g.branch('0f85',null)
    cell=None
    if null:g.take('33c0','418906');g.jump('e9')
    else:
        if not dispatch:g.take('48895c2430')
        g.take('488b4720');cell=g.relative('488b0d')
        g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('74',False,1)
        g.take('33d2','488bcb');g.call(s['typeHandle'])
        if not dispatch:g.take('488b5c2430')
        g.take('4885c0');g.branch('74',False,1)
        g.take('33d2','488bc8');g.call(s['isAbstract']);g.take('84c0');g.branch('75',not create,1)
        if create:g.take('488b4720','488b88c0000000','488b4958');g.call(s['activate'])
        else:g.take('33c0');g.jump('eb',1)
        g.take('488b4f20','4c8bc0','498bd6','4c8b89c0000000','488bce','4d8b4918');g.call(s['nonnull'])
    if dispatch:g.take('488b5c2430')
    g.take('488b742438','488b7c2440','4883c420','415e','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,dispatch=dispatch,null=null,
        create=None if null else create,typeClassCell=cell,managedOutputBytes=4,defaultZeroBytes=4 if null else 0,
        sameReaderAndOutput=True,normalReturn=True,entryRspRestored=True)


def nonnull4_program(regions,entry,s,*,null=False):
    need('literal-null-wrapper-switch',True,type(null)is bool)
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','4c89442418','57','4883ec20');ready=flag(g)
    g.take('498bf9','488bf2','488bd9');g.branch('0f84',False)
    cell=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
    g.take('488b4f20');g.call(s['resolve']);g.take('488b88c0000000','488b4920');g.call(s['wrapperProvider'])
    g.take('4885c0');g.branch('74',False,1)
    g.take('b905000000','4c8d4c2440','4c8bc3','488bd0');g.call(s['wrapperInvoke'])
    g.take('488b5c2440','4885db');g.branch('74',null,1)
    if null:g.take('33c0');g.jump('eb',1)
    else:
        g.take('488b4f20');g.call(s['resolve']);g.take('ba08000000','488b88c0000000');g.call(s['indexed'])
        g.take('488bd0','33c9','4c8bc3');g.call(s['conversion'])
    g.take('488b5c2430','8906','488b742438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,providerClassCell=cell,returnedWrapperNull=null,
        wrapperProviderContextSlot=4,conversionInterfaceContextSlot=8,conversionSelector=0,
        managedOutputBytes=4,defaultZeroBytes=4 if null else 0,unchangedGetterEaxStored=True,
        sameReaderAndOutput=True,normalReturn=True,entryRspRestored=True)


def conversion4_program(regions,entry,prepare,*,ordinal):
    need('bounded-owned-interface-ordinal',True,type(ordinal)is int and 0<=ordinal<=16)
    g=BytesPath(regions,entry)
    g.take('48895c2408','48896c2410','4889742418','57','4883ec20','498b38','498bf0','0fb7e9','488bda','488bcf')
    g.call(prepare);g.take('440fb78730010000','33c0','66413bc0');g.branch('73',False,1)
    g.take('488b97b0000000')
    for i in range(ordinal+1):
        g.take('0fb7c8','4803c9','48391cca');g.branch('74',i==ordinal,1)
        if i<ordinal:g.take('66ffc0','66413bc0');g.branch('72',True,1)
    g.take('0fb7d0','488b87b0000000','4803d2','8b44d008','03c5','4898','4883c014','48c1e004','4803c7',
        '4c8b00','488bce','488b5008','488b5c2430','488b6c2438','488b742440','4883c420','5f','49ffe0')
    return dict(selectedBytes=g.seen,interfaceOrdinal=ordinal,selector='incoming UInt16 CX; caller zero',
        getValueMethodSlot=0,receiver='incoming R8 wrapper forwarded RCX',
        getterMethodInfo='matching slot MethodInfo RDX',unchangedGetterEaxReturned=True,
        entryRspRestored=True,normalReturnViaGetterTail=True)


def derive(image,pins,child=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack import pointer_param as pointer,buff_ptr_sources,event_args_paths,primitive_param
    from scripts.game_data.memorypack import scalar_param_native as scalar,pooled_global_buff_id_sources as helpers
    from scripts.game_data.memorypack.skill_gameplay_tag_value_sources import derive as child_source
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _selected_wrapper
    from scripts.game_data.memorypack.skill_root_value_dispatch import provider_inline_cast_program
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image)
    child=child_source(image,pins)if child is None else child
    need('same-child-native',pins,child['nativeInputs']);need('exact-child-value4',(VALUE,WRAPPER,4),
        (child['typeName'],child['wrapperName'],child['layout']['managedBytes']))
    wrapper=_selected_wrapper(image,WRAPPER);pair=child['registeredPair'];pointer.registered_pair(image,pair,wrapper,label='tagValueTransfer.pair')
    face,=pair['composition']['interfaces'];getter=md.methods[face['getValueMethodIndex']]
    need('own-nominal-interface',wrapper.type_definition,face['wrapperDefinition'])
    scalar.owned_method_abi(image,ctx,getter.index,wrapper.type_definition,(VALUE,17,False),[],'tagValueTransfer.getter')
    pointer.leaf(image,image.method_pointer_va(getter),['8B4110','C3'])
    td=md.types[wrapper.type_definition];section=md.sections['interfaceOffsets'];at=section.offset+td.interface_offsets_start*8
    ordinal=list(struct.iter_unpack('<ii',md.buf[at:at+td.interface_offsets_count*8])).index((face['interfaceTypeIndex'],face['interfaceOffset']))
    context,context_proof=buff_ptr_sources._adapter_context(image,ge);registrations={};sources={};s={}
    for role,name in(('adapter','Deserialize'),('nonnull','DeserializeNotNull'),('readNull','ReadIsNull')):
        method=buff_ptr_sources._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2',name)
        registrations[role]=ge.resolve(method.index,[VALUE,'object'],[]);s[role]=registrations[role]['pointer'];sources[role]=pointer.owned(image,s[role])
    list_td=ctx.index.types['MemoryPack.Formatters.ListFormatter`1']
    lm,=[m for m in md.methods_for(list_td)if md.string(m.name_index)=='Deserialize']
    registrations['list']=ge.resolve(lm.index,[VALUE],[]);sources['list']=pointer.owned(image,registrations['list']['pointer'])
    def call(body,offset):
        rows=[r for r in body['rows']if int(r['va'],16)==body['pointer']+offset];need('one-source-call',1,len(rows))
        raw=bytes.fromhex(rows[0]['bytes']);need('exact-owned-E8',(5,232),(len(raw),raw[0]));return control_transfer(rows[0])['target']
    for name,off in dict(readNull=55,typeHandle=109,isAbstract=129,activate=153,nonnull=182).items():
        target=call(sources['adapter'],off)
        if name in s:need('same-canonical-method-context:'+name,s[name],target)
        s[name]=target
    s.update({name:call(sources['nonnull'],off)for name,off in dict(resolve=66,wrapperProvider=82,wrapperInvoke=108,indexed=144,conversion=157).items()})
    need('same-context-resolver',s['resolve'],call(sources['nonnull'],127))
    s['provider']=call(sources['list'],338);s['dispatch']=call(sources['list'],455)
    for role in('provider','dispatch','conversion','wrapperInvoke'):sources[role]=pointer.owned(image,s[role])
    s['prepare']=call(sources['dispatch'],33);need('same-conversion-prepare',s['prepare'],call(sources['conversion'],35))
    s['peek']=call(sources['readNull'],14);ff=BytesPath(sources['readNull']['regions'],s['readNull']+21).relative('0f85')
    s['header']=BytesPath(sources['readNull']['regions'],ff+8).relative('e8')
    paths={role:[adapter4_program(sources[role]['regions'],s[role],s,dispatch=role=='dispatch',**path)
        for path in({},{'create':False},{'null':True})]for role in('adapter','dispatch')}
    paths['nonnull']=[nonnull4_program(sources['nonnull']['regions'],s['nonnull'],s,null=n)for n in(False,True)]
    paths['conversion']=conversion4_program(sources['conversion']['regions'],s['conversion'],s['prepare'],ordinal=ordinal)
    paths['readNull']=[helpers.read_null_program(sources['readNull']['regions'],s['readNull'],s,null=n)for n in(False,True)]
    ps={name:call(sources['provider'],off)for name,off in dict(typeHandle=52,backend=79,indexed=96,assignable=116).items()}
    for name in('typeHandle','indexed'):need('same-provider-helper:'+name,s[name],ps[name])
    provider=provider_inline_cast_program(sources['provider']['regions'],s['provider'],ps)
    need('same-Type-static-cell',provider['typeClassCell'],paths['adapter'][0]['typeClassCell'])
    need('same-provider-static-cell',provider['providerClassCell'],paths['nonnull'][0]['providerClassCell'])
    need('named-TypeFromHandle',base+pair['registration']['helperMethods']['typeFromHandle'][3],s['typeHandle'])
    sources['backend']=pointer.owned(image,ps['backend']);tails=[control_transfer(r)['target']for r in sources['backend']['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe9']
    need('one-backend-tail',1,len(tails));backend=helpers.backend_bridge(sources['backend']['regions'],ps['backend'],tails[0])
    invocation=deserialize_slot(sources['wrapperInvoke']['regions'],s['wrapperInvoke'],prepare=s['prepare'],
        callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]))
    for role in('peek','header'):sources[role]=pointer.owned(image,s[role])
    offsets=scalar.reader_offsets(image,'tagValueTransfer');peek=event_args_paths.peek(sources['peek']['regions'],s['peek'],offsets)
    header=vector_recorder(image)(s['header']-base);primitive_param.object_header_source(image,header,offsets)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-gameplay-tag-value-transfer.v1',nativeInputs=pins,
        status='proved-selected-value4-transfer',typeName=VALUE,managedBytes=4,wireBytes=None,
        registrations=registrations,adapterContext=context,adapterContextProof=context_proof,
        interfaceOrdinal=ordinal,paths=paths,providerProgram=provider,backendProgram=backend,
        wrapperInvocation=invocation,peek=peek,header=header,symbolRvas={k:v-base for k,v in s.items()},
        sourceWindows={k:v['windows']for k,v in sources.items()},callbackBinding=dict(
            actualDispatcherComparedAdapterRva=s['adapter']-base,exactClosedWrapperPointerEqualityInferred=False,condition=__doc__),
        positiveCollectionAdmitted=False,rawUnmanagedTagGrammarUsed=False,
        evidenceBoundary=dict(exact='Nominal generated GameplayTag canonical managed4 adapter/default/nonnull/GetValue conversion and actual compared list dispatcher, complete returns and provider/header/wrapper forwarding.',
            conditional=__doc__,structuralOnly='Stored generated tag record.',unresolved=['list count/Add and actual parent','runtime meaning/selection','whole owner/EOF']))))

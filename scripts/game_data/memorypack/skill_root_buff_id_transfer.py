"""Exact selected BuffId value8 adapter and actual list callback transfers.

The closed canonical BuffId/object adapter, its actual compared dispatcher,
owned nonnull context, nominal wrapper and interface getter are separately
selected. FF/default returns zero8 and positive conversion returns the complete
getter QWORD unchanged in RAX. Reusing exact managed8 byte algorithms supplies
no GlobalBuffId or Param identity and no wire-width inference. Concrete-wrapper
inflation has no closed registration row; callback/context selection remains
conditional and no static pointer equality is invented. Ready coherent typed
contexts, disjoint buffered storage and compatible normal helper effects are
conditions. Collection count/Add and enclosing owner/EOF remain independent.
"""
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath,deserialize_slot
from scripts.game_data.memorypack.skill_root_buff_id_sources import need,VALUE,WRAPPER
from scripts.game_data.memorypack import pooled_global_buff_id_sources as programs
from scripts.game_data.memorypack.pooled_string_list_sources import flag


def adapter8_program(regions,entry,s,*,dispatch=False,null=False,create=True):
    need('literal-adapter-paths',True,all(type(v)is bool for v in(dispatch,null,create)))
    g=BytesPath(regions,entry)
    if dispatch:
        g.take('48895c2408','4889742410','48897c2418','4156','4883ec20','488b0a','4d8bf1','498bf0','488bda')
        g.call(s['prepare']);g.take('488b3b')
        need('exact-compared-canonical-adapter',s['adapter'],g.relative('488d0d'))
        g.take('488b8790010000','488bbf98010000','483bc1');g.branch('0f85',False)
        ready=flag(g);g.branch('0f84',False)
    else:
        g.take('4889742410','48897c2418','4156','4883ec20');ready=flag(g)
        g.take('498bf9','4d8bf0','488bf2');g.branch('0f84',False)
    g.take('488b4720','488bce','488b90c0000000','488b12');g.call(s['readNull'])
    g.take('84c0');g.branch('0f85',null)
    type_cell=None
    if null:g.take('33c0','498906');g.jump('e9')
    else:
        if not dispatch:g.take('48895c2430')
        g.take('488b4720');type_cell=g.relative('488b0d')
        g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('0f84',False)
        g.take('33d2','488bcb');g.call(s['typeHandle'])
        if not dispatch:g.take('488b5c2430')
        g.take('4885c0');g.branch('74',False,1)
        g.take('b944000000','488bd0');g.call(s['creationTest']);g.take('a980000000');g.branch('77',not create,1)
        if create:g.take('488b4720','488b88c0000000','488b4958');g.call(s['activate'])
        else:g.take('33c0');g.jump('eb',1)
        g.take('488b4f20','4c8bc0','498bd6','4c8b89c0000000','488bce','4d8b4918');g.call(s['nonnull'])
    if dispatch:g.take('488b5c2430')
    g.take('488b742438','488b7c2440','4883c420','415e','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,dispatch=dispatch,null=null,
        createWrapper=None if null else create,typeClassCell=type_cell,outputBytes=8,
        sameIncomingReaderAndOutput=True,nonnullContextSlot=3,wrapperTypeSlot=10,
        activatorContextSlot=11,normalReturn=True,entryRspRestored=True)


def nonnull8_program(regions,entry,s,*,null=False):
    need('literal-nonnull-path',True,type(null)is bool)
    return programs.nonnull_program(regions,entry,s,null=null)


def provider_program(regions,entry,s):
    """Actual list provider's complete initialized nonnull backend/cast path."""
    g=BytesPath(regions,entry)
    g.take('48895c2410','57','4883ec20','4883793800','488bf9');g.branch('0f84',False)
    type_cell=g.relative('488b0d');g.take('488b5f38','83b9e000000000','488b1b');g.branch('0f84',False)
    g.take('33d2','488bcb');g.call(s['typeHandle'])
    provider_cell=g.relative('488b0d');g.take('488bd8','83b9e000000000');g.branch('0f84',False)
    g.take('488bcb');g.call(s['backend'])
    g.take('488b4f38','ba01000000','488bd8');g.call(s['indexed'])
    g.take('4885db');g.branch('74',False,1)
    g.take('488b0b','488bd0');g.call(s['assignable']);g.take('84c0');g.branch('74',False,1)
    g.take('488bc3','488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,typeClassCell=type_cell,providerClassCell=provider_cell,
        typeContextSlot=0,resultTypeContextSlot=1,normalReturn=True,
        output='same nonnull backend full reference after successful assignability predicate')


def derive(image,pins,child=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack import pointer_param as pointer,buff_ptr_sources,event_args_paths,primitive_param
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.skill_root_buff_id_sources import derive as child_source
    from scripts.game_data.memorypack.skill_shared_sequence_sources import selected_inputs,_selected_wrapper
    from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    _publication_gate(image,pins);selected_inputs(pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    md=image.metadata;ge=GenericEntries(image);child=child_source(image,pins)if child is None else child
    need('same-child-inputs',pins,child['nativeInputs'])
    need('exact-child-nominal',(VALUE,WRAPPER,8),(child['typeName'],child['wrapperName'],child['layout']['managedBytes']))
    image.check_windows(child['sourceWindows'],label='buffIdTransfer.child')
    wrapper=_selected_wrapper(image,WRAPPER);pair=child['registeredPair']
    pointer.registered_pair(image,pair,wrapper,label='buffIdTransfer.registration')
    face,=pair['composition']['interfaces'];need('same-wrapper-definition',wrapper.type_definition,face['wrapperDefinition'])
    getter=md.methods[face['getValueMethodIndex']]
    scalar.owned_method_abi(image,ctx,getter.index,wrapper.type_definition,(VALUE,17,False),[],'buffIdTransfer.getter')
    need('named-GetValue','GetValue',md.string(getter.name_index))
    pointer.leaf(image,image.method_pointer_va(getter),['488B4110','C3'])
    td=md.types[wrapper.type_definition];section=md.sections['interfaceOffsets'];at=section.offset+td.interface_offsets_start*8
    ordinal=list(struct.iter_unpack('<ii',md.buf[at:at+td.interface_offsets_count*8])).index((face['interfaceTypeIndex'],face['interfaceOffset']))
    context,context_proof=buff_ptr_sources._adapter_context(image,ge)
    registrations={};sources={};s={}
    for role,name in(('adapter','Deserialize'),('nonnull','DeserializeNotNull'),('readNull','ReadIsNull')):
        method=buff_ptr_sources._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2',name)
        registrations[role]=ge.resolve(method.index,[VALUE,'object'],[])
        s[role]=registrations[role]['pointer'];sources[role]=pointer.owned(image,s[role])
    list_td=ctx.index.types['MemoryPack.Formatters.ListFormatter`1']
    method,=[m for m in md.methods_for(list_td)if md.string(m.name_index)=='Deserialize']
    registrations['list']=ge.resolve(method.index,[VALUE],[]);sources['list']=pointer.owned(image,registrations['list']['pointer'])
    def call(body,offset):
        rows=[r for r in body['rows']if int(r['va'],16)==body['pointer']+offset]
        need('one-owned-call',1,len(rows));row=rows[0];raw=bytes.fromhex(row['bytes'])
        need('exact-owned-E8',(5,232),(len(raw),raw[0]));return control_transfer(row)['target']
    for name,off in dict(readNull=55,typeHandle=113,creationTest=136,activate=163,nonnull=192).items():
        target=call(sources['adapter'],off)
        if name in s:need('same-canonical-context-target:'+name,s[name],target)
        s[name]=target
    s.update({name:call(sources['nonnull'],off)for name,off in
        dict(resolve=66,wrapperProvider=82,wrapperInvoke=112,indexed=148,conversion=159,barrier=170).items()})
    need('same-context-resolver',s['resolve'],call(sources['nonnull'],131))
    s['provider']=call(sources['list'],260);s['dispatch']=call(sources['list'],329)
    for role in('provider','dispatch','conversion','wrapperInvoke'):sources[role]=pointer.owned(image,s[role])
    s['prepare']=call(sources['dispatch'],33);need('same-interface-prepare',s['prepare'],call(sources['conversion'],27))
    s['peek']=call(sources['readNull'],14)
    read_null_ff=BytesPath(sources['readNull']['regions'],s['readNull']+21).relative('0f85')
    s['header']=BytesPath(sources['readNull']['regions'],read_null_ff+8).relative('e8')
    for role in('peek','header'):sources[role]=pointer.owned(image,s[role])
    paths={role:[adapter8_program(sources[role]['regions'],s[role],s,dispatch=role=='dispatch',**path)
        for path in({},{'create':False},{'null':True})]for role in('adapter','dispatch')}
    paths['nonnull']=[nonnull8_program(sources['nonnull']['regions'],s['nonnull'],s,null=n)for n in(False,True)]
    paths['conversion']=programs.conversion_program(sources['conversion']['regions'],s['conversion'],s,ordinal=ordinal)
    paths['readNull']=[programs.read_null_program(sources['readNull']['regions'],s['readNull'],s,null=n)for n in(False,True)]
    ps={name:call(sources['provider'],off)for name,off in dict(typeHandle=56,backend=87,indexed=104,assignable=120).items()}
    need('same-provider-TypeFromHandle',s['typeHandle'],ps['typeHandle']);need('same-indexed-context',s['indexed'],ps['indexed'])
    provider=provider_program(sources['provider']['regions'],s['provider'],ps)
    need('same-type-static-cell',provider['typeClassCell'],paths['adapter'][0]['typeClassCell'])
    nonnull_provider_cell=BytesPath(sources['nonnull']['regions'],s['nonnull']+42).relative('488b0d')
    need('same-provider-static-cell',provider['providerClassCell'],nonnull_provider_cell)
    need('same-child-GC-barrier',child['symbolRvas']['barrier'],s['barrier']-base)
    need('named-TypeFromHandle',base+pair['registration']['helperMethods']['typeFromHandle'][3],s['typeHandle'])
    sources['backend']=pointer.owned(image,ps['backend'])
    tails=[control_transfer(r)['target']for r in sources['backend']['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe9']
    need('one-backend-tail',1,len(tails));backend=programs.backend_bridge(sources['backend']['regions'],ps['backend'],tails[0])
    invocation=deserialize_slot(sources['wrapperInvoke']['regions'],s['wrapperInvoke'],prepare=s['prepare'],
        callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]))
    list_context=ContextSymbols(image).context(list_td.index)
    list_proof=validate_list_formatter_base_context(image,list_context,ge,fail=need)
    offsets=scalar.reader_offsets(image,'buffIdTransfer');peek=event_args_paths.peek(sources['peek']['regions'],s['peek'],offsets)
    header=vector_recorder(image)(s['header']-base);primitive_param.object_header_source(image,header,offsets)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-root-buff-id-transfer.v1',nativeInputs=pins,
        status='proved-selected-value8-transfer',typeName=VALUE,managedBytes=8,wireBytes=None,
        registrations=registrations,adapterContext=context,adapterContextProof=context_proof,
        listContext=list_context,listContextProof=list_proof,interfaceOrdinal=ordinal,paths=paths,
        providerProgram=provider,backendProgram=backend,wrapperInvocation=invocation,peek=peek,header=header,
        symbolRvas={k:v-base for k,v in s.items()},sourceWindows={k:v['windows']for k,v in sources.items()},
        callbackBinding=dict(actualDispatcherComparedAdapterRva=s['adapter']-base,
            exactClosedWrapperPointerEqualityInferred=False,condition=__doc__),
        positiveCollectionAdmitted=False,runtimeSelectionObserved=False,
        evidenceBoundary=dict(exact='Exact BuffId canonical value8/FF/nonnull conversion, actual list dispatcher comparison, owned wrapper/getter and full normal returns.',
            conditional=__doc__,structuralOnly='Stored buff identifier.',
            unresolved=['positive count/loop/Add and parent framing','runtime selection','whole owner/physical EOF']))))

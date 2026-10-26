"""Exact Query hidden16 canonical callback and actual caller transfer.

The typed ReadValue request and supplied actual fixed-slot5 dispatcher own the
nominal Query value and its canonical comparison. The canonical branch reads
the selected wrapper, finds its exact registered interface/GetValue, copies
all16 returned bytes and barriers the actual reference lane8. FF and a null
wrapper default all16 bytes. No concrete-wrapper inflated callback is equated
to a canonical registration and no managed width supplies wire framing. Ready
coherent supplied contexts/callback, bounded interface search, disjoint buffered
storage and normal compatible helper effects are conditions. Parent framing,
array grammar, runtime choice and whole SkillData/EOF remain independent.
"""
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath,deserialize_slot
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.skill_root_tag_query_sources import need,VALUE,WRAPPER


def adapter16_program(regions,entry,s,*,dispatch=False,null=False,create=True):
    need('literal-adapter-paths',True,all(type(x)is bool for x in(dispatch,null,create)))
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
    g.take('84c0');g.branch('0f85',null);cell=None
    if null:
        g.take('488d5424'+('30'if dispatch else'38'),'488bce');g.call(s['header'])
        g.take('0f57c0','0f114500');g.jump('e9')
    else:
        if not dispatch:g.take('48895c2430')
        g.take('488b4720');cell=g.relative('488b0d')
        g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('0f84',False)
        g.take('33d2','488bcb');g.call(s['typeHandle'])
        if not dispatch:g.take('488b5c2430')
        g.take('4885c0');g.branch('74',False,1)
        g.take('b944000000','488bd0');g.call(s['creationTest']);g.take('a980000000');g.branch('77',not create,1)
        if create:g.take('488b4720','488b88c0000000','488b4958');g.call(s['activate'])
        else:g.take('33c0');g.jump('eb',1)
        g.take('488b4f20','4c8bc0','488bd5','4c8b89c0000000','488bce','4d8b4918');g.call(s['nonnull'])
    if dispatch:g.take('488b5c2438')
    g.take('488b6c2440','488b742448','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,dispatch=dispatch,ff=null,
        createWrapper=None if null else create,typeClassCell=cell,managedOutputBytes=16,
        defaultZeroBytes=16 if null else 0,wireBytes=1 if null else None,
        selectorRead=False if dispatch else None,nonnullContextSlot=3,wrapperTypeSlot=10,
        activatorContextSlot=11,sameIncomingReaderAndOutput=True,normalReturn=True,entryRspRestored=True)


def nonnull16_program(regions,entry,s,*,ordinal,wrapper_null=False):
    need('literal-wrapper-null',True,type(wrapper_null)is bool)
    need('bounded-owned-interface-ordinal',True,type(ordinal)is int and 0<=ordinal<=16)
    g=BytesPath(regions,entry)
    g.take('48895c2410','48896c2420','4c89442418','57','4883ec30');ready=flag(g)
    g.take('498bd9','488bea','488bf9');g.branch('0f84',False)
    provider=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
    g.take('488b4b20');g.call(s['resolve']);g.take('488b88c0000000','488b4920');g.call(s['wrapperProvider'])
    g.take('4885c0');g.branch('0f84',False)
    g.take('b905000000','4889742440','4c8d4c2450','4c8bc7','488bd0');g.call(s['wrapperInvoke'])
    g.take('488b742450','4885f6');g.branch('0f84',wrapper_null);getter=None
    if wrapper_null:
        g.take('0f57c0','0f114500');g.jump('eb',1)
    else:
        g.take('488b4b20');g.call(s['resolve']);g.take('ba08000000','488b88c0000000');g.call(s['indexed'])
        g.take('488b3e','488bd8','488bcf');g.call(s['prepare'])
        g.take('440fb78730010000','33c9','66413bc8');g.branch('73',False,1)
        g.take('488b97b0000000')
        for i in range(ordinal+1):
            g.take('0fb7c1','4803c0','48391cc2');g.branch('74',i==ordinal,1)
            if i<ordinal:g.take('66ffc1','66413bc8');g.branch('72',True,1)
        g.take('488b87b0000000','0fb7d1','4803d2','486344d008','4883c014','48c1e004','4803c7',
            '4c8b08','488d4c2420','4c8b4008','488bd6');getter=g.at;g.take('41ffd1')
        g.take('488d4d08','0f1000','0f114500');g.call(s['barrier'])
    g.take('488b742440','488b5c2448','488b6c2458','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,providerClassCell=provider,wrapperNull=wrapper_null,
        wrapperProviderContextSlot=4,conversionInterfaceContextSlot=8,interfaceOrdinal=ordinal,
        getValueMethodSlot=0,hiddenGetterCall=getter,managedOutputBytes=16,
        completeCopiedBytes=0 if wrapper_null else 16,defaultZeroBytes=16 if wrapper_null else 0,
        hiddenGetterArguments=dict(rcx='local16 output',rdx='returned wrapper',r8='owned GetValue MethodInfo'),
        referenceLaneOffset=8,sameReaderAndOutput=True,entryRspRestored=True,normalReturn=True)


def derive(image,pins,*,typed_request,dispatcher_target,child=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack import pointer_param as pointer,buff_ptr_sources,primitive_param,event_args_paths
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.skill_root_tag_query_sources import derive as child_source
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _selected_wrapper
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    _publication_gate(image,pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);ge=GenericEntries(image)
    child=child_source(image,pins)if child is None else child;need('same-child-pins',pins,child['nativeInputs'])
    need('exact-child-type-and-ABI',(VALUE,WRAPPER,16),(child['typeName'],child['wrapperName'],child['layout']['managedBytes']))
    wrapper=_selected_wrapper(image,WRAPPER);pair=child['registeredPair'];pointer.registered_pair(image,pair,wrapper,label='queryTransfer.registration')
    face,=pair['composition']['interfaces'];need('same-wrapper-definition',wrapper.type_definition,face['wrapperDefinition'])
    getter=md.methods[face['getValueMethodIndex']]
    scalar.owned_method_abi(image,ctx,getter.index,wrapper.type_definition,(VALUE,17,False),[],'queryTransfer.getter')
    pointer.leaf(image,image.method_pointer_va(getter),['0F104210','488BC1','0F1101','C3'])
    td=md.types[wrapper.type_definition];section=md.sections['interfaceOffsets'];at=section.offset+td.interface_offsets_start*8
    ordinal=list(struct.iter_unpack('<ii',md.buf[at:at+td.interface_offsets_count*8])).index((face['interfaceTypeIndex'],face['interfaceOffset']))
    typed=buff_ptr_sources._typed_context(image,typed_request,VALUE,ge)
    context,context_proof=buff_ptr_sources._adapter_context(image,ge);registrations={};sources={};s={}
    for role,name in(('adapter','Deserialize'),('nonnull','DeserializeNotNull')):
        method=buff_ptr_sources._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2',name)
        registrations[role]=ge.resolve(method.index,[VALUE,'object'],[])
        s[role]=registrations[role]['pointer'];sources[role]=pointer.owned(image,s[role])
    sources['dispatch']=pointer.owned(image,dispatcher_target);s['dispatch']=dispatcher_target
    def call(body,offset):
        rows=[r for r in body['rows']if int(r['va'],16)==body['pointer']+offset];need('one-owned-call',1,len(rows))
        raw=bytes.fromhex(rows[0]['bytes']);need('exact-E8',(5,232),(len(raw),raw[0]));return control_transfer(rows[0])['target']
    for name,off in dict(peek=45,typeHandle=103,creationTest=126,activate=153,nonnull=182).items():
        actual=call(sources['adapter'],off)
        if name in s:need('same-closed-context-target:'+name,s[name],actual)
        s[name]=actual
    ff=BytesPath(sources['adapter']['regions'],s['adapter']+52).relative('0f85')
    s['header']=BytesPath(sources['adapter']['regions'],ff+8).relative('e8')
    s.update({name:call(sources['nonnull'],off)for name,off in dict(resolve=66,wrapperProvider=82,wrapperInvoke=117,indexed=157,prepare=171,barrier=294).items()})
    need('same-context-resolver',s['resolve'],call(sources['nonnull'],140))
    need('same-dispatch-class-prepare',s['prepare'],call(sources['dispatch'],37))
    need('same-child-reference-barrier',child['symbolRvas']['barrier'],s['barrier']-base)
    need('named-TypeFromHandle',base+pair['registration']['helperMethods']['typeFromHandle'][3],s['typeHandle'])
    paths={role:[adapter16_program(sources[role]['regions'],s[role],s,dispatch=role=='dispatch',**p)
        for p in({},{'create':False},{'null':True})]for role in('adapter','dispatch')}
    paths['nonnull']=[nonnull16_program(sources['nonnull']['regions'],s['nonnull'],s,ordinal=ordinal,wrapper_null=n)for n in(False,True)]
    for role in('wrapperInvoke','peek','header'):sources[role]=pointer.owned(image,s[role])
    invocation=deserialize_slot(sources['wrapperInvoke']['regions'],s['wrapperInvoke'],prepare=s['prepare'],
        callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]))
    offsets=scalar.reader_offsets(image,'queryTransfer');peek=event_args_paths.peek(sources['peek']['regions'],s['peek'],offsets)
    header=vector_recorder(image)(s['header']-base);primitive_param.object_header_source(image,header,offsets)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-root-tag-query-transfer.v1',nativeInputs=pins,
        status='proved-selected-value16-transfer',typeName=VALUE,managedBytes=16,wireBytes=None,typedReadContext=typed,
        registrations=registrations,adapterContext=context,adapterContextProof=context_proof,
        interfaceOrdinal=ordinal,paths=paths,wrapperInvocation=invocation,peek=peek,header=header,
        dispatcherTargetRva=dispatcher_target-base,readerMethodDefinition=typed_request['methodSpec'][0],
        symbolRvas={k:v-base for k,v in s.items()},sourceWindows={k:v['windows']for k,v in sources.items()},
        callbackBinding=dict(actualDispatcherComparedAdapterRva=s['adapter']-base,
            exactClosedWrapperPointerEqualityInferred=False,condition=__doc__),
        childWireGrammarAdmitted=False,parentFieldAdmitted=False,runtimeSelectionObserved=False,
        evidenceBoundary=dict(exact='Nominal Query canonical managed16 adapter, exact actual compared dispatcher, zero16 FF/null-wrapper, complete registered GetValue/interface conversion and reference-lane8 normal return.',
            conditional=__doc__,structuralOnly='Stored tag query value.',unresolved=['actual enclosing typed parent/cursor join','independent array grammar','runtime selection','whole owner/physical EOF']))))

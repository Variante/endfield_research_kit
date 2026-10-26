"""Pull value16 canonical callback, actual list dispatcher and hidden getter.

The exact closed Pull/object canonical adapter is independently selected. The
actual List<Pull> dispatcher must compare its slot5 pointer to that entry and
execute the matched program. Selected wrapper forwarding and the owned nominal
conversion interface/GetValue copy all16 output bytes unchanged; FF and a null
wrapper zero16. The reference lane0 barrier is distinct from the Single/padding
lanes. No registered body is assigned to an absent inflated wrapper entry.
Coherent ready closed MethodInfos, matching canonical callback, normal compatible
helpers and disjoint buffered storage remain conditions. This owns no wire
child/count/action/root or runtime provider choice.
"""
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath,deserialize_slot
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.skill_root_child_bindings import need
from scripts.game_data.memorypack.skill_pull_attenuation_sources import TYPE,WRAPPER


def nonnull_program(regions,entry,s,*,null=False):
    need('pull-literal-wrapper-null',True,type(null)is bool)
    g=BytesPath(regions,entry);g.take('48895c2408','4889742410','4c89442418','57','4883ec30');ready=flag(g)
    g.take('498bf9','488bf2','488bd9');g.branch('0f84',False)
    provider=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
    g.take('488b4f20');g.call(s['resolve']);g.take('488b88c0000000','488b4920');g.call(s['wrapperProvider'])
    g.take('4885c0');g.branch('0f84',False)
    g.take('b905000000','4c8d4c2450','4c8bc3','488bd0');g.call(s['ordinaryDispatch'])
    g.take('488b5c2450','4885db');g.branch('74',null,1)
    if null:g.take('0f57c0','0f1106');g.jump('eb',1)
    else:
        g.take('488b4f20');g.call(s['resolve']);g.take('ba08000000','488b88c0000000');g.call(s['context'])
        g.take('4c8bc0','488d4c2420','4c8bcb');g.call(s['conversion'])
        g.take('488bce','0f1000','0f1106');g.call(s['barrier'])
    g.take('488b5c2440','488b742448','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,providerClassCell=provider,wrapperNull=null,
        wrapperProviderContextSlot=4,conversionInterfaceContextSlot=8,managedOutputBytes=16,
        referenceLaneOffset=0,defaultZeroBytes=16 if null else 0,unchangedGetterBytes=0 if null else 16,
        sameIncomingReaderAndOutput=True,normalReturn=True,entryRspRestored=True)


def derive(image,pins,child):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import pointer_param as pointer,buff_ptr_sources,animation_mask_sources as programs
    from scripts.game_data.memorypack import pooled_global_buff_id_sources as provider_programs,event_args_paths,primitive_param,scalar_param_native as scalar
    from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _selected_wrapper,_fast_barrier
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image)
    need('pull-transfer-own-child',(pins,TYPE,WRAPPER,16),tuple(child.get(k)for k in('nativeInputs','typeName','wrapperName'))+(child['layout']['managedBytes'],))
    wrapper=_selected_wrapper(image,WRAPPER);pair=child['registeredPair'];registration=pointer.registered_pair(image,pair,wrapper,label='pullTransfer.registration')
    face,=pair['composition']['interfaces'];need('pull-interface-owned-by-wrapper',wrapper.type_definition,face['wrapperDefinition'])
    getter=md.methods[face['getValueMethodIndex']]
    scalar.owned_method_abi(image,ctx,getter.index,wrapper.type_definition,(TYPE,17,False),[],'pullTransfer.GetValue')
    own_getter=pointer.leaf(image,image.method_pointer_va(getter),['0F104210','488BC1','0F1101','C3'])
    need('pull-identical-owned-getter',child['getter'],own_getter)
    td=md.types[wrapper.type_definition];section=md.sections['interfaceOffsets'];at=section.offset+td.interface_offsets_start*8
    ordinal=list(struct.iter_unpack('<ii',md.buf[at:at+td.interface_offsets_count*8])).index((face['interfaceTypeIndex'],face['interfaceOffset']))
    adapter_context,adapter_context_proof=buff_ptr_sources._adapter_context(image,ge);sources={};s={};registrations={}
    for role,name in(('adapter','Deserialize'),('nonnull','DeserializeNotNull'),('readNull','ReadIsNull')):
        method=buff_ptr_sources._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2',name)
        selected=ge.resolve(method.index,[TYPE,'object'],[]);registrations[role]=selected;s[role]=selected['pointer'];sources[role]=pointer.owned(image,s[role])
    list_td=ctx.index.types['MemoryPack.Formatters.ListFormatter`1'];lm,=[m for m in md.methods_for(list_td)if md.string(m.name_index)=='Deserialize']
    registrations['list']=ge.resolve(lm.index,[TYPE],[]);sources['list']=pointer.owned(image,registrations['list']['pointer'])
    def call(role,offset):return buff_ptr_sources._call(sources[role],offset)
    for role,offset in dict(readNull=54,typeHandle=108,creationTest=128,activate=152,notNull=181).items():
        target=call('adapter',offset)
        if role=='readNull':need('pull-same-registered-ReadIsNull',s[role],target)
        if role=='notNull':need('pull-same-registered-Nonnull',s['nonnull'],target)
        s[role]=target
    s.update({role:call('nonnull',offset)for role,offset in dict(resolve=66,wrapperProvider=82,ordinaryDispatch=112,context=148,conversion=164,barrier=178).items()})
    need('pull-same-context-resolver',s['resolve'],call('nonnull',131))
    need('pull-same-wrapper-reference-barrier',child['symbolRvas']['barrier'],s['barrier']-base)
    s['provider']=call('list',232);s['dispatch']=call('list',312)
    for role in('provider','dispatch','conversion','ordinaryDispatch'):sources[role]=pointer.owned(image,s[role])
    s['prepare']=call('dispatch',32);need('pull-same-conversion-prepare',s['prepare'],call('conversion',35))
    s['peek']=call('readNull',14);ff=BytesPath(sources['readNull']['regions'],s['readNull']+21).relative('0f85')
    s['header']=BytesPath(sources['readNull']['regions'],ff+8).relative('e8')
    need('pull-same-wrapper-object-header',child['symbolRvas']['header'],s['header']-base)
    paths={role:[programs.adapter_program(sources[role]['regions'],s[role],s,inline=role=='dispatch',**path)
        for path in(dict(create=True),dict(create=False),dict(null=True))]for role in('adapter','dispatch')}
    paths['nonnull']=[nonnull_program(sources['nonnull']['regions'],s['nonnull'],s,null=n)for n in(False,True)]
    paths['conversion']=programs.conversion_program(sources['conversion']['regions'],s['conversion'],s['prepare'],ordinal=ordinal)
    paths['readNull']=[provider_programs.read_null_program(sources['readNull']['regions'],s['readNull'],s,null=n)for n in(False,True)]
    ps={role:call('provider',offset)for role,offset in dict(typeHandle=52,backend=79,indexed=96,cast=107).items()}
    need('pull-same-provider-TypeFromHandle',s['typeHandle'],ps['typeHandle']);need('pull-same-provider-context-helper',s['context'],ps['indexed'])
    need('pull-named-TypeFromHandle',base+pair['registration']['helperMethods']['typeFromHandle'][3],s['typeHandle'])
    provider=provider_programs.compared_provider(sources['provider']['regions'],s['provider'],ps)
    sources['cast']=pointer.owned(image,ps['cast']);sources['backend']=pointer.owned(image,ps['backend'])
    targets={control_transfer(r)['target']for r in sources['cast']['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8'}
    need('pull-one-owned-cast-predicate',1,len(targets));predicate,=targets
    paths['cast']=[provider_programs.successful_cast(sources['cast']['regions'],ps['cast'],predicate,null=n)for n in(False,True)]
    tails={control_transfer(r)['target']for r in sources['backend']['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe9'}
    need('pull-one-owned-backend-tail',1,len(tails));tail,=tails
    backend=provider_programs.backend_bridge(sources['backend']['regions'],ps['backend'],tail)
    list_context=ContextSymbols(image).context(list_td.index)
    list_context_proof=validate_list_formatter_base_context(image,list_context,ge,fail=need)
    invocation=deserialize_slot(sources['ordinaryDispatch']['regions'],s['ordinaryDispatch'],prepare=s['prepare'],
        callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]))
    classes=[derive_typed_usage_context(image,s['provider']-base+offset,label='pullTransfer.providerClass')for offset in(20,57)]
    need('pull-exact-provider-class-owners',[(1,'System.Type'),(1,'MemoryPack.MemoryPackFormatterProvider')],[(c['tag'],c['typeName'])for c in classes])
    for role in('peek','header'):sources[role]=pointer.owned(image,s[role])
    offsets=scalar.reader_offsets(image,'pullTransfer');peek=event_args_paths.peek(sources['peek']['regions'],s['peek'],offsets)
    header=vector_recorder(image)(s['header']-base);primitive_param.object_header_source(image,header,offsets)
    barrier_windows,barrier,_=_fast_barrier(image,s['barrier']);_publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-pull-attenuation-transfer.v1',status='proved-selected-pull-value16-transfer',
        nativeInputs=pins,typeName=TYPE,wrapperName=WRAPPER,managedBytes=16,referenceLaneOffset=0,wireBytes=None,
        canonicalCallbackAdmitted=True,originalDefaultZeroBytes=16,ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        registrations=registrations,registeredPair=registration,adapterContext=adapter_context,adapterContextProof=adapter_context_proof,
        interfaceOrdinal=ordinal,listContext=list_context,listContextProof=list_context_proof,paths=paths,providerProgram=provider,
        providerClasses=classes,backendProgram=backend,wrapperInvocation=invocation,peek=peek,header=header,
        barrierWindows=barrier_windows,barrierProgram=barrier,symbolRvas={k:v-base for k,v in s.items()},
        sourceWindows={role:body['windows']for role,body in sources.items()},callbackBinding=dict(
            actualDispatcherComparedAdapterRva=s['adapter']-base,exactClosedWrapperPointerEqualityInferred=False,
            condition='Selected slot5 and coherent Pull/wrapper closed MethodInfo equal the independently proved canonical program; live callback selection is unobserved.'),
        runtimeSelectionObserved=False,positiveCollectionAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Own nominal canonical managed16 adapter and actual compared list dispatcher, FF/null-wrapper zero16, wrapper forwarding, typed interface/GetValue unchanged16 and lane0 barrier with complete normal frames.',
            conditional=__doc__,structuralOnly='Stored Pull value representation.',
            unresolved=['independent positive list count/Add source','separate wire child grammar','runtime provider/formatter choice','enclosing action/root/physical EOF']))))

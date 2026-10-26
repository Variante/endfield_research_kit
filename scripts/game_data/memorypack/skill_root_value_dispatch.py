"""Exact selected DataPair managed32 adapter and value-list transfers.

The actual list callback dispatcher compares its selected slot-five pointer to
the independently registered DataPair/object canonical adapter. Its selected
inline path reads the wrapper, finds the exact conversion interface, forwards a
hidden32 getter result and copies both chunks unchanged. FF/default output and
fresh/reused wrapper paths are independent complete selected programs. This
does not equate an inflated DataPair/wrapper callback with the canonical pointer
or turn managed32 storage into a serialized width. Coherent initialized closed
MethodInfo, selected callback equality, valid disjoint source/output/frame and
ordinary noninterfering helpers/barriers remain explicit conditions. Runtime
provider/default/override/inflation selection is unobserved.
"""
from __future__ import annotations

import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import scalar_param_native as scalar
from scripts.game_data.memorypack.pooled_string_list_sources import flag

LABEL='skillRootValueDispatch'


def need(check,expected,actual):scalar.need(LABEL,check,expected,actual)


def adapter32_program(regions,entry,s,*,dispatch=False,null=False,create=True,wrapper_null=False,ordinal):
    """DataPair canonical adapter and its actual compared inline dispatcher."""
    need('literal-path-switches',True,all(type(x)is bool for x in(dispatch,null,create,wrapper_null)))
    need('null-path-does-not-have-wrapper-result',False,null and wrapper_null)
    need('bounded-interface-ordinal',True,type(ordinal)is int and 0<=ordinal<=16)
    g=BytesPath(regions,entry)
    if dispatch:
        g.take('48895c2420','66894c2408','55','56','57','4883ec40','488b0a','498be9','498bf0','488bda')
        g.call(s['prepare']);g.take('488b03','4c8b9090010000','488bb898010000')
        need('compared-canonical-adapter',s['adapter'],g.relative('488d05'))
        g.take('4c3bd0');g.branch('0f85',False)
        metadata=flag(g);g.branch('0f84',False)
    else:
        g.take('4055','56','57','4883ec40');metadata=flag(g)
        g.take('498bf9','498be8','488bf2');g.branch('0f84',False)
    g.take('488bce','c64424'+('60'if dispatch else'68')+'00');g.call(s['peek'])
    g.take('84c0');g.branch('0f85',null)
    type_cell=provider_cell=None;getter_at=None
    if null:
        g.take('488d5424'+('60'if dispatch else'68'),'488bce');g.call(s['header'])
        g.take('0f57c0','0f114500','0f114510');g.jump('e9')
    else:
        if not dispatch:g.take('48895c2460')
        g.take('488b4720');type_cell=g.relative('488b0d')
        g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('0f84',False)
        g.take('33d2','488bcb');g.call(s['typeHandle']);g.take('4885c0');g.branch('0f84',False)
        g.take('b944000000','488bd0');g.call(s['creationTest'])
        g.take('33db','a980000000');g.branch('0f87',not create)
        if create:
            g.take('488b4720','488b88c0000000','488b4958');g.call(s['activate'])
        else:g.take('488bc3');g.jump('e9')
        ready=g.relative('381d');g.take('488b4f20','4889442468','488b91c0000000','488b7a18')
        g.branch('0f84',False);provider_cell=g.relative('488b0d')
        g.take('3999e0000000');g.branch('0f84',False)
        g.take('488b4f20');g.call(s['resolve'])
        g.take('488b88c0000000','488b4920');g.call(s['wrapperProvider'])
        g.take('4885c0');g.branch('0f84',False)
        g.take('b905000000','4c89742470','4c8d4c2468','4c8bc6','488bd0');g.call(s['wrapperInvoke'])
        g.take('4c8b742468','4d85f6');g.branch('0f84',wrapper_null)
        if wrapper_null:
            g.take('0f57c0','0f114500','0f114510');g.jump('e9')
        else:
            g.take('488b4f20');g.call(s['resolve'])
            g.take('ba08000000','488b88c0000000');g.call(s['indexed'])
            g.take('498b36','488bf8','488bce');g.call(s['prepare'])
            g.take('0fb79630010000','663bda');g.branch('73',False,1)
            g.take('488b8eb0000000')
            for i in range(ordinal+1):
                g.take('0fb7c3','4803c0','48393cc1');g.branch('74',i==ordinal,1)
                if i<ordinal:g.take('66ffc3','663bda');g.branch('72',True,1)
            g.take('488b86b0000000','0fb7cb','4803c9','486344c808','4883c014',
                '48c1e004','4803c6','4c8b08','488d4c2420','4c8b4008','498bd6')
            getter_at=g.at;g.take('41ffd1','488bcd','0f1000','0f104810','0f114500','0f114d10')
            g.call(s['barrier'])
        g.take('4c8b742470')
        if not dispatch:g.take('488b5c2460')
    if dispatch:g.take('488b5c2478')
    g.take('4883c440','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,dispatch=dispatch,metadataReadyFlag=metadata,
        ff=null,createWrapperBeforeRead=None if null else create,
        returnedWrapperNull=None if null else wrapper_null,outputBytes=32,
        defaultOutputBytes=32 if null or wrapper_null else 0,
        typeClassCell=type_cell,providerClassCell=provider_cell,
        wrapperProviderContextSlot=4,conversionInterfaceContextSlot=8,
        conversionInterfaceOrdinal=ordinal,conversionMethodSlot=0,
        hiddenGetterCall=getter_at,hiddenGetterArguments=dict(rcx='local output32',rdx='returned wrapper',r8='selected GetValue MethodInfo'),
        getterReturnsSameOutputPointer=True,copiedCompleteGetterBytes=0 if null or wrapper_null else 32,
        sameIncomingReaderAndOutput=True,entryRspRestored=True,normalReturn=True,
        rcxSelectorUsed=False if dispatch else None,wireBytes=1 if null else None)


def provider_inline_cast_program(regions,entry,s):
    """Actual list provider's independently checked inline successful cast."""
    g=BytesPath(regions,entry)
    g.take('48895c2410','57','4883ec20','4883793800','488bf9');g.branch('74',False,1)
    type_cell=g.relative('488b0d');g.take('488b5f38','83b9e000000000','488b1b')
    g.branch('0f84',False);g.take('33d2','488bcb');g.call(s['typeHandle'])
    provider_cell=g.relative('488b0d');g.take('488bd8','83b9e000000000');g.branch('74',False,1)
    g.take('488bcb');g.call(s['backend'])
    g.take('488b4f38','ba01000000','488bd8');g.call(s['indexed'])
    g.take('4885db');g.branch('0f84',False)
    g.take('488b0b','488bd0');g.call(s['assignable'])
    g.take('84c0');g.branch('0f84',False)
    g.take('488bc3','488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,typeClassCell=type_cell,providerClassCell=provider_cell,
        typeContextSlot=0,resultTypeContextSlot=1,
        output='unchanged compatible backend formatter reference',normalReturn=True)


def validate_data_pair_wrapper_component(image,pins,component,*,ctx):
    """Recheck the nominal owner, registration and hidden32 getter on this image."""
    from scripts.game_data.memorypack import pointer_param as pointer
    from scripts.game_data.memorypack.skill_root_value_sources import DATA_PAIR,DATA_PAIR_WRAPPER,_selected_wrapper
    need('same-wrapper-native-inputs',pins,component['nativeInputs'])
    need('exact-wrapper-component',(DATA_PAIR,DATA_PAIR_WRAPPER,32),
        (component['typeName'],component['wrapperName'],component['layout']['managedBytes']))
    wrapper=_selected_wrapper(image,DATA_PAIR_WRAPPER)
    need('selected-data-pair-wrapper',DATA_PAIR,wrapper.wrapped_type)
    image.check_windows(component['sourceWindows'],label=LABEL+'.wrapper')
    pair=component['registeredPair']
    pointer.registered_pair(image,pair,wrapper,label=LABEL+'.registeredPair')
    face,=pair['composition']['interfaces']
    need('exact-interface-wrapper-definition',wrapper.type_definition,face['wrapperDefinition'])
    getter=image.metadata.methods[face['getValueMethodIndex']]
    scalar.owned_method_abi(image,ctx,getter.index,wrapper.type_definition,
        (DATA_PAIR,17,False),[],LABEL+'.dataPairGetter')
    need('named-data-pair-getter','GetValue',image.metadata.string(getter.name_index))
    pointer.leaf(image,image.method_pointer_va(getter),['0F104210','488BC1','0F104A20','0F1101','0F114910','C3'])
    return wrapper,face


def derive_data_pair_transfer(image,pins,wrapper_component):
    """Fresh exact nominal adapter, its actual list dispatcher and typed joins."""
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
    from scripts.game_data.memorypack import pointer_param as pointer,buff_ptr_sources
    from scripts.game_data.memorypack.skill_shared_sequence_sources import selected_inputs
    from scripts.game_data.memorypack.skill_root_value_sources import DATA_PAIR,DATA_PAIR_WRAPPER
    from scripts.game_data.memorypack import event_args_paths,pooled_global_buff_id_sources as providers
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.memorypack import primitive_param
    selected_inputs(pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);ge=GenericEntries(image);md=image.metadata
    wrapper,face=validate_data_pair_wrapper_component(image,pins,wrapper_component,ctx=ctx)
    pair=wrapper_component['registeredPair'];face,=pair['composition']['interfaces']
    wrapper_td=md.types[face['wrapperDefinition']];section=md.sections['interfaceOffsets']
    start=section.offset+wrapper_td.interface_offsets_start*8
    offsets=list(struct.iter_unpack('<ii',md.buf[start:start+wrapper_td.interface_offsets_count*8]))
    ordinal=offsets.index((face['interfaceTypeIndex'],face['interfaceOffset']))
    adapter_context,adapter_context_proof=buff_ptr_sources._adapter_context(image,ge)
    method=buff_ptr_sources._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2','Deserialize')
    canonical=ge.resolve(method.index,[DATA_PAIR,'object'],[])
    list_td=ctx.index.types['MemoryPack.Formatters.ListFormatter`1']
    list_method,=[m for m in md.methods_for(list_td)if md.string(m.name_index)=='Deserialize']
    list_entry=ge.resolve(list_method.index,[DATA_PAIR],[])
    sources=dict(adapter=pointer.owned(image,canonical['pointer']),list=pointer.owned(image,list_entry['pointer']))
    def call(body,offset):
        row,=[r for r in body['rows']if int(r['va'],16)==body['pointer']+offset]
        raw=bytes.fromhex(row['bytes']);need('exact-direct-call',(5,232),(len(raw),raw[0]))
        return control_transfer(row)['target']
    s={name:call(sources['adapter'],off)for name,off in dict(peek=38,typeHandle=96,creationTest=118,
        activate=151,resolve=211,wrapperProvider=227,wrapperInvoke=262,indexed=302,prepare=316,barrier=441).items()}
    # The FF branch itself owns its cold fragment. Follow the selected E9/JE
    # rather than guessing a contiguous range or a historical fragment RVA.
    g=BytesPath(sources['adapter']['regions'],sources['adapter']['pointer']+45)
    ff=g.relative('0f85');s['header']=BytesPath(sources['adapter']['regions'],ff+8).relative('e8')
    s['adapter']=canonical['pointer'];s['dispatch']=call(sources['list'],449);s['provider']=call(sources['list'],357)
    for role in('dispatch','provider','wrapperInvoke','peek','header'):
        sources[role]=pointer.owned(image,s[role])
    paths={role:[adapter32_program(sources[role]['regions'],sources[role]['pointer'],s,
        dispatch=role=='dispatch',ordinal=ordinal,**path)for path in(
            {},{'create':False},{'wrapper_null':True},{'create':False,'wrapper_null':True},{'null':True})]
        for role in('adapter','dispatch')}
    # Generic slot ownership is independent of the particular DataPair body.
    # The list provider request is slot3 GetFormatter<VAR0>; slot0 contains the
    # same exact list element. The full base validator proves reciprocity.
    from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context
    list_context=ContextSymbols(image).context(list_td.index)
    typed_list=validate_list_formatter_base_context(image,list_context,ge,fail=need)
    ps={name:call(sources['provider'],off)for name,off in dict(typeHandle=52,backend=79,indexed=96,assignable=116).items()}
    need('same-type-from-handle',s['typeHandle'],ps['typeHandle']);need('same-indexed-context-helper',s['indexed'],ps['indexed'])
    provider=provider_inline_cast_program(sources['provider']['regions'],s['provider'],ps)
    need('named-type-from-handle',base+pair['registration']['helperMethods']['typeFromHandle'][3],s['typeHandle'])
    sources['backend']=pointer.owned(image,ps['backend'])
    tails=[control_transfer(r)['target']for r in sources['backend']['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe9']
    need('one-provider-backend-tail',1,len(tails))
    backend=providers.backend_bridge(sources['backend']['regions'],ps['backend'],tails[0])
    invocation=deserialize_slot(sources['wrapperInvoke']['regions'],s['wrapperInvoke'],prepare=s['prepare'],
        callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]))
    reader_offsets=scalar.reader_offsets(image,LABEL)
    peek=event_args_paths.peek(sources['peek']['regions'],s['peek'],reader_offsets)
    header=vector_recorder(image)(s['header']-base)
    primitive_param.object_header_source(image,header,reader_offsets)
    need('same-type-static-cell',provider['typeClassCell'],paths['adapter'][0]['typeClassCell'])
    need('same-provider-static-cell',provider['providerClassCell'],paths['adapter'][0]['providerClassCell'])
    return json.loads(json.dumps(dict(schema='endfield.skill-root-data-pair-transfer.v1',nativeInputs=pins,
        status='proved-selected-value32-transfer',typeName=DATA_PAIR,managedBytes=32,wireBytes=None,
        canonicalRegistration=canonical,listRegistration=list_entry,adapterContext=adapter_context,
        adapterContextProof=adapter_context_proof,listContext=list_context,listContextProof=typed_list,
        interfaceOrdinal=ordinal,paths=paths,providerProgram=provider,backendProgram=backend,
        wrapperInvocation=invocation,peek=peek,header=header,
        symbolRvas={k:v-base for k,v in s.items()},sourceWindows={k:b['windows']for k,b in sources.items()},
        callbackBinding=dict(actualDispatcherComparedAdapterRva=canonical['pointer']-base,
            exactClosedWrapperPointerEqualityInferred=False,condition='The runtime selected slot-five callback and closed MethodInfo match the compared DataPair canonical program and coherent exact DataPair/wrapper context.'),
        runtimeSelectionObserved=False,positiveCollectionAdmitted=False,
        evidenceBoundary=dict(exact='DataPair canonical managed32 adapter, actual compared list dispatcher, default zero32/FF, fresh/reused wrapper and bounded owned conversion-interface search, copy32 and complete returns; actual typed provider source, wrapper callback forwarding and buffered FF sources.',
            conditional=__doc__,unresolved=['positive list loop/allocation composition','runtime formatter/MethodInfo selection','whole root/EOF']))))


def derive_data_pair_child(image,pins):
    """Own the nominal child only; every enclosing caller/list remains separate."""
    from scripts.game_data.memorypack.skill_root_value_sources import DATA_PAIR,derive_data_pair
    child=derive_data_pair(image,pins)
    transfer=derive_data_pair_transfer(image,pins,child)
    capability=dict(typeName=DATA_PAIR,elementValueType=True,memberCount=4,nullable=True,
        nullMarker=255,managedBytes=32,wireBytes=None,
        orderedReads=[dict(fieldName=f,kind=k)for f,k in(
            ('isDynamic','bool'),('key','pooled-string'),('valueDouble','double-bits'),('valueStr','pooled-string'))],
        positiveWireBytes=18,nullWireBytes=1,nullReturnsDefaultValue=True,
        callbackSelectionConditional=True,wholeSkillDataAdmitted=False)
    return dict(schema='endfield.skill-root-data-pair-child.v1',status='validated-conditional-child',
        nativeInputs=pins,capabilities={'skill-root-data-pair':capability},
        proof=dict(child=child,transfer=transfer),
        evidenceBoundary=dict(exact='Selected nominal DataPair MC4/FF source, own wrapper registration, typed hidden32 getter, canonical value adapter and actual compared list dispatcher/provider/conversion.',
            conditional=transfer['callbackBinding']['condition'],
            structuralOnly='Stored blackboard value; no runtime skill or Story behavior is inferred.',
            unresolved=['independent enclosing typed caller and hidden32 ABI join','enclosing collection count/loop/Add and owner framing','runtime selection','whole owner/physical EOF']))

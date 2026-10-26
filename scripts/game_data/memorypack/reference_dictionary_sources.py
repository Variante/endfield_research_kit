"""Current open reference/reference dictionary source, with no child grammar.

The selected nominal ReadPackable parent and both closed reference carriers
are authenticated independently from the object/object source witness. The
actual selected callback must match that source with compatible closed
contexts and normal helpers. This does not observe provider/factory selection
or grant either key/value wire grammar.
"""
def derive(image,pins,*,typed_request,call_target,key_type,value_type,count_limit):
    import copy,json
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.formatter_composition import _vtable,validate_generic_contexts
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack import scalar_param_native as scalar,npc_collection_programs as programs
    from scripts.game_data.memorypack import npc_collection_sources,modelview_packable_sources,lang_key_list_sources
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.levelscript_interactive_sources import dictionary_context
    if type(count_limit)is not int or not 0<=count_limit<=65536:raise ValueError('referenceDictionary.finite-count-limit')
    need=lambda k,e,a:scalar.need('referenceDictionary',k,e,a)
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    cs=ContextSymbols(image);entries=GenericEntries(image)
    type_name='System.Collections.Generic.Dictionary`2<'+key_type+','+value_type+'>'
    bind_typed_read(image,typed_request,method_name='ReadPackable',argument=type_name,kind=21,reference=True)
    argument,=image.instantiations.resolve(typed_request['methodSpec'][2]).arguments
    carrier=cs.type(argument.type_pointer_va)
    need('nominal-dictionary','System.Collections.Generic.Dictionary`2',carrier['definition']['name'])
    need('two-owned-arguments',[key_type,value_type],[r['name']for r in carrier['classArguments']])
    for role,selected in zip(('key','value'),carrier['classArguments'],strict=True):
        raw=bytes.fromhex(selected['rawHex']);need(role+'-ordinary-reference',True,raw[10]in(14,18,21)and raw[11]==0)
        need(role+'-not-managed-value',False,ctx.is_value_type(selected['name']))
    core=_load('npc_runtime_native.json',pins);generic=_load('leveldata_npc_patrol_native.json',pins)['declarations']
    routes=copy.deepcopy(generic['adapters']['referenceRoutes']);routes['wrappers']=[]
    reference=modelview_packable_sources.validate_components(image,pins,core['readPackable'],routes)
    need('actual-reference-parent',base+core['readPackable']['entryRva'],call_target)
    td=ctx.index.types['MemoryPack.Formatters.DictionaryFormatter`2']
    method,=[m for m in md.methods_for(td)if md.string(m.name_index)=='Deserialize']
    context=cs.context(td.index);validate_generic_contexts(image,[context],label='referenceDictionary')
    context_proof=dictionary_context(image,context);slots={r['relativeSlot']:r for r in context['entries']}
    need('slot5-ABI',(False,5,2,'void'),
        (bool(method.flags&16),method.slot,method.parameter_count,ctx.type_name(method.return_type)))
    _vtable(image,td.index,5,method.index,'referenceDictionary')
    reader,out=md.parameters_for(method)
    raw=image.pe.bytes_at_va(ctx.type_pointer(reader.type_index),16)
    need('Reader-byref',(b'\x11\x20',ctx.index.types['MemoryPack.MemoryPackReader'].index),
        (raw[10:12],int.from_bytes(raw[:8],'little')))
    raw=image.pe.bytes_at_va(ctx.type_pointer(out.type_index),16)
    output=image.pe.bytes_at_va(ctx.type_pointer(slots[3]['index']),16)
    need('owned-Dictionary-output',(b'\x15\x20',output[:8]),(raw[10:12],raw[:8]))
    witness=entries.resolve(method.index,['object','object'],[]);body=owned(image,witness['pointer'])
    closed_observations=entries.observe(method.index,[key_type,value_type],[])
    closed=entries.resolve(method.index,[key_type,value_type],[])if closed_observations else None
    if closed is not None:need('actual-closed-source',witness['pointer'],closed['pointer'])
    calls=[control_transfer(r)['target']for r in body['rows']if len(bytes.fromhex(r['bytes']))==5 and bytes.fromhex(r['bytes'])[0]==0xe8]
    need('complete-helper-roles',True,len(calls)>=9)
    symbols=dict(classResolve=calls[0],allocate=calls[1],constructor=calls[2],barrier=calls[3],provider=calls[4],dispatch=calls[6],insert=calls[8])
    need('same-provider-body',calls[4],calls[5]);need('same-reference-dispatch',calls[6],calls[7])
    layout=scalar.reader_offsets(image,'referenceDictionary');layout['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    paths=[programs.dictionary(body['regions'],body['pointer'],symbols,layout,count=n)for n in(-1,0,1)if n<=count_limit]
    for path in paths:
        path['condition']='Fresh output and sufficient buffered bounds; initialized coherent owned TK/TV reference contexts; matching actual canonical callback and separately authenticated key/value providers/callbacks. Normal typed constructor(count,comparer), class, insertion and disabled barrier effects remain conditional. Exact signed count loop; no live provider/factory choice or child grammar follows.'
    ctor=md.methods[slots[4]['methodSpec'][0]]
    need('typed-constructor-ABI',('System.Collections.Generic.Dictionary`2',False,2,'void'),
        (image.type_name(ctor.declaring_type),bool(ctor.flags&16),ctor.parameter_count,ctx.type_name(ctor.return_type)))
    capacity,comparer=md.parameters_for(ctor)
    scalar.ordinary(image,ctx.type_pointer(capacity.type_index),8,'referenceDictionary.capacity')
    comparison=cs.type(ctx.type_pointer(comparer.type_index))
    need('comparer-key-owner','System.Collections.Generic.IEqualityComparer`1',comparison['definition']['name'])
    key_var,=comparison['classArguments']
    need('comparer-owned-key',(ctor.declaring_type,0),(key_var['parameterOwner']['typeIndex'],key_var['parameterOwner']['ordinal']))
    need('actual-typed-constructor',entries.resolve(ctor.index,['object','object'],[])['pointer'],symbols['constructor'])
    overloads=[m for m in md.methods_for(td)if md.string(m.name_index)=='.ctor']
    default,=[m for m in overloads if not m.parameter_count];compared,=[m for m in overloads if m.parameter_count==1]
    defaults,=entries.observe(default.index,['object','object'],[]);compareds,=entries.observe(compared.index,['object','object'],[])
    for declaration,entry in((default,defaults),(compared,compareds)):
        need('own-formatter-constructor-MethodSpec',declaration.index,entries.specs[entry['methodSpecIndex']][0])
        need('explicit-folded-formatter-constructor',True,declaration.index in entry['methodDefinitionIndices'])
    default_body=owned(image,defaults['pointer']);compared_body=owned(image,compareds['pointer'])
    constructors=[programs.dictionary_formatter_default(default_body['regions'],default_body['pointer'],compared_body['pointer']),
        programs.dictionary_formatter_comparer(compared_body['regions'],compared_body['pointer'],symbols['barrier'])]
    provider_context=cs.context(slots[6]['methodSpec'][0],is_method=True)
    need('same-open-GetFormatter-definition',slots[6]['methodSpec'][0],slots[7]['methodSpec'][0])
    validate_generic_contexts(image,[provider_context],label='referenceDictionary.provider')
    ps={r['relativeSlot']:r for r in provider_context['entries']};need('provider-own-slots',[0,1],sorted(ps))
    need('provider-owned-T',provider_context['definition'],ps[0]['type']['parameterOwner']['methodIndex'])
    need('provider-owned-return-T',provider_context['definition'],ps[1]['type']['classArguments'][0]['parameterOwner']['methodIndex'])
    provider_symbols={k:base+v for k,v in generic['referenceProviderSymbols'].items()}
    provider=owned(image,symbols['provider'])
    provider_program=lang_key_list_sources.wrapper_provider_program(provider['regions'],provider['pointer'],provider_symbols)
    factory=lang_key_list_sources.generic_provider_factory(image,pins,provider_symbols,need)
    mapping=npc_collection_sources._factory(image,ctx,entries,core['collections'],need)
    return json.loads(json.dumps(dict(nativeInputs=pins,typeName=type_name,typedRequest=typed_request,
        callTargetRva=call_target-base,closedCarrier=carrier,referenceParent=reference,
        sourceWitness=witness,sourceWitnessClassArguments=['object','object'],sourceWindows=body['windows'],
        programs=paths,context=context,contextProof=context_proof,readerFields=layout,
        symbolRvas={k:v-base for k,v in symbols.items()},constructorObservations=[defaults,compareds],
        constructorPrograms=constructors,constructorWindows=[default_body['windows'],compared_body['windows']],
        providerContext=provider_context,providerWindows=provider['windows'],providerProgram=provider_program,
        providerFactory=factory,collectionFactory=mapping,closedRegistration=closed,
        closedRegistrationObservations=closed_observations,closedPointerEquivalenceProved=closed is not None,
        actualCallbackEqualsCanonicalRequired=True,countLimit=count_limit,headerBytes=4,
        keyGrammarAdmitted=False,valueGrammarAdmitted=False,parentFieldAdmitted=False,
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))

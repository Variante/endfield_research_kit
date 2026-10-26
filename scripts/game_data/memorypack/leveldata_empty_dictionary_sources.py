"""The current LevelData enum-key dictionary, restricted to -1/0 counts.

The concrete enum specialization is not assumed to be registered or pointer
equivalent to an integer specialization. This independently proves the open
TK/TV formatter's reference-output/count programs and its owned generic
contexts. Admission is conditional on the actual selected callback being this
proved source with coherent closed contexts. Neither key/value callbacks nor
positive counts, comparer/hash/storage behavior or live factory selection are
admitted.
"""
KEY='Beyond.Gameplay.LevelWideConfig+LevelWideConfigType'
VALUE='System.Collections.Generic.Dictionary`2<string,Beyond.Gameplay.LevelWideConfig>'
TYPE='System.Collections.Generic.Dictionary`2<'+KEY+','+VALUE+'>'


def select_parent(leveldata):
    parents=[(field,read)for field,read in zip(leveldata['fields'],
        leveldata['program']['orderedReads'],strict=True)if field['name']=='levelWideConfigs']
    if len(parents)!=1:raise ValueError('leveldataEmptyDictionary.one-current-parent')
    field,read=parents[0]
    if (field['typeName']!=TYPE or read['fieldName']!=field['name']
            or read.get('typedUsage')is None):
        raise ValueError('leveldataEmptyDictionary.closed-parent')
    return field,read


def capability():
    """An explicitly conditional count capability; no concrete sharing claim."""
    return dict(closedDictionaryType=TYPE,keyType=KEY,valueType=VALUE,
        allowedCounts=[-1,0],countLimit=0,headerBytes=4,outputBytes=8,
        positiveCountsAdmitted=False,keyGrammarAdmitted=False,valueGrammarAdmitted=False,
        closedPointerEquivalenceProved=False,actualCallbackEqualsCanonicalRequired=True,
        sourceWitnessClassArguments=['object','object'],
        typedConstructorAndHelperCompatibilityRequired=True,
        actualEnumCallbackSelectionObserved=False,providerFactorySelectionObserved=False,
        parentFieldAdmitted=True,wholeOwnerAdmitted=False)


def derive(image,pins,leveldata):
    import copy,json
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.formatter_composition import (
        _vtable,derive_typed_usage_context,validate_generic_contexts)
    from scripts.game_data.memorypack import (
        scalar_param_native as scalar,npc_collection_programs as programs,
        npc_collection_sources,modelview_packable_sources,lang_key_list_sources)
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.levelscript_interactive_sources import dictionary_context
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    cs=ContextSymbols(image);entries=GenericEntries(image)
    need=lambda k,e,a:scalar.need('leveldataEmptyDictionary',k,e,a)
    need('selected-inputs',pins,leveldata['nativeInputs'])
    field,read=select_parent(leveldata)
    usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,
        label='leveldataEmptyDictionary.parent')
    bind_typed_read(image,usage,method_name='ReadPackable',argument=TYPE,kind=21,reference=True)
    argument,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
    carrier=cs.type(argument.type_pointer_va)
    need('closed-dictionary','System.Collections.Generic.Dictionary`2',carrier['definition']['name'])
    key,value=carrier['classArguments'];kr=bytes.fromhex(key['rawHex']);vr=bytes.fromhex(value['rawHex'])
    need('exact-key-name',KEY,key['name']);need('exact-value-name',VALUE,value['name'])
    need('nominal-value-type-key',(b'\x11\x80',ctx.index.types[KEY].index),
        (kr[10:12],int.from_bytes(kr[:8],'little')))
    need('key-parent','System.Enum',ctx.parent(KEY))
    # Backing type is recorded as nominal metadata, never used as a key codec.
    backing=ctx.field(KEY+'::value__')
    need('key-field-owner',KEY,backing[0])
    need('ordinary-generic-reference-value',b'\x15\x00',vr[10:12])
    core=_load('npc_runtime_native.json',pins)
    need('actual-ReadPackable-source',base+core['readPackable']['entryRva'],read['sourceTarget'])
    result=derive_source_witness(image,pins)
    result['parent']=dict(field=field,source=read,typedRequest=usage,closedCarrier=carrier,keyEnumBacking=backing)
    result['capability']=capability()
    return json.loads(json.dumps(result))


def derive_source_witness(image,pins):
    """Fresh open TK/TV -1/0 source only; no closed parent or capability.

    The object/object registration identifies the independent byte witness.
    It does not establish any differently closed pointer, callback/provider
    selection, typed constructor/helper compatibility, key or value codec.
    Each consumer must prove its own exact nominal parent and retain these
    conditions before admitting even the selected null/new-zero states.
    """
    import copy,json
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.formatter_composition import (
        _vtable,derive_typed_usage_context,validate_generic_contexts)
    from scripts.game_data.memorypack import (
        scalar_param_native as scalar,npc_collection_programs as programs,
        npc_collection_sources,modelview_packable_sources,lang_key_list_sources)
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.levelscript_interactive_sources import dictionary_context
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image,pins)
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    cs=ContextSymbols(image);entries=GenericEntries(image)
    need=lambda k,e,a:scalar.need('leveldataEmptyDictionary',k,e,a)
    core=_load('npc_runtime_native.json',pins)
    generic=_load('leveldata_npc_patrol_native.json',pins)['declarations']
    routes=copy.deepcopy(generic['adapters']['referenceRoutes']);routes['wrappers']=[]
    reference=modelview_packable_sources.validate_components(image,pins,core['readPackable'],routes)

    td=ctx.index.types['MemoryPack.Formatters.DictionaryFormatter`2']
    method,=[m for m in md.methods_for(td)if md.string(m.name_index)=='Deserialize']
    context=cs.context(td.index);validate_generic_contexts(image,[context],label='leveldataEmptyDictionary')
    context_proof=dictionary_context(image,context);slots={r['relativeSlot']:r for r in context['entries']}
    need('slot5-ABI',(False,5,2,'void'),
        (bool(method.flags&16),method.slot,method.parameter_count,ctx.type_name(method.return_type)))
    _vtable(image,td.index,5,method.index,'leveldataEmptyDictionary')
    reader,out=md.parameters_for(method)
    rr=image.pe.bytes_at_va(ctx.type_pointer(reader.type_index),16)
    output=image.pe.bytes_at_va(ctx.type_pointer(out.type_index),16)
    declared=image.pe.bytes_at_va(ctx.type_pointer(slots[3]['index']),16)
    need('reader-byref',(b'\x11\x20',ctx.index.types['MemoryPack.MemoryPackReader'].index),
        (rr[10:12],int.from_bytes(rr[:8],'little')))
    need('same-owned-output',(b'\x15\x20',declared[:8]),(output[10:12],output[:8]))
    # This is a current source witness, not a concrete enum registration.
    witness=entries.resolve(method.index,['object','object'],[])
    witness_arguments=[cs.type(a.type_pointer_va)['name']for a in
        image.instantiations.resolve(witness['classInstantiation']['index']).arguments]
    need('canonical-source-witness-arguments',['object','object'],witness_arguments)
    body=owned(image,witness['pointer'])
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    calls=[control_transfer(r)['target']for r in body['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8']
    need('source-call-count',True,len(calls)>=9)
    symbols=dict(classResolve=calls[0],allocate=calls[1],constructor=calls[2],barrier=calls[3],
        provider=calls[4],dispatch=calls[6],insert=calls[8])
    need('same-open-provider',calls[4],calls[5]);need('same-open-dispatch',calls[6],calls[7])
    offsets=scalar.reader_offsets(image,'leveldataEmptyDictionary')
    offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    paths=[programs.dictionary(body['regions'],body['pointer'],symbols,offsets,count=n)for n in(-1,0)]
    for path in paths:
        path['condition']='Fresh output; buffered valid -1/0 count; initialized coherent closed TK/TV context; actual selected callback equals independently proved canonical source. Normal typed allocation/constructor(count,comparer), provider and disabled barrier effects remain conditional. No key/value callback or insertion executes.'
    ctor=md.methods[slots[4]['methodSpec'][0]]
    need('constructor-ABI',('System.Collections.Generic.Dictionary`2',False,2,'void'),
        (image.type_name(ctor.declaring_type),bool(ctor.flags&16),ctor.parameter_count,ctx.type_name(ctor.return_type)))
    capacity,comparer=md.parameters_for(ctor)
    scalar.ordinary(image,ctx.type_pointer(capacity.type_index),8,'leveldataEmptyDictionary.capacity')
    comparison=cs.type(ctx.type_pointer(comparer.type_index))
    need('comparer-definition','System.Collections.Generic.IEqualityComparer`1',comparison['definition']['name'])
    key_var,=comparison['classArguments']
    need('comparer-owned-key',(ctor.declaring_type,0),
        (key_var['parameterOwner']['typeIndex'],key_var['parameterOwner']['ordinal']))
    need('actual-constructor-witness',entries.resolve(ctor.index,['object','object'],[])['pointer'],symbols['constructor'])
    overloads=[m for m in md.methods_for(td)if md.string(m.name_index)=='.ctor']
    default,=[m for m in overloads if m.parameter_count==0]
    compared,=[m for m in overloads if m.parameter_count==1]
    # Folded constructors are explicit current observations, not unique-owner
    # pointer resolutions. Their full selected programs and own MethodSpecs
    # are checked independently below.
    default_entry,=entries.observe(default.index,['object','object'],[])
    compared_entry,=entries.observe(compared.index,['object','object'],[])
    for declaration,observation in ((default,default_entry),(compared,compared_entry)):
        need('constructor-own-MethodSpec',declaration.index,entries.specs[observation['methodSpecIndex']][0])
        need('constructor-explicit-fold',True,declaration.index in observation['methodDefinitionIndices'])
    default_body=owned(image,default_entry['pointer']);compared_body=owned(image,compared_entry['pointer'])
    constructors=[programs.dictionary_formatter_default(default_body['regions'],default_body['pointer'],compared_body['pointer']),
        programs.dictionary_formatter_comparer(compared_body['regions'],compared_body['pointer'],symbols['barrier'])]
    provider_context=cs.context(slots[6]['methodSpec'][0],is_method=True)
    need('one-open-provider-definition',slots[6]['methodSpec'][0],slots[7]['methodSpec'][0])
    validate_generic_contexts(image,[provider_context],label='leveldataEmptyDictionary.provider')
    ps={r['relativeSlot']:r for r in provider_context['entries']}
    need('provider-own-slots',[0,1],sorted(ps))
    need('provider-owned-T',provider_context['definition'],ps[0]['type']['parameterOwner']['methodIndex'])
    need('provider-result-owned-T',provider_context['definition'],ps[1]['type']['classArguments'][0]['parameterOwner']['methodIndex'])
    provider_symbols={k:base+v for k,v in generic['referenceProviderSymbols'].items()}
    provider=owned(image,symbols['provider'])
    provider_program=lang_key_list_sources.wrapper_provider_program(provider['regions'],provider['pointer'],provider_symbols)
    provider_factory=lang_key_list_sources.generic_provider_factory(image,pins,provider_symbols,need)
    factory=npc_collection_sources._factory(image,ctx,entries,core['collections'],need)
    barrier,barrier_proof,_=_fast_barrier(image,symbols['barrier'])
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(nativeInputs=pins,referenceParentSource=reference,
        sourceWitness=witness,sourceWitnessClassArguments=witness_arguments,
        sourceWindows=body['windows'],sourcePrograms=paths,context=context,
        contextProof=context_proof,formatterConstructors=constructors,
        constructorObservations=[default_entry,compared_entry],uniqueConstructorBodyOwnershipProved=False,
        constructorWindows=[default_body['windows'],compared_body['windows']],
        providerContext=provider_context,providerWindows=provider['windows'],providerProgram=provider_program,
        providerFactory=provider_factory,factory=factory,barrier=dict(source=barrier,proof=barrier_proof),
        closedPointerEquivalenceProved=False,
        actualCallbackEqualsCanonicalRequired=True,wholeOwnerAdmitted=False,
        liveFormatterSelectionObserved=False)))

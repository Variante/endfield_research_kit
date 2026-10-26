"""Own normalized enum/reference dictionary and its exact nested-value join.

The registered Int32Enum/reference source is a code witness, never evidence
that an integer dictionary or the original closed dictionary has its pointer.
Original typed contexts and actual callback equality remain conditions.
"""
import json

from scripts.game_data.memorypack.leveldata_levelwide_inner_sources import KEY,VALUE,TYPE as INNER,PARENT as TYPE


def need(check,condition):
    if not condition:raise ValueError('levelwideOuter.'+check)


def helper_entry_observations(symbols,pair_registration,add_registration):
    """A separately proved direct pair body need not be a registered entry.

    The owner must prove that body's entire selected source and the actual
    caller-supplied pair MethodInfo/ABI separately. This function supplies no
    such proof, pointer alias or original closed registration identity.
    """
    values=(symbols.get('keyValue'),symbols.get('Add'),pair_registration.get('pointer'),add_registration.get('pointer'))
    need('literal-helper-entry-observations',all(type(value)is int and value>0 for value in values))
    need('same-actual-selected-typed-Add',symbols['Add']==add_registration['pointer'])
    return dict(actualPairTarget=symbols['keyValue'],canonicalPairRegistration=pair_registration,
        samePairPhysicalEntry=symbols['keyValue']==pair_registration['pointer'],
        actualPairBodyAndOwnedMethodInfoABIRequired=True,actualPairRegistrationIdentityProved=False,
        actualAddRegistration=add_registration,closedPointerEquivalenceProved=False)


def prove_count_induction(paths):
    """Pure byte-identical loop certificate; provides no callback admission."""
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    from scripts.game_data.memorypack.leveldata_levelwide_records import LIMIT
    inductions=[]
    need('both-exact-comparer-paths',len(paths)==10 and all(type(p.get('sameComparer'))is bool for p in paths))
    for comparer in(False,True):
        programs=[dict(p,elementCallbacks=len(p['keyValueCallbackSites']))for p in paths if p['sameComparer']is comparer]
        singles=[p for p in programs if p['countWitness']==1]
        need('one-complete-positive-witness-per-comparer',len(singles)==1)
        single=singles[0]['selectedBytes']
        edges=[single[i+2][0]for i,(_,raw)in enumerate(single[:-3])
            if raw.lower()=='ffc7'and single[i+1][1].lower()=='3b7c2430'and single[i+2][1].lower()=='0f8c']
        need('sole-actual-counter-comparison-backedge',len(edges)==1)
        induction=prove_induction(programs,initial='33ff',increment='ffc7',comparison='3b7c2430',
            counter='edi',saved_count='rsp+48',max_count=LIMIT,mode_key='newDictionary',backedge_sites=edges)
        inductions.append(dict(sameComparer=comparer,proof=induction))
    return inductions


def derive(image,pins,*,parent_request,key_source,inner_source):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context,_vtable
    from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack.leveldata_levelwide_inner_sources import validate_parent_carrier
    from scripts.game_data.memorypack.leveldata_levelwide_dictionary_programs import enum_dictionary,enum_pair
    from scripts.game_data.memorypack.levelscript_interactive_sources import dictionary_context,dictionary_add_program
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.scalar_param_native import reader_offsets
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    _publication_gate(image,pins);base=image.pe.image_base;md=image.metadata
    ctx=NativeReferenceContext(image);cs=ContextSymbols(image);ge=GenericEntries(image)
    validate_typed_usage_context(image,parent_request,label='levelwideOuter.actual-parent')
    bind_typed_read(image,parent_request,method_name='ReadPackable',argument=TYPE,kind=21,reference=True)
    argument,=image.instantiations.resolve(parent_request['methodSpec'][2]).arguments
    carrier=cs.type(argument.type_pointer_va)
    validate_parent_carrier(carrier,key_definition=ctx.index.types[KEY].index,value_definition=ctx.index.types[VALUE].index)
    need('own-fresh-children',key_source['nativeInputs']==inner_source['nativeInputs']==pins
        and inner_source['typeName']==INNER and inner_source['positiveCountLoopProved']is True
        and inner_source['pooledStringKeyGrammarProved']is True)
    key=key_source['capability']
    need('exact-nominal-key',key['typeName']==KEY and key['typeDefinition']==ctx.index.types[KEY].index
        and key['status']=='validated-conditional-callback'and key['wireBytes']==4 and key['callbackSlot']==5
        and key['actualRuntimeSelectionObserved']is False)
    callback=key_source['proof']['selectedCallbackSource']['proof']
    image.check_windows(callback['callbackWindows'],label='levelwideOuter.own-nominal-callback')
    selected=ge.resolve(key['formatterMethodDefinition'],['System.Int32Enum'],[])
    need('same-independent-selected-key-code',selected['pointer']==base+key['callbackTargetRva'])
    _vtable(image,ctx.index.types[key['formatterType']].index,5,key['formatterMethodDefinition'],'levelwideOuter.key')
    td=ctx.index.types['MemoryPack.Formatters.DictionaryFormatter`2']
    method,=[m for m in md.methods_for(td)if md.string(m.name_index)=='Deserialize']
    _vtable(image,td.index,5,method.index,'levelwideOuter.dictionary')
    context=cs.context(td.index);context_proof=dictionary_context(image,context)
    # Both separately selected sources use this same owned generic declaration;
    # this equality does not assert equality of their compiled entries.
    need('same-original-helper-ABI-context',context==inner_source['sourceWitness']['context'])
    slots={row['relativeSlot']:row for row in context['entries']}
    need('same-owned-pair-Add-definitions',
        slots[8]['methodSpec'][0]==inner_source['helperABI']['pairMethodDefinition']
        and slots[9]['methodSpec'][0]==inner_source['helperABI']['AddMethodDefinition'])
    registration=ge.resolve(method.index,['System.Int32Enum','object'],[])
    body=owned(image,registration['pointer']);offsets=reader_offsets(image,'levelwideOuter')
    offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    paths=[enum_dictionary(body['regions'],body['pointer'],offsets,count=n,same_comparer=c)
        for n in(-1,0,1,2,3)for c in(False,True)]
    symbols={}
    for path in paths:
        for role,target in path['symbols'].items():
            need('same-owned-helper:'+role,role not in symbols or symbols[role]==target)
            symbols[role]=target
    need('one-owned-positive-loop',all(p['normalReturn']and p['entryRspRestored']
        and p['keyOutputBytes']==4 and p['valueOutputBytes']==8 and p['countSlot']==48
        and p['counter']=='edi'and p['valueReferenceUnchanged']is True for p in paths))
    from scripts.game_data.memorypack.leveldata_levelwide_records import LIMIT
    inductions=prove_count_induction(paths)
    pair_registration=ge.resolve(slots[8]['methodSpec'][0],[],['System.Int32Enum','object'])
    add_registration=ge.resolve(slots[9]['methodSpec'][0],['System.Int32Enum','object'],[])
    helper_entries=helper_entry_observations(symbols,pair_registration,add_registration)
    pair_body=owned(image,symbols['keyValue'])
    pair=enum_pair(pair_body['regions'],pair_body['pointer'],offsets,callback=selected['pointer'])
    inner_target=inner_source['registration']['pointer']
    dispatch=owned(image,pair['valueDispatcher'])
    value_dispatch=deserialize_slot(dispatch['regions'],dispatch['pointer'],prepare=pair['prepareTarget'],callback=inner_target)
    add_body=owned(image,symbols['Add']);calls=[]
    for row in add_body['rows']:
        raw=bytes.fromhex(row['bytes'])
        if raw==b'\xc3':break
        if raw[:1]==b'\xe8':calls.append(control_transfer(row)['target'])
    need('sole-Add-insertion-call',len(calls)==1)
    add=dictionary_add_program(add_body['regions'],add_body['pointer'],dict(tryInsert=calls[0]))
    barrier=_fast_barrier(image,symbols['barrier'])
    image.check_windows(inner_source['sourceWindows'],label='levelwideOuter.independent-nested-value-source')
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.story-levelwide-outer-dictionary-source.v1',
        status='validated-conditional-source-only',nativeInputs=pins,typeName=TYPE,keyType=KEY,valueType=INNER,
        actualParent=dict(typedRequest=parent_request,closedCarrier=carrier),registration=registration,
        sourceWitnessClassArguments=['System.Int32Enum','object'],context=context,contextProof=context_proof,
        sourceWindows=body['windows'],sourceRegions=[[at-base,raw.hex()]for at,raw in body['regions']],
        sourcePrograms=paths,readerOffsets=offsets,symbolRvas={role:target-base for role,target in symbols.items()},
        keyCallback=key_source,pair=pair,helperEntryObservations=helper_entries,pairWindows=pair_body['windows'],
        valueCallback=dict(typeName=INNER,callbackTargetRva=inner_target-base,dispatch=value_dispatch),
        Add=dict(registration=add_registration,program=add,windows=add_body['windows']),barrier=barrier,
        helperABI=inner_source['helperABI'],induction=inductions,positiveCountLoopProved=True,positiveCountRange=[1,LIMIT],
        keyGrammarProved=True,valueGrammarAdmitted=False,positiveDictionaryAdmitted=False,
        closedPointerEquivalenceProved=False,actualCallbackEqualsSourceWitnessRequired=True,
        actualKeyCallbackEqualsOwnNominalRequired=True,actualValueCallbackEqualsOwnInnerSourceRequired=True,
        typedConstructorAndHelperCompatibilityRequired=True,runtimeFormatterSelectionObserved=False,
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Actual outer/nested nominal carriers; separate enum/reference source, own ordinary enum callback and second raw-DWORD comparison, actual direct pair body and separately owned pair MethodInfo ABI, exact Add registration/ABI, same-Reader reference dispatcher to independent nested source, invariant count loop and complete normal return. The separate canonical pair registration is an observation and may have a different physical entry.',
            conditional=__doc__+' Initialized matching contexts, initially-null output, selected ready paths, disabled collector and normal compatible allocation/provider/Initialize/comparer/TryInsert effects remain required.',
            unresolved=['concrete nested child grammar and actual host field composition','runtime callbacks/providers/factory or dictionary gameplay behavior']))))

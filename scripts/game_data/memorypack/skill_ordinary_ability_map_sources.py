"""Ordinary AbilityActionMap, its Sequence array and its separate reference list.

The older passive-map component owns an existing selected wrapper. This owner
additionally requires all four complete concrete caller paths, own construction
and GetValue, an ordinary canonical adapter and actual ReadValue identity.
Its array holds independently admitted SequenceActionData references, never
AbilityActionData references or fixed-width wire elements. The outer list has
its own actual ReadPackable request/count/callback/Add induction. Initialized
coherent contexts, matching canonical callbacks, normal typed allocation and
helpers, disabled collector and stable disjoint buffered storage remain
conditions. Runtime event delivery, provider choice, enclosing action/root and
physical EOF remain unresolved. Pure composition supplies no native admission.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

SCHEMA='endfield.skill-ordinary-ability-map-sources.v1'
TYPE='Beyond.Gameplay.Core.AbilityActionMap'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_AbilityActionMapForMemoryPack'
EVENT='Beyond.Gameplay.Core.AbilitySystem+Event'
SEQUENCE='Beyond.Gameplay.Core.SequenceActionData'
CAPABILITY='skill-ordinary-ability-action-map'
ARRAY='skill-ordinary-ability-map-sequence-array'
LIST='skill-action-ordinary-ability-map-list'


def ordered_reads():
    return [dict(memberIndex=0,fieldName='abilityEvent',kind='scalar32',childCapability=None),
        dict(memberIndex=1,fieldName='actions',kind='ordinary-map-sequence-array',childCapability=ARRAY)]


def require_source(source,pins):
    need('ordinary-map-own-complete-source',True,source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==pins and(source.get('wrappedType'),source.get('wrapperName'))==(TYPE,WRAPPER)
        and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False
        and source.get('wholeOwnerAdmitted')is False)
    need('ordinary-map-actual-field-order',[('abilityEvent',EVENT),('actions',SEQUENCE+'[]')],
        [(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])])
    life=source.get('lifecycle',{})
    need('ordinary-map-direct-owned-holder',True,life.get('directHolderMode')is True
        and life.get('typedCache')is None and life.get('baseHolder')==[WRAPPER,TYPE,16])
    paths=source.get('programs',[])
    need('ordinary-map-four-complete-frames',True,len(paths)==4 and all(type(p.get('existing'))is bool
        and type(p.get('wrapperNull'))is bool and p.get('frame',{}).get('entryRspRestored')is True
        and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths)
        and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)})


def require_sequence(sequence,pins):
    need('ordinary-map-Sequence-native-inputs',pins,sequence['nativeInputs'])
    cap=sequence['capabilities']['SequenceActionData']
    need('ordinary-map-independent-ordinary-Sequence',True,cap.get('typeName')==SEQUENCE
        and all(cap.get(k)is True for k in('nullAdmitted','wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
            'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved','positiveCountsAdmitted','freshArrayCountInductionProved'))
        and cap.get('collectionCounts')==[-1,0]and all(type(n)is int for n in cap['collectionCounts'])
        and type(cap.get('countLimit'))is int and cap['countLimit']==10000
        and type(cap.get('referenceReaderMethodDefinition'))is int and cap['referenceReaderMethodDefinition']>0
        and type(cap.get('referenceReaderTargetRva'))is int and cap['referenceReaderTargetRva']>0)
    return cap


def compose_array(pins,typed_request,call_target_rva,array,sequence):
    """Bind the actual reference-array callback to its complete ordinary child."""
    element=require_sequence(sequence,pins);need('ordinary-map-array-native-inputs',pins,array['nativeInputs'])
    need('ordinary-map-owned-array-status','validated-conditional-reference-array-component',array.get('status'))
    need('ordinary-map-actual-array-request',typed_request,array['typedRequest'])
    need('ordinary-map-array-ReadArray',(6,'MemoryPack.MemoryPackReader','ReadArray',[],[SEQUENCE]),
        tuple(typed_request.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments')))
    need('ordinary-map-array-source-identity',True,type(call_target_rva)is int and call_target_rva>0
        and type(typed_request['methodSpec'][0])is int and typed_request['methodSpec'][0]>0
        and type(array.get('arrayReaderMethodDefinition'))is int
        and array['arrayReaderMethodDefinition']==typed_request['methodSpec'][0]
        and type(array.get('arrayReaderTargetRva'))is int and array['arrayReaderTargetRva']==call_target_rva)
    need('ordinary-map-array-scope',True,(array.get('elementType'),array.get('closedArrayType'))==(SEQUENCE,SEQUENCE+'[]')
        and array.get('elementValueType')is False
        and type(array.get('countLimit'))is int and array['countLimit']==10000
        and array.get('positiveCountsAdmitted')is True and array.get('nullable')is True
        and array.get('collectionCounts')==[-1,0]and all(type(n)is int for n in array['collectionCounts'])
        and all(array.get(k)is False for k in('elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted')))
    nominal=array['elementNominalReference'];adapter=sequence['proof']['lifecycle']['adapter']
    need('ordinary-map-exact-array-element-Reader',
        (SEQUENCE,element['wrapperName'],element['referenceReaderMethodDefinition'],element['referenceReaderTargetRva']),
        tuple(nominal.get(k)for k in('typeName','wrapperName','referenceReaderMethodDefinition','referenceReaderTargetRva')))
    need('ordinary-map-same-selected-canonical-adapter',adapter['callbackBinding']['canonicalTargetRva'],
        nominal['callbackBinding']['canonicalTargetRva'])
    need('ordinary-map-conditional-callback-selection',True,adapter['callbackBinding'].get('actualCallbackEqualsCanonicalRequired')is True
        and nominal['callbackBinding'].get('actualCallbackEqualsCanonicalRequired')is True)
    return dict(elementType=SEQUENCE,elementValueType=False,closedArrayType=SEQUENCE+'[]',elementCapability='SequenceActionData',
        collectionCounts=[-1,0],countLimit=10000,positiveCountsAdmitted=True,nullable=True,elementGrammarAdmitted=True,
        arrayReaderMethodDefinition=array['arrayReaderMethodDefinition'],arrayReaderTargetRva=call_target_rva,
        wholeGrammarAdmitted=True,parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def bind_array_member(pins,join,child,capability):
    need('ordinary-map-array-capability',ARRAY,capability)
    need('ordinary-map-array-same-owned-source',child['proof']['array'],join['arraySource'])
    cap=compose_array(pins,join['typedRequest'],join['sourceTargetRva'],join['arraySource'],child['proof']['sequence'])
    need('ordinary-map-array-exact-capability',cap,child['capabilities'][ARRAY])
    need('ordinary-map-named-array-field',('actions',SEQUENCE+'[]'),(join['fieldName'],join['typeName']))
    return dict(fieldName='actions',typeName=SEQUENCE+'[]',capability=ARRAY,
        readerMethodDefinition=cap['arrayReaderMethodDefinition'],sourceTargetRva=cap['arrayReaderTargetRva'],
        arrayCapabilityShape=cap,elementCapabilityShape=child['capabilities']['SequenceActionData'])


def bind_program(program):
    need('ordinary-map-literal-member-count',True,type(program.get('memberCount'))is int and program['memberCount']==2)
    need('ordinary-map-exact-compiled-fields',True,program.get('reads')==ordered_reads()
        and all(type(r.get('memberIndex'))is int for r in program['reads']))
    need('ordinary-map-exact-array-dependency',[ARRAY],program.get('requiredCapabilities'))


def _derive_on_sequence(image,pins,sequence):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.generated_reader_sources import derive as source_derive
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.pointer_param import leaf
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    from scripts.game_data.memorypack import skill_ordinary_ability_map_factory_sources as factory
    _publication_gate(image,pins);element=require_sequence(sequence,pins)
    prepared=factory.prepare(image,pins)
    def factory_prover(actual_image,ctx,wrapper,body,symbols,original_ctor):
        need('ordinary-map-same-selected-factory-image',True,actual_image is image)
        return factory.prove(actual_image,ctx,wrapper,body,symbols,original_ctor,prepared=prepared)
    source=source_derive(image,pins,WRAPPER,direct_factory_prover=factory_prover);require_source(source,pins)
    read=source['orderedSourceReads'][1];request=derive_typed_usage_context(image,read['context']['instructionRva'],label='ordinaryAbilityMap')
    array=source['sourceScope']['arraySources']['1']
    need('ordinary-map-independently-same-actual-array-source',prepared['actualArraySource'],array)
    array_cap=compose_array(pins,request,read['sourceTargetRva'],array,sequence)
    array_child=dict(nativeInputs=pins,capabilities={ARRAY:array_cap,'SequenceActionData':element},proof=dict(array=array,sequence=sequence))
    compiled,pending=compile_member_program(source,pins,wrapper_name=WRAPPER,type_name=TYPE,value4={},typed_requests={1:request},
        arrays={SEQUENCE+'[]':(ARRAY,'ordinary-map-sequence-array',ARRAY)},array_children={1:array_child},array_binder=bind_array_member)
    need('ordinary-map-complete-member-program',[],pending);bind_program(compiled)
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==WRAPPER]
    pair=derive_pair(image,TYPE,WRAPPER);adapter=derive_adapter(image,pins,pair,wrapper)
    need('ordinary-map-same-owned-getter',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
    getter=leaf(image,image.pe.image_base+adapter['getterMethod'][3],['488B4110','C3'])
    need('ordinary-map-same-owned-reader',source['method'],adapter['pairForwarder']['readerMethod'])
    abi=reference_reader_abi(image,pins)
    cap=dict(typeName=TYPE,wrapperName=WRAPPER,memberCount=2,orderedReads=ordered_reads(),nullable=True,nullMarker=255,nullAdmitted=True,
        wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,ownConcreteGetterSemanticsProved=True,
        ownConcreteFactorySemanticsProved=True,completeSourceOwnedProgram=True,
        **{k:abi[k]for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')})
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,nativeInputs=pins,status='validated-conditional-ordinary-ability-map',
        capabilities={CAPABILITY:cap,ARRAY:array_cap},requiredExternalCapabilities=['SequenceActionData'],
        requiredExternalCapabilityIdentities={'SequenceActionData':{k:element[k]for k in('typeName','referenceReaderMethodDefinition','referenceReaderTargetRva')}},
        proof=dict(source=source,compiled=compiled,arrayChild=array_child,pair=pair,adapter=adapter,getter=getter,referenceABI=abi),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(exact='Own complete new/existing/FF map caller and concrete lifecycle, Event enum32 source, actual ReadArray<Sequence> context/callback/count induction and ordinary pair/adapter/Reader.',
            conditional=__doc__,structuralOnly='Stored event/sequence configuration.',unresolved=['live event/provider choice','enclosing action/root/physical EOF']))))


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_sequence_components import derive as sequence_derive
    _publication_gate(image,pins)
    return _derive_on_sequence(image,pins,sequence_derive(image,pins))


def _derive_list_on_child(image,pins,child,*,typed_request,call_target,count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as list_derive
    from scripts.game_data.memorypack.skill_action_reference_list_sources import compose_reference_list,bind_parent_request,bind_reference_reader
    _publication_gate(image,pins)
    listing=list_derive(image,pins,typed_request=typed_request,call_target=call_target,element_type=TYPE,count_limit=count_limit)
    parent=bind_parent_request(listing,typed_request,call_target,image.pe.image_base,label='ordinary-ability-map-list')
    reader=bind_reference_reader(image,pins,listing,child,element_capability=CAPABILITY,label='ordinary-ability-map-list')
    cap=compose_reference_list(listing,child,pins,element_type=TYPE,element_capability=CAPABILITY,label='ordinary-ability-map-list')
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-ordinary-ability-map-list.v1',nativeInputs=pins,
        status='validated-conditional-ordinary-ability-map-list',capabilities={**child['capabilities'],LIST:cap},
        requiredExternalCapabilities=child['requiredExternalCapabilities'],
        requiredExternalCapabilityIdentities=child['requiredExternalCapabilityIdentities'],
        proof=dict(collection=listing,child=child,actualParentRequestBinding=parent,listElementReaderBinding=reader),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(exact='Actual nominal ordinary map list/count/callback/Add induction joined to complete independent ordinary map and Sequence array.',
            conditional=__doc__,structuralOnly='Stored event/sequence collection.',unresolved=['enclosing action/root/physical EOF','live callback choice','nonempty reused/growth/refill']))))


def derive_list(image,pins,*,typed_request,call_target,count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image,pins)
    return _derive_list_on_child(image,pins,derive(image,pins),typed_request=typed_request,call_target=call_target,count_limit=count_limit)

"""Finite ordinary-reference list children with independent element owners.

Only the explicit Blackboard and SequenceActionData closed nominal lists enter
this domain. The list's actual ReadPackable MethodSpec/E8, selected canonical
reference callback and bounded fresh/reused-empty count loop are independent
of the child's ordinary ReadValue, lifecycle and wire program. References
occupying eight managed bytes never imply eight serialized bytes. Initialized
coherent contexts, matching normal callbacks/helpers, typed zeroed allocation,
disabled compatible collector and stable disjoint buffered storage remain
conditions. Nonempty reuse/growth/refill, live callback selection, enclosing
actions and physical EOF remain unproved.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

TYPES={
    'Beyond.Blackboard+BlackboardDouble':('skill-action-blackboard-double-list','skill-blackboard-double'),
    'Beyond.Blackboard+BlackboardString':('skill-action-blackboard-string-list','skill-blackboard-string'),
    'Beyond.Gameplay.Core.Conditions.BlackboardBuffId':('skill-action-blackboard-buff-id-list','skill-blackboard-buff-id'),
    'Beyond.Gameplay.Core.SequenceActionData':('skill-action-sequence-list','SequenceActionData'),
}


def compose_reference_list(collection,child,pins,*,element_type,element_capability,label):
    """Pure nominal/count/ABI join; no native or enclosing-owner admission."""
    check=lambda name,expected,actual:need(label+'-'+name,expected,actual)
    check('same-native-inputs',pins,collection['nativeInputs']);check('child-same-native-inputs',pins,child['nativeInputs'])
    check('current-reference-loop','validated-bounded-reference-list-induction',collection['status'])
    check('exact-element',element_type,collection['elementType'])
    check('unadmitted-enclosure',True,all(collection.get(k)is False for k in
        ('elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted')))
    check('fresh-and-empty-reuse',True,collection.get('nullable')is True and collection.get('freshListsAdmitted')is True
        and type(collection.get('reusedListsRequireInitialCount'))is int and collection['reusedListsRequireInitialCount']==0
        and collection.get('reusedListsRequireCapacityAtLeastCount')is True)
    counts=collection['countRange']
    check('literal-bounded-induction',True,isinstance(counts,list)and len(counts)==2
        and all(type(n)is int for n in counts)and counts[0]==-1 and 3<=counts[1]<=10000)
    cap=child['capabilities'][element_capability]
    check('positive-ordinary-child',True,cap.get('typeName')==element_type and cap.get('wholeGrammarAdmitted')is True
        and cap.get('ordinaryOriginalReadValueAdmitted')is True and cap.get('ownConcreteGetterSemanticsProved')is True
        and cap.get('ownConcreteFactorySemanticsProved')is True
        and type(cap.get('referenceReaderMethodDefinition'))is int and cap['referenceReaderMethodDefinition']>0
        and type(cap.get('referenceReaderTargetRva'))is int and cap['referenceReaderTargetRva']>0)
    witness=collection['witnessComponent'];usage=witness['typedRequest'];nominal='System.Collections.Generic.List`1<'+element_type+'>'
    check('same-callback-reference-definition',cap['referenceReaderMethodDefinition'],
        witness['referenceSource']['valueContext']['readerMethodDefinition'])
    check('exact-actual-request',(6,'MemoryPack.MemoryPackReader','ReadPackable',[],[nominal]),
        tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments')))
    check('literal-parent-reader',True,type(usage['methodSpec'][0])is int and usage['methodSpec'][0]>0
        and type(witness.get('callTargetRva'))is int and witness['callTargetRva']>0)
    return dict(elementType=element_type,elementValueType=False,closedListType=nominal,elementCapability=element_capability,
        collectionCounts=[-1,0],countLimit=counts[1],positiveCountsAdmitted=True,nullable=True,elementGrammarAdmitted=True,
        packableReaderMethodDefinition=usage['methodSpec'][0],packableReaderTargetRva=witness['callTargetRva'],
        callbackSelectionConditional=True,wholeSkillDataAdmitted=False)


def bind_reference_reader(image,pins,collection,child,*,element_capability,label):
    """Fresh actual optimized Reader source, separately from its definition."""
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    reader=ec.clone_facts(image,pins)['ReadValue'];cap=child['capabilities'][element_capability]
    need(label+'-same-actual-reader-definition',reader['equivalentMethod'][0],cap['referenceReaderMethodDefinition'])
    need(label+'-same-actual-reader-target',reader['targetRva'],cap['referenceReaderTargetRva'])
    need(label+'-same-callback-reader-definition',cap['referenceReaderMethodDefinition'],
        collection['witnessComponent']['referenceSource']['valueContext']['readerMethodDefinition'])
    return dict(actualReadValue=reader,callbackReaderMethodDefinition=cap['referenceReaderMethodDefinition'],
        actualOptimizedReaderTargetRva=cap['referenceReaderTargetRva'],canonicalPointerEqualityClaimed=False)


def bind_parent_request(collection,typed_request,call_target,image_base,*,label):
    """The supplied source call must be the independently proved list request."""
    witness=collection['witnessComponent']
    need(label+'-same-actual-parent-request',typed_request,witness['typedRequest'])
    need(label+'-literal-actual-parent-target',True,type(call_target)is int and type(image_base)is int
        and call_target>image_base and type(witness.get('callTargetRva'))is int)
    need(label+'-same-actual-parent-target',call_target-image_base,witness['callTargetRva'])
    return dict(typedRequest=typed_request,callTargetRva=call_target-image_base)


def _derive_on_child(image,pins,child,*,typed_request,call_target,count_limit=10000):
    """Caller freshly owns the independently selected child on this same image."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as list_source
    _publication_gate(image,pins)
    args=typed_request.get('methodArguments',[])
    candidates=[t for t in TYPES if args==['System.Collections.Generic.List`1<'+t+'>']]
    need('reference-list-finite-element',1,len(candidates));element,=candidates;capability,element_capability=TYPES[element]
    collection=list_source(image,pins,typed_request=typed_request,call_target=call_target,element_type=element,count_limit=count_limit)
    parent=bind_parent_request(collection,typed_request,call_target,image.pe.image_base,label='action-reference-list')
    binding=bind_reference_reader(image,pins,collection,child,element_capability=element_capability,label='action-reference-list')
    cap=compose_reference_list(collection,child,pins,element_type=element,element_capability=element_capability,label='action-reference-list')
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-action-reference-list-sources.v1',
        status='validated-conditional-action-reference-list',nativeInputs=pins,
        capabilities={capability:cap,element_capability:child['capabilities'][element_capability]},
        requiredExternalCapabilities=[element_capability],proof=dict(collection=collection,child=child,
            actualParentRequestBinding=parent,listElementReadValueBinding=binding),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
            exact='Actual selected closed reference-list count/callback/Add and induction, exact nominal ordinary child lifecycle/wire source identity.',
            conditional=__doc__,structuralOnly='Stored authored collection.',
            unresolved=['actual enclosing parent action/field/union','runtime callback/provider selection','nonempty reuse/growth/refill','whole owner/physical EOF']))))


def derive(image,pins,*,typed_request,call_target,count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image,pins)
    args=typed_request.get('methodArguments',[])
    candidates=[t for t in TYPES if args==['System.Collections.Generic.List`1<'+t+'>']]
    need('reference-list-finite-element',1,len(candidates));element,=candidates
    if element=='Beyond.Blackboard+BlackboardDouble':
        from scripts.game_data.memorypack.skill_blackboard_double_sources import derive as child_source
    elif element=='Beyond.Gameplay.Core.Conditions.BlackboardBuffId':
        from scripts.game_data.memorypack.skill_blackboard_buff_id_sources import derive as child_source
    elif element=='Beyond.Blackboard+BlackboardString':
        from scripts.game_data.memorypack.skill_blackboard_string_sources import derive as child_source
    else:
        from scripts.game_data.memorypack.skill_sequence_components import derive as child_source
    return _derive_on_child(image,pins,child_source(image,pins),typed_request=typed_request,call_target=call_target,count_limit=count_limit)

"""Actual action list calls joined to finite current selector union routes.

The selected reference-list callback, constructor/Add/count induction and
ordinary ReadValue identity are independently proved for the actual parent
request. The element is an explicitly finite tagged union, not an ordinary
record with an inferred whole grammar. Each admitted tag still requires its
own current route program at decode time. Matching initialized contexts and
callbacks, normal helper effects, disabled collector, fresh or reused-empty
lists with spare capacity and sufficiently buffered disjoint storage remain
conditions. Live selection and enclosing action/physical EOF are separate.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

SCHEMA='endfield.skill-action-selector-list-sources.v1'
TYPES={
    'Beyond.Gameplay.Core.Selector+Validator+Data':(
        'skill-action-selector-validator-list','SelectorValidator','selector-validator-list'),
    'Beyond.Gameplay.Core.Selector+PostProcessor+Data':(
        'skill-action-selector-postprocessor-list','SelectorPostProcessor','selector-postprocessor-list'),
}


def _compose_selector_list(collection,selectors,pins,*,element_type):
    """Pure exact nominal/callback/finite-route join; native derive is separate."""
    need('selector-list-finite-element',True,element_type in TYPES)
    capability,family,wire=TYPES[element_type]
    need('selector-list-native-inputs',(pins,pins),
        (collection.get('nativeInputs'),selectors.get('nativeInputs')))
    need('selector-list-current-finite-owner',True,
        selectors.get('status')=='validated-finite-current-selector-routes'
        and selectors.get('wholeSkillDataAdmitted')is False
        and selectors.get('nullUnions',{}).get(family)is True)
    child=selectors['capabilities'][family]
    tags=child.get('admittedRouteTags')
    need('selector-list-owned-finite-routes',True,
        child.get('typeName')==element_type and child.get('nullAdmitted')is True
        and child.get('wholeGrammarAdmitted')is False
        and child.get('positiveRoutesRequireExplicitProgram')is True
        and isinstance(tags,list)and bool(tags)
        and all(type(tag)is int and 0<=tag<=65535 for tag in tags)
        and tags==sorted(set(tags)))
    programs=[row for row in selectors['programs']if row['family']==family]
    need('selector-list-exact-program-bijection',tags,sorted(row['tag']for row in programs))
    from scripts.game_data.memorypack.skill_timeline_current_sequence import validate_program
    for program in programs:validate_program(program)
    need('selector-list-independent-induction',True,
        collection.get('status')=='validated-bounded-reference-list-induction'
        and collection.get('elementType')==element_type
        and all(collection.get(key)is False for key in
            ('elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted'))
        and collection.get('nullable')is True and collection.get('freshListsAdmitted')is True
        and type(collection.get('reusedListsRequireInitialCount'))is int
        and collection['reusedListsRequireInitialCount']==0
        and collection.get('reusedListsRequireCapacityAtLeastCount')is True)
    counts=collection.get('countRange')
    need('selector-list-literal-count-bound',True,isinstance(counts,list)and len(counts)==2
        and all(type(n)is int for n in counts)and counts[0]==-1 and 3<=counts[1]<=10000)
    witness=collection['witnessComponent'];usage=witness['typedRequest']
    nominal='System.Collections.Generic.List`1<'+element_type+'>'
    need('selector-list-actual-request',(6,'MemoryPack.MemoryPackReader','ReadPackable',[],[nominal]),
        tuple(usage.get(key)for key in('tag','typeName','methodName','classArguments','methodArguments')))
    need('selector-list-literal-reader-identities',True,
        type(usage['methodSpec'][0])is int and usage['methodSpec'][0]>0
        and type(witness.get('callTargetRva'))is int and witness['callTargetRva']>0
        and type(child.get('referenceReaderMethodDefinition'))is int
        and child['referenceReaderMethodDefinition']>0
        and type(child.get('referenceReaderTargetRva'))is int and child['referenceReaderTargetRva']>0)
    need('selector-list-same-callback-reader',child['referenceReaderMethodDefinition'],
        witness['referenceSource']['valueContext']['readerMethodDefinition'])
    return dict(elementType=element_type,elementValueType=False,closedListType=nominal,
        elementCapability=family,collectionCounts=[-1,0],countLimit=counts[1],positiveCountsAdmitted=True,
        nullable=True,elementGrammarAdmitted=True,admittedRouteTags=tags,
        packableReaderMethodDefinition=usage['methodSpec'][0],packableReaderTargetRva=witness['callTargetRva'],
        callbackSelectionConditional=True,wholeSkillDataAdmitted=False)


def compose_selector_list(collection,selectors,pins,*,element_type):
    """Keep a failed finite join attributable before another aggregate run."""
    try:return _compose_selector_list(collection,selectors,pins,element_type=element_type)
    except(ValueError,KeyError,TypeError,IndexError)as error:
        from scripts.game_data.memorypack.corpus_gate import CensusGateError
        diagnostic=CensusGateError('skillActionSelectorListSources.finite-list-join',
            source='scripts/game_data/memorypack/skill_action_selector_list_sources.py',
            expected='same selected native inputs, exact nominal reference-list callback and count induction, complete finite selector route programs',
            actual=dict(reason=str(error)[:1400],elementType=element_type))
        diagnostic.diagnostic.update(validator='skillActionSelectorListSources',
            failedGate=str(error).split(':',1)[0],typeName=element_type,nativeInputs=pins,
            actualParentRequest=collection.get('witnessComponent',{}).get('typedRequest',{}))
        diagnostic.args=(json.dumps(diagnostic.diagnostic,sort_keys=True),);raise diagnostic from error


def _derive_on_selectors(image,pins,selectors,*,typed_request,call_target,count_limit=10000):
    """The caller freshly owns selectors on this same explicitly selected image."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as derive_list
    from scripts.game_data.memorypack.skill_action_reference_list_sources import bind_parent_request,bind_reference_reader
    _publication_gate(image,pins)
    candidates=[name for name in TYPES
        if typed_request.get('methodArguments')==['System.Collections.Generic.List`1<'+name+'>']]
    need('selector-list-one-exact-nominal',1,len(candidates));element,=candidates
    capability,family,wire=TYPES[element]
    collection=derive_list(image,pins,typed_request=typed_request,call_target=call_target,
        element_type=element,count_limit=count_limit)
    parent=bind_parent_request(collection,typed_request,call_target,image.pe.image_base,label='action-selector-list')
    reader=bind_reference_reader(image,pins,collection,selectors,element_capability=family,label='action-selector-list')
    cap=compose_selector_list(collection,selectors,pins,element_type=element)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-action-selector-list',nativeInputs=pins,
        capabilities={capability:cap,family:selectors['capabilities'][family]},requiredExternalCapabilities=[family],
        proof=dict(collection=collection,selectors=selectors,actualParentRequestBinding=parent,listElementReadValueBinding=reader),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,wholeSkillDataAdmitted=False,
        evidenceBoundary=dict(exact='Actual closed parent request and reference-list induction plus exact ordinary reader and finite selector route identity.',
            conditional=__doc__,structuralOnly='Stored authored selector collection.',
            unresolved=['runtime callback/provider selection','nonempty reuse/growth/refill','enclosing action and physical EOF']))))


def derive(image,pins,*,typed_request,call_target,count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_selector_union_sources import derive as derive_selectors
    _publication_gate(image,pins)
    return _derive_on_selectors(image,pins,derive_selectors(image,pins),typed_request=typed_request,
        call_target=call_target,count_limit=count_limit)

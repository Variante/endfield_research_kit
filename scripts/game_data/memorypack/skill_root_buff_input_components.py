"""Positive BuffInput composition with exact AssignPair and reference sources.

The MC3 caller's assignItems ReadPackable request joins the separately proved
closed AssignPair value40 list, including its own MC6/FF child and hidden value
conversion. BuffInput's own inherited holder/cache/getter/setter and constructor
programs join the exact reference adapter. Lists of BuffInput additionally own
their actual typed parent helper and independent reference count/callback/Add
program. No BuffInputBase union sibling, arbitrary reference list, enclosing
root or physical EOF is admitted by these components. Runtime selection,
inflation and unselected malformed/refill/growth paths remain unresolved;
ordinary coherent selected contexts, normal typed allocations, stable disjoint
buffered storage and noninterfering helper/barrier effects are conditions.
"""
import json

from scripts.game_data.memorypack.skill_root_assign_pair_sources import need,VALUE as ASSIGN_PAIR

VALUE='Beyond.Gameplay.Core.BuffInput'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_BuffInputForMemoryPack'
LIST='System.Collections.Generic.List`1<'+VALUE+'>'


def bind_components(pins,parent,collection,adapter,clones):
    """Join actual source identities; a similarly named child is insufficient."""
    need('buff-input-source-type',(VALUE,WRAPPER),(parent['typeName'],parent['wrapperName']))
    for role,component in(('parent',parent),('collection',collection),('adapter',adapter)):
        need('same-buff-input-pins:'+role,pins,component['nativeInputs'])
    need('positive-list-status','validated-conditional-components',collection['status'])
    need('exact-buff-input-program-MC3',[3,3,None,None],
        [p.get('memberCount')for p in parent['programs']])
    join,=parent['requiredChildJoins'];need('actual-assignItems-field','assignItems',join['fieldName'])
    cap=collection['capabilities']['skill-root-assign-pair-list']
    need('literal-list-booleans',True,all(type(cap.get(k))is bool for k in
        ('elementValueType','elementGrammarAdmitted','positiveCountsAdmitted','nullable')))
    need('exact-assign-pair-value-list',(ASSIGN_PAIR,True,40,True,'skill-root-assign-pair'),
        tuple(cap.get(k)for k in('elementType','elementValueType','managedElementBytes','elementGrammarAdmitted','elementCapability')))
    need('exact-value-list-count-scope',([-1,0],True,True),(cap['collectionCounts'],cap['positiveCountsAdmitted'],cap['nullable']))
    need('literal-list-counts',True,all(type(count)is int for count in cap['collectionCounts']))
    need('bounded-value-list-cap',True,type(cap.get('countLimit'))is int and 1<=cap['countLimit']<=4096)
    value=collection['capabilities']['skill-root-assign-pair']
    need('independent-MC6-child',(ASSIGN_PAIR,6,40,22,1,True),tuple(value.get(k)for k in
        ('typeName','memberCount','managedBytes','positiveWireBytes','nullWireBytes','nullReturnsDefaultValue')))
    need('same-assignItems-method',join['typedRequest']['methodSpec'][0],cap['packableReaderMethodDefinition'])
    need('same-assignItems-target',join['sourceTargetRva'],cap['packableReaderTargetRva'])
    need('exact-reference-adapter',(VALUE,WRAPPER),(adapter['typeName'],adapter['wrapperName']))
    need('same-registered-pair',parent['registeredPair'],adapter['pair'])
    need('actual-BuffInput-GetValue-target',parent['getterForwarder']['entryRva'],adapter['getterMethod'][3])
    need('same-interface-GetValue-name',(WRAPPER,'GetValue'),tuple(adapter['getterMethod'][1:3]))
    need('adapter-does-not-supply-concrete-getter-semantics',True,adapter['getterReturnedReferenceSemanticsProved']is False)
    read=clones['ReadValue']
    need('selected-reference-reader',(['MemoryPack.MemoryPackReader','ReadValue'],'reference'),
        (read['equivalentMethod'][1:3],read['resultAbi']))
    return dict(typeName=VALUE,wrapperName=WRAPPER,memberCount=3,nullable=True,nullMarker=255,
        nullAdmitted=True,wholeGrammarAdmitted=True,
        orderedReads=[dict(fieldName=n,kind=k,childCapability=c)for n,k,c in(
            ('assignBlackboard','bool',None),('assignItems','value-list','skill-root-assign-pair-list'),
            ('buffId','pooled-string','byte-payload'))],
        referenceReaderMethodDefinition=read['equivalentMethod'][0],referenceReaderTargetRva=read['targetRva'],
        ownConcreteGetterSemanticsProved=True,callbackSelectionConditional=True,wholeSkillDataAdmitted=False)


def derive(image,pins):
    """Reprove all exact nominal children on the same selected image."""
    from scripts.game_data.memorypack.skill_root_buff_input_sources import derive_buff_input
    from scripts.game_data.memorypack.skill_root_assign_pair_lists import derive as list_source
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_shared_sequence_sources import selected_inputs,_selected_wrapper
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    selected_inputs(pins);parent=derive_buff_input(image,pins);join,=parent['requiredChildJoins']
    collection=list_source(image,pins,typed_request=join['typedRequest'],
        call_target=image.pe.image_base+join['sourceTargetRva'])
    wrapper=_selected_wrapper(image,WRAPPER)
    adapter=derive_adapter(image,pins,parent['registeredPair'],wrapper)
    clones=ec.clone_facts(image,pins);cap=bind_components(pins,parent,collection,adapter,clones)
    caps=dict(collection['capabilities']);caps['skill-root-buff-input']=cap
    return json.loads(json.dumps(dict(schema='endfield.skill-root-buff-input-components.v1',
        nativeInputs=pins,status='validated-conditional-components',capabilities=caps,
        proof=dict(parent=parent,assignPairList=collection,referenceAdapter=adapter,referenceClones=clones),
        evidenceBoundary=dict(exact='BuffInput MC3/FF/new source and inherited cached holder/getter/setter semantics, exact named reference adapter/GetValue linkage and independent positive AssignPair value40 collection/child sources.',
            conditional=__doc__,structuralOnly='Stored authored buff and blackboard assignment configuration.',
            unresolved=['BuffInputBase concrete sibling/union composition','independent enclosing list/root framing','runtime selection','whole SkillData/physical EOF']))))


def derive_list(image,pins,*,typed_request,call_target,count_limit=10000):
    """Compose one independent actual List<BuffInput> parent with its child."""
    from scripts.game_data.memorypack.skill_cost_data_list_sources import derive_reference_list_component
    need('bounded-reference-list-count',True,type(count_limit)is int and 0<=count_limit<=10000)
    if count_limit>17:
        from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_induction
        parent=reference_induction(image,pins,typed_request=typed_request,call_target=call_target,
            element_type=VALUE,count_limit=count_limit)
        witness=parent['witnessComponent']
    else:
        parent=derive_reference_list_component(image,pins,typed_request=typed_request,call_target=call_target,
            element_type=VALUE,count_limit=count_limit)
        witness=parent
    child=derive(image,pins)
    need('same-reference-list-child-type',VALUE,parent['elementType'])
    need('exact-parent-closed-type',LIST,typed_request['methodArguments'][0])
    cap=dict(elementType=VALUE,elementValueType=False,closedListType=LIST,collectionCounts=[-1,0],
        positiveCountsAdmitted=count_limit>0,countLimit=count_limit,nullable=True,
        elementCapability='skill-root-buff-input',elementGrammarAdmitted=True,
        packableReaderMethodDefinition=typed_request['methodSpec'][0],packableReaderTargetRva=witness['callTargetRva'],
        wholeSkillDataAdmitted=False)
    caps=dict(child['capabilities']);caps['skill-root-buff-input-list']=cap
    return dict(schema='endfield.skill-root-buff-input-list.v1',nativeInputs=pins,
        status='validated-conditional-components',capabilities=caps,proof=dict(parent=parent,child=child),
        evidenceBoundary=dict(exact='Actual selected List<BuffInput> typed parent, signed count/callback/Add and exact nominal positive/FF reference child.',
            conditional=__doc__,structuralOnly='Stored buff configuration list.',
            unresolved=['independent enclosing root/record framing','runtime selection','whole SkillData/physical EOF']))

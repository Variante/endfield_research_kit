"""Positive BuffInputBase short union with independently complete concrete children.

The actual generated base formatter reads only tags0/1 and canonical FF on the
proved selected paths. Each positive caller is its exact ReadPackable<Concrete
Wrapper>, followed by the separately proved inherited base-interface GetValue
reading holder16. Concrete BuffInput cache24 and CreateBuffActionInput cache32,
factories/setters and their independent AssignPair value40 list/child grammars
must all compose. No concrete Original adapter is borrowed for the direct
wrapper caller. Create's capability explicitly excludes ordinary Original
ReadValue admission. The outer actual root ReadValue bridge and canonical base
adapter are separately joined; runtime callback/provider/inflation choice and
unselected existing-output/reserved/refill paths remain conditional/unresolved.
This is stored structural configuration, with no root/physical EOF admission.
"""
import json

from scripts.game_data.memorypack.skill_root_assign_pair_sources import need

TYPE='Beyond.Gameplay.Core.BuffInputBase'
BASE='Beyond.Gameplay.Core.BuffInput'
CREATE='Beyond.Gameplay.Core.CreateBuffActionInput'
CAPABILITY='skill-root-buff-input-base-positive'
CREATE_CAPABILITY='skill-root-create-buff-action-input'
ROUTES=(
    (0,BASE,'Beyond.MemoryPack.Beyond_Gameplay_Core_BuffInputForMemoryPack','skill-root-buff-input'),
    (1,CREATE,'Beyond.MemoryPack.Beyond_Gameplay_Core_CreateBuffActionInputForMemoryPack',CREATE_CAPABILITY),
)
CREATE_ORDER=[dict(fieldName=n,kind=k,childCapability=c)for n,k,c in(
    ('assignBlackboard','bool',None),('assignItems','value-list','skill-root-assign-pair-list'),
    ('buffId','pooled-string','byte-payload'),('buffIdKey','pooled-string','byte-payload'),('readIdFromBlackboard','bool',None))]


def bind_concrete_children(pins,union,base,create,collection):
    for role,component in(('base',base),('create',create),('collection',collection)):
        need('same-union-child-pins:'+role,pins,component['nativeInputs'])
    need('exact-base-union',TYPE,union['typeName'])
    need('literal-base-union-admission-flags',True,all(type(union.get(k))is bool for k in(
        'baseGetterSemanticsAdmitted','concreteGetterSemanticsAdmitted','concreteFactorySemanticsAdmitted','concreteChildGrammarAdmitted','wholeUnionAdmitted')))
    need('base-only-source-admission',(True,False,False,False,False),tuple(union.get(k)for k in(
        'baseGetterSemanticsAdmitted','concreteGetterSemanticsAdmitted','concreteFactorySemanticsAdmitted','concreteChildGrammarAdmitted','wholeUnionAdmitted')))
    expected=[(tag,name,wrapper)for tag,name,wrapper,_ in ROUTES]
    actual=[(r['tag'],r['wrappedType'],r['wrapperName'])for r in union['programs']]
    need('exact-two-concrete-routes',expected,actual)
    need('literal-short-route-tags',True,all(type(r['tag'])is int for r in union['programs']))
    need('separate-child-source-admission',True,all(r['concreteGrammarAdmitted']is False for r in union['programs']))
    need('exact-Create-child',(CREATE,ROUTES[1][2]),(create['typeName'],create['wrapperName']))
    need('Create-complete-selected-MC5-paths',[5,5,None,None,5,None,None],
        [p['memberCount']for p in create['programs']])
    need('same-inherited-BuffInput-source',base['proof']['parent'],create['inheritedBuffInput'])
    join,=create['requiredChildJoins'];need('Create-own-assignItems','assignItems',join['fieldName'])
    cap=collection['capabilities']['skill-root-assign-pair-list']
    need('Create-actual-list-method',join['typedRequest']['methodSpec'][0],cap['packableReaderMethodDefinition'])
    need('Create-actual-list-target',join['sourceTargetRva'],cap['packableReaderTargetRva'])
    for key in('skill-root-assign-pair','skill-root-assign-pair-list'):
        need('same-independent-assignment-grammar:'+key,base['capabilities'][key],collection['capabilities'][key])
    create_cap=dict(typeName=CREATE,wrapperName=ROUTES[1][2],memberCount=5,nullable=True,
        nullAdmitted=True,nullMarker=255,wholeGrammarAdmitted=True,orderedReads=CREATE_ORDER,
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        generatedWrapperOnly=True,ordinaryOriginalReadValueAdmitted=False,
        callbackSelectionConditional=True,wholeSkillDataAdmitted=False)
    routes=[dict(tag=tag,wrappedType=name,wrapperName=wrapper,childCapability=child)for tag,name,wrapper,child in ROUTES]
    return create_cap,routes


def derive(image,pins):
    from scripts.game_data.memorypack.current_reference_union_sources import derive as union_source
    from scripts.game_data.memorypack.skill_root_buff_input_components import derive as base_source
    from scripts.game_data.memorypack.skill_root_create_buff_input_sources import derive as create_source
    from scripts.game_data.memorypack.skill_root_assign_pair_lists import derive as list_source
    from scripts.game_data.memorypack.skill_root_prefix_sources import derive as prefix_source
    from scripts.game_data.memorypack.skill_shared_sequence_sources import selected_inputs
    selected_inputs(pins);base=image.pe.image_base
    parent=union_source(image,pins,families=['BuffInputBase']);union=parent['families']['BuffInputBase']
    ordinary=base_source(image,pins);create=create_source(image,pins);join,=create['requiredChildJoins']
    collection=list_source(image,pins,typed_request=join['typedRequest'],call_target=base+join['sourceTargetRva'])
    create_cap,routes=bind_concrete_children(pins,union,ordinary,create,collection)
    prefix=prefix_source(image,pins);bridge=prefix['proof']['buffInputNull']
    need('same-current-base-pair',bridge['pair'],union['pair'])
    need('same-current-base-canonical-adapter',bridge['canonicalRegistration']['pointer']-base,
        union['adapter']['canonicalRoutes']['symbolRvas']['main'])
    event=prefix['proof']['program']['orderedFields'][3]
    usage=prefix['proof']['contexts']['4']
    need('actual-root4-type',(TYPE,TYPE),(usage['methodArguments'][0],bridge['typeName']))
    need('actual-root4-ReadValue-method',usage['methodSpec'][0],bridge['referenceReaderMethodDefinition'])
    need('actual-root4-ReadValue-target',event['sourceTarget']-base,bridge['referenceReaderTargetRva'])
    cap=dict(typeName=TYPE,nullable=True,nullMarker=255,nullAdmitted=True,wholeGrammarAdmitted=True,
        routes=routes,baseGetterSemanticsProved=True,concreteChildGrammarsProved=True,
        referenceReaderMethodDefinition=bridge['referenceReaderMethodDefinition'],referenceReaderTargetRva=bridge['referenceReaderTargetRva'],
        supportedShortTags=[0,1],extendedTagsAdmitted=False,reservedMarkersAdmitted=False,
        callbackSelectionConditional=True,wholeSkillDataAdmitted=False)
    caps=dict(ordinary['capabilities']);caps[CREATE_CAPABILITY]=create_cap;caps[CAPABILITY]=cap
    return json.loads(json.dumps(dict(schema='endfield.skill-root-buff-input-union.v1',nativeInputs=pins,
        status='validated-conditional-components',capabilities=caps,
        proof=dict(union=parent,buffInput=ordinary,createBuffInput=create,createAssignPairList=collection,
            rootPrefix=prefix,root4ReadValueBridge=bridge['readerProgram']),
        evidenceBoundary=dict(exact='Current nominal root4 reference bridge, canonical base adapter, exact generated short-tag0/1 and FF source, inherited base holder/interface conversion and both complete concrete MC3/MC5/FF/factory/cache/setter plus positive AssignPair child/list compositions.',
            conditional=__doc__,structuralOnly='Stored authored buff and blackboard configuration.',
            unresolved=['runtime formatter/cache/default/inflation choice','existing-output alternatives and reserved/refill paths','whole root/physical EOF']))))

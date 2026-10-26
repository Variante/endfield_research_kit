"""Two current AbilityCondition routes with concrete source-owned grammars.

The base short-tag/FF caller and canonical adapter independently own the actual
ReadPackable<ConcreteWrapper> and inherited interface/holder16 conversion. Each
concrete complete generated reader separately proves new/existing/FF frames,
typed construction, cache24/getter/setter coherence and its exact enum32 plus
strong BlackboardDouble child. No unused concrete Original adapter is admitted.
The optional list entry owns its actual closed count/loop/Add/induction source.
Coherent selected runtime callbacks, normal helpers/allocations, disabled GC,
selected exported pool and disjoint buffered storage remain conditions. Stored
conditions establish neither runtime predicates nor root/whole owner/EOF.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

TYPE='Beyond.Gameplay.Core.Abilities.Condition.ConditionBase'
CAPABILITY='skill-root-ability-condition'
LIST_CAP='skill-root-ability-condition-list'
DOUBLE='skill-blackboard-double'
PREFIX='Beyond.Gameplay.Core.Abilities.Condition.'
ROUTES=((0,PREFIX+'CheckAttribute','skill-root-check-attribute'),(1,PREFIX+'CheckCurHpRatio','skill-root-check-cur-hp-ratio'))
DECLARATIONS={
 PREFIX+'CheckAttribute':(('attributeType',PREFIX+'CheckAttribute+AttributeType'),('compareType','Beyond.CompareType'),('value','Beyond.Blackboard+BlackboardDouble')),
 PREFIX+'CheckCurHpRatio':(('compareType','Beyond.CompareType'),('value','Beyond.Blackboard+BlackboardDouble')),
}


def bind_union(union,children):
    need('Condition-literal-base-only-flags',True,union.get('baseGetterSemanticsAdmitted')is True
        and all(union.get(k)is False for k in('concreteGetterSemanticsAdmitted','concreteFactorySemanticsAdmitted','concreteChildGrammarAdmitted','wholeUnionAdmitted')))
    need('Condition-exact-base-type',TYPE,union['typeName'])
    need('Condition-exact-two-routes',[(tag,typ)for tag,typ,_ in ROUTES],[(r['tag'],r['wrappedType'])for r in union['programs']])
    routes=[]
    for route,(tag,typ,capability)in zip(union['programs'],ROUTES,strict=True):
        child=children[typ];cap=child['capability'];source=child['source']
        need('Condition-literal-short-route',True,type(route['tag'])is int and route['concreteGrammarAdmitted']is False)
        need('Condition-source-exact-wrapper',route['wrapperName'],source['wrapperName'])
        need('Condition-wrapper-only-child',True,cap['generatedWrapperOnly']is True
            and cap['ordinaryOriginalReadValueAdmitted']is False and cap['wholeGrammarAdmitted']is True
            and cap['ownConcreteGetterSemanticsProved']is True and cap['ownConcreteFactorySemanticsProved']is True)
        usage=route['typedRequest']
        need('Condition-actual-concrete-request',('MemoryPack.MemoryPackReader','ReadPackable',[],[source['wrapperName']]),
            tuple(usage.get(k)for k in('typeName','methodName','classArguments','methodArguments')))
        need('Condition-same-owned-concrete-reader',source['method'],source['lifecycle']['readerMethod'])
        routes.append(dict(tag=tag,wrappedType=typ,wrapperName=source['wrapperName'],childCapability=capability))
    return routes


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.generated_reader_sources import derive_many
    from scripts.game_data.memorypack.current_reference_union_sources import derive as union_source
    from scripts.game_data.memorypack.skill_blackboard_double_sources import derive as double_source
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    _publication_gate(image,pins)
    wrappers=[]
    for _,typ,_ in ROUTES:
        wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==typ];wrappers.append(wrapper.name)
    sources=derive_many(image,pins,wrappers);double=double_source(image,pins)
    children={};caps=dict(double['capabilities'])
    for result,(_,typ,name)in zip(sources['owners'],ROUTES,strict=True):
        need('Condition-complete-concrete-source:'+typ,'complete-reader-source-proved',result['status'])
        source=result['proof'];reads=source['orderedSourceReads']
        need('Condition-finite-named-members',list(DECLARATIONS[typ]),[(r['fieldName'],r['declaredType'])for r in reads])
        requests={r['memberIndex']:derive_typed_usage_context(image,r['context']['instructionRva'],label='Condition.child')
            for r in reads if r['declaredType']=='Beyond.Blackboard+BlackboardDouble'}
        compiled,pending=compile_member_program(source,pins,wrapper_name=source['wrapperName'],type_name=typ,value4={},
            references={'Beyond.Blackboard+BlackboardDouble':(DOUBLE,'record',DOUBLE)},
            reference_children={'Beyond.Blackboard+BlackboardDouble':double},typed_requests=requests)
        need('Condition-all-child-joins-complete',[],pending)
        order=[dict(fieldName=n,kind='record'if t=='Beyond.Blackboard+BlackboardDouble'else'enum32',
            childCapability=DOUBLE if t=='Beyond.Blackboard+BlackboardDouble'else None)for n,t in DECLARATIONS[typ]]
        need('Condition-finite-compiled-program',[(n,'record'if t=='Beyond.Blackboard+BlackboardDouble'else'scalar32',
            DOUBLE if t=='Beyond.Blackboard+BlackboardDouble'else None)for n,t in DECLARATIONS[typ]],
            [(r['fieldName'],r['kind'],r['childCapability'])for r in compiled['reads']])
        cap=dict(typeName=typ,wrapperName=source['wrapperName'],memberCount=len(order),nullable=True,nullMarker=255,
            nullAdmitted=True,wholeGrammarAdmitted=True,orderedReads=order,generatedWrapperOnly=True,
            ordinaryOriginalReadValueAdmitted=False,ownConcreteGetterSemanticsProved=True,
            ownConcreteFactorySemanticsProved=True,callbackSelectionConditional=True,wholeSkillDataAdmitted=False)
        caps[name]=cap;children[typ]=dict(source=source,compiled=compiled,capability=cap)
    parent=union_source(image,pins,families=['AbilityCondition']);union=parent['families']['AbilityCondition']
    routes=bind_union(union,children);reference=reference_reader_abi(image,pins)
    caps[CAPABILITY]=dict(typeName=TYPE,nullable=True,nullMarker=255,nullAdmitted=True,wholeGrammarAdmitted=True,
        supportedShortTags=[0,1],extendedTagsAdmitted=False,reservedMarkersAdmitted=False,routes=routes,
        baseGetterSemanticsProved=True,concreteChildGrammarsProved=True,callbackSelectionConditional=True,
        **{k:reference[k]for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')},wholeSkillDataAdmitted=False)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-root-condition-components.v1',nativeInputs=pins,
        status='validated-conditional-components',capabilities=caps,requiredExternalCapabilities=['byte-payload'],
        proof=dict(union=parent,children=children,blackboardDouble=double,referenceAbi=reference),
        evidenceBoundary=dict(exact='Finite AbilityCondition tag0/1/FF source and base adapter/interface conversion, concrete CheckAttribute/CheckCurHpRatio complete lifecycle/source and named enum32/strong BlackboardDouble child joins.',
            conditional=__doc__,structuralOnly='Stored condition configuration.',unresolved=['runtime predicate/selection','enclosing owner/EOF']))))


def derive_list(image,pins,*,typed_request,call_target,count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as list_source
    child=derive(image,pins)
    collection=list_source(image,pins,typed_request=typed_request,call_target=call_target,element_type=TYPE,count_limit=count_limit)
    witness=collection['witnessComponent'];caps=dict(child['capabilities'])
    caps[LIST_CAP]=dict(elementType=TYPE,elementValueType=False,closedListType='System.Collections.Generic.List`1<'+TYPE+'>',
        collectionCounts=[-1,0],nullable=True,countLimit=count_limit,positiveCountsAdmitted=True,
        elementCapability=CAPABILITY,elementGrammarAdmitted=True,
        packableReaderMethodDefinition=witness['typedRequest']['methodSpec'][0],packableReaderTargetRva=witness['callTargetRva'],
        callbackSelectionConditional=True,wholeSkillDataAdmitted=False)
    _publication_gate(image,pins)
    return dict(schema='endfield.skill-root-condition-list-components.v1',nativeInputs=dict(pins),status='validated-conditional-components',
        capabilities=caps,proof=dict(child=child,collection=collection),requiredExternalCapabilities=['byte-payload'],
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=child['evidenceBoundary'])

"""Ordinary GlobalBuffInput with its distinct GlobalBuffId value child.

The complete MC3/new/existing/FF caller has a plain holder16 and no inherited
BuffInput cache. Its bool, actual closed AssignPair40 list and typed managed8
GlobalBuffId return each have separate source and wire owners. GlobalBuffId's
MC1/pool4 bytes are not BuffInput's directly stored pooled string. The own
Original ordinary adapter/GetValue and actual reference Reader are freshly
joined; the source-proved constructor is required to return normally. Ready
compatible contexts/callbacks, normal typed zeroed allocations/constructor
effects, disabled collector and stable disjoint storage remain conditions.
Runtime global-buff effects/provider selection, enclosing action/list/union,
growth/refill and whole SkillData/physical EOF remain unresolved.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

SCHEMA='endfield.skill-global-buff-input-sources.v1'
TYPE='Beyond.Gameplay.Core.GlobalBuffInput'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_GlobalBuffInputForMemoryPack'
CAPABILITY='skill-global-buff-input'
GLOBAL='Beyond.Gameplay.Core.GlobalBuffId'
GLOBAL_CAP='skill-global-buff-id'
ASSIGN_LIST='System.Collections.Generic.List`1<Beyond.Blackboard+AssignPair>'
ASSIGN_CAP='skill-root-assign-pair-list'
LIST='System.Collections.Generic.List`1<'+TYPE+'>'
LIST_CAPABILITY='skill-action-global-buff-input-list'
MEMBERS=[('assignBlackboard','bool'),('assignItems',ASSIGN_LIST),('globalBuffId',GLOBAL)]
ORDER=[dict(fieldName=n,kind=k,childCapability=c)for n,k,c in(
    ('assignBlackboard','bool',None),('assignItems','value-list',ASSIGN_CAP),('globalBuffId','record',GLOBAL_CAP))]


def require_source(source,pins):
    """Finite current source boundary, independent of same-size child aliases."""
    need('GlobalInput-complete-selected-source',True,source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==pins and(source.get('wrappedType'),source.get('wrapperName'))==(TYPE,WRAPPER)
        and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False
        and source.get('wholeOwnerAdmitted')is False)
    need('GlobalInput-exact-named-members',MEMBERS,[(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])])
    life=source.get('lifecycle',{})
    need('GlobalInput-plain-owned-holder16',True,life.get('directHolderMode')is True
        and life.get('typedCache')is None and life.get('baseHolder')==[WRAPPER,TYPE,16])
    paths=source.get('programs',[])
    need('GlobalInput-four-complete-selected-frames',True,len(paths)==4 and all(type(p.get('existing'))is bool
        and type(p.get('wrapperNull'))is bool and p.get('frame',{}).get('entryRspRestored')is True
        and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths)
        and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)})


def bind_program(compiled):
    need('GlobalInput-literal-MC3',True,type(compiled.get('memberCount'))is int and compiled['memberCount']==3)
    expected=[dict(memberIndex=i,fieldName=n,kind=k,childCapability=c)for i,(n,k,c)in enumerate((
        ('assignBlackboard','bool-byte',None),('assignItems','root-collection',ASSIGN_CAP),
        ('globalBuffId','root-record',GLOBAL_CAP)))]
    need('GlobalInput-complete-distinct-child-program',expected,compiled.get('reads'))
    need('GlobalInput-literal-member-indices',True,all(type(r.get('memberIndex'))is int for r in compiled['reads']))
    need('GlobalInput-exact-child-requirements',sorted([ASSIGN_CAP,GLOBAL_CAP]),compiled.get('requiredCapabilities'))
    return ORDER


def _derive_on_source(image,pins,source):
    """Internal composition of a freshly derived concrete source on this image."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.skill_root_assign_pair_lists import derive as list_source
    from scripts.game_data.memorypack.skill_action_managed_value_bindings import bind,TYPES
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.pointer_param import leaf
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    _publication_gate(image,pins);require_source(source,pins);reads=source['orderedSourceReads'];requests={}
    for read in reads:
        if read.get('context')is not None:
            requests[read['memberIndex']]=derive_typed_usage_context(image,read['context']['instructionRva'],label='skillGlobalBuffInput')
    listing=list_source(image,pins,typed_request=requests[1],call_target=image.pe.image_base+reads[1]['sourceTargetRva'])
    global_source=source['sourceScope']['managedValueSources']['2']['proof']['childSource']
    need('GlobalInput-fresh-own-Global-source',True,global_source.get('schema')=='endfield.skill-global-buff-id-sources.v1'
        and global_source.get('status')=='validated-conditional-global-buff-id'and global_source.get('nativeInputs')==pins
        and global_source.get('typeName')==GLOBAL)
    compiled,pending=compile_member_program(source,pins,wrapper_name=WRAPPER,type_name=TYPE,value4={},
        typed_requests=requests,collections={ASSIGN_LIST:(ASSIGN_CAP,'root-collection',ASSIGN_CAP)},
        collection_children={1:listing},typed_values={GLOBAL:TYPES[GLOBAL]},value_children={2:global_source},value_binder=bind)
    need('GlobalInput-no-unproved-child',[],pending);order=bind_program(compiled)
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==WRAPPER]
    need('GlobalInput-actual-owned-wrapper',TYPE,wrapper.wrapped_type)
    pair=derive_pair(image,TYPE,WRAPPER);adapter=derive_adapter(image,pins,pair,wrapper)
    need('GlobalInput-same-source-owned-getter',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
    need('GlobalInput-same-source-owned-reader',source['method'],adapter['pairForwarder']['readerMethod'])
    getter=leaf(image,image.pe.image_base+adapter['getterMethod'][3],['488B4110','C3'])
    readers=reference_reader_abi(image,pins)
    cap=dict(typeName=TYPE,wrapperName=WRAPPER,memberCount=3,nullable=True,nullMarker=255,nullAdmitted=True,
        wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,ownConcreteGetterSemanticsProved=True,
        ownConcreteFactorySemanticsProved=True,completeSourceOwnedProgram=True,orderedReads=order,
        referenceReaderMethodDefinition=readers['referenceReaderMethodDefinition'],referenceReaderTargetRva=readers['referenceReaderTargetRva'],
        callbackSelectionConditional=True,wholeOwnerAdmitted=False)
    caps={**listing['capabilities'],**global_source['capabilities'],CAPABILITY:cap}
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-global-buff-input',nativeInputs=pins,
        capabilities=caps,requiredExternalCapabilities=['byte-payload'],proof=dict(source=source,compiled=compiled,
            typedRequests=requests,assignPairList=listing,globalBuffId=global_source,pair=pair,adapter=adapter,getter=getter,referenceReaders=readers),
        wholeOwnerAdmitted=False,evidenceBoundary=dict(exact='Complete nominal MC3 source/new/existing/FF/frame, bool, actual closed AssignPair40 positive list, distinct typed GlobalBuffId managed8/MC1 child, ordinary adapter/GetValue and actual reference Reader.',
            conditional=__doc__,structuralOnly='Stored global buff input and blackboard assignments.',
            unresolved=['enclosing action/list/union/root/EOF','runtime global buff application/provider choice','nonempty reuse/growth/refill']))))


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.generated_reader_sources import derive_many
    _publication_gate(image,pins)
    result,=derive_many(image,pins,[WRAPPER])['owners']
    if result.get('status')!='complete-reader-source-proved':
        raise ValueError('skillGlobalBuffInput.complete-reader:'+str(result)[:2400])
    return _derive_on_source(image,pins,result['proof'])


def _derive_list_on_child(image,pins,child,*,typed_request,call_target,count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as list_source
    from scripts.game_data.memorypack.skill_action_reference_list_sources import compose_reference_list,bind_parent_request,bind_reference_reader
    _publication_gate(image,pins);need('GlobalInput-list-exact-closed-nominal',[LIST],typed_request.get('methodArguments'))
    listing=list_source(image,pins,typed_request=typed_request,call_target=call_target,element_type=TYPE,count_limit=count_limit)
    parent=bind_parent_request(listing,typed_request,call_target,image.pe.image_base,label='global-buff-input-list')
    reader=bind_reference_reader(image,pins,listing,child,element_capability=CAPABILITY,label='global-buff-input-list')
    cap=compose_reference_list(listing,child,pins,element_type=TYPE,element_capability=CAPABILITY,label='global-buff-input-list')
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-global-buff-input-list.v1',status='validated-conditional-global-buff-input-list',
        nativeInputs=pins,capabilities={**child['capabilities'],LIST_CAPABILITY:cap},requiredExternalCapabilities=[CAPABILITY],
        proof=dict(collection=listing,child=child,actualParentRequestBinding=parent,listElementReadValueBinding=reader),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
            exact='Actual closed List<GlobalBuffInput> MethodSpec/E8, independent signed count/callback/Add/induction and exact ordinary nominal child.',
            conditional=__doc__,structuralOnly='Stored global buff input collection.',
            unresolved=['enclosing action/union/root/EOF','runtime callback/provider choice','nonempty reuse/growth/refill']))))


def derive_list(image,pins,*,typed_request,call_target,count_limit=10000):
    return _derive_list_on_child(image,pins,derive(image,pins),typed_request=typed_request,call_target=call_target,count_limit=count_limit)

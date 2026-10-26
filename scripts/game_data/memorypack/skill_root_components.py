"""Current root49 caller/child composition with an explicit finite open tail.

Every source-owned root field is listed, but a field is admitted only after its
actual nominal child target/MethodSpec joins an independently proved component.
The contiguous grammar covers members1 through48 when independently proved
SequenceActionData and TargetSettings capabilities match their exact source
identities. The complete selected existing-root native return is proved by
the tail owner independently of those grammars. Whole SkillData still requires
all49 fields, exact physical EOF and the operation's source/pool/native exit
checks. New/null root, runtime provider choice and unproved descendants remain
unresolved; normal coherent selected contexts and disjoint buffered storage
are conditions, never inferred from a field name or managed width.
"""
import json

from scripts.game_data.memorypack import scalar_param_native as scalar
from scripts.game_data.memorypack.skill_root_tail_sources import DECLARATIONS

LABEL='skillRootComponents'
REFERENCE_CAPS={
 'Beyond.Gameplay.AttributeModifierData':'skill-root-attribute-modifier-data',
 'Beyond.Gameplay.Core.CastData':'skill-root-cast-data',
 'Beyond.Gameplay.Core.SequenceActionData':'SequenceActionData',
 'Beyond.Gameplay.Core.GameplayTagList':'skill-root-gameplay-tag-list',
 'Beyond.Gameplay.Core.BuffFindSettings':'skill-root-buff-find-settings',
 'Beyond.Gameplay.Core.GameplayTagQuery':'skill-root-gameplay-tag-query',
 'Beyond.Gameplay.Core.SwitchToBuffConfig':'skill-root-switch-to-buff-config',
}
LIST_CAPS={
 'System.Collections.Generic.List`1<Beyond.Gameplay.Core.BuffInput>':'skill-root-buff-input-list',
 'System.Collections.Generic.List`1<Beyond.Gameplay.Core.BuffId>':'skill-root-buff-id-list',
 'System.Collections.Generic.List`1<Beyond.Gameplay.Core.ToggleBuffData>':'skill-root-toggle-buff-list',
 'System.Collections.Generic.List`1<Beyond.Gameplay.Core.UIRangeHintData>':'skill-root-ui-range-hint-list',
}


def need(check,expected,actual):scalar.need(LABEL,check,expected,actual)


def root_reads():
    reads=[dict(memberIndex=i,fieldName=n,kind=k,childCapability=c)for i,n,k,c in(
        (1,'aiExclusiveFrame','int32',None),(2,'attackRangeType','enum32',None),
        (3,'blackboard','value-list','skill-root-data-pair-list-positive'),
        (4,'buffInputBase','record-union','skill-root-buff-input-base-positive'))]
    for index,name,typename,kind in DECLARATIONS:
        child=None
        if kind in('reference','hidden16-inline'):
            child=REFERENCE_CAPS[typename];kind='sequence-profile'if typename=='Beyond.Gameplay.Core.SequenceActionData'else'record'
        elif kind=='list':child=LIST_CAPS[typename];kind='record-list'
        elif kind=='string':kind='pooled-string';child='byte-payload'
        else:kind={'boolean':'bool-byte','single':'single-bits','vector3-inline':'vector3-raw12'}.get(kind,kind)
        reads.append(dict(memberIndex=index,fieldName=name,kind=kind,childCapability=child))
    need('complete-root-member-order',list(range(1,49)),[r['memberIndex']for r in reads])
    return reads


def bind_root_list(pins,event,usage,component,*,capability,base):
    need('same-root-list-pins',pins,component['nativeInputs'])
    cap=component['capabilities'][capability]
    need('root-typed-list-name',event['typeName'],cap['closedListType'])
    need('actual-root-list-request',('MemoryPack.MemoryPackReader','ReadPackable',[],[event['typeName']]),
        tuple(usage[k]for k in('typeName','methodName','classArguments','methodArguments')))
    need('actual-root-list-method',usage['methodSpec'][0],cap['packableReaderMethodDefinition'])
    need('actual-root-list-target',event['sourceCall']['target']-base,cap['packableReaderTargetRva'])
    return dict(memberIndex=event['memberIndex'],fieldName=event['fieldName'],capability=capability,
        methodDefinition=cap['packableReaderMethodDefinition'],sourceTargetRva=cap['packableReaderTargetRva'],
        exactClosedType=cap['closedListType'])


def bind_root_reference(pins,event,usage,component,*,capability,base):
    from scripts.game_data.memorypack.skill_root_child_bindings import bind_read_value
    row=bind_read_value(pins,dict(fieldName=event['fieldName'],typeName=event['typeName'],
        sourceTargetRva=event['sourceCall']['target']-base,typedRequest=usage),component,capability)
    return dict(memberIndex=event['memberIndex'],**row)


def bind_external_reference(event,usage,reference,*,base):
    """Declare the actual nominal/reader join without admitting an external child."""
    need('finite-external-root-reference',(34,'Beyond.Gameplay.Core.SequenceActionData'),
        (event['memberIndex'],event['typeName']))
    need('literal-external-reader-identity',True,all(type(reference.get(k))is int and reference[k]>0
        for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')))
    need('actual-external-reference-request',('MemoryPack.MemoryPackReader','ReadValue',[],[event['typeName']]),
        tuple(usage.get(k)for k in('typeName','methodName','classArguments','methodArguments')))
    need('actual-external-reference-method',reference['referenceReaderMethodDefinition'],usage['methodSpec'][0])
    need('actual-external-reference-call-target',reference['referenceReaderTargetRva'],event['sourceCall']['target']-base)
    return dict(typeName=event['typeName'],**{k:reference[k]
        for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')})


def bind_root_query(pins,event,usage,query,provider,*,base):
    """Join the root's actual inline provider and fixed Query16 dispatcher."""
    need('same-root-Query-pins',pins,query['nativeInputs'])
    need('exact-root-Query-field',(42,'Beyond.Gameplay.Core.GameplayTagQuery'),(event['memberIndex'],event['typeName']))
    cap=query['capabilities']['skill-root-gameplay-tag-query']
    need('complete-root-Query-grammar',True,cap.get('wholeGrammarAdmitted')is True)
    need('root-Query-nominal',event['typeName'],cap['typeName'])
    need('root-Query-typed-request',('MemoryPack.MemoryPackReader','ReadValue',[],[event['typeName']]),
        tuple(usage.get(k)for k in('typeName','methodName','classArguments','methodArguments')))
    need('root-Query-literal-identities',True,all(type(cap.get(k))is int and cap[k]>0
        for k in('valueReaderMethodDefinition','valueDispatcherTargetRva')))
    need('root-Query-reader-and-actual-dispatch',(usage['methodSpec'][0],event['sourceCall']['target']-base),
        (cap['valueReaderMethodDefinition'],cap['valueDispatcherTargetRva']))
    program=provider['providerProgram'];symbols=provider['providerSymbolRvas']
    need('root-Query-exact-static-cells',(program['providerClassCell'],program['typeClassCell']),
        (event['providerClassCell'],event['typeClassCell']))
    for field,name in(('typeFromHandle','typeHandle'),('backend','backend'),('resolveClass','indexed'),('predicate','assignable')):
        need('root-Query-inline-helper:'+field,symbols[name],event[field]['target']-base)
    return dict(memberIndex=42,fieldName=event['fieldName'],typeName=cap['typeName'],
        capability='skill-root-gameplay-tag-query',readerMethodDefinition=cap['valueReaderMethodDefinition'],
        actualDispatcherTargetRva=cap['valueDispatcherTargetRva'],inlineProviderBindingProved=True)


def derive(image,pins):
    """Reprove the caller and the currently closed contiguous child prefix."""
    from scripts.game_data.memorypack.skill_root_prefix_sources import derive as prefix_source
    from scripts.game_data.memorypack.skill_root_tail_sources import derive as tail_source
    from scripts.game_data.memorypack.skill_root_value_lists import derive as pair_lists
    from scripts.game_data.memorypack.skill_root_buff_input_components import derive_list as buff_lists
    from scripts.game_data.memorypack.skill_root_buff_input_union import derive as buff_union
    from scripts.game_data.memorypack.skill_root_attribute_components import derive as attribute_source
    from scripts.game_data.memorypack.skill_root_cast_components import derive as cast_source
    from scripts.game_data.memorypack.skill_root_gameplay_tag_list_components import derive as tags_source
    from scripts.game_data.memorypack.skill_root_buff_find_components import derive as find_source
    from scripts.game_data.memorypack.skill_root_buff_id_lists import derive as id_list_source
    from scripts.game_data.memorypack.skill_root_switch_components import derive as switch_source
    from scripts.game_data.memorypack.skill_root_toggle_components import derive_list as toggle_lists
    from scripts.game_data.memorypack.skill_root_ui_range_components import derive_list as ui_lists
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.memorypack.buff_ptr_sources import _typed_context
    prefix=prefix_source(image,pins);tail=tail_source(image,pins,prefix)
    pair=pair_lists(image,pins,prefix=prefix)
    event=tail['program']['orderedFields'][0]
    need('first-tail-field',(5,'buffs'),(event['memberIndex'],event['fieldName']))
    buffs=buff_lists(image,pins,typed_request=tail['contexts']['buffs'],call_target=event['sourceCall']['target'])
    union=buff_union(image,pins)
    attributes=attribute_source(image,pins);cast=cast_source(image,pins)
    tags=tags_source(image,pins);find=find_source(image,pins)
    id_event=next(e for e in tail['program']['orderedFields']if e['memberIndex']==40)
    ids=id_list_source(image,pins,typed_request=tail['contexts'][id_event['fieldName']],call_target=id_event['sourceCall']['target'])
    switch=switch_source(image,pins,buffs=buffs)
    toggle_event=next(e for e in tail['program']['orderedFields']if e['memberIndex']==46)
    toggles=toggle_lists(image,pins,typed_request=tail['contexts'][toggle_event['fieldName']],call_target=toggle_event['sourceCall']['target'],buffs=buffs)
    ui_event=next(e for e in tail['program']['orderedFields']if e['memberIndex']==47)
    ui=ui_lists(image,pins,typed_request=tail['contexts'][ui_event['fieldName']],call_target=ui_event['sourceCall']['target'])
    binding=bind_root_list(pins,event,tail['contexts']['buffs'],buffs,
        capability='skill-root-buff-input-list',base=image.pe.image_base)
    reads=root_reads();capabilities=dict(prefix['capabilities'])
    capabilities.update(pair['capabilities']);capabilities.update(buffs['capabilities'])
    for component in(union,attributes,cast,tags,find,ids,switch,toggles,ui):
        need('same-root-component-pins',pins,component['nativeInputs'])
        for name,cap in component['capabilities'].items():
            if name in capabilities:need('same-independent-root-child:'+name,capabilities[name],cap)
            capabilities[name]=cap
    reference_bindings=[]
    for index,component,cap in((10,attributes,'skill-root-attribute-modifier-data'),(11,cast,'skill-root-cast-data'),
            (38,tags,'skill-root-gameplay-tag-list'),(39,find,'skill-root-buff-find-settings'),
            (43,switch,'skill-root-switch-to-buff-config'),(45,tags,'skill-root-gameplay-tag-list')):
        event=next(e for e in tail['program']['orderedFields']if e['memberIndex']==index)
        reference_bindings.append(bind_root_reference(pins,event,tail['contexts'][event['fieldName']],component,
            capability=cap,base=image.pe.image_base))
    sequence_event=next(e for e in tail['program']['orderedFields']if e['memberIndex']==34)
    sequence_identity=bind_external_reference(sequence_event,tail['contexts'][sequence_event['fieldName']],
        cast['proof']['parentReference'],base=image.pe.image_base)
    external_identities=dict(switch['requiredExternalCapabilityIdentities'])
    need('same-root-and-Switch-Sequence-identity',sequence_identity,external_identities['SequenceActionData'])
    id_binding=bind_root_list(pins,id_event,tail['contexts'][id_event['fieldName']],ids,
        capability='skill-root-buff-id-list',base=image.pe.image_base)
    later_lists=[bind_root_list(pins,event,tail['contexts'][event['fieldName']],component,capability=capability,base=image.pe.image_base)
        for event,component,capability in((toggle_event,toggles,'skill-root-toggle-buff-list'),(ui_event,ui,'skill-root-ui-range-hint-list'))]
    query_event=next(e for e in tail['program']['orderedFields']if e['memberIndex']==42)
    query_usage=tail['contexts'][query_event['fieldName']]
    query_context=_typed_context(image,query_usage,query_event['typeName'],GenericEntries(image))
    provider_usages={}
    for role,site,key,typename in(('provider','providerUsageSite','providerClassCell','MemoryPack.MemoryPackFormatterProvider'),
            ('type','typeUsageSite','typeClassCell','System.Type')):
        u=derive_typed_usage_context(image,query_event[site]-image.pe.image_base,label=LABEL+'.Query.'+role)
        need('root-Query-named-provider-usage:'+role,(1,typename,query_event[key]-image.pe.image_base),
            (u['tag'],u['typeName'],u['usageCellRva']));provider_usages[role]=u
    query_binding=bind_root_query(pins,query_event,query_usage,find['proof']['query'],find['proof'],base=image.pe.image_base)
    last=48
    for event in tail['program']['orderedFields'][1:5]:
        need('admitted-prefix-Boolean-kind','boolean',event['kind'])
        need('same-proved-Boolean-helper',tail['primitiveSources']['boolean']['targetRva'],event['sourceCall']['target']-image.pe.image_base)
    capabilities['SkillDataContinuation']=dict(memberCount=49,startMemberIndex=1,lastMemberIndex=last,
        orderedReads=reads[:last],wholeSkillDataAdmitted=False)
    return json.loads(json.dumps(dict(schema='endfield.skill-root-components.v2',nativeInputs=pins,
        status='validated-conditional-root-prefix-components',capabilities=capabilities,orderedReads=reads,
        proof=dict(prefix=prefix,rootTail=tail,dataPair=pair,buffInput=buffs,buffInputUnion=union,rootBuffsBinding=binding,
            attributeModifiers=attributes,castData=cast,rootReferenceBindings=reference_bindings,
            gameplayTags=tags,buffFindSettings=find,buffIdList=ids,rootBuffIdBinding=id_binding,
            switchToBuff=switch,toggleBuffs=toggles,uiRangeHints=ui,rootLaterListBindings=later_lists,
            rootQueryBinding=query_binding,rootQueryContext=query_context,rootQueryProviderUsages=provider_usages,
            externalReferenceBindings=external_identities,
            externalChildGrammarAdmittedByThisComponent=False),
        lastCompleteMember=last,nextMemberIndex=last+1,completeSelectedReturnProved=True,wholeSkillDataAdmitted=False,
        requiredExternalCapabilities=['SequenceActionData','byte-payload','target-profile'],
        requiredExternalCapabilityIdentities=external_identities,
        pendingJoins=[dict(memberIndex=r['memberIndex'],fieldName=r['fieldName'],requiredCapability=r['childCapability'])
            for r in reads[last:]if r['childCapability']is not None],
        evidenceBoundary=dict(exact='Complete root49 existing caller source and native return, root fields1 through48 selected child source joins, including DataPair32, BuffInput/AssignPair40, AttributeModifier arrays, concrete BlackboardDouble/Cast/Cost, generated GameplayTag lists, BuffFind/Query/BuffId, Switch, Toggle/Condition and UIRange/SkillHint/Vector2. Sequence and TargetSettings require separately admitted grammar/lifecycle capabilities and exact nominal reader identities.',
            conditional=__doc__,structuralOnly='Stored Skill configuration; no live execution or event semantics.',
            unresolved=['external Sequence/Target source admission','root field0/action graph','new/null root','runtime selection','whole SkillData/physical EOF']))))

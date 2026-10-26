"""Finite Skill managed-value returns joined to their own wire capabilities.

BuffId and GlobalBuffId each carry a different nominal reference in managed8;
Query carries enum/padding/reference in managed16. Their actual ReadValue,
complete source-local/field transfer, named setter, reference lanes and full
caller frame are independent of MC1/pool4 or MC2/tag-array wire grammar. This
pure callable joins freshly derived components and supplies no native status.
Coherent selected callbacks, initialized nominal contexts, normal compatible
helpers, disabled collector and disjoint stable storage remain conditions.
Live callback selection, effects, enclosing action/union/root and EOF remain
unresolved. Neither managed size nor a similarly named value selects a child.
"""
from scripts.game_data.memorypack.skill_root_child_bindings import need

BUFF='Beyond.Gameplay.Core.BuffId'
GLOBAL='Beyond.Gameplay.Core.GlobalBuffId'
QUERY='Beyond.Gameplay.Core.GameplayTagQuery'
SMART='Beyond.Gameplay.Core.SmartTargetSelectSetting'
ENVELOPE='Cinemachine.CinemachineImpulseManager+EnvelopeDefinition'
TYPES={BUFF:('skill-root-buff-id','root-record','skill-root-buff-id'),
    GLOBAL:('skill-global-buff-id','root-record','skill-global-buff-id'),
    QUERY:('skill-root-gameplay-tag-query','root-record','skill-root-gameplay-tag-query'),
    SMART:('skill-smart-target-select-setting','root-record','skill-smart-target-select-setting'),
    ENVELOPE:('skill-impulse-envelope','root-record','skill-impulse-envelope')}
LAYOUTS={BUFF:(8,[['buffId','string',16,14]],[0],[]),
    GLOBAL:(8,[['id','string',16,14]],[0],[]),
    QUERY:(16,[['queryType',QUERY+'+QueryType',16,17],['tags','Beyond.Gameplay.Core.GameplayTag[]',24,29]],[8],[[4,4]])}


def require_wire_capability(component,pins,type_name,capability):
    """Finite independently proved wire scope, without generic size inference."""
    need('managed-Skill-finite-domain',True,type_name in TYPES and capability==TYPES[type_name][0])
    need('managed-Skill-wire-same-native-inputs',pins,component.get('nativeInputs'))
    cap=component.get('capabilities',{}).get(capability,{})
    if type_name==SMART:
        from scripts.game_data.memorypack.skill_smart_target_value_codec import require_capability
        return require_capability(cap)
    if type_name==ENVELOPE:
        from scripts.game_data.memorypack.skill_impulse_envelope_codec import require_capability
        return require_capability(cap)
    width=LAYOUTS[type_name][0];count=2 if type_name==QUERY else 1
    need('managed-Skill-wire-exact-nominal',type_name,cap.get('typeName'))
    need('managed-Skill-wire-literal-shape',True,all(type(cap.get(k))is int and cap[k]==v for k,v in
        (('managedBytes',width),('memberCount',count),('nullMarker',255),('nullWireBytes',1)))
        and cap.get('nullable')is True and cap.get('nullReturnsDefaultValue')is True and cap.get('wireBytes')is None)
    if type_name==QUERY:
        need('managed-Skill-Query-own-grammar',True,all(cap.get(k)is True for k in
            ('wholeGrammarAdmitted','ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved'))
            and cap.get('positiveWireBytes')is None and cap.get('orderedReads')==[
                dict(fieldName='queryType',kind='enum32',childCapability=None),
                dict(fieldName='tags',kind='unmanaged-array',childCapability='skill-root-gameplay-tag-array')])
    else:
        field='buffId'if type_name==BUFF else'id'
        need('managed-Skill-own-MC1-pool4-grammar',True,type(cap.get('positiveWireBytes'))is int and cap['positiveWireBytes']==5
            and cap.get('orderedReads')==[dict(fieldName=field,kind='pooled-string')])
        if type_name==GLOBAL:
            need('managed-Skill-Global-own-source',True,all(cap.get(k)is True for k in
                ('wholeGrammarAdmitted','ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved')))
    return cap


def bind(source,scope,read,pins,usage,component,capability):
    """Domain callback for generated_record_components' typed_values hook."""
    if read.get('declaredType')==SMART:
        from scripts.game_data.memorypack.skill_smart_target_value_bindings import bind as smart_bind
        return smart_bind(source,scope,read,pins,usage,component,capability)
    if read.get('declaredType')==ENVELOPE:
        from scripts.game_data.memorypack.skill_impulse_envelope_bindings import bind as envelope_bind
        return envelope_bind(source,scope,read,pins,usage,component,capability)
    from scripts.game_data.memorypack.generated_managed_value_components import require_transfer
    type_name=read.get('declaredType');cap=require_wire_capability(component,pins,type_name,capability)
    index=read['memberIndex'];source_context=None
    actual=scope.get('managedValueSources',{}).get(str(index),{});definition=usage.get('methodSpec',[None])[0]
    if read.get('sourceContextMode')is not None or actual.get('sourceContextMode')is not None or actual.get('contextMode')is not None:
        from scripts.game_data.memorypack.generated_managed_forwarder_components import require_source
        nested=require_source(actual,read,pins,usage)
        source_context=actual['proof']['internalContext']
    else:nested=actual
    transfer=(require_transfer(source,scope,read,pins)if source_context is None else
        require_transfer(source,scope,read,pins,source_context=source_context))
    width,fields,lanes,padding=LAYOUTS[type_name];layout=source['setters'][index]['managedValueLayout']
    need('managed-Skill-exact-current-fields-and-lanes',(width,fields,lanes,padding),tuple(layout.get(k)for k in
        ('managedBytes','fields','referenceLaneOffsets','paddingByteRanges')))
    need('managed-Skill-own-actual-ReadValue',True,actual.get('nativeInputs')==pins
        and nested.get('status')=='proved-conditional-typed-nominal-value-read'
        and actual.get('typeName')==type_name and actual.get('managedBytes')==width and actual.get('actualSourceProved')is True
        and actual.get('resultAbi')==('rax'if width==8 else'hidden-local')and actual.get('wireGrammarAdmitted')is False
        and actual.get('sourceTargetRva')==read.get('sourceTargetRva')and type(definition)is int
        and actual.get('readerMethodDefinition')==definition and actual.get('proof',{}).get('typedRequest')==usage
        and(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))==
            (6,'MemoryPack.MemoryPackReader','ReadValue',[],[type_name]))
    if type_name==QUERY:
        adapter=actual.get('proof',{}).get('adapter',{})
        need('managed-Skill-Query-own-dispatcher-identity',True,type(cap.get('valueReaderMethodDefinition'))is int
            and cap['valueReaderMethodDefinition']==definition==adapter.get('readerMethodDefinition')
            and type(cap.get('valueDispatcherTargetRva'))is int and cap['valueDispatcherTargetRva']>0
            and cap['valueDispatcherTargetRva']==adapter.get('dispatcherTargetRva'))
    return dict(fieldName=read['fieldName'],typeName=type_name,capability=capability,
        readerMethodDefinition=definition,sourceTargetRva=read['sourceTargetRva'],
        managedValueTransfer=transfer,managedValueCapabilityShape=cap,ordinaryReferenceIdentityClaimed=False)


def derive_children(image,pins,complete):
    """Fresh nominal wire children shared by action and selector composition."""
    result={}
    for source in complete:
        for read in source['orderedSourceReads']:
            name=read['declaredType']
            if not read['kind'].startswith('managed:')or name not in TYPES or name in result:continue
            actual=source['sourceScope']['managedValueSources'][str(read['memberIndex'])]
            if name==BUFF:
                from scripts.game_data.memorypack.skill_root_buff_id_lists import derive_value
                result[name]=derive_value(image,pins)
            elif name==QUERY:
                from scripts.game_data.memorypack.skill_root_tag_query_components import derive
                result[name]=derive(image,pins,typed_request=actual['proof']['typedRequest'],
                    dispatcher_target=image.pe.image_base+actual['proof']['adapter']['dispatcherTargetRva'])
            elif name==SMART:
                from scripts.game_data.memorypack.skill_smart_target_value_components import derive
                result[name]=derive(image,pins,typed_request=actual['proof']['typedRequest'],
                    source_target=image.pe.image_base+read['sourceTargetRva'])
            elif name==ENVELOPE:
                from scripts.game_data.memorypack.skill_impulse_envelope_components import derive
                result[name]=derive(image,pins,typed_request=actual['proof']['typedRequest'],
                    source_target=image.pe.image_base+read['sourceTargetRva'])
            else:
                from scripts.game_data.memorypack.skill_global_buff_id_sources import derive
                result[name]=derive(image,pins)
    return result

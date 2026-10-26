"""Current NPC battle collection sources, independently of child admission.

The two string-list parents compose the current pooled string slot5 source.
SkillBBData's DataPair list has its own managed32 callback/storage proof. The
enclosing records, Collider and SkillBBData list callback remain separate.
"""
BATTLE='Beyond.Gameplay.Core.AbilitySystemForNpcData+NpcData'
SKILL=BATTLE+'+SkillBBData'
PAIR='Beyond.Blackboard+DataPair'
COLLIDER='Beyond.Gameplay.ColliderShapeData'
PLANS={BATTLE:(('activeSkillId','System.Collections.Generic.List`1<string>'),('battleShapeData',COLLIDER),
    ('blackboard','System.Collections.Generic.List`1<'+SKILL+'>'),('passiveSkillId','System.Collections.Generic.List`1<string>')),
    SKILL:(('blackboard','System.Collections.Generic.List`1<'+PAIR+'>'),('skillId','string'))}
COUNT_LIMIT=4096


def validate_plan(name,proof):
    if (name not in PLANS or proof.get('wrappedType')!=name
            or proof.get('completeSelectedCallerAdmitted')is not True
            or [(r['fieldName'],r['declaredType'])for r in proof['orderedSourceReads']]!=list(PLANS[name])
            or proof['lifecycle']['GetValue']['program'].get('fullReferenceOutput')is not True):
        raise ValueError('currentNpcBattleLists.closed-record-source:'+name)


def bind_reference_callback(component,*,pooled_string=False):
    """The list calls slot5 directly; no shared dispatch helper is executed."""
    expected=dict(reader='r13',output='rsp+32',receiver='r12',methodInfoSlot=408,callbackSlot=400)
    if (component.get('elementRuntimeBytes')!=8 or component.get('elementGrammarAdmitted')is not False
            or any(p.get('callbackAbi')!=expected for p in component['programs'])
            or type(pooled_string)is not bool):
        raise ValueError('currentNpcBattleLists.exact-direct-slot5-ABI')
    return dict(callbackAbi=expected,directSlot5Invocation=True,sharedDispatcherExecuted=False,
        actualCallbackPointerEqualityProved=False,actualCallbackEqualsProvedChildRequired=True,
        pooledStringCallbackRequired=pooled_string,liveFormatterSelectionObserved=False)


def derive_lists(image,pins):
    import json
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import generated_reader_sources,pooled_string_list_sources,scalar_param_native as scalar
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    from scripts.game_data.memorypack.skill_cost_data_list_sources import derive_reference_list_component,_load
    from scripts.game_data.memorypack.levelscript_collection_sources import reference_list_induction
    from scripts.game_data.memorypack.skill_root_value_lists import derive_data_pair_list_component
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.pointer_param import owned
    base=image.pe.image_base;ctx=NativeReferenceContext(image)
    need=lambda key,expected,actual:scalar.need('currentNpcBattleLists',key,expected,actual)
    wrappers={w.wrapped_type:w for w in derive_from_image(image).values()if w.wrapped_type in PLANS}
    need('exact-two-records',set(PLANS),set(wrappers))
    generated=generated_reader_sources.derive_many(image,pins,[wrappers[n].name for n in PLANS])
    records={}
    for name,row in zip(PLANS,generated['owners'],strict=True):
        need('complete-generated-source:'+name,'complete-reader-source-proved',
            row['status']if row['status']=='complete-reader-source-proved'else row)
        validate_plan(name,row['proof']);records[name]=row['proof']
    offsets=scalar.reader_offsets(image,'currentNpcBattleLists')
    offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    parents=[]
    for read in records[BATTLE]['orderedSourceReads']:
        if read['fieldName']not in('activeSkillId','blackboard','passiveSkillId'):continue
        element=SKILL if read['fieldName']=='blackboard'else'string'
        usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='currentNpcBattleLists.parent')
        component=derive_reference_list_component(image,pins,typed_request=usage,
            call_target=base+read['sourceTargetRva'],element_type=element,count_limit=2)
        body=owned(image,component['entry']['pointer'])
        induction=reference_list_induction(body['regions'],body['pointer'],offsets,
            {k:base+v for k,v in component['symbols'].items()})
        parents.append(dict(fieldName=read['fieldName'],typeName=read['declaredType'],element=element,
            source=read,typedRequest=usage,collection=component,positiveCountInduction=induction,
            callback=bind_reference_callback(component,pooled_string=element=='string')))
    need('three-exact-reference-parents',['activeSkillId','blackboard','passiveSkillId'],[p['fieldName']for p in parents])
    read=records[SKILL]['orderedSourceReads'][0]
    usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='currentNpcBattleLists.DataPairParent')
    pairs=derive_data_pair_list_component(image,pins,typed_request=usage,call_target=base+read['sourceTargetRva'],count_limit=COUNT_LIMIT)
    cap=pairs['capabilities']['skill-root-data-pair-list-positive']
    need('actual-DataPair-parent-source',(read['sourceTargetRva'],usage['methodSpec'][0]),
        (cap['packableReaderTargetRva'],cap['packableReaderMethodDefinition']))
    strings=pooled_string_list_sources.validate_string_components(image,_load('levelscript_pooled_string_list_native.json',pins))
    pair=derive_pair(image,BATTLE);adapter=derive_adapter(image,pins,pair,wrappers[BATTLE])
    need('same-generated-GetValue',records[BATTLE]['lifecycle']['GetValue']['method'],adapter['getterMethod'])
    need('same-generated-slot5',records[BATTLE]['lifecycle']['concreteFormatter']['method'][0],
        pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
    need('independent-pooled-string-slot5',(5,4,8),
        (strings['stringFormatterSlot'],strings['wireBytes'],strings['managedReferenceBytes']))
    return json.loads(json.dumps(dict(nativeInputs=pins,records=records,referenceParents=parents,
        dataPairList=dict(source=read,typedRequest=usage,component=pairs),
        pooledString=dict(component=strings,actualCallbackEqualsPooledStringRequired=True,
            liveFormatterSelectionObserved=False),
        battleAdapter=dict(pair=pair,adapter=adapter),countLimit=COUNT_LIMIT,
        childRecordGrammarAdmitted=False,enclosingNpcParentAdmitted=False,wholeOwnerAdmitted=False,
        liveFormatterSelectionObserved=False)))

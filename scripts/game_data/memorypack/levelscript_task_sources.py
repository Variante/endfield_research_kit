"""Current pooled Task/TaskCondition sources and separately typed dictionaries.

GameCondition is null-only here. Positive condition tags never inherit older
task receipts, action-map tag metadata or an unrelated Ability condition.
"""
TASK='Beyond.Gameplay.LevelScriptTaskData'
CONDITION=TASK+'+TaskConditionData'
GAME_CONDITION='Beyond.Gameplay.GameCondition'
PLANS={TASK:(('canBeTracked','bool'),('conditionDict','System.Collections.Generic.Dictionary`2<string,'+CONDITION+'>'),
    ('needManualCheck','bool'),('taskType','Beyond.Gameplay.LevelScriptTaskType')),
    CONDITION:(('condition',GAME_CONDITION),('isMainObjective','bool'),('objectiveEnum','Beyond.Gameplay.TaskObjectiveEnum'))}


def validate_plan(name,proof):
    if (name not in PLANS or proof.get('wrappedType')!=name or proof.get('completeSelectedCallerAdmitted')is not True
            or [(r['fieldName'],r['declaredType'])for r in proof['orderedSourceReads']]!=list(PLANS[name])
            or proof['lifecycle']['GetValue']['program'].get('fullReferenceOutput')is not True):
        raise ValueError('currentLevelScriptTask.closed-record-plan:'+name)


def derive(image,pins,owners):
    import json
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
    from scripts.game_data.memorypack import generated_reader_sources,reference_dictionary_sources
    from scripts.game_data.memorypack import scalar_param_native as scalar,pooled_string_list_sources
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_action_null_source import derive_reference_null
    from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    need=lambda k,e,a:scalar.need('currentLevelScriptTask',k,e,a)
    need('current-selected-owners',pins,owners['nativeInputs'])
    wrappers={w.wrapped_type:w for w in derive_from_image(image).values()if w.wrapped_type in PLANS}
    need('exact-two-owned-wrappers',set(PLANS),set(wrappers))
    result=generated_reader_sources.derive_many(image,pins,[wrappers[n].name for n in PLANS])
    records={};offsets=scalar.reader_offsets(image,'currentLevelScriptTask')
    for name,row in zip(PLANS,result['owners'],strict=True):
        need('complete-generated-source:'+name,'complete-reader-source-proved',
            row['status']if row['status']=='complete-reader-source-proved'else dict(status=row['status'],reason=row.get('reason')))
        proof=row['proof'];validate_plan(name,proof)
        pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrappers[name]);primitives={}
        need('exact-GetValue-source',proof['lifecycle']['GetValue']['method'],adapter['getterMethod'])
        need('exact-concrete-slot5',proof['lifecycle']['concreteFormatter']['method'][0],
            pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
        for read in proof['orderedSourceReads']:
            if read['kind']not in('byte','scalar32'):continue
            source=vector_recorder(image)(read['sourceTargetRva'])
            checked=scalar.boolean_source(image,source,offsets,'currentLevelScriptTask.bool')if read['kind']=='byte'else scalar.integer_source(
                image,source,offsets,'currentLevelScriptTask.int32',width=4)
            enum=None
            if read.get('context')is not None:
                usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='currentLevelScriptTask.enum')
                bind_typed_read(image,usage,method_name='ReadUnmanaged',argument=read['declaredType'],kind=17,reference=False)
                need('nominal-enum-parent','System.Enum',ctx.parent(read['declaredType']))
                need('enum-int32-backing',(read['declaredType'],'int',16),ctx.field(read['declaredType']+'::value__'))
                enum=usage
            primitives[read['fieldName']]=dict(source=source,proof=checked,typedEnum=enum)
        records[name]=dict(source=proof,pair=pair,adapter=adapter,primitives=primitives)
    root=owners['owners']['Beyond.Gameplay.LevelScriptData']
    root_field,root_read=next((f,r)for f,r in zip(root['fields'],root['program']['orderedReads'],strict=True)if f['name']=='taskMap')
    root_usage=derive_typed_usage_context(image,root_read['typedUsage']['instruction']-base,label='currentLevelScriptTask.rootParent')
    nested=next(r for r in records[TASK]['source']['orderedSourceReads']if r['fieldName']=='conditionDict')
    nested_usage=derive_typed_usage_context(image,nested['context']['instructionRva'],label='currentLevelScriptTask.conditionParent')
    parents=[]
    for parent_name,usage,target,value in(('taskMap',root_usage,root_read['sourceTarget'],TASK),
            ('conditionDict',nested_usage,base+nested['sourceTargetRva'],CONDITION)):
        dictionary=reference_dictionary_sources.derive(image,pins,typed_request=usage,call_target=target,
            key_type='string',value_type=value,count_limit=16384)
        parents.append(dict(fieldName=parent_name,typedRequest=usage,collection=dictionary))
    null=derive_reference_null(image,pins,GAME_CONDITION)
    child=records[CONDITION]['source']['orderedSourceReads'][0]
    usage=derive_typed_usage_context(image,child['context']['instructionRva'],label='currentLevelScriptTask.nullCondition')
    bind_typed_read(image,usage,method_name='ReadValue',argument=GAME_CONDITION,kind=18,reference=True)
    need('actual-GameCondition-null-source',null['referenceReaderTargetRva'],child['sourceTargetRva'])
    need('actual-GameCondition-read-definition',null['referenceReaderMethodDefinition'],usage['methodSpec'][0])
    need('null-only-child',(True,False,255,1),(null['nullAdmitted'],null['positiveAdmitted'],null['nullMarker'],null['consumedBytes']))
    strings=pooled_string_list_sources.validate_string_components(image,_load('levelscript_pooled_string_list_native.json',pins))
    string_method,=[m for m in md.methods_for(ctx.index.types['MemoryPack.BeyondStringFormatter'])if md.string(m.name_index)=='Deserialize']
    dictionary=parents[0]['collection'];symbols={k:base+v for k,v in dictionary['symbolRvas'].items()}
    dispatch=owned(image,symbols['dispatch'])
    pooled_key=deserialize_slot(dispatch['regions'],dispatch['pointer'],prepare=base+records[TASK]['adapter']['canonicalRoutes']['symbolRvas']['prepare'],
        callback=image.method_pointer_va(string_method))
    for name,record in records.items():
        need('same-actual-value-slot-dispatch:'+name,record['adapter']['canonicalRoutes']['symbolRvas']['dispatch'],dictionary['symbolRvas']['dispatch'])
    return json.loads(json.dumps(dict(nativeInputs=pins,records=records,parents=parents,
        gameConditionNull=dict(parent=child,typedRequest=usage,component=null),
        pooledStringKey=dict(component=strings,dispatchWindows=dispatch['windows'],program=pooled_key),
        capability=dict(countLimit=16384,headerBytes=4,taskMemberCount=4,conditionMemberCount=3,
            gameConditionNullOnly=True,gameConditionNullMarker=255,positiveGameConditionAdmitted=False,
            sourceWitnessClassArguments=['object','object'],actualCallbackEqualsCanonicalRequired=True,
            recordGrammar='MC4-or-FF;TaskCondition-MC3-or-FF;GameCondition-FF-only',
            profileAdmitted=True,wholeGrammarAdmitted=False,wholeOwnerAdmitted=False),wholeOwnerAdmitted=False,
        liveFormatterSelectionObserved=False)))

"""Finite current LevelData records compiled from complete generated sources.

Only the explicit ordered plans below are available. The shared compiler owns
actual primitive and Vector3 source/field transfers; this owner additionally
proves pooled targets, ordinary adapters/GetValue and each exact host list.
"""
PLANS={
 'Beyond.Gameplay.LevelTransformData':(('key','string','byte-payload'),('position','UnityEngine.Vector3','unity-vector3-raw12'),
    ('rotation','UnityEngine.Vector3','unity-vector3-raw12'),('transId','int','scalar32')),
 'Beyond.Gameplay.LevelCameraPoseData':(('cameraId','int','scalar32'),('fov','float','float32-bits'),
    ('position','UnityEngine.Vector3','unity-vector3-raw12'),('rotation','UnityEngine.Vector3','unity-vector3-raw12')),
 'Beyond.Gameplay.LevelErosionSludgeDataV2':(('coreId','ulong','scalar64-bits'),('globalVarId','int','scalar32'),
    ('globalVarValue','long','scalar64-bits'),('sludgeName','string','byte-payload')),
}
FIELDS={'aiTransData':'Beyond.Gameplay.LevelTransformData','cameraPoses':'Beyond.Gameplay.LevelCameraPoseData',
    'sludgeDatas':'Beyond.Gameplay.LevelErosionSludgeDataV2'}
COUNT_LIMIT=4096


def bind_program(name,source,program,pending):
    plan=PLANS.get(name)
    if (plan is None or pending or not isinstance(program,dict)
            or source.get('wrappedType')!=name
            or [(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']]!=[(n,t)for n,t,_ in plan]
            or program['memberCount']!=len(plan)
            or [(r['fieldName'],r['kind'])for r in program['reads']]!=[(n,k)for n,_,k in plan]
            or program['requiredCapabilities']!=(['byte-payload']if any(k=='byte-payload'for _,_,k in plan)else[])
            or program['childBindings']):
        raise ValueError('leveldataSimpleRecords.exact-finite-source-program:'+name)


def derive(image,pins,host):
    import json
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import generated_reader_sources,pooled_source_helper,scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    need=lambda key,expected,actual:scalar.need('leveldataSimpleRecords',key,expected,actual)
    need('same-current-host',pins,host['nativeInputs']);base=image.pe.image_base
    wrappers={w.wrapped_type:w for w in derive_from_image(image).values()if w.wrapped_type in PLANS}
    need('three-finite-wrappers',set(PLANS),set(wrappers))
    generated=generated_reader_sources.derive_many(image,pins,[wrappers[n].name for n in PLANS])
    records={};capabilities={}
    for name,result in zip(PLANS,generated['owners'],strict=True):
        need('complete-generated-source:'+name,'complete-reader-source-proved',
            result['status']if result['status']=='complete-reader-source-proved'else result)
        source=result['proof'];program,pending=compile_member_program(source,pins,
            wrapper_name=wrappers[name].name,type_name=name,value4={})
        bind_program(name,source,program,pending)
        need('complete-original-GetValue',True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
        pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrappers[name])
        need('same-owned-GetValue',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
        need('same-concrete-slot5',source['lifecycle']['concreteFormatter']['method'][0],
            pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
        pool={str(read['memberIndex']):pooled_source_helper.validate_on_image(image,base+read['sourceTargetRva'],pins)
            for read in source['orderedSourceReads']if read['kind']=='byte-payload'}
        records[name]=dict(source=source,compiled=program,pair=pair,adapter=adapter,pooled=pool)
        capabilities[name]=dict(typeName=name,memberCount=len(PLANS[name]),nullAdmitted=True,positiveAdmitted=True,
            program=program,finiteFloatProfile=True,profileAdmitted=True,wholeGrammarAdmitted=False,
            actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False)
    parents=[]
    for field,name in FIELDS.items():
        declaration,read=next((f,r)for f,r in zip(host['fields'],host['program']['orderedReads'],strict=True)if f['name']==field)
        need('exact-nominal-host-list','System.Collections.Generic.List`1<'+name+'>',declaration['typeName'])
        usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='leveldataSimpleRecords.parent')
        collection=reference_list(image,pins,typed_request=usage,call_target=read['sourceTarget'],element_type=name,count_limit=COUNT_LIMIT)
        witness=collection['witnessComponent']
        need('actual-list-parent-target',read['sourceTarget']-base,witness['callTargetRva'])
        need('actual-list-child-nominal',name,witness['elementType'])
        parents.append(dict(field=declaration,source=read,typedRequest=usage,collection=collection,
            callbackSelectionConditional=True,actualCallbackEqualsProvedChildRequired=True))
    return json.loads(json.dumps(dict(nativeInputs=pins,records=records,parents=parents,
        capabilities=capabilities,countLimit=COUNT_LIMIT,wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))

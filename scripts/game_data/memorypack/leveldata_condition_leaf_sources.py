"""Finite current mission/quest condition leaves; union selection is separate."""
PLANS={
 'Beyond.Gameplay.SimpleConditionCheckMissionNotPaused':(('missionId','string','byte-payload'),),
 'Beyond.Gameplay.SimpleConditionCheckMissionState':(('compareOperator','Beyond.GEnums.CompareOperator','scalar32'),
    ('compareTarget','Beyond.GEnums.MissionState','scalar32'),('missionId','string','byte-payload')),
 'Beyond.Gameplay.SimpleConditionCheckQuestState':(('compareOperator','Beyond.GEnums.CompareOperator','scalar32'),
    ('compareTarget','Beyond.GEnums.QuestState','scalar32'),('questId','string','byte-payload')),
}


def bind_program(name,source,program,pending):
    plan=PLANS.get(name)
    if (plan is None or pending or source.get('wrappedType')!=name
            or[(r['fieldName'],r['declaredType'])for r in source.get('orderedSourceReads',[])]!=[(n,t)for n,t,k in plan]
            or program.get('memberCount')!=len(plan) or program.get('requiredCapabilities')!=['byte-payload']
            or program.get('childBindings')!=[]
            or[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
                (i,n,k,'byte-payload'if k=='byte-payload'else None)for i,(n,t,k)in enumerate(plan)]):
        raise ValueError('storyConditionLeaf.exact-finite-source:'+name)


def derive(image,pins):
    """Fresh whole stored leaf programs, nominal enums, pooled target and adapter."""
    import json
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import generated_reader_sources,pooled_source_helper,scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    need=lambda k,e,a:scalar.need('storyConditionLeaf',k,e,a)
    base=image.pe.image_base;ctx=NativeReferenceContext(image)
    wrappers={w.wrapped_type:w for w in derive_from_image(image).values()if w.wrapped_type in PLANS}
    need('exact-finite-nominal-leaves',set(PLANS),set(wrappers))
    selected=generated_reader_sources.derive_many(image,pins,[wrappers[n].name for n in PLANS]);records={};caps={}
    for name,result in zip(PLANS,selected['owners'],strict=True):
        need('complete-current-source:'+name,'complete-reader-source-proved',
            result['status']if result['status']=='complete-reader-source-proved'else result)
        source=result['proof'];program,pending=compile_member_program(source,pins,wrapper_name=wrappers[name].name,type_name=name,value4={})
        bind_program(name,source,program,pending)
        pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrappers[name])
        need('full-original-GetValue',True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
        need('same-original-getter',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
        need('same-concrete-slot5',source['lifecycle']['concreteFormatter']['method'][0],
            pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
        pooled={str(read['memberIndex']):pooled_source_helper.validate_on_image(image,base+read['sourceTargetRva'],pins)
            for read in source['orderedSourceReads']if read['kind']=='byte-payload'}
        enums={}
        for field,declared,kind in PLANS[name]:
            if kind!='scalar32':continue
            need('nominal-enum:'+declared,'System.Enum',ctx.parent(declared));value=ctx.field(declared+'::value__')
            need('literal-enum-storage:'+declared,True,value[1]in('int','uint'))
            enums[field]=dict(typeName=declared,backing=value[1],field=value)
        records[name]=dict(source=source,pair=pair,adapter=adapter,pooled=pooled)
        caps[name]=dict(typeName=name,memberCount=len(PLANS[name]),program=program,enumBackings=enums,
            nullAdmitted=True,positiveAdmitted=True,wholeGrammarAdmitted=True,
            actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False)
    return json.loads(json.dumps(dict(nativeInputs=pins,records=records,capabilities=caps,
        unionSelectionAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))

"""Current AirWall Mission checks, with independent original adapters/lists.

Generated reader proofs supply lifecycle and field transfers. The nominal
original registrations, canonical reference adapters, actual AirWall caller,
both list parents and full repeated collection loop are separate joins here.
No mission evaluation or effective runtime callback choice is observed.
"""
TOTAL='Beyond.Gameplay.MissionTotalCheckData'
CHECK='Beyond.Gameplay.MissionCheckData'
PLANS={TOTAL:(('downReason','System.Collections.Generic.List`1<'+CHECK+'>'),
    ('isDownAny','bool'),('isRiseAny','bool'),('riseReason','System.Collections.Generic.List`1<'+CHECK+'>')),
    CHECK:(('detailState','int'),('id','string'),('isQuest','bool'),('isSame','bool'))}


def validate_plan(original,source):
    if (original not in PLANS or source.get('wrappedType')!=original
            or source.get('completeSelectedCallerAdmitted')is not True
            or [(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']]!=list(PLANS[original])):
        raise ValueError('leveldataMission.closed-source-plan:'+original)
    getter=source['lifecycle']['GetValue']['program']
    if getter.get('fullReferenceOutput')is not True:
        raise ValueError('leveldataMission.complete-GetValue-reference:'+original)


def derive(image,pins,airwalls,current_children):
    import json
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import generated_reader_sources,scalar_param_native as scalar,pooled_source_helper
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_cost_data_list_sources import derive_reference_list_component
    from scripts.game_data.memorypack.levelscript_collection_sources import reference_list_induction
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    base=image.pe.image_base;ctx=NativeReferenceContext(image)
    need=lambda k,e,a:scalar.need('leveldataMission',k,e,a)
    need('same-current-pins',(pins,pins),(airwalls['nativeInputs'],current_children['nativeInputs']))
    records={};wrappers={w.wrapped_type:w for w in derive_from_image(image).values()if w.wrapped_type in PLANS}
    need('exact-two-wrappers',set(PLANS),set(wrappers))
    targets=generated_reader_sources.derive_many(image,pins,[wrappers[n].name for n in PLANS])
    offsets=scalar.reader_offsets(image,'leveldataMission')
    for original,result in zip(PLANS,targets['owners'],strict=True):
        need('complete-current-generated-source:'+original,'complete-reader-source-proved',result['status'])
        source=result['proof'];validate_plan(original,source)
        pair=derive_pair(image,original);adapter=derive_adapter(image,pins,pair,wrappers[original])
        need('same-generated-concrete-slot5',source['lifecycle']['concreteFormatter']['method'][0],
            pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
        need('same-generated-GetValue',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
        primitives={}
        for read in source['orderedSourceReads']:
            if read['declaredType']not in('int','bool','string'):continue
            target=base+read['sourceTargetRva']
            if read['declaredType']=='string':primitives[read['fieldName']]=pooled_source_helper.validate_on_image(image,target,pins)
            else:
                native=vector_recorder(image)(read['sourceTargetRva'])
                proof=scalar.boolean_source(image,native,offsets,'leveldataMission.bool')if read['declaredType']=='bool'else scalar.integer_source(
                    image,native,offsets,'leveldataMission.int',width=4)
                primitives[read['fieldName']]=dict(source=native,proof=proof)
        records[original]=dict(source=source,profile=pair,adapter=adapter,primitives=primitives)
    actual,=[p for p in airwalls['records']['Beyond.Gameplay.AirWallCheckData']['children']if p['field']['name']=='missionData']
    # The independently current Interactive component proves this actual
    # ReadValue reference helper, its own MVAR contexts and canonical dispatch.
    reader=current_children['interactive']['readValue']
    need('actual-MissionTotal-parent-source',reader['selectedBytes'][0][0],actual['source']['sourceTarget'])
    need('actual-MissionTotal-request',('ReadValue',[TOTAL]),
        (actual['typedRequest']['methodName'],actual['typedRequest']['methodArguments']))
    parents=[]
    for read in records[TOTAL]['source']['orderedSourceReads']:
        if read['fieldName']not in('downReason','riseReason'):continue
        usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='leveldataMission.listParent')
        component=derive_reference_list_component(image,pins,typed_request=usage,
            call_target=base+read['sourceTargetRva'],element_type=CHECK,count_limit=2)
        body=owned(image,component['entry']['pointer'])
        layout=dict(offsets,totalLength=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16)
        induction=reference_list_induction(body['regions'],body['pointer'],layout,
            {k:base+v for k,v in component['symbols'].items()})
        parents.append(dict(fieldName=read['fieldName'],typeName=read['declaredType'],source=read,
            typedRequest=usage,collection=component,positiveCountInduction=induction))
    need('two-exact-MissionCheck-list-parents',['downReason','riseReason'],[p['fieldName']for p in parents])
    return json.loads(json.dumps(dict(nativeInputs=pins,records=records,parent=actual,
        referenceParentSource=reader,listParents=parents,countLimit=4096,
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))

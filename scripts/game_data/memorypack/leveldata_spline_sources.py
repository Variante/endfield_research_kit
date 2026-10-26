"""Explicit current Spline7 profile and its three independent value lists."""
TYPE='Beyond.Gameplay.LevelSplineData'
CAP='story-level-spline'
LIMIT=4096
LIST=lambda t:'System.Collections.Generic.List`1<'+t+'>'
BEZIER='UnityEngine.Splines.BezierKnot'
COLLECTIONS={LIST('int'):('story-spline-int-list','int32-list','int',4),
    LIST('float'):('story-spline-float-list','float32-list','float',4),
    LIST(BEZIER):('story-bezier-knot-list','bezier56-list',BEZIER,56)}
PLAN=(('closed','bool','bool-byte'),('keyNodeIndexList',LIST('int'),'int32-list'),
    ('knotProgresses',LIST('float'),'float32-list'),('knots',LIST(BEZIER),'bezier56-list'),
    ('position','UnityEngine.Vector3','unity-vector3-raw12'),('rotation','UnityEngine.Vector3','unity-vector3-raw12'),
    ('splineId','int','scalar32'))


def bind_collection(pins,join,child,capability):
    expected=COLLECTIONS.get(join['typeName']);usage=join['typedRequest'];cap=child.get('capabilities',{}).get(capability,{})
    if (expected is None or expected[0]!=capability or child.get('nativeInputs')!=pins
            or(cap.get('typeName'),cap.get('elementType'),cap.get('elementWireBytes'))!=(join['typeName'],expected[2],expected[3])
            or any(cap.get(k)is not True for k in('nullable','positiveCountsAdmitted','actualCallbackEqualsProvedChildRequired'))
            or type(cap.get('countLimit'))is not int or cap['countLimit']!=LIMIT
            or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[join['typeName']]
            or(cap.get('readerMethodDefinition'),cap.get('sourceTargetRva'))!=(usage['methodSpec'][0],join['sourceTargetRva'])):
        raise ValueError('currentSpline.exact-current-collection:'+join['typeName'])
    return dict(fieldName=join['fieldName'],typeName=join['typeName'],capability=capability,
        readerMethodDefinition=cap['readerMethodDefinition'],sourceTargetRva=cap['sourceTargetRva'],
        countLimit=LIMIT,actualCallbackEqualsProvedChildRequired=True)


def derive(image,pins,host):
    import json
    from scripts.game_data import levelscript_int_list_native as integers
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import generated_reader_sources,scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.leveldata_bezier_list_sources import derive as derive_bezier
    from scripts.game_data.memorypack.float_list_sources import derive as derive_float
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    need=lambda k,e,a:scalar.need('currentSpline',k,e,a)
    need('same-current-host',pins,host['nativeInputs']);base=image.pe.image_base
    wrapper,=[w for w in derive_from_image(image).values()if w.wrapped_type==TYPE]
    source=generated_reader_sources.derive(image,pins,wrapper.name)
    need('exact-Spline7-declarations',[(n,t)for n,t,k in PLAN],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
    requests={r['memberIndex']:derive_typed_usage_context(image,r['context']['instructionRva'],label='currentSpline.child')
        for r in source['orderedSourceReads']if r['declaredType']in COLLECTIONS}
    read=source['orderedSourceReads'][3];bezier=derive_bezier(image,pins,typed_request=requests[3],call_target=base+read['sourceTargetRva'])
    need('exact-Bezier-inline-source',(56,56,True,False),
        (bezier['capability']['elementWireBytes'],bezier['capability']['managedElementBytes'],
         bezier['capability']['inlineElementSource'],bezier['capability']['closedElementRegistrationEquivalenceProved']))
    reference=bezier['proof']['context'];int_raw=integers.CONTRACT_PATH.read_bytes();int_fact=_load(integers.CONTRACT_PATH.name,pins)
    integers._validate_native(image,int_fact);proofs={};caps={};children={}
    for read in source['orderedSourceReads']:
        declared=read['declaredType'];index=read['memberIndex']
        if declared not in COLLECTIONS:continue
        key,kind,element,width=COLLECTIONS[declared];usage=requests[index]
        bind_typed_read(image,usage,method_name='ReadPackable',argument=declared,kind=21,reference=True)
        need('same-actual-packable-source:'+declared,(reference['callTargetRva'],reference['typedRequest']['methodSpec'][0]),
            (read['sourceTargetRva'],usage['methodSpec'][0]))
        argument,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
        carrier=ContextSymbols(image).type(argument.type_pointer_va);arg,=carrier['classArguments']
        if element in('int','float'):
            need('exact-primitive-element:'+element,(element,b'\x08\x80'if element=='int'else b'\x0c\x80'),
                (arg['name'],bytes.fromhex(arg['rawHex'])[10:12]))
        proof=(dict(sourceContract=integers.CONTRACT_PATH.name,source=int_fact,closedCarrier=carrier)if element=='int'
            else derive_float(image,pins,dict(typedRead=usage),int_fact)if element=='float'else bezier)
        cap=dict(typeName=declared,elementType=element,elementWireBytes=width,nullable=True,positiveCountsAdmitted=True,
            countLimit=LIMIT,readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=read['sourceTargetRva'],
            actualCallbackEqualsProvedChildRequired=True)
        if element==BEZIER:cap.update(inlineElementSource=True,closedElementRegistrationEquivalenceProved=False)
        caps[key]=cap;children[index]=dict(nativeInputs=pins,capabilities={key:cap})
        proofs[read['fieldName']]=dict(source=read,typedRequest=usage,component=proof)
    program,pending=compile_member_program(source,pins,wrapper_name=wrapper.name,type_name=TYPE,value4={},
        collections={t:(key,kind,key)for t,(key,kind,e,w)in COLLECTIONS.items()},collection_children=children,
        typed_requests=requests,collection_binder=bind_collection)
    need('complete-Spline7-program',[],pending)
    need('exact-Spline7-wire-order',[(n,k)for n,t,k in PLAN],[(r['fieldName'],r['kind'])for r in program['reads']])
    pair=derive_pair(image,TYPE);adapter=derive_adapter(image,pins,pair,wrapper)
    need('whole-owned-original',True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
    need('same-owned-GetValue',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
    need('same-owned-slot5',source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
    field,parent=next((f,r)for f,r in zip(host['fields'],host['program']['orderedReads'],strict=True)if f['name']=='splines')
    need('exact-host-Spline-list',LIST(TYPE),field['typeName'])
    usage=derive_typed_usage_context(image,parent['typedUsage']['instruction']-base,label='currentSpline.hostParent')
    listing=reference_list(image,pins,typed_request=usage,call_target=parent['sourceTarget'],element_type=TYPE,count_limit=LIMIT)
    need('Int32-declaration-bookend',int_raw,integers.CONTRACT_PATH.read_bytes())
    cap=dict(typeName=TYPE,memberCount=7,program=program,collections=caps,nullAdmitted=True,positiveAdmitted=True,
        profileAdmitted=True,wholeGrammarAdmitted=False,finiteFloatProfile=True,
        actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
        standaloneBezierElementAdmitted=False)
    return json.loads(json.dumps(dict(nativeInputs=pins,source=source,pair=pair,adapter=adapter,children=proofs,
        capability=cap,parent=dict(field=field,source=parent,typedRequest=usage,collection=listing),
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))

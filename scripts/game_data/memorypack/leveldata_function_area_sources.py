"""Current FunctionArea base records under an explicit bounded child profile."""
TYPE='Beyond.Gameplay.LevelFunctionAreaData+FunctionAreaBaseData'
PARENT='Beyond.Gameplay.LevelFunctionAreaData'
HIDE=PARENT+'+FunctionAreaFactoryHideDesc'
VECTORS='System.Collections.Generic.List`1<UnityEngine.Vector2>'
CAP='story-function-area-base'
HIDE_CAP='story-function-area-factory-hide-null'
VECTOR_CAP='story-function-area-vector2-list'
LIMIT=4096
RANGE='Beyond.Gameplay.ThreeDimRange'
PLAN=(('bufferDistance','float','float32-bits'),('defaultOff','bool','bool-byte'),('enableFactoryHide','bool','bool-byte'),
 ('euler','UnityEngine.Vector3','unity-vector3-raw12'),('factoryHideDesc',HIDE,'factory-hide-null'),
 ('functionType','Beyond.Gameplay.EFunctionAreaType','scalar32'),('hasCondition','bool','bool-byte'),('index','int','scalar32'),
 ('offset','UnityEngine.Vector3','unity-vector3-raw12'),('posList',VECTORS,'vector2-list'),
 ('postion','UnityEngine.Vector3','unity-vector3-raw12'),('radius','float','float32-bits'),
 ('shapeType','Beyond.Gameplay.Core.TriggerObserverComponent+Shape','scalar32'),
 ('size','UnityEngine.Vector3','unity-vector3-raw12'),('uniqueId','ulong','scalar64-bits'))


def plan(*,positive_factory_hide=False):
    if type(positive_factory_hide)is not bool:raise ValueError('functionArea.literal-factory-hide-profile')
    return tuple((n,t,'factory-hide-record'if n=='factoryHideDesc'and positive_factory_hide else k)for n,t,k in PLAN)


def bind_hide(pins,join,child,capability):
    cap=child.get('capabilities',{}).get(capability,{});usage=join['typedRequest']
    if (capability!=HIDE_CAP or child.get('nativeInputs')!=pins or join['typeName']!=HIDE
            or cap.get('typeName')!=HIDE or cap.get('nullAdmitted')is not True or cap.get('positiveAdmitted')is not False
            or type(cap.get('nullMarker'))is not int or cap['nullMarker']!=255
            or type(cap.get('consumedBytes'))is not int or cap['consumedBytes']!=1
            or usage.get('methodName')!='ReadValue'or usage.get('methodArguments')!=[HIDE]
            or(cap.get('referenceReaderMethodDefinition'),cap.get('referenceReaderTargetRva'))!=(usage['methodSpec'][0],join['sourceTargetRva'])):
        raise ValueError('functionArea.exact-factory-FF-parent')
    return dict(fieldName=join['fieldName'],typeName=HIDE,capability=capability,
        readerMethodDefinition=cap['referenceReaderMethodDefinition'],sourceTargetRva=cap['referenceReaderTargetRva'],
        positiveAdmitted=False,nullMarker=255,consumedBytes=1)


def bind_vectors(pins,join,child,capability):
    cap=child.get('capabilities',{}).get(capability,{});usage=join['typedRequest']
    if (capability!=VECTOR_CAP or child.get('nativeInputs')!=pins or join['typeName']!=VECTORS
            or cap.get('typeName')!=VECTORS or cap.get('nullable')is not True or cap.get('positiveCountsAdmitted')is not True
            or type(cap.get('countLimit'))is not int or cap['countLimit']!=LIMIT
            or(cap.get('elementType'),cap.get('elementWireBytes'))!=('UnityEngine.Vector2',8)
            or cap.get('actualCallbackEqualsProvedChildRequired')is not True
            or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[VECTORS]
            or(cap.get('readerMethodDefinition'),cap.get('sourceTargetRva'))!=(usage['methodSpec'][0],join['sourceTargetRva'])):
        raise ValueError('functionArea.exact-Vector2-parent')
    return dict(fieldName=join['fieldName'],typeName=VECTORS,capability=capability,
        readerMethodDefinition=cap['readerMethodDefinition'],sourceTargetRva=cap['sourceTargetRva'],
        countLimit=LIMIT,actualCallbackEqualsProvedChildRequired=True)


def derive(image,pins,parent,*,positive_factory_hide=False):
    import json
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import generated_reader_sources,scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.leveldata_vector2_list_sources import derive_collection
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_action_null_source import derive_reference_null
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    from scripts.game_data.memorypack import leveldata_factory_hide_sources as factory_hide
    need=lambda k,e,a:scalar.need('functionArea',k,e,a)
    selected_plan=plan(positive_factory_hide=positive_factory_hide)
    need('same-current-parent',pins,parent['nativeInputs']);ctx=NativeReferenceContext(image);base=image.pe.image_base
    wrapper,=[w for w in derive_from_image(image).values()if w.wrapped_type==TYPE]
    hide=factory_hide.derive(image,pins)if positive_factory_hide else None
    source=hide['parent']['source']if hide is not None else generated_reader_sources.derive(image,pins,wrapper.name)
    need('exact-finite-base-declarations',[(n,t)for n,t,k in PLAN],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
    null=None if positive_factory_hide else derive_reference_null(image,pins,HIDE)
    hide_key=factory_hide.CAP if positive_factory_hide else HIDE_CAP
    hide_cap=hide['capability']if positive_factory_hide else null
    requests={};vector=None
    for read in source['orderedSourceReads']:
        if read['declaredType']not in(HIDE,VECTORS):continue
        usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='functionArea.child')
        requests[read['memberIndex']]=usage
        if read['declaredType']==VECTORS:
            vector=derive_collection(image,pins,typed_request=usage,call_target=base+read['sourceTargetRva'])
            need('independent-Vector2-collection',(8,8,4),
                (vector['capability']['elementWireBytes'],vector['capability']['managedElementBytes'],vector['capability']['headerBytes']))
            vector_cap=dict(typeName=VECTORS,elementType='UnityEngine.Vector2',elementWireBytes=8,countLimit=LIMIT,
                nullable=True,positiveCountsAdmitted=True,actualCallbackEqualsProvedChildRequired=True,
                readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=read['sourceTargetRva'])
    program,pending=compile_member_program(source,pins,wrapper_name=wrapper.name,type_name=TYPE,value4={},
        references={HIDE:(hide_key,'factory-hide-record'if positive_factory_hide else'factory-hide-null',hide_key)},
        reference_children={HIDE:dict(nativeInputs=pins,capabilities={hide_key:hide_cap})},typed_requests=requests,
        collections={VECTORS:(VECTOR_CAP,'vector2-list',VECTOR_CAP)},
        collection_children={9:dict(nativeInputs=pins,capabilities={VECTOR_CAP:vector_cap})},
        collection_binder=bind_vectors,reference_binder=factory_hide.bind_parent if positive_factory_hide else bind_hide)
    need('complete-finite-program',[],pending)
    need('exact-finite-wire-order',[(n,k)for n,t,k in selected_plan],[(r['fieldName'],r['kind'])for r in program['reads']])
    pair=derive_pair(image,TYPE);adapter=derive_adapter(image,pins,pair,wrapper)
    need('owned-full-GetValue',True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
    need('same-owned-GetValue',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
    need('same-owned-slot5',source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
    enums={}
    for name,typename,kind in PLAN:
        if kind!='scalar32'or typename=='int':continue
        need('nominal-enum-parent:'+typename,'System.Enum',ctx.parent(typename));field=ctx.field(typename+'::value__')
        need('nominal-four-byte-enum:'+typename,True,field[1]in('int','uint'))
        enums[name]=dict(typeName=typename,backing=field[1],field=field)
    owner=parent['records'][PARENT];bridge,=[r for r in owner['childLists']if r['field']['name']=='baseData']
    need('exact-current-base-list-parent','System.Collections.Generic.List`1<'+TYPE+'>',bridge['field']['typeName'])
    usage=derive_typed_usage_context(image,bridge['source']['typedUsage']['instruction']-base,label='functionArea.baseParent')
    collection=reference_list(image,pins,typed_request=usage,call_target=bridge['source']['sourceTarget'],element_type=TYPE,count_limit=LIMIT)
    cap=dict(typeName=TYPE,memberCount=15,program=program,enumBackings=enums,nullAdmitted=True,positiveAdmitted=True,
        profileAdmitted=True,wholeGrammarAdmitted=False,finiteFloatProfile=True,countLimit=LIMIT,
        positiveFactoryHideDescAdmitted=positive_factory_hide,actualCallbackEqualsProvedChildRequired=True,
        vectorCollection=vector_cap,liveFormatterSelectionObserved=False)
    if positive_factory_hide:cap['factoryHideCapability']=hide_cap
    result=dict(nativeInputs=pins,source=source,pair=pair,adapter=adapter,nullFactoryHideDesc=null,
        vectorList=vector,capability=cap,parent=dict(ownedParent=owner,source=bridge['source'],typedRequest=usage,collection=collection),
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)
    if positive_factory_hide:result['positiveFactoryHideDesc']=hide
    from scripts.game_data.codecs.leveldata.current_function_area import validate
    result=json.loads(json.dumps(result));validate(result['capability']);return result


def derive_ranges(image,pins,parent,geometry):
    """Join the independently owned range reader to this actual list parent."""
    import json
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
    need=lambda k,e,a:scalar.need('functionAreaRanges',k,e,a)
    need('same-current-parent',pins,parent['nativeInputs']);need('same-current-geometry',pins,geometry['nativeInputs'])
    child=geometry['records'][RANGE]
    need('exact-owned-range-fields',[('m_center','UnityEngine.Vector3'),('m_size','UnityEngine.Vector3')],
        [(f['name'],f['typeName'])for f in child['fields']])
    need('complete-positive-child-source',True,any(not p['null']for p in child['programs']))
    owner=parent['records'][PARENT];bridge,=[r for r in owner['childLists']if r['field']['name']=='ranges']
    closed='System.Collections.Generic.List`1<'+RANGE+'>';base=image.pe.image_base
    need('exact-nominal-parent-list',closed,bridge['field']['typeName'])
    usage=derive_typed_usage_context(image,bridge['source']['typedUsage']['instruction']-base,label='functionAreaRanges.parent')
    listing=reference_list(image,pins,typed_request=usage,call_target=bridge['source']['sourceTarget'],element_type=RANGE,count_limit=LIMIT)
    witness=listing['witnessComponent'];need('actual-parent-method',usage,witness['typedRequest'])
    cap=dict(typeName=closed,headerBytes=4,countLimit=LIMIT,allowedCounts=None,wholeGrammarAdmitted=False,
        profileAdmitted=True,actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
        childBinding=dict(fieldName='ranges',typeName=closed,capability='story-function-area-range',
            readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=witness['callTargetRva']))
    return json.loads(json.dumps(dict(nativeInputs=pins,parent=bridge,typedRequest=usage,collection=listing,
        child=child,capability=cap,wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))

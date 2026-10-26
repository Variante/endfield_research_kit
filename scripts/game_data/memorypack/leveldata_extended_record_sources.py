"""Finite current host profiles with separately proved pooled lists/null child."""
ENV='Beyond.Gameplay.LevelEnvironmentVolume'
UI='Beyond.Gameplay.LevelUIData'
CLUSTER='Beyond.Gameplay.LevelNpcClusterData'
POLY='Beyond.BeyondPolyLineShape'
STRINGS='System.Collections.Generic.List`1<string>'
STRING_CAP='story-pooled-string-list'
NULL_CAP='story-polyline-shape-null'
COUNT_LIMIT=4096
from scripts.game_data.memorypack.leveldata_polyline_sources import CAP as POLY_CAP
PLANS={
 ENV:(('blendDistance','float','float32-bits'),('blendMode','HG.Rendering.Runtime.EnvBlendMode','scalar32'),
  ('envPhasePath','string','byte-payload'),('fadeInDuration','float','float32-bits'),('fadeOutDuration','float','float32-bits'),
  ('polyLineShape',POLY,'null-reference'),('position','UnityEngine.Vector3','unity-vector3-raw12'),
  ('priority','HG.Rendering.Runtime.EnvPriority','scalar32'),('rotation','UnityEngine.Vector3','unity-vector3-raw12'),
  ('scale','UnityEngine.Vector3','unity-vector3-raw12'),('volumeId','ulong','scalar64-bits'),
  ('volumeType','HG.Rendering.Runtime.EnvVolumeType','scalar32')),
 UI:(('args',STRINGS,'pooled-string-list'),('globalId','ulong','scalar64-bits'),
  ('position','UnityEngine.Vector3','unity-vector3-raw12'),('rotEuler','UnityEngine.Vector3','unity-vector3-raw12'),
  ('scale','UnityEngine.Vector3','unity-vector3-raw12'),('uiPrefabPath','string','byte-payload')),
 CLUSTER:(('npcClusterId','string','byte-payload'),('npcs',STRINGS,'pooled-string-list')),
}
FIELDS={'environmentVolumes':ENV,'levelUIs':UI,'npcClusters':CLUSTER}


def plan_for(name,positive_polyline=False):
    if type(positive_polyline)is not bool:raise ValueError('currentHostExtended.literal-polyline-mode')
    plan=PLANS[name]
    return tuple((n,t,'record'if t==POLY else k)for n,t,k in plan)if name==ENV and positive_polyline else plan


def bind_polyline(pins,join,child,capability):
    from scripts.game_data.codecs.leveldata.current_polyline import validate
    cap=child.get('capabilities',{}).get(capability,{});usage=join['typedRequest']
    if (capability!=POLY_CAP or child.get('nativeInputs')!=pins or join['typeName']!=POLY
            or usage.get('methodName')!='ReadValue'or usage.get('methodArguments')!=[POLY]
            or any(type(cap.get(k))is not int for k in('referenceReaderMethodDefinition','referenceReaderTargetRva'))
            or(cap['referenceReaderMethodDefinition'],cap['referenceReaderTargetRva'])!=(usage['methodSpec'][0],join['sourceTargetRva'])):
        raise ValueError('currentHostExtended.exact-positive-Polyline-parent')
    validate(cap)
    return dict(fieldName=join['fieldName'],typeName=POLY,capability=capability,
        readerMethodDefinition=cap['referenceReaderMethodDefinition'],sourceTargetRva=cap['referenceReaderTargetRva'],
        profileAdmitted=True,wholeGrammarAdmitted=cap.get('wholeGrammarAdmitted')is True,actualCallbackEqualsProvedChildRequired=True)


def bind_null(pins,join,child,capability):
    cap=child['capabilities'][capability];usage=join['typedRequest']
    if (capability!=NULL_CAP or child.get('nativeInputs')!=pins or join['typeName']!=POLY
            or cap.get('nullAdmitted')is not True or cap.get('positiveAdmitted')is not False
            or type(cap.get('nullMarker'))is not int or type(cap.get('consumedBytes'))is not int
            or(cap.get('typeName'),cap.get('nullAdmitted'),cap.get('positiveAdmitted'),cap.get('nullMarker'),cap.get('consumedBytes'))!=(POLY,True,False,255,1)
            or usage.get('methodName')!='ReadValue'or usage.get('methodArguments')!=[POLY]
            or type(cap.get('referenceReaderMethodDefinition'))is not int or type(cap.get('referenceReaderTargetRva'))is not int
            or(cap['referenceReaderMethodDefinition'],cap['referenceReaderTargetRva'])!=(usage['methodSpec'][0],join['sourceTargetRva'])):
        raise ValueError('currentHostExtendedRecords.exact-FF-child-parent')
    return dict(fieldName=join['fieldName'],typeName=POLY,capability=capability,
        readerMethodDefinition=cap['referenceReaderMethodDefinition'],sourceTargetRva=cap['referenceReaderTargetRva'],
        positiveAdmitted=False,nullMarker=255,consumedBytes=1,callbackSelectionConditional=True)


def bind_strings(pins,join,child,capability):
    cap=child['capabilities'][capability];usage=join['typedRequest']
    if (capability!=STRING_CAP or child.get('nativeInputs')!=pins or join['typeName']!=STRINGS
            or cap.get('elementValueType')is not False
            or(cap.get('closedListType'),cap.get('elementType'),cap.get('elementValueType'),cap.get('countLimit'))!=(STRINGS,'string',False,COUNT_LIMIT)
            or any(cap.get(key)is not True for key in('nullable','positiveCountsAdmitted','elementGrammarAdmitted','actualCallbackEqualsPooledStringRequired'))
            or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[STRINGS]
            or(cap.get('packableReaderMethodDefinition'),cap.get('packableReaderTargetRva'))!=(usage['methodSpec'][0],join['sourceTargetRva'])):
        raise ValueError('currentHostExtendedRecords.exact-pooled-string-list-parent')
    return dict(fieldName=join['fieldName'],typeName=STRINGS,capability=capability,
        readerMethodDefinition=cap['packableReaderMethodDefinition'],sourceTargetRva=cap['packableReaderTargetRva'],
        countLimit=COUNT_LIMIT,actualCallbackEqualsPooledStringRequired=True,callbackSelectionConditional=True)


def bind_program(name,source,program,pending,*,positive_polyline=False):
    plan=plan_for(name,positive_polyline)if name in PLANS else None
    if (plan is None or pending or not isinstance(program,dict)or source.get('wrappedType')!=name
            or[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']]!=[(n,t)for n,t,_ in plan]
            or program.get('memberCount')!=len(plan)
            or[(r['fieldName'],r['kind'])for r in program['reads']]!=[(n,k)for n,_,k in plan]):
        raise ValueError('currentHostExtendedRecords.exact-finite-source-program:'+name)


def derive(image,pins,host,*,types=None,positive_polyline=False):
    import json
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import generated_reader_sources,pooled_source_helper,scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
    from scripts.game_data.memorypack.skill_action_null_source import derive_reference_null
    from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
    from scripts.game_data.memorypack.pooled_string_list_sources import validate_string_components
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    from scripts.game_data.memorypack.leveldata_polyline_graph_components import derive as derive_polyline
    need=lambda k,e,a:scalar.need('currentHostExtendedRecords',k,e,a)
    need('same-current-host',pins,host['nativeInputs']);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    selected=tuple(PLANS)if types is None else types
    need('finite-selected-records',True,isinstance(selected,tuple)and 0<len(selected)<=len(PLANS)
        and len(set(selected))==len(selected)and set(selected)<=set(PLANS))
    need('literal-polyline-mode',bool,type(positive_polyline))
    wrappers={w.wrapped_type:w for w in derive_from_image(image).values()if w.wrapped_type in selected}
    need('exact-selected-wrappers',set(selected),set(wrappers))
    generated=generated_reader_sources.derive_many(image,pins,[wrappers[n].name for n in selected])
    polyline=derive_polyline(image,pins)if ENV in selected and positive_polyline else None
    null=derive_reference_null(image,pins,POLY)if ENV in selected and not positive_polyline else None
    null_child=dict(nativeInputs=pins,capabilities={NULL_CAP:null})if null is not None else None
    strings=validate_string_components(image,_load('levelscript_pooled_string_list_native.json',pins))
    need('current-pooled-string-slot5',(5,4,8),(strings['stringFormatterSlot'],strings['wireBytes'],strings['managedReferenceBytes']))
    records={};caps={}
    for name,result in zip(selected,generated['owners'],strict=True):
        need('complete-current-generated-source:'+name,'complete-reader-source-proved',
            result['status']if result['status']=='complete-reader-source-proved'else result)
        source=result['proof'];requests={};collection_children={};collections={};list_proofs={};enums={}
        for read in source['orderedSourceReads']:
            if read['declaredType']in(POLY,STRINGS):
                usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='currentHostExtendedRecords.child')
                requests[read['memberIndex']]=usage
            if read['declaredType']==STRINGS:
                collection=reference_list(image,pins,typed_request=usage,call_target=base+read['sourceTargetRva'],element_type='string',count_limit=COUNT_LIMIT)
                witness=collection['witnessComponent'];cap=dict(closedListType=STRINGS,elementType='string',elementValueType=False,
                    nullable=True,positiveCountsAdmitted=True,elementGrammarAdmitted=True,countLimit=COUNT_LIMIT,
                    actualCallbackEqualsPooledStringRequired=True,packableReaderMethodDefinition=usage['methodSpec'][0],
                    packableReaderTargetRva=witness['callTargetRva'])
                collections[STRINGS]=(STRING_CAP,'pooled-string-list',STRING_CAP)
                collection_children[read['memberIndex']]=dict(nativeInputs=pins,capabilities={STRING_CAP:cap})
                list_proofs[read['fieldName']]=dict(collection=collection,pooledString=strings,capability=cap)
            if read['kind']=='scalar32'and read['declaredType']not in('int','uint'):
                enum=read['declaredType'];need('exact-nominal-enum:'+enum,'System.Enum',ctx.parent(enum))
                backing=ctx.field(enum+'::value__');need('actual-four-byte-enum-backing',True,backing[1]in('int','uint'))
                enums[read['fieldName']]=dict(typeName=enum,backing=backing[1],field=backing)
        references={POLY:(POLY_CAP,'record',POLY_CAP)if positive_polyline else(NULL_CAP,'null-reference',NULL_CAP)}if name==ENV else{}
        reference_child=dict(nativeInputs=pins,capabilities={POLY_CAP:polyline['capability']})if polyline is not None else null_child
        program,pending=compile_member_program(source,pins,wrapper_name=wrappers[name].name,type_name=name,value4={},
            references=references,reference_children={POLY:reference_child}if name==ENV else{},typed_requests=requests,
            collections=collections,collection_children=collection_children,collection_binder=bind_strings,
            reference_binder=bind_polyline if positive_polyline else bind_null)
        bind_program(name,source,program,pending,positive_polyline=positive_polyline)
        pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrappers[name])
        need('complete-original-GetValue',True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
        need('same-owned-GetValue',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
        need('same-concrete-slot5',source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
        pooled={str(r['memberIndex']):pooled_source_helper.validate_on_image(image,base+r['sourceTargetRva'],pins)
            for r in source['orderedSourceReads']if r['kind']=='byte-payload'}
        records[name]=dict(source=source,compiled=program,pair=pair,adapter=adapter,pooled=pooled,lists=list_proofs,enumBackings=enums)
        caps[name]=dict(typeName=name,memberCount=len(PLANS[name]),nullAdmitted=True,positiveAdmitted=True,program=program,
            finiteFloatProfile=True,profileAdmitted=True,wholeGrammarAdmitted=False,countLimit=COUNT_LIMIT,enumBackings=enums,
            nullReferenceTypes=[POLY]if name==ENV and not positive_polyline else[],pooledStringListTypes=[STRINGS]if collections else[],
            positivePolylineProfile=name==ENV and positive_polyline,
            actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False)
    parents=[]
    for field,name in FIELDS.items():
        if name not in selected:continue
        declaration,read=next((f,r)for f,r in zip(host['fields'],host['program']['orderedReads'],strict=True)if f['name']==field)
        usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='currentHostExtendedRecords.parent')
        collection=reference_list(image,pins,typed_request=usage,call_target=read['sourceTarget'],element_type=name,count_limit=COUNT_LIMIT)
        parents.append(dict(field=declaration,source=read,typedRequest=usage,collection=collection,
            actualCallbackEqualsProvedChildRequired=True,callbackSelectionConditional=True))
    return json.loads(json.dumps(dict(nativeInputs=pins,records=records,parents=parents,capabilities=caps,
        nullPolyline=null,positivePolyline=polyline,pooledStrings=strings,countLimit=COUNT_LIMIT,wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))

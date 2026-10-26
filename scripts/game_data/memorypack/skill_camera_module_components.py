"""Finite concrete camera-module records and their ordinary abstract union.

Every named record requires its complete current generated four-path source,
exact named fields, own concrete cached getter/factories and inherited holder
coherence. Actual typed Unity curves retain their independent complete owner.
The thirteen union routes separately own their closed child MethodInfos and
base-interface conversions; no concrete Original registration is required for
those actual ReadPackable wrapper calls. The abstract base has no invented
concrete factory. Normal compatible callbacks/helpers, coherent initialized
contexts, disabled collector and stable disjoint storage remain conditional.
Runtime camera behavior, list/parent/root/EOF and unknown/reserved routes remain
unresolved by these stored configuration programs.
"""
import json

from scripts.game_data.memorypack import skill_camera_module_union_sources as union_source

SCHEMA='endfield.skill-camera-module-components.v1'
TYPE=union_source.TYPE
WRAPPER=union_source.WRAPPER
CAPABILITY='skill-camera-control-module'
LIST='skill-camera-control-module-list'
CURVE='UnityEngine.AnimationCurve'
STYLE='Cinemachine.CinemachineBlendDefinition+Style'
TIME='Beyond.Gameplay.View.CameraControlBlendTimeType'
PREFIX='Beyond.Gameplay.View.CameraControl'
BASE=(('limitToInputType','bool'),('supportInputTypeController','bool'),('supportInputTypeKeyboard','bool'),('supportInputTypeTouch','bool'))
LOCK_AIM=(('horizontalBaseAngleMax','float'),('horizontalBaseAngleMin','float'),('noInputDampingTime','float'),('verticalBaseValue','float'),
    ('verticalBaseValueMax','float'),('verticalBaseValueMin','float'),('verticalRelativeToTarget','bool'))
DEFINITIONS={
 'LockAim':('lock-aim',LOCK_AIM),
 'FightOrbit':('fight-orbit',(('fightCamAutoOrbitBlendTimeCurve',CURVE),('fightCamAutoOrbitCD','float'),('fightCamAutoOrbitCurve',CURVE),
    ('fightCamAutoOrbitHorizontalStep','float'),('fightCamAutoOrbitHorizontalTargetMax','float'),('fightCamAutoOrbitHorizontalTargetMin','float'),
    ('fightCamAutoOrbitHorizontalTimeCurve',CURVE),('fightCamAutoOrbitMaxHorizontalOffset','float'),('fightCamAutoOrbitMaxY','float'),
    ('fightCamAutoOrbitMinHorizontalOffset','float'),('fightCamAutoOrbitMinY','float'),('needAutoOrbit','bool'),('outFightAutoZoomDampTime','float'))),
 'AutoZoom':('auto-zoom',(('moveAutoZoomInTarget','float'),('moveAutoZoomOutAcc','float'),('moveAutoZoomOutSpeed','float'),('moveAutoZoomOutTarget','float'))),
 'AutoYaw':('auto-yaw',(('inputCoolDown','float'),('yawFollowAccelDeg','float'),('yawFollowSpeedDeg','float'),('yawFollowSpeedFactorCurve',CURVE))),
 'AutoPitch':('auto-pitch',(('adaptedToSlope','bool'),('autoPitchCancelDecel','float'),('autoPitchMax','float'),('autoPitchMin','float'),
    ('autoPitchProtectTime','float'),('autoPitchSmoothTime','float'),('autoPitchTargetMax','float'),('autoPitchTargetMin','float'),('verticalValueBySlope',CURVE))),
 'AimAssist':('aim-assist',(('dampingCurveHController',CURVE),('dampingCurveHTouch',CURVE),('dampingCurveVController',CURVE),('dampingCurveVTouch',CURVE),
    ('swipeCompensationCurveHController',CURVE),('swipeCompensationCurveHTouch',CURVE),('swipeCompensationCurveVController',CURVE),
    ('swipeCompensationCurveVTouch',CURVE),('swipeCompensationRadius','float'))),
 'LockEnemy':('lock-enemy',LOCK_AIM+(('alpha','float'),('autoLockBlendInTimeFactor','float'),('autoLockBlendOutTimeFactor','float'),('changeBlendCurve',CURVE),
    ('changeDuration','float'),('changeDurationByDeltaYaw',CURVE),('enteringCurve',CURVE),('enteringStyle',STYLE),('enteringTime','float'),
    ('enteringTimeByDeltaYaw',CURVE),('enteringTimeType',TIME),('mountPoint','Beyond.Gameplay.MountPoint'))),
 'WaterLimit':('water-limit',(('tweenSpeed','float'),('verticalLimitByHeight',CURVE))),
 'WaterDrone':('water-drone',(('moveSpeedFactorWhenLocked','float'),)),
 'RangedOrbit':('ranged-orbit',(('horizontalSpeed','float'),('maxRelativeHorizontalAngle','float'),('maxVerticalValue','float'),
    ('minRelativeHorizontalAngle','float'),('minVerticalValue','float'),('verticalSpeed','float'))),
 'RangedAutoOrbit':('ranged-auto-orbit',(('autoOrbitCd','float'),('blendCurve',CURVE),('firstAutoOrbitNoInterrupt','bool'),
    ('horizontalTargetMax','float'),('horizontalTargetMin','float'),('horizontalTimeCurve',CURVE),('maxHorizontalOffset','float'),
    ('maxVerticalValue','float'),('minHorizontalOffset','float'),('minVerticalValue','float'),('verticalTimeCurve',CURVE))),
 'ParamTween':('param-tween',(('applyRuntimeFOVOffset','bool'),('applyZoomScale','bool'),('duration','float'),('targetRuntimeFOVOffset','float'),('targetZoomScale','float'))),
 'OneTimeRotate':('one-time-rotate',(('blendStyle',STYLE),('customCurve',CURVE),('duration','float'),
    ('inputConflictStrategy',PREFIX+'OneTimeRotateConfig+InputConflictStrategy'),('totalAngle','float'))),
}
RECORDS={PREFIX+short+'Config':dict(capability='skill-camera-module-'+key,wrapperName='Beyond.MemoryPack.Beyond_Gameplay_View_CameraControl'+short+'ConfigForMemoryPack',
    cacheOffset=32 if short=='LockEnemy'else 24,members=BASE+fields)for short,(key,fields)in DEFINITIONS.items()}
REFERENCES={CURVE:('curve-profile','curve-profile','curve-profile')}
KINDS={'bool':'bool-byte','float':'float32-bits',CURVE:'curve-profile',STYLE:'scalar32',TIME:'scalar32',
    'Beyond.Gameplay.MountPoint':'scalar32',PREFIX+'OneTimeRotateConfig+InputConflictStrategy':'scalar32'}


def need(check,condition):
    if not condition:raise ValueError('skillCameraModuleComponents.'+check)


def ordered_reads(name):
    need('finite-record',name in RECORDS)
    return[dict(memberIndex=i,fieldName=field,kind=KINDS[typ],childCapability='curve-profile'if typ==CURVE else None)
        for i,(field,typ)in enumerate(RECORDS[name]['members'])]


def bind_child(route,source,compiled,pins):
    name=route.get('wrappedType');need('finite-actual-route',name in RECORDS and type(route.get('tag'))is int and 0<=route['tag']<13)
    spec=RECORDS[name]
    need('actual-closed-wrapper',route.get('wrapperName')==spec['wrapperName']and route.get('typedRequest',{}).get('methodArguments')==[spec['wrapperName']])
    need('own-complete-concrete-source',source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==pins and(source.get('wrappedType'),source.get('wrapperName'))==(name,spec['wrapperName'])
        and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False and source.get('wholeOwnerAdmitted')is False)
    reads=source.get('orderedSourceReads',[])
    need('exact-literal-named-member-order',[(r.get('fieldName'),r.get('declaredType'))for r in reads]==list(spec['members'])
        and[r.get('memberIndex')for r in reads]==list(range(len(spec['members'])))and all(type(r.get('memberIndex'))is int for r in reads))
    order=ordered_reads(name);required=['curve-profile']if any(t==CURVE for f,t in spec['members'])else[]
    need('complete-exact-field-program',type(compiled.get('memberCount'))is int and compiled['memberCount']==len(order)
        and compiled.get('reads')==order and compiled.get('requiredCapabilities')==required
        and all(type(r.get('memberIndex'))is int for r in compiled['reads']))
    curve_reads=[r for r in reads if r['declaredType']==CURVE];bindings=compiled.get('childBindings',[])
    need('every-exact-ordinary-curve-source-join',len(bindings)==len(curve_reads)and all(
        (b.get('fieldName'),b.get('typeName'),b.get('capability'))==(r['fieldName'],CURVE,'curve-profile')
        and type(b.get('readerMethodDefinition'))is int and type(b.get('sourceTargetRva'))is int
        and b['readerMethodDefinition']==r.get('context',{}).get('methodSpec',[None])[0]
        and b['sourceTargetRva']==r.get('sourceTargetRva')for b,r in zip(bindings,curve_reads)))
    life=source.get('lifecycle',{});cache=[spec['wrapperName'],name,spec['cacheOffset']];base=[WRAPPER,TYPE,16]
    getter=life.get('coherentGetter',{})
    need('exact-physical-base-and-concrete-cache',life.get('baseHolder')==base and life.get('typedCache')==cache
        and getter.get('baseHolder')==base and getter.get('typedCache')==cache and getter.get('coherentNonNullSamePointerReturn')is True
        and life.get('originalRegistrationRequired')is False and life.get('GetValue',{}).get('method',[None,None,None])[1:3]==[spec['wrapperName'],'GetValue'])
    constructed=source.get('constructedGetterJoin',{})
    need('constructed-inherited-holder-coherence',constructed.get('constructedReferenceOffsets')==[16,spec['cacheOffset']]
        and constructed.get('inheritedCacheCoherenceAssumed')is False and len(constructed.get('setters',[]))==len(order))
    paths=source.get('programs',[])
    need('all-four-complete-source-frames',len(paths)==4 and all(type(p.get('existing'))is bool and type(p.get('wrapperNull'))is bool
        and p.get('frame',{}).get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths)
        and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)})
    factories=life.get('factories',[])
    need('both-actual-concrete-factories',len(factories)==2 and{f['method'][2]for f in factories}=={'.ctor','CreateInstance'}
        and all(f.get('originalAllocation',{}).get('typeName')==name for f in factories))
    return dict(typeName=name,wrapperName=spec['wrapperName'],memberCount=len(order),orderedReads=order,nullable=True,nullMarker=255,
        nullAdmitted=True,wholeGrammarAdmitted=True,ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        generatedWrapperOnly=True,ordinaryOriginalReadValueAdmitted=False,callbackSelectionConditional=True,wholeOwnerAdmitted=False)


def _derive_on_curve(image,pins,curve):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.generated_reader_sources import derive_many
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    _publication_gate(image,pins);union=union_source.derive_source(image,pins)
    need('complete-source-union',union.get('nativeInputs')==pins and union.get('schema')==union_source.SCHEMA
        and union.get('status')=='validated-conditional-camera-module-source'and union.get('baseGetterSemanticsAdmitted')is True
        and all(union.get(k)is False for k in('concreteGetterSemanticsAdmitted','concreteFactorySemanticsAdmitted','concreteChildGrammarAdmitted','wholeUnionAdmitted','wholeOwnerAdmitted')))
    routes=union['programs'];need('complete-actual-thirteen-route-domain',len(routes)==13 and[r['tag']for r in routes]==list(range(13))
        and{r['wrappedType']for r in routes}==set(RECORDS)and len({r['wrapperName']for r in routes})==13)
    generated=derive_many(image,pins,[r['wrapperName']for r in routes]);need('same-selected-concrete-source',generated['nativeInputs']==pins)
    caps={};proofs={};required=set();joins=[]
    for route,result in zip(routes,generated['owners'],strict=True):
        if result.get('status')!='complete-reader-source-proved':raise ValueError('skillCameraModuleComponents.complete-reader:'+route['wrapperName']+':'+str(result.get('reason'))[:2600])
        source=result['proof'];requests={r['memberIndex']:derive_typed_usage_context(image,r['context']['instructionRva'],label='cameraModule.curve')
            for r in source['orderedSourceReads']if r['declaredType']==CURVE}
        compiled,pending=compile_member_program(source,pins,wrapper_name=route['wrapperName'],type_name=route['wrappedType'],value4={},
            references=REFERENCES,reference_children={CURVE:curve},typed_requests=requests)
        need('all-independent-member-children:'+route['wrappedType'],pending==[])
        cap=bind_child(route,source,compiled,pins);key=RECORDS[route['wrappedType']]['capability'];caps[key]=cap
        required.update(compiled['requiredCapabilities']);proofs[route['wrappedType']]=dict(source=source,compiled=compiled,typedRequests=requests)
        joins.append(dict(tag=route['tag'],wrappedType=route['wrappedType'],wrapperName=route['wrapperName'],childCapability=key))
    reader=reference_reader_abi(image,pins)
    need('same-ordinary-union-reader-definition',reader['referenceReaderMethodDefinition']==union['proof']['referencePackable']['valueContext']['readerMethodDefinition'])
    caps[CAPABILITY]=dict(typeName=TYPE,wrapperName=WRAPPER,nullable=True,nullMarker=255,nullAdmitted=True,wholeGrammarAdmitted=True,
        ordinaryOriginalReadValueAdmitted=True,baseGetterSemanticsProved=True,concreteChildGrammarsProved=True,allConcreteFactoriesProved=True,
        supportedShortTags=list(range(13)),extendedTagsAdmitted=False,reservedMarkersAdmitted=False,routes=joins,
        **{k:reader[k]for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')},callbackSelectionConditional=True,wholeOwnerAdmitted=False)
    identity={k:curve['capabilities']['curve-profile'][k]for k in('typeName','referenceReaderMethodDefinition','referenceReaderTargetRva')}
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-camera-module-components',nativeInputs=pins,capabilities=caps,
        requiredExternalCapabilities=sorted(required),requiredExternalCapabilityIdentities={'curve-profile':identity},
        proof=dict(union=union,concreteRecords=proofs,curve=curve,referenceReader=reader),wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Complete actual thirteen short/FF union paths and base conversions; every concrete four-path source/lifecycle/named primitive field and independently typed ordinary Unity curve.',
            conditional=__doc__,structuralOnly='Stored camera module configuration.',
            unresolved=['actual enclosing list/parent/action/root/EOF','existing-output union alternatives','runtime camera/provider behavior','reserved/extended tags']))))


def derive(image,pins):
    from scripts.game_data.memorypack.skill_animation_curve_sources import derive as source
    curve=source(image,pins)
    envelope=dict(nativeInputs=pins,capabilities={'curve-profile':curve['capabilities']['skill-animation-curve']},proof=curve)
    return _derive_on_curve(image,pins,envelope)

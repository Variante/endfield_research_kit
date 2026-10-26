"""Finite CameraControlStateCustomConfig source and ordinary reference ABI.

The complete current generated MC34 caller owns all new/existing/FF transfers,
named setters, exact InitialParam raw24 source and complete normal frames.
Concrete factory/GetValue and the ordinary canonical adapter/Reader are proved
independently. This source owner does not yet admit the delegated enum/module
lists or the whole positive record. Transition conditions and Unity curves
keep independent list/reference owners; a managed width supplies no bytes.

Ready coherent contexts/callbacks, compatible originals, normal typed helpers
and allocation, disabled collector and stable disjoint buffered storage remain
conditions. Stored configuration proves no camera execution, live provider,
enclosing action, root or physical EOF.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

SCHEMA='endfield.skill-camera-custom-config-source.v1'
TYPE='Beyond.Gameplay.View.CameraControlStateCustomConfig'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_View_CameraControlStateCustomConfigForMemoryPack'
CAPABILITY='skill-camera-control-custom-config'
INITIAL='Beyond.Gameplay.View.CameraControlStateInitialParam'
CURVE='UnityEngine.AnimationCurve'
CONDITION='Beyond.Gameplay.View.CameraControlState+TransitionConditionAnd'
ENUM='Beyond.Gameplay.View.CameraControlModuleType'
MODULE='Beyond.Gameplay.View.CameraControlModuleConfig'
LIST=lambda name:'System.Collections.Generic.List`1<'+name+'>'
MEMBERS=(
 ('additiveHorizontalAngle','float'),('additiveVerticalValue','float'),('additiveZoomScale','float'),
 ('blendInCustomCurve',CURVE),('blendInStyle','Cinemachine.CinemachineBlendDefinition+Style'),('blendInTime','float'),
 ('blendInTimeByDeltaVertical',CURVE),('blendInTimeByDeltaYaw',CURVE),('blendOutCustomCurve',CURVE),
 ('blendOutStyle','Cinemachine.CinemachineBlendDefinition+Style'),('blendOutTime','float'),
 ('blendOutTimeByDeltaVertical',CURVE),('blendOutTimeByDeltaYaw',CURVE),('blendPriority','float'),
 ('blendTimeType','Beyond.Gameplay.View.CameraControlBlendTimeType'),('disabledModules',LIST(ENUM)),
 ('disablePlayerInputInState','bool'),('disablePlayerInputOnBlendIn','bool'),('disablePlayerInputOnBlendOut','bool'),
 ('enterConditionsOr',LIST(CONDITION)),('exitParam',INITIAL),('immediateEnter','bool'),('initialParam',INITIAL),
 ('keepAdditiveParamOnLeave','bool'),('keepCollisionStatusOnTransition','bool'),('leaveConditionsOr',LIST(CONDITION)),
 ('moduleConfigs',LIST(MODULE)),('overrideLowerParamsToDefault','bool'),('priority','float'),('recoverParamWhenExit','bool'),
 ('useAdditiveParam','bool'),('useDistanceRatio','bool'),('useExitParam','bool'),('useInitialParam','bool'))
PENDING_CHILDREN=[dict(memberIndex=i,fieldName=n,typeName=t,grammarAdmitted=False)
    for i,(n,t)in enumerate(MEMBERS)if i in(15,26)]


def require_source(source,pins):
    need('camera-custom-own-selected-source',True,source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==pins and(source.get('wrappedType'),source.get('wrapperName'))==(TYPE,WRAPPER)
        and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False
        and source.get('wholeOwnerAdmitted')is False)
    need('camera-custom-exact-34-named-fields',list(MEMBERS),
        [(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])])
    need('camera-custom-literal-source-indices',True,
        [r.get('memberIndex')for r in source['orderedSourceReads']]==list(range(34))
        and all(type(r.get('memberIndex'))is int for r in source['orderedSourceReads']))
    life=source.get('lifecycle',{})
    need('camera-custom-own-holder',True,life.get('directHolderMode')is True and life.get('typedCache')is None
        and life.get('baseHolder')==[WRAPPER,TYPE,16])
    paths=source.get('programs',[])
    need('camera-custom-four-complete-return-frames',True,len(paths)==4 and all(type(p.get('existing'))is bool
        and type(p.get('wrapperNull'))is bool and p.get('frame',{}).get('entryRspRestored')is True
        and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths)
        and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)})
    for index in(20,22):
        read=source['orderedSourceReads'][index]
        need('camera-custom-explicit-InitialParam-source:'+str(index),'value24:'+INITIAL,read.get('kind'))
    return source


def derive_caller(image,pins):
    """Fresh complete four-path caller; no ordinary adapter or child claim."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.generated_reader_sources import derive as caller
    from scripts.game_data.memorypack.skill_camera_custom_factory_sources import prove
    from functools import partial
    _publication_gate(image,pins)
    source=caller(image,pins,WRAPPER,typed_factory_prover=partial(prove,pins=pins));require_source(source,pins)
    _publication_gate(image,pins)
    return source


def derive_source(image,pins):
    """Fresh full source/ordinary ABI only; pending children grant no codec."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.pointer_param import leaf
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    _publication_gate(image,pins)
    source=derive_caller(image,pins)
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==WRAPPER]
    pair=derive_pair(image,TYPE,WRAPPER);adapter=derive_adapter(image,pins,pair,wrapper)
    need('camera-custom-own-canonical-GetValue',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
    getter=leaf(image,image.pe.image_base+adapter['getterMethod'][3],['488B4110','C3'])
    need('camera-custom-own-canonical-reader',source['method'],adapter['pairForwarder']['readerMethod'])
    reader=reference_reader_abi(image,pins)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        typeName=TYPE,wrapperName=WRAPPER,memberCount=34,pendingChildren=PENDING_CHILDREN,
        proof=dict(source=source,pair=pair,adapter=adapter,getter=getter,referenceReader=reader),
        capabilities={},ordinarySourceAndAdapterProved=True,wholeGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Own complete MC34 generated four-path source/frames, typed raw InitialParam24 source/setters, own constructor/GetValue and ordinary canonical reference adapter/Reader.',
            conditional=__doc__,structuralOnly='Stored camera configuration.',
            unresolved=['nominal CameraControlModuleType list callback/framing','CameraControlModuleConfig child/list grammar',
                'fresh independent Unity curves and transition-list joins','positive record/action/root/physical EOF','runtime camera/provider selection']))))

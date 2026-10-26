"""Finite generated concrete wrapper wire plans; Original adapter is separate."""

from scripts.game_data.memorypack.leveldata_function_specific_sources import CHILDREN

TAGS=(0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 17)
PLANS={
 'Beyond.Gameplay.LevelFunctionAreaData+AmbienceCameraData':(
  ('blendInStyle', 'Cinemachine.CinemachineBlendDefinition+Style', 'scalar32'),
  ('blendInTime', 'float', 'float32-bits'),
  ('blendOutStyle', 'Cinemachine.CinemachineBlendDefinition+Style', 'scalar32'),
  ('blendOutTime', 'float', 'float32-bits'),
  ('duration', 'float', 'float32-bits'),
  ('enableHorizontalLimit', 'bool', 'bool-byte'),
  ('enableVerticalLimit', 'bool', 'bool-byte'),
  ('enableZoomLimit', 'bool', 'bool-byte'),
  ('initialHorizontalAngle', 'float', 'float32-bits'),
  ('initialVerticalValue', 'float', 'float32-bits'),
  ('maxHorizontalAngle', 'float', 'float32-bits'),
  ('maxVerticalValue', 'float', 'float32-bits'),
  ('maxZoom', 'float', 'float32-bits'),
  ('minHorizontalAngle', 'float', 'float32-bits'),
  ('minVerticalValue', 'float', 'float32-bits'),
  ('minZoom', 'float', 'float32-bits'),
  ('screenX', 'float', 'float32-bits'),
  ('screenY', 'float', 'float32-bits'),
  ('useInitialParam', 'bool', 'bool-byte'),
  ('useLocalRotation', 'bool', 'bool-byte'),
 ),
 'Beyond.Gameplay.LevelFunctionAreaData+BlightMiasmaAreaData':(
  ('areaLevel', 'int', 'scalar32'),
 ),
 'Beyond.Gameplay.LevelFunctionAreaData+BlockAIBarkData':(
  ('defaultOn', 'bool', 'bool-byte'),
 ),
 'Beyond.Gameplay.LevelFunctionAreaData+CameraAddControlStateData':(
  ('blendInStyle', 'Cinemachine.CinemachineBlendDefinition+Style', 'scalar32'),
  ('blendInTime', 'float', 'float32-bits'),
  ('blendOutStyle', 'Cinemachine.CinemachineBlendDefinition+Style', 'scalar32'),
  ('blendOutTime', 'float', 'float32-bits'),
  ('multipleCCS', 'bool', 'bool-byte'),
  ('overrideBlendIn', 'bool', 'bool-byte'),
  ('overrideBlendOut', 'bool', 'bool-byte'),
  ('state2CheckAngle', 'float', 'float32-bits'),
  ('state2Config', 'string', 'byte-payload'),
  ('stateCheckAngle', 'float', 'float32-bits'),
  ('stateConfig', 'string', 'byte-payload'),
 ),
 'Beyond.Gameplay.LevelFunctionAreaData+CameraLookAtData':(
  ('blendInStyle', 'Cinemachine.CinemachineBlendDefinition+Style', 'scalar32'),
  ('blendInTime', 'float', 'float32-bits'),
  ('blendOutStyle', 'Cinemachine.CinemachineBlendDefinition+Style', 'scalar32'),
  ('blendOutTime', 'float', 'float32-bits'),
  ('duration', 'float', 'float32-bits'),
  ('horizontalSpeedFactor', 'float', 'float32-bits'),
  ('lookAtRotationPitch', 'float', 'float32-bits'),
  ('lookAtRotationYaw', 'float', 'float32-bits'),
  ('useLocalRotation', 'bool', 'bool-byte'),
  ('useVerticalValue', 'bool', 'bool-byte'),
  ('verticalSpeedFactor', 'float', 'float32-bits'),
  ('verticalValue', 'float', 'float32-bits'),
  ('zoomScale', 'float', 'float32-bits'),
 ),
 'Beyond.Gameplay.LevelFunctionAreaData+CameraVolumeData':(
  ('blendStyle', 'Cinemachine.CinemachineBlendDefinition+Style', 'scalar32'),
  ('duration', 'float', 'float32-bits'),
  ('fov', 'float', 'float32-bits'),
  ('id', 'ulong', 'scalar64-bits'),
  ('needInterruptMainHudAction', 'bool', 'bool-byte'),
  ('overrideBlend', 'bool', 'bool-byte'),
  ('pos', 'UnityEngine.Vector3', 'unity-vector3-raw12'),
  ('rot', 'UnityEngine.Vector3', 'unity-vector3-raw12'),
  ('tweenTime', 'float', 'float32-bits'),
  ('useBlackScreen', 'bool', 'bool-byte'),
  ('useOnce', 'bool', 'bool-byte'),
  ('useYawCheck', 'bool', 'bool-byte'),
 ),
 'Beyond.Gameplay.LevelFunctionAreaData+CarryTagZoneData':(
  ('zoneTag', 'Beyond.Gameplay.Core.GameplayTag', 'gameplay-tag32'),
 ),
 'Beyond.Gameplay.LevelFunctionAreaData+DitherFactoryZoneData':(
  ('center', 'UnityEngine.Vector3', 'unity-vector3-raw12'),
  ('size', 'UnityEngine.Vector3', 'unity-vector3-raw12'),
 ),
 'Beyond.Gameplay.LevelFunctionAreaData+ForbidGeneralAbilityZoneData':(
  ('abilityType', 'Beyond.Gameplay.EForbidGeneralAbilityType', 'scalar32'),
 ),
 'Beyond.Gameplay.LevelFunctionAreaData+HideNpcInRangeParams':(
  ('npcTypes', 'Beyond.Gameplay.Core.HideNpcTypeMask', 'scalar32'),
 ),
 'Beyond.Gameplay.LevelFunctionAreaData+RadioTriggerZoneData':(
  ('hideAfterMissionId', 'string', 'byte-payload'),
  ('hideBeforeMissionId', 'string', 'byte-payload'),
  ('hideCompleteMissionId', 'string', 'byte-payload'),
  ('prtsId', 'string', 'byte-payload'),
  ('radioId', 'string', 'byte-payload'),
  ('triggerId', 'ulong', 'scalar64-bits'),
  ('useRadioTriggerOnce', 'bool', 'bool-byte'),
 ),
 'Beyond.Gameplay.LevelFunctionAreaData+RepatriateZoneData':(
  ('lifeRatio', 'float', 'float32-bits'),
  ('useRepatriateZoneType', 'bool', 'bool-byte'),
 ),
 'Beyond.Gameplay.LevelFunctionAreaData+RopeCameraData':(
  ('fov', 'float', 'float32-bits'),
  ('pos', 'UnityEngine.Vector3', 'unity-vector3-raw12'),
  ('rot', 'UnityEngine.Vector3', 'unity-vector3-raw12'),
 ),
 'Beyond.Gameplay.LevelFunctionAreaData+VisitLocStatData':(
  ('saveId', 'int', 'scalar32'),
 ),
}


def bind_program(name,source,program,pending):
    plan=PLANS.get(name)
    if (plan is None or pending or not isinstance(program,dict)or source.get('wrappedType')!=name
            or [(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]!=[(n,t)for n,t,k in plan]
            or type(program.get('memberCount'))is not int or program['memberCount']!=len(plan)
            or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
            or [(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
                (i,n,k,'byte-payload'if k=='byte-payload'else None)for i,(n,t,k)in enumerate(plan)]
            or program.get('requiredCapabilities')!=(['byte-payload']if any(k=='byte-payload'for n,t,k in plan)else[])
            or program.get('childBindings')!=[]):
        raise ValueError('storySpecificLeaves.exact-finite-wrapper-program:'+str(name))


def derive(image,pins):
    """Fresh wrapper sources only; no concrete Original adapter is selected."""
    import json
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import generated_reader_sources,pooled_source_helper,scalar_param_native as scalar,buff_gameplay_tag_native
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    need=lambda k,e,a:scalar.need('storySpecificLeaves',k,e,a)
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()if w.wrapped_type in PLANS}
    need('finite-explicit-wrapper-set',set(PLANS),set(wrappers))
    generated=generated_reader_sources.derive_many(image,pins,[wrappers[n].name for n in PLANS])
    tag=buff_gameplay_tag_native.validate_on_image(image,pins)
    need('independent-GameplayTag-source','validated',tag.get('status'))
    records={};caps={}
    for name,row in zip(PLANS,generated['owners'],strict=True):
        need('complete-own-wrapper-source:'+name,'complete-reader-source-proved',row['status']if row['status']=='complete-reader-source-proved'else row)
        source=row['proof'];plan=PLANS[name]
        need('exact-reviewed-field-plan:'+name,[(n,t)for n,t,k in plan],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
        program,pending=compile_member_program(source,pins,wrapper_name=wrappers[name].name,type_name=name,
            value4={'Beyond.Gameplay.Core.GameplayTag':tag})
        bind_program(name,source,program,pending)
        enum_backings={}
        for field,declared,kind in plan:
            if kind!='scalar32'or declared=='int':continue
            need('nominal-enum:'+declared,'System.Enum',ctx.parent(declared))
            value=ctx.field(declared+'::value__');need('enum-32-backing',True,value[1]in('int','uint'))
            enum_backings[field]=dict(typeName=declared,backing=value[1],field=list(value))
        pool={str(read['memberIndex']):pooled_source_helper.validate_on_image(image,base+read['sourceTargetRva'],pins)
            for read in source['orderedSourceReads']if read['kind']=='byte-payload'}
        need('owned-full-original-reference',True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
        concrete=source['lifecycle']['concreteFormatter']['method']
        need('actual-own-concrete-callback',wrappers[name].name+'+'+wrappers[name].name.rsplit('.',1)[-1]+'Formatter',concrete[1])
        records[name]=dict(source=source,compiled=program,pooled=pool,enumBackings=enum_backings)
        caps[name]=dict(typeName=name,wrapperName=wrappers[name].name,memberCount=len(plan),program=program,enumBackings=enum_backings,
            concreteFormatterMethod=concrete,originalGetterMethod=source['lifecycle']['GetValue']['method'],
            nullAdmitted=True,positiveAdmitted=True,profileAdmitted=True,finiteFloatProfile=True,
            wrapperWireGrammarAdmitted=True,wholeGrammarAdmitted=False,
            actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
            concreteOriginalAdapterUsed=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.story-function-specific-wrapper-children.v1',
        status='validated-finite-wrapper-child-grammars',nativeInputs=pins,records=records,capabilities=caps,gameplayTag=tag,
        wholeUnionAdmitted=False,wholeOwnerAdmitted=False,concreteOriginalAdapterUsed=False,
        evidenceBoundary=dict(exact='Finite explicit nominal ordered wrapper fields, complete generated new/existing/FF callers/lifecycles and concrete callbacks; each primitive/Vector3/GameplayTag/pooled source independently joined.',
            conditional='Matching ready concrete wrapper callback and contexts, buffered disjoint input/output/frame, coherent original/cache and normal helper/allocation/barrier effects. Base union selection and inherited Original conversion are independently required.',
            unresolved=['four other concrete route grammars','base union source and inherited conversion','actual enclosing list/parent',
                'runtime provider/default/override selection','physical EOF/whole owner']))))

"""Finite ordinary action records with independently owned reference children.

Only the named records below enter this owner. Complete generated caller,
new/existing/FF frames, concrete construction/cache/GetValue and canonical
ordinary adapter must precede the actual typed child Reader joins. Scalars
and pools use their source programs; BlackboardDouble, Target, Sequence and
Unity curve each retain their own wire/lifecycle capability. This supplies no
list count, enclosing action tag or whole SkillData/EOF. Coherent initialized
contexts, matching callbacks, normal typed allocation/constructor/helpers,
disabled collector and disjoint stable storage are conditions; runtime
effects/provider selection and unselected refill/error paths remain open.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

DOUBLE='Beyond.Blackboard+BlackboardDouble'
TARGET='Beyond.Gameplay.Core.TargetSettings'
SEQUENCE='Beyond.Gameplay.Core.SequenceActionData'
CURVE='UnityEngine.AnimationCurve'
VECTOR='Beyond.Blackboard+BlackboardVector3'
LINE_END='Beyond.Gameplay.Core.Selector+HitBoxFinder+LineEndPoint'
HITBOX='Beyond.Gameplay.Core.Selector+HitBoxFinder+ShapeData'
IMPULSE='Beyond.Gameplay.Core.CameraImpulseAction+ImpulseDefinitionData'
ENVELOPE='Cinemachine.CinemachineImpulseManager+EnvelopeDefinition'
VALUE_TYPES={ENVELOPE:('skill-impulse-envelope','root-record','skill-impulse-envelope')}
REFERENCES={DOUBLE:('skill-blackboard-double','blackboard-double','scalar-payload'),
    TARGET:('target-profile','target-profile','target-profile'),SEQUENCE:('SequenceActionData','sequence-profile','SequenceActionData'),
    CURVE:('curve-profile','curve-profile','curve-profile'),
    VECTOR:('skill-blackboard-vector3','blackboard-vector3','blackboard-vector3'),
    LINE_END:('skill-selector-hitbox-line-end','action-nested-record-profile','skill-selector-hitbox-line-end')}
RECORDS={
 IMPULSE:dict(capability='skill-action-impulse-definition',
    wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_CameraImpulseAction_ImpulseDefinitionDataForMemoryPack',members=(
        ('amplitudeGain','float','single-bits',None),('cameraShake2D','bool','bool',None),
        ('customImpulseShape',CURVE,'curve-profile','curve-profile'),
        ('directionMode','Cinemachine.CinemachineImpulseManager+ImpulseEvent+DirectionMode','enum32',None),
        ('dissipationDistance','float','single-bits',None),
        ('dissipationMode','Cinemachine.CinemachineImpulseManager+ImpulseEvent+DissipationMode','enum32',None),
        ('dissipationRate','float','single-bits',None),('frequencyGain','float','single-bits',None),
        ('impactRadius','float','single-bits',None),('impulseChannel','int','int32',None),('impulseDuration','float','single-bits',None),
        ('impulseShape','Cinemachine.CinemachineImpulseDefinition+ImpulseShapes','enum32',None),
        ('impulseType','Cinemachine.CinemachineImpulseDefinition+ImpulseTypes','enum32',None),
        ('propagationSpeed','float','single-bits',None),('randomize','bool','bool',None),
        ('rawSignalPath','string','pooled-string','byte-payload'),
        ('repeatMode','Cinemachine.CinemachineImpulseDefinition+RepeatMode','enum32',None),
        ('timeEnvelope',ENVELOPE,'root-record','skill-impulse-envelope'))),
 'Beyond.Gameplay.Core.MoveToAction+SubSpeed':dict(capability='skill-action-move-sub-speed',
    wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_MoveToAction_SubSpeedForMemoryPack',members=(
        ('fixedSpeed',DOUBLE,'blackboard-double','scalar-payload'),('rootMotionAnimKey','string','pooled-string','byte-payload'),
        ('rootMotionScale',DOUBLE,'blackboard-double','scalar-payload'),('speedCurve',CURVE,'curve-profile','curve-profile'),
        ('speedType','Beyond.Gameplay.Core.MoveToAction+SpeedType','enum32',None))),
 LINE_END:dict(capability='skill-selector-hitbox-line-end',
    wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_HitBoxFinder_LineEndPointForMemoryPack',members=(
        ('contextKey','string','pooled-string','byte-payload'),('mountPoint','Beyond.Gameplay.MountPoint','enum32',None),
        ('source','Beyond.Gameplay.ActionTargetType','enum32',None))),
 HITBOX:dict(capability='skill-selector-hitbox-shape',
    wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_HitBoxFinder_ShapeDataForMemoryPack',members=(
        ('angle',DOUBLE,'blackboard-double','scalar-payload'),
        ('castDirection','Beyond.Gameplay.Core.Selector+HitBoxFinder+CastDirection','enum32',None),
        ('centerOffset',VECTOR,'blackboard-vector3','blackboard-vector3'),
        ('directionRef','Beyond.Gameplay.Core.Selector+HitBoxFinder+DirectionRef','enum32',None),
        ('dirRefMountPoint','Beyond.Gameplay.MountPoint','enum32',None),('enablePreview','bool','bool',None),
        ('eulerAngle',VECTOR,'blackboard-vector3','blackboard-vector3'),('height',DOUBLE,'blackboard-double','scalar-payload'),
        ('hitEffectTowardsType','Beyond.Gameplay.Core.Selector+HitBoxFinder+HitEffectTowardsType','enum32',None),
        ('innerRadius',DOUBLE,'blackboard-double','scalar-payload'),('limitAngle','bool','bool',None),('limitHeight','bool','bool',None),
        ('lineBoxSize',VECTOR,'blackboard-vector3','blackboard-vector3'),('lineEnd',LINE_END,'action-nested-record-profile','skill-selector-hitbox-line-end'),
        ('lineLengthOffset',DOUBLE,'blackboard-double','scalar-payload'),('lineRadius',DOUBLE,'blackboard-double','scalar-payload'),
        ('lineShapeType','Beyond.Gameplay.Core.Selector+HitBoxFinder+LineShapeType','enum32',None),
        ('lineStart',LINE_END,'action-nested-record-profile','skill-selector-hitbox-line-end'),
        ('maxHeight',DOUBLE,'blackboard-double','scalar-payload'),('outerRadius',DOUBLE,'blackboard-double','scalar-payload'),
        ('positionRef','Beyond.Gameplay.Core.Selector+HitBoxFinder+PositionRef','enum32',None),('posRefMP','Beyond.Gameplay.MountPoint','enum32',None),
        ('radius',DOUBLE,'blackboard-double','scalar-payload'),('shapeType','Beyond.Gameplay.Core.Selector+HitBoxFinder+ShapeType','enum32',None),
        ('size',VECTOR,'blackboard-vector3','blackboard-vector3'),('useDirection','bool','bool',None),('useFullRotation','bool','bool',None))),
 'Beyond.Gameplay.Core.EnablePartsAction+DisablePartParam':dict(capability='skill-action-disable-part-parameters',
    wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_EnablePartsAction_DisablePartParamForMemoryPack',members=(
        ('clearBuff','bool','bool',None),)),
 'Beyond.Gameplay.Core.EnablePartsAction+EnablePartParam':dict(capability='skill-action-enable-part-parameters',
    wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_EnablePartsAction_EnablePartParamForMemoryPack',members=(
        ('hpSetType','Beyond.GEnums.PartModifyAttrType','enum32',None),('hpValue',DOUBLE,'blackboard-double','scalar-payload'),
        ('poiseSetType','Beyond.GEnums.PartModifyAttrType','enum32',None),('poiseValue',DOUBLE,'blackboard-double','scalar-payload'),
        ('setHp','bool','bool',None),('setPoise','bool','bool',None))),
 'Beyond.Gameplay.Core.LaunchProjectile+PresetPointDef':dict(capability='skill-action-projectile-preset-point',
    wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_LaunchProjectile_PresetPointDefForMemoryPack',members=(
        ('presetPoint',TARGET,'target-profile','target-profile'),('presetPointKey','string','pooled-string','byte-payload'))),
 'Beyond.Gameplay.Core.ComboCacheAction+Data+BattleCmdMappingModifierData':dict(capability='skill-action-battle-command-mapping-modifier',
    wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_ComboCacheAction_Data_BattleCmdMappingModifierDataForMemoryPack',members=(
        ('cacheEndByAction','bool','bool',None),('cacheTime',DOUBLE,'blackboard-double','scalar-payload'),
        ('clearOffsetTargetSkillIdOnEnd','bool','bool',None),('cmdType','Beyond.Gameplay.Core.AbilitySystem+ComboController+BattleCommandType','enum32',None),
        ('overrideCacheTime','bool','bool',None),('skillId','string','pooled-string','byte-payload'))),
 'Beyond.Gameplay.Core.OverrideRawAttributeAction+AttributeOverrideEntry':dict(capability='skill-action-attribute-override-entry',
    wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_OverrideRawAttributeAction_AttributeOverrideEntryForMemoryPack',members=(
        ('attributeType','Beyond.GEnums.AttributeType','enum32',None),('overrideValue',DOUBLE,'blackboard-double','scalar-payload'))),
 'Beyond.Gameplay.Core.ReadSkillSettingData+ReadData':dict(capability='skill-action-read-skill-setting',
    wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_ReadSkillSettingData_ReadDataForMemoryPack',members=(
        ('column',DOUBLE,'blackboard-double','scalar-payload'),('dataKey','string','pooled-string','byte-payload'),
        ('enhanceAttributeSource',TARGET,'target-profile','target-profile'),('storeKey','string','pooled-string','byte-payload'))),
 'Beyond.Gameplay.Core.ReceiveMoveInputAction+Data+MoveParamData':dict(capability='skill-action-move-parameters',
    wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_ReceiveMoveInputAction_Data_MoveParamDataForMemoryPack',members=(
        ('disableDynamicPush','bool','bool',None),('faceToMoveDir','bool','bool',None),
        ('inputDirection','Beyond.Gameplay.Core.ReceiveMoveInputAction+DirectionType','enum32',None),('overrideRotateSpeed','bool','bool',None),
        ('rotateSpeed',DOUBLE,'blackboard-double','scalar-payload'),('speed',DOUBLE,'blackboard-double','scalar-payload'),
        ('speedCurve',CURVE,'curve-profile','curve-profile'),('speedScale',DOUBLE,'blackboard-double','scalar-payload'),
        ('speedType','Beyond.Gameplay.Core.ReceiveMoveInputAction+SpeedType','enum32',None))),
 'Beyond.Gameplay.Core.SwitchAction+Option':dict(capability='skill-action-switch-option',
    wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_SwitchAction_OptionForMemoryPack',members=(
        ('actionData',SEQUENCE,'sequence-profile','SequenceActionData'),('value',DOUBLE,'blackboard-double','scalar-payload'))),
 'Beyond.Gameplay.Core.TeleportPosSelectAction+FixDistanceData':dict(capability='skill-action-teleport-fixed-distance',
    wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_TeleportPosSelectAction_FixDistanceDataForMemoryPack',members=(
        ('distance',DOUBLE,'blackboard-double','scalar-payload'),('excludeCurrentPos','bool','bool',None),('useAddScoreToPrevSide','bool','bool',None))),
 'Beyond.Gameplay.Core.TeleportPosSelectAction+RangedData':dict(capability='skill-action-teleport-ranged',
    wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_TeleportPosSelectAction_RangedDataForMemoryPack',members=(
        ('forwardDistance',DOUBLE,'blackboard-double','scalar-payload'),)),
}


def ordered_reads(name):return[dict(fieldName=n,kind=k,childCapability=c)for n,t,k,c in RECORDS[name]['members']]


def require_source(source,pins,name):
    need('nested-record-finite-source',True,name in RECORDS and source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==pins and(source.get('wrappedType'),source.get('wrapperName'))==(name,RECORDS[name]['wrapperName'])
        and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False and source.get('wholeOwnerAdmitted')is False)
    need('nested-record-exact-fields',[(n,t)for n,t,k,c in RECORDS[name]['members']],
        [(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])])
    life=source.get('lifecycle',{});get=life.get('GetValue',{})
    need('nested-record-own-getter-semantics',True,life.get('directHolderMode')is True
        or(life.get('coherentGetter')or{}).get('coherentNonNullSamePointerReturn')is True)
    need('nested-record-own-GetValue-profile',True,life.get('directHolderMode')is True
        or get.get('entryProof',{}).get('kind')=='owned-zero-context-getter-tail'
        or get.get('ownedCoherentGetter',{}).get('coherentNonNullSamePointerReturn')is True)
    paths=source.get('programs',[])
    need('nested-record-four-complete-frames',True,len(paths)==4 and all(type(p.get('existing'))is bool
        and type(p.get('wrapperNull'))is bool and p.get('frame',{}).get('entryRspRestored')is True
        and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths)
        and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)})


def bind_program(name,compiled):
    need('nested-record-finite-program',True,name in RECORDS)
    aliases={'bool':'bool-byte','enum32':'scalar32','int32':'scalar32','single-bits':'float32-bits','pooled-string':'byte-payload'};members=RECORDS[name]['members']
    expected=[dict(memberIndex=i,fieldName=n,kind=aliases.get(k,k),childCapability=c)for i,(n,t,k,c)in enumerate(members)]
    need('nested-record-exact-program',True,type(compiled.get('memberCount'))is int and compiled['memberCount']==len(expected)
        and compiled.get('reads')==expected and all(type(r.get('memberIndex'))is int for r in compiled['reads']))
    need('nested-record-exact-child-scope',sorted({c for n,t,k,c in members if c is not None}),compiled.get('requiredCapabilities'))
    return ordered_reads(name)


def _derive_on_children(image,pins,reference_children,*,type_names=None,managed_value_children=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.generated_reader_sources import derive_many
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    from scripts.game_data.memorypack import pooled_source_helper
    _publication_gate(image,pins);names=list(RECORDS)if type_names is None else list(type_names)
    need('nested-record-finite-selection',True,bool(names)and len(names)==len(set(names))and set(names)<=set(RECORDS))
    if any(t==LINE_END for name in names for n,t,k,c in RECORDS[name]['members'])and LINE_END not in reference_children:
        reference_children=dict(reference_children)
        reference_children[LINE_END]=_derive_on_children(image,pins,{},type_names=[LINE_END])
    generated=derive_many(image,pins,[RECORDS[n]['wrapperName']for n in names]);caps={};records={};required=set();identities={};managed_identities={}
    managed_value_children={}if managed_value_children is None else dict(managed_value_children)
    need('nested-record-generated-native-inputs',pins,generated['nativeInputs'])
    for name,result in zip(names,generated['owners'],strict=True):
        if result.get('status')!='complete-reader-source-proved':
            raise ValueError('skillActionNestedRecord.complete-reader:'+name+': '+str(dict(status=result.get('status'),reason=result.get('reason')))[:2500])
        source=result['proof'];require_source(source,pins,name)
        requests={r['memberIndex']:derive_typed_usage_context(image,r['context']['instructionRva'],label='skillActionNestedRecord')
            for r in source['orderedSourceReads']if r['declaredType']in REFERENCES or r['declaredType']in VALUE_TYPES}
        from scripts.game_data.memorypack.skill_action_managed_value_bindings import derive_children,bind as bind_value
        managed_value_children.update(derive_children(image,pins,[source])if any(r['declaredType']in VALUE_TYPES
            and r['declaredType']not in managed_value_children for r in source['orderedSourceReads'])else{})
        selected_values={r['memberIndex']:managed_value_children[r['declaredType']]
            for r in source['orderedSourceReads']if r['declaredType']in VALUE_TYPES}
        compiled,pending=compile_member_program(source,pins,wrapper_name=source['wrapperName'],type_name=name,value4={},
            references=REFERENCES,reference_children=reference_children,typed_requests=requests,
            typed_values=VALUE_TYPES,value_children=selected_values,value_binder=bind_value)
        need('nested-record-all-child-joins:'+name,[],pending);order=bind_program(name,compiled);required.update(compiled['requiredCapabilities'])
        for read in source['orderedSourceReads']:
            nominal=read['declaredType']
            if nominal in REFERENCES:
                capability,wire,operation=REFERENCES[nominal];child=reference_children[nominal]['capabilities'][capability]
                identities[operation]={k:child[k]for k in('typeName','referenceReaderMethodDefinition','referenceReaderTargetRva')}
            elif nominal in VALUE_TYPES:
                capability,wire,operation=VALUE_TYPES[nominal]
                managed_identities[operation]=managed_value_children[nominal]['capabilities'][capability]
        pooled={}
        for read in source['orderedSourceReads']:
            if read['kind']=='byte-payload'and read['sourceTargetRva']not in pooled:
                at=read['sourceTargetRva'];pooled[at]=pooled_source_helper.validate_on_image(image,image.pe.image_base+at,pins)
        wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==source['wrapperName']]
        life=source['lifecycle'];owned=life.get('directHolderMode')is not True and'ownedCoherentGetter'in life['GetValue']
        pair=derive_pair(image,name,wrapper.name,owned_getter_family=owned);adapter=derive_adapter(image,pins,pair,wrapper)
        need('nested-record-same-owned-GetValue',life['GetValue']['method'],adapter['getterMethod'])
        need('nested-record-same-owned-reader',source['method'],adapter['pairForwarder']['readerMethod'])
        caps[RECORDS[name]['capability']]=dict(typeName=name,wrapperName=wrapper.name,memberCount=len(order),orderedReads=order,
            nullable=True,nullAdmitted=True,nullMarker=255,wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,
            ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,callbackSelectionConditional=True,wholeOwnerAdmitted=False)
        records[name]=dict(source=source,compiled=compiled,typedRequests=requests,pair=pair,adapter=adapter,pooledSources=pooled)
    readers=reference_reader_abi(image,pins)
    for cap in caps.values():cap.update({k:readers[k]for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')})
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-action-nested-record-sources.v1',status='validated-conditional-action-nested-records',nativeInputs=pins,
        capabilities=caps,requiredExternalCapabilities=sorted(required-set(caps)),
        requiredExternalCapabilityIdentities={name:shape for name,shape in identities.items()if name not in caps},
        requiredExternalManagedValueIdentities=managed_identities,
        proof=dict(records=records,referenceChildren=reference_children,referenceReaders=readers,managedValueChildren=managed_value_children),wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Finite complete concrete caller/lifecycle/GetValue/ordinary adapter/actual Reader and every typed primitive/pool/independent ordinary child join.',
            conditional=__doc__,structuralOnly='Stored authored action settings.',unresolved=['actual enclosing collection/action/union/root/EOF','runtime effects/provider selection','refill/error paths']))))


def derive(image,pins,*,type_names=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image,pins);names=list(RECORDS)if type_names is None else list(type_names)
    need('nested-record-finite-selection',True,bool(names)and len(names)==len(set(names))and set(names)<=set(RECORDS))
    needed={t for name in names for n,t,k,c in RECORDS[name]['members']if t in REFERENCES};children={}
    if DOUBLE in needed:
        from scripts.game_data.memorypack.skill_blackboard_double_sources import derive as child
        children[DOUBLE]=child(image,pins)
    if TARGET in needed:
        from scripts.game_data.memorypack.skill_ec_components import derive as child
        children[TARGET]=child(image,pins)
    if SEQUENCE in needed:
        from scripts.game_data.memorypack.skill_sequence_components import derive as child
        children[SEQUENCE]=child(image,pins)
    if CURVE in needed:
        from scripts.game_data.memorypack.skill_animation_curve_sources import derive as child
        actual=child(image,pins);children[CURVE]=dict(nativeInputs=pins,capabilities={'curve-profile':actual['capabilities']['skill-animation-curve']},proof=actual)
    if VECTOR in needed:
        from scripts.game_data.memorypack.skill_blackboard_vector3_sources import derive as child
        children[VECTOR]=child(image,pins)
    return _derive_on_children(image,pins,children,type_names=names)

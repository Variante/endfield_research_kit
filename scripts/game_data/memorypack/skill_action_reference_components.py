"""Finite ordinary reference children of current Skill actions.

Only the finite explicitly selected records below enter here. Their exact
named fields, primitive source programs, new/existing/FF paths, own generated
factories and plain holder16 GetValue join independently selected canonical
registration/adapters and actual ordinary Reader sources. Metadata names alone
never select a grammar. Typed normal allocation/constructor effects, matching
callbacks, coherent initialized classes, disabled collector and disjoint
buffered storage remain conditions. Stored configuration proves no animation,
alert execution, live provider choice, enclosing action/root or physical EOF.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

SCHEMA='endfield.skill-action-reference-components.v2'
DEFAULT_TYPES=('Beyond.Gameplay.Core.AnimatorParamAction','Beyond.Gameplay.Core.SkillAlertData')
RECORDS={
 'Beyond.Gameplay.View.CameraControlState+TransitionCondition':dict(capability='skill-camera-transition-condition',
    wrapperName='Beyond.MemoryPack.Beyond_Gameplay_View_CameraControlState_TransitionConditionForMemoryPack',
    members=(('boolValue','bool','bool'),('buffValue','string','pooled-string'),
        ('comparator','Beyond.Gameplay.View.CameraControlConditionComparator','enum32'),
        ('conditionType','Beyond.Gameplay.View.CameraControlConditionType','enum32'),('floatValue','float','single-bits'))),
 'Beyond.Gameplay.Core.AnimatorParamAction':dict(capability='skill-action-animator-param',
    wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_AnimatorParamActionForMemoryPack',
    members=(('animatorParam','int','int32'),('boolValue','bool','bool'),('floatValue','float','single-bits'),
        ('intValue','int','int32'),('paramType','UnityEngine.AnimatorControllerParameterType','enum32'))),
 'Beyond.Gameplay.Core.SkillAlertData':dict(capability='skill-action-alert-data',
    wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_SkillAlertDataForMemoryPack',
    members=(('activeTime','float','single-bits'),('angle','float','single-bits'),('circleOriginOffset','float','single-bits'),
        ('moveType','Beyond.Gameplay.Core.AlertMoveType','enum32'),('radius','float','single-bits'),
        ('rayMaxDistance','float','single-bits'),('rayOriginOffset','float','single-bits'),('rayWidth','float','single-bits'),
        ('shape','Beyond.Gameplay.Core.AlertShape','enum32'))),
 'Beyond.Gameplay.WeaponVFXOverrideConfig':dict(capability='skill-action-weapon-vfx-override',
    wrapperName='Beyond.MemoryPack.Beyond_Gameplay_WeaponVFXOverrideConfigForMemoryPack',
    members=tuple((name,'bool','bool')for name in(
        'enableToFightAppearParticleFx','enableToFightAppearRendererFx','enableToIdleAppearParticleFx',
        'enableToIdleAppearRendererFx','enableToIdleAppearRendererFx2','enableToIdleAppearRendererFx3',
        'enableToIdleAppearRendererFx4','enableToIdleDisappearParticleFx','enableToIdleDisappearRendererFx'))+
        tuple((name,'string','pooled-string')for name in(
        'toFightAppearParticleFx','toFightAppearRendererFx','toIdleAppearParticleFx','toIdleAppearRendererFx',
        'toIdleAppearRendererFx2','toIdleAppearRendererFx3','toIdleAppearRendererFx4','toIdleDisappearParticleFx',
        'toIdleDisappearRendererFx'))),
}


def require_record_scope(source,pins,type_name):
    """Finite source/nominal boundary only; no native admission from this join."""
    need('action-reference-explicit-nominal',True,type_name in RECORDS)
    spec=RECORDS[type_name];name=spec['wrapperName']
    need('action-reference-selected-source',True,source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==pins and(source.get('wrappedType'),source.get('wrapperName'))==(type_name,name)
        and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False
        and source.get('wholeOwnerAdmitted')is False)
    need('action-reference-exact-field-order',[(n,t)for n,t,k in spec['members']],
        [(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
    life=source['lifecycle']
    need('action-reference-direct-owned-holder',True,life.get('directHolderMode')is True
        and life.get('typedCache')is None and life.get('baseHolder')==[name,type_name,16])
    paths=source['programs']
    need('action-reference-complete-four-paths',True,len(paths)==4 and all(type(p.get('existing'))is bool
        and type(p.get('wrapperNull'))is bool and p.get('frame',{}).get('entryRspRestored')is True
        and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths)
        and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)})


def bind_program(type_name,compiled):
    """Require the finite independently source-compiled primitive program."""
    need('action-reference-program-nominal',True,type_name in RECORDS)
    members=RECORDS[type_name]['members'];reads=compiled['reads']
    need('action-reference-literal-program-count',True,type(compiled.get('memberCount'))is int and compiled['memberCount']==len(members))
    need('action-reference-ordered-member-indices',True,len(reads)==len(members)
        and all(type(r.get('memberIndex'))is int for r in reads)and[r['memberIndex']for r in reads]==list(range(len(members))))
    aliases={'bool':'bool-byte','int32':'scalar32','enum32':'scalar32','single-bits':'float32-bits','pooled-string':'byte-payload'}
    need('action-reference-finite-wire-program',[(n,aliases[k],'byte-payload'if k=='pooled-string'else None)for n,t,k in members],
        [(r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in reads])
    required=['byte-payload']if any(k=='pooled-string'for n,t,k in members)else[]
    need('action-reference-exact-delegated-capabilities',required,compiled['requiredCapabilities'])
    return [dict(fieldName=n,kind=k,childCapability='byte-payload'if k=='pooled-string'else None)for n,t,k in members]


def derive(image,pins,*,type_names=None):
    """Fresh same-image source, typed ordinary adapters and concrete getters."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.generated_reader_sources import derive_many
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.pointer_param import leaf
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    _publication_gate(image,pins)
    names=list(DEFAULT_TYPES)if type_names is None else list(type_names)
    need('finite-distinct-action-reference-scope',True,0<len(names)<=len(RECORDS)
        and len(names)==len(set(names))and all(name in RECORDS for name in names))
    wrappers=[RECORDS[name]['wrapperName']for name in names]
    generated=derive_many(image,pins,wrappers);records={};caps={};required=set()
    need('action-reference-selected-native-inputs',pins,generated['nativeInputs'])
    for result,type_name in zip(generated['owners'],names,strict=True):
        if result['status']!='complete-reader-source-proved':
            from scripts.game_data.memorypack.corpus_gate import CensusGateError
            failure=CensusGateError('skillActionReference.complete-generated-source',
                source='scripts/game_data/memorypack/generated_reader_sources.py',
                expected='complete-reader-source-proved',actual=dict(status=result['status'],reason=str(result.get('reason'))[:2400]))
            failure.diagnostic.update(validator='skillActionReferenceComponents',failedGate='complete-generated-source',
                typeName=type_name,wrapperName=RECORDS[type_name]['wrapperName'],nativeInputs=pins)
            failure.args=(json.dumps(failure.diagnostic,sort_keys=True),)
            raise failure
        source=result['proof'];require_record_scope(source,pins,type_name)
        compiled,pending=compile_member_program(source,pins,wrapper_name=source['wrapperName'],type_name=type_name,value4={})
        need('action-reference-no-pending-child',[],pending);order=bind_program(type_name,compiled)
        required.update(compiled['requiredCapabilities']);pooled={}
        from scripts.game_data.memorypack import pooled_source_helper
        for read in source['orderedSourceReads']:
            if read['kind']=='byte-payload'and read['sourceTargetRva']not in pooled:
                target=read['sourceTargetRva'];pooled[target]=pooled_source_helper.validate_on_image(image,image.pe.image_base+target,pins)
        wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==source['wrapperName']]
        need('action-reference-actual-wrapper-original',type_name,wrapper.wrapped_type)
        pair=derive_pair(image,type_name,wrapper.name);adapter=derive_adapter(image,pins,pair,wrapper)
        need('action-reference-same-owned-getter',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
        getter=leaf(image,image.pe.image_base+adapter['getterMethod'][3],['488B4110','C3'])
        need('action-reference-same-owned-static-reader',source['method'],adapter['pairForwarder']['readerMethod'])
        records[type_name]=dict(source=source,compiled=compiled,pair=pair,adapter=adapter,getter=getter,pooledSources=pooled)
        wire=1+sum(1 if kind=='bool'else 4 for field,typ,kind in RECORDS[type_name]['members'])
        cap=dict(typeName=type_name,wrapperName=wrapper.name,memberCount=len(order),nullable=True,
            nullMarker=255,nullAdmitted=True,wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,
            orderedReads=order,ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
            callbackSelectionConditional=True,positiveWireBytes=wire,nullWireBytes=1,wholeSkillDataAdmitted=False)
        caps[RECORDS[type_name]['capability']]=cap
    reader=reference_reader_abi(image,pins)
    for cap in caps.values():
        cap.update({key:reader[key]for key in('referenceReaderMethodDefinition','referenceReaderTargetRva')})
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-action-reference-components',nativeInputs=pins,
        capabilities=caps,requiredExternalCapabilities=sorted(required),proof=dict(records=records,referenceReaders=reader),
        wholeSkillDataAdmitted=False,evidenceBoundary=dict(
            exact='Finite named primitive/pooled programs, complete selected new/existing/FF source and frames, generated setter/factory source, plain holder16 getter, independently proved pooled helper, freshly selected canonical ordinary adapters and actual Reader identities.',
            conditional=__doc__,structuralOnly='Stored animation-parameter and alert configuration.',
            unresolved=['live provider/formatter/inflation selection','normal compatible constructor/helper effects','action execution','cold/refill/error paths','enclosing action/root/physical EOF']))))

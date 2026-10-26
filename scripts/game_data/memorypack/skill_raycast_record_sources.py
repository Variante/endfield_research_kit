"""Finite ordinary RayCast settings with independent vector/reference sources.

Only the four named concrete records below enter this owner. Their complete
new/existing/FF callers, exact named fields and captured Vector3/primitive bits,
own factories/GetValue and ordinary canonical adapters precede child admission.
Curve and BlackboardVector3 retain separate complete wire/lifecycle owners;
the RaycastData reference list independently owns its actual parent request,
count/callback/Add induction. No managed width supplies wire framing. Ready
coherent contexts, matching callbacks, normal compatible typed allocation and
helpers, disabled collector and stable disjoint buffered storage are conditions.
Runtime raycast/VFX/provider selection, enclosing action/root and EOF stay open.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

SCHEMA='endfield.skill-raycast-record-sources.v1'
PREFIX='Beyond.Gameplay.Core.RayCastEffectAction+'
CURVE='UnityEngine.AnimationCurve'
VECTOR='Beyond.Blackboard+BlackboardVector3'
REFERENCES={CURVE:('curve-profile','curve-profile','curve-profile'),VECTOR:('skill-blackboard-vector3','blackboard-vector3','blackboard-vector3')}
RECORDS={
 PREFIX+'CurveRayData':dict(capability='skill-raycast-curve-data',wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_RayCastEffectAction_CurveRayDataForMemoryPack',members=(
    ('endPosOffset','UnityEngine.Vector3','unity-vector3-raw12',None),('progressCurve',CURVE,'curve-profile','curve-profile'),
    ('sourceMountPoint','Beyond.Gameplay.MountPoint','enum32',None),('sourcePosType',PREFIX+'RayCastEffectPosType','enum32',None),
    ('startPosOffset','UnityEngine.Vector3','unity-vector3-raw12',None),('xCurve',CURVE,'curve-profile','curve-profile'),
    ('yCurve',CURVE,'curve-profile','curve-profile'),('zCurve',CURVE,'curve-profile','curve-profile'))),
 PREFIX+'MountPointRayData':dict(capability='skill-raycast-mount-point-data',wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_RayCastEffectAction_MountPointRayDataForMemoryPack',members=(
    ('castDirection',PREFIX+'RayCastDirection','enum32',None),('sourceMountPoint','Beyond.Gameplay.MountPoint','enum32',None),
    ('startPosOffset','UnityEngine.Vector3','unity-vector3-raw12',None))),
 PREFIX+'PointToPointRayData':dict(capability='skill-raycast-point-to-point-data',wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_RayCastEffectAction_PointToPointRayDataForMemoryPack',members=(
    ('endPosBB',VECTOR,'blackboard-vector3','blackboard-vector3'),('endPosOffset','UnityEngine.Vector3','unity-vector3-raw12',None),
    ('endPosStickToGround','bool','bool',None),('groundCheckDistance','float','single-bits',None),('limitToPointDistance','bool','bool',None),
    ('sourceMountPoint','Beyond.Gameplay.MountPoint','enum32',None),('sourcePosType',PREFIX+'RayCastEffectPosType','enum32',None),
    ('sourceWeaponIndex','int','int32',None),('sourceWeaponMountPoint','Beyond.Gameplay.WeaponMountPoint','enum32',None),
    ('startPosOffset','UnityEngine.Vector3','unity-vector3-raw12',None),('targetMountPoint','Beyond.Gameplay.MountPoint','enum32',None),
    ('targetPosType',PREFIX+'RayCastEffectPosType','enum32',None),('useSourceWeaponMountPoint','bool','bool',None))),
 PREFIX+'RaycastData':dict(capability='skill-raycast-data',wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_RayCastEffectAction_RaycastDataForMemoryPack',members=(
    ('angleVelocity','float','single-bits',None),('rayDir','UnityEngine.Vector3','unity-vector3-raw12',None),
    ('rayDirectionType',PREFIX+'RayDirectionType','enum32',None),('sourceMountPoint','Beyond.Gameplay.MountPoint','enum32',None),
    ('startAngleOffset','UnityEngine.Vector3','unity-vector3-raw12',None),('targetMountPoint','Beyond.Gameplay.MountPoint','enum32',None))),
}
LIST='skill-action-raycast-data-list'
ELEMENT=PREFIX+'RaycastData'


def ordered_reads(name):return[dict(fieldName=n,kind=k,childCapability=c)for n,t,k,c in RECORDS[name]['members']]


def require_source(source,pins,name):
    need('raycast-finite-own-source',True,name in RECORDS and source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==pins and(source.get('wrappedType'),source.get('wrapperName'))==(name,RECORDS[name]['wrapperName'])
        and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False and source.get('wholeOwnerAdmitted')is False)
    need('raycast-exact-owned-field-order',[(n,t)for n,t,k,c in RECORDS[name]['members']],
        [(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])])
    life=source.get('lifecycle',{})
    need('raycast-plain-owned-holder',True,life.get('directHolderMode')is True and life.get('typedCache')is None
        and life.get('baseHolder')==[RECORDS[name]['wrapperName'],name,16])
    paths=source.get('programs',[])
    need('raycast-four-complete-frames',True,len(paths)==4 and all(type(p.get('existing'))is bool and type(p.get('wrapperNull'))is bool
        and p.get('frame',{}).get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths)
        and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)})


def bind_program(name,compiled):
    need('raycast-finite-program-name',True,name in RECORDS)
    aliases={'enum32':'scalar32','int32':'scalar32','bool':'bool-byte','single-bits':'float32-bits'}
    expected=[dict(memberIndex=i,fieldName=n,kind=aliases.get(k,k),childCapability=c)for i,(n,t,k,c)in enumerate(RECORDS[name]['members'])]
    need('raycast-literal-exact-program',True,type(compiled.get('memberCount'))is int and compiled['memberCount']==len(expected)
        and compiled.get('reads')==expected and all(type(r.get('memberIndex'))is int for r in compiled['reads']))
    need('raycast-exact-independent-reference-scope',sorted({c for n,t,k,c in RECORDS[name]['members']if c is not None}),compiled.get('requiredCapabilities'))
    return ordered_reads(name)


def _derive_on_children(image,pins,reference_children,*,type_names=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.generated_reader_sources import derive_many
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.pointer_param import leaf
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    from scripts.game_data.memorypack.skill_raycast_factory_sources import prove as factory_prover
    _publication_gate(image,pins);names=list(RECORDS)if type_names is None else list(type_names)
    need('raycast-distinct-finite-selection',True,bool(names)and len(names)==len(set(names))and set(names)<=set(RECORDS))
    generated=derive_many(image,pins,[RECORDS[n]['wrapperName']for n in names],direct_factory_prover=factory_prover);caps={};records={};required=set();identities={}
    need('raycast-same-selected-inputs',pins,generated['nativeInputs'])
    for name,result in zip(names,generated['owners'],strict=True):
        if result.get('status')!='complete-reader-source-proved':raise ValueError('skillRaycastRecord.complete-reader:'+name+': '+str(result.get('reason'))[:2600])
        source=result['proof'];require_source(source,pins,name)
        requests={r['memberIndex']:derive_typed_usage_context(image,r['context']['instructionRva'],label='skillRaycastRecord')
            for r in source['orderedSourceReads']if r['declaredType']in REFERENCES}
        compiled,pending=compile_member_program(source,pins,wrapper_name=source['wrapperName'],type_name=name,value4={},
            references=REFERENCES,reference_children=reference_children,typed_requests=requests)
        need('raycast-complete-child-program:'+name,[],pending);order=bind_program(name,compiled);required.update(compiled['requiredCapabilities'])
        for nominal,(capability,wire,operation)in REFERENCES.items():
            if any(t==nominal for n,t,k,c in RECORDS[name]['members']):
                child=reference_children[nominal]['capabilities'][capability]
                identities[operation]={k:child[k]for k in('typeName','referenceReaderMethodDefinition','referenceReaderTargetRva')}
        wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==source['wrapperName']]
        pair=derive_pair(image,name,wrapper.name);adapter=derive_adapter(image,pins,pair,wrapper)
        need('raycast-same-own-GetValue',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
        getter=leaf(image,image.pe.image_base+adapter['getterMethod'][3],['488B4110','C3'])
        need('raycast-same-own-reader',source['method'],adapter['pairForwarder']['readerMethod'])
        caps[RECORDS[name]['capability']]=dict(typeName=name,wrapperName=wrapper.name,memberCount=len(order),orderedReads=order,
            nullable=True,nullMarker=255,nullAdmitted=True,wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,
            ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,completeSourceOwnedProgram=True)
        records[name]=dict(source=source,compiled=compiled,typedRequests=requests,pair=pair,adapter=adapter,getter=getter)
    abi=reference_reader_abi(image,pins)
    for cap in caps.values():cap.update({k:abi[k]for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')})
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-raycast-records',nativeInputs=pins,capabilities=caps,
        requiredExternalCapabilities=sorted(required),requiredExternalCapabilityIdentities=identities,
        proof=dict(records=records,referenceChildren=reference_children,referenceABI=abi),wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Four finite own concrete callers/lifecycles and ordinary adapters/Reader, literal native vector/primitive-to-field programs and independently typed strong reference joins.',
            conditional=__doc__,structuralOnly='Stored raycast configuration.',unresolved=['enclosing action/list/root/physical EOF','runtime raycast/provider/VFX behavior']))))


def derive(image,pins,*,type_names=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image,pins);names=list(RECORDS)if type_names is None else list(type_names)
    need('raycast-distinct-finite-selection',True,bool(names)and len(names)==len(set(names))and set(names)<=set(RECORDS))
    needed={t for name in names for n,t,k,c in RECORDS[name]['members']if t in REFERENCES};children={}
    if CURVE in needed:
        from scripts.game_data.memorypack.skill_animation_curve_sources import derive as child
        result=child(image,pins);children[CURVE]=dict(nativeInputs=pins,capabilities={'curve-profile':result['capabilities']['skill-animation-curve']},proof=result)
    if VECTOR in needed:
        from scripts.game_data.memorypack.skill_blackboard_vector3_sources import derive as child
        children[VECTOR]=child(image,pins)
    return _derive_on_children(image,pins,children,type_names=names)


def _derive_list_on_child(image,pins,child,*,typed_request,call_target,count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as list_source
    from scripts.game_data.memorypack.skill_action_reference_list_sources import compose_reference_list,bind_parent_request,bind_reference_reader
    _publication_gate(image,pins);element=RECORDS[ELEMENT]['capability']
    listing=list_source(image,pins,typed_request=typed_request,call_target=call_target,element_type=ELEMENT,count_limit=count_limit)
    parent=bind_parent_request(listing,typed_request,call_target,image.pe.image_base,label='raycast-data-list')
    reader=bind_reference_reader(image,pins,listing,child,element_capability=element,label='raycast-data-list')
    cap=compose_reference_list(listing,child,pins,element_type=ELEMENT,element_capability=element,label='raycast-data-list')
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-raycast-data-list.v1',status='validated-conditional-raycast-data-list',nativeInputs=pins,
        capabilities={LIST:cap,element:child['capabilities'][element]},requiredExternalCapabilities=[element],
        proof=dict(collection=listing,child=child,actualParentRequestBinding=parent,listElementReaderBinding=reader),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(exact='Own actual nominal RaycastData list request/count/callback/Add induction and complete ordinary element.',
            conditional=__doc__,structuralOnly='Stored raycast list.',unresolved=['actual enclosing action/root/physical EOF','live callback selection','nonempty reuse/growth/refill']))))


def derive_list(image,pins,*,typed_request,call_target,count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image,pins)
    return _derive_list_on_child(image,pins,derive(image,pins,type_names=[ELEMENT]),typed_request=typed_request,call_target=call_target,count_limit=count_limit)

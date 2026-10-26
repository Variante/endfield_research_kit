"""Finite ordinary collider and physics-source records for current actions.

The exact concrete generated source owns every scalar, pooled index and typed
Unity Vector3 transfer. Physics offsets instead use ordinary BlackboardVector3
children; a raw Vector3 never supplies those nested bytes. Each own GetValue,
factory, canonical ordinary adapter and actual Reader is independently joined.
Coherent initialized contexts, matching callbacks, normal compatible allocation
and helpers, disabled collector and stable disjoint buffered storage remain
conditions. Enclosing actions, physics execution and root/EOF are not admitted.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

VECTOR='Beyond.Blackboard+BlackboardVector3'
VECTOR_CAP='blackboard-vector3'
RECORDS={
 'Beyond.Gameplay.ColliderShapeData':dict(capability='skill-action-collider-shape',
    wrapperName='Beyond.MemoryPack.Beyond_Gameplay_ColliderShapeDataForMemoryPack',members=(
        ('_center','UnityEngine.Vector3','unity-vector3-raw12',None),
        ('_centerXKey','string','pooled-string','byte-payload'),('_centerYKey','string','pooled-string','byte-payload'),
        ('_centerZKey','string','pooled-string','byte-payload'),('_extent','UnityEngine.Vector3','unity-vector3-raw12',None),
        ('_extentXKey','string','pooled-string','byte-payload'),('_extentYKey','string','pooled-string','byte-payload'),
        ('_extentZKey','string','pooled-string','byte-payload'),('_height','float','single-bits',None),
        ('_heightKey','string','pooled-string','byte-payload'),('_radius','float','single-bits',None),
        ('_radiusKey','string','pooled-string','byte-payload'),('_rotationOffset','UnityEngine.Vector3','unity-vector3-raw12',None),
        ('_shape','Beyond.Gameplay.ColliderShape','enum32',None),('_useCenterKey','bool','bool',None),('_useExtentKey','bool','bool',None))),
 'Beyond.Gameplay.Core.PhysicsCastAction+SourceForwardData':dict(capability='skill-action-physics-source-forward',
    wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_PhysicsCastAction_SourceForwardDataForMemoryPack',members=(
        ('directionSubType','Beyond.Gameplay.Core.PhysicsCastAction+SourceForwardDirectionSubType','enum32',None),
        ('mountPoint','Beyond.Gameplay.MountPoint','enum32',None),('offsetForwardDirectionType','Beyond.Gameplay.DirectionType','enum32',None),
        ('rayLocalRotationEuler',VECTOR,'blackboard-vector3',VECTOR_CAP),('startPosOffset',VECTOR,'blackboard-vector3',VECTOR_CAP))),
 'Beyond.Gameplay.Core.PhysicsCastAction+SourceToTargetData':dict(capability='skill-action-physics-source-to-target',
    wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_PhysicsCastAction_SourceToTargetDataForMemoryPack',members=(
        ('endPosOffset',VECTOR,'blackboard-vector3',VECTOR_CAP),('offsetForwardDirectionType','Beyond.Gameplay.DirectionType','enum32',None),
        ('rayLocalRotationEuler',VECTOR,'blackboard-vector3',VECTOR_CAP),('sourceMountPoint','Beyond.Gameplay.MountPoint','enum32',None),
        ('startPosOffset',VECTOR,'blackboard-vector3',VECTOR_CAP),('targetMountPoint','Beyond.Gameplay.MountPoint','enum32',None))),
}


def ordered_reads(name):
    return[dict(fieldName=n,kind=k,childCapability=c)for n,t,k,c in RECORDS[name]['members']]


def bind_program(name,compiled):
    need('geometry-explicit-nominal',True,name in RECORDS)
    members=RECORDS[name]['members'];aliases={'bool':'bool-byte','enum32':'scalar32','single-bits':'float32-bits','pooled-string':'byte-payload'}
    expected=[dict(memberIndex=i,fieldName=n,kind=aliases.get(k,k),childCapability=c)for i,(n,t,k,c)in enumerate(members)]
    need('geometry-literal-complete-program',True,type(compiled.get('memberCount'))is int and compiled['memberCount']==len(members)
        and compiled.get('reads')==expected and all(type(r.get('memberIndex'))is int for r in compiled['reads']))
    required=sorted({c for n,t,k,c in members if c is not None})
    need('geometry-exact-child-scope',required,compiled.get('requiredCapabilities'))
    return ordered_reads(name)


def require_source(source,pins,name):
    need('geometry-complete-nominal-source',True,name in RECORDS and source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==pins and(source.get('wrapperName'),source.get('wrappedType'))==(RECORDS[name]['wrapperName'],name)
        and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False
        and source.get('wholeOwnerAdmitted')is False)
    need('geometry-exact-declarations',[(n,t)for n,t,k,c in RECORDS[name]['members']],
        [(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
    life=source.get('lifecycle',{})
    need('geometry-source-owned-getter-profile',True,life.get('directHolderMode')is True
        or(life.get('coherentGetter')or{}).get('coherentNonNullSamePointerReturn')is True)
    paths=source['programs']
    need('geometry-four-complete-return-paths',True,len(paths)==4
        and{(p.get('existing'),p.get('wrapperNull'))for p in paths}=={(False,False),(True,False),(False,True),(True,True)}
        and all(type(p.get('existing'))is bool and type(p.get('wrapperNull'))is bool
            and p.get('frame',{}).get('entryRspRestored')is True
            and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths))


def _derive_on_children(image,pins,reference_children,*,type_names=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.generated_reader_sources import derive_many
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    from scripts.game_data.memorypack import pooled_source_helper
    from scripts.game_data.memorypack.corpus_gate import CensusGateError
    _publication_gate(image,pins);names=list(RECORDS)if type_names is None else list(type_names)
    need('geometry-finite-distinct-selection',True,bool(names)and len(names)==len(set(names))and set(names)<=set(RECORDS))
    generated=derive_many(image,pins,[RECORDS[name]['wrapperName']for name in names]);caps={};records={};required=set();identities={}
    need('geometry-same-generated-inputs',pins,generated['nativeInputs'])
    for name,row in zip(names,generated['owners'],strict=True):
        if row['status']!='complete-reader-source-proved':
            failure=CensusGateError('skillActionGeometry.complete-generated-source',
                source='scripts/game_data/memorypack/generated_reader_sources.py',expected='complete-reader-source-proved',
                actual=dict(status=row['status'],reason=str(row.get('reason'))[:2400]))
            failure.diagnostic.update(validator='skillActionGeometry',failedGate='complete-generated-source',
                typeName=name,wrapperName=RECORDS[name]['wrapperName'],nativeInputs=pins)
            failure.args=(json.dumps(failure.diagnostic,sort_keys=True),);raise failure
        source=row['proof'];require_source(source,pins,name)
        requests={r['memberIndex']:derive_typed_usage_context(image,r['context']['instructionRva'],label='skillActionGeometry')
            for r in source['orderedSourceReads']if r['declaredType']==VECTOR}
        compiled,pending=compile_member_program(source,pins,wrapper_name=source['wrapperName'],type_name=name,value4={},
            references={VECTOR:('skill-blackboard-vector3','blackboard-vector3',VECTOR_CAP)},
            reference_children=reference_children,typed_requests=requests)
        need('geometry-all-child-joins',[],pending);order=bind_program(name,compiled);required.update(compiled['requiredCapabilities'])
        if VECTOR_CAP in compiled['requiredCapabilities']:
            child=reference_children[VECTOR]['capabilities']['skill-blackboard-vector3']
            identities[VECTOR_CAP]={k:child[k]for k in('typeName','referenceReaderMethodDefinition','referenceReaderTargetRva')}
        pooled={}
        for read in source['orderedSourceReads']:
            if read['kind']=='byte-payload'and read['sourceTargetRva']not in pooled:
                at=read['sourceTargetRva'];pooled[at]=pooled_source_helper.validate_on_image(image,image.pe.image_base+at,pins)
        wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==source['wrapperName']]
        pair=derive_pair(image,name,wrapper.name,owned_getter_family=source['lifecycle'].get('directHolderMode')is not True)
        adapter=derive_adapter(image,pins,pair,wrapper)
        need('geometry-same-owned-GetValue',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
        need('geometry-same-owned-static-reader',source['method'],adapter['pairForwarder']['readerMethod'])
        cap=dict(typeName=name,wrapperName=wrapper.name,memberCount=len(order),orderedReads=order,nullable=True,nullMarker=255,
            nullAdmitted=True,wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,
            ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
            callbackSelectionConditional=True,wholeSkillDataAdmitted=False)
        caps[RECORDS[name]['capability']]=cap
        records[name]=dict(source=source,compiled=compiled,typedRequests=requests,pair=pair,adapter=adapter,pooledSources=pooled)
    readers=reference_reader_abi(image,pins)
    for cap in caps.values():cap.update({k:readers[k]for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')})
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-action-geometry-sources.v1',
        status='validated-conditional-action-geometry',nativeInputs=pins,capabilities=caps,
        requiredExternalCapabilities=sorted(required),requiredExternalCapabilityIdentities=identities,
        proof=dict(records=records,referenceReaders=readers,referenceChildren=reference_children),wholeSkillDataAdmitted=False,
        evidenceBoundary=dict(exact='Finite complete collider/physics-source programs, actual Unity value/pool/Blackboard reads and whole field transfers, own concrete lifecycle/GetValue and ordinary canonical adapters.',
            conditional=__doc__,structuralOnly='Stored authored collider and physics-source settings.',
            unresolved=['actual enclosing action/union/root/EOF','physics/runtime provider selection','cold/refill/error paths']))))


def derive(image,pins,*,type_names=None):
    names=list(RECORDS)if type_names is None else list(type_names);children={}
    if any(name in RECORDS and any(t==VECTOR for n,t,k,c in RECORDS[name]['members'])for name in names):
        from scripts.game_data.memorypack.skill_blackboard_vector3_sources import derive as child_source
        children[VECTOR]=child_source(image,pins)
    return _derive_on_children(image,pins,children,type_names=names)

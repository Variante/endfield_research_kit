"""Named CurveEvaluateFloat member9 source, with independent current children."""
from __future__ import annotations

import copy
import json

from scripts.common import check_installed_native_inputs
from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
from scripts.game_data.buff_frontiers_regenerate import _method_row
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import native_validation_failure, open_native_image, read_reviewed_contract
from scripts.game_data.memorypack import animation_curve_source, buff_blackboard_double_native
from scripts.game_data.memorypack import buff_ec_profiles_native as ec
from scripts.game_data.memorypack import buff_profile_source, pooled_source_helper
from scripts.game_data.skill_custom_root_motion_regenerate import prove_primitive
from scripts.game_data.skill_timeline_routes_regenerate import reference_primitives

SCHEMA='endfield.buff-98-profile-roles-native.v1'
CONTRACT_PATH=CONTRACTS_DIR/'buff_98_roles_native.json'
PROJECTION_PATH=CONTRACTS_DIR/'buff_98_native.json'
LABEL='buff98ProfileRoles'


def need(check,condition,detail=None):
    if not condition:raise ValueError(f'{LABEL}.{check}:{str(detail)[:700]}')


def derive(image,inputs,reviewed,projection):
    need('schema',reviewed.get('schema')==SCHEMA and reviewed.get('projection')==PROJECTION_PATH.name)
    need('claim-set',[c['profile'] for c in reviewed['claims']]==['member9'])
    base=image.pe.image_base
    primitives=reference_primitives()
    reference=json.loads((CONTRACTS_DIR/'skill_custom_root_motion_native.json').read_bytes())
    need('primitive-inputs',reference['nativeInputs']==inputs)
    targets=ec.clone_facts(image,inputs)
    targets.update(bool=base+primitives['bool'],int32=base+primitives['int32'],string=base+primitives['bytes'])
    prove_primitive(image,targets['bool'],'bool-byte');prove_primitive(image,targets['int32'],'int32')
    pooled_source_helper.validate_on_image(image,targets['string'],inputs)
    scalar=buff_blackboard_double_native.derive(image,inputs)
    need('scalar-current',scalar==json.loads(buff_blackboard_double_native.CONTRACT_PATH.read_bytes()))
    curve=animation_curve_source.validate_on_image(image,inputs)
    need('curve-current',curve['status']=='validated')
    ec_fact=json.loads(ec.CONTRACT_PATH.read_bytes())
    need('barrier-inputs',ec_fact['nativeInputs']==inputs)
    barriers={p['headerProof']['referenceBarrierTargetRva'] for p in ec_fact['proof']['profiles']}
    need('shared-null-target',len(barriers)==1)
    aliases={'UnityEngine.AnimationCurve':'curve','Beyond.Blackboard+BlackboardDouble':'scalar-payload'}
    profiles=[buff_profile_source.derive_profile(image,c,targets,aliases,next(iter(barriers))) for c in reviewed['claims']]
    methods=[_method_row(image,[0,owner,name,1]) for owner,name in reviewed['methodRoles']]
    windows={}
    for method in methods:
        for w in ec.family(image,method[3])[1]:windows.setdefault((w['startRva'],w['endRva']),w)
    for profile in profiles:
        for w in profile['headerProof']['helperWindows']:windows.setdefault((w['startRva'],w['endRva']),w)
    need('read-order',projection['anonymousReadOrder']=={
        c['profile']:c['anonymousReadOrder'] for c in reviewed['claims']})
    shape=list(projection['nestedContexts'][0])
    projected=copy.deepcopy(projection)
    projected.update(schemaVersion=2,roleContract=CONTRACT_PATH.name,methods=methods,
        codeWindows=[dict(w,requiredRoleContract=CONTRACT_PATH.name) for w in windows.values()],
        nestedContexts=[{k:c[k] for k in shape} for p in profiles for c in p['contexts']],
        boundary=reviewed['projectionBoundary'])
    current=copy.deepcopy(reviewed)
    current.update(status='exact-current-build',nativeInputs=dict(inputs),proof=dict(profiles=profiles,
        childContracts=['memorypack_animation_curve_native.json',buff_blackboard_double_native.CONTRACT_PATH.name],
        readerOffsets=ec.source_offsets(image)))
    return json.loads(json.dumps(current)),json.loads(json.dumps(projected))


def validate_on_image(image,inputs,*,projection=None):
    reviewed,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    projection=projection if projection is not None else json.loads(PROJECTION_PATH.read_bytes())
    return validate_candidate_on_image(image,inputs,reviewed,projection)


def validate_candidate_on_image(image,inputs,reviewed,projection):
    need('schema-and-status',reviewed.get('schema')==SCHEMA and reviewed.get('status')=='exact-current-build')
    need('native-inputs',reviewed['nativeInputs']==inputs)
    need('required-role-contract',projection.get('schemaVersion')==2 and
        projection.get('roleContract')==CONTRACT_PATH.name and bool(projection.get('codeWindows')) and
        all(w.get('requiredRoleContract')==CONTRACT_PATH.name for w in projection['codeWindows']))
    actual,projected=derive(image,inputs,reviewed,projection)
    need('reviewed-proof',actual==reviewed,ec.first_difference(reviewed,actual))
    need('projection-current',projected==projection,ec.first_difference(projection,projected))
    return dict(status='validated',nativeInputs=inputs,roleContract=CONTRACT_PATH.name,
        profiles={p['profile']:len(p['events']) for p in actual['proof']['profiles']},
        evidenceBoundary=actual['evidenceBoundary'])


def validate_current_native_contract(*,gameassembly=None,metadata=None):
    if (gameassembly is None)!=(metadata is None):raise ValueError(f'{LABEL}.native:both-selected-paths-required')
    try:
        reviewed,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
        inputs=reviewed['nativeInputs']
        gate=check_installed_native_inputs(inputs['GameAssembly.dll'],inputs['global-metadata.dat'],
            gameassembly=gameassembly,metadata=metadata)
        if gate.status!='validated':return dict(status=gate.status,detail=gate.detail)
        image=open_native_image(gate.gameassembly,gate.metadata)
        _publication_gate(image,inputs);result=validate_on_image(image,inputs);_publication_gate(image,inputs)
        return result
    except (ValueError,KeyError,IndexError,TypeError,OSError) as error:
        return native_validation_failure(error,label=LABEL,source_path=CONTRACT_PATH)

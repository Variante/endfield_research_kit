"""Compose strict direct-call Buff reader scopes for explicit reviewed owners."""
from __future__ import annotations

import copy
import json

from scripts.game_data.buff_frontiers_regenerate import _method_row
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.memorypack import buff_ec_profiles_native as ec
from scripts.game_data.memorypack import buff_profile_source as source
from scripts.game_data.memorypack import pooled_source_helper
from scripts.game_data.skill_custom_root_motion_regenerate import prove_primitive
from scripts.game_data.skill_timeline_routes_regenerate import reference_primitives


def single_target(image,claims,offsets):
    """Join all declared Single members to one independently proved callee."""
    found=set()
    for claim in claims:
        if not any(m['declaredType']=='float' for m in claim['members']):continue
        method=_method_row(image,[0,claim['ownerType'],claim['methodName'],1])
        _,_,rows=ec.family(image,method[3])
        header=ec.one(rows,lambda r:r['text']=='cmp sil, '+hex(len(claim['members'])),'single.member-count')
        path,_=ec.fast_path(rows,header,'rdi',offsets)
        calls=[]
        for i,row in enumerate(path):
            flow=control_transfer(row);prior=ec.last_write(path,i,'rcx')
            if flow['kind']=='call' and prior and prior['text']=='mov rcx, rdi':calls.append(row)
        source.need('single.member-source-count',len(calls)==len(claim['members']))
        found.update(control_transfer(call)['target'] for call,member in zip(calls,claim['members'])
                     if member['declaredType']=='float')
    source.need('single.unique-target',len(found)==1,len(found))
    target=next(iter(found));family,windows,rows=ec.family(image,target-image.pe.image_base)
    program=source.float32_program(rows,target,offsets)
    by={ec.va(r):r for r in rows}
    return target,dict(family=family,codeWindows=windows,
        selectedProgram=[ec.site(by[a],image.pe.image_base) for a in program],wireBytes=4,resultRegister='xmm0')


def derive(image,inputs,reviewed,projection,*,role_contract,dependencies):
    base=image.pe.image_base;offsets=ec.source_offsets(image)
    reference=json.loads((CONTRACTS_DIR/'skill_custom_root_motion_native.json').read_bytes())
    source.need('primitive-inputs',reference['nativeInputs']==inputs)
    primitive=reference_primitives(reference);targets=ec.clone_facts(image,inputs)
    targets.update(bool=base+primitive['bool'],int32=base+primitive['int32'],string=base+primitive['bytes'])
    prove_primitive(image,targets['bool'],'bool-byte');prove_primitive(image,targets['int32'],'int32')
    pooled_source_helper.validate_on_image(image,targets['string'],inputs)
    facts={}
    if any(m['declaredType']=='float' for c in reviewed['claims'] for m in c['members']):
        targets['float32'],facts['float32']=single_target(image,reviewed['claims'],offsets)
    source.need('current-ec-dependency',ec.validate_on_image(image,inputs)['status']=='validated')
    ec_fact=json.loads(ec.CONTRACT_PATH.read_bytes())
    barrier={p['headerProof']['referenceBarrierTargetRva'] for p in ec_fact['proof']['profiles']}
    source.need('shared-null-target',len(barrier)==1)
    profiles=[source.derive_profile(image,c,targets,reviewed['typeRoles'],next(iter(barrier)),
        event_builder=source.direct_profile_events) for c in reviewed['claims']]
    methods=[_method_row(image,[0,owner,name,1]) for owner,name in reviewed['methodRoles']]
    unique={}
    def add(windows):
        for window in windows:unique.setdefault((window['startRva'],window['endRva']),window)
    for method in methods:add(ec.family(image,method[3])[1])
    for profile in profiles:add(profile['headerProof']['helperWindows'])
    for fact in facts.values():add(fact['codeWindows'])
    source.need('projection-read-order',projection['anonymousReadOrder']==
        {c['profile']:c['anonymousReadOrder'] for c in reviewed['claims']})
    shape=list(projection['nestedContexts'][0])
    out=copy.deepcopy(projection)
    out.update(schemaVersion=2,roleContract=role_contract,methods=methods,
        codeWindows=[dict(w,requiredRoleContract=role_contract) for w in unique.values()],
        nestedContexts=[{k:c[k] for k in shape} for p in profiles for c in p['contexts']],
        boundary=reviewed['projectionBoundary'])
    current=copy.deepcopy(reviewed)
    current.update(status='exact-current-build',nativeInputs=dict(inputs),proof=dict(readerOffsets=offsets,
        profiles=profiles,primitiveSources=facts,childContracts=list(dependencies)))
    return json.loads(json.dumps(current)),json.loads(json.dumps(out))

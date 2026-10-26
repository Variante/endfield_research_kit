"""Audit sampled native configuration independently of versioned ECS ownership.

Admitted original-getter records prove typed actor/shape fields and repeated
registration reads even for ordinary Unity actors without ECS userdata. That
does not identify a serialized asset or a continuously alive actor. Keep those
native reads separate from the stricter versioned ECS join.

Original worker generations and saved island decisions supply sampled solver
dispatch evidence. A repeated public-scene pointer can relate scene observations
conditionally; it is not a body-to-step, pair-filter execution or contact join.
The separate original compiled isKinematic route names the observed mode bit
only when its native gate validates; absent semantics leave the raw flags alone.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import struct

if __package__ in {None, ''}:
    raise SystemExit('Run as: python -m scripts.game_data.collision_runtime_configuration')

from scripts.common import sha256_file
from scripts.game_data.collision_body_state_native import CONTRACT, SCHEMA as BODY_SCHEMA
from scripts.game_data.collision_body_mode_native import load as load_body_mode
from scripts.game_data.collision_capture_body_state import decode_body_states
from scripts.game_data.collision_capture_dispatch import decode_dispatch
from scripts.game_data.collision_capture_geometry_state import decode_geometry_state
from scripts.game_data.collision_capture_queries import decode_queries
from scripts.game_data.collision_runtime_dispatch import worker_steps
from scripts.game_data.collision_runtime_mesh import load_admission, read_calls, _output_path
from scripts.game_data.collision_runtime_mesh_native import load_layout
from scripts.game_data.collision_solver_dispatch_native import load as load_dispatch_layout
from scripts.game_data.corpus_common import atomic_write_text


def summarize(bodies, dispatch, workers, queries, *, dispatch_public_delta, body_mode=None):
    """Summarize only complete repeated native fields; ECS absence stays explicit."""
    selected = []
    for sample in bodies['samples']:
        fields = sample['after']
        # All interpreted registration, geometry, shape flags and filter/scene
        # operands must be present. A static actor has no dynamic flags word.
        required = 2031 if fields['actorClass'] == 1 else 2047 if fields['actorClass'] == 2 else 0
        if required and sample['stable'] and fields['readMask'] == required:
            selected.append(sample)
    groups = []
    for actor, shape in sorted({(s['actor'], s['shape']) for s in selected}):
        rows = [s for s in selected if (s['actor'], s['shape']) == (actor, shape)]
        observations = Counter((s['after']['actorClass'], s['after']['bodyFlags'],
                                s['after']['shapeFlags'], s['after']['geometryType'],
                                s['after']['registrationState'], s['after']['publicScene']) for s in rows)
        groups.append(dict(actor=actor, shape=shape, samples=len(rows),
            versionedEcsOwnerSamples=sum(s['stableEcsIdentity'] for s in rows),
            configurations=[dict(actorClass=key[0], bodyFlags=key[1] if key[0] == 2 else None,
                shapeFlags=key[2], geometryType=key[3], registrationState=key[4], publicScene=f'{key[5]:016x}',
                samples=count) for key,count in sorted(observations.items())],
            boundary='direct repeated original-getter typed fields; no continuous lifetime or serialized identity without the separate ECS/source join'))
    dynamic = [s for s in selected if s['after']['actorClass'] == 2]
    conversions={row['call']:row for row in queries['conversions']}
    unity_ids={}
    for sample in selected:
        conversion=conversions.get(sample['conversionCall'])
        if conversion is None:
            continue
        if (conversion['nativeActor'],conversion['nativeShape']) != (sample['actor'],sample['shape']):
            raise ValueError('body/query-conversion native actor/shape differs')
        result=conversion['result']
        if result['colliderInstanceId'] and result['ecsId']==0 and result['ecsVersion']==0:
            unity_ids[sample['call']]=result['colliderInstanceId']
    for group in groups:
        group['queryConvertedUnityColliderInstanceIds']=sorted({unity_ids[s['call']] for s in selected
            if (s['actor'],s['shape'])==(group['actor'],group['shape']) and s['call'] in unity_ids})
        if body_mode:
            for fields in group['configurations']:
                if fields['actorClass']==2:
                    fields['kinematic']=bool(fields['bodyFlags'] & body_mode['layout']['mode']['mask'])
    populations = Counter((phase, tuple(sorted(u[phase]['population'].items())))
                          for u in dispatch['updates'] for phase in ('before', 'after'))
    body_scenes = {s['after']['publicScene'] for s in selected}
    # Dispatch records carry the internal scene argument, while body records
    # separately retain the public interface returned by the typed getter.
    # Normalize through the dispatch contract before comparing those domains.
    update_scenes = {int(u[phase]['scene'],16)+dispatch_public_delta for u in dispatch['updates'] for phase in ('before','after')
                     if u[phase]['state'] & 1}
    summary=dict(coverage=dict(samples=len(bodies['samples']), stableTypedFieldSamples=len(selected),
        versionedEcsOwnerSamples=sum(s['stableEcsIdentity'] for s in selected),
        nativeOnlySamples=sum(not s['stableEcsIdentity'] for s in selected),
        actors=len({s['actor'] for s in selected}), shapes=len(groups), dynamicSamples=len(dynamic),
        dynamicActors=len({s['actor'] for s in dynamic}),
        queryConvertedUnityColliderSamples=len(unity_ids),
        dynamicQueryConvertedUnityColliderSamples=sum(s['call'] in unity_ids for s in dynamic),
        simulationEnabledSamples=sum(s['after']['simulationEnabled'] is True for s in selected),
        sceneQueryEnabledSamples=sum(s['after']['sceneQueryEnabled'] is True for s in selected),
        triggerEnabledSamples=sum(s['after']['triggerEnabled'] is True for s in selected),
        registeredSamples=sum(s['after']['registrationState']=='in_scene' for s in selected)),
        dynamicBodyFlags=dict(Counter(str(s['after']['bodyFlags']) for s in dynamic)),
        actorShapes=groups,
        sceneConfiguration=[dict(publicScene=f'{scene:016x}', filterSlot0=f'{slot0:016x}',
                                filterSlot1=f'{slot1:016x}', notificationCallback=f'{callback:016x}', samples=count)
            for (scene,slot0,slot1,callback),count in sorted(Counter((s['after']['publicScene'],s['after']['filterSlot0'],
                s['after']['filterSlot1'],s['after']['notificationCallback']) for s in selected).items())],
        sceneAddressComparison=dict(bodyPublicScenes=[f'{v:016x}' for v in sorted(body_scenes)],
            dispatchPublicScenes=[f'{v:016x}' for v in sorted(update_scenes)],
            sharedAddresses=[f'{v:016x}' for v in sorted(body_scenes & update_scenes)],
            boundary='conditional address comparison between independently typed scenes; no body-to-original-step or continuous scene lifetime claim'),
        dispatch=dict(coverage=dispatch['coverage'], classification=dispatch['classification'],
            workerCoverage=workers['coverage'],
            populations=[dict(phase=phase, population=dict(values), samples=count) for (phase,values),count in sorted(populations.items())]),
        bodyModeEvidence=dict(status='validated_compiled_semantics' if body_mode else 'unresolved',
            meaning=body_mode['representation']['bodyModeName'] if body_mode else None,
            boundary=body_mode['evidenceBoundary'] if body_mode else 'Raw flags remain anonymous without the named compiled API/setter gate.'),
        remainingGaps=['Native-only records and converted Unity Collider InstanceIDs do not supply serialized asset identity.',
                       'Scene configuration pointers and shape filter words do not record pair-filter execution.',
                       'Body-to-step ownership, continuous lifetime and positive solver contacts remain unproved.'])
    if body_mode:
        kinematic=[s for s in dynamic if s['after']['bodyFlags'] & body_mode['layout']['mode']['mask']]
        summary['coverage'].update(kinematicSamples=len(kinematic),kinematicActors=len({s['actor'] for s in kinematic}))
    else:
        summary['remainingGaps'].insert(0,'Anonymous body-mode bit requires named API/setter evidence.')
    return summary


def audit(root: Path, *, game_root: Path) -> dict:
    root=root.resolve()
    result=dict(schema='endfield.collision-runtime-configuration.v2', status='failed', session=str(root), diagnostics=[])
    try:
        admitted,profile,receipt,_=load_admission(root,game_root=game_root)
        if profile['schema'] not in ('endfieldCapture.collisionBuild.v13','endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
            raise ValueError('capture has no typed body/shape configuration records')
        directory=game_root.parent if game_root.name=='Endfield_Data' else game_root
        paths={name:directory/row['relativePath'] for name,row in profile['files'].items()}
        contract,gate=load_layout(gameassembly=paths['gameAssembly'],metadata=paths['metadata'],
            unityplayer=paths['unityPlayer'],contract_path=CONTRACT,schema=BODY_SCHEMA,
            validator='collision_runtime_configuration')
        result['nativeGate']=gate
        if contract is None:
            raise ValueError('body configuration native gate:'+gate['status'])
        if contract != profile['bodyCapture']['contract']:
            raise ValueError('capture/current body configuration contract differs')
        dispatch_contract,dispatch_gate=load_dispatch_layout(gameassembly=paths['gameAssembly'],
            metadata=paths['metadata'],unityplayer=paths['unityPlayer'])
        result['dispatchNativeGate']=dispatch_gate
        if dispatch_contract is None:
            raise ValueError('dispatch configuration native gate:'+dispatch_gate['status'])
        if dispatch_contract != profile['dispatchCapture']['contract']:
            raise ValueError('capture/current dispatch configuration contract differs')
        body_mode,mode_gate=load_body_mode(gameassembly=paths['gameAssembly'],metadata=paths['metadata'],unityplayer=paths['unityPlayer'])
        result['bodyModeNativeGate']=mode_gate
        calls=read_calls(root,profile)
        bodies=decode_body_states(calls,profile,receipt)
        dispatch=decode_dispatch(calls,profile,receipt)
        detail=decode_geometry_state(calls,profile,receipt,admitted['nativeMemory'])
        queries=decode_queries(calls,profile,receipt)
        for name,value in (('bodyStates',bodies),('physicsDispatch',dispatch),('geometryState',detail),('queries',queries)):
            if admitted[name] != value:
                raise ValueError('cached observations differ:'+name)
        workers=worker_steps(calls,dispatch,detail)
        summary=summarize(bodies,dispatch,workers,queries,
                          dispatch_public_delta=dispatch_contract['layout']['scene']['publicSceneDelta'],body_mode=body_mode)
        if sha256_file(root/'events.jsonl') != admitted['journalSha256'] or sha256_file(root/'native-memory.bin') != receipt['nativeMemory']['sha256']:
            raise ValueError('capture changed during configuration audit')
        result.update(status='validated_sampled_configuration', journalSha256=admitted['journalSha256'],
            archiveSha256=receipt['nativeMemory']['sha256'],**summary,
            boundary='Direct sampled typed configuration, separate versioned ECS ownership, and original worker/dispatch decisions. Not a global body census, executed filter decision or positive solver-contact proof.')
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,struct.error) as error:
        result.update(status='failed',diagnostics=[dict(check='runtime_configuration',detail=str(error)[:1800])])
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',type=Path,required=True)
    parser.add_argument('--game-root',type=Path,required=True)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args(argv)
    result=audit(args.session,game_root=args.game_root)
    output=_output_path(args.output or args.session/'collected/runtime-configuration.json')
    atomic_write_text(output,json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({key:result[key] for key in ('status','coverage','dynamicBodyFlags','diagnostics') if key in result}))
    return int(result['status']=='failed')


if __name__=='__main__':
    raise SystemExit(main())

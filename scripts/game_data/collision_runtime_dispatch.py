"""Audit original worker dispatch chains separately from scene/step candidates.

Original nested scene/context ownership and saved decisions are direct. A typed
same-scene core whose interval encloses a worker update is only a candidate;
reused task addresses, equal step bits and timing do not establish its origin.
Expanded captures additionally retain the original producer/decrement/task-run
chain, which may close sampled worker updates and their saved island decisions.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import struct

from scripts.common import sha256_file
from scripts.game_data.collision_capture_dispatch import decode_dispatch
from scripts.game_data.collision_capture_geometry_state import decode_geometry_state
from scripts.game_data.collision_runtime_mesh import load_admission, read_calls, _output_path, _le_pointer
from scripts.game_data.collision_solver_dispatch_native import load
from scripts.game_data.corpus_common import atomic_write_text


def step_candidates(calls, dispatch, contract, player):
    task_window=next((w for w in contract.get('codeWindows',[]) if w['role']=='task_run_virtual_dispatch'),None)
    task_probe=next((p for p in contract.get('probes',[]) if p['role']=='task_run_virtual_dispatch'),None)
    task_return=player+task_window['rva']+task_probe['offset']+len(bytes.fromhex(task_probe['hex'])) if task_window and task_probe else None
    typed=[];unavailable=[]
    for call, entry in calls.items():
        if entry['kind']!=11:
            continue
        row=entry['returnRecord'];query=bytes.fromhex(row['queryHex'])
        returned=struct.unpack_from('<Q',bytes.fromhex(row['after']))[0]
        if row['queryState']!=1:
            unavailable.append(call);continue
        public,tag,stamp=struct.unpack_from('<3Q',query)
        if tag!=player+contract['layout']['scene']['vtableRva'] or not entry['qpc']<=returned<=stamp<=row['qpc']:
            raise ValueError('dispatch candidate typed completed core projection:'+str(call))
        typed.append(dict(call=call,thread=entry['thread'],entryQpc=entry['qpc'],originalReturnQpc=returned,
                          publicScene=f'{public:016x}',requestedSceneId=_le_pointer(entry['args'][0]),
                          stepBits=_le_pointer(entry['args'][1])))
    scenes={s['call']:s for s in dispatch['scenes']};rows=[]
    for update in dispatch['updates']:
        scene=scenes.get(update['sceneUpdateCall'])
        if scene is None:
            rows.append(dict(updateCall=update['call'],status='unbound_original_scene',candidates=[]));continue
        public=int(scene['scene'],16)+contract['layout']['scene']['publicSceneDelta']
        candidates=[c for c in typed if int(c['publicScene'],16)==public and
                    c['entryQpc']<=scene['entryQpc']<=scene['returnQpc']<=c['originalReturnQpc']]
        rows.append(dict(updateCall=update['call'],sceneUpdateCall=scene['call'],scene=scene['scene'],
                         provedStepJoin=update['stepJoin'],sameThreadCoreCall=update['sameThreadCoreCall'],
                         continuation=scene['continuation'],candidates=[dict(c,stepBitsEqual=c['stepBits']==update['arguments'][11]) for c in candidates],
                         callerBinding='observed_common_task_run_return_site' if task_return and int(scene['caller'],16)==task_return else 'unreviewed_return_site',
                         status='unique_enclosing_typed_core_candidate' if len(candidates)==1 else
                                'ambiguous_enclosing_typed_core_candidates' if candidates else 'no_enclosing_typed_core_candidate',
                         boundary='conditional temporal candidates only: completed typed public scene and original interval. No worker task enqueue/generation causality is recorded.'))
    return dict(typedCoreCalls=len(typed),unavailableCoreCalls=unavailable,updates=rows,
                coverage=dict(Counter(r['status'] for r in rows)),
                uniqueContinuations=len({r['continuation'] for r in rows if 'continuation' in r}),
                callerCoverage=dict(Counter(r.get('callerBinding','unavailable') for r in rows)),
                boundary='Direct original scene/update nesting is retained. Even one enclosing core with equal step bits does not prove that core scheduled the worker task; repeated continuations carry no generation token.')


def audit(root, *, game_root=None):
    root=root.resolve();result=dict(schema='endfield.collision-runtime-dispatch-candidates.v1',status='failed',session=str(root),diagnostics=[])
    try:
        admitted,profile,receipt,_=load_admission(root,game_root=game_root)
        if profile['schema'] not in ('endfieldCapture.collisionBuild.v11','endfieldCapture.collisionBuild.v12','endfieldCapture.collisionBuild.v13','endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
            raise ValueError('capture has no original dynamics/island observer')
        calls=read_calls(root,profile);dispatch=decode_dispatch(calls,profile,receipt)
        if dispatch!=admitted['physicsDispatch']:raise ValueError('cached original dispatch observations differ')
        directory=game_root.parent if game_root and game_root.name=='Endfield_Data' else game_root
        paths={n:directory/r['relativePath'] if directory else Path(r['path']) for n,r in profile['files'].items()}
        contract,gate=load(gameassembly=paths['gameAssembly'],metadata=paths['metadata'],unityplayer=paths['unityPlayer'])
        result['nativeGate']=gate
        if contract is None:raise ValueError('selected dispatch native gate:'+gate['status'])
        for key,name in (('gameAssemblySha256','gameAssembly'),('metadataSha256','metadata'),('unityPlayerSha256','unityPlayer')):
            if contract['nativeInputs'][key].lower()!=profile['files'][name]['sha256'].lower():raise ValueError('dispatch capture/current build differs:'+name)
        candidates=step_candidates(calls,dispatch,contract,_le_pointer(receipt['playerBase']))
        if profile['schema']in ('endfieldCapture.collisionBuild.v12','endfieldCapture.collisionBuild.v13','endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
            detail=decode_geometry_state(calls,profile,receipt,admitted['nativeMemory'])
            if detail!=admitted['geometryState']:raise ValueError('cached geometry/task observations differ')
            result['originalTaskGenerations']=dict(simulations=detail['simulations'],releases=detail['releases'],atomicDecisions=detail['atomicDecisions'],runs=detail['runs'],coverage=detail['workerCoverage'])
            result['originalWorkerSteps']=worker_steps(calls,dispatch,detail)
        if sha256_file(root/'events.jsonl')!=admitted['journalSha256'] or sha256_file(root/'native-memory.bin')!=admitted['nativeMemory']['sha256']:
            raise ValueError('capture changed during dispatch candidate audit')
        result.update(status='validated_candidate_boundary',journalSha256=admitted['journalSha256'],archiveSha256=admitted['nativeMemory']['sha256'],
                      originalDispatchCoverage=dispatch['coverage'],stepCandidates=candidates)
    except (OSError,ValueError,KeyError,TypeError,struct.error,RuntimeError) as error:
        result.update(status='failed',diagnostics=[dict(check='worker_core_candidates',detail=str(error)[:1600])])
    return result


def worker_steps(calls,dispatch,observations):
    """Keep the observed producer/task chain distinct from temporal candidates."""
    run_for_scene={}
    for run in observations['runs']:
        if run['status']!='observed_scene_generation_atomic_dispatch_and_task_run':continue
        for call in run['sceneUpdateCalls']:
            if call in run_for_scene:raise ValueError('worker scene has two task generations')
            run_for_scene[call]=run
    scenes={s['call']:s for s in dispatch['scenes']};decisions={}
    for d in dispatch['decisions']:decisions.setdefault(d['updateCall'],[]).append(d)
    rows=[]
    for update in dispatch['updates']:
        run=run_for_scene.get(update['sceneUpdateCall'])
        if run is None:
            rows.append(dict(updateCall=update['call'],status='unobserved_original_task_generation'));continue
        scene=scenes[update['sceneUpdateCall']];core=calls[run['coreCall']]
        if scene['scene']!=run['before']['scene'] or scene['continuation']!=run['before']['continuation'] or scene['thread']!=run['thread'] or update['thread']!=run['thread']:
            raise ValueError('worker scene/update typed task owner differs')
        bits=_le_pointer(core['args'][1])
        if update['arguments'][11]!=bits:raise ValueError('worker original producer/update step bits differ')
        for d in decisions.get(update['call'],[]):
            if d['sceneUpdateCall']!=scene['call'] or d['thread']!=run['thread']:raise ValueError('worker island decision original owner differs')
        rows.append(dict(status='observed_original_worker_step',updateCall=update['call'],sceneUpdateCall=scene['call'],runCall=run['call'],
                         enqueueCall=run['enqueueCall'],simulationCall=run['simulationCall'],coreCall=run['coreCall'],
                         scene=scene['scene'],stepBits=bits,producerThread=core['thread'],workerThread=run['thread'],
                         requestedSceneId=_le_pointer(core['args'][0]),decisions=[dict(call=d['call'],decision=d['decision'],count=d['count']) for d in decisions.get(update['call'],[])],
                         boundary='original scene generation and task dispatch/run establish this sampled worker update and step; a zero island decision precedes solver work and does not establish global contact absence'))
    return dict(updates=rows,coverage=dict(Counter(r['status'] for r in rows)),
                boundary='Only original producer/decrement/task-run/scene/update chains are joined. Enclosing-time candidates and unsampled generations remain separate.')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--session',type=Path,required=True)
    parser.add_argument('--game-root',type=Path);parser.add_argument('--output',type=Path);args=parser.parse_args(argv)
    report=audit(args.session,game_root=args.game_root)
    output=_output_path(args.output or args.session/'collected/runtime-dispatch-candidates.json')
    atomic_write_text(output,json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(status=report['status'],coverage=report.get('stepCandidates',{}).get('coverage'),diagnostics=report['diagnostics'])))
    return int(report['status']=='failed')


if __name__=='__main__':raise SystemExit(main())

"""Audit exact missing hit-geometry fields and covered contact-report routes.

Uses admitted immutable bytes. Coverage is a byte-range fact, not a type or
lifetime proof. Empty notifications, scene linkage and query blocking never
establish solver-contact absence or participation.

Evidence and admission boundary
-------------------------------
The exact address-union census distinguishes missing bytes from decoder failure;
coverage elsewhere is censused without borrowing another checkpoint's snapshot.
A nonsentinel hit face witnesses the original geometry-getter/remap path, not an
uncopied pointer or concrete vtable. The auxiliary pointer differing from the
ordinary query shape reinforces separate index domains without exposing geometry.

Typed scene reads after a completed core may join a preceding report guard only
under that same original core and scene. Guards after the read, other scenes or
missing windows do not join. Empty reports, unentered builders/finalizers and
sampled dispatch guards remain distinct from absent touching pairs or solving.
Query blocking, kinematic population and lack of exported Rigidbody rows cannot
establish awake islands, constraints or absence of installed physical bodies.
Later positive solve observations do not retroactively fill older archives.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import struct

if __package__ in {None, ''}:
    raise SystemExit('Run as: python -m scripts.game_data.collision_runtime_evidence_boundary')

from scripts.common import sha256_file
from scripts.game_data.collision_capture_queries import decode_queries
from scripts.game_data.collision_capture_ecs import decode_ecs
from scripts.game_data.collision_runtime_mesh import load_admission, WindowView, WindowGap, _output_path, _le_pointer
from scripts.game_data.collision_runtime_mesh_native import load_layout
from scripts.game_data.collision_runtime_shape import CONTRACT as SHAPE_CONTRACT, NATIVE_SCHEMA as SHAPE_SCHEMA
from scripts.game_data.collision_runtime_actor import CONTRACT as ACTOR_CONTRACT, NATIVE_SCHEMA as ACTOR_SCHEMA
from scripts.game_data.collision_shape_index_native import load as load_index
from scripts.game_data.collision_solver_dispatch_native import load as load_solver
from scripts.game_data.corpus_common import atomic_write_text


def address_coverage(windows, address, size, call):
    if type(address) is not int or type(size) is not int or not 65536 <= address < 0x800000000000-size or not 0<size<=4096:
        raise ValueError('hit field address/size bound')
    matches=[w for w in windows if int(w['address'],16)<=address and address+size<=int(w['address'],16)+w['bytes']]
    same=[w for w in matches if w['call']==call];other=[w for w in matches if w['call']!=call]
    return dict(address=f'{address:016x}',bytes=size,status='same_call_bytes' if same else 'other_call_bytes_only' if other else 'absent',
                sameCall=same,otherCall=other)


def scene_relation(view, collider, player_base, layout_contract, guards, parent_call):
    layout=layout_contract['layout']
    wrapper=view.scalar(collider+layout['collider']['sceneWrapper'],'Q','collider.sceneWrapper')
    public=view.scalar(wrapper+layout['wrapper']['scene'],'Q','wrapper.publicScene')
    if view.scalar(public,'Q','scene.vtable')!=player_base+layout['scene']['vtableRva']:
        raise ValueError('scene relation PxScene vtable differs')
    scb=public+layout['scene']['scb']
    first_read=min(r['qpc'] for r in view.reads)
    matched=[g for g in guards if g['parentCall']==parent_call and int(g['scScenePointer'],16)==scb and g['sampleQpc']<=first_read]
    return dict(status='same_completed_core_report_scene' if matched else 'observed_scene_without_same_core_guard',
                wrapper=f'{wrapper:016x}',publicScene=f'{public:016x}',scbScene=f'{scb:016x}',
                guardCalls=[g['call'] for g in matched],reads=view.reads,
                boundary='Same-core guard and separately timed typed scene reads; continuous membership and solver pairs remain unproved.')


def solver_dispatch_evidence(view, scene, player_base, contract):
    """Checkpoint population is separate from an update-time branch witness."""
    layout = contract['layout']
    result = dict(pointers={}, backend='unavailable', controller='unavailable', population={},
                  workGate='unavailable', gaps=[], requiredRanges=[],
                  boundary=contract['evidenceBoundary'])
    pointers = {}
    for name in ('islandManager','dynamicsContext','simulationController'):
        offset=layout['scene'][name]
        try:
            pointers[name] = view.scalar(scene+offset, 'Q', 'solver.scene.'+name)
            result['pointers'][name] = f'{pointers[name]:016x}'
        except WindowGap as error:
            result['gaps'].append(dict(field=name, detail=str(error)))
    for name, status in (('dynamicsContext', 'backend'), ('simulationController', 'controller')):
        pointer = pointers.get(name)
        if not pointer:
            continue
        result['requiredRanges'].append(dict(field=name+'.vtable', address=f'{pointer:016x}', bytes=8))
        try:
            vtable = view.scalar(pointer, 'Q', name+'.vtable')
            if name == 'dynamicsContext':
                result[status] = next((kind for kind in ('pgs','tgs')
                                       if vtable == player_base+layout['context'][kind+'VtableRva']), 'unreviewed_context_type')
            else:
                result[status] = 'cpu_empty_rigid_body_solver_delegate' if vtable == player_base+layout['context']['cpuControllerVtableRva'] else 'unreviewed_controller_type'
            result[name+'Vtable'] = f'{vtable:016x}'
        except WindowGap as error:
            result['gaps'].append(dict(field=name+'.vtable', detail=str(error)))
    manager = pointers.get('islandManager')
    if manager:
        accurate = manager+layout['islandManager']['accurateIsland']
        for name, offset in layout['accurateIsland'].items():
            result['requiredRanges'].append(dict(field='population.'+name, address=f'{accurate+offset:016x}', bytes=4))
            try:
                result['population'][name] = view.scalar(accurate+offset, 'I', 'solver.population.'+name)
            except WindowGap as error:
                result['gaps'].append(dict(field='population.'+name, detail=str(error)))
        if 'activeIslands' in result['population']:
            result['workGate'] = ('nonzero_active_islands_at_checkpoint' if result['population']['activeIslands']
                                  else 'zero_active_islands_at_checkpoint')
    result['reads'] = list(view.reads)
    return result


def auxiliary_relation(record, offset):
    before,after=record['before'],record['after']
    if not before or not after or not before['identityReady'] or not after['identityReady']:
        return dict(status='identity_unavailable')
    if before['shape']!=after['shape']:
        return dict(status='query_shape_changed')
    values=[struct.unpack_from('<Q',bytes.fromhex(s['rawHex']),96+offset)[0] for s in (before,after)]
    if values[0]!=values[1]:return dict(status='auxiliary_pointer_changed')
    auxiliary=values[0];shape=int(before['shape'],16)
    if not 65536<=shape<0x800000000000 or auxiliary and not 65536<=auxiliary<0x800000000000:
        return dict(status='shape_pointer_unavailable')
    return dict(status='query_is_separate_from_auxiliary' if auxiliary and shape!=auxiliary else
                       'query_is_auxiliary' if auxiliary else 'no_auxiliary_pointer',
                auxiliaryShape=f'{auxiliary:016x}',queryShape=f'{shape:016x}')


def face_path_evidence(hit, unavailable_face):
    face=hit['result']['faceId']
    return 'successful_virtual_geometry_getter_and_remap_consumer' if face!=unavailable_face else 'sentinel_does_not_select_getter_path'


def audit(root, *, game_root=None):
    root=root.resolve();result=dict(schema='endfield.collision-runtime-evidence-boundary.v4',status='failed',session=str(root),diagnostics=[])
    try:
        calls={}
        admission,profile,receipt,samples=load_admission(root,game_root=game_root,calls_out=calls)
        directory=game_root.parent if game_root and game_root.name=='Endfield_Data' else game_root
        paths={name:directory/row['relativePath'] if directory else Path(row['path']) for name,row in profile['files'].items()}
        selected=dict(gameassembly=paths['gameAssembly'],metadata=paths['metadata'],unityplayer=paths['unityPlayer'])
        shape,sg=load_layout(**selected,contract_path=SHAPE_CONTRACT,schema=SHAPE_SCHEMA,validator='collision_hit_shape_fields')
        actor,ag=load_layout(**selected,contract_path=ACTOR_CONTRACT,schema=ACTOR_SCHEMA,validator='collision_report_scene_fields')
        indexing,ig=load_index(**selected);solver,dg=load_solver(**selected)
        result['nativeGates']=dict(shape=sg,scene=ag,index=ig,solver=dg)
        if any(c is None for c in (shape,actor,indexing,solver)):
            failed=[dict(role=role,**gate) for role,gate in result['nativeGates'].items() if gate['status']!='validated']
            raise ValueError('selected native field gate:'+json.dumps(failed)[:1200])
        for contract in (shape,actor,indexing,solver):
            for key,name in (('gameAssemblySha256','gameAssembly'),('metadataSha256','metadata'),('unityPlayerSha256','unityPlayer')):
                if contract['nativeInputs'][key].lower()!=profile['files'][name]['sha256'].lower():raise ValueError('capture/selected field build differs:'+name)
        queries=decode_queries(calls,profile,receipt);ecs=decode_ecs(calls,profile,admission['nativeMemory'])
        if queries!=admission['queries'] or ecs!=admission['ecs']:raise ValueError('cached query/ECS observations differ')
        stages=None
        if profile['schema'] in ('endfieldCapture.collisionBuild.v10','endfieldCapture.collisionBuild.v11','endfieldCapture.collisionBuild.v12','endfieldCapture.collisionBuild.v13','endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
            from scripts.game_data.collision_capture_stages import decode_stages
            stages=decode_stages(calls,profile,receipt)
            if stages!=admission.get('physicsStages'):raise ValueError('cached physics-stage observations differ')
        raw=(root/'native-memory.bin').read_bytes();windows=admission['nativeMemory']['windows'];fields=shape['layout']['shape']
        hits=[];census=Counter();records={r['call']:r for r in ecs['records'] if r['kind']==30}
        for hit in queries['conversions']:
            pointer=int(hit['nativeShape'],16);coverage={}
            for name,offset,size in (('shapeVtable',0,8),('inlineGeometryType',fields['inlineGeometry'],4),
                 ('bufferFlags',fields['bufferFlags'],1),('bufferPointer',fields['bufferPointer'],8),
                 ('inlineTriangleMesh',fields['inlineGeometry']+shape['layout']['geometry']['triangleMesh'],8)):
                coverage[name]=address_coverage(windows,pointer+offset,size,hit['call'])
                census[name+'.'+coverage[name]['status']]+=1
            row=dict(call=hit['call'],actor=hit['nativeActor'],shape=hit['nativeShape'],ecsId=hit['result']['ecsId'],fields=coverage,
                     geometryIdentity='unresolved_missing_shape_fields' if any(v['status']=='absent' for v in coverage.values()) else 'covered_bytes_require_typed_geometry_decode')
            row['geometryConsumerPath']=face_path_evidence(hit,indexing['queryFaceEvidence']['unavailableFaceId'])
            census['geometryConsumerPath.'+row['geometryConsumerPath']]+=1
            record=records.get(hit['call'])
            if record and record.get('matchesReturnedPhysicsIdentity'):
                row['auxiliaryRelation']=auxiliary_relation(record,indexing['actorUserdata']['complexShape'])
                census['auxiliary.'+row['auxiliaryRelation']['status']]+=1
            hits.append(row)
        scenes=[];player_base=_le_pointer(receipt['playerBase'])
        native_roots={(s['call'],s['role']):_le_pointer(s['nativeRoot']) for s in admission['nativeMemory']['samples']}
        for sample in samples:
            if sample['kind']!='physics_collider':continue
            native=native_roots.get((sample['call'],'collider'))
            row=dict(call=sample['call'],parentCall=sample['parentCall'],checkpoint=sample['completedStepOrdinal'])
            if not native:row.update(status='unavailable',detail='native Collider root missing')
            else:
                view=WindowView(windows,raw,call=sample['call'],root=f'{native:016x}',role='collider')
                try:
                    row.update(scene_relation(view,native,player_base,actor,queries['guards'],sample['parentCall']))
                    row['solverDispatch']=solver_dispatch_evidence(view,int(row['scbScene'],16),player_base,solver)
                    for span in row['solverDispatch']['requiredRanges']:
                        span['coverage']=address_coverage(windows,int(span['address'],16),span['bytes'],sample['call'])
                except WindowGap as error:row.update(status='unavailable',detail=str(error))
            scenes.append(row)
        contact_routes=[r for r in admission['hookCoverage'] if r['kind'] in ('contact_header','report_build','report_dispatch')]
        contacts=admission['contacts']
        result.update(status='validated_observation_boundary',journalSha256=admission['journalSha256'],archiveSha256=admission['nativeMemory']['sha256'],
            census=dict(census),hits=hits,sceneRelations=scenes,sceneCoverage=dict(Counter(s['status'] for s in scenes)),
            contactRoutes=contact_routes,reportGuards=dict(Counter(g['bypass'] for g in queries['guards'])),
            solverDispatchCoverage={field:dict(Counter(s.get('solverDispatch',{}).get(field,'unavailable') for s in scenes)) for field in ('backend','controller','workGate')},
            nativeSolverDispatch=solver['dispatch'],
            contactHeaders=len(contacts['headers']),contactPairs=len(contacts['pairs']),reportStreams=len(queries['streams']),
            solverParticipation='unresolved_no_contact_records' if not contacts['pairs'] else 'recorded_pairs_require_selected_native_solver_proof',
            queryConsumption=queries['counters'],
            evidenceBoundary='Exact address-range coverage, repeated auxiliary pointer reads and typed same-core scene linkage in admitted bytes. Nonsentinel faces witness the original successful virtual geometry-getter/remap path, without the returned pointer value or a live concrete vtable binding. Query/filter consumption is separate positive gameplay collision evidence. Missing shape fields prevent exact geometry-pointer decoding; empty notifications and zero covered report-route entries do not establish solver-contact absence or participation.')
        if stages is not None:
            result['physicsStages']=stages
            joined={g['getterCall']:g for g in stages['liveCaches'] if g['validatedSampledJoin']}
            getter_by_hit={g['parentCall']:g for g in stages['getters'] if g['success'] and g['readState']==1}
            for hit in hits:
                getter=getter_by_hit.get(hit['call'])
                if getter:
                    hit['originalGetterOutput']=getter
                    hit['geometryIdentity']='observed_getter_pointer_live_cache_unjoined'
                    if getter['call'] in joined:
                        hit['liveCacheProvenance']=joined[getter['call']]
                        hit['geometryIdentity']='sampled_getter_pointer_live_cache_join'
            result['solverParticipation']='observed_original_contact_solver_descriptors' if stages['solvePairs'] else 'unresolved_no_sampled_solver_descriptors'
            result['evidenceBoundary']='Original getter outputs and live typed cache/CAB samples can supply sampled geometry-pointer identity. Original solver contact invocation is independent of notification reports. Scene/step ownership, continuous lifetime and positive impulse remain distinct checks; missing samples never establish absence.'
        if profile['schema'] in ('endfieldCapture.collisionBuild.v11','endfieldCapture.collisionBuild.v12','endfieldCapture.collisionBuild.v13','endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
            from scripts.game_data.collision_capture_dispatch import decode_dispatch
            dispatch=decode_dispatch(calls,profile,receipt)
            if dispatch!=admission.get('physicsDispatch'):raise ValueError('cached dynamics dispatch observations differ')
            result['physicsDispatch']=dispatch
            result['originalIslandDecisions']=dict(Counter(d['decision'] for d in dispatch['decisions']))
        if sha256_file(root/'events.jsonl')!=admission['journalSha256'] or sha256_file(root/'native-memory.bin')!=admission['nativeMemory']['sha256']:
            raise ValueError('capture changed during boundary audit')
    except (OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,struct.error) as error:
        result={k:v for k,v in result.items() if k in ('schema','session','nativeGates')}
        result.update(status='failed',hits=[],sceneRelations=[],diagnostics=[dict(check='collision_runtime_boundary',detail=str(error)[:1600])])
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--session',type=Path,required=True)
    parser.add_argument('--game-root',type=Path);parser.add_argument('--output',type=Path);args=parser.parse_args(argv)
    report=audit(args.session,game_root=args.game_root);output=_output_path(args.output or args.session/'collected/runtime-evidence-boundary.json')
    atomic_write_text(output,json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:report[k] for k in ('status','census','sceneCoverage','solverDispatchCoverage','reportGuards','contactRoutes','contactPairs','solverParticipation','diagnostics') if k in report}))
    return int(report['status']=='failed')


if __name__=='__main__':raise SystemExit(main())

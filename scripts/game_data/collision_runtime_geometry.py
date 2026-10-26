"""Join admitted getter/cache observations to source descriptors and cooked Meshes.

Header agreement is separate from captured vertex/index equality. Repeated
reference slots and descriptor index/scale evidence retain their own boundaries.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import struct

from scripts.common import sha256_file
from scripts.game_data.collision_capture_stages import decode_stages
from scripts.game_data.collision_capture_queries import decode_queries
from scripts.game_data.collision_capture_ecs import decode_ecs
from scripts.game_data.collision_capture_geometry_state import decode_geometry_state
from scripts.game_data.collision_runtime_mesh import load_admission, read_calls, WindowView, WindowGap, _output_path, _le_pointer, _floats
from scripts.game_data.collision_runtime_ecs import descriptor_candidate
from scripts.game_data.collision_shape_index_native import load as load_index
from scripts.game_data.cooked_collision_corpus import validate_receipt, receipt_payloads, check_receipt_snapshot
from scripts.game_data.cooked_collision import read_triangle_mesh
from scripts.game_data.ecs_collision import decode
from scripts.game_data.collision_geometry_evidence import source_surface_evidence, current_surface_evidence, sweep_feature_metrics
from scripts.game_data.collision_query_consumption import consumption_index
from scripts.game_data.collision_capture_memory import AddressCoverage
from scripts.game_data.corpus_common import atomic_write_text


def descriptor_scale_evidence(projection, slots, shape_index, scale_hex, selection):
    candidates=[]
    for r in projection['records']:
        if r.get('meshSlot') not in slots or r['kind'] not in ('mesh','triangleMesh'):
            continue
        raw=bytes.fromhex(r['rawHex']);at=0 if projection['kind']=='mesh' else 44
        matches=raw[at:at+12].hex()==scale_hex
        candidates.append(dict(meshSlot=r['meshSlot'],offset=r['offset'],scaleBitsMatch=matches,
                               scale=r['scale'],position=r.get('position'),rotation=r.get('rotation')))
    ordinal,domain=descriptor_candidate(projection,shape_index,selection)
    matching=[r for r in candidates if r['scaleBitsMatch']]
    agrees=bool(len(matching)==1 and ordinal and ordinal.get('meshSlot')==matching[0]['meshSlot'] and ordinal['offset']==matching[0]['offset'])
    return dict(aliasSlots=sorted(slots),candidates=candidates,shapeIndex=shape_index,indexDomain=domain,
                ordinalSlot=ordinal.get('meshSlot') if ordinal else None,
                selectedCandidateSlot=matching[0]['meshSlot'] if agrees else None,
                status='index_and_scale_agree' if agrees else 'ambiguous_or_different',
                boundary='conditional: original geometry scale bits and reviewed actor index domain select the same stored descriptor; continuous attachment history and actual pose remain separate')


def live_header(view, cache, player, contract):
    t=contract['layout']['triangle']
    if view.scalar(cache,'Q','triangle.vtable')!=player+t['vtableRva']:
        raise ValueError('getter triangle-cache vtable differs')
    flags=view.scalar(cache+t['flags'],'B','triangle.flags')
    return dict(vertices=view.scalar(cache+t['vertexCount'],'I','triangle.vertices'),
                triangles=view.scalar(cache+t['triangleCount'],'I','triangle.triangles'),flags=flags,
                indexWidth=2 if flags&t['index16Mask'] else 4,
                vertexPointer=f"{view.scalar(cache+t['vertices'],'Q','triangle.vertexPointer'):016x}",
                indexPointer=f"{view.scalar(cache+t['triangles'],'Q','triangle.indexPointer'):016x}",
                boundsCenterHex=view.read(cache+t['boundsCenter'],12,'triangle.boundsCenter').hex(),
                boundsExtentsHex=view.read(cache+t['boundsExtents'],12,'triangle.boundsExtents').hex())


def captured_array_extents(observation,blob,header):
    """Read authenticated prefixes from one sample; never fill uncaptured tails."""
    if not observation['stableHeaderAndOrigin'] or not observation['stableEcsIdentity']:
        raise WindowGap('array header/origin/ECS snapshot incomplete or changed')
    found=observation['before']
    for key in ('vertices','triangles','indexWidth','vertexPointer','indexPointer'):
        if found[key]!=header[key]:raise ValueError('same-getter array/header differs:'+key)
    data=[]
    for role,key,size in (('geometryVertices','vertexPointer',header['vertices']*12),('geometryIndices','indexPointer',header['triangles']*3*header['indexWidth'])):
        root=int(header[key],16);cursor=root;parts=[]
        for w in observation['spanWindows'][role]:
            raw=blob[w['payloadOffset']:w['payloadOffset']+w['bytes']]
            if w['call']!=observation['call'] or w['role']!=role or int(w['root'],16)!=root or int(w['address'],16)!=cursor or len(raw)!=w['bytes'] or hashlib.sha256(raw).hexdigest()!=w['sha256']:
                raise ValueError('array extent identity/continuity/hash:'+role)
            parts.append(raw);cursor+=len(raw)
        if cursor-root>size:raise ValueError('array extent exceeds declared size:'+role)
        data.append(b''.join(parts))
    return tuple(data)


def captured_arrays(observation,blob,header):
    """Require both whole arrays from one admitted getter/cache sample."""
    vertices,indices=captured_array_extents(observation,blob,header)
    if len(vertices)!=header['vertices']*12:raise WindowGap('array extent incomplete:geometryVertices')
    if len(indices)!=header['triangles']*3*header['indexWidth']:raise WindowGap('array extent incomplete:geometryIndices')
    if not observation['validatedSampledJoin']:raise WindowGap('whole-array observation not admitted as complete')
    return vertices,indices


def compare_array_extents(vertices,indices,header,stored_vertices,stored_triangles):
    """Byte equality of saved prefixes remains separate from whole-array equality."""
    if header['indexWidth'] not in (2,4) or len(stored_vertices)!=header['vertices']*12 or len(stored_triangles)!=header['triangles']:
        raise ValueError('stored/runtime array dimensions differ')
    expected_indices=struct.pack('<'+str(header['triangles']*3)+('H' if header['indexWidth']==2 else 'I'),
                                 *(i for face in stored_triangles for i in face))
    result={}
    for name,actual,expected in (('vertices',vertices,stored_vertices),('indices',indices,expected_indices)):
        if len(actual)>len(expected) or actual!=expected[:len(actual)]:raise ValueError('captured geometry array prefix differs:'+name)
        result[name]=dict(capturedBytes=len(actual),requestedBytes=len(expected),complete=len(actual)==len(expected),
                          status='captured_prefix_matches' if actual else 'unobserved')
    result['boundary']='direct: bytes from one admitted getter/cache sample match the authenticated source prefix; uncaptured tails remain unobserved'
    return result


def stored_sources(receipts, *, requested_identities=None):
    """Authenticate whole selections; decode only requested exact identities.

    A broad current corpus can supply observed Meshes without re-decoding its
    unrelated payloads. Receipt admission and conflicting raw identities still
    cover the full selection; every consumed buffer retains its typed/raw join.
    """
    if isinstance(receipts,Path):receipts=[receipts]
    admitted=[];cooked={};identities={}
    for path in receipts or ():
        report=validate_receipt(path);admitted.append(report)
        for r in report['objects']:
            key=(r['identity']['sourceFile'].lower(),r['identity']['pathId']&((1<<64)-1))
            previous=identities.get(key)
            if previous is not None and previous!=r['rawSha256']:raise ValueError('authenticated stored Mesh identity has conflicting raw bytes:'+str(key))
            identities[key]=r['rawSha256']
            if requested_identities is not None and key not in requested_identities:
                continue
            for kind,payload,info in receipt_payloads(r):
                if kind=='triangle':
                    value=(r,read_triangle_mesh(payload),payload,info)
                    if key in cooked:
                        if cooked[key][0][2]!=payload:raise ValueError('authenticated stored Mesh identity has conflicting triangle bytes:'+str(key))
                    else:cooked[key]=[value]
    return admitted,cooked


def audit(root, *, stored_receipt=None, game_root=None):
    root=root.resolve();result=dict(schema='endfield.collision-runtime-geometry.v2',status='failed',session=str(root),samples=[],diagnostics=[])
    try:
        admitted,profile,receipt,_=load_admission(root,game_root=game_root)
        calls=read_calls(root,profile)
        if profile['schema'] not in ('endfieldCapture.collisionBuild.v10','endfieldCapture.collisionBuild.v11','endfieldCapture.collisionBuild.v12','endfieldCapture.collisionBuild.v13','endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):raise ValueError('capture has no geometry-output/cache observer')
        stages=decode_stages(calls,profile,receipt)
        if stages!=admitted['physicsStages']:raise ValueError('cached physics-stage values differ')
        queries=decode_queries(calls,profile,receipt)
        if queries!=admitted['queries']:raise ValueError('cached query consumption observations differ')
        ecs=decode_ecs(calls,profile,admitted['nativeMemory'])
        if ecs!=admitted['ecs']:raise ValueError('cached geometry source observations differ')
        detail=None
        if profile['schema']in ('endfieldCapture.collisionBuild.v12','endfieldCapture.collisionBuild.v13','endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
            detail=decode_geometry_state(calls,profile,receipt,admitted['nativeMemory'])
            if detail!=admitted['geometryState']:raise ValueError('cached geometry/task observations differ')
        bodies={}
        if profile['schema'] in ('endfieldCapture.collisionBuild.v13','endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
            from scripts.game_data.collision_capture_body_state import decode_body_states
            body_observations=decode_body_states(calls,profile,receipt)
            if body_observations!=admitted['bodyStates']:raise ValueError('cached body/shape/scene observations differ')
            bodies={b['getterCall']:b for b in body_observations['samples']}
            if len(bodies)!=len(body_observations['samples']):raise ValueError('duplicate body state sample in one getter')
        directory=game_root.parent if game_root and game_root.name=='Endfield_Data' else game_root
        paths={n:directory/r['relativePath'] if directory else Path(r['path']) for n,r in profile['files'].items()}
        indexing,gate=load_index(gameassembly=paths['gameAssembly'],metadata=paths['metadata'],unityplayer=paths['unityPlayer'])
        result['nativeIndexGate']=gate
        if indexing is None:raise ValueError('descriptor index native gate:'+gate['status'])
        for key,name in (('gameAssemblySha256','gameAssembly'),('metadataSha256','metadata'),('unityPlayerSha256','unityPlayer')):
            if indexing['nativeInputs'][key]!=profile['files'][name]['sha256'].lower():raise ValueError('capture/index build differs:'+name)
        requested={(c['serializedOrigin']['cab'].lower(),int(c['serializedOrigin']['pathId']))
                   for c in stages['liveCaches'] if c['validatedSampledJoin']}
        stored,cooked=stored_sources(stored_receipt,requested_identities=requested)
        blob=(root/'native-memory.bin').read_bytes();windows=admitted['nativeMemory']['windows'];player=_le_pointer(receipt['playerBase'])
        address_coverage=AddressCoverage(windows)
        layout=profile['stageCapture']['cacheLayout'];getters={g['call']:g for g in stages['getters']}
        records={r['call']:r for r in ecs['records'] if r['kind']==37}
        conversions={q['call']:q for q in queries['conversions']}
        requests={q['call']:q for q in queries['requests']}
        fields={f['name']:f['offset'] for t in profile['queryCapture']['contract']['types'] if t['type']=='UnityEngine.RaycastHit' for f in t['fields']}
        consumption=consumption_index(queries,fields)
        source=next(s for s in profile['sources'] if Path(s['path']).name=='ecs_collision_native.json')
        source_contract=json.loads((root/'static-sources'/source['archiveName']).read_bytes())
        for key,name in (('gameAssemblySha256','gameAssembly'),('metadataSha256','metadata'),('unityPlayerSha256','unityPlayer')):
            if source_contract['nativeInputs'][key].lower()!=profile['files'][name]['sha256'].lower():raise ValueError('frozen geometry source/current build differs:'+name)
        grouped=defaultdict(list)
        for c in stages['liveCaches']:
            if c['validatedSampledJoin']:grouped[(c['getterCall'],c['decoderCall'],c['meshObject'],c['triangle'])].append(c)
        samples=[];projections={};world_vertex_cache={}
        arrays_by_getter=defaultdict(list);poses_by_getter={};inputs_by_conversion={}
        if detail:
            for a in detail['arrays']:arrays_by_getter[a['getterCall']].append(a)
            poses_by_getter={p['getterCall']:p for p in detail['poses']}
            inputs_by_conversion={h['call']:h for h in detail['nativeHitInputs']}
        for (getter_call,decoder,mesh,cache),matches in grouped.items():
            g=getters[getter_call];origin=matches[0]['serializedOrigin'];key=(origin['cab'],int(origin['pathId']))
            row=dict(getterCall=getter_call,conversionCall=g['parentCall'],decoderCall=decoder,
                     actor=g['actor'],shape=g['shape'],meshObject=mesh,triangleCache=cache,serializedOrigin=origin,
                     cacheSampleCalls=[c['call'] for c in matches],sourceSlots=sorted({c['sourceSlot'] for c in matches}),
                     geometryScaleHex=g['consumedGeometryHex'][8:32],geometryScale=_floats(bytes.fromhex(g['consumedGeometryHex'])[4:16]))
            record=records[decoder]
            if not record['producerCall'] or not record['sourceComplete'] or not record['meshIdsComplete']:raise ValueError('geometry source route/span unavailable:'+str(decoder))
            if decoder not in projections:
                payload=b''.join(blob[w['payloadOffset']:w['payloadOffset']+w['bytes']] for w in record['spanWindows']['source'])
                projection=decode(payload,layout=source_contract['layout'],kinds=source_contract['kinds'],limits=source_contract['limits'],mesh_count=record['meshCount'])
                projections[decoder]=(projection,hashlib.sha256(payload).hexdigest())
            projection,source_sha=projections[decoder]
            query=conversions[g['parentCall']]
            row['descriptor']=descriptor_scale_evidence(projection,set(row['sourceSlots']),query['result']['componentIndex'],row['geometryScaleHex'],indexing['selection'])
            row['sourceDefinitionSha256']=source_sha;row['queryResult']=query['result']
            request=requests[query['parentCall']]
            row['queryRequestCall']=request['call'];row['queryRequestKind']=request['kind']
            row['sweepFeature']=sweep_feature_metrics(request,query['result'])
            row['queryConsumption']=consumption.get(g['parentCall'],dict(hitCalls=[],selectedOwnerReturns=[],filterDecisions=[]))
            if getter_call in poses_by_getter:row['currentPose']=poses_by_getter[getter_call]
            if getter_call in bodies:row['currentBodyState']=bodies[getter_call]
            if g['parentCall'] in inputs_by_conversion:row['nativeHitInput']=inputs_by_conversion[g['parentCall']]
            headers=[]
            for c in matches:
                view=WindowView(windows,blob,call=c['call'],root=cache,role='getterTriangle')
                try:headers.append(live_header(view,int(cache,16),player,layout))
                except WindowGap as error:row.setdefault('headerGaps',[]).append(str(error))
            if headers:
                if any(h!=headers[0] for h in headers):raise ValueError('same-getter cache headers conflict')
                row['runtimeHeader']=headers[0]
            selected=cooked.get(key,[])
            if len(selected)==1 and headers:
                obj,geometry,raw,info=selected[0];h=headers[0]
                row['storedMesh']=dict(name=obj['name'],identity=obj['identity'],renderVertexCount=obj['renderVertexCount'],collisionOnly=obj['collisionOnly'],
                                       rawSha256=obj['rawSha256'],payloadSha256=info['sha256'],vertices=len(geometry.geometry.vertices),triangles=len(geometry.geometry.triangles),
                                       countsMatch=(h['vertices'],h['triangles'])==(len(geometry.geometry.vertices),len(geometry.geometry.triangles)))
                if not row['storedMesh']['countsMatch']:raise ValueError('live/stored geometry counts differ:'+obj['name'])
                row['sourceSurface']=source_surface_evidence(geometry,projection,set(row['sourceSlots']),query['result'],row['geometryScaleHex'],
                    vertex_cache=world_vertex_cache,cache_key=(decoder,key),
                    point_eligible=row['sweepFeature']['status']!='initial_overlap_or_nonpositive_distance')
                if detail:
                    row['currentSurface']=current_surface_evidence(geometry,row.get('currentPose'),query['result'],row['geometryScale'],
                        struct.unpack('<4f',bytes.fromhex(g['consumedGeometryHex'])[16:32]),row.get('nativeHitInput'),
                        point_eligible=row['sweepFeature']['status']!='initial_overlap_or_nonpositive_distance')
                row['runtimeArrayCoverage']={
                    'vertices':address_coverage.span(int(h['vertexPointer'],16),h['vertices']*12,matches[0]['call']),
                    'indices':address_coverage.span(int(h['indexPointer'],16),h['triangles']*3*h['indexWidth'],matches[0]['call'])}
                spans={s['field']:raw[s['start']:s['end']] for s in geometry.spans}
                view=WindowView(windows,blob,call=matches[0]['call'],root=cache,role='getterTriangle')
                try:
                    exact=[a for a in arrays_by_getter[getter_call] if a['cacheSampleCall'] in row['cacheSampleCalls'] and a['triangle']==cache and a['mesh']==mesh and a['serializedOrigin']==origin]
                    if len(exact)>1:raise ValueError('duplicate complete-array identity in one getter')
                    if exact:
                        prefixes=captured_array_extents(exact[0],blob,h)
                        row['arrayPrefixEquality']=compare_array_extents(*prefixes,h,spans['mesh.vertices'],geometry.geometry.triangles)
                        row['arrayObservationCall']=exact[0]['call']
                        vertices,indices=captured_arrays(exact[0],blob,h);row['arrayObservationCall']=exact[0]['call']
                    else:
                        vertices=view.read(int(h['vertexPointer'],16),h['vertices']*12,'vertices')
                        indices=view.read(int(h['indexPointer'],16),h['triangles']*3*h['indexWidth'],'indices')
                    decoded=struct.unpack('<'+str(h['triangles']*3)+('H' if h['indexWidth']==2 else 'I'),indices)
                    if vertices!=spans['mesh.vertices'] or list(decoded)!=[i for face in geometry.geometry.triangles for i in face]:raise ValueError('captured geometry arrays differ')
                    row['vertexIndexEquality']='captured_arrays_match'
                except WindowGap as error:row.update(vertexIndexEquality='unavailable',arrayGap=str(error))
            else:row['storedMeshStatus']='not_selected_or_header_unavailable'
            samples.append(row)
        for selection in stored:check_receipt_snapshot(selection)
        if sha256_file(root/'events.jsonl')!=admitted['journalSha256'] or sha256_file(root/'native-memory.bin')!=receipt['nativeMemory']['sha256']:raise ValueError('capture changed during geometry audit')
        result.update(status='validated_sampled_geometry_identity',samples=samples,
                      journalSha256=admitted['journalSha256'],archiveSha256=receipt['nativeMemory']['sha256'],
                      coverage=dict(getterCalls=len(samples),uniqueShapes=len({s['shape'] for s in samples}),uniqueMeshIdentities=len({(s['serializedOrigin']['cab'],s['serializedOrigin']['pathId']) for s in samples}),
                                    descriptorCandidates=sum(s['descriptor']['status']=='index_and_scale_agree' for s in samples),capturedArrays=sum(s.get('vertexIndexEquality')=='captured_arrays_match' for s in samples)),
                      boundary='Direct sampled getter pointer equals a live typed Mesh cache with repeated CAB/PathID. Descriptor index/scale selection is conditional. Cooked source decoding and live header agreement do not replace missing runtime vertex/index arrays, actual pose or solver evidence.')
        if detail:result['geometryStateCoverage']=dict(coverage=detail['coverage'],workerCoverage=detail['workerCoverage'])
    except (OSError,ValueError,KeyError,StopIteration,TypeError,struct.error,RuntimeError) as error:
        result.update(status='failed',samples=[],diagnostics=[dict(check='runtime_geometry_identity',detail=str(error)[:1800])])
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--session',type=Path,required=True)
    parser.add_argument('--stored-receipt',type=Path,action='append',help='Repeat for independently authenticated selections');parser.add_argument('--game-root',type=Path);parser.add_argument('--output',type=Path);args=parser.parse_args(argv)
    r=audit(args.session,stored_receipt=args.stored_receipt,game_root=args.game_root)
    output=_output_path(args.output or args.session/'collected/runtime-geometry-identity.json');atomic_write_text(output,json.dumps(r,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:r[k] for k in ('status','coverage','diagnostics') if k in r}));return int(r['status']=='failed')


if __name__=='__main__':raise SystemExit(main())

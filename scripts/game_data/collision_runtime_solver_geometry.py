"""Recover copied solver-side geometry and keep cooked-Mesh joins explicit.

Evidence and admission boundary
-------------------------------
Admitted stage/ECS and response records are recomputed before interpreting the
same-solve-call contact-manager shape-core prefix. Selected getter/type predicates
support complete finite capsule radius/half-height and box half-extents, consistent
with the primitive ABI; these are candidate geometry, not a Unity Mesh identity.
Positive response samples classify as capsule/box. A separately observed triangle
preparation lacks a matching solve and its Mesh pointer lies beyond the saved
prefix. Another call cannot fill it, and no match does not prove it was never solved.

Stored-source selection requires the same actor, masked userdata, physics version,
Entity and earlier original source callback; equal dimensions or reused addresses
are insufficient. Current observations therefore establish positive physical
response, but no physical solving for the recovered cooked Mesh assets. Their
query/getter/cache/array and gameplay-use evidence remains independently valid.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import struct

from scripts.common import sha256_file
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.collision_runtime_mesh import load_admission, _output_path
from scripts.game_data.collision_solver_geometry_native import load
from scripts.game_data.collision_capture_ecs import identity


def core_geometry(raw, contract):
    c=contract['layout']['core']
    if len(raw)!=c['prefixBytes']:raise ValueError('solver-geometry core prefix width')
    tag=struct.unpack_from('<I',raw,c['geometry'])[0];name=contract['geometryTypes'].get(str(tag))
    item=dict(type=tag,kind=name or 'unreviewed',coreHex=raw.hex(),storedMeshIdentity='unresolved')
    rule=contract['primitives'].get(name)
    if rule:
        values={};bits={}
        for field,spec in rule['fields'].items():
            offset=c['geometry']+spec['offset'];size=4*spec['count'];data=raw[offset:offset+size]
            if len(data)!=size:raise ValueError('solver-geometry primitive field outside prefix:'+field)
            decoded=list(struct.unpack('<'+'f'*spec['count'],data))
            if any(not math.isfinite(x) or x<=0 for x in decoded):
                index=next(i for i,x in enumerate(decoded) if not math.isfinite(x) or x<=0)
                raise ValueError(f'solver-geometry invalid primitive scalar:{field}[{index}]: expected=finite>0, actual={decoded[index]}, bits={data[index*4:index*4+4].hex()}')
            values[field]=decoded[0] if spec['count']==1 else decoded;bits[field]=data.hex()
        item.update(status='copied_primitive_geometry',parameters=values,parameterBits=bits,
            storedMeshIdentity='not_a_mesh_geometry',boundary='Same-call copied primitive dimensions; owner/source lifetime and world pose remain conditional.')
    elif name=='triangleMesh':
        offset=c['trianglePointer']
        item.update(status='triangle_geometry_without_mesh_pointer',requiredPointerBytes=dict(offset=offset,bytes=8),
            boundary='Copied triangle type; the triangle Mesh pointer lies outside this core prefix and cannot be filled from another callback.')
    else:
        item.update(status='geometry_type_only',boundary='Copied type only; this reader has not authenticated this geometry payload.')
    return item


def actor_sources(records):
    owners=defaultdict(list);decoders=defaultdict(list);actors=defaultdict(list)
    for r in records:
        after=r.get('after')
        if not after or not after['identityReady']:continue
        if r['kind']==37:decoders[identity(after)].append(r);actors[after['actor']].append(r)
        if r['kind']==47 and r['identityMatchesDecoder'] and r['entityMatchesProducer']:owners[identity(after)].append(r)
    return owners,decoders,actors


def source_join(first, last, owners, decoders, actors):
    if not first or not last or not first['identityReady'] or not last['identityReady']:
        return dict(status='runtime_identity_unavailable',sourceCandidates=[])
    if identity(first)!=identity(last) or (first['entityGlobalIndex'],first['entityVersion'])!=(last['entityGlobalIndex'],last['entityVersion']):
        return dict(status='runtime_identity_changed',sourceCandidates=[])
    key=identity(last);entity=(last['entityGlobalIndex'],last['entityVersion'])
    candidates=[r for r in owners.get(key,[]) if r['after']['endQpc']<=first['startQpc'] and
                (r['after']['entityGlobalIndex'],r['after']['entityVersion'])==entity]
    decoded=[r for r in decoders.get(key,[]) if r['after']['endQpc']<=first['startQpc']]
    stale=[r for r in actors.get(last['actor'],[]) if identity(r['after'])!=key]
    return dict(status='unique_versioned_actor_source' if len(candidates)==1 else 'ambiguous_actor_source' if candidates else
                'decoder_observed_without_assigned_owner' if decoded else 'source_not_observed',
        sourceCandidates=[dict(ownerCall=r['call'],decoderCall=r['decoderCall'],producerCall=r['producerCall']) for r in candidates],
        exactDecoderCalls=[r['call'] for r in decoded],rejectedSameAddressDecoders=[r['call'] for r in stale],
        boundary='Exact versioned actor/Entity source only; descriptor slot, CAB/PathID and this shape geometry still need independent evidence.')


def decode(calls, stages, ecs, response, contract):
    from scripts.game_data.collision_capture_ecs import snapshot
    owners,decoders,actors=actor_sources(ecs['records']);responses={r['call']:r for r in response['samples']};rows=[]
    for pair in stages['preparationPairs']+stages['solvePairs']:
        record=calls[pair['call']]['returnRecord'];provenance=pair.get('provenance')
        if not provenance or provenance['state']!=7:continue
        q=bytes.fromhex(record['queryHex']);core=q[48:128]
        try:geometry=core_geometry(core,contract)
        except ValueError as error:raise ValueError(f'solver-geometry call={pair["call"]}, shape={provenance["candidateShape"]}: {error}') from error
        first,last=snapshot(record['ecsBeforeHex']),snapshot(record['ecsAfterHex'])
        row=dict(call=pair['call'],stage=pair.get('stage','after_solve'),side=pair['side'],actor=provenance['actor'],shape=provenance['candidateShape'],
                 descriptor=pair['descriptor'],geometry=geometry,source=source_join(first,last,owners,decoders,actors))
        if 'solveCall' in pair:
            sample=responses.get(pair['call']);row.update(solveCall=pair['solveCall'],prepCall=pair['routePrepCall'],stableDescriptorKey=pair['stableDescriptorKey'],
                responseStatus=sample['status'] if sample else 'unsupported_response_variant',
                positiveAccumulatedNormal=sample.get('response',{}).get('positiveAccumulatedNormal') if sample else None)
        else:row['prepCall']=pair['prepCall']
        rows.append(row)
    positive=[r for r in rows if r.get('positiveAccumulatedNormal') is True]
    positive_pairs=defaultdict(list)
    for r in positive:positive_pairs[(r['solveCall'],r['descriptor'])].append(r)
    triangles=[r for r in rows if r['stage']=='after_prepare' and r['geometry']['kind']=='triangleMesh']
    triangle_routes=[]
    for r in triangles:
        matches=[s for s in rows if s['stage']=='after_solve' and s['prepCall']==r['prepCall'] and s['descriptor']==r['descriptor'] and s['side']==r['side'] and s['actor']==r['actor'] and s['shape']==r['shape']]
        triangle_routes.append(dict(prepCall=r['prepCall'],sampleCall=r['call'],actor=r['actor'],shape=r['shape'],
            solveSamples=[s['call'] for s in matches],status='sampled_solver_route' if matches else 'no_sampled_solver_route',
            boundary='Absence of a selected matching solve sample does not establish that the prepared contact was never solved.'))
    return dict(samples=rows,positiveGeometryKinds=dict(Counter(r['geometry']['kind'] for r in positive)),
        geometryCoverage=dict(Counter(r['geometry']['kind'] for r in rows)),sourceCoverage=dict(Counter(r['source']['status'] for r in rows)),
        positivePairs=[dict(solveCall=key[0],descriptor=key[1],sides=[dict(side=r['side'],actor=r['actor'],shape=r['shape'],geometry=r['geometry']['kind']) for r in rs]) for key,rs in sorted(positive_pairs.items())],
        trianglePreparationRoutes=triangle_routes,
        cookedMeshSolverProof='unproved',boundary=contract['evidenceBoundary'])


def audit(root, *, game_root=None):
    root=root.resolve();result=dict(schema='endfield.collision-runtime-solver-geometry.v1',status='failed',session=str(root),diagnostics=[])
    try:
        calls={};admitted,profile,receipt,_=load_admission(root,game_root=game_root,calls_out=calls)
        directory=game_root.parent if game_root and game_root.name=='Endfield_Data' else game_root
        paths={n:directory/r['relativePath'] if directory else Path(r['path']) for n,r in profile['files'].items()}
        selected=dict(gameassembly=paths['gameAssembly'],metadata=paths['metadata'],unityplayer=paths['unityPlayer'])
        contract,gate=load(**selected);result['nativeGate']=gate
        if contract is None:raise ValueError('solver-geometry selected native gate:'+gate['status'])
        for key,name in (('gameAssemblySha256','gameAssembly'),('metadataSha256','metadata'),('unityPlayerSha256','unityPlayer')):
            if contract['nativeInputs'][key].lower()!=profile['files'][name]['sha256'].lower():raise ValueError('solver-geometry capture/native build differs:'+name)
        from scripts.game_data.collision_capture_stages import decode_stages
        from scripts.game_data.collision_capture_ecs import decode_ecs
        from scripts.game_data.collision_solver_response_native import load as load_response
        from scripts.game_data.collision_runtime_solver_response import decode as decode_response
        stages=decode_stages(calls,profile,receipt);ecs=decode_ecs(calls,profile,admitted['nativeMemory'])
        if stages!=admitted['physicsStages'] or ecs!=admitted['ecs']:raise ValueError('solver-geometry cached stage/ECS observations differ')
        response_contract,response_gate=load_response(**selected);result['responseNativeGate']=response_gate
        if response_contract is None:raise ValueError('solver-geometry response gate:'+response_gate['status'])
        if response_contract['nativeInputs']!=contract['nativeInputs']:raise ValueError('solver-geometry response/geometry native inputs differ')
        response=decode_response(calls,stages,admitted['nativeMemory']['windows'],(root/'native-memory.bin').read_bytes(),response_contract)
        result.update(decode(calls,stages,ecs,response,contract))
        for name,path in (('journalSha256',root/'events.jsonl'),('archiveSha256',root/'native-memory.bin')):
            expected=admitted[name] if name=='journalSha256' else admitted['nativeMemory']['sha256']
            if sha256_file(path)!=expected:raise ValueError('solver-geometry capture changed:'+name)
            result[name]=expected
        result['status']='validated_copied_geometry_boundary'
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,struct.error) as error:
        result={k:v for k,v in result.items() if k in ('schema','session','nativeGate','responseNativeGate')}
        result.update(status='failed',diagnostics=[dict(check='solver_geometry',detail=str(error)[:1600])])
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--session',type=Path,required=True);p.add_argument('--game-root',type=Path);p.add_argument('--output',type=Path);a=p.parse_args(argv)
    r=audit(a.session,game_root=a.game_root);atomic_write_text(_output_path(a.output or a.session/'collected/runtime-solver-geometry.json'),json.dumps(r,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:r[k] for k in ('status','positiveGeometryKinds','geometryCoverage','sourceCoverage','trianglePreparationRoutes','diagnostics') if k in r}));return int(r['status']=='failed')


if __name__=='__main__':raise SystemExit(main())

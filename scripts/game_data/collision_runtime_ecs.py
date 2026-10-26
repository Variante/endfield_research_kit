"""Join admitted runtime collider creation, mesh resources and query owners.

The actor's ordered mesh inputs are proved separately from a hit shape's
geometry. Descriptor candidates use the proved auxiliary/ordinary native index
domains; constructor success and attachment history remain conditions. Names
and equal parameter tuples never select geometry.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import struct

from scripts.common import sha256_file
from scripts.game_data.collision_capture_ecs import decode_ecs
from scripts.game_data.collision_capture_inspect import _origin
from scripts.game_data.collision_runtime_mesh import load_admission, _output_path
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.ecs_collision import decode, decode_prefix, annotate_parameters
from scripts.game_data.collision_shape_index_native import load as load_shape_index


def descriptor_candidate(projection, ordinal, selection):
    """Select a conditional descriptor in its proved native index domain.

    The separately stored auxiliary shape is not part of positive actor shape
    enumeration. Constructor success and later attachment history remain gaps.
    """
    auxiliary = set(selection['auxiliaryKinds'])
    records = projection.get('records', [])
    if ordinal == selection['auxiliaryIndex']:
        candidates = [r for r in records if r['kind'] in auxiliary]
        return (candidates[0] if len(candidates) == 1 else None), 'auxiliary_shape'
    active = [r for r in records if r['kind'] not in auxiliary and r['attachmentGate'] is not False]
    index = ordinal - selection['ordinaryIndexBase']
    return (active[index] if 0 <= index < len(active) else None), 'enumerated_actor_shapes'


def bind_meshes(ids, resources, objects, calls):
    """Agreeing repeated reads may bind one input; busy reads remain gaps."""
    bindings=[]
    for slot,mesh_id in enumerate(ids):
        candidates=[]
        for obj in objects:
            if obj['readState']!=1 or obj['decoderMeshId']!=mesh_id:
                continue
            handle=struct.unpack('<I',bytes.fromhex(obj['handleBeforeHex']))[0]
            matched=[r for r in resources if r['success'] and r['readState']==1 and
                     struct.unpack_from('<I',bytes.fromhex(r['outputsHex']))[0]==handle and
                     calls[r['call']]['returnRecord']['qpc']<=calls[obj['call']]['qpc']]
            keys=sorted({r['resourceHex'] for r in matched})
            origin=_origin(obj['serializedOrigin'])
            candidates.append(dict(objectCall=obj['call'],resourceCalls=[r['call'] for r in matched],
                                   resourceHexes=keys,origin=origin))
        origins={json.dumps(c['origin'],sort_keys=True) for c in candidates if c['origin']['status']=='mapped'}
        keys={key for c in candidates for key in c['resourceHexes']}
        # All candidates are in the same original source callback and refer to
        # the exact mesh ID supplied to this decoder. No cross-frame ID lookup.
        complete=[c for c in candidates if c['origin']['status']=='mapped' and len(c['resourceHexes'])==1]
        status='matched_resource_and_serialized_input' if complete and len(origins)==len(keys)==1 else (
               'ambiguous' if len(origins)>1 or len(keys)>1 else 'serialized_map_busy' if candidates else 'lookup_not_observed')
        bindings.append(dict(meshSlot=slot,instanceId=mesh_id,status=status,candidates=candidates,
                             origin=json.loads(next(iter(origins))) if len(origins)==1 else None,
                             resourceHex=next(iter(keys)) if len(keys)==1 else None))
    return bindings


def definition_route_status(record):
    """A copied generic decoder argument is not a universal word-count ABI.

    Streaming source callbacks establish the reviewed u32-vector route. An
    unbound managed byte-buffer caller cannot reuse that framing interpretation.
    Keep its observed actor identity, but do not trim or decode excess bytes.
    """
    if not record['producerCall']:
        return 'unbound_decoder_input'
    if not record['sourceComplete'] or not record['meshIdsComplete']:
        return 'incomplete_source_span'
    return None


def source_spans(record, raw):
    spans={}
    for role,windows in record['spanWindows'].items():
        root=int(record['sourcePointer'] if role=='source' else record['meshIdsPointer'],16);cursor=root;parts=[]
        for w in sorted(windows,key=lambda w:int(w['address'],16)):
            data=raw[w['payloadOffset']:w['payloadOffset']+w['bytes']]
            if w['call']!=record['call'] or w['role']!=role or int(w['root'],16)!=root or int(w['address'],16)!=cursor or len(data)!=w['bytes'] or hashlib.sha256(data).hexdigest()!=w['sha256']:
                raise ValueError('runtime definition span identity/continuity/hash:'+role)
            parts.append(data);cursor+=len(data)
        spans[role]=b''.join(parts)
    return spans


def unbound_prefix(record, spans, contract):
    if not record['meshIdsComplete']:
        return dict(status='mesh_id_span_unavailable',boundary='Ordered input IDs were not completely observed.')
    try:
        prefix=decode_prefix(spans['source'],layout=contract['layout'],kinds=contract['kinds'],limits=contract['limits'],mesh_count=record['meshCount'])
        annotate_parameters(prefix['projection'],contract['enums'])
        prefix.update(status='schema_sized_prefix',lengthArgumentUnits='unresolved',sourceSha256=hashlib.sha256(spans['source'][:prefix['consumedBytes']]).hexdigest())
        return prefix
    except ValueError as error:
        return dict(status='prefix_unavailable',detail=str(error),capturedBytes=len(spans['source']),
            boundary='Missing or invalid schema bytes withhold projection; no trimming by caller length or recovery from another callback.')


def decoder_assignment_queries(records, joins, definitions):
    """Use an observed original Entity setter, separately from source callbacks."""
    from scripts.game_data.collision_capture_ecs import identity
    assignments=defaultdict(list);by_call={r['call']:r for r in records};defined={d['call']:d for d in definitions};rows=[]
    for r in records:
        if r['kind']!=40 or r['readState']==3 or not r['entityMatchesAssigned']:continue
        a,b=r['before'],r['after']
        if a and b and a['identityReady'] and b['identityReady'] and identity(a)==identity(b):assignments[identity(b)].append(r)
    for join in joins:
        if join['status']!='decoder_identity_with_later_query_owner':continue
        query=by_call[join['queryCall']];q=query['after'];candidates=[]
        qb=query['before']
        if not qb or not q or not qb['identityReady'] or not q['identityReady'] or identity(qb)!=identity(q) or (
                qb['entityGlobalIndex'],qb['entityVersion'])!=(q['entityGlobalIndex'],q['entityVersion']):
            rows.append(dict(queryCall=join['queryCall'],status='query_identity_changed',candidates=[]));continue
        for call in join['decoderIdentityCandidates']:
            source=by_call[call];after=source['after']
            if not after or not after['identityReady'] or identity(after)!=identity(q):continue
            for setter in assignments.get(identity(q),[]):
                first,last=setter['before'],setter['after']
                if after['endQpc']<=first['startQpc']<=last['endQpc']<=query['before']['startQpc'] and (
                        last['entityGlobalIndex'],last['entityVersion'])==(q['entityGlobalIndex'],q['entityVersion']):
                    d=defined.get(call,{});prefix=d.get('prefixEvidence',{})
                    candidates.append(dict(decoderCall=call,assignmentCall=setter['call'],definitionEvidence='schema_sized_prefix' if prefix.get('status')=='schema_sized_prefix' else
                        'owned_definition' if d.get('status')=='decoded_definition' else 'unavailable'))
        rows.append(dict(queryCall=join['queryCall'],actor=q['actor'],physicsId=q['physicsId'],physicsVersion=q['physicsVersion'],
            entityGlobalIndex=q['entityGlobalIndex'],entityVersion=q['entityVersion'],candidates=candidates,
            status='observed_decoder_assignment_query_identity' if len(candidates)==1 else 'ambiguous_assignment_route' if candidates else 'assignment_not_observed',
            boundary='Original decoder identity, original Entity setter input/return and query-time identity agree. Source callback, caller length units, stored file, exact shape selection and continuous lifetime remain separate.'))
    return rows


def audit(session: Path, *, game_root: Path | None=None, export_root: Path | None=None):
    root=session.resolve()
    result=dict(schema='endfield.collision-runtime-ecs.v4',status='failed',session=str(root),diagnostics=[])
    try:
        calls={}
        admitted,profile,receipt,_=load_admission(root,game_root=game_root,calls_out=calls)
        directory=game_root.parent if game_root and game_root.name=='Endfield_Data' else game_root
        paths={name:directory/row['relativePath'] if directory else Path(row['path']) for name,row in profile['files'].items()}
        indexing,gate=load_shape_index(gameassembly=paths['gameAssembly'],metadata=paths['metadata'],unityplayer=paths['unityPlayer'])
        result['shapeIndexNativeGate']=gate
        if indexing is None:raise ValueError('shape index native:'+gate['status']+':'+gate.get('detail',''))
        for key,name in (('gameAssemblySha256','gameAssembly'),('metadataSha256','metadata'),('unityPlayerSha256','unityPlayer')):
            if indexing['nativeInputs'][key].lower()!=profile['files'][name]['sha256'].lower():
                raise ValueError('capture/shape index build differs:'+name)
        checked=decode_ecs(calls,profile,admitted['nativeMemory'])
        if checked!=admitted['ecs']:raise ValueError('cached ECS observation values differ')
        source=next(s for s in profile['sources'] if Path(s['path']).name=='ecs_collision_native.json')
        from scripts.game_data.ecs_collision_native import load as load_definition
        contract,definition_gate=load_definition(gameassembly=paths['gameAssembly'],metadata=paths['metadata'],unityplayer=paths['unityPlayer'],
            contract_path=root/'static-sources'/source['archiveName'])
        result['definitionNativeGate']=definition_gate
        if contract is None:raise ValueError('runtime definition selected native gate:'+definition_gate['status'])
        for key,name in (('gameAssemblySha256','gameAssembly'),('metadataSha256','metadata'),('unityPlayerSha256','unityPlayer')):
            if contract['nativeInputs'][key].lower()!=profile['files'][name]['sha256'].lower():raise ValueError('capture/definition native inputs differ:'+name)
        raw=(root/'native-memory.bin').read_bytes()
        definitions=[];census=Counter();by_parent={}
        for r in checked['records']:by_parent.setdefault(r['parent'],[]).append(r)
        for record in checked['records']:
            if record['kind']!=37:continue
            item=dict(call=record['call'],producerCall=record['producerCall'],complete=record['sourceComplete'] and record['meshIdsComplete'])
            route=definition_route_status(record)
            if route:
                item.update(status=route,rawLengthArgument=record['sourceWords'])
                if route=='unbound_decoder_input':
                    item['prefixEvidence']=unbound_prefix(record,source_spans(record,raw),contract)
                    census['unboundPrefix.'+item['prefixEvidence']['status']]+=1
                census[route]+=1;definitions.append(item);continue
            if calls[record['producerCall']]['kind'] not in range(42,47):
                raise ValueError('runtime definition source callback kind:call='+str(record['call']))
            spans=source_spans(record,raw)
            payload=spans['source'];ids=list(struct.unpack('<'+'i'*record['meshCount'],spans['meshIds']))
            try:
                projection=decode(payload,layout=contract['layout'],kinds=contract['kinds'],limits=contract['limits'],mesh_count=len(ids))
            except ValueError as error:
                raise ValueError(f"runtime definition framing:call={record['call']},producer={record['producerCall']},sourceWords={record['sourceWords']},capturedBytes={len(payload)},sha256={hashlib.sha256(payload).hexdigest()}:{error}") from error
            annotate_parameters(projection,contract['enums'])
            parent=record['producerCall'];siblings=by_parent.get(parent,[]) if parent else []
            # Only reads completed before this decoder's entry can supply inputs.
            siblings=[s for s in siblings if calls[s['call']]['returnRecord']['qpc']<=calls[record['call']]['qpc']]
            bindings=bind_meshes(ids,[s for s in siblings if s['kind'] in (38,39)],
                                 [s for s in siblings if s['kind']==41],calls)
            item.update(status='decoded_runtime_source',bodySha256=hashlib.sha256(payload).hexdigest(),projection=projection,
                        meshBindings=bindings,meshIds=ids,heightmapId=record['heightmapId'])
            census['definitions']+=1;census['records']+=len(projection['records']);census['meshSlots']+=len(ids)
            census.update('mesh_'+b['status'] for b in bindings);definitions.append(item)
        defined={d['call']:d for d in definitions};conversions={c['call']:c for c in admitted['queries']['conversions']}
        queries={c['call']:c for c in checked['records'] if c['kind']==30}
        hits=[]
        for join in checked['querySourceJoins']:
            if join['status']!='unique_versioned_runtime_source':continue
            source=join['sourceCandidates'][0];definition=defined[source['decoderCall']]
            hit=conversions[join['queryCall']];query=queries[join['queryCall']]
            observed=bytes.fromhex(query['before']['rawHex'])
            actual=dict(gameplayOptionsWord=struct.unpack_from('<I',observed,128)[0],tagConfigWord=struct.unpack_from('<I',observed,132)[0],
                        surfaceTypeByte=observed[136],secondaryFlag=bool(observed[140]))
            row=dict(queryCall=join['queryCall'],**source,entityGlobalIndex=query['after']['entityGlobalIndex'],entityVersion=query['after']['entityVersion'],
                     actor=query['after']['actor'],physicsId=query['after']['physicsId'],physicsVersion=query['after']['physicsVersion'],
                     shape=query['after']['shape'],shapeIndex=hit['result']['componentIndex'],observedParameters=actual,
                     actorMeshSlots=[b['meshSlot'] for b in definition.get('meshBindings',[])],
                     geometrySelection='unresolved-constructor-success-attachment-history-and-geometry')
            ordinal=row['shapeIndex']
            candidate,domain=descriptor_candidate(definition.get('projection',{}),ordinal,indexing['selection'])
            row['shapeIndexDomain']=domain
            if candidate is not None:
                expected={k:candidate[k] for k in ('gameplayOptionsWord','tagConfigWord','surfaceTypeByte')}
                row['ordinalCandidate']=dict(offset=candidate['offset'],kind=candidate['kind'],meshSlot=candidate.get('meshSlot'),
                    expectedParameters=expected,parametersMatch=all(actual[k]==v for k,v in expected.items()),
                    gameplayOptionXor=actual['gameplayOptionsWord']^expected['gameplayOptionsWord'],
                    boundary='conditional descriptor in native index domain; constructor success, attachment history and geometry remain unproved')
                census['hitParameterMatch' if row['ordinalCandidate']['parametersMatch'] else 'hitParameterDifference']+=1
            hits.append(row)
        if export_root is not None:
            from scripts.game_data.collision_runtime_asset_inputs import link_inputs
            selected_game_root=directory/'Endfield_Data' if directory else paths['metadata'].parents[2]
            result['assetInputs']=link_inputs(definitions,export_root=export_root,game_root=selected_game_root)
            if result['assetInputs']['status']!='validated_input_container_joins':
                raise ValueError('AssetBundle input join:'+str(result['assetInputs']['diagnostics']))
        ready=Counter('ecs' if c['result']['ecsId'] else 'ordinaryCollider' if c['result']['colliderInstanceId'] else 'unresolved'
                      for c in admitted['queries']['conversions'])
        for name,path in (('journalSha256',root/'events.jsonl'),('archiveSha256',root/'native-memory.bin')):
            expected=admitted['journalSha256'] if name=='journalSha256' else receipt['nativeMemory']['sha256']
            if sha256_file(path)!=expected:raise ValueError('capture changed during ECS comparison:'+name)
            result[name]=expected
        assignments=decoder_assignment_queries(checked['records'],checked['querySourceJoins'],definitions)
        result.update(status='validated_runtime_source_joins',definitions=definitions,hits=hits,census=dict(census),conversionKinds=dict(ready),
                      decoderAssignmentQueries=assignments,assignmentCoverage=dict(Counter(r['status'] for r in assignments)),
                      uniqueHitActors=len({h['actor'] for h in hits}),uniqueHitEntities=len({(h['entityGlobalIndex'],h['entityVersion']) for h in hits}),
                      sourceJoins=checked['querySourceJoins'],
                      evidenceBoundary=dict(direct='Same-callback decoder inputs, later assigned Entity and versioned registry identity match returned query physics ID/version. Matching resource handle lookups and the serialized instance-ID map identify observed decoder mesh inputs.',
                          structuralOnly='Schema-sized captured prefixes for unbound decoder callers; length units, opaque trailing bytes and stored-file selection remain unresolved. Separate original Entity setter routes can bind sampled decoder/query runtime identity without inventing a source callback.',
                          conditional='Descriptor candidates use separate auxiliary and positive actor-enumeration index domains. Constructor success and attachment history remain conditions; full actor mesh inputs and equal parameter tuples do not select the geometry of a particular returned PxShape.',
                          unresolved='Unobserved source routes, serialized-map lock contention, exact hit-shape geometry selection, underlying stored-file selection and solver-contact participation.'))
    except (OSError,ValueError,KeyError,StopIteration,struct.error,RuntimeError) as error:
        result.update(status='failed',diagnostics=[dict(check='runtime_ecs_source_join',detail=str(error)[:1600])])
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',type=Path,required=True);parser.add_argument('--game-root',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--export-root',type=Path,help='Optionally join observed input identities to current exported AssetBundle containers')
    args=parser.parse_args(argv);output=_output_path(args.output or args.session/'collected/runtime-ecs-provenance.json')
    report=audit(args.session,game_root=args.game_root,export_root=args.export_root)
    atomic_write_text(output,json.dumps(report,indent=2,allow_nan=False)+'\n')
    summary={k:report[k] for k in ('status','census','assignmentCoverage','conversionKinds','uniqueHitActors','uniqueHitEntities','diagnostics') if k in report}
    if 'assetInputs' in report:summary['assetInputs']={k:report['assetInputs'][k] for k in ('status','census') if k in report['assetInputs']}
    print(json.dumps(summary))
    return int(report['status']=='failed')


if __name__=='__main__':raise SystemExit(main())

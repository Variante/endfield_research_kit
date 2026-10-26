"""Decode paired ECS creation/owner and query-time registry observations.

These are versioned runtime identities. Stored definitions or numeric resource
matches alone do not establish a currently loaded subasset or solver contact.
"""
from __future__ import annotations

import struct
from collections import defaultdict

STATE_BITS = {1:'actor_tag',2:'actor_userdata',4:'shape_tag',8:'shape_userdata',
              16:'registry_header',32:'bounded_id',64:'registry_row',128:'version_matches',
              256:'actor_matches',512:'stable_userdata',1024:'stable_registry_row'}
REQUIRED = 1|2|16|32|64|128|256|512|1024


def snapshot(text):
    raw=bytes.fromhex(text)
    if len(raw)!=192:
        raise ValueError('ECS snapshot width')
    if not any(raw):
        return None
    actor,shape,actor_tag,userdata,shape_tag,shape_userdata,registry,rows=struct.unpack_from('<8Q',raw)
    capacity,physics_id,version,state=struct.unpack_from('<4I',raw,64)
    start,end=struct.unpack_from('<2Q',raw,80)
    if state & ~2047 or start>end:
        raise ValueError(f'ECS snapshot state/timing: state={state:#x},allowedMask=0x7ff,startQpc={start},endQpc={end}')
    entity_index,entity_version=struct.unpack_from('<2I',raw,112)
    row_version,row_actor=struct.unpack_from('<IQ',raw,148)
    ready=state & REQUIRED == REQUIRED
    stored_id,stored_version=struct.unpack_from('<2I',raw,120)
    if ready and (not physics_id or physics_id>=capacity or userdata!=actor_tag & ~7 or
                  (stored_id,stored_version)!=(physics_id,version) or row_version!=version or row_actor!=actor or raw[96:128]!=raw[160:192]):
        raise ValueError('ECS registry/identity snapshot contradicts state')
    return dict(actor=f'{actor:016x}',shape=f'{shape:016x}',actorTaggedUserdata=f'{actor_tag:016x}',
                userdata=f'{userdata:016x}',shapeTaggedUserdata=f'{shape_tag:016x}',shapeUserdata=f'{shape_userdata:016x}',
                registry=f'{registry:016x}',registryRows=f'{rows:016x}',registryCapacity=capacity,
                physicsId=physics_id,physicsVersion=version,entityGlobalIndex=entity_index,entityVersion=entity_version,
                startQpc=start,endQpc=end,state=state,checks=[name for bit,name in STATE_BITS.items() if state&bit],
                identityReady=ready,rawHex=raw.hex())


def identity(value):
    return (value['actor'],value['userdata'],value['physicsId'],value['physicsVersion'])


def decode_ecs(calls, profile, memory):
    records=[];owners={};queries=[];sources={};resources={};windows={}
    for w in memory.get('windows',[]):
        if w['role'] in ('source','meshIds'):
            windows.setdefault((w['call'],w['role']),[]).append(w)
    for call,entry in sorted(calls.items()):
        row=entry['returnRecord'];kind=row['kind']
        if kind>=48 or kind<37 and kind!=30:
            continue
        # These fixed transport slots are reused by other event families (for
        # example pair policy's layer matrix). Only ECS-owned roles decode them
        # as registry snapshots; their own readers validate all other roles.
        frames=[]
        for field in ('ecsBeforeHex','ecsAfterHex'):
            try:
                frames.append(snapshot(row[field]))
            except ValueError as error:
                raise ValueError(f'ECS decode call={call},kind={kind},field={field}: {error}') from error
        before,after=frames
        args=[int.from_bytes(bytes.fromhex(v),'little') for v in row['args']]
        record=dict(call=call,kind=kind,parent=entry['parent'],before=before,after=after)
        if kind==37:
            record.update(sourcePointer=f'{args[0]:016x}',sourceWords=args[1],meshIdsPointer=f'{args[2]:016x}',
                          meshCount=args[3],heightmapId=args[4],producerCall=args[6],actorResult=row['result'])
            record['spanWindows']={role:windows.get((call,role),[]) for role in ('source','meshIds')}
            for role,requested in (('source',args[1]*4),('meshIds',args[3]*4)):
                summary=row['sourceMemory' if role=='source' else 'meshIdsMemory']
                record[role+'Complete']=summary['bytes']==requested and not any(summary[k] for k in ('limits','rejected','unreadable'))
            sources[call]=record
        elif kind in (38,39):
            record.update(resourceHex=row['before'][:32],outputsHex=row['after'][:24],success=bool(int.from_bytes(bytes.fromhex(row['result']),'little')),
                          readState=row['queryState'])
            resources.setdefault(entry['parent'],[]).append(record)
        elif kind==41:
            record.update(handleBeforeHex=row['before'][:8],handleAfterHex=row['after'][:8],nativeObject=row['result'],
                          decoderMeshId=row['meshId'],serializedOrigin=row['meshOrigin'],readState=row['queryState'])
        elif kind==40:
            assigned=int.from_bytes(bytes.fromhex(row['before'])[:8],'little')
            record.update(assignedEntity=assigned,readState=row['queryState'],
                          entityMatchesAssigned=bool(after and after['identityReady'] and
                                                    (after['entityVersion']<<32|after['entityGlobalIndex'])==assigned))
        elif kind in range(42,47):
            record.update(declaredEntity=args[0],contextPointer=f'{args[1]:016x}',contextHex=row['sourceContextHex'],
                          callerPointer=f'{args[2]:016x}',readState=row['queryState'])
        elif kind==47:
            decoder=args[1];producer=args[2]
            if decoder not in sources or sources[decoder]['producerCall']!=producer or entry['parent']!=producer or calls[producer]['kind'] not in range(42,47):
                raise ValueError('ECS later owner lacks decoder/source nesting')
            first=sources[decoder]['after']
            record.update(decoderCall=decoder,producerCall=producer,declaredEntity=args[3],
                          identityMatchesDecoder=bool(first and after and first['identityReady'] and after['identityReady'] and identity(first)==identity(after)))
            if record['identityMatchesDecoder']:
                record['entityMatchesProducer']=(after['entityVersion']<<32|after['entityGlobalIndex'])==args[3]
                if record['entityMatchesProducer']:owners.setdefault(identity(after),[]).append(record)
        elif kind==30:
            if before and after and before['identityReady'] and after['identityReady'] and identity(before)==identity(after):
                raw=bytes.fromhex(row['after']);fields={f['name']:f['offset'] for t in profile['queryCapture']['contract']['types'] if t['type']=='UnityEngine.RaycastHit' for f in t['fields']}
                result_id=struct.unpack_from('<I',raw,fields['m_EcsId'])[0]
                result_version=struct.unpack_from('<I',raw,fields['m_EcsVersion'])[0]
                record['matchesReturnedPhysicsIdentity']=(result_id,result_version)==(after['physicsId'],after['physicsVersion'])
                if record['matchesReturnedPhysicsIdentity']:queries.append(record)
        records.append(record)
    # Causality and a versioned registry identity are required. Pointer, name,
    # position or ID coincidence on its own is never used to assign a source.
    joins=[]
    decoders_by_identity=defaultdict(list)
    for source in sources.values():
        if source['after'] and source['after']['identityReady']:
            decoders_by_identity[identity(source['after'])].append(source)
    for query in queries:
        candidates=[owner for owner in owners.get(identity(query['after']),[]) if owner['after']['endQpc']<=query['before']['startQpc']
                    and (owner['after']['entityGlobalIndex'],owner['after']['entityVersion'])==(query['after']['entityGlobalIndex'],query['after']['entityVersion'])]
        decoder_candidates=[source for source in decoders_by_identity.get(identity(query['after']),[]) if source['after']['endQpc']<=query['before']['startQpc']]
        joins.append(dict(queryCall=query['call'],sourceCandidates=[dict(decoderCall=o['decoderCall'],producerCall=o['producerCall'],ownerCall=o['call']) for o in candidates],
                          decoderIdentityCandidates=[s['call'] for s in decoder_candidates],
                          status='unique_versioned_runtime_source' if len(candidates)==1 else 'ambiguous' if candidates else
                          'decoder_identity_with_later_query_owner' if len(decoder_candidates)==1 else 'creation_not_observed'))
    return dict(schema='endfield.collision-ecs-observations.v1',records=records,querySourceJoins=joins,
                gaps=['Stored-source framing, observed resource handles, serialized mesh origin and runtime owner remain separate joins.',
                      'Bounded reads and repeated registry rows are separately timed; absent or drifting rows cannot prove ownership.',
                      'Query hits and filters do not prove solver contact participation.'])

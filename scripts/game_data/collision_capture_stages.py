"""Decode original getter outputs and solver-stage observations, fail closed.

Pointer equality is sampled evidence. A preparation route candidate does not
prove continuous lifetime or the owning scene/step on another worker thread.
"""
from __future__ import annotations
import struct

from scripts.game_data.collision_capture_ecs import snapshot, identity


def decode_stages(calls, profile, receipt):
    from scripts.game_data.collision_capture_inspect import _require, _u64, _bytes, _origin
    c=profile['stageCapture']['contract'];layout=c['layout'];player=_u64(receipt['playerBase'])
    getters=[];caches=[];prepares=[];pairs=[];solves=[];solve_pairs=[]
    def data(entry):
        r=entry['returnRecord']
        return r,list(map(_u64,r['args'])),_bytes(r['before'],64,'stage before'),_bytes(r['after'],128,'stage after'),_bytes(r['queryHex'],192,'stage query')
    def origin(value):
        if value['state']==3:
            _require(type(value['check']) is int and 1<=value['check']<=11,'stage provenance failure check')
            return dict(status='read_failure',check=value['check'])
        return _origin(value,required=bool(value['state']))
    def ancestor(entry,call):
        for _ in range(64):
            if entry['parent']==call:return True
            entry=calls.get(entry['parent'])
            if not entry:return False
        return False
    def actor(row,q,cm,side):
        core,shape,owner=struct.unpack_from('<3Q',q,8);state=struct.unpack_from('<I',q,32)[0];tag=struct.unpack_from('<Q',q,40)[0]
        ecs=snapshot(row['ecsAfterHex'])
        _require(state==row['queryState'] and not state&~7,'stage actor state')
        if state&1:
            _require(core==struct.unpack_from('<Q',cm,layout['cmShapeCore1' if side else 'cmShapeCore0'])[0],'CM shape-core pointer')
        if state&2:
            _require(core>=layout['shapeCoreCandidateApiDelta'] and shape==core-layout['shapeCoreCandidateApiDelta'] and
                     tag==player+layout['shapeVtableRva'] and ecs and int(ecs['actor'],16)==owner and int(ecs['shape'],16)==shape,'typed candidate shape/actor')
        return dict(contactManager=f'{struct.unpack_from("<Q",q)[0]:016x}',shapeCore=f'{core:016x}',
                    candidateShape=f'{shape:016x}',actor=f'{owner:016x}',state=state,ecs=ecs,
                    boundary='conditional: native embedded-core candidate with typed vtable and actor observation; owning scene/step unresolved')
    for call,entry in sorted(calls.items()):
        kind=entry['kind']
        if not 48<=kind<=65:continue
        r,a,b,e,q=data(entry)
        observation=dict(call=call,parentCall=entry['parent'],thread=entry['thread'],entryQpc=entry['qpc'],returnQpc=r['qpc'],flags=r['flags'])
        if kind==48:
            parent=calls.get(entry['parent']);_require(parent and parent['kind']==30,'getter lacks original hit-converter parent')
            p=bytes.fromhex(parent['before']);_require(a[0]==struct.unpack_from('<Q',p,8)[0] and a[2]==struct.unpack_from('<Q',p)[0],'getter/converter actor shape')
            success=_u64(r['result']);_require(success in (0,1),'getter bool result')
            ready=success and r['queryState']==1
            if ready:
                _require(struct.unpack_from('<2Q',q)==(player+layout['shapeVtableRva'],)*2 and struct.unpack_from('<I',e)[0]==5 and e[36:40]==bytes(4),'getter type/vtable/padding')
            before=snapshot(r['ecsBeforeHex']);after=snapshot(r['ecsAfterHex'])
            stable=bool(before and after and before['identityReady'] and after['identityReady'] and identity(before)==identity(after))
            observation.update(success=bool(success),readState=r['queryState'],shape=f'{a[0]:016x}',actor=f'{a[2]:016x}',
                               triangle=f'{struct.unpack_from("<Q",e,40)[0]:016x}' if ready else None,
                               consumedGeometryHex=e[:48].hex() if ready else None,stableEcsIdentity=stable,ecs=after)
            getters.append(observation)
        elif kind==49:
            parent=calls.get(entry['parent']);source=calls.get(a[4]);decoder=calls.get(a[5]);producer=calls.get(a[6])
            _require(parent and parent['kind']==48 and source and source['kind']==41 and decoder and decoder['kind']==37 and producer and producer['kind'] in range(42,47),'cache source calls')
            _require(ancestor(source,a[6]) and _u64(source['returnRecord']['result'])==a[3] and
                     _u64(decoder['returnRecord']['result'])==a[0] and _u64(decoder['args'][6])==a[6], 'cache source native object/decoder')
            getter=data(parent);_require(a[2]==struct.unpack_from('<Q',getter[3],40)[0] and a[1]==getter[1][0] and a[0]==getter[1][2], 'cache original getter output')
            first=struct.unpack_from('<QQiI',b);second=struct.unpack_from('<QQiI',e)
            live=origin(r['meshOrigin']);repeat=origin(r['colliderOrigin']);baseline=origin(source['returnRecord']['meshOrigin'])
            state=0
            if first[3] and first[2]==source['returnRecord']['meshId']:state|=1
            if first[3] and second[3] and first[:3]==second[:3]:state|=2
            # The typed triangle check is additionally verified from its archived
            # native window by the memory validator when a full match is retained.
            if struct.unpack_from('<Q',q,8)[0]==player+layout['triangleVtableRva']:state|=4
            if first[1]==a[2] and a[2]:state|=8
            if first[2]==source['returnRecord']['meshId']:state|=16
            if live['status']=='mapped':state|=32
            if live['status']=='mapped' and live==repeat:state|=64
            if live['status']=='mapped' and live==baseline:state|=128
            _require(state==r['queryState'],'cache state contradicts copied values')
            ecs=snapshot(r['ecsAfterHex']);getter_ecs=snapshot(getter[0]['ecsAfterHex'])
            ready=state==255 and bool(ecs and getter_ecs and ecs['identityReady'] and getter_ecs['identityReady'] and identity(ecs)==identity(getter_ecs))
            if state&1:_require(first[0]==player+layout['meshVtableRva'],'live Mesh vtable')
            observation.update(getterCall=entry['parent'],sourceLookupCall=a[4],decoderCall=a[5],producerCall=a[6],sourceSlot=a[7],
                               meshObject=f'{a[3]:016x}',triangle=f'{a[2]:016x}',instanceId=first[2],state=state,
                               serializedOrigin=live,repeatedOrigin=repeat,sourceOrigin=baseline,validatedSampledJoin=ready,
                               boundary='direct sampled equality of original getter pointer and live typed Mesh-held cache with repeated CAB/PathID; continuous lifetime unresolved')
            caches.append(observation)
        elif kind in (50,51):
            start,end=struct.unpack_from('<2Q',q,176);_require(entry['qpc']<=start<=end<=r['qpc'],'preparation original interval')
            observation.update(family='PGS' if kind==50 else 'TGS',args=a,preparedResult=_u64(r['result']))
            observation.update(originalEntryQpc=start,originalReturnQpc=end)
            prepares.append(observation)
        elif kind in (52,53):
            parent=calls.get(entry['parent']);_require(parent and parent['kind']==a[7] and a[7] in (50,51) and a[0]==entry['parent'] and a[6] in (0,1),'solver prepare sample parent')
            _require(struct.unpack_from('<H',b,30)[0]==1,'preparation contact descriptor marker')
            cm=bytes.fromhex(r['sourceContextHex'])[:128];cm_ptr=struct.unpack_from('<Q',b,32)[0]
            _require(struct.unpack_from('<Q',q)[0]==cm_ptr,'prepared contact-manager pointer')
            observation.update(stage='before_prepare' if kind==52 else 'after_prepare',prepCall=a[0],descriptor=f'{a[1]:016x}',
                               headerIndex=a[3],lane=a[4],side=a[6],context=f'{a[5]:016x}',beforeDescriptorHex=b[:48].hex(),
                               afterDescriptorHex=e[:48].hex() if kind==53 else None,managerHex=cm.hex(),provenance=actor(r,q,cm,a[6]))
            pairs.append(observation)
        elif 54<=kind<=63 or kind==65:
            start,end=struct.unpack_from('<2Q',q,176);_require(entry['qpc']<=start<=end<=r['qpc'],'solver original interval')
            observation.update(family='PGS' if kind<62 else 'TGS',nativeKind=kind,args=a)
            observation.update(originalEntryQpc=start,originalReturnQpc=end)
            solves.append(observation)
        elif kind==64:
            parent=calls.get(entry['parent']);_require(parent and (54<=parent['kind']<=63 or parent['kind']==65) and a[0]==entry['parent'] and a[4] in (0,1),'solver solve sample parent')
            candidate=calls.get(a[3]);_require(not a[3] or candidate and candidate['kind'] in (50,51),'solver route preparation call')
            _require(not a[6]&~15,'solver route state')
            cm=bytes.fromhex(r['sourceContextHex'])[:128]
            provenance=actor(r,q,cm,a[4]) if a[6]&7==7 else None
            if a[6]&7==7:
                matching=[p for p in pairs if p['stage']=='after_prepare' and p['side']==a[4] and p['prepCall']==a[3]
                          and bytes.fromhex(p['afterDescriptorHex'])[:20]==b[:20]
                          and bytes.fromhex(p['afterDescriptorHex'])[32:48]==b[32:48]]
                native_entry=struct.unpack_from('<Q',bytes.fromhex(parent['returnRecord']['queryHex']),176)[0]
                _require(matching and candidate['qpc']<=a[7]<=native_entry and
                         any(int(p['context'],16)==a[5] and p['entryQpc']>=a[7] and p['managerHex'][48:128]==cm[24:64].hex() for p in matching), 'solver preparation route copied key/CM/context')
                _require(q[128:168]==cm[24:64],'solver repeated contact-manager provenance')
            exact_descriptor=bool(b[:20]==e[:20] and b[32:48]==e[32:48] and not r['flags']&256)
            before_ecs=snapshot(r['ecsBeforeHex']);after_ecs=snapshot(r['ecsAfterHex'])
            stable_actor=bool(before_ecs and after_ecs and before_ecs['identityReady'] and after_ecs['identityReady'] and identity(before_ecs)==identity(after_ecs))
            observation.update(solveCall=a[0],descriptor=f'{a[1]:016x}',lane=a[2],side=a[4],routePrepCall=a[3],
                               context=f'{a[5]:016x}',routeState=a[6],routeSampleQpc=a[7],beforeDescriptorHex=b[:48].hex(),afterDescriptorHex=e[:48].hex(),
                               stableDescriptorKey=exact_descriptor,stableEcsIdentity=stable_actor,provenance=provenance,
                               boundary='direct original solver contact invocation; preparation route remains conditional on sampled descriptor/CM identity and unresolved worker scene/step ownership')
            if profile.get('schema')=='endfieldCapture.collisionBuild.v17':
                mask=struct.unpack_from('<I',q,168)[0];_require(not mask&~7,'solver body copy read mask')
                observation['bodyReadMask']=mask
            solve_pairs.append(observation)
    limits=c['limits'];_require(len(getters)<=limits['maxGeometry'] and len(caches)<=limits['maxCacheSamples'] and
            len(prepares)<=limits['maxPrepCalls'] and len(solves)<=limits['maxSolveCalls'] and len(solve_pairs)<=limits['maxSolvePairs']*2,'stage sample limits')
    census=receipt['physicsStages']
    for key,limit in dict(geometryGetters=limits['maxGeometry'],cacheSamples=limits['maxCacheSamples'],cacheMatches=limits['maxCacheSamples'],
                          prepCalls=limits['maxPrepCalls'],prepPairs=limits['maxPrepPairs'],solveCalls=limits['maxSolveCalls'],solvePairs=limits['maxSolvePairs'],routeCandidates=limits['maxSolvePairs']*2).items():
        _require(type(census.get(key)) is int and 0<=census[key]<=limit,'stage census bound:'+key)
    _require(census['cacheMatches']==sum(x['state']==255 for x in caches) and
             census['routeCandidates']==sum(x['routeState']&7==7 for x in solve_pairs),'stage positive candidate census')
    _require(all(type(census.get(k)) is int and census[k]>=0 for k in ('gaps','limited')),'stage diagnostic census')
    for key,actual in dict(geometryGetters=len(getters),cacheSamples=len(caches),prepCalls=len(prepares),prepPairs=sum(p['stage']=='after_prepare' and p['side']==0 for p in pairs),solveCalls=len(solves),solvePairs=len(solve_pairs)//2).items():
        # Failed guarded reads can consume a selected prep-pair slot without a
        # later post-preparation row. This is a gap, never a invented pair.
        _require(type(census[key]) is int and census[key]>=actual and (key=='prepPairs' or census[key]==actual),'stage census:'+key)
    gaps=[]
    if not any(g['success'] for g in getters):gaps.append('No sampled successful original triangle getter.')
    if not any(c['validatedSampledJoin'] for c in caches):gaps.append('No validated getter-to-live-Mesh-cache provenance sample.')
    if not solve_pairs:gaps.append('No sampled solver contact descriptor; character movement queries alone do not establish solver participation.')
    if solve_pairs:gaps.append('Solver scene/step ownership, continuous descriptor lifetime, and positive impulse remain separate checks.')
    return dict(schema='endfield.collision-physics-stage-observations.v1',getters=getters,liveCaches=caches,prepares=prepares,
                preparationPairs=pairs,solves=solves,solvePairs=solve_pairs,coverage=census,gaps=gaps)

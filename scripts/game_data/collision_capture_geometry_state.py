"""Decode admitted array, pose, original-hit and task-generation observations."""
from collections import Counter
import math
import struct
from scripts.game_data.collision_capture_ecs import snapshot, identity


def decode_geometry_state(calls,profile,receipt,memory):
    from scripts.game_data.collision_capture_inspect import _require as need,_u64,_bytes,_origin
    c=profile['detailCapture']['contract'];player=_u64(receipt['playerBase']);limits=c['limits']
    cache=profile['stageCapture']['cacheLayout']['layout'];arrays=[];poses=[];simulations=[];releases=[];atomics=[];runs=[];inputs=[]
    windows={}
    for w in memory['windows']:
        if w['role'] in ('geometryVertices','geometryIndices'):windows.setdefault((w['call'],w['role']),[]).append(w)
    def header(raw):
        v=struct.unpack('<QII4QiIII',raw[:64]);tag,nv,nt,vertices,indices,held,mesh_tag,instance,flags,width,state=v
        need(not state&~15,'array header read flags')
        if state&1:need(mesh_tag==player+cache['mesh']['vtableRva'],'array typed Mesh')
        if state&2:need(tag==player+cache['triangle']['vtableRva'],'array typed triangle cache')
        if state&8:need(width==(2 if flags&cache['triangle']['index16Mask'] else 4) and flags<=255,'array index width/flags')
        return dict(triangleTag=tag,vertices=nv,triangles=nt,vertexPointer=f'{vertices:016x}',indexPointer=f'{indices:016x}',held=f'{held:016x}',meshTag=mesh_tag,instanceId=instance,flags=flags,indexWidth=width,readState=state)
    def task(raw):
        if profile.get('schema') in ('endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
            from scripts.game_data.collision_capture_lifecycle import task_header
            return task_header(raw,profile,player)
        values=struct.unpack('<7Q2I',raw[:64]);pointer,tag,manager,continuation,scene,dispatcher,manager_tag,refs,state=values
        need(not state&~15,'task read flags')
        if state&1:
            tags={player+c['bindings']['taskVtable']}
            if profile.get('schema') in ('endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):tags.update(player+t['vtableRva'] for t in profile['lifecycleCapture']['task']['contract']['taskTypes'])
            need(tag in tags,'typed task vtable')
        if state&2:need(manager_tag==player+c['bindings']['managerVtable'],'typed task manager')
        return dict(task=f'{pointer:016x}',vtable=f'{tag:016x}',manager=f'{manager:016x}',continuation=f'{continuation:016x}',scene=f'{scene:016x}',dispatcher=f'{dispatcher:016x}',managerVtable=f'{manager_tag:016x}',references=refs,readState=state)
    def original(entry,row):
        start,end=struct.unpack_from('<2Q',bytes.fromhex(row['queryHex']),176)
        need(entry['qpc']<=start<=end<=row['qpc'],'detail original interval');return start,end
    def ancestor(entry,call):
        seen=set()
        while entry and entry['call'] not in seen:
            if entry['call']==call:return True
            seen.add(entry['call']);entry=calls.get(entry['parent'])
        return False
    by_call={}
    scenes_by_parent={}
    for v in calls.values():
        if v['kind']==66:scenes_by_parent.setdefault(v['parent'],[]).append(v)
    for call,entry in sorted(calls.items()):
        row=entry['returnRecord'];kind=entry['kind']
        if kind==30:
            raw=_bytes(row['before'],64,'native hit input');repeat=_bytes(row['queryHex'],192,'native hit repeat')[64:120]
            hit=c['layout']['hit'];rep=c['representation'];flags=struct.unpack_from('<H',raw,rep['nativeHitFlagsCandidateOffset'])[0]
            carrier=bytes.fromhex(row['after']);echo=(raw[hit['point']:hit['point']+12]==carrier[:12] and raw[hit['normal']:hit['normal']+12]==carrier[12:24] and raw[hit['distance']:hit['distance']+4]==carrier[28:32])
            need(not any(raw[rep['nativeHitBytes']:]),'native hit input tail')
            distance=struct.unpack_from('<f',raw,hit['distance'])[0]
            parent=calls.get(entry['parent']);sweep=bool(parent and parent['kind'] in (16,17,21))
            inputs.append(dict(call=call,sourcePrefixHex=raw[:rep['nativeHitBytes']].hex(),repeatedPrefixHex=repeat.hex(),stableInput=raw[:rep['nativeHitBytes']]==repeat,
                outputConsumedFieldsEqual=echo,nativeFaceIndex=struct.unpack_from('<I',raw,hit['face'])[0],flagsCandidate=flags,
                positionCandidateValid=bool(flags&rep['candidatePositionMask']),normalCandidateValid=bool(flags&rep['candidateNormalMask']),faceCandidateValid=bool(flags&rep['candidateFaceMask']),
                initialOverlapCandidate=distance<=0 if sweep and math.isfinite(distance) else None,boundary=rep['hitBoundary']))
            continue
        if not 70<=kind<=75:continue
        a=list(map(_u64,row['args']));b=_bytes(row['before'],64,'detail before');e=_bytes(row['after'],128,'detail after');q=_bytes(row['queryHex'],192,'detail query')
        item=dict(call=call,parentCall=entry['parent'],thread=entry['thread'],entryQpc=entry['qpc'],returnQpc=row['qpc'])
        if kind==70:
            parent=calls.get(entry['parent']);need(parent and parent['kind']==49 and parent['returnRecord']['queryState']==255 and a[4]==parent['call'] and a[5]==parent['parent'],'array cache/getter ancestry')
            need(a[:4]==[_u64(parent['args'][i]) for i in (0,1,2,3)],'array owner arguments')
            before,after=header(b),header(e);origin=_origin(row['meshOrigin']);repeat=_origin(row['colliderOrigin'],required=row['colliderOrigin']['state']!=0)
            need(before['readState']==15 and before['held']==f'{a[2]:016x}' and before['instanceId']==parent['returnRecord']['meshId'] and origin==_origin(parent['returnRecord']['meshOrigin']),'array parent cache identity')
            need(a[6:8]==[before['vertices']*12,before['triangles']*3*before['indexWidth']] and all(0<n<=limits['maxArraySpanBytes'] for n in a[6:8]),'array byte/count bound')
            stable=b==e[:64] and origin==repeat
            summaries=[row['sourceMemory'],row['meshIdsMemory']]
            complete=stable and all(s['bytes']==n and not any(s[k] for k in ('limits','rejected','unreadable')) for s,n in zip(summaries,a[6:8]))
            need(row['queryState']==after['readState']|(16 if stable else 0)|(32 if complete else 0),'array copied state')
            first,last=snapshot(row['ecsBeforeHex']),snapshot(row['ecsAfterHex'])
            ecs_stable=bool(first and last and first['identityReady'] and last['identityReady'] and identity(first)==identity(last))
            item.update(getterCall=a[5],cacheSampleCall=a[4],actor=f'{a[0]:016x}',shape=f'{a[1]:016x}',triangle=f'{a[2]:016x}',mesh=f'{a[3]:016x}',before=before,after=after,
                        serializedOrigin=origin,stableHeaderAndOrigin=stable,complete=complete,stableEcsIdentity=ecs_stable,
                        validatedSampledJoin=complete and ecs_stable,spanWindows={role:windows.get((call,role),[]) for role in ('geometryVertices','geometryIndices')},
                        boundary='sampled original getter/cache join with repeated typed header and CAB/PathID; array equality requires stored comparison; endpoints do not establish an atomic snapshot or continuous lifetime')
            arrays.append(item)
        elif kind==71:
            parent=calls.get(entry['parent']);need(parent and parent['kind']==48 and a[2]==parent['call'] and a[3]==parent['parent'] and a[:2]==[_u64(parent['args'][2]),_u64(parent['args'][0])],'pose getter/actor/shape ancestry')
            frames=[]
            for raw,meta in ((b,q[:64]),(e[:64],q[64:128])):
                atag,stag,ap,sp,ab,sb,attached,af,sf=struct.unpack('<7Q2I',meta);state=struct.unpack_from('<I',raw,56)[0]
                need(not state&~31 and not any(raw[60:64]) and af<=255 and sf<=255,'pose state/flags')
                if state&1:need(atag==player+c['bindings']['actorVtable'],'typed static actor pose')
                if state&2:need(stag==player+c['bindings']['shapeVtable'],'typed shape pose')
                p=c['layout']['pose']
                if state&4:need(ap==(ab+p['actorBuffered'] if af&p['actorMask'] else a[0]+p['actorInline']),'actor pose selected address')
                if state&8:need(sp==(sb+c['representation']['shapeBufferedPoseOffset'] if sf&p['shapeMask'] else a[1]+p['shapeInline']),'shape pose selected address')
                if state&16:need(attached==a[0],'pose shape actor edge')
                floats=struct.unpack('<14f',raw[:56]);finite=all(math.isfinite(v) for v in floats)
                frames.append(dict(readState=state,actorPoseHex=raw[:28].hex(),shapePoseHex=raw[28:56].hex(),finite=finite,
                    actorRotation=list(floats[:4]) if finite else None,actorPosition=list(floats[4:7]) if finite else None,
                    shapeRotation=list(floats[7:11]) if finite else None,shapePosition=list(floats[11:14]) if finite else None,actorFlags=af,shapeFlags=sf,
                    actorPoseAddress=f'{ap:016x}',shapePoseAddress=f'{sp:016x}'))
            stable=frames[1]['readState']==31 and b==e[:64] and q[:64]==q[64:128]
            need(row['queryState']==frames[1]['readState']|(32 if stable else 0),'pose copied state')
            need(_u64(row['result'])==_u64(parent['returnRecord']['result']),'pose original getter result')
            start,end=original(entry,row)
            need(parent['qpc']<=entry['qpc']<=row['qpc']<=parent['returnRecord']['qpc'],'pose inside getter interval')
            first,last=snapshot(row['ecsBeforeHex']),snapshot(row['ecsAfterHex'])
            ecs_stable=bool(first and last and first['identityReady'] and last['identityReady'] and identity(first)==identity(last))
            item.update(getterCall=a[2],actor=f'{a[0]:016x}',shape=f'{a[1]:016x}',before=frames[0],after=frames[1],stable=stable,
                        stableEcsIdentity=ecs_stable,validatedCurrentPose=stable and ecs_stable and frames[1]['finite'],
                        originalEntryQpc=start,originalReturnQpc=end,boundary='typed static actor/global and shape/local getter-consumer fields around the original geometry getter; separately timed scalar reads')
            poses.append(item)
        elif kind==72:
            core=calls.get(a[6]);need(core and core['kind']==11 and core['thread']==entry['thread'] and ancestor(entry,a[6]),'simulation original core ancestry')
            need(a[1]==_u64(core['args'][1]) and a[4]<=0xffffffff and a[5] in (0,1),'simulation argument widths/step')
            frames=[struct.unpack('<2Q2I',raw[:24]) for raw in (b,e)]
            for public,tag,stage,state in frames:
                need(state in (0,1,3) and public==a[0] and (not state&1 or tag==player+c['bindings']['sceneVtable']),'simulation typed scene')
            registered=row['queryState']==1;need(row['queryState'] in (0,1) and (not registered or frames[0][2:]==(c['representation']['idleSimulationStage'],3)),'simulation generation eligibility')
            start,end=original(entry,row)
            item.update(coreCall=a[6],publicScene=f'{a[0]:016x}',scene=f'{a[0]-profile["dispatchCapture"]["contract"]["layout"]["scene"]["publicSceneDelta"]:016x}',
                beforeStage=frames[0][2],afterStage=frames[1][2],afterReadState=frames[1][3],registered=registered,originalEntryQpc=start,originalReturnQpc=end)
            simulations.append(item)
        elif kind==73:
            before,after=task(b),task(e);simulation=by_call.get(a[3]);source=calls.get(a[3])
            need(source and source['kind']==72 and simulation and simulation['registered'] and a[4]==simulation['coreCall'] and before['readState']==15 and before['manager']==f'{a[0]:016x}' and before['task']==f'{a[1]:016x}' and before['scene']==simulation['scene']==f'{a[2]:016x}','task release generation/receiver')
            need(bytes.fromhex(row['sourceContextHex'])[:64]==bytes.fromhex(source['before']),'release generation snapshot')
            start,end=original(entry,row);need(row['queryState']==after['readState'],'release read state')
            core=calls[a[4]]
            need(simulation['originalEntryQpc']<=entry['qpc']<=row['qpc']<=struct.unpack_from('<Q',bytes.fromhex(core['returnRecord']['after']))[0],'release inside owning original core interval')
            item.update(simulationCall=a[3],coreCall=a[4],before=before,after=after,originalEntryQpc=start,originalReturnQpc=end)
            releases.append(item)
        elif kind==74:
            parent=calls.get(entry['parent']);release=by_call.get(a[1]);need(parent and parent['kind']==73 and a[1]==entry['parent'] and release and entry['thread']==parent['thread'],'atomic original release ancestry')
            need(a[0]==a[2]+c['layout']['task']['references'] and a[6]==player+c['representation']['atomicReturnRva'] and a[3:6]==[_u64(parent['args'][3]),_u64(parent['args'][4]),_u64(parent['args'][2])],'atomic original reference/site/owner')
            need(b==bytes.fromhex(parent['before']),'atomic inherited task snapshot')
            after=task(e);value=_u64(row['result']);need(value<=0xffffffff,'atomic signed return width')
            queued=bool(row['queryState']&4);need(row['queryState'] in (1,3,7) and bool(row['queryState']&2)==(value==0),'atomic decision state')
            if queued:need(after['readState']==15 and after['dispatcher']!='0000000000000000' and b[:56]==e[:56] and value==0,'queued repeated typed task/dispatcher')
            start,end=original(entry,row)
            need(release['originalEntryQpc']<=entry['qpc']<=row['qpc']<=release['originalReturnQpc'],'atomic inside original release interval')
            item.update(releaseCall=a[1],simulationCall=a[3],coreCall=a[4],scene=f'{a[5]:016x}',before=task(b),after=after,zeroResult=value==0,queued=queued,originalEntryQpc=start,originalReturnQpc=end)
            atomics.append(item)
        else:
            before,after=task(b),task(e);queued=by_call.get(a[1]);need(before['readState']==15 and before['task']==f'{a[0]:016x}' and before['scene']==f'{a[4]:016x}' and before['manager']==f'{a[5]:016x}','run typed owner arguments')
            joined=row['queryState']==1;need(row['queryState'] in (0,1),'run route state')
            if joined:
                source=calls.get(a[1]);need(source and source['kind']==74 and queued and queued['queued'] and a[2:4]==[queued['simulationCall'],queued['coreCall']],'run original enqueue generation')
                need(bytes.fromhex(row['sourceContextHex'])[:64]==bytes.fromhex(source['returnRecord']['after'])[:64] and b==bytes.fromhex(source['returnRecord']['after'])[:64] and source['returnRecord']['qpc']<=entry['qpc'],'run repeated task identity and queue-before-run')
                need(struct.unpack_from('<Q',q)[0]==queued['originalReturnQpc'],'run original atomic timestamp')
                core=calls[a[3]];simulation=by_call[a[2]];projection=bytes.fromhex(core['returnRecord']['queryHex'])
                need(core['qpc']<=entry['qpc']<=row['qpc']<=struct.unpack_from('<Q',bytes.fromhex(core['returnRecord']['after']))[0],'run original owning core interval')
                selected=core['returnRecord']['queryState']==1 and struct.unpack_from('<Q',projection)[0]==int(simulation['publicScene'],16) and simulation['afterReadState']==3 and simulation['afterStage']==c['representation']['acceptedSimulationStage']
                status='observed_scene_generation_atomic_dispatch_and_task_run' if selected else 'unresolved_completed_core_or_accepted_scene_projection'
            else:status='unbound_task_generation'
            start,end=original(entry,row)
            scene_calls=scenes_by_parent.get(call,[])
            for scene_call in scene_calls:
                need(_u64(scene_call['args'][0])==int(before['scene'],16) and _u64(scene_call['args'][1])==int(before['continuation'],16),'run original scene/continuation binding')
                need(start<=scene_call['qpc']<=scene_call['returnRecord']['qpc']<=end,'scene inside original task run interval')
            item.update(enqueueCall=a[1],simulationCall=a[2],coreCall=a[3],before=before,after=after,status=status,producerJoined=joined,
                        sceneUpdateCalls=[v['call'] for v in scene_calls],originalEntryQpc=start,originalReturnQpc=end,
                        boundary='original scene generation, zero atomic decrement, typed release dispatcher and exact typed task run; missing or drifting phases remain unjoined')
            runs.append(item)
        if kind in (73,74,75) and profile.get('schema') in ('endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
            from scripts.game_data.collision_capture_lifecycle import task_owner
            item['ownerBefore']=task_owner(q[64:96],item['before'],profile,player)
            item['ownerAfter']=task_owner(q[96:128],item['after'],profile,player)
            if kind==73:item['producerCall']=a[6]
            if kind==74:item['producerCall']=a[7];need(a[7]==_u64(parent['args'][6]),'atomic producer echo')
            if kind==75:item['producerCall']=a[7]
        by_call[call]=item
    counts=dict(arrays=len(arrays),completeArrays=sum(x['complete'] for x in arrays),arrayBytes=sum(_u64(calls[x['call']]['args'][6])+_u64(calls[x['call']]['args'][7]) for x in arrays),
                poses=len(poses),hitInputs=len(inputs),simulations=len(simulations),releases=len(releases),atomicDecisions=len(atomics),enqueues=sum(x['queued'] for x in atomics),runs=len(runs),workerJoins=sum(x['producerJoined'] for x in runs))
    census=receipt['geometryState'];need(all(type(census.get(k)) is int and census[k]==v for k,v in counts.items()),'geometry/task producer accounting')
    need(all(type(census.get(k)) is int and census[k]>=0 for k in ('gaps','limited')),'detail diagnostic counters')
    for name,key in (('arrays','maxArrays'),('poses','maxPoses'),('simulations','maxSimulations'),('releases','maxTaskRecords'),('atomicDecisions','maxTaskRecords'),('runs','maxTaskRecords')):need(counts[name]<=limits[key],'detail sample bound:'+name)
    need(counts['arrayBytes']<=limits['maxArrayTotalBytes'],'detail array byte budget')
    start=12+len(profile['queryCapture']['hooks'])+len(profile['ecsCapture']['hooks'])+len(profile['stageCapture']['hooks'])+len(profile['dispatchCapture']['hooks'])
    for i,h in enumerate(profile['detailCapture']['hooks']):need(receipt['entered'][start+i]>=sum(v['kind']==h['kind'] for v in calls.values()),'detail original entry census')
    return dict(schema='endfield.collision-geometry-state-observations.v1',arrays=arrays,poses=poses,nativeHitInputs=inputs,simulations=simulations,releases=releases,atomicDecisions=atomics,runs=runs,
                coverage=census,workerCoverage=dict(Counter(r['status'] for r in runs)),boundary=c['evidenceBoundary'])


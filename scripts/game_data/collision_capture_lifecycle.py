"""Admit observed task producers and body activation without repairing gaps."""
from collections import Counter
import struct


def need(ok,detail):
    if not ok:raise ValueError('collision-lifecycle:'+detail)


def number(value):return int.from_bytes(bytes.fromhex(value),'little')


def task_header(raw,profile,player):
    values=struct.unpack('<7Q2I',raw[:64]);pointer,tag,manager,continuation,scene,dispatcher,manager_tag,refs,state=values
    c=profile['detailCapture']['contract'];tags={player+c['bindings']['taskVtable']}
    tags.update(player+t['vtableRva'] for t in profile['lifecycleCapture']['task']['contract']['taskTypes'])
    need(not state&~15,'task header flags')
    if state&1:need(tag in tags,'task concrete vtable')
    if state&2:need(manager_tag==player+c['bindings']['managerVtable'],'task manager vtable')
    return dict(task=f'{pointer:016x}',vtable=f'{tag:016x}',manager=f'{manager:016x}',continuation=f'{continuation:016x}',
        scene=f'{scene:016x}',dispatcher=f'{dispatcher:016x}',managerVtable=f'{manager_tag:016x}',references=refs,readState=state)


def task_owner(raw,header,profile,player):
    owner,scene,peer,role,state=struct.unpack('<3Q2I',raw)
    need(role<=len(profile['lifecycleCapture']['task']['contract']['taskTypes']) and not state&~7,'task owner kind/read flags')
    c=profile['lifecycleCapture']['task']['contract'];tag=int(header['vtable'],16)
    roles={player+profile['detailCapture']['contract']['bindings']['taskVtable']:0}
    roles.update({player+t['vtableRva']:i+1 for i,t in enumerate(c['taskTypes'])})
    if state&1:need(roles.get(tag)==role,'task owner/header concrete type')
    if state==7:
        need(scene==int(header['scene'],16),'task normalized Scene differs')
        if role==3:need(owner==peer and scene!=owner,'NPhaseCore reciprocal Scene owner')
        else:
            public=bool(role and c['taskTypes'][role-1]['ownerKind']=='publicScene')
            need(owner==scene+(c['publicSceneDelta'] if public else 0),'public/internal Scene task owner')
            if role:
                task=c['taskTypes'][role-1];need(int(header['task'],16)==scene+c['layout']['scene'][task['sceneField']]+(c['publicSceneDelta'] if public else 0),'embedded Scene task coordinate')
    return dict(owner=f'{owner:016x}',scene=f'{scene:016x}',sceneCore=f'{peer:016x}',role=role,readState=state)


def live_frame(raw,body_contract,body_state,player,*,body=True):
    values=struct.unpack('<5Qi4IHBB',raw[:64]);native,actor,tag,scene,address,instance,control,sleep,state,body_control,flags,cached,pad=values
    need(not state&~127 and not pad,'body read flags/padding')
    need(not state&2 or state&1,'body identity depends on native component')
    if state&4:need(state&1 and tag==player+body_state['layout']['actor']['dynamicVtable'],'typed dynamic body')
    for bit in (8,16,32,64):need(not state&bit or state&4,'body field read dependency')
    if state&8:need(control>>body_state['layout']['actor']['stateShift'] in (1,2) and scene>=65536,'body scene registration')
    if state&16:need(not flags&~body_state['layout']['body']['visibleMask'],'body flag width')
    if state&64:need(cached in (0,1),'cached kinematic scalar')
    if not body:need(not state&~3,'break object is not a Rigidbody')
    return dict(native=f'{native:016x}',actor=f'{actor:016x}',actorTag=f'{tag:016x}',internalScene=f'{scene:016x}',instanceId=instance,
        registration=control>>body_state['layout']['actor']['stateShift'] if state&8 else None,
        flagsAddress=f'{address:016x}',bodyControl=body_control,readState=state,
        kinematic=bool(flags&body_contract['kinematicMask']) if state&16 else None,sleeping=bool(sleep) if state&32 else None,
        rawSleepState=sleep if state&32 else None,cachedKinematic=bool(cached) if state&64 else None)


def decode_lifecycle(calls,profile,receipt,geometry):
    from scripts.game_data.collision_capture_inspect import _origin
    player=number(receipt['playerBase']);life=profile['lifecycleCapture'];task=life['task']['contract'];body=life['body']['contract']
    body_state=profile['bodyCapture']['contract'];simulations={s['call']:s for s in geometry['simulations']};runs={r['call']:r for r in geometry['runs']}
    producers=[];bodies=[];breaks=[];routes=[];rechecks=[];activations=[]
    def within(entry,parent):
        need(parent['thread']==entry['thread'],'original ancestor thread')
        cursor=entry;seen=set()
        while cursor and cursor['call'] not in seen:
            if cursor['call']==parent['call']:break
            seen.add(cursor['call']);cursor=calls.get(cursor['parent'])
        need(cursor is not None and cursor['call']==parent['call'],'original producer ancestry')
        need(parent['qpc']<=entry['qpc']<=entry['returnRecord']['qpc']<=parent['returnRecord']['qpc'],'original ancestor interval')
    for call,entry in sorted(calls.items()):
        kind=entry['kind']
        if not 84<=kind<=98:continue
        row=entry['returnRecord'];args=list(map(number,row['args']));before=bytes.fromhex(row['before']);after=bytes.fromhex(row['after']);query=bytes.fromhex(row['queryHex'])
        start,end=struct.unpack_from('<2Q',query,176);need(entry['qpc']<=start<=end<=row['qpc'],'original hook interval')
        item=dict(call=call,kind=kind,parentCall=entry['parent'],entryQpc=entry['qpc'],originalEntryQpc=start,originalReturnQpc=end)
        if kind>=94:
            from scripts.game_data.collision_capture_activation import decode as decode_activation
            item.update(decode_activation(entry,profile));activations.append(item);continue
        if kind in (84,85,91,92,93):
            bound=row['queryState']==1;need(row['queryState'] in (0,1),'producer binding state')
            sim=simulations.get(args[2]);need(not bound or sim and sim['registered'] and sim['scene']==f'{args[0]:016x}' and sim['coreCall']==args[3],'producer selected simulation')
            if not bound:need(args[2:4]==[0,0],'unbound producer cannot borrow a scene generation')
            if kind in (84,93):
                upstream=args[5] if kind==84 and profile['schema'] in ('endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17') else args[4] if kind==93 else 0
                if bound:
                    if upstream:
                        run=runs.get(upstream);need(run and run['producerJoined'] and run['before']['scene']==f'{args[0]:016x}' and run['simulationCall']==args[2] and run['coreCall']==args[3],'dependency producer upstream task generation')
                        expected_role=4 if kind==84 else 5
                        need(run['ownerBefore']['role']==expected_role,'dependency producer upstream concrete task')
                        need(run['producerCall']==args[6 if kind==84 else 5],'dependency producer upstream seed echo')
                        within(entry,calls[upstream])
                    else:
                        need(kind==84,'shape producer requires original task run')
                        within(entry,calls[args[2]])
                if profile['schema'] in ('endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17') or kind==93:
                    item.update(taskRunCall=upstream,seedProducerCall=args[6] if kind==84 and upstream else args[5] if kind==93 else 0)
                headers=[task_header(raw,profile,player) for raw in (before,bytes.fromhex(row['sourceContextHex'])[:64],after[:64],after[64:128])]
                owners=[task_owner(query[i*32:(i+1)*32],h,profile,player) for i,h in enumerate(headers)]
                need(headers[0]['task']==headers[2]['task'] and headers[1]['task']==headers[3]['task'],'producer embedded task roots')
                expected_cont=headers[3]['task'] if kind==84 else f'{args[1]:016x}'
                need(headers[2]['continuation']==expected_cont or headers[2]['readState']!=15,'producer original continuation wiring')
                if kind==93:need(headers[3]['continuation']==headers[2]['task'] or headers[3]['readState']!=15,'shape producer pre-narrowphase continuation')
                item.update(headers=headers,owners=owners)
            else:
                run=runs.get(args[4]);need(not bound or run and run['producerJoined'] and run['simulationCall']==args[2] and run['coreCall']==args[3] and run['before']['scene']==f'{args[0]:016x}','filter producer original task run')
                if bound:
                    within(entry,calls[args[4]]);need(args[5]==run['producerCall'],'filter producer seed echo')
                item.update(taskRunCall=args[4],seedProducerCall=args[5])
                if kind==85:
                    item.update(nphaseCore=f'{args[7]:016x}',nphaseAfter=f'{int.from_bytes(after[:8],"little"):016x}')
                    if bound:need(run['ownerBefore']['role']==2,'filter producer requires broadphase continuation run')
                else:
                    if bound:
                        need(run['ownerBefore']['role']==(7 if kind==91 else 8),'native phase requires public Scene root task')
                        need(bytes.fromhex(row['sourceContextHex'])[:64]==bytes.fromhex(calls[args[4]]['before']),'native phase inherited original root task')
                        need(args[7]<=0xffffffff and args[7]==number(calls[args[2]]['args'][1]),'native phase inherited original step delta')
                        if kind==91:need(args[7]&0x7fffffff and not (args[7]&0x7f800000==0x7f800000 and args[7]&0x007fffff),'native simulate zero/unordered no-op cannot seed tasks')
                    headers=[task_header(raw,profile,player) for raw in (before,after[:64])]
                    owners=[task_owner(query[n*32:(n+1)*32],h,profile,player) for n,h in enumerate(headers)]
                    need(headers[0]['task']==headers[1]['task'],'native phase root task identity')
                    item.update(headers=headers,owners=owners,deltaBits=f'{args[7]:08x}')
            item.update(simulationCall=args[2],coreCall=args[3],scene=f'{args[0]:016x}',status='observed_original_producer' if bound else 'unbound_original_producer');producers.append(item)
            continue
        first=live_frame(before,body,body_state,player,body=kind!=89);last=live_frame(after,body,body_state,player,body=kind!=89)
        need(row['queryState']==1|(2 if before==after[:64] else 0),'body snapshot repeat state')
        identities=[]
        for raw,frame in ((query[64:96],first),(query[96:128],last)):
            klass,statics,offset,initialized,native=struct.unpack('<2QiIQ',raw)
            if frame['readState']&2:
                need(klass and statics and initialized and 0<=offset<=256 and native==int(frame['native'],16),'body runtime InstanceID offset witness')
            identities.append(dict(klass=f'{klass:016x}',statics=f'{statics:016x}',nativeOffset=offset,initialized=initialized))
        item['identityReads']=identities
        source=_origin(row['colliderOrigin'],required=row['colliderOrigin']['state']!=0)
        repeat=_origin(row['meshOrigin'],required=row['meshOrigin']['state']!=0)
        item.update(managedBody=f'{args[0]:016x}',before=first,after=last,source=source,repeatedSource=repeat,
            stableNativeIdentity=first['native']==last['native'] and first['instanceId']==last['instanceId'] and bool(first['readState']&2 and last['readState']&2),
            stableSerializedIdentity=source==repeat and source['status']=='mapped')
        handle,binding_slot,root_origin=struct.unpack_from('<IIQ',query,128)
        item['rootHandle']=handle;item['rootOriginCall']=root_origin;item['rootBinding']=binding_slot
        if kind==89:breaks.append(item);continue
        if kind==88:need(number(row['result']) in (0,1),'sleeping original bool result');item['originalSleepingResult']=bool(number(row['result']))
        if kind==86:need(args[1] in (0,1),'kinematic bool argument');item['requestedKinematic']=bool(args[1])
        if args[4] and kind!=90:
            parent=calls.get(args[4]);allowed=(89,95,96,97) if profile['schema'] in ('endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17') else (89,);need(parent and parent['kind'] in allowed,'body break provenance');within(entry,parent)
            if profile['schema'] in ('endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):item.update(activationContextCall=args[4],activationContextKind=parent['kind'])
        if kind==87:
            from scripts.game_data.collision_capture_inspect import _floats
            need(args[2]<=0xffffffff,'force mode i32 width')
            item.update(forceMode=args[2] if args[2]<0x80000000 else args[2]-(1<<32),forceBefore=_floats(query[:12]) if not row['flags']&256 else None,forceAfter=_floats(query[16:28]) if not row['flags']&512 else None)
        committed_before,cb_state,committed_after,ca_state=struct.unpack_from('<4H',query,48)
        need(cb_state in (0,1) and ca_state in (0,1),'committed body read states')
        item.update(committedKinematicBefore=bool(committed_before&body['kinematicMask']) if cb_state else None,committedKinematicAfter=bool(committed_after&body['kinematicMask']) if ca_state else None)
        need(binding_slot<=2 and (kind!=90 or args[7]==binding_slot),'root binding index')
        binding=body['bindings'][args[7] if kind==90 else kind-86];expected=player+binding['functionRva'];cache_before,cache_after=struct.unpack_from('<2Q',query,32)
        item.update(breakCall=args[4],liveBindingMatches=cache_before==expected and cache_after==expected,
            observedAwakeDynamic=cache_before==expected and cache_after==expected and item['stableNativeIdentity'] and ca_state==1 and not committed_after&body['kinematicMask'] and last['readState']==127 and last['kinematic'] is False and last['sleeping'] is False,
            boundary='Observed original operation and separately timed state; no whole-step lifetime or shape/solver participation.')
        if profile['schema']=='endfieldCapture.collisionBuild.v17' and kind!=90:
            item['enrollmentReason']='activation_context' if args[4] else 'observed_awake_simulating_body' if handle else None
            if handle and not args[4]:need(kind==86 and args[1]==0 and item['observedAwakeDynamic'],'body retention without activation requires original dynamic operation')
        if kind==90:
            parent=calls.get(args[2]);origin=calls.get(args[1]);need(parent and parent['kind'] in (82,52,53,64),'body recheck owning pair/solver record')
            within(entry,parent);need(args[2]==entry['parent'] and origin and origin['kind'] in (86,87),'body recheck original operation')
            original=origin['returnRecord'];metadata=bytes.fromhex(original['queryHex']);oh,ob,oc=struct.unpack_from('<IIQ',metadata,128)
            need(handle==oh==args[5] and root_origin==oc==args[1] and binding_slot==ob==args[7] and handle and handle<=0xffffffff,'body recheck pin/source witness')
            enrolled=struct.unpack_from('<Q',query,144)[0];original_query=bytes.fromhex(original['queryHex']);source_enrolled=struct.unpack_from('<Q',original_query,144)[0]
            source_return=struct.unpack_from('<Q',original_query,184)[0]
            need(enrolled==source_enrolled and source_return<=enrolled<=original['qpc'] and enrolled<=entry['qpc'],'body pin must precede recheck after original operation')
            initial=live_frame(bytes.fromhex(original['after']),body,body_state,player)
            if parent['kind']==82:need(args[3:5]==list(map(number,parent['args'][:2])),'body recheck pair actor/shape')
            else:
                projection=bytes.fromhex(parent['returnRecord']['queryHex']);expected_actor=struct.unpack_from('<Q',projection,24)[0];expected_shape=struct.unpack_from('<Q',projection,16)[0]
                need(args[3:5]==[expected_actor,expected_shape],'body recheck solver actor/shape')
            matched=item['stableNativeIdentity'] and first['native']==initial['native'] and first['instanceId']==initial['instanceId'] and first['actor']==last['actor']==f'{args[3]:016x}'
            item.update(pairCall=args[2],originCall=args[1],shape=f'{args[4]:016x}',currentOwnedActor=matched,enrollmentQpc=enrolled)
            item['observedAwakeDynamic'] &= matched
            rechecks.append(item)
        else:bodies.append(item)
    by_producer={p['call']:p for p in producers};atomics={a['call']:a for a in geometry['atomicDecisions']}
    by_route={}
    for run in (sorted(geometry['runs'],key=lambda r:r['entryQpc']) if profile['schema'] in ('endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17') else geometry['runs']):
        if not run['ownerBefore']['role']:continue
        source=by_producer.get(run['producerCall']);queued=atomics.get(run['enqueueCall']);role=run['ownerBefore']['role']
        status='unbound_original_task_producer'
        if run['producerJoined']:
            public_root=role in (7,8)
            simulation=simulations.get(run['producerCall']) if public_root else None
            if public_root:
                need(task['taskTypes'][role-1]['role']==task['simulationSeedRole'],'public task unsupported original simulation seed role')
                need(simulation and simulation['call']==run['simulationCall'] and queued and queued['queued'],'public task original simulation seed')
                release=calls[queued['releaseCall']];within(release,calls[simulation['call']])
                need(simulation['originalEntryQpc']<=release['qpc']<=release['returnRecord']['qpc']<=simulation['originalReturnQpc'],'public task release inside original simulation')
                need(queued['producerCall']==simulation['call'],'public task simulation seed echo')
                source_entry=simulation['originalEntryQpc'];upstream_ok=True
            else:
                need(source and queued and queued['queued'] and source['simulationCall']==run['simulationCall'] and source['coreCall']==run['coreCall'],'task original producer/atomic/run generation')
                need(queued['producerCall']==run['producerCall'],'task producer seed echo')
                expected={1:(84,),2:(84,),3:(85,),4:(93,),5:(91,92),6:(93,)}[role]
                need(source['kind'] in expected,'task concrete producing NPhaseCore program' if role==3 else 'task concrete producing program')
                if role==3:need(source['nphaseCore']==run['ownerBefore']['owner'],'filter task producing NPhaseCore')
                if profile['schema'] in ('endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
                    if role in (3,5,6):within(calls[queued['releaseCall']],calls[source['call']])
                    if role!=3:
                        roots=[(h,o) for h,o in zip(source['headers'],source['owners']) if h['task']==run['before']['task'] and o['role']==role and o['readState']==7]
                        need(roots,'task original producer concrete root witness')
                source_entry=source['originalEntryQpc'];upstream_ok=True
                if profile['schema'] in ('endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17') and source.get('taskRunCall'):
                    upstream=by_route.get(source['taskRunCall'])
                    upstream_ok=bool(upstream and upstream['status']=='observed_original_producer_atomic_and_run')
            need(source_entry<=queued['entryQpc']<=run['entryQpc'],'task producer before queue and run')
            status='observed_original_producer_atomic_and_run' if run['status']=='observed_scene_generation_atomic_dispatch_and_task_run' and upstream_ok else 'unresolved_original_core_projection' if upstream_ok else 'unresolved_original_producer_chain'
        routes.append(dict(taskRunCall=run['call'],role=run['ownerBefore']['role'],producerCall=run['producerCall'],simulationCall=run['simulationCall'],coreCall=run['coreCall'],status=status))
        by_route[run['call']]=routes[-1]
    counts=dict(producers=len(producers),bodyEvents=len(bodies),breakEvents=len(breaks),bodyRechecks=len(rechecks));census=receipt['lifecycle']
    if profile['schema'] in ('endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
        counts['activationEvents']=len(activations)
        phase_counts=[sum(a['kind']==kind for a in activations) for kind in range(94,99)]
        need(all(n<=life['activation']['contract']['limits']['maxEventsPerStage'] for n in phase_counts),'activation per-stage sample limit')
        need(census.get('activationPhases')==phase_counts,'activation stage census')
        for key,value in (('managerTrue',True),('managerFalse',False)):
            need(census.get(key)==sum(a['kind']==98 and a['originalManagerResult'] is value for a in activations),'activation original manager result census')
    need(all(census.get(k)==v and type(census.get(k)) is int for k,v in counts.items()),'lifecycle event census')
    need(census.get('bodyRoots')==census.get('releasedBodyRoots') and type(census.get('bodyRoots')) is int and 0<=census['bodyRoots']<=body['limits']['maxBodyRoots'],'root handles released after quiescence')
    need(counts['bodyRechecks']<=body['limits']['maxBodyRechecks'],'body recheck limit')
    need(all(type(census.get(k)) is int and census[k]>=0 for k in ('gaps','limited')),'lifecycle diagnostic census')
    need(counts['producers']<=task['limits']['maxProducers'] and counts['bodyEvents']<=body['limits']['maxBodyEvents'] and counts['breakEvents']<=body['limits']['maxBreakEvents'],'lifecycle sample bounds')
    result=dict(schema='endfield.collision-lifecycle-observations.v2' if profile['schema'] in ('endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17') else 'endfield.collision-lifecycle-observations.v1',producers=producers,bodies=bodies,breaks=breaks,bodyRechecks=rechecks,taskRoutes=routes,
        coverage=census,routeCoverage=dict(Counter(r['status'] for r in routes)),boundary='Original producer/reference/run routes and body operations; absent sources and positive solver participation remain separate.')
    if profile['schema'] in ('endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):result['activationStages']=activations
    return result

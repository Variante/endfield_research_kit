"""Decode original dynamics updates and their saved island-count operands."""
import struct


def decode_dispatch(calls, profile, receipt):
    from scripts.game_data.collision_capture_inspect import _require, _u64, _bytes
    c=profile['dispatchCapture']['contract'];player=_u64(receipt['playerBase'])
    scenes=[];updates=[];decisions=[];by_call={}
    def snapshot(raw, pop):
        fields=struct.unpack('<6Q4I',raw[:64]);scene,context,manager,scene_tag,tag,pool,state,backend,mask,reserved=fields
        _require(not state&~31 and not mask&~63 and not reserved and backend in (0,1,2),'dispatch snapshot flags')
        _require(bool(state&4)==bool(backend),'dispatch backend state contradicts bytes')
        if state&1:_require(scene and scene_tag==player+c['layout']['scene']['vtableRva'],'dispatch typed public scene')
        if state&4:_require(context and backend and tag==player+c['layout']['context'][('pgs' if backend==1 else 'tgs')+'VtableRva'],'dispatch context vtable')
        if state&8:_require(state&4,'dispatch pool lacks typed context')
        if state&16:_require(state&2,'dispatch held context/manager match lacks scene read')
        values=struct.unpack('<6I',pop)
        return dict(scene=f'{scene:016x}',context=f'{context:016x}',islandManager=f'{manager:016x}',
            publicSceneVtable=f'{scene_tag:016x}',contextVtable=f'{tag:016x}',pool=f'{pool:016x}',state=state,
            backend={0:'unavailable',1:'pgs',2:'tgs'}[backend],populationMask=mask,
            population={name:values[i] for i,name in enumerate(('activeIslands','rigidBodies','kinematics','articulations','contactManagers','constraints')) if mask&(1<<i)})
    for call,entry in sorted(calls.items()):
        if entry['kind'] not in (66,67,68,69):continue
        row=entry['returnRecord'];a=list(map(_u64,row['args']));q=_bytes(row['queryHex'],192,'dispatch query')
        before=_bytes(row['before'],64,'dispatch before');after=_bytes(row['after'],128,'dispatch after')
        start,end=struct.unpack_from('<2Q',q,176)
        _require(entry['qpc']<=start<=end<=row['qpc'],'dispatch original interval')
        item=dict(call=call,parentCall=entry['parent'],thread=entry['thread'],kind=entry['kind'],entryQpc=entry['qpc'],returnQpc=row['qpc'],originalEntryQpc=start,originalReturnQpc=end)
        if entry['kind'] in (66,67,68):
            item.update(before=snapshot(before,q[:24]),after=snapshot(after,q[24:48]))
            _require(row['queryState']==item['after']['state'],'dispatch copied state')
            item['stableContextMembers']=before[:48]==after[:48]
        if entry['kind']==66:
            _require(int(item['before']['scene'],16)==int(item['after']['scene'],16)==a[0],'dispatch scene argument')
            item.update(scene=f'{a[0]:016x}',continuation=f'{a[1]:016x}',caller=f'{a[2]:016x}',sameThreadCoreCall=a[3],stepJoin='unresolved_worker_or_scene_projection')
            if a[3]:
                core=calls.get(a[3]);_require(core and core['kind']==11 and core['thread']==entry['thread'],'dispatch same-thread original core')
                _require(a[4:6]==list(map(_u64,core['args'][:2])),'dispatch original core request')
                ancestor=entry;seen=set()
                while ancestor and ancestor['call']!=a[3] and ancestor['call'] not in seen:
                    seen.add(ancestor['call']);ancestor=calls.get(ancestor['parent'])
                _require(ancestor and ancestor['call']==a[3],'dispatch core ancestry')
                returned=core['returnRecord'];cq=_bytes(returned['queryHex'],192,'core scene projection')
                if returned['queryState']==1:
                    public,tag,stamp=struct.unpack_from('<3Q',cq)
                    original_return=struct.unpack_from('<Q',bytes.fromhex(returned['after']))[0]
                    _require(original_return<=stamp<=returned['qpc'] and tag==player+c['layout']['scene']['vtableRva'],'dispatch completed-core scene projection')
                    if public==a[0]+c['layout']['scene']['publicSceneDelta']:
                        item['stepJoin']='same_thread_original_core_and_typed_scene'
            scenes.append(item)
        elif entry['kind'] in (67,68):
            arguments=list(struct.unpack_from('<14Q',q,48));family='pgs' if entry['kind']==67 else 'tgs'
            _require(arguments[:4]==a[:4] and all(arguments[i]<=0xffffffff for i in (5,7,8,11,13)),'dispatch fourteen argument widths/identity')
            _require(bytes.fromhex(entry['queryHex'])[48:160]==q[48:160],'dispatch original arguments changed')
            _require(int(item['before']['context'],16)==int(item['after']['context'],16)==a[0] and int(item['before']['islandManager'],16)==int(item['after']['islandManager'],16)==a[1],'dispatch update receiver arguments')
            item.update(family=family,arguments=arguments,sceneUpdateCall=a[4],scene=f'{a[5]:016x}',caller=f'{a[6]:016x}',sameThreadCoreCall=a[7],sceneJoin='unbound_update',stepJoin='unresolved_worker_or_scene_projection')
            if a[4]:
                parent=calls.get(a[4]);owner=by_call.get(a[4])
                _require(parent and parent['kind']==66 and entry['parent']==a[4] and parent['thread']==entry['thread'] and owner and a[5]==_u64(parent['args'][0]) and a[7]==_u64(parent['args'][3]),'dispatch scene/update ancestry')
                _require(bytes.fromhex(row['sourceContextHex'])[:64]==bytes.fromhex(parent['before']),'dispatch inherited scene snapshot')
                _require(owner['originalEntryQpc']<=entry['qpc']<=row['qpc']<=owner['originalReturnQpc'],'dispatch child original interval')
                if item['before']['state']&19==19 and item['before']['backend']==family:
                    item['sceneJoin']='original_scene_update_and_held_context'
                    item['stepJoin']=owner['stepJoin']
            updates.append(item)
        else:
            parent=calls.get(a[4]);update=by_call.get(a[4]);_require(parent and parent['kind'] in (67,68) and entry['parent']==a[4] and parent['thread']==entry['thread'] and update,'dispatch decision original update parent')
            site=next(s for s in c['decisionSites'] if s['kind']==parent['kind'])
            _require(65536<=a[2]<0x800000000000-512 and not a[2]%8 and a[1]==player+site['returnRva'] and a[3]==a[2]+site['countFromReturnSlot'] and struct.unpack_from('<Q',q,48)[0]==a[1],'dispatch original saved-count stack site')
            _require(a[5:8]==[_u64(parent['args'][4]),_u64(parent['args'][0]),_u64(parent['args'][5])],'dispatch decision owner arguments')
            _require(bytes.fromhex(row['sourceContextHex'])[:64]==bytes.fromhex(parent['before']),'dispatch decision inherited context')
            _require(update['originalEntryQpc']<=entry['qpc']<=row['qpc']<=update['originalReturnQpc'],'dispatch decision original interval')
            count,ready=struct.unpack_from('<2I',before);repeat,read_after=struct.unpack_from('<2I',after)
            _require(ready in (0,1) and read_after in (0,1),'dispatch count read flags')
            state=ready|(read_after<<1)|(4 if ready and read_after and count==repeat else 0)
            _require(state==row['queryState'],'dispatch count state contradicts bytes')
            item.update(family=update['family'],updateCall=a[4],sceneUpdateCall=a[5],scene=f'{a[7]:016x}',context=f'{a[6]:016x}',originalReturnSite=f'{a[1]:016x}',
                returnSlot=f'{a[2]:016x}',savedCountAddress=f'{a[3]:016x}',count=count if ready else None,repeatedCount=repeat if read_after else None,
                poolMatchesUpdate=int(update['before']['pool'],16)==a[0] and bool(update['before']['state']&8),sceneJoin=update['sceneJoin'],stepJoin=update['stepJoin'],
                decision='zero_active_islands_early_return' if state==7 and count==0 else 'nonzero_active_islands_pass_gate' if state==7 else 'unavailable_or_changed',
                boundary='Original saved branch operand copied at its reviewed call site and repeated; original update returned normally. Passing the island gate does not prove contact constraints, solver calls or impulse.')
            decisions.append(item)
        by_call[call]=item
    counters=receipt['physicsDispatch'];limits=c['limits']
    expected=dict(sceneUpdates=len(scenes),dynamicsUpdates=len(updates),decisions=len(decisions),
        zeroIslands=sum(d['decision']=='zero_active_islands_early_return' for d in decisions),
        nonzeroIslands=sum(d['decision']=='nonzero_active_islands_pass_gate' for d in decisions),unboundUpdates=sum(not u['sceneUpdateCall'] for u in updates))
    _require(all(type(counters.get(k)) is int and counters[k]==v for k,v in expected.items()),'dispatch producer accounting')
    _require(len(scenes)<=limits['maxSceneUpdates'] and len(updates)<=limits['maxDynamicsUpdates'] and len(decisions)<=limits['maxDecisions'],'dispatch sample limits')
    _require(all(type(counters.get(k)) is int and counters[k]>=0 for k in ('gaps','limited')),'dispatch diagnostic counters')
    base=12+len(profile['queryCapture']['hooks'])+len(profile['ecsCapture']['hooks'])+len(profile['stageCapture']['hooks'])
    entered={h['role']:receipt['entered'][base+i] for i,h in enumerate(profile['dispatchCapture']['hooks'])}
    for h,n in zip(profile['dispatchCapture']['hooks'],entered.values()):_require(n>=sum(e['kind']==h['kind'] for e in calls.values()),'dispatch entry census')
    classification=('dynamics_update_unentered' if not entered['pgs_dynamics_update'] and not entered['tgs_dynamics_update'] else
                    'observed_nonzero_island_decisions' if expected['nonzeroIslands'] else
                    'observed_zero_island_decisions' if expected['zeroIslands'] else 'entered_updates_without_valid_decision')
    return dict(schema='endfield.collision-dynamics-dispatch-observations.v1',scenes=scenes,updates=updates,decisions=decisions,coverage=counters,entered=entered,
                classification=classification,
                boundary='Original update entry and saved island decision are distinct from sampled checkpoint counts and later preparation/solve. Cross-thread step ownership, contact eligibility and positive impulse remain explicit joins.')

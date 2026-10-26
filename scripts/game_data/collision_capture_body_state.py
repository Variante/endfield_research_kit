"""Admit typed body/shape/scene snapshots without inferring contact execution."""
from collections import Counter
import struct
from scripts.game_data.collision_capture_ecs import snapshot,identity


def decode_frame(raw,filters,args,player,contract):
    from scripts.game_data.collision_capture_inspect import _require as need
    values=struct.unpack('<13Q4IHBBI',raw)
    names=('actorTag','shapeTag','attachedActor','storedScbScene','publicScene','sceneTag','bodyBuffer','bodyFlagsAddress','shapeBuffer','shapeFlagsAddress','filterSlot0','filterSlot1','notificationCallback','actorControl','bodyControl','shapeControl','readMask','bodyFlags','shapeFlags','actorClass','geometryType')
    row=dict(zip(names,values));l=contract['layout'];state=row['readMask'];cls=row['actorClass'];actor,shape=args[:2]
    need(not state&~2047 and row['shapeControl']<=255,'body state read mask/control')
    expected=1 if row['actorTag']==player+l['actor']['staticVtable'] else 2 if row['actorTag']==player+l['actor']['dynamicVtable'] else 0
    need(cls==expected and bool(state&1)==bool(cls),'body state typed actor class')
    if state&2:need(row['shapeTag']==player+l['shape']['vtable'],'body state typed shape')
    if state&4:need(state&2 and row['attachedActor']==actor,'body state shape/actor edge')
    if state&8:need(state&1,'body state registration owner')
    if state&16:
        need(cls==2 and row['bodyFlags']<=l['body']['visibleMask'],'body state original flags getter owner/width')
        selected=row['bodyBuffer']+l['body']['bufferedFlags'] if row['bodyControl']&l['body']['bufferMask'] else actor+l['body']['inlineFlags']
        need(row['bodyFlagsAddress']==selected and selected>=65536,'body state buffered/inline flag address')
    if state&32:
        selected=row['shapeBuffer']+l['shape']['bufferedFlags'] if row['shapeControl']&l['shape']['flagMask'] else shape+l['shape']['inlineFlags']
        need(state&2 and row['shapeFlagsAddress']==selected and selected>=65536,'body state buffered/inline shape flag address')
    if state&256:
        need(state&8 and row['actorControl']>>l['actor']['stateShift'] in (1,2) and row['storedScbScene']>=65536 and row['publicScene']==row['storedScbScene']+l['scene']['publicDelta'] and row['sceneTag']==player+l['scene']['vtable'],'body state registered public scene')
    if state&512:need(state&256,'body state scene configuration owner')
    need(not state&(64|128) or state&2,'body state typed filter words')
    if state&1024:need(state&2,'body state typed geometry')
    else:row['geometryType']=None
    words=struct.unpack('<8I',filters)
    row.update(simulationFilterWords=list(words[:4]) if state&64 else None,queryFilterWords=list(words[4:]) if state&128 else None,
               registrationState=('not_in_scene','insert_pending','in_scene','remove_pending')[row['actorControl']>>l['actor']['stateShift']] if state&8 else None,
               bodyModeBit0=bool(row['bodyFlags']&1) if state&16 else None,
               simulationEnabled=bool(row['shapeFlags']&1) if state&32 else None,
               sceneQueryEnabled=bool(row['shapeFlags']&2) if state&32 else None,
               triggerEnabled=bool(row['shapeFlags']&4) if state&32 else None)
    return row


def decode_body_states(calls,profile,receipt):
    from scripts.game_data.collision_capture_inspect import _require as need,_u64,_bytes
    c=profile['bodyCapture']['contract'];player=_u64(receipt['playerBase']);rows=[]
    for call,entry in sorted(calls.items()):
        if entry['kind']!=76:continue
        record=entry['returnRecord'];args=list(map(_u64,record['args']));getter=calls.get(args[2]);parent=calls.get(entry['parent'])
        need(getter and getter['kind']==48 and args[:2]==[_u64(getter['args'][2]),_u64(getter['args'][0])] and args[3]==getter['parent'],'body state original getter owner')
        need(parent and (parent['call']==getter['call'] or parent['kind']==71 and parent['parent']==getter['call']) and entry['thread']==getter['thread'],'body state original getter ancestry/thread')
        before=_bytes(record['sourceContextHex'],144,'body state before');after=_bytes(record['after'],128,'body state after');query=_bytes(record['queryHex'],192,'body state query')
        need(not any(before[128:]) and before[:64]==_bytes(record['before'],64,'body state before echo'),'body state wire tail/echo')
        frames=[decode_frame(raw,filters,args,player,c) for raw,filters in ((before[:128],query[:32]),(after,query[32:64]))]
        stable=before[:128]==after and query[:32]==query[32:64]
        need(record['queryState']==1|(2 if stable else 0),'body state repeat status')
        start,end=struct.unpack_from('<2Q',query,176)
        need(entry['qpc']<=start<=end<=record['qpc']<=getter['returnRecord']['qpc'] and getter['qpc']<=entry['qpc'],'body state original call interval')
        need(_u64(record['result'])==_u64(getter['returnRecord']['result']),'body state original return forwarding')
        first,last=snapshot(record['ecsBeforeHex']),snapshot(record['ecsAfterHex'])
        ecs_stable=bool(first and last and first['identityReady'] and last['identityReady'] and identity(first)==identity(last))
        mask=frames[1]['readMask']
        ready=stable and ecs_stable and mask&(1|2|4|8|32|1024)==1071 and (frames[1]['actorClass']==1 or bool(mask&16))
        rows.append(dict(call=call,getterCall=args[2],conversionCall=args[3],actor=f'{args[0]:016x}',shape=f'{args[1]:016x}',
                         before=frames[0],after=frames[1],stable=stable,stableEcsIdentity=ecs_stable,validatedTypedConfiguration=bool(ready),
                         originalEntryQpc=start,originalReturnQpc=end,boundary=c['evidenceBoundary']))
    expected=dict(samples=len(rows),dynamic=sum(r['after']['actorClass']==2 for r in rows),
                  queryOnly=sum(r['after']['readMask']&39==39 and not r['after']['shapeFlags']&1 and bool(r['after']['shapeFlags']&2) for r in rows),
                  gaps=sum(r['after']['readMask']!=(2031 if r['after']['actorClass']==1 else 2047) for r in rows))
    need(receipt['bodyStates']==expected and len(rows)<=c['limits']['maxBodyStates'],'body state producer accounting/bound')
    return dict(schema='endfield.collision-body-state-observations.v2',samples=rows,coverage=expected,
                classes=dict(Counter(str(r['after']['actorClass']) for r in rows)),boundary=c['evidenceBoundary'])

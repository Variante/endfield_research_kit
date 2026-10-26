"""Admit original pair/filter calls and separately timed passive policy reads.

Original returns prove sampled decisions. Configuration and model comparisons
remain conditional; absent parents, byte masks and sampled limits stay explicit.
"""
from __future__ import annotations

from collections import Counter
import struct

from scripts.game_data.collision_capture_body_state import decode_frame
from scripts.game_data.collision_capture_ecs import snapshot, identity
from scripts.game_data.collision_pair_filter_native import evaluate_shader


def need(value, detail):
    if not value:
        raise ValueError('collision-pair-filter:'+detail)


def raw(row, name, size):
    text = row[name]
    need(isinstance(text,str) and len(text)==size*2,'wire width:'+name)
    value = bytes.fromhex(text)
    need(value.hex()==text,'canonical wire:'+name)
    return value


def pointer(text):
    value = bytes.fromhex(text)
    need(len(value)==8 and value.hex()==text,'pointer wire')
    return int.from_bytes(value,'little')


def interval(entry, row):
    start,end = struct.unpack_from('<2Q',raw(row,'queryHex',192),176)
    need(entry['qpc']<=start<=end<=row['qpc'],'original/read interval')
    return start,end


def packet(data, valid):
    if not valid:
        return None
    fields = struct.unpack('<QQI4xQQII',data[:48])
    return dict(zip(('shader','constantBlock','constantBytes','pairCallback','allocator','kinematicKinematicMode','kinematicStaticMode'),fields))


def core(data, sim, contract):
    fields = struct.unpack('<4QHBBII4x2Q',data)
    names = ('shapeSim','actorSim','actorCore','shapeCore','committedFlags','shapeFlags','actorType','geometryType','readMask','nativeActorCandidate','nativeShapeCandidate')
    out = dict(zip(names,fields));state = out['readMask']
    need(out['shapeSim']==sim and not state&~511,'core root/read mask')
    for bit,parent in ((4,1),(8,4),(16,2),(32,8),(64,2),(128,8),(256,2)):
        need(not state&bit or state&parent,'core read dependency')
    if state&32:
        need(out['actorType'] in (1,2),'committed body flags type')
    if state&128:
        embedding = contract['layout']['bodyEmbedding']
        need(out['actorType'] in (0,1) and out['nativeActorCandidate']==out['actorCore']-embedding['scb']-embedding['core'],'core public actor embedding')
    if state&256:
        need(state&128 and out['nativeShapeCandidate']==out['shapeCore']-contract['layout']['shapeCore']['publicOffset'],'core public shape embedding/actor')
    out['boundary']='Original pair input core pointers and separately timed fields; public candidates require the separate typed owner read. No continuous lifetime.'
    return out


def step(data, entry, calls, contract):
    call,scene,simulation,physics,kind,state = struct.unpack('<4Q2I',data)
    need(state in (0,1,3),'step read mask')
    if not state:
        need(not any(data),'unobserved step carries values')
        return dict(status='unobserved_original_step')
    owner = calls.get(call)
    need(owner and owner['kind']==kind and owner['thread']==entry['thread'],'step original owner/thread')
    cursor = entry['parent'];found = False
    for _ in range(64):
        if cursor==call:found=True;break
        if not cursor:break
        ancestor=calls.get(cursor);need(ancestor is not None,'missing step ancestor');cursor=ancestor['parent']
    need(found,'step is not an original ancestor')
    args = list(map(pointer,owner['args']))
    if kind==75:
        expected=(args[4],args[2],args[3]);expected_state=3 if owner['returnRecord']['queryState']&1 else 1
    elif kind==72:
        expected=(args[0]-contract['layout']['scene']['publicDelta'],call,args[6]);expected_state=1
    elif kind==66:
        expected=(args[0],0,args[3]);expected_state=1
    elif kind in (67,68):
        expected=(args[5],0,args[7]);expected_state=1
    else:
        raise ValueError('collision-pair-filter:unsupported step ancestor')
    need((scene,simulation,physics)==expected and state==expected_state,'step identity fields')
    start,end = interval(owner,owner['returnRecord']);pair_start,pair_end = interval(entry,entry['returnRecord'])
    need(start<=pair_start<=pair_end<=end,'pair outside original step interval')
    return dict(status='observed_original_worker_generation' if state==3 else 'observed_original_ancestry',
        ownerCall=call,ownerKind=kind,internalScene=f'{scene:016x}',simulationCall=simulation,physicsCoreCall=physics,
        boundary='Same-thread original ancestry; a missing generation is not repaired by the scene address.')


def policy_frame(data, matrix, scene, player, body, contract):
    values = struct.unpack('<10Q4I',data[:96])
    names = ('internalScene','publicScene','publicTag','shader','pairCallback','notification','notificationVtable','notificationTarget','manager','matrix','kinematicKinematicMode','kinematicStaticMode','readMask','reserved')
    out = dict(zip(names,values));state=out['readMask']
    need(out['internalScene']==scene and out['publicScene']==scene+contract['layout']['scene']['publicDelta'] and not state&~127 and not out['reserved'],'policy scene domain/mask')
    if state&1:need(out['publicTag']==player+body['layout']['scene']['vtable'],'policy public scene tag')
    for bit,parent in ((2,1),(8,4),(16,8),(32,2),(64,32)):
        need(not state&bit or state&parent,'policy read dependency')
    need(not any(matrix[128:]),'policy matrix wire tail')
    out['matrixRows']=list(struct.unpack('<32I',matrix[:128])) if state&16 else None
    return out


def decode_pair_filter(calls, profile, receipt, *, task_routes=None):
    contract=profile['pairCapture']['contract'];body=profile['bodyCapture']['contract'];player=pointer(receipt['playerBase'])
    groups={kind:[] for kind in range(77,84)};by_call={}
    for call,entry in sorted(calls.items()):
        kind=entry['kind']
        if kind not in groups:continue
        row=entry['returnRecord'];args=list(map(pointer,row['args']));before=raw(row,'before',64);after=raw(row,'after',128)
        source=raw(row,'sourceContextHex',144);query=raw(row,'queryHex',192)
        item=dict(call=call,parentCall=entry['parent'],kind=kind,thread=entry['thread'])
        if kind in (77,83):
            if kind==77:need(pointer(row['result'])==args[0],'prefilter hidden result forwarding')
            else:need(pointer(row['result'])==0,'dispatcher void result')
            bm=struct.unpack_from('<I',before,48)[0];am=struct.unpack_from('<I',after,60)[0]
            need(not bm&~(3 if kind==77 else 1) and not am&~(7 if kind==77 else 3),'pair packet/result mask')
            need(not any(source[128:]),'pair core wire tail')
            first=[core(source[n*64:(n+1)*64],args[2+n],contract) for n in range(2)]
            last=[core(query[n*64:(n+1)*64],args[2+n],contract) for n in range(2)]
            original=struct.unpack_from('<HHI',after,48) if am&2 else None
            item.update(arguments=args,beforePacket=packet(before,bm&1),afterPacket=packet(after,am&1),
                beforeCores=first,afterCores=last,originalResult=dict(zip(('filterFlags','pairFlags','pairId'),original)) if original else None,
                triggerAfter=bool(after[56]) if kind==77 and am&4 else None,step=step(query[128:168],entry,calls,contract),
                originalInterval=list(interval(entry,row)))
            joined=item['step']
            if profile.get('schema') in ('endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17') and joined.get('ownerKind')==75:
                owner=calls[joined['ownerCall']]
                tag=int.from_bytes(bytes.fromhex(owner['before'])[8:16],'little')
                types=profile['lifecycleCapture']['task']['contract']['taskTypes']
                if tag in {player+t['vtableRva'] for t in types}:
                    need(task_routes is not None,'pair step requires original lifecycle admission')
                    route=next((r for r in task_routes if r['taskRunCall']==joined['ownerCall']),None)
                    need(route is not None,'pair step has no admitted task run')
                    joined['producerCall']=route['producerCall']
                    if route['status']!='observed_original_producer_atomic_and_run':
                        joined['status']=route['status']
        elif kind==78:
            need(pointer(row['result'])==args[0],'shader hidden result forwarding')
            masks=[struct.unpack_from('<I',data,36)[0] for data in (before,after)]
            need(not masks[0]&~7 and not masks[1]&~15,'shader read mask')
            fields=[list(struct.unpack('<8I',data[:32])) if mask&3==3 else None for data,mask in zip((before,after),masks)]
            original=struct.unpack_from('<H',after,34)[0] if masks[1]&8 else None
            if original is not None:need(original in (0,2),'selected shader result domain')
            item.update(arguments=args,filterWordsBefore=fields[0],filterWordsAfter=fields[1],
                filterWordsStable=fields[0] is not None and fields[0]==fields[1],originalFilterResult=original,
                pairFlagsBefore=struct.unpack_from('<H',before,32)[0] if masks[0]&4 else None,
                pairFlagsAfter=struct.unpack_from('<H',after,32)[0] if masks[1]&4 else None,originalInterval=list(interval(entry,row)))
        elif kind==79:
            need(pointer(row['result']) in (0,1),'layer bool result')
            fields=[]
            for data in (before,after):
                manager,matrix,address,value,state,a,b=struct.unpack('<3Q4I',data[:40])
                need(manager==args[0] and (a,b)==tuple(args[1:3]) and not state&~7,'layer owner/arguments/mask')
                if state&1:need(a<contract['rules']['layerLimit'] and b<contract['rules']['layerLimit'],'layer bounds')
                if state&4:need(state&3==3 and address==matrix+a*4,'layer row address')
                fields.append(dict(manager=manager,matrix=matrix,rowAddress=address,row=value if state&4 else None,readMask=state))
            item.update(arguments=args,before=fields[0],after=fields[1],layer0=args[1],layer1=args[2],originalExcluded=bool(pointer(row['result'])),originalInterval=list(interval(entry,row)))
        elif kind==80:
            need(pointer(row['result']) in (0,1),'object bool result')
            fields=[]
            for data,prefix in ((source,raw(row,'ecsBeforeHex',192)),(after,raw(row,'ecsAfterHex',192))):
                words=struct.unpack('<8I',data[:32]);a,b,begin,end,count,state,tagged,n,reserved=struct.unpack('<5Q4I',data[32:88])
                need(not state&~31 and not reserved and n<=contract['limits']['maxIgnoreKeys'],'ignore header mask/prefix')
                if state&1:
                    need((a,b)==(words[1]|words[3]<<32,words[5]|words[7]<<32),'ignore key words')
                    need(tagged==((1 if a&contract['rules']['tagMask'] else 0)|(2 if b&contract['rules']['tagMask'] else 0)),'ignore key tags')
                if state&2:need(state&1 and (tagged or not a or not b),'ignore bypass')
                if state&8:need(state&4 and not tagged and a and b and end>=begin and (end-begin)%8==0 and count==(end-begin)//8,'ignore extent')
                if state&16:need(state&8 and n==min(count,contract['limits']['maxIgnoreKeys']),'ignore prefix extent')
                need(not any(prefix[n*8:]),'ignore prefix wire tail')
                fields.append(dict(filterWords=list(words) if state&1 else None,key0=a,key1=b,begin=begin,end=end,count=count,readMask=state,
                    prefix=list(struct.unpack('<'+str(n)+'Q',prefix[:n*8])) if state&16 else None,completeList=bool(state&16 and n==count)))
            need(before==source[:64],'ignore header echo')
            item.update(arguments=args,before=fields[0],after=fields[1],originalExcluded=bool(pointer(row['result'])),originalInterval=list(interval(entry,row)))
        elif kind==81:
            need(pointer(row['result'])==0,'policy passive result')
            need(args[1]==entry['parent'] and calls[entry['parent']]['kind']==args[4] and args[5] in (0,1),'policy original/read owner')
            owner=calls[entry['parent']];owner_args=list(map(pointer,owner['args']))
            if args[4]==72:
                need(args[0]==owner_args[0]-contract['layout']['scene']['publicDelta'] and args[2:4]==[0,0],'policy simulation scene domain')
                start,end=interval(owner,owner['returnRecord'])
                need(row['qpc']<=start if args[5]==0 else entry['qpc']>=end,'policy simulation phase')
            elif args[4] in (76,82):
                owner_after=raw(owner['returnRecord'],'after',128)
                scene=struct.unpack_from('<Q',owner_after,24)[0];mask=struct.unpack_from('<I',owner_after,116)[0]
                need(mask&256 and args[0]==scene and args[2:4]==owner_args[:2] and args[5]==1,'policy typed body scene owner')
            else:
                raise ValueError('collision-pair-filter:unsupported policy source')
            need(before==source[:64] and not any(source[96:]) and not any(after[96:]),'policy frame echo/tail')
            first=policy_frame(source,raw(row,'ecsBeforeHex',192),args[0],player,body,contract)
            last=policy_frame(after,raw(row,'ecsAfterHex',192),args[0],player,body,contract)
            stable=source[:96]==after[:96] and raw(row,'ecsBeforeHex',192)==raw(row,'ecsAfterHex',192)
            need(row['queryState']==(3 if stable else 1),'policy repeat status')
            item.update(sourceKind=args[4],sourcePhase=args[5],before=first,after=last,stable=stable)
        elif kind==82:
            need(pointer(row['result'])==0,'owner passive result')
            parent=calls.get(args[2]);need(parent and parent['kind'] in (77,83) and entry['parent']==args[2] and args[3] in (0,1) and args[6] in (0,1),'pair owner parent/side/phase')
            parent_args=list(map(pointer,parent['args']));parent_row=parent['returnRecord']
            data=raw(parent_row,'sourceContextHex',144) if args[6]==0 else raw(parent_row,'queryHex',192)
            parent_core=core(data[args[3]*64:(args[3]+1)*64],parent_args[2+args[3]],contract)
            need((args[0],args[1],args[4],args[5])==(parent_core['nativeActorCandidate'],parent_core['nativeShapeCandidate'],parent_core['actorCore'],parent_core['shapeCore']),'pair owner core/public pointer join')
            need(before==source[:64] and not any(source[128:]),'pair owner body echo/tail')
            frames=[decode_frame(data,filters,args,player,body) for data,filters in ((source[:128],query[:32]),(after,query[32:64]))]
            stable=source[:128]==after and query[:32]==query[32:64]
            need(row['queryState']==(3 if stable else 1),'pair owner repeat status')
            start,end=interval(entry,row);ps,pe=interval(parent,parent['returnRecord'])
            need(end<=ps if args[6]==0 else start>=pe,'pair owner original phase interval')
            first,last=snapshot(row['ecsBeforeHex']),snapshot(row['ecsAfterHex'])
            for frame in (first,last):
                if frame:
                    need((frame['actor'],frame['shape'])==(f'{args[0]:016x}',f'{args[1]:016x}'),'pair owner ECS actor/shape')
            ready=bool(first and last and first['identityReady'] and last['identityReady'] and identity(first)==identity(last))
            item.update(actor=f'{args[0]:016x}',shape=f'{args[1]:016x}',side=args[3],phase=args[6],before=frames[0],after=frames[1],stable=stable,
                versionedEcsOwner=list(identity(first)) if ready else None,
                boundary='Passive typed pair-bound body/shape and repeated ECS reads; no geometry getter or serialized asset claim.')
        groups[kind].append(item);by_call[call]=item
    # Bind helper returns to their original shader, independently of passive
    # matrix/list comparisons. Unparented samples retain their own result.
    for shader in groups[78]:
        children=[r for r in groups[79]+groups[80] if r['parentCall']==shader['call']]
        layer=[r for r in children if r['kind']==79];obj=[r for r in children if r['kind']==80]
        shader['helperCalls']=[r['call'] for r in children]
        shader['conditionalModel']=None
        words=shader['filterWordsBefore'];args=shader['arguments']
        if words and shader['filterWordsStable'] and len(layer)==len(obj)==1:
            need((layer[0]['layer0'],layer[0]['layer1'])==(words[0]&255,words[4]&255),'shader/layer original argument join')
            need(obj[0]['arguments'][1:3]==[args[2],args[4]],'shader/object original argument join')
            for helper in (layer[0],obj[0]):
                need(shader['originalInterval'][0]<=helper['originalInterval'][0]<=helper['originalInterval'][1]<=shader['originalInterval'][1],'helper outside original shader interval')
            model=evaluate_shader(words[:4],words[4:],args[1],args[3],rules=contract['rules'],
                layer_excluded=layer[0]['originalExcluded'],object_excluded=obj[0]['originalExcluded'])
            shader['conditionalModel']=dict(**model,matchesOriginalResult=model['result']==shader['originalFilterResult'])
        dispatcher=by_call.get(shader['parentCall'])
        if dispatcher and dispatcher['kind']==83:
            need(args[5]==dispatcher['arguments'][0]+2,'dispatcher/shader pair-flags pointer')
            shader['dispatcherCall']=dispatcher['call']
    for pair in groups[77]+groups[83]:
        pair['shaderCalls']=[s['call'] for s in groups[78] if s.get('dispatcherCall')==pair['call']]
        pair['dispatcherCalls']=[d['call'] for d in groups[83] if d['parentCall']==pair['call']]
        pair['ownerCalls']=[o['call'] for o in groups[82] if o['parentCall']==pair['call']]
    names={77:'pairs',78:'shaders',79:'layers',80:'objects',81:'policies',82:'owners',83:'dispatches'}
    counts={name:len(groups[kind]) for kind,name in names.items()};observed=receipt['pairFiltering']
    need(all(type(observed[k]) is int and observed[k]>=0 for k in (*names.values(),'gaps','limited')),'pair producer counts')
    need(all(counts[k]==observed[k] for k in counts),'pair producer sample accounting')
    for name,maximum in (('pairs','maxPairs'),('dispatches','maxDispatches'),('shaders','maxShaders'),('layers','maxLayerChecks'),('objects','maxObjectChecks'),('policies','maxPolicies'),('owners','maxOwners')):
        need(counts[name]<=contract['limits'][maximum],'pair producer bound:'+name)
    return dict(schema='endfield.collision-pair-filter-observations.v1',coverage={**counts,'gaps':observed['gaps'],'limited':observed['limited']},
        prefilters=groups[77],dispatches=groups[83],shaders=groups[78],layerDecisions=groups[79],objectDecisions=groups[80],policies=groups[81],owners=groups[82],
        boundary='Original sampled pair/filter/helper outputs and passive typed configuration. No continuous lifetime, unobserved branch, unsampled pair census or solver-contact inference.')

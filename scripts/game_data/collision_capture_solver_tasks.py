"""Admit original PGS scheduling chains without a nearest-context/time join.

Evidence and admission boundary
-------------------------------
Exact selected PGS declarations distinguish context-owned UpdateContinuationTask
and solver start/partition/setup/preparation/solve/end tasks from Scene-owned
broadphase tasks. The update supplies the exact context, island manager,
continuation and auxiliary arguments. The common run wrapper ends before the
base-task release decrements its continuation, outside the worker scope.

Direct generation admission requires original manager release, zero decision and
typed run plus an unchanged same-thread completed-task witness at original base
release. Only that continuation inherits completion; nested releases may inherit
their active worker cause. New release/run invalidates stale addresses, contention
invalidates route epochs and missing budgets leave routes unbound. Raw headers,
typed manager, intervals and continuation equality are independently checked.
Prepared adapters do not supply unobserved live task routes, a public simulation
core, asset owner or continuous actor lifetime from context equality or timing.
"""
from collections import Counter
import struct


def need(value, message):
    if not value:
        raise ValueError('collision-solver-task:'+message)


def number(value):
    return int.from_bytes(bytes.fromhex(value),'little')


def header(raw, contract, detail, player):
    task,tag,manager,continuation,dispatcher,mtag,refs,role,state,pad=struct.unpack('<6Q4I',raw[:64])
    types={player+t['vtableRva']:t['role'] for t in contract['taskTypes']}
    need(not pad and not state&~7 and 0<=role<=len(types),'header flags/type')
    if state&1:need(types.get(tag)==role and role>0,'concrete vtable')
    if state&2:need(state&1 and mtag==player+detail['bindings']['managerVtable'],'TaskManager vtable')
    if state&4:need(state&2 and dispatcher>=65536,'dispatcher dependency')
    return dict(task=task,tag=tag,manager=manager,continuation=continuation,dispatcher=dispatcher,managerTag=mtag,
                references=refs,role=role,state=state)


def same(a,b,*,references=True):
    keys=('task','tag','manager','continuation','dispatcher','managerTag','role','state')+ (('references',) if references else ())
    return a['state']==b['state']==7 and all(a[k]==b[k] for k in keys)


def decode_solver_tasks(calls, profile, receipt):
    contract=profile['lifecycleCapture']['solver']['contract'];detail=profile['detailCapture']['contract'];player=number(receipt['playerBase'])
    records={};census=Counter()
    def within(child, parent):
        need(child['thread']==parent['thread'],'source thread differs')
        node=child;visited=set()
        while node and node['call'] not in visited and node['call']!=parent['call']:
            visited.add(node['call']);node=calls.get(node['parent'])
        need(node and node['call']==parent['call'],'source is not original ancestor')
        need(parent['qpc']<=child['qpc']<=child['returnRecord']['qpc']<=parent['returnRecord']['qpc'],'source interval')
        q=bytes.fromhex(parent['returnRecord'].get('queryHex',bytes(192).hex()));start,end=struct.unpack_from('<2Q',q,176)
        need(start<=child['qpc']<=child['returnRecord']['qpc']<=end,'outside original source call')
    for call,e in sorted(calls.items()):
        if not 99<=e['kind']<=102:continue
        row=e['returnRecord'];q=bytes.fromhex(row['queryHex']);a=list(map(number,row['args']));kind=e['kind']
        start,end=struct.unpack_from('<2Q',q,176)
        need(e['qpc']<=start<=end<=row['qpc'],'original call interval')
        dyn,source,source_kind,delta,scene,context,islands,epoch=struct.unpack_from('<2Q2I4Q',q)
        flags=row['queryState'];need(not flags&~(3 if kind==99 else 7 if kind==100 else 9 if kind==101 else 1),'route flags')
        before=header(bytes.fromhex(row['before']),contract,detail,player)
        after=header(bytes.fromhex(row['after']),contract,detail,player) if kind!=102 else None
        raw=bytes.fromhex(row['sourceContextHex'])[:64]
        task=a[1] if kind==99 else a[2] if kind==100 else a[0]
        need(before['task']==task,'header task argument')
        need(struct.unpack_from('<Q',raw)[0]==before['tag'] and struct.unpack_from('<Q',raw,16)[0]==before['manager'] and
             struct.unpack_from('<Q',raw,24)[0]==before['continuation'] and struct.unpack_from('<I',raw,32)[0]==before['references'],'raw task/header witness')
        if flags&1:need(dyn and source and epoch and context>=65536 and islands>=65536 and scene>=65536,'bound cause fields')
        else:need(not any((dyn,source,source_kind,delta,scene,context,islands,epoch)),'unbound cause carries identity')
        r=dict(call=call,kind=kind,entry=e,args=a,before=before,after=after,raw=raw,dynamics=dyn,source=source,
               sourceKind=source_kind,deltaBits=delta,scene=scene,context=context,islands=islands,epoch=epoch,flags=flags,start=start,end=end)
        records[call]=r;census[kind]+=1
    checked={};busy=set()
    def admit(call):
        if call in checked:return checked[call]
        need(call in records and call not in busy,'missing/cyclic scheduling source');busy.add(call);r=records[call]
        k=r['kind'];a=r['args'];e=r['entry'];bound=bool(r['flags']&1)
        if bound:
            if k==99:
                need(a[0]==r['before']['manager'] and a[2:7]==[r['dynamics'],r['source'],r['scene'],r['context'],r['islands']],'release cause echo')
                src=calls.get(r['source']);need(src and src['kind']==r['sourceKind'],'release original source kind');within(e,src)
                if src['kind']==67:
                    need(r['dynamics']==src['call'] and r['before']['role']==1,'PGS root identity')
                    args=list(map(number,src['args']));dq=bytes.fromhex(src['returnRecord']['queryHex'])
                    need([r['context'],r['islands'],r['scene']]==[args[0],args[1],args[5]] and
                         struct.unpack_from('<I',dq,136)[0]==r['deltaBits'],'original PGS arguments/delta')
                    d=bytes.fromhex(src['before']);state,backend=struct.unpack_from('<2I',d,48)
                    need(state==31 and backend==1 and struct.unpack_from('<3Q',d)==(r['scene'],r['context'],r['islands']),'original typed Scene/PGS ownership')
                    need(struct.unpack_from('<3Q',r['raw'],40)==(args[0],args[1],args[3]) and r['before']['continuation']==args[2],'original root stored argument handoff')
                else:
                    need(src['kind'] in (101,102),'unsupported scheduling source')
                    parent=admit(src['call']);need(parent['bound'],'source generation unbound')
                    need(all(r[x]==parent[x] for x in ('dynamics','deltaBits','scene','context','islands','epoch')),'source generation differs')
                    if src['kind']==102:need(parent['before']['continuation']==a[1],'completion released wrong continuation')
            elif k==100:
                parent=admit(a[1]);need(parent['kind']==99 and e['parent']==a[1] and parent['bound'],'atomic original release');within(e,parent['entry'])
                need(a[0]==a[2]+contract['layout']['task']['references'] and a[2]==parent['before']['task'] and
                     a[7]==player+detail['representation']['atomicReturnRva'],'atomic operand/return site')
                need(same(r['before'],parent['before']) and r['raw']==parent['raw'],'atomic source header')
                need(r['source']==a[1] and r['sourceKind']==99,'atomic source identity')
                if r['flags']&4:
                    need(r['flags']&2 and number(e['returnRecord']['result'])==0 and r['after']['references']==0 and same(r['before'],r['after'],references=False),'zero-reference queue decision')
            elif k==101:
                parent=admit(a[1]);need(parent['kind']==100 and parent['flags']&4,'worker queue absent/unadmitted')
                need(a[3]==parent['args'][1] and a[0]==parent['before']['task'] and same(r['before'],parent['after']),'worker generation header differs')
                need(r['start']>=parent['end'],'worker precedes atomic decision')
                need(r['source']==a[3] and r['sourceKind']==99,'worker original release identity')
                if r['flags']&8:need(same(r['before'],r['after']),'completed worker header differs')
            else:
                parent=admit(a[1]);need(parent['kind']==101 and parent['flags']&8 and parent['entry']['thread']==e['thread'],'completion worker generation')
                need(same(r['before'],parent['after']) and r['raw']==parent['raw'] and r['start']>=parent['end'] and a[3]==r['before']['continuation'],'completion header/lifetime handoff')
                need(r['source']==a[1] and r['sourceKind']==101,'completion source identity')
            if k!=99:
                need(all(r[x]==parent[x] for x in ('dynamics','deltaBits','scene','context','islands','epoch')),'queued generation differs')
        else:
            if k==101:need(not a[1],'unbound worker carries queue')
            if k==102:need(not a[1],'unbound completion carries worker')
        r['bound']=bound;checked[call]=r;busy.remove(call);return r
    for call in records:admit(call)
    stages=[]
    for call,e in sorted(calls.items()):
        if e['kind'] not in (50,54,55,56,57,58,59,60,61):continue
        cursor=e;visited=set();owner=None
        while cursor and cursor['call'] not in visited:
            visited.add(cursor['call'])
            if cursor['kind']==101:owner=checked[cursor['call']];break
            cursor=calls.get(cursor['parent'])
        if owner:
            within(e,owner['entry'])
            stages.append(dict(call=call,kind=e['kind'],workerCall=owner['call'],dynamicsCall=owner['dynamics'] if owner['bound'] else None,
                status='observed_original_pgs_task_generation' if owner['bound'] else 'unbound_worker_generation'))
    result=[]
    for r in records.values():
        result.append(dict(call=r['call'],kind=r['kind'],task=f"{r['before']['task']:016x}",role=r['before']['role'],sourceCall=r['source'],sourceKind=r['sourceKind'],
            dynamicsCall=r['dynamics'] or None,internalScene=f"{r['scene']:016x}" if r['scene'] else None,deltaBits=r['deltaBits'],
            status='observed_original_scheduling_cause' if r['bound'] else 'unbound_scheduling_cause'))
    receipt_counts=receipt['solverTasks']
    for kind,key in ((99,'releases'),(100,'atomics'),(101,'runs'),(102,'completions')):need(receipt_counts[key]==census[kind],'receipt '+key+' census')
    need(receipt_counts['enqueues']==sum(bool(r['flags']&4) for r in records.values() if r['kind']==100),'enqueue census')
    need(receipt_counts['joins']==sum(r['bound'] for r in records.values() if r['kind']==101),'worker join census')
    return dict(schema='endfield.collision-solver-task-observations.v1',routes=result,stages=stages,
        coverage=dict(Counter(s['status'] for s in stages)),
        boundary='Original PGS dynamics-call scheduling cause; public simulation core, asset provenance, continuous body lifetime and fresh response remain separate evidence.')

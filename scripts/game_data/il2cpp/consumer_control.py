"""Complete named-consumer byte/edge/frame checks without live branch claims."""
from __future__ import annotations
from collections import deque
from .initializer_control import control_transfer
from .field_setup_control import _frames
from .integer_source_operands import is_unknown_instruction

LABEL='consumerControl'

def check_consumer_control(rows,*,entry,owned_ranges):
    by_at={int(r['va'],16):r for r in rows}
    if len(by_at)!=len(rows) or entry not in by_at:raise ValueError(LABEL+'.entry-or-duplicate')
    if any(is_unknown_instruction(r) for r in rows):raise ValueError(LABEL+'.unknown-instruction')
    ordered=sorted(owned_ranges)
    if not ordered or any(a>=b for a,b in ordered) or any(a[1]>b[0] for a,b in zip(ordered,ordered[1:])):
        raise ValueError(LABEL+'.owned-ranges')
    covered=set()
    for start,end in ordered:
        part=sorted((r for r in rows if start<=int(r['va'],16)<end),key=lambda r:int(r['va'],16))
        cursor=start
        for row in part:
            at=int(row['va'],16);size=len(bytes.fromhex(row['bytes']))
            if at!=cursor or not size or cursor+size>end:raise ValueError(LABEL+'.byte-partition')
            covered.add(at);cursor+=size
        if cursor!=end:raise ValueError(LABEL+'.byte-partition')
    if covered!=set(by_at):raise ValueError(LABEL+'.outside-owned-range')
    edges={};calls=[];branches=[];returns=[];traps=[]
    for at,row in sorted(by_at.items()):
        flow=control_transfer(row);kind=flow['kind'];end=at+len(bytes.fromhex(row['bytes']));targets=[]
        if kind in ('jump','conditional'):
            targets.append(flow['target']);branches.append({'site':at,**flow})
        if kind in ('next','conditional','call','indirectCall','registerCall'):targets.append(end)
        if kind in ('call','indirectCall','registerCall'):
            if kind=='call' and flow['target'] in by_at:raise ValueError(LABEL+'.call-into-owned-body')
            calls.append({'site':at,**flow})
        elif kind=='return':returns.append(at)
        elif kind=='trap':traps.append(at)
        elif kind not in ('next','jump','conditional'):raise ValueError(LABEL+'.unsupported-transfer')
        if any(target not in by_at for target in targets):raise ValueError(LABEL+'.edge-outside-instruction-boundary')
        edges[at]=set(targets)
    reached=set();pending=deque((entry,))
    while pending:
        at=pending.popleft()
        if at in reached:continue
        reached.add(at);pending.extend(edges[at]-reached)
    if reached!=set(by_at):raise ValueError(LABEL+'.unreachable-owned-instructions')
    frames=_frames(rows,edges,0,{'entryRva':entry},transfer_decoder=control_transfer)
    return {'instructionsChecked':len(rows),'ownedRangesChecked':len(ordered),'calls':calls,
        'branches':branches,'returns':returns,'traps':traps,'frames':frames,'edges':edges,
        'evidenceBoundary':'conditional','condition':'static reachability and ordinary returning Win64 callees',
        'branchFeasibilityKnown':False,'runtimeExecutionKnown':False}

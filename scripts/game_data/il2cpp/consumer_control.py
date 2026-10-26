"""Complete named-consumer byte/edge/frame checks without live branch claims."""
from __future__ import annotations
from collections import deque
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.field_setup_control import _frames
from scripts.game_data.il2cpp.integer_source_operands import is_unknown_instruction

LABEL='consumerControl'

def consumer_transfer(row,*,computed_jump_targets=None,tail_exits=None):
    at=int(row['va'],16);computed_jump_targets=computed_jump_targets or {};tail_exits=tail_exits or {}
    if at in computed_jump_targets and at in tail_exits:raise ValueError(LABEL+'.computed-tail-overlap')
    if at in tail_exits:
        raw=bytes.fromhex(row['bytes']);spec=tail_exits[at]
        if not isinstance(spec,dict):raise ValueError(LABEL+'.tail-exit-shape')
        if set(spec)=={'register'}:
            opcode=raw[1:] if len(raw)==3 and raw[0] in (0x40,0x41,0x48,0x49) else raw
            rex=raw[0] if len(raw)==3 else 0
            if len(opcode)!=2 or opcode[0]!=0xff or not 0xe0<=opcode[1]<=0xe7:raise ValueError(LABEL+'.tail-register-bytes')
            register=('rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi','r8','r9','r10','r11','r12','r13','r14','r15')[(opcode[1]&7)+(8 if rex&1 else 0)]
            if register=='rsp' or spec['register']!=register or row['text']!='jmp '+register:raise ValueError(LABEL+'.tail-register-value')
            return dict(kind='tailExit',register=register)
        if set(spec)=={'target'}:
            flow=control_transfer(row)
            if flow.get('kind')!='jump' or type(spec['target']) is not int or flow['target']!=spec['target']:raise ValueError(LABEL+'.tail-direct-target')
            return dict(flow,kind='tailExit')
        raise ValueError(LABEL+'.tail-exit-shape')
    if at in computed_jump_targets:
        raw=bytes.fromhex(row['bytes'])
        if len(raw)!=2 or raw[0]!=0xff or not 0xe0<=raw[1]<=0xe7:raise ValueError(LABEL+'.computed-register-jump')
        register=('rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi')[raw[1]-0xe0]
        if row['text']!='jmp '+register:raise ValueError(LABEL+'.computed-register-jump-text')
        return dict(kind='computedJump',register=register)
    return control_transfer(row)


def build_consumer_control_graph(rows,*,entry,owned_ranges,computed_jump_targets=None,tail_exits=None):
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
    computed_jump_targets=computed_jump_targets or {}
    if any(type(site) is not int or site not in by_at or not isinstance(targets,(list,tuple,set,frozenset))
           or not 1<=len(targets)<=256 or any(type(target) is not int or target not in by_at for target in targets)
           for site,targets in computed_jump_targets.items()):
        raise ValueError(LABEL+'.computed-jump-boundaries')
    tail_exits=tail_exits or {}
    if any(type(site) is not int or site not in by_at for site in tail_exits):raise ValueError(LABEL+'.tail-exit-boundary')
    def selected_transfer(row):return consumer_transfer(row,computed_jump_targets=computed_jump_targets,tail_exits=tail_exits)
    edges={};calls=[];branches=[];returns=[];traps=[];tails=[]
    for at,row in sorted(by_at.items()):
        flow=selected_transfer(row);kind=flow['kind'];end=at+len(bytes.fromhex(row['bytes']));targets=[]
        if kind=='tailExit':
            if 'target' in flow and any(a<=flow['target']<b for a,b in ordered):raise ValueError(LABEL+'.tail-into-owned-body')
            tails.append(dict(site=at,**flow))
        if kind=='computedJump':
            targets.extend(computed_jump_targets[at]);branches.append({'site':at,**flow})
        if kind in ('jump','conditional'):
            targets.append(flow['target']);branches.append({'site':at,**flow})
        if kind in ('next','conditional','call','indirectCall','registerCall'):targets.append(end)
        if kind in ('call','indirectCall','registerCall'):
            if kind=='call' and flow['target'] in by_at and flow['target']!=entry:raise ValueError(LABEL+'.call-into-owned-body')
            calls.append({'site':at,**flow})
        elif kind=='return':returns.append(at)
        elif kind=='trap':traps.append(at)
        elif kind not in ('next','jump','conditional','computedJump','tailExit'):raise ValueError(LABEL+'.unsupported-transfer')
        if any(target not in by_at for target in targets):raise ValueError(LABEL+'.edge-outside-instruction-boundary')
        edges[at]=set(targets)
    reached=set();pending=deque((entry,))
    while pending:
        at=pending.popleft()
        if at in reached:continue
        reached.add(at);pending.extend(edges[at]-reached)
    return {'instructionsChecked':len(rows),'ownedRangesChecked':len(ordered),'calls':calls,
        'branches':branches,'returns':returns,'traps':traps,'tailExits':tails,'edges':edges,
        'reachableInstructions':sorted(reached),'nonEntryInstructions':sorted(set(by_at)-reached)}


def check_consumer_control(rows,*,entry,owned_ranges,computed_jump_targets=None,tail_exits=None):
    graph=build_consumer_control_graph(rows,entry=entry,owned_ranges=owned_ranges,computed_jump_targets=computed_jump_targets,tail_exits=tail_exits)
    if graph['nonEntryInstructions']:raise ValueError(LABEL+'.unreachable-owned-instructions')
    def frame_transfer(row):
        flow=consumer_transfer(row,computed_jump_targets=computed_jump_targets,tail_exits=tail_exits)
        return {'kind':'return' if flow['kind']=='tailExit' else 'jump' if flow['kind']=='computedJump' else flow['kind']}
    frames=_frames(rows,graph['edges'],0,{'entryRva':entry},transfer_decoder=frame_transfer)
    return {**graph,'frames':frames,'evidenceBoundary':'conditional',
        'condition':'static reachability and ordinary returning Win64 callees, including recursive entry calls; selected external tail exits require a restored entry stack and remain conditional on ordinary tail-call behavior',
        'branchFeasibilityKnown':False,'runtimeExecutionKnown':False}

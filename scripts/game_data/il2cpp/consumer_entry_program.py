"""Separate the ordinary entry graph from unentered owned byte candidates."""
from scripts.game_data.il2cpp.consumer_control import build_consumer_control_graph,check_consumer_control
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions


def ordinary_consumer_entry(rows,*,entry,owned_ranges,computed_jump_targets=None,tail_exits=None):
    graph=build_consumer_control_graph(rows,entry=entry,owned_ranges=owned_ranges,computed_jump_targets=computed_jump_targets,tail_exits=tail_exits)
    reached=set(graph['reachableInstructions']);selected=[];ranges=[];unentered=[]
    for row in sorted(rows,key=lambda row:int(row['va'],16)):
        at=int(row['va'],16);end=at+len(bytes.fromhex(row['bytes']))
        if at not in reached:unentered.append(row);continue
        selected.append(row)
        if ranges and ranges[-1][1]==at:ranges[-1]=(ranges[-1][0],end)
        else:ranges.append((at,end))
    jumps={at:targets for at,targets in (computed_jump_targets or {}).items() if at in reached}
    tails={at:spec for at,spec in (tail_exits or {}).items() if at in reached}
    control=check_consumer_control(selected,entry=entry,owned_ranges=ranges,computed_jump_targets=jumps,tail_exits=tails)
    return dict(rows=selected,ranges=ranges,control=control,fullGraph=graph,computedJumpTargets=jumps,tailExits=tails,
        unenteredOwnedByteCandidates=unentered,evidenceBoundary='conditional',
        condition='Every owned byte is retained. Frame/value proofs cover the ordinary entry graph; unentered owned bytes remain decoded candidates. Exception/resumption entries and runtime execution are outside this proof.')


def read_ordinary_consumer_entry(image,body,*,tail_targets=()):
    base=image.pe.image_base
    ranges=[(base+row['runtimeTriple'][0],base+row['runtimeTriple'][1]) for row in image.unwind_index.family(body.pointer-base)['ranges']]
    rows=[]
    for start,end in sorted(ranges):rows+=decode_type_data_initialization_instructions(image.mapper,image.pe.bytes_at_va(start,end-start),start)
    rows=[dict(row,offset=int(row['va'],16)-body.pointer) for row in rows]
    if not isinstance(tail_targets,(tuple,list,set,frozenset)) or len(tail_targets)>16 or any(type(t)is not int or not 0<t<1<<64 for t in tail_targets):raise ValueError('consumerEntry.selected-tail-targets')
    tails={}
    for row in rows:
        flow=control_transfer(row)
        if flow['kind']=='jump' and flow['target'] in tail_targets:tails[int(row['va'],16)]=dict(target=flow['target'])
    if {v['target'] for v in tails.values()}!=set(tail_targets):raise ValueError('consumerEntry.selected-tail-target-not-used')
    return ordinary_consumer_entry(rows,entry=body.pointer,owned_ranges=ranges,tail_exits=tails)

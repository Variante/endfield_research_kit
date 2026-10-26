"""Decode every reachable instruction in a bounded, call-free entry program.

A closed reachable graph proves neither physical function extent nor ownership
of unused bytes. Branches into instruction interiors and escapes are refused.
"""
from __future__ import annotations
from collections import deque
from .initializer_control import control_transfer
from .integer_source_operands import is_unknown_instruction
from .integer_widths import decode_byte_register_xor
from .memory_moves import decode_memory_move
from .integer_context_memory import decode_memory_register_compare
from .integer_tag_dispatch import decode_memory_immediate_compare


def decode_closed_leaf_entry(mapper,data,entry_va):
    if not isinstance(data,bytes) or not data or type(entry_va) is not int or entry_va<0:
        raise ValueError('closedLeafEntry.input-domain')
    pending=deque([entry_va]);rows={};edges={}
    while pending:
        at=pending.popleft()
        if at in rows:continue
        if any(other<at<other+len(bytes.fromhex(old['bytes'])) for other,old in rows.items()):
            raise ValueError(f'closedLeafEntry.overlapping-instructions: target={hex(at)}')
        offset=at-entry_va
        if not 0<=offset<len(data):raise ValueError('closedLeafEntry.edge-escapes-prefix')
        try:
            decoded=(decode_memory_move(data,offset,entry_va) or decode_byte_register_xor(data,offset,entry_va)
                or decode_memory_register_compare(data,offset,entry_va) or decode_memory_immediate_compare(data,offset,entry_va))
            row,end=decoded if decoded is not None else mapper.decode_one_x64(data,offset,entry_va)
        except (ValueError,IndexError) as error:
            raise ValueError(f'closedLeafEntry.decode: offset={offset} bytes={data[offset:offset+15].hex()} cause={str(error)[:240]}') from error
        raw=bytes.fromhex(row['bytes'])
        if is_unknown_instruction(row) or end<=offset or end>len(data):
            raise ValueError(f'closedLeafEntry.unknown-or-truncated-instruction: offset={offset} text={row["text"]} end={end} prefixBytes={len(data)}')
        if int(row['va'],16)!=at or raw!=data[offset:end]:raise ValueError('closedLeafEntry.decoder-coverage')
        finish=entry_va+end
        for other,old in rows.items():
            if at<other+len(bytes.fromhex(old['bytes'])) and other<finish:
                raise ValueError('closedLeafEntry.overlapping-instructions')
        flow=control_transfer(row);kind=flow['kind'];targets=[]
        if kind in ('next','conditional'):targets.append(finish)
        if kind in ('jump','conditional'):targets.append(flow['target'])
        if kind not in ('next','jump','conditional','return','trap'):
            raise ValueError('closedLeafEntry.not-call-free-or-unreviewed-transfer')
        if any(not entry_va<=target<entry_va+len(data) for target in targets):
            raise ValueError('closedLeafEntry.edge-escapes-prefix')
        rows[at]=row;edges[at]=set(targets);pending.extend(targets)
    if not any(control_transfer(r)['kind'] in ('return','trap') for r in rows.values()):
        raise ValueError('closedLeafEntry.no-terminal')
    return {'rows':[rows[at] for at in sorted(rows)],'edges':edges,
        'closedReachableInstructionGraph':True,'physicalFunctionExtentProved':False,
        'containsCalls':False,'terminationProved':False,'runtimeExecutionKnown':False}

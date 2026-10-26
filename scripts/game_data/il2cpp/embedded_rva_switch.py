"""Partition an owned method extent using its guarded embedded RVA dispatch.

Do not decode the table as instructions. A complete unsigned EAX guard,
CDQE, DWORD indexed load, image-base add and register jump bind its extent.
The older-base variant is conditional on the named base register still
holding image base; the local LEA variant checks that load directly.
"""
from __future__ import annotations
from .integer_addressing import decode_lea_address,decode_register_arithmetic
from .memory_moves import decode_memory_move
from .runtime_data_instructions import decode_runtime_data
from .stack_argument_flow import _edge


def partition_embedded_rva_switch(index,body):
    raw=index.pe.bytes_at_va(body.pointer,body.size);base=index.pe.image_base;found=[];failures=[]
    for offset in range(len(raw)-14):
        if raw[offset:offset+2]!=b'\x83\xf8' or not 0<=raw[offset+2]<32:continue
        maximum=raw[offset+2];at=offset+3
        if raw[at:at+2]!=b'\x0f\x87':continue
        guard_target=body.pointer+at+6+int.from_bytes(raw[at+2:at+6],'little',signed=True);at+=6
        if raw[at:at+2]!=b'\x48\x98':continue
        at+=2;base_load=None
        try:
            lea=decode_lea_address(raw,at,body.pointer)
            if lea is not None and lea[0]['addressOperation'].get('absoluteAddress')==base:
                base_load=lea[0]['addressOperation']['destination'];at=lea[1]
            load=decode_memory_move(raw,at,body.pointer)
            if load is None:continue
            row,end=load;op=row['memoryOperation'];address=op['address']
            if (op['direction'],op['registerBits'],op['memoryBytes'],address['index'],address['scale'])!=('load',32,4,'rax',4):continue
            if address['ripRelative'] or address['base'] is None:continue
            origin=address['base']
            if base_load is not None and origin!=base_load:continue
            destination=op['backingRegister'];table_start=base+address['displacement']-body.pointer
            if table_start<=end or table_start+4*(maximum+1)!=len(raw):continue
            add=decode_register_arithmetic(raw,end,body.pointer)
            if add is None:continue
            fact=add[0]['integerOperation'];end=add[1]
            if (fact['operation'],fact['bits'],fact['destination'],fact['source'])!=('add',64,destination,origin):continue
            jump,stop=index.mapper.decode_one_x64(raw,end,body.pointer)
            if jump['text']!=f'jmp {destination}':continue
            rows=decode_runtime_data(index.mapper,raw[:table_start],body.pointer)
            if any(r['text'].startswith('db ') for r in rows):raise ValueError('unknown code instruction before table')
            if base_load is None and not any(r['offset']<offset and
                    r.get('addressOperation',{}).get('destination')==origin and
                    r.get('addressOperation',{}).get('absoluteAddress')==base for r in rows):
                raise ValueError('older base has no checked preceding image-base LEA')
            boundaries={int(r['va'],16) for r in rows}
            if body.pointer+offset not in boundaries or body.pointer+at not in boundaries or body.pointer+end not in boundaries:
                raise ValueError('dispatch instruction interior')
            if guard_target not in boundaries:raise ValueError('unsigned guard exit is not a code boundary')
            targets=[base+int.from_bytes(raw[i:i+4],'little') for i in range(table_start,len(raw),4)]
            if any(t not in boundaries for t in targets):raise ValueError('table target is not an owned code boundary')
            for r in rows:
                edge=_edge(r)
                if edge and body.pointer<=edge[0]<body.pointer+body.size and edge[0] not in boundaries:
                    raise ValueError('local branch enters data or instruction interior')
            if b''.join(bytes.fromhex(r['bytes']) for r in rows)!=raw[:table_start]:raise ValueError('code-byte coverage')
            found.append({'rows':rows,'codeBytes':table_start,'tableBytes':len(raw)-table_start,
                'tableTargets':targets,'dispatchOffset':offset,'tableIndexMaximum':maximum,
                'tableBaseRegister':origin,'localImageBaseLoad':base_load is not None,
                'evidenceBoundary':'conditional' if base_load is None else 'exact',
                'condition':'Older dispatch base equals selected image base; complete prefix framing and table targets only, not every method operation or live dispatch.' if base_load is None else 'Complete code/table framing and local dispatch; method behavior and live selection are separate.'})
        except (ValueError,KeyError,IndexError) as exc:failures.append(str(exc))
    if len(found)!=1:raise ValueError(f'embedded-rva-switch: expected=one complete guarded tail table actual={len(found)} failures={failures[:3]}')
    return found[0]


def check_embedded_rva_switch(index,body):
    try:partition_embedded_rva_switch(index,body)
    except (ValueError,KeyError,IndexError) as exc:return str(exc)
    return None

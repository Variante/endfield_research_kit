"""A reference result reaches another named call on selected fallthrough.

Only complete contiguous instructions, full register copies and normal Win64
call preservation are used. Conditional branches select fallthrough; other
control transfers and unknown instructions refuse. No live path is selected.
"""
from __future__ import annotations
import re
from .reference_layouts import NativeReferenceContext
from .stack_argument_flow import decode_stack_flow,_edge,GP,VOLATILE


def named_reference_type(index,pointer,symbol,parameter=None):
    context=NativeReferenceContext(index.image,index=index);found=[]
    for row in index.names_by_pointer.get(pointer,()):
        if f"{row.get('type')}.{row.get('method')}"!=symbol:continue
        method=index.metadata.methods[row['methodIndex']]
        types=([method.return_type] if parameter is None else [p.type_index for p in index.metadata.parameters_for(method)
            if index.metadata.string(p.name_index)==parameter])
        for type_index in types:
            record=context.image.pe.bytes_at_va(context.type_pointer(type_index),16)
            if len(record)!=16 or record[10] not in (0x0e,0x12,0x14,0x15,0x1c,0x1d) or record[11]!=0:
                return None
            name=context.type_name(type_index)
            if name.split('<',1)[0] not in index.types or context.is_value_type(name):return None
            found.append(name)
    return found[0] if found and len(set(found))==1 else None


def check_reference_result(index,body,spec):
    from .body_claims import _named_direct_call,_REGISTER_ROOT,_writes_register
    try:
        rows=decode_stack_flow(index.mapper,index.pe.bytes_at_va(body.pointer,body.size),body.pointer)
        for first,source_row in enumerate(rows):
            producer=_named_direct_call(index,source_row,spec['fromCall'])
            if producer is None:continue
            reference=named_reference_type(index,producer,spec['fromCall'])
            if not reference:continue
            aliases={'rax'}
            for row in rows[first+1:]:
                consumer=_named_direct_call(index,row,spec['toCall'])
                if consumer is not None:
                    kind,register=index.parameter_location(consumer,spec['toCall'],spec['toParameter'])
                    if (kind=='register' and register in aliases and
                        named_reference_type(index,consumer,spec['toCall'],spec['toParameter'])==reference):return None
                text=row['text'];edge=_edge(row)
                if edge:
                    if not edge[1]:break
                    continue
                if text.startswith(('db','jmp','ret','int3')):break
                if match:=re.fullmatch(r'mov (\w+), (\w+)',text):
                    destination,source=match.groups();root=_REGISTER_ROOT.get(destination)
                    if root:
                        retain=destination in GP and source in GP and source in aliases
                        aliases.discard(root)
                        if retain:aliases.add(root)
                else:
                    for register in tuple(aliases):
                        if _writes_register(row,register):aliases.discard(register)
                if text.startswith('call '):aliases-=VOLATILE
                if not aliases:break
    except (ValueError,KeyError,IndexError) as exc:return f'reference-result:{exc}'
    return f"reference-result: no selected full reference from {spec['fromCall']} to {spec['toCall']}.{spec['toParameter']}"

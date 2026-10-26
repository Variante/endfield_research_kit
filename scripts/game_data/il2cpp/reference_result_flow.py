"""A reference result reaches another named call on selected fallthrough.

Only complete contiguous instructions, full register copies and normal Win64
call preservation are used. Conditional branches select fallthrough; other
control transfers and unknown instructions refuse. No live path is selected.
"""
from __future__ import annotations
import re
from .protocol import canonical_type_name
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
            name=canonical_type_name(context.type_name(type_index))
            if name.split('<',1)[0] not in index.types or context.is_value_type(name):return None
            found.append(name)
    return found[0] if found and len(set(found))==1 else None


def receiver_field_argument(index,before,producer,spec):
    """Type a shared generic ``T get_x()`` result by its receiver field.

    A shared reference instantiation returns ``T``, so the producer's own
    return type names no reference. With ``receiverField`` the producer must
    be a no-argument instance method of a one-parameter generic class whose
    return type is that class variable, ``rcx`` at the call must be loaded
    from the named field with no call in between, and the field must be
    declared as a closed instantiation of the producer's class. The field's
    sole type argument is then the result's type; nothing else is inferred.
    """
    from .body_claims import _field_load,_writes_register
    owner_type,_,method_name=spec['fromCall'].rpartition('.')
    if not owner_type.endswith('`1'):return None
    context=NativeReferenceContext(index.image,index=index)
    rows=[row for row in index.names_by_pointer.get(producer,())
          if row.get('type')==owner_type and row.get('method')==method_name]
    if not rows:return None
    for row in rows:
        method=index.metadata.methods[row['methodIndex']]
        if list(index.metadata.parameters_for(method)):return None
        raw=context.image.pe.bytes_at_va(context.type_pointer(method.return_type),16)
        if len(raw)!=16 or raw[10]!=0x13 or raw[11]!=0:return None
    _owner,field_type,offset=context.field(spec['receiverField'])
    match=re.fullmatch(re.escape(owner_type)+r'<([^<>,]+)>',field_type)
    if not match:return None
    for row in reversed(before[-8:]):
        text=row['text']
        if text.startswith('call '):return None
        if _writes_register(row,'rcx'):
            if _field_load(text,offset)!='rcx':return None
            argument=canonical_type_name(match.group(1))
            return argument if argument in index.types and not context.is_value_type(argument) else None
    return None


def check_reference_result(index,body,spec):
    from .body_claims import _named_direct_call,_REGISTER_ROOT,_writes_register
    try:
        rows=decode_stack_flow(index.mapper,index.pe.bytes_at_va(body.pointer,body.size),body.pointer)
        for first,source_row in enumerate(rows):
            producer=_named_direct_call(index,source_row,spec['fromCall'])
            if producer is None:continue
            reference=named_reference_type(index,producer,spec['fromCall'])
            if not reference and spec.get('receiverField'):
                reference=receiver_field_argument(index,rows[:first],producer,spec)
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

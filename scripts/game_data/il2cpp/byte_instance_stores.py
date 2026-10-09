"""Prove one owned byte-argument store on a checked normal instance path.

Only nongeneric reference methods with one bool/byte argument and void/bool
return qualify. Complete pointer and low-byte aliases survive a named Boolean
guard; its false JNE fallthrough reaches the named instance field. Unknown
instructions, gaps, partial pointers and wrong widths fail closed.
"""
from __future__ import annotations
import re
from typing import Any
from .reference_layouts import NativeReferenceContext

REGISTERS = ("rax","rcx","rdx","rbx","rsp","rbp","rsi","rdi",*(f"r{n}" for n in range(8,16)))
VOLATILE = {"rax","rcx","rdx","r8","r9","r10","r11"}


def _encoding(row: dict[str,Any]) -> tuple[int, bytes]:
    raw=bytes.fromhex(str(row.get("bytes") or ""))
    if raw and 0x40<=raw[0]<=0x4f:return raw[0],raw[1:]
    return 0,raw


def _low_byte(code: int, rex: int) -> str | None:
    if code<4:return ("al","cl","dl","bl")[code]
    if code<8:return ("spl","bpl","sil","dil")[code-4] if rex else None
    return f"r{code}b"


def check_byte_instance_store(index: Any, body: Any, spec: dict[str,Any]) -> str | None:
    from . import body_claims as claims
    label="byte-instance-store"
    try:
        context=NativeReferenceContext(index.image,index=index)
        owner,_,_=body.symbol.rpartition(".");td=index.types.get(owner)
        declarations=[row for row in index.names_by_pointer.get(body.pointer,[]) if f"{row.get('type')}.{row.get('method')}"==body.symbol]
        if (td is None or context.is_value_type(owner) or td.generic_container_index>=0
                or index.names_of(body.pointer)!=[body.symbol] or len(declarations)!=1):
            return f"{label}: unique nongeneric reference body ownership is missing"
        method=index.metadata.methods[declarations[0]['methodIndex']]
        parameters=list(index.metadata.parameters_for(method))
        result=index.pe.bytes_at_va(context.type_pointer(method.return_type),16)
        field_owner,field_type,field_offset=context.field(spec['field'])
        if (method.flags&0x10 or method.generic_container_index>=0 or method.declaring_type!=td.index
                or len(parameters)!=1 or index.metadata.string(parameters[0].name_index)!=spec['parameter']
                or field_owner!=owner or field_type not in {'bool','byte'}
                or context.type_name(parameters[0].type_index)!=field_type
                or len(result)!=16 or result[10] not in {1,2} or result[11]&0x7f
                or index.parameter_location(body.pointer,body.symbol,'this')!=('register','rcx')
                or index.parameter_location(body.pointer,body.symbol,spec['parameter'])!=('register','rdx')):
            return f"{label}: selected instance/field/parameter ABI is not established"
        argument=index.pe.bytes_at_va(context.type_pointer(parameters[0].type_index),16)
        if len(argument)!=16 or argument[10] not in {2,5} or argument[11]&0x7f:
            return f"{label}: complete undecorated bool/byte argument is missing"
    except (ValueError,KeyError,IndexError,claims.ClaimError) as exc:
        return f"{label}: selected declaration proof failed: {exc}"

    def address(row: dict[str,Any]) -> int:return int(row['va'],16)
    def adjacent(a: dict[str,Any],b: dict[str,Any]) -> bool:
        return address(a)+len(bytes.fromhex(a['bytes']))==address(b)
    refs={'rcx':'this'};values={'rdx'};at=0;guard_target=None;normal_start=None
    while at<len(body.rows):
        row=body.rows[at];text=str(row.get('text') or '');rex,raw=_encoding(row)
        if ((at==0 and address(row)!=body.pointer) or (at and not adjacent(body.rows[at-1],row))
                or not raw or text.startswith('db')):
            return f"{label}: unknown instruction or noncontiguous normal prefix"
        call=re.fullmatch(r'call 0x([0-9a-f]+)',text)
        if call:
            pointer=int(call[1],16)
            if (guard_target is not None or len(raw)!=5 or raw[0]!=0xe8
                    or address(row)+5+int.from_bytes(raw[1:],'little',signed=True)!=pointer
                    or spec['guard'] not in index.names_of(pointer)):
                return f"{label}: unexpected normal-prefix call"
            named=[r for r in index.names_by_pointer.get(pointer,[]) if f"{r.get('type')}.{r.get('method')}"==spec['guard']]
            if len(named)!=1:return f"{label}: unique Boolean guard declaration is missing"
            guard=index.metadata.methods[named[0]['methodIndex']]
            result=index.pe.bytes_at_va(context.type_pointer(guard.return_type),16)
            if len(result)!=16 or result[10]!=2 or result[11]&0x7f:
                return f"{label}: selected guard does not return a direct Boolean"
            tail=body.rows[at+1:at+3]
            if len(tail)!=2 or not adjacent(row,tail[0]) or not adjacent(tail[0],tail[1]):
                return f"{label}: guard test/branch is not contiguous"
            branch=bytes.fromhex(tail[1]['bytes'])
            if (tail[0].get('text')!='test al, al' or bytes.fromhex(tail[0]['bytes'])!=b'\x84\xc0'
                    or not (len(branch)==2 and branch[:1]==b'\x75' or len(branch)==6 and branch[:2]==b'\x0f\x85')):
                return f"{label}: false Boolean JNE fallthrough is missing"
            guard_target=address(tail[1])+len(branch)+int.from_bytes(branch[1:] if len(branch)==2 else branch[2:],'little',signed=True)
            normal_start=address(tail[1])+len(branch)
            refs={r:v for r,v in refs.items() if r not in VOLATILE};values-=VOLATILE
            at+=3;continue
        # Complete low-byte memory store. The actual ModRM joins both receiver
        # and byte source; field offsets come from the selected runtime type.
        if raw[0]==0x88 and len(raw)>=3 and not rex&8:
            modrm=raw[1];mode=modrm>>6;source=((modrm>>3)&7)+(8 if rex&4 else 0)
            base=(modrm&7)+(8 if rex&1 else 0);byte=_low_byte(source,rex)
            if ((mode,len(raw)) in {(1,3),(2,6)} and modrm&7!=4 and byte
                    and refs.get(REGISTERS[base])=='this' and REGISTERS[source] in values
                    and int.from_bytes(raw[2:],'little',signed=True)==field_offset
                    and text==f'mov [{REGISTERS[base]}+0x{field_offset:x}], {byte}'
                    and normal_start is not None and guard_target is not None
                    and not normal_start<=guard_target<address(row)+len(bytes.fromhex(row['bytes']))):
                return None
            return f"{label}: byte store lacks owned receiver, complete argument or false-guard selection"
        moved=re.fullmatch(r'mov (\w+), (\w+)',text);established=False
        if moved and len(raw)==2 and raw[0]==0x8a and raw[1]>>6==3 and not rex&8:
            destination=((raw[1]>>3)&7)+(8 if rex&4 else 0);source=(raw[1]&7)+(8 if rex&1 else 0)
            names=(_low_byte(destination,rex),_low_byte(source,rex))
            if names!=moved.groups() or None in names:return f"{label}: incomplete byte copy"
            present=REGISTERS[source] in values;root=REGISTERS[destination]
            refs.pop(root,None);values.discard(root)
            if present:values.add(root)
            established=True
        elif moved and len(raw)==2 and raw[0] in {0x8b,0x89} and raw[1]>>6==3 and rex&8:
            a=((raw[1]>>3)&7)+(8 if rex&4 else 0);b=(raw[1]&7)+(8 if rex&1 else 0)
            destination,source=(a,b) if raw[0]==0x8b else (b,a)
            if (REGISTERS[destination],REGISTERS[source])!=moved.groups():return f"{label}: pointer copy decode disagrees"
            origin=refs.get(REGISTERS[source]);root=REGISTERS[destination]
            refs.pop(root,None);values.discard(root)
            if origin:refs[root]=origin
            established=True
        elif not re.fullmatch(r'(?:mov \[rsp\+0x[0-9a-f]+\], (?:rbx|rsi|rdi|rbp|r1[2-5])|push (?:rbx|rsi|rdi|rbp|r1[2-5])|sub rsp, 0x[0-9a-f]+|xor \w+, \w+|mov \w+, 0x[0-9a-f]+|nop)',text):
            return f"{label}: unsupported normal-prefix instruction: {text}"
        if not established:
            for register in set(refs)|values:
                if claims._writes_register(row,register):refs.pop(register,None);values.discard(register)
        at+=1
    return f"{label}: no owned {spec['parameter']} byte store into {spec['field']} after false {spec['guard']}"

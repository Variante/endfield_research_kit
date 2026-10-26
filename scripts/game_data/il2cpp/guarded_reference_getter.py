"""Prove a typed reference getter on its false guard/false init-argument path.

The complete primary byte profile records the owned cold branch and the skipped
optional helper. Cold-patch behavior and the optional helper's semantics remain
separate. Field and method selectors come from reviewed named claims.
"""
from __future__ import annotations

import hashlib

from .instance_string_field_calls import _at,_raw,_require,_branch,_call,_owner,_type
from .ai_blackboard_selection import _method,_field,_ancestor
from .reference_layouts import NativeReferenceContext

MODE='guarded-instance-reference-getter-false-boolean-argument'


def validate_program(rows,*,field_offset,guard_pointer,owned_cold_entries):
    """Prove all primary instructions and the selected stored-reference return."""
    raw=[_raw(r) for r in rows];by={_at(r):i for i,r in enumerate(rows)}
    _require(bool(rows) and len(by)==len(rows),'reference-getter-body','unique instruction boundaries',len(rows))
    for a,b in zip(rows,rows[1:]):
        _require(_at(a)+len(_raw(a))==_at(b),'reference-getter-contiguity',a,b)
    _require(all(not r['text'].startswith('db ') for r in rows),'reference-getter-decoding',
             'complete supported primary byte program',None)
    cursor=0
    def peek():
        _require(cursor<len(rows),'reference-getter-truncated','complete selected instruction',cursor)
        return rows[cursor]
    def take(expected):
        nonlocal cursor
        row=peek();cursor+=1
        _require(_raw(row)==expected,'reference-getter-instruction',expected.hex(),row)
        return row
    save=_raw(peek())
    _require(len(save)==5 and save[:4]==b'\x48\x89\x5c\x24' and 8<=save[4]<=32 and save[4]%8==0,
             'reference-getter-save','MOV [caller shadow slot],RBX without overlapping return address',peek())
    cursor+=1;take(b'\x57')
    reserve=_raw(peek())
    _require(len(reserve)==4 and reserve[:3]==b'\x48\x83\xec',
             'reference-getter-frame','SUB RSP,sign-extended imm8',rows[cursor])
    size=int.from_bytes(reserve[3:],'little',signed=True)
    _require(32<=size<128 and size%16==0 and size+8+save[4]<128,
             'reference-getter-frame-size','aligned shadow frame with positive disp8 restore',size)
    cursor+=1;take(b'\x0f\xb6\xfa');take(b'\x48\x8b\xd9');take(b'\x33\xd2')
    guard_id=_raw(peek())
    _require(len(guard_id)==5 and guard_id[0]==0xb9,'reference-getter-guard-argument',
             'MOV ECX,imm32',rows[cursor]);cursor+=1
    guard=peek();cursor+=1
    _require(_call(guard)==guard_pointer,'reference-getter-guard-call','selected named patch guard',guard)
    take(b'\x84\xc0');cold=_branch(peek(),opcode=b'\x0f\x85');cursor+=1
    _require(cold in owned_cold_entries,'reference-getter-cold-owner','exact owned cold entry',hex(cold))
    take(b'\x40\x84\xff');branch=peek();cursor+=1
    getter=_branch(branch,opcode=b'\x74')
    optional_arg=_raw(peek())
    _require(len(optional_arg)==5 and optional_arg[0]==0xb9,'reference-getter-optional-argument',
             'bounded skipped MOV ECX,imm32',rows[cursor]);cursor+=1
    take(b'\x48\x8b\xd3');optional_call=peek();cursor+=1;optional_target=_call(optional_call)
    _require(getter in by and getter==_at(peek()),'reference-getter-false-input-edge',
             'false DIL jumps over all optional initialization instructions',hex(getter))
    _require(type(field_offset) is int and 0<field_offset<=0x7fffffff,
             'reference-getter-offset','declared positive instance offset',field_offset)
    take(b'\x48\x8b\x83'+field_offset.to_bytes(4,'little'))
    take(b'\x48\x8b\x5c\x24'+bytes([size+8+save[4]]));take(b'\x48\x83\xc4'+bytes([size]))
    take(b'\x5f');ret=take(b'\xc3')
    _require(cursor==len(rows),'reference-getter-terminal','primary ends at matched plain RET',cursor)
    return {'patchCheckVa':_at(guard),'patchResultCondition':False,'booleanArgumentCondition':False,
        'booleanInputRepresentation':'low byte of incoming RDX, zero extended into EDI',
        'storedReferenceReadVa':getter,'fieldOffset':field_offset,'returnVa':_at(ret),
        'returnSource':'current field reference read after false patch guard',
        'thisAlias':'rbx','coldEntryVa':cold,'coldPatchBehaviorProved':False,
        'optionalHelper':{'callVa':_at(optional_call),'targetVa':optional_target,
            'skippedOnSelectedFalseArgumentPath':True,'behaviorProved':False},
        'completeSelectedGetterProgramProved':True,'runtimeExecutionKnown':False,
        'guardEffectProved':False,'fieldInitialValuePreservedByGuardProved':False}


def prove(index,claim):
    _require(claim.get('mode')==MODE,'reference-getter-mode',MODE,claim.get('mode'))
    image=index.image;method=_method(image,{'type':claim['type'],'method':claim['method'],'image':claim['image']})
    params=list(image.metadata.parameters_for(method))
    _require(not method.flags&0x10 and method.generic_container_index<0
             and _type(image,method.return_type)==(0x12,claim['fieldType'],False)
             and len(params)==1 and _type(image,params[0].type_index)==(2,'bool',False)
             and image.metadata.string(params[0].name_index)==claim['argument'],
             'reference-getter-signature','instance nongeneric class return and named Boolean argument',method.index)
    guard=_method(image,claim['guard']);gp=list(image.metadata.parameters_for(guard))
    _require(guard.flags&0x10 and guard.generic_container_index<0
             and _type(image,guard.return_type)==(2,'bool',False)
             and [_type(image,p.type_index) for p in gp]==[(8,'int',False)],
             'reference-getter-guard-signature','nongeneric static Boolean guard with Int32 input',guard.index)
    context=NativeReferenceContext(image,index=index)
    _owner(image,claim['fieldType']);_ancestor(context,claim['type'],claim['field'].partition('::')[0])
    offset=_field(context,claim['field'],claim['fieldType'])
    ptr=image.method_pointer_va(method)
    _require(ptr in index.extents,'reference-getter-unwind','exact primary PE-owned entry',hex(ptr))
    size=index.extents[ptr]-ptr
    _require(0<size<=4096,'reference-getter-primary-size','bounded primary body',size)
    rows=index._decode(ptr,size)
    _require(sum(len(_raw(r)) for r in rows)==size,'reference-getter-byte-coverage',size,len(rows))
    fragments=index.chained_fragments.get(ptr,[])
    result=validate_program(rows,field_offset=offset,guard_pointer=image.method_pointer_va(guard),
        owned_cold_entries={start for start,extent in fragments if extent>0})
    result.update(method=[method.index,claim['type'],claim['method'],ptr-image.pe.image_base],
        field=claim['field'],declaredReturnType=claim['fieldType'],
        primaryCodeWindow={'startRva':ptr-image.pe.image_base,'endRva':ptr+size-image.pe.image_base,
            'sha256':hashlib.sha256(image.pe.bytes_at_va(ptr,size)).hexdigest().upper()},
        ownedColdWindows=[{'startRva':start-image.pe.image_base,'length':extent,
            'sha256':hashlib.sha256(image.pe.bytes_at_va(start,extent)).hexdigest().upper(),
            'behaviorProved':False} for start,extent in fragments],
        evidenceBoundary='conditional',
        condition='coherent receiver/frame, zero incoming Boolean byte, false guard result, ordinary returning Win64 guard and valid field/restore reads')
    return result

"""Explicit unmanaged DWORD source with a complete cursor-call program.

Addresses, window digests and instruction witnesses belong to the reviewed
declaration. The buffered normal paths below prove raw stored bits, not refill
outcomes, provider selection, runtime reader coherence or setter execution.
"""
from __future__ import annotations

import struct
from typing import Any, Callable
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import struct_output_sources as structs


def check_dword_cursor_source(image: Any, source: dict, member: dict, proof: dict,
                              context: dict, offsets: list[int], entry: dict, *,
                              record: str, label: str, fail: Callable) -> None:
    """Check complete direct and registered bodies independently, then cursor.

    The caller must already have checked type size, its typed source context,
    exact closed registration and the actual direct source-call destination.
    This mode additionally proves the generic return signature and freshly
    derives reader field slots before using any recorded displacements.
    """
    def error(check: str, expected: Any, actual: Any) -> None:
        fail(check,expected,actual,record=record,field=member['fieldName'])

    if not isinstance(proof,dict) or proof.get('mode')!='dword-with-cursor-call' or proof.get('width')!=4:
        error('unmanaged-cursor-mode','explicit four-byte cursor-call mode',proof)
    selected=NativeReferenceContext(image)
    method=image.metadata.methods[context['methodSpec'][0]]
    identity=[method.index,image.type_name(method.declaring_type),image.metadata.string(method.name_index)]
    section=image.metadata.sections['genericContainers']
    at=section.offset+method.generic_container_index*16
    if method.generic_container_index<0 or not section.offset<=at<=section.offset+section.size-16:
        error('unmanaged-cursor-generic-container','bounded method container',method.generic_container_index)
    container=struct.unpack_from('<iiii',image.metadata.buf,at)
    pointer=image.pe.u64_at_va(int(image.registration['types'],16)+method.return_type*8)
    returned=image.pe.bytes_at_va(pointer,16)
    if (identity!=proof.get('sourceDefinition') or identity[1:]!=['MemoryPack.MemoryPackReader','ReadUnmanaged']
            or method.flags&0x10 or method.parameter_count!=0 or container[:3]!=(method.index,1,1)
            or len(returned)!=16 or returned[10:12]!=b'\x1e\0' or int.from_bytes(returned[:8],'little')!=container[3]):
        error('unmanaged-cursor-signature','instance ReadUnmanaged<T>() returns its sole undecorated MVAR',identity)
    if not selected.is_value_type(identity[1]):
        error('unmanaged-cursor-reader-type','value-type reader receiver',identity[1])
    fields=runtime_type_field_offsets(image.metadata,image.pe,image.registration,method.declaring_type)
    names=('currentPtr','bufferLength','advancedCount','consumed')
    if any(type(fields.get(n)) is not int or fields[n]<16 for n in names):
        error('unmanaged-cursor-reader-fields','four boxed reader fields',fields)
    actual=[fields[n]-16 for n in names]
    if actual!=offsets:
        error('unmanaged-cursor-reader-offsets',actual,offsets)
    buffer,remaining,advanced,consumed=offsets

    def full(window: Any, rows: Any, expected: list[bytes], part: str) -> None:
        if (not isinstance(window,dict) or any(type(window.get(k)) is not int for k in ('startRva','endRva'))
                or window['startRva']>=window['endRva']):
            error('unmanaged-cursor-window','bounded full program',window)
        structs._program(image,window,rows,expected,label=label+'.'+part,fail=error)
        if rows[0][0]!=window['startRva'] or rows[-1][0]+len(expected[-1])!=window['endRva']:
            error('unmanaged-cursor-program-extent',window,[rows[0],rows[-1]])

    def rows_of(value: Any,count: int) -> list:
        if (not isinstance(value,list) or len(value)!=count or
                any(not isinstance(r,list) or len(r)!=2 or type(r[0]) is not int or not isinstance(r[1],str) for r in value)):
            error('unmanaged-cursor-program-shape',count,value)
        return value

    def branch(rows: list,index: int,prefix: bytes,width: int,window: dict,*,target: int|None=None) -> bytes:
        try:raw=bytes.fromhex(rows[index][1])
        except ValueError:error('unmanaged-cursor-branch','hex branch',rows[index])
        if len(raw)!=len(prefix)+width or not raw.startswith(prefix):
            error('unmanaged-cursor-branch',prefix.hex().upper()+' relative branch',rows[index])
        reached=rows[index][0]+len(raw)+int.from_bytes(raw[-width:],'little',signed=True)
        if target is not None:
            if reached!=target:error('unmanaged-cursor-branch-target',target,reached)
        elif window['startRva']<=reached<window['endRva']:
            error('unmanaged-cursor-cold-branch','cold target outside selected normal program',reached)
        return raw

    def call(value: Any,rows: list,index: int,window: dict,*,target: int|None=None) -> bytes:
        if (not isinstance(value,dict) or any(type(value.get(k)) is not int for k in ('rva','targetRva'))
                or value['rva']!=rows[index][0] or not window['startRva']<=value['rva']<=window['endRva']-5
                or target is not None and value['targetRva']!=target):
            error('unmanaged-cursor-call','actual bounded instruction and target',value)
        named.check_call(image,value,label=label,fail=error)
        return image.pe.bytes_at_va(image.pe.image_base+value['rva'],5)

    window=next(w for w in source['codeWindows'] if w['startRva']==proof['windowStartRva'])
    advance=proof.get('advanceWindow') or {}
    registered=proof.get('registeredReader') or {}
    if not isinstance(registered,dict):
        error('unmanaged-cursor-registered-proof','registered reader object',registered)
    rw=registered.get('window') or {}
    # Fail closed before malformed declarations can become unchecked lookups.
    for w in (window,advance,rw):
        if (not isinstance(w,dict) or any(type(w.get(k)) is not int for k in ('startRva','endRva'))
                or w['startRva']>=w['endRva']):
            error('unmanaged-cursor-window','bounded source, registered and cursor programs',w)
    if entry['pointer']!=image.pe.image_base+rw['startRva']:
        error('unmanaged-cursor-registration','exact closed registered body',entry)
    image.check_windows([window,rw,advance],label=label)
    direct=rows_of(proof.get('instructions'),16)
    rr=rows_of(registered.get('completeInstructions'),19)
    ar=rows_of(proof.get('advanceInstructions'),20)
    source_call=call(proof.get('advanceCall'),direct,10,window,target=advance['startRva'])
    registered_call=call(registered.get('advanceCall'),rr,13,rw,target=advance['startRva'])
    ensure=call(registered.get('ensureCall'),rr,8,rw)
    anchors=('startRva','endRva','sha256')
    rw_advance=registered.get('advanceWindow')
    if not isinstance(rw_advance,dict) or any(rw_advance.get(k)!=advance.get(k) for k in anchors):
        error('unmanaged-cursor-shared-helper',advance,rw_advance)
    head=[b'\x48\x89\x5c\x24\x08',b'\x57',b'\x48\x83\xec\x20',
          b'\x83\x79'+bytes((remaining,4)),b'\x48\x8b\xf9']
    body=[b'\x48\x8b\x5f'+bytes((buffer,)),b'\xba\x04\x00\x00\x00',b'\x48\x8b\xcf',b'\x8b\x1b']
    tail=[b'\x8b\xc3',b'\x48\x8b\x5c\x24\x30',b'\x48\x83\xc4\x20',b'\x5f',b'\xc3']
    full(window,direct,head+[branch(direct,5,b'\x0f\x8c',4,window)]+body+[source_call]+tail,'source')
    full(rw,rr,head+[branch(rr,5,b'\x7d',1,rw,target=rr[9][0]),
        b'\x45\x33\xc0',b'\xba\x04\x00\x00\x00',ensure]+body+[registered_call]+tail,'registered')
    full(advance,ar,[b'\x85\xd2',branch(ar,1,b'\x74',1,advance,target=ar[-1][0]),
        b'\x48\x89\x5c\x24\x10',b'\x57',b'\x48\x83\xec\x20',b'\x48\x63\xfa',
        b'\x48\x8b\xd9',b'\x48\x89\x74\x24\x30',b'\x8b\x71'+bytes((remaining,)),b'\x2b\xf7',
        branch(ar,10,b'\x0f\x88',4,advance),b'\x48\x01\x7b'+bytes((buffer,)),
        b'\x01\x7b'+bytes((advanced,)),b'\x01\x7b'+bytes((consumed,)),b'\x89\x73'+bytes((remaining,)),
        b'\x48\x8b\x74\x24\x30',b'\x48\x8b\x5c\x24\x38',b'\x48\x83\xc4\x20',b'\x5f',b'\xc3'],'advance')


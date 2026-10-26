"""Buffered inline signed-length reads feeding a separately proved UTF8 helper.

This profile proves the original reader pointer, four-byte length/cursor
program, bounds guard and all null/empty/positive result branches. It stops
at the common result join; generic runtime Data layout and subsequent stores
are deliberately outside its claim.
"""
from __future__ import annotations

from typing import Any, Callable
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import reference_output_sources as references
from scripts.game_data.memorypack import struct_output_sources as structs

LABEL = 'inlineUtf8Source'
MODE = 'buffered-reader-rdi-signed-length-rbx-utf8-result'


def _target(row: list) -> int:
    raw=bytes.fromhex(row[1]);start=2 if raw[:1]==b'\x0f' else 1
    return row[0]+len(raw)+int.from_bytes(raw[start:],'little',signed=True)


def _selected(image: Any, window: dict, rows: list, expected: list[bytes], branches: dict,
              end: int, fail: Callable) -> None:
    if not isinstance(rows,list) or len(rows)!=len(expected):
        fail('inline-utf8-selected-size',len(expected),rows)
    for ordinal,(row,wanted) in enumerate(zip(rows,expected,strict=True)):
        if (not isinstance(row,list) or len(row)!=2 or type(row[0]) is not int
                or row[1]!=wanted.hex().upper()
                or not window['startRva']<=row[0]<row[0]+len(wanted)<=window['endRva']):
            fail('inline-utf8-selected-instruction',[ordinal,wanted.hex().upper()],row)
        following=rows[ordinal+1][0] if ordinal+1<len(rows) else end
        if ordinal in branches:
            prefix,taken=branches[ordinal]
            op=bytes.fromhex(prefix)
            if len(wanted)!=len(op)+(1 if len(op)==1 else 4) or not wanted.startswith(op):
                fail('inline-utf8-selected-branch',prefix,row)
            success=_target(row) if taken else row[0]+len(wanted)
        else:
            success=row[0]+len(wanted)
        if following!=success:
            fail('inline-utf8-selected-edge',success,following)
    image.check_instruction_windows(rows,label=LABEL)


def validate_inline_utf8_source(image: Any, source: dict, record: dict, *,
                                utf8_method: list, empty_literal_cell: int,
                                fail: Callable) -> dict:
    proof=record['inlineStringSource']
    if proof.get('mode')!=MODE:
        fail('inline-utf8-mode',MODE,proof.get('mode'))
    normal=next(w for w in source['codeWindows'] if w['startRva']==record['readerMethod'][3])
    structs.check_reader_ref_wrapper_abi(image,record,fail=fail)
    prefix=proof['aliasPrefix'];references._program(image,normal,prefix,fail)
    if prefix[0][0]!=normal['startRva'] or prefix[-1][0]+len(bytes.fromhex(prefix[-1][1]))!=proof['lengthProgram'][0][0]:
        fail('inline-utf8-alias-extent','entry through inline length source',prefix)
    aliases={'rdi':'488BF9','rsi':'488BF2'};seen=set()
    for at,h in prefix:
        raw=bytes.fromhex(h);decoded=image.mapper.decode_x64_subset(raw,image.pe.image_base+at,stop_offset=len(raw))
        if len(decoded)!=1 or decoded[0]['text'].startswith('db'):
            fail('inline-utf8-alias-instruction','one understood instruction',[at,h])
        register=(decoded[0].get('write') or {}).get('register')
        if register in {'rdi','edi','di','dil','rsi','esi','si','sil'}:
            if register not in aliases or register in seen or h!=aliases[register]:
                fail('inline-utf8-pointer-clobber',aliases,[at,h,register])
            seen.add(register)
        if raw[:1]==b'\xe8' and seen!=set(aliases):
            fail('inline-utf8-late-alias',sorted(aliases),sorted(seen))
    if seen!=set(aliases):fail('inline-utf8-missing-alias',sorted(aliases),sorted(seen))
    selected=NativeReferenceContext(image);definition=proof['readerTypeDefinition']
    if image.type_name(definition)!='MemoryPack.MemoryPackReader' or not selected.is_value_type(image.type_name(definition)):
        fail('inline-utf8-reader-type','MemoryPackReader value type',definition)
    fields=runtime_type_field_offsets(image.metadata,image.pe,image.registration,definition)
    names=('currentPtr','bufferLength','advancedCount','consumed','totalLength')
    if fields!=proof['readerFieldOffsets'] or any(type(fields.get(n)) is not int or not 16<=fields[n]<144 for n in names):
        fail('inline-utf8-reader-layout',proof['readerFieldOffsets'],fields)
    pointer,remaining,advanced,consumed,total=[fields[n]-16 for n in names]
    if len({pointer,remaining,advanced,consumed,total})!=5:
        fail('inline-utf8-reader-slot-overlap','five distinct fields',fields)
    length=proof['lengthProgram'];actual=[bytes.fromhex(row[1]) for row in length]
    if len(actual)!=11:fail('inline-utf8-length-size',11,length)
    expected=[b'\x83\x7f'+bytes((remaining,4)),actual[1],b'\x48\x8b\x47'+bytes((pointer,)),
        b'\x48\x63\x18',b'\x8b\x6f'+bytes((remaining,)),b'\x83\xed\x04',actual[6],
        b'\x48\x83\x47'+bytes((pointer,4)),b'\x83\x47'+bytes((advanced,4)),
        b'\x83\x47'+bytes((consumed,4)),b'\x89\x6f'+bytes((remaining,))]
    bounds=proof['boundsProgram'];_selected(image,normal,length,expected,{1:('7D',True),6:('79',True)},bounds[0][0],fail)
    if len(bounds)!=5:fail('inline-utf8-bounds-size',5,bounds)
    wanted=[b'\x48\x63\x47'+bytes((consumed,)),b'\x48\x8b\x4f'+bytes((total,)),
            b'\x48\x2b\xc8',b'\x48\x3b\xcb',bytes.fromhex(bounds[4][1])]
    paths=proof['resultPrograms'];join=proof['resultJoinRva']
    if set(paths)!={'null','empty','positive'}:fail('inline-utf8-result-scope','all three distinct branches',paths)
    _selected(image,normal,bounds,wanted,{4:('0F8C',False)},paths['null'][0][0],fail)
    if normal['startRva']<=_target(bounds[4])<normal['endRva']:
        fail('inline-utf8-bounds-failure','unproved cold failure outside normal window',_target(bounds[4]))
    for mode,rows in paths.items():
        actual=[bytes.fromhex(row[1]) for row in rows]
        count={'null':5,'empty':8,'positive':12}[mode]
        if len(actual)!=count:fail('inline-utf8-result-size',[mode,count],rows)
        common=[b'\x83\xfb\xff',b'\x0f\x95\xc0',b'\x84\xc0',actual[3]]
        branches={3:('74',mode=='null')}
        if mode=='null':expected=common+[b'\x33\xdb']
        elif mode=='empty':
            expected=common+[b'\x85\xdb',actual[5],actual[6],actual[7]]
            branches.update({5:('74',True),7:('EB',True)})
            raw=actual[6]
            if len(raw)!=7 or raw[:3]!=b'\x48\x8b\x1d' or rows[6][0]+7+int.from_bytes(raw[3:],'little',signed=True)!=empty_literal_cell:
                fail('inline-utf8-empty-cell','same independently validated empty string literal cell',rows[6])
        else:
            expected=common+[b'\x85\xdb',actual[5],b'\x45\x33\xc0',b'\x8b\xd3',b'\x48\x8b\xcf',
                             actual[9],b'\x48\x8b\xd8',actual[11]]
            branches.update({5:('74',False),11:('EB',True)})
            call=proof['utf8Call'];named.check_call(image,call,label=LABEL,fail=fail)
            if rows[9][0]!=call['rva'] or call['targetRva']!=utf8_method[3]:
                fail('inline-utf8-callee','actual independently validated ReadUtf8 method',call)
        if rows[0][0]!=bounds[-1][0]+len(bytes.fromhex(bounds[-1][1])):
            fail('inline-utf8-result-entry','all branches start immediately after bound check',rows[0])
        _selected(image,normal,rows,expected,branches,join,fail)
    return {'lengthSourceBytes':4,'resultRegister':'rbx','sameReaderForwarded':True,
        'nullEmptyPositiveProgramsProved':True,'readUtf8MethodIdentityProved':True,
        'evidenceBoundary':'conditional','condition':'buffered normal path, initialized metadata/literal and ordinary Win64 returning calls',
        'genericDataDestinationLayoutProved':False,'failureOrRefillParityKnown':False,
        'invalidUtf8ReplacementParityKnown':False,'runtimeExecutionKnown':False}

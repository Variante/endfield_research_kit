"""Prove selected generated primitive Param owned stores and pooled paths.

This is a selected-image component proof, not an enclosing owner admission.
Generic heap layout and live formatter/holder selection remain conditional.

Evidence and admission boundary:

Conditional scalar components each prove actual source, complete typed owned
store/allocation and pooled path before any null shortcut. Boolean
normalizes the source byte, Int32/UInt32 preserve their signed/unsigned
bits, Single preserves precision/signed zero, and UInt64 proves its own
inline counter program. Spline uses its own saved-reader/factory/null-guard
profile; tag and volume wrappers have independent DWORD/QWORD sources.
Ordinary allocation type records exclude byref/pinned/modifier/value
markers. Enum/Byte shortcuts are not admitted by scalar width. Generic heap
layout, live provider and enclosing EOF are separate.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.il2cpp.protocol import native_enum_members

from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack import pooled_source_helper, scalar_param_native as scalar
from scripts.game_data.memorypack.wrapper_members import derive_from_image

LABEL='memorypackPrimitiveParam'


def reader_abi(image,ctx,method,wrapper):
    parameters=list(image.metadata.parameters_for(method))
    scalar.need(LABEL,'readerStaticArity',(16,2,2),(method.flags&16,method.parameter_count,len(parameters)))
    scalar.ordinary(image,ctx.type_pointer(method.return_type),1,LABEL+'.readerReturn')
    for p,expected,kind in zip(parameters,('MemoryPack.MemoryPackReader',wrapper.name),(17,18)):
        raw=image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16)
        scalar.need(LABEL,'byrefReaderArgument',(expected,kind,32),(ctx.type_name(p.type_index),raw[10],raw[11]))
        scalar.need(LABEL,'byrefDefinition',ctx.index.types[expected].index,int.from_bytes(raw[:8],'little'))


def inline_program(image,record,slots,offsets,*,width=1,reference=False,floating=False,vector3=False):
    """Prove every hot read/store, saved alias, null/count edge and frame exit."""
    cur,rem,adv,used=(offsets[n] for n in ('currentPtr','bufferLength','advancedCount','consumed'))
    slot=lambda name:bytes((slots[name],))
    rows=record['instructions']
    scalar.need(LABEL,'supportedConstWidth',True,(vector3 and width==12 and not reference and not floating) or (not vector3 and
        ((reference and width==8 and not floating) or (not reference and width in (1,4) and (not floating or width==4)))))
    expected=[b'\x48\x89\x5c\x24\x08',b'\x48\x89\x6c\x24\x10',b'\x48\x89\x74\x24\x18',b'\x57',b'\x48\x83\xec\x20',None,
        b'\x48\x8b\xfa',b'\x48\x8b\xd9',None,b'\x83\x7b'+bytes((rem,1)),None,b'\x48\x8b\x43'+bytes((cur,)),b'\x0f\xb6\x30',
        b'\x8b\x6b'+bytes((rem,)),b'\x83\xed\x01',None,b'\x48\xff\x43'+bytes((cur,)),b'\xff\x43'+bytes((adv,)),b'\xff\x43'+bytes((used,)),
        b'\x89\x6b'+bytes((rem,)),b'\x40\x80\xfe\xff',None,b'\x48\x83\x3f\x00',None,b'\x40\x80\xfe\x04',None,
        b'\x48\x8b\x37',b'\x48\x8b\xcb',None,b'\x48\x85\xf6',None,b'\x48\x8b\x4e\x10',b'\x48\x85\xc9',None,(b'\x88\x41' if width==1 else b'\x89\x41')+slot('constValue'),
        b'\x48\x8b\xcb',b'\x48\x8b\x37',None,b'\x48\x85\xf6',None,b'\x48\x8b\x4e\x10',b'\x48\x85\xc9',None,b'\x89\x41'+slot('idRef'),
        b'\x48\x8b\xcb',b'\x48\x8b\x37',None,b'\x48\x85\xf6',None,b'\x48\x8b\x4e\x10',b'\x48\x85\xc9',None,b'\x89\x41'+slot('paramSource'),
        b'\x48\x8b\xcb',b'\x48\x8b\x3f',None,b'\x48\x85\xff',None,b'\x48\x8b\x4f\x10',b'\x48\x85\xc9',None,b'\x48\x89\x41'+slot('path'),
        b'\x48\x83\xc1'+slot('path'),b'\x48\x8b\x5c\x24\x30',b'\x48\x8b\x6c\x24\x38',b'\x48\x8b\x74\x24\x40',b'\x48\x83\xc4\x20',b'\x5f',None,
        b'\x48\xc7\x07\x00\x00\x00\x00',b'\x48\x8b\xcf',None,None,b'\xcc',None,None,None,None,None,None,None,None]
    # The reference profile stores/barriers RAX before scheduling the Int32
    # read; the scalar profile stores AL/EAX and has no first barrier.
    if reference:
        expected[34:37]=[b'\x48\x89\x41'+slot('constValue'),b'\x48\x83\xc1'+slot('constValue'),None,b'\x48\x8b\x37',b'\x48\x8b\xcb']
    if floating:
        expected[31:33]=[b'\x48\x8b\x46\x10',b'\x48\x85\xc0']
        expected[34:37]=[b'\x48\x8b\x37',b'\x48\x8b\xcb',b'\xf3\x0f\x11\x40'+slot('constValue')]
    if vector3:
        expected[4]=b'\x48\x83\xec\x30'
        expected[63:67]=[b'\x48\x8b\x5c\x24\x40',b'\x48\x8b\x6c\x24\x48',b'\x48\x8b\x74\x24\x50',b'\x48\x83\xc4\x30']
        expected[80:80]=[None,None]
        expected[34:35]=[b'\xf2\x0f\x10\x44\x24\x20',b'\x8b\x44\x24\x28',b'\xf2\x0f\x11\x41'+slot('constValue'),b'\x89\x41'+bytes((slots['constValue']+8,))]
        expected[26:29]=[None,b'\x48\x8d\x4c\x24\x20',b'\x48\x8b\x37',b'\x48\x8b\xd3',None]
    at=lambda n:n+(2 if reference and n>=37 else 0)+(2*(n>=26)+3*(n>=35)+2*(n>=80) if vector3 else 0)
    scalar.program_extent(rows,record['window'],LABEL);scalar.program(image,rows,expected,LABEL)
    def branch(at,opcode,destination=None):
        rva,encoded=rows[at];raw=bytes.fromhex(encoded)
        scalar.need(LABEL,'branchShape',(len(opcode)+(1 if len(opcode)==1 and opcode!=b'\xe9' else 4),opcode),(len(raw),raw[:len(opcode)]))
        target=rva+len(raw)+int.from_bytes(raw[len(opcode):],'little',signed=True)
        if destination is None:scalar.need(LABEL,'coldGuardOutsidePrimary',False,record['window']['startRva']<=target<record['window']['endRva'])
        else:scalar.need(LABEL,'branchTarget',rows[destination][0],target)
    for n,opcode,dest in ((8,b'\x0f\x84',74),(10,b'\x0f\x8c',None),(15,b'\x0f\x88',None),(21,b'\x0f\x84',69),
            (23,b'\x0f\x84',None),(25,b'\x0f\x85',None),(30,b'\x0f\x84',72),(33,b'\x0f\x84',72),
            *[(at,b'\x74',72) for at in (39,42,48,51,57,60)],(71,b'\xeb',63),(81,b'\xe9',9)):
        branch(at(n),opcode,at(dest) if dest is not None else None)
    for n in (28,37,46,55,72,75,77,79,*((36,) if reference else ())):
        raw=bytes.fromhex(rows[36 if reference and n==36 else at(n)][1]);scalar.need(LABEL,'callShape',(5,0xe8),(len(raw),raw[0]))
    for n in (74,76,78):
        raw=bytes.fromhex(rows[at(n)][1]);scalar.need(LABEL,'initializerLoadShape',(7,b'\x48\x8d\x0d'),(len(raw),raw[:3]))
    if vector3:
        raw=bytes.fromhex(rows[85][1]);scalar.need(LABEL,'vectorInitializerLoad',(7,b'\x48\x8d\x0d'),(len(raw),raw[:3]))
        raw=bytes.fromhex(rows[86][1]);scalar.need(LABEL,'vectorInitializerCall',(5,b'\xe8'),(len(raw),raw[:1]))
        rva,encoded=rows[26];raw=bytes.fromhex(encoded);initial=bytes.fromhex(rows[83][1])
        scalar.need(LABEL,'vectorMethodInfoLoad',(7,b'\x4c\x8b\x05'),(len(raw),raw[:3]))
        scalar.need(LABEL,'sameVectorInitializedCell',rva+7+int.from_bytes(raw[3:],'little',signed=True),rows[83][0]+7+int.from_bytes(initial[3:],'little',signed=True))
    flag,store=(bytes.fromhex(rows[at(n)][1]) for n in (5,80))
    scalar.need(LABEL,'initFlagShapes',(b'\x80\x3d',0,b'\xc6\x05',1),(flag[:2],flag[-1],store[:2],store[-1]))
    scalar.need(LABEL,'initFlagWidths',(7,7),(len(flag),len(store)))
    scalar.need(LABEL,'sharedInitFlag',rows[5][0]+7+int.from_bytes(flag[2:6],'little',signed=True),rows[at(80)][0]+7+int.from_bytes(store[2:6],'little',signed=True))
    tail=bytes.fromhex(rows[at(68)][1]);scalar.need(LABEL,'barrierTailShape',(5,0xe9),(len(tail),tail[0]))
    targets={name:rows[at(n)][0]+5+int.from_bytes(bytes.fromhex(rows[at(n)][1])[1:],'little',signed=True)
            for name,n in (('constValue',28),('idRef',37),('paramSource',46),('path',55),('barrier',68))}
    if reference:
        call=rows[36];scalar.need(LABEL,'sameConstantBarrier',targets['barrier'],call[0]+5+int.from_bytes(bytes.fromhex(call[1])[1:],'little',signed=True))
    return targets


def single_source(image,record,offsets):
    """Prove the buffered raw Single read and complete XMM6/frame restore."""
    cur,rem,adv,used=(offsets[n] for n in ('currentPtr','bufferLength','advancedCount','consumed'))
    expected=[b'\x48\x89\x5c\x24\x08',b'\x57',b'\x48\x83\xec\x30',b'\x83\x79'+bytes((rem,4)),b'\x48\x8b\xd9',b'\x0f\x29\x74\x24\x20',None,
        b'\x48\x8b\x43'+bytes((cur,)),b'\xf3\x0f\x10\x30',b'\x8b\x7b'+bytes((rem,)),b'\x83\xc7\xfc',None,
        b'\x48\x83\x43'+bytes((cur,4)),b'\x83\x43'+bytes((adv,4)),b'\x83\x43'+bytes((used,4)),b'\x89\x7b'+bytes((rem,)),
        b'\x48\x8b\x5c\x24\x40',b'\x0f\x28\xc6',b'\x0f\x28\x74\x24\x20',b'\x48\x83\xc4\x30',b'\x5f',b'\xc3']
    scalar.program_extent(record['instructions'],record['window'],LABEL+'.single');image.check_windows([record['window']],label=LABEL+'.single')
    scalar.program(image,record['instructions'],expected,LABEL+'.single')
    for n,opcode in ((6,b'\x0f\x8c'),(11,b'\x0f\x88')):
        rva,encoded=record['instructions'][n];raw=bytes.fromhex(encoded)
        scalar.need(LABEL,'singleGuard',(6,opcode),(len(raw),raw[:2]))
        target=rva+6+int.from_bytes(raw[2:],'little',signed=True)
        scalar.need(LABEL,'singleColdGuardOutsideBufferedProgram',False,record['window']['startRva']<=target<record['window']['endRva'])


def object_header_source(image,record,offsets):
    """One buffered byte to the out slot; AL is false exactly for 0xff."""
    cur,rem,adv,used=(offsets[n] for n in ('currentPtr','bufferLength','advancedCount','consumed'))
    expected=[b'\x48\x89\x5c\x24\x08',b'\x48\x89\x74\x24\x10',b'\x57',b'\x48\x83\xec\x20',b'\x83\x79'+bytes((rem,1)),
        b'\x48\x8b\xfa',b'\x48\x8b\xd9',None,b'\x48\x8b\x43'+bytes((cur,)),b'\x0f\xb6\x08',b'\x88\x0f',
        b'\x8b\x73'+bytes((rem,)),b'\x83\xee\x01',None,b'\x48\xff\x43'+bytes((cur,)),b'\xff\x43'+bytes((adv,)),b'\xff\x43'+bytes((used,)),
        b'\x89\x73'+bytes((rem,)),b'\x80\x3f\xff',b'\x48\x8b\x5c\x24\x30',b'\x48\x8b\x74\x24\x38',b'\x0f\x95\xc0',b'\x48\x83\xc4\x20',b'\x5f',b'\xc3']
    scalar.program_extent(record['instructions'],record['window'],LABEL+'.header');image.check_windows([record['window']],label=LABEL+'.header')
    scalar.program(image,record['instructions'],expected,LABEL+'.header')
    for n,opcode in ((7,b'\x0f\x8c'),(13,b'\x0f\x88')):
        rva,encoded=record['instructions'][n];raw=bytes.fromhex(encoded)
        scalar.need(LABEL,'headerGuard',(6,opcode),(len(raw),raw[:2]))
        target=rva+6+int.from_bytes(raw[2:],'little',signed=True)
        scalar.need(LABEL,'headerColdGuardOutsideBufferedProgram',False,record['window']['startRva']<=target<record['window']['endRva'])


def setter_call_program(image,record,setters,*,width=4,vector2=False,output=False,typed_enum=False,typed_qword=False,integer_slots=None):
    """The buffered header/typed setter-call profile, including its null edge."""
    rows=record['instructions'];expected=[b'\x48\x89\x5c\x24\x18',b'\x57',b'\x48\x83\xec\x20',None,b'\x48\x8b\xda',b'\x48\x8b\xf9',None,
        b'\x48\x8d\x54\x24\x30',b'\xc6\x44\x24\x30\x00',b'\x48\x8b\xcf',None,b'\x84\xc0',None,b'\x48\x89\x74\x24\x38',
        b'\x48\x83\x3b\x00',None,b'\x0f\xb6\x74\x24\x30',b'\x40\x80\xfe\x04',None]
    scalar.need(LABEL,'outputCallProfile',True,not output or (width==4 and not vector2 and not typed_enum and not typed_qword))
    scalar.need(LABEL,'typedEnumCallWidth',True,not typed_enum or (width in (1,4) and not vector2 and not typed_qword))
    scalar.need(LABEL,'typedQwordProfile',True,not typed_qword or width==8 and not vector2 and not typed_enum)
    inline=integer_slots is not None
    scalar.need(LABEL,'inlineBindingProfile',True,not inline or typed_qword and not output and isinstance(integer_slots,dict) and set(integer_slots)=={'idRef','paramSource'} and all(type(v) is int and 16<=v<128 for v in integer_slots.values()) and abs(integer_slots['idRef']-integer_slots['paramSource'])>=4)
    typed=vector2 or typed_enum or typed_qword
    if output:expected[17]=b'\x40\x80\xfe\x02'
    for _ in range(1 if output else 3):expected.extend([b'\x48\x8b\x33',b'\x48\x8b\xcf',None,b'\x48\x85\xf6',None,b'\x45\x33\xc0',b'\x8b\xd0',b'\x48\x8b\xce',None])
    expected.extend([b'\x48\x8b\x1b',b'\x48\x8b\xcf',None,b'\x48\x85\xdb',None,b'\x45\x33\xc0',b'\x48\x8b\xd0',b'\x48\x8b\xcb',None,
        b'\x48\x8b\x74\x24\x38',b'\x48\x8b\x5c\x24\x40',b'\x48\x83\xc4\x20',b'\x5f',b'\xc3',None,b'\xcc',None,None,None,None,None,None,None,None])
    scalar.need(LABEL,'setterCallConstWidth',True,width in (4,8) or width==1 and typed_enum)
    if width==1:expected[25]=b'\x0f\xb6\xd0'
    if width==8:expected[25]=b'\x48\x8b\xd0'
    if inline:
        expected[37:39]=[b'\x48\x8b\xcf',b'\x48\x8b\x33'];expected[46:48]=[b'\x48\x8b\xcf',b'\x48\x8b\x1b']
        for start,name in ((33,'idRef'),(42,'paramSource')):expected[start:start+4]=[b'\x48\x8b\x4e\x10',b'\x48\x85\xc9',None,b'\x89\x41'+bytes((integer_slots[name],))]
    if typed:
        if vector2:scalar.need(LABEL,'vector2CallWidth',8,width)
        expected[68:68]=[None,None]
        expected[19:22]=[None,b'\x48\x8b\xcf',b'\x48\x8b\x33',None]
    at=lambda n:n+(int(n>=19)+2*int(n>=68) if typed else -18*int(n>=46) if output else 0)
    scalar.program_extent(rows,record['window'],LABEL+'.setterCalls');scalar.program(image,rows,expected,LABEL+'.setterCalls')
    def target(n,opcode):
        rva,encoded=rows[at(n)];raw=bytes.fromhex(encoded);size=2 if opcode==b'\x74' else len(opcode)+4
        scalar.need(LABEL,'setterCallControlShape',(size,opcode),(len(raw),raw[:len(opcode)]))
        return rva+size+int.from_bytes(raw[len(opcode):],'little',signed=True)
    for n,dest in ((6,62),(23,60),*((() if output else ((32,60),(41,60)))),(50,60),(69,7)):
        scalar.need(LABEL,'setterCallBranchTarget',rows[at(dest)][0],target(n,b'\xe9' if n==69 else b'\x0f\x84' if n==6 else b'\x74'))
    if inline:
        for n in (35,44):scalar.need(LABEL,'inlineBindingNullGuard',rows[at(60)][0],target(n,b'\x74'))
    for n,opcode in ((15,b'\x0f\x84'),(18,b'\x0f\x85')):
        scalar.need(LABEL,'setterCallColdGuardOutsidePrimary',False,record['window']['startRva']<=target(n,opcode)<record['window']['endRva'])
    for name,n in ((('paramTarget',27),('path',54)) if output else (('constValue',27),('path',54)) if inline else (('constValue',27),('idRef',36),('paramSource',45),('path',54))):
        scalar.need(LABEL,'ownedSetterCall:'+name,setters[name],target(n,b'\xe8'))
    for n in (60,63,65,67):target(n,b'\xe8')
    scalar.need(LABEL,'setterCallSameInitializer',1,len({target(n,b'\xe8') for n in (63,65,67)}))
    for n in (62,64,66):
        raw=bytes.fromhex(rows[at(n)][1]);scalar.need(LABEL,'setterCallInitializerLoad',(7,b'\x48\x8d\x0d'),(len(raw),raw[:3]))
    if typed:
        load=bytes.fromhex(rows[19][1]);init=bytes.fromhex(rows[67][1]);last=bytes.fromhex(rows[69][1]);call=bytes.fromhex(rows[70][1])
        scalar.need(LABEL,'vector2MethodInfoLoad',(7,b'\x48\x8b\x15'),(len(load),load[:3]))
        scalar.need(LABEL,'vector2SameInitializedCell',rows[19][0]+7+int.from_bytes(load[3:],'little',signed=True),rows[67][0]+7+int.from_bytes(init[3:],'little',signed=True))
        scalar.need(LABEL,'vector2ExtraInitializer',(7,b'\x48\x8d\x0d',5,b'\xe8'),(len(last),last[:3],len(call),call[:1]))
        scalar.need(LABEL,'typedExtraInitializerTarget',target(63,b'\xe8'),rows[70][0]+5+int.from_bytes(call[1:],'little',signed=True))
    flag,store=(bytes.fromhex(rows[at(n)][1]) for n in (3,68))
    scalar.need(LABEL,'setterCallInitFlag',(7,b'\x80\x3d',0,7,b'\xc6\x05',1),(len(flag),flag[:2],flag[-1],len(store),store[:2],store[-1]))
    scalar.need(LABEL,'setterCallSharedInitFlag',rows[3][0]+7+int.from_bytes(flag[2:6],'little',signed=True),rows[at(68)][0]+7+int.from_bytes(store[2:6],'little',signed=True))
    calls=(('header',10),('null',12),('paramTarget',21),('path',48)) if output else (('header',10),('null',12),('constValue',21),('idRef',30),('paramSource',39),('path',48))
    return {name:target(n,b'\x0f\x84' if name=='null' else b'\xe8') for name,n in calls}


def null_output_program(image,record,restore_rva):
    rows=record['instructions'];window=record['window']
    scalar.need(LABEL,'nullWithinOwnedFragment',True,record['fragmentStartRva']<=window['startRva']<window['endRva']<=record['fragmentEndRva'])
    scalar.program_extent(rows,window,LABEL+'.null');image.check_windows([window],label=LABEL+'.null')
    scalar.program(image,rows,[b'\x48\x8b\xcb',b'\x48\xc7\x03\x00\x00\x00\x00',None,b'\x90',None],LABEL+'.null')
    targets=[]
    for n,opcode in ((2,b'\xe8'),(4,b'\xe9')):
        raw=bytes.fromhex(rows[n][1]);scalar.need(LABEL,'nullControlShape',(5,opcode),(len(raw),raw[:1]))
        targets.append(rows[n][0]+5+int.from_bytes(raw[1:],'little',signed=True))
    scalar.need(LABEL,'nullRestoresUnsavedRsi',restore_rva,targets[1])
    return targets[0]


def vector3_setter(image,rows,slot):
    scalar.program(image,rows,[b'\x48\x83\xec\x28',b'\x4c\x8b\x41\x10',b'\x4d\x85\xc0',b'\x75\x06',None,b'\xcc',
        b'\xf2\x0f\x10\x02',b'\x8b\x42\x08',b'\xf2\x41\x0f\x11\x40'+bytes((slot,)),b'\x41\x89\x40'+bytes((slot+8,)),b'\x48\x83\xc4\x28',b'\xc3'],LABEL+'.vectorSetter')
    scalar.need(LABEL,'vectorSetterNonNull',rows[6][0],rows[3][0]+2+6)
    raw=bytes.fromhex(rows[4][1]);scalar.need(LABEL,'vectorSetterThrow',(5,b'\xe8'),(len(raw),raw[:1]))


def vector2_setter(image,rows,slot):
    scalar.program(image,rows,[b'\x48\x83\xec\x28',b'\x48\x8b\x41\x10',b'\x48\x89\x54\x24\x30',b'\x48\x85\xc0',b'\x75\x06',None,b'\xcc',
        b'\xf3\x0f\x10\x44\x24\x30',b'\xf3\x0f\x10\x4c\x24\x34',b'\xf3\x0f\x11\x40'+bytes((slot,)),b'\xf3\x0f\x11\x48'+bytes((slot+4,)),
        b'\x48\x83\xc4\x28',b'\xc3'],LABEL+'.vector2Setter')
    scalar.need(LABEL,'vector2SetterNonNull',rows[7][0],rows[4][0]+2+6)
    raw=bytes.fromhex(rows[5][1]);scalar.need(LABEL,'vector2SetterThrow',(5,b'\xe8'),(len(raw),raw[:1]))


def enum_call_program(image,record,setters,constructor,*,width=4):
    """Complete initialized-header enum caller; null and owned stores are explicit."""
    rows=record['instructions']
    expected=[b'\x48\x89\x5c\x24\x10',b'\x48\x89\x74\x24\x18',b'\x57',b'\x48\x83\xec\x20',None,
        b'\x48\x8b\xda',b'\x48\x8b\xf1',None,None,None,None,None,None,None,None,None,None,
        b'\x48\x8d\x54\x24\x30',b'\xc6\x44\x24\x30\x00',b'\x48\x8b\xce',None,b'\x84\xc0',None,
        b'\x48\x83\x3b\x00',None,None,None,b'\x48\x8b\xf8',b'\x48\x85\xc0',None,b'\x33\xd2',b'\x48\x8b\xc8',None,
        b'\x48\x8b\xcb',b'\x48\x89\x3b',None,b'\x80\x7c\x24\x30\x04',None,None,b'\x48\x8b\xce',b'\x48\x8b\x3b',None,
        b'\x48\x85\xff',None,b'\x45\x33\xc0',b'\x8b\xd0',b'\x48\x8b\xcf',None]
    scalar.need(LABEL,'enumCallWidth',True,width in (1,4))
    if width==1:expected[45]=b'\x8a\xd0'
    for _ in range(2):expected.extend([b'\x48\x8b\x3b',b'\x48\x8b\xce',None,b'\x48\x85\xff',None,b'\x45\x33\xc0',b'\x8b\xd0',b'\x48\x8b\xcf',None])
    expected.extend([b'\x48\x8b\x1b',b'\x48\x8b\xce',None,b'\x48\x85\xdb',None,b'\x45\x33\xc0',b'\x48\x8b\xd0',b'\x48\x8b\xcb',None,None,None,b'\xcc',None,None,None,b'\x33\xd2',b'\x48\x8b\xcb',None,
        b'\x44\x8a\x44\x24\x30',b'\x45\x33\xc9',b'\xb2\x04',b'\x48\x8b\xc8',None,b'\xcc',b'\x48\x8b\xcb',b'\x48\xc7\x03\x00\x00\x00\x00',None,
        b'\x48\x8b\x5c\x24\x38',b'\x48\x8b\x74\x24\x40',b'\x48\x83\xc4\x20',b'\x5f',b'\xc3'])
    scalar.program_extent(rows,record['window'],LABEL+'.enumCaller');scalar.program(image,rows,expected,LABEL+'.enumCaller')
    def target(n,opcode):
        rva,encoded=rows[n];raw=bytes.fromhex(encoded);size=len(opcode)+(1 if opcode in (b'\x75',b'\x74',b'\xeb') else 4)
        scalar.need(LABEL,'enumControlShape',(size,opcode),(len(raw),raw[:len(opcode)]))
        return rva+size+int.from_bytes(raw[len(opcode):],'little',signed=True)
    for n,opcode,destination in ((7,b'\x75',17),(22,b'\x0f\x84',90),(24,b'\x75',36),(29,b'\x0f\x84',76),
            (37,b'\x0f\x85',78),*((n,b'\x74',76) for n in (43,52,61,70)),(75,b'\xeb',93)):
        scalar.need(LABEL,'enumBranchTarget',rows[destination][0],target(n,opcode))
    initial=[]
    for n in (8,10,12,14):
        rva,encoded=rows[n];raw=bytes.fromhex(encoded)
        scalar.need(LABEL,'enumInitializerLoad',(7,b'\x48\x8d\x0d'),(len(raw),raw[:3]))
        initial.append(rva+7+int.from_bytes(raw[3:],'little',signed=True))
    scalar.need(LABEL,'enumSameInitializer',1,len({target(n,b'\xe8') for n in (9,11,13,15)}))
    for n,opcode,cell in ((25,b'\x48\x8b\x0d',initial[1]),(38,b'\x48\x8b\x15',initial[2]),
                          (78,b'\x48\x8b\x0d',initial[3]),(79,b'\x48\x8b\x1d',initial[0])):
        rva,encoded=rows[n];raw=bytes.fromhex(encoded)
        scalar.need(LABEL,'enumInitializedCell',(7,opcode,cell),(len(raw),raw[:3],rva+7+int.from_bytes(raw[3:],'little',signed=True)))
    flag,store=(bytes.fromhex(rows[n][1]) for n in (4,16))
    scalar.need(LABEL,'enumInitFlag',(7,b'\x80\x3d',0,7,b'\xc6\x05',1),(len(flag),flag[:2],flag[-1],len(store),store[:2],store[-1]))
    scalar.need(LABEL,'enumSameInitFlag',rows[4][0]+7+int.from_bytes(flag[2:6],'little',signed=True),rows[16][0]+7+int.from_bytes(store[2:6],'little',signed=True))
    scalar.need(LABEL,'enumAllocatedConstructor',constructor,target(32,b'\xe8'))
    for name,n in (('constValue',47),('idRef',56),('paramSource',65),('path',74)):
        scalar.need(LABEL,'enumOwnedSetter:'+name,setters[name],target(n,b'\xe8'))
    for n in (26,76,80,83,88):target(n,b'\xe8')
    scalar.need(LABEL,'enumSameBarrier',target(35,b'\xe8'),target(92,b'\xe8'))
    return {name:target(n,b'\xe8') for name,n in (('header',20),('constValue',41),('idRef',50),('paramSource',59),('path',68),('barrier',92))}


def initialized_enum_program(image,record,setters,*,width=4):
    """Complete typed DWORD/QWORD caller with initialization before its header read."""
    scalar.need(LABEL,'initializedTypedWidth',True,type(width) is int and width in (4,8))
    rows=record['instructions']
    expected=[b'\x48\x89\x5c\x24\x18',b'\x57',b'\x48\x83\xec\x20',None,b'\x48\x8b\xda',b'\x48\x8b\xf9',None,
        None,None,None,None,None,None,None,None,None,b'\x48\x8d\x54\x24\x30',b'\xc6\x44\x24\x30\x00',b'\x48\x8b\xcf',None,
        b'\x84\xc0',None,b'\x48\x89\x74\x24\x38',b'\x48\x83\x3b\x00',None,b'\x0f\xb6\x74\x24\x30',b'\x40\x80\xfe\x04',None,
        None,b'\x48\x8b\xcf',b'\x48\x8b\x33',None,b'\x48\x85\xf6',b'\x75\x06',None,b'\xcc',b'\x45\x33\xc0',b'\x8b\xd0',b'\x48\x8b\xce',None]
    for _ in range(2):expected.extend([b'\x48\x8b\x33',b'\x48\x8b\xcf',None,b'\x48\x85\xf6',None,b'\x45\x33\xc0',b'\x8b\xd0',b'\x48\x8b\xce',None])
    expected.extend([b'\x48\x8b\x1b',b'\x48\x8b\xcf',None,b'\x48\x85\xdb',None,b'\x45\x33\xc0',b'\x48\x8b\xd0',b'\x48\x8b\xcb',None,
        b'\x48\x8b\x74\x24\x38',b'\x48\x8b\x5c\x24\x40',b'\x48\x83\xc4\x20',b'\x5f',b'\xc3'])
    if width==8:expected[37]=b'\x48\x8b\xd0'
    scalar.program_extent(rows,record['window'],LABEL+'.initializedEnum');scalar.program(image,rows,expected,LABEL+'.initializedEnum')
    def target(n,opcode):
        rva,encoded=rows[n];raw=bytes.fromhex(encoded);size=len(opcode)+(1 if opcode in (b'\x75',b'\x74') else 4)
        scalar.need(LABEL,'initializedEnumControl',(size,opcode),(len(raw),raw[:len(opcode)]))
        return rva+size+int.from_bytes(raw[len(opcode):],'little',signed=True)
    for n,opcode,destination in ((6,b'\x75',16),(33,b'\x75',36),*((n,b'\x74',34) for n in (44,53,62))):
        scalar.need(LABEL,'initializedEnumBranch',rows[destination][0],target(n,opcode))
    for n,opcode in ((21,b'\x0f\x84'),(24,b'\x0f\x84'),(27,b'\x0f\x85')):
        scalar.need(LABEL,'initializedEnumColdGuard',False,record['window']['startRva']<=target(n,opcode)<record['window']['endRva'])
    for n in (7,9,11,13):
        raw=bytes.fromhex(rows[n][1]);scalar.need(LABEL,'initializedEnumCellLoad',(7,b'\x48\x8d\x0d'),(len(raw),raw[:3]))
    scalar.need(LABEL,'initializedEnumSameInitializer',1,len({target(n,b'\xe8') for n in (8,10,12,14)}))
    flag,store=(bytes.fromhex(rows[n][1]) for n in (3,15))
    scalar.need(LABEL,'initializedEnumFlag',(7,b'\x80\x3d',0,7,b'\xc6\x05',1),(len(flag),flag[:2],flag[-1],len(store),store[:2],store[-1]))
    scalar.need(LABEL,'initializedEnumSameFlag',rows[3][0]+7+int.from_bytes(flag[2:6],'little',signed=True),rows[15][0]+7+int.from_bytes(store[2:6],'little',signed=True))
    load=bytes.fromhex(rows[28][1]);init=bytes.fromhex(rows[11][1])
    scalar.need(LABEL,'initializedEnumContextLoad',(7,b'\x48\x8b\x15'),(len(load),load[:3]))
    scalar.need(LABEL,'initializedEnumSameContext',rows[11][0]+7+int.from_bytes(init[3:],'little',signed=True),rows[28][0]+7+int.from_bytes(load[3:],'little',signed=True))
    for name,n in (('constValue',39),('idRef',48),('paramSource',57),('path',66)):
        scalar.need(LABEL,'initializedEnumSetter:'+name,setters[name],target(n,b'\xe8'))
    target(34,b'\xe8')
    return {name:target(n,b'\x0f\x84' if name=='null' else b'\xe8') for name,n in (('header',19),('null',21),('constValue',31),('idRef',42),('paramSource',51),('path',60))}


def derive_parameter(image,inputs,primitive,*,value_type=None,enum_byte=False,unmanaged_qword=False):
    """Derive current declarations; never reuse an old RVA or generic heap offset."""
    if primitive not in ('bool','int','string','float','uint','ulong','vector2','vector3'):raise ValueError(LABEL+'.unsupported-primitive:'+str(primitive))
    width,kind={'bool':(1,2),'int':(4,8),'string':(8,14),'float':(4,12),'uint':(4,9),'ulong':(8,11),'vector2':(8,17),'vector3':(12,17)}[primitive]
    reference=primitive=='string';floating=primitive=='float';vector2=primitive=='vector2';vector3=primitive=='vector3';called=primitive in ('uint','ulong','vector2')
    scalar.need(LABEL,"unmanagedQwordProfile",True,type(unmanaged_qword) is bool and (not unmanaged_qword or primitive=="ulong" and type(value_type) is str and not enum_byte))
    enum=value_type is not None and not unmanaged_qword
    if enum and primitive!='int':raise ValueError(LABEL+'.enum-integer-profile-required')
    if enum_byte:
        scalar.need(LABEL,'byteEnumProfile',True,enum);width=1
    typename=value_type if value_type is not None else 'UnityEngine.Vector'+primitive[-1] if vector2 or vector3 else primitive
    if enum or unmanaged_qword:kind=17;called=True
    wrapped='Beyond.Gameplay.Actions.Param`1<'+typename+'>'
    base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);index=image.body_index
    unwind=image.unwind_index if called else None
    matches=[w for w in derive_from_image(image).values() if w.wrapped_type==wrapped]
    scalar.need(LABEL,'wrapperCount',1,len(matches));wrapper=matches[0]
    scalar.need(LABEL,'memberTypes',[('constValue',typename),('idRef','int'),('paramSource','int'),('path','string')],[(m.name,m.declared_type) for m in wrapper.members])
    if unmanaged_qword:
        definition=ctx.index.types[typename]
        fields=[(md.string(f.name_index),*ctx.field(typename+'::'+md.string(f.name_index))[1:]) for f in md.fields_for(definition) if not ctx.field_attributes(f.type_index)&16]
        scalar.need(LABEL,'unmanagedQwordValue',True,ctx.is_value_type(typename))
        scalar.need(LABEL,'unmanagedQwordField',[('id','ulong',16)],fields)
        value_field,=[f for f in md.fields_for(definition) if not ctx.field_attributes(f.type_index)&16]
        scalar.ordinary(image,ctx.type_pointer(value_field.type_index),11,LABEL+'.unmanagedQwordField')
        sizes=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*definition.index)
        scalar.need(LABEL,'unmanagedQwordSizes',(24,8),(image.pe.u32_at_va(sizes),image.pe.u32_at_va(sizes+4)))
    if enum:
        scalar.need(LABEL,'enumConstantKind',('enum','scalar8' if enum_byte else 'scalar32',width),(wrapper.members[0].kind,wrapper.members[0].underlying_kind,wrapper.members[0].width))
        definition=ctx.index.types[typename];backing=[f for f in md.fields_for(definition) if md.string(f.name_index)=='value__']
        scalar.need(LABEL,'oneEnumBacking',1,len(backing));scalar.ordinary(image,ctx.type_pointer(backing[0].type_index),5 if enum_byte else 8,LABEL+'.enumBacking')
    scalar.need(LABEL,'wrapperHolder', (wrapper.name,wrapped,16),ctx.field(wrapper.name+'::__instance'))
    def record(pointer,size=None,*,owned=False):
        end=pointer+size if size is not None else index.extents[pointer]
        ranges=[]
        if owned:
            ranges=sorted(tuple(r['runtimeTriple'][:2]) for r in unwind.family(pointer-base)['ranges'])
            scalar.need(LABEL,'ownedPrimaryRange',True,(pointer-base,end-base) in ranges)
            for a,b in ranges:
                if base+a==end:end=base+b
        raw=image.pe.bytes_at_va(pointer,end-pointer);rows=index._decode(pointer,end-pointer)
        return {'pointerRva':pointer-base,'window':{'startRva':pointer-base,'endRva':end-base,'sha256':hashlib.sha256(raw).hexdigest().upper()},
                'instructions':[[int(r['va'],16)-base,bytes.fromhex(r['bytes']).hex().upper()] for r in rows],
                **({'contiguousOwnedRanges':[[a,b] for a,b in ranges if pointer-base<=a<end-base]} if owned else {})}
    methods={};slots={}
    for name in ('.ctor','CreateInstance','GetValue','Deserialize',*('set___'+m.name+'__' for m in wrapper.members)):
        found=[m for m in md.methods_for(md.types[wrapper.type_definition]) if md.string(m.name_index)==name]
        scalar.need(LABEL,'namedMethod:'+name,1,len(found));m=found[0]
        methods[name]={'methodIndex':m.index,**record(image.method_pointer_va(m),5 if name=='GetValue' else None,owned=called and name=='Deserialize')}
        if name=='Deserialize':
            reader_abi(image,ctx,m,wrapper)
        else:
            name_type={'constValue':(typename,kind,reference),'idRef':('int',8,False),'paramSource':('int',8,False),'path':('string',14,True)}
            result=(wrapped,21,True) if name=='GetValue' else ('void',1,False)
            scalar.owned_method_abi(image,ctx,m.index,wrapper.type_definition,result,[name_type[name[6:-2]]] if name.startswith('set___') else [],LABEL)
        if name.startswith('set___'):
            member=name[6:-2];instructions=methods[name]['instructions'];is_reference=member=='path' or (reference and member=='constValue')
            nonnull_reference=is_reference and bytes.fromhex(instructions[3][1])==b'\x75\x06'
            slots[member]=bytes.fromhex(instructions[(8 if vector3 else 9) if (vector2 or vector3) and member=='constValue' else (6 if nonnull_reference else 4) if is_reference else 6][1])[-1]
            if vector3 and member=='constValue':vector3_setter(image,instructions,slots[member])
            elif vector2 and member=='constValue':vector2_setter(image,instructions,slots[member])
            else:scalar.parameter_setter(image,instructions,name='path' if is_reference else member,slot=slots[member],width=width,label=LABEL+'.'+member,floating=floating and member=='constValue')
    occupied=[at for name,size in (('constValue',width),('idRef',4),('paramSource',4),('path',8)) for at in range(slots[name],slots[name]+size)]
    scalar.need(LABEL,'disjointOwnedSlots',(width+16,True),(len(set(occupied)),all(16<=at<128 for at in occupied)))
    scalar.program(image,methods['GetValue']['instructions'],[b'\x48\x8b\x41\x10',b'\xc3'],LABEL+'.getter')
    loads=[row for row in methods['.ctor']['instructions'] if bytes.fromhex(row[1])[:3]==b'\x48\x8b\x0d']
    scalar.need(LABEL,'oneAllocationLoad',1,len(loads))
    parameter={'methods':methods,'ownedFieldSlots':slots,'allocationContext':derive_typed_usage_context(image,loads[0][0],label=LABEL)}
    scalar.need(LABEL,'allocationType',wrapped,parameter['allocationContext']['typeName']);scalar.allocation_bridge(image,ctx,parameter,LABEL)
    offsets=scalar.reader_offsets(image,LABEL);extra={}
    if called:
        typed_enum=enum and len(methods['Deserialize']['instructions'])==73
        initialized_typed=(enum or unmanaged_qword) and len(methods['Deserialize']['instructions'])==72
        owned_setters={n:methods['set___'+n+'__']['pointerRva'] for n in slots}
        targets=(initialized_enum_program(image,methods['Deserialize'],owned_setters,width=width) if initialized_typed else
            enum_call_program(image,methods['Deserialize'],owned_setters,methods['.ctor']['pointerRva'],width=width) if enum and not typed_enum else
            setter_call_program(image,methods['Deserialize'],{n:methods['set___'+n+'__']['pointerRva'] for n in slots},width=width,vector2=vector2,typed_enum=typed_enum,typed_qword=unmanaged_qword))
        extra['headerSource']=record(base+targets['header']);object_header_source(image,extra['headerSource'],offsets)
        if enum or unmanaged_qword:
            context=derive_typed_usage_context(image,methods['Deserialize']['instructions'][28 if initialized_typed else 19 if typed_enum or unmanaged_qword else 38][0],label=LABEL)
            scalar.need(LABEL,'enumTypedReader',('MemoryPack.MemoryPackReader','ReadUnmanaged',[],[typename]),
                (context['typeName'],context['methodName'],context['classArguments'],context['methodArguments']))
            arguments=image.instantiations.resolve(context['methodSpec'][2]).arguments
            scalar.need(LABEL,'enumReaderArgumentCount',1,len(arguments))
            scalar.ordinary(image,arguments[0].type_pointer_va,17,LABEL+'.enumReadArgument')
            scalar.need(LABEL,'enumReaderDefinition',definition.index,int.from_bytes(bytes.fromhex(arguments[0].raw_type_record_hex)[:8],'little'))
            extra['constantReadContext']=context
        if not enum or typed_enum or initialized_typed:
            pointer=base+targets['null'];owner=base+methods['Deserialize']['pointerRva']
            ranges=[tuple(r['runtimeTriple'][:2]) for r in unwind.family(owner-base)['ranges'] if r['runtimeTriple'][0]<=pointer-base<r['runtimeTriple'][1]]
            scalar.need(LABEL,'oneOwnedNullFragment',1,len(ranges));start,end=ranges[0];size=end-start;start+=base
            extra['nullBranch']={**record(pointer,start+size-pointer),'ownerRva':owner-base,'fragmentStartRva':start-base,'fragmentEndRva':start+size-base}
            targets['barrier']=null_output_program(image,extra['nullBranch'],methods['Deserialize']['instructions'][68 if initialized_typed else 57 if vector2 or typed_enum or unmanaged_qword else 56][0])
    else:targets=inline_program(image,methods['Deserialize'],slots,offsets,width=width,reference=reference,floating=floating,vector3=vector3)
    scalar.need(LABEL,'sameIntegerSource',targets['idRef'],targets['paramSource'])
    if vector2 or vector3:
        from scripts.game_data.memorypack.vector3_source import validate_vector3_source
        from scripts.game_data.memorypack.vector2_source import validate_vector2_source
        context=derive_typed_usage_context(image,methods['Deserialize']['instructions'][19 if vector2 else 26][0],label=LABEL)
        constant=(validate_vector2_source if vector2 else validate_vector3_source)(image,context,targets['constValue'])
    else:constant=pooled_source_helper.validate_on_image(image,base+targets['constValue'],inputs) if reference else record(base+targets['constValue'])
    if enum_byte:
        scalar.raw_byte_source(image,constant,offsets)
    elif unmanaged_qword:
        from scripts.game_data.memorypack.unmanaged_qword_source import validate as validate_qword
        constant['bufferedProgram']=validate_qword(image,base+targets['constValue'],offsets)
    elif primitive=='ulong':
        scalar.integer_source(image,constant,offsets,LABEL+'.constant',width=8)
    elif floating:single_source(image,constant,offsets)
    elif not reference and not (vector2 or vector3):(scalar.boolean_source if primitive=='bool' else scalar.integer_source)(image,constant,offsets,LABEL+'.constant')
    integer=record(base+targets['idRef'])
    scalar.integer_source(image,integer,offsets,LABEL+'.integer')
    strings=pooled_source_helper.validate_on_image(image,base+targets['path'],inputs)
    scalar.need(LABEL,'poolEncoding','int32-pool-index',strings['wireEncoding'])
    path_rows=methods['set___path__']['instructions']
    path=path_rows[9 if bytes.fromhex(path_rows[3][1])==b'\x75\x06' else 7];raw=bytes.fromhex(path[1])
    scalar.need(LABEL,'samePathBarrier',targets['barrier'],path[0]+5+int.from_bytes(raw[1:],'little',signed=True))
    if reference:
        scalar.need(LABEL,'samePooledSource',targets['path'],targets['constValue'])
        call=methods['set___constValue__']['instructions'][7];raw=bytes.fromhex(call[1])
        scalar.need(LABEL,'sameConstantSetterBarrier',targets['barrier'],call[0]+5+int.from_bytes(raw[1:],'little',signed=True))
    return {'status':'validated',**({'valueType':typename,'valueFields':[list(f) for f in fields],'rawSize':8} if unmanaged_qword else {}),'parameter':parameter,'booleanSource' if primitive=='bool' else 'constantSource':constant,'int32Source':integer,'readerFieldOffsets':offsets,'targets':targets,**extra,
            'evidenceBoundary':{'direct':{'bool':'Named typed wrapper, owned constructor/store slots, complete selected inline read/store/return program, normalized byte source, two Int32 reads and pooled path.',
                'int':('Named typed unsigned-byte enum backing, owned constructor/setter slots, complete selected header/caller/null program, exact enum ReadUnmanaged context, one raw byte, two raw DWORD reads and pooled path.' if enum_byte else 'Named typed signed-Int32 enum backing, owned constructor/setter slots, complete selected header/caller/null program, exact enum ReadUnmanaged context, three raw DWORD reads and pooled path.' if enum else 'Named typed Int32 wrapper, owned constructor/store slots, complete selected inline read/store/return program, three raw DWORD reads and pooled path.'),
                'float':'Named typed Single wrapper, owned constructor/store slots, complete selected inline read/store/return program, raw XMM Single transfer, two Int32 reads and pooled path.',
                'uint':'Named typed UInt32 wrapper, owned constructor/setter slots, complete selected buffered-header/setter-call program and owned null branch, raw DWORD transfers and pooled path.',
                'ulong':('Named typed unmanaged one-UInt64 value wrapper, exact closed ReadUnmanaged context, owned constructor/setter slots, complete selected caller/null branch, raw eight-byte transfer and owned Advance paths with pooled tail.' if unmanaged_qword else 'Named typed UInt64 wrapper, owned constructor/setter slots, complete selected buffered-header/setter-call program and owned null branch, full QWORD transfer and eight-byte cursor accounting with pooled path.'),
                'vector3':'Named typed Vector3 wrapper, owned constructor/setter slots, complete selected caller with disjoint stack result and 8+4-byte field transfer, typed Vector3 source and pooled path.',
                'vector2':'Named typed Vector2 wrapper, owned constructor/setter slots, complete typed caller/context, raw packed XY transfer, matching two-Single setter, buffered source and pooled path.',
                'string':'Named typed String wrapper, owned constructor/store slots, complete selected inline read/store/return program, two pooled string reads, two Int32 reads and both reference barriers.'}[primitive],
                'conditional':'Initialized metadata, valid disjoint reader/output storage, sufficient buffers, matching initialized StringPool and selected compatible nonnull wrapper/holder; ordinary ABI-preserving allocation, barrier and callees.',
                'unresolved':['generic Param heap field layout independent of these owned setters','cold refill/allocation paths','live provider/holder selection','enclosing owner and corpus admission']}}


def validate_contract(*,contract_path,schema,primitive,label,game_root=None,gameassembly=None,metadata=None,codec_kind=None,value_type=None,enum_byte=False):
    try:
        if enum_byte and value_type is None:raise ValueError(label+'.byte-enum-type-required')
        path=Path(contract_path);raw=path.read_bytes();fact=json.loads(raw);pins=fact['nativeInputs'];codec='Param<'+('Vector'+primitive[-1] if primitive in ('vector2','vector3') else primitive)+'>'
        if value_type is not None:
            codec=codec_kind
            if set(fact)!={'schema','status','nativeInputs','components','evidenceBoundary'}:
                raise ValueError(label+'.contract:component-scope')
            selected=[row for row in fact['components'] if row.get('codecKind')==codec]
            if (len(selected)!=1 or set(selected[0])!={'codecKind','wrappedType','proof'}
                    or selected[0]['wrappedType']!='Beyond.Gameplay.Actions.Param`1<'+value_type+'>'):
                raise ValueError(label+'.contract:closed-enum-component')
            declared=selected[0]['proof']
            fact={**fact,'codecKind':codec}
        else:declared={'status':'validated','evidenceBoundary':fact['evidenceBoundary'],**fact['proof']}
        if (fact.get('schema'),fact.get('status'),fact.get('codecKind'))!=(schema,'exact-current-build',codec) or set(pins)!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}:
            raise ValueError(label+'.contract:identity-or-pin-scope')
        if (gameassembly is None)!=(metadata is None):raise ValueError(label+'.native:both paths required')
        root=Path(game_root) if game_root is not None else None
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
            gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll' if root else None,
            metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat' if root else None)
        if gate.status!='validated':return {'status':gate.status,'detail':gate.detail}
        failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
        if failed:return failed
        strings=pooled_source_helper.CONTRACT_PATH.read_bytes()
        image=open_native_image(gate.gameassembly,gate.metadata)
        actual=derive_parameter(image,pins,primitive,**({'value_type':value_type,**({'enum_byte':True} if enum_byte else {})} if value_type is not None else {}))
        if fact['evidenceBoundary']!=actual['evidenceBoundary']:raise ValueError(label+'.contract:evidence-boundary')
        validate_claims(declared,actual,label=label+'.proof');validate_claims(actual,declared,label=label+'.declaration')
        enum_values=native_enum_members(image.metadata,image.body_index.enum_defaults,image.pe,image.registration,value_type) if value_type is not None else None
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        if after.status!='validated':return {'status':after.status,'detail':'native inputs changed during validation: '+after.detail}
        failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
        if failed:return failed
        if path.read_bytes()!=raw or pooled_source_helper.CONTRACT_PATH.read_bytes()!=strings:raise ValueError(label+'.contract:declaration changed during validation')
        return {'status':'validated','codecKind':codec,'rawSize':1 if enum_byte else {'bool':1,'int':4,'string':8,'float':4,'uint':4,'ulong':8,'vector2':8,'vector3':12}[primitive],'pathEncoding':'int32-pool-index',
            **({'valueEncoding':'int32-pool-index'} if primitive=='string' else {}),**({'enumValues':enum_values} if enum_values is not None else {}),'nativeInputs':pins,'evidenceBoundary':actual['evidenceBoundary']}
    except (ValueError,KeyError,IndexError,TypeError,OSError,RuntimeError) as error:
        return native_validation_failure(error,label=label,source_path=contract_path)


def run_cli(validator,default):
    import argparse
    parser=argparse.ArgumentParser(description='Authenticate the selected primitive Param storage component.')
    for name in ('contract','game-root','gameassembly','metadata'):parser.add_argument('--'+name,type=Path,default=default if name=='contract' else None)
    args=parser.parse_args()
    result=validator(contract_path=args.contract,game_root=args.game_root,gameassembly=args.gameassembly,metadata=args.metadata)
    print(json.dumps(result,indent=2));return 0 if result['status']=='validated' else 2

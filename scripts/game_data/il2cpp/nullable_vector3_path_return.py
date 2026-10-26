"""Exact Win64 hot path producing a tagged Vector3 return buffer.

The complete primary/continuation program binds incoming aliases, a path
reference read, 32-bit count arithmetic, a twelve-byte indexed copy, a data
flag guard and the sixteen-byte caller-buffer return. Named types/fields and
closed Nullable interface programs are authenticated by the caller. This does
not infer the array header, total closed value size, navigation writes, cold
initialization/IFix/distance paths or actual gameplay execution.
"""
from __future__ import annotations

import hashlib


def prove_nullable_vector3_path_return(raw: bytes, *, entry_va: int,
        type_init_va: int, patched_check_va: int, patched_path_va: int,
        calculate_corners_va: int, null_failure_va: int, bounds_failure_va: int,
        distance_path_va: int, path_corners_offset: int, data_reference_offset: int,
        distance_flag_offset: int) -> dict:
    """Prove the complete hot program; every split/call target is explicit."""
    addresses = (entry_va,type_init_va,patched_check_va,patched_path_va,
        calculate_corners_va,null_failure_va,bounds_failure_va,distance_path_va)
    if (not isinstance(raw,bytes) or any(type(v) is not int or not 0<v<1<<64 for v in addresses)
            or entry_va+len(raw)>=1<<64):
        raise ValueError('nullable-vector3-path.input: original bytes and bounded addresses required')
    if any(type(v) is not int or not 0<v<128 for v in
           (path_corners_offset,data_reference_offset,distance_flag_offset)):
        raise ValueError('nullable-vector3-path.field: positive signed-byte field offsets required')
    rows=[];offset=0
    def literal(hexed,meaning):
        nonlocal offset
        expected=bytes.fromhex(hexed);actual=raw[offset:offset+len(expected)]
        if actual!=expected:
            raise ValueError(f'nullable-vector3-path.instruction: offset={offset} expected={hexed} actual={actual.hex().upper()}')
        rows.append({'offset':offset,'rawHex':hexed,'operation':meaning});offset+=len(expected)
    def branch(prefix,target,meaning,*,short=False):
        nonlocal offset
        opcode=bytes.fromhex(prefix);size=len(opcode)+(1 if short else 4)
        actual=raw[offset:offset+size]
        if len(actual)!=size or actual[:len(opcode)]!=opcode:
            raise ValueError(f'nullable-vector3-path.branch-opcode: offset={offset} expected={prefix} actual={actual.hex().upper()}')
        destination=entry_va+offset+size+int.from_bytes(actual[len(opcode):],'little',signed=True)
        if destination!=target:
            raise ValueError(f'nullable-vector3-path.branch-target: offset={offset} expected={target:#x} actual={destination:#x}')
        rows.append({'offset':offset,'rawHex':actual.hex().upper(),'operation':meaning,'targetVa':target});offset+=size
    for h,m in [('4055','push incoming rbp'),('56','push incoming rsi'),('57','push incoming rdi'),
        ('4156','push incoming r14'),('4157','push incoming r15'),
        ('488D6C24E1','rbp = entry rsp - 71'),('4881ECB0000000','rsp = entry rsp - 216')]:literal(h,m)
    flag=raw[offset:offset+7]
    if len(flag)!=7 or flag[:2]!=bytes.fromhex('803D') or flag[-1]!=0:
        raise ValueError('nullable-vector3-path.initialization-flag: exact RIP byte compare with zero required')
    flag_va=entry_va+offset+7+int.from_bytes(flag[2:6],'little',signed=True)
    if not 0<flag_va<1<<64:raise ValueError('nullable-vector3-path.initialization-flag: address overflow')
    rows.append({'offset':offset,'rawHex':flag.hex().upper(),'operation':'compare anonymous initialized flag with zero','readVa':flag_va});offset+=7
    for h,m in [('4D8BF1','r14 = incoming r9 expect-position pointer'),('4D8BF8','r15 = incoming r8 source-position pointer'),
        ('488BF2','rsi = incoming rdx receiver'),('488BF9','rdi = incoming rcx output buffer')]:literal(h,m)
    branch('0F84',type_init_va,'if initialization flag is zero branch to separate init code')
    for h,m in [('48899C24E0000000','save rbx in entry home slot +8'),('33C0','zero eax and full rax'),
        ('4C89A424E8000000','save r12 in entry home slot +16'),('0F57C0','zero xmm0 bits'),
        ('4C89AC24F0000000','save r13 in entry home slot +24'),('33D2','zero edx and full rdx')]:literal(h,m)
    immediate=raw[offset:offset+5]
    if len(immediate)!=5 or immediate[0]!=0xb9:
        raise ValueError('nullable-vector3-path.patch-id: complete MOV ECX,imm32 required')
    patch_id=int.from_bytes(immediate[1:],'little')
    rows.append({'offset':offset,'rawHex':immediate.hex().upper(),'operation':'supply patch-check id in ecx','immediate':patch_id});offset+=5
    for h,m in [('0F29B424A0000000','save nonvolatile xmm6'),('0F1145FF','zero sixteen-byte local output at rbp-1'),
        ('488945AF','zero fallback local bytes 0..7 at rbp-81'),('8945B7','zero fallback local bytes 8..11')]:literal(h,m)
    branch('E8',patched_check_va,'call selected patch check')
    literal('84C0','test returned al for zero')
    branch('0F85',patched_path_va,'if patched branch to separate wrapper code')
    literal('488B5D6F','rbx = incoming fifth visible argument at entry rsp+40')
    literal('4885DB','test path reference for null')
    branch('0F84',null_failure_va,'if path is null branch to selected failure helper block')
    literal('33D2','zero optional method context in rdx')
    literal('488BCB','rcx = path reference')
    branch('E8',calculate_corners_va,'call selected CalculateCorners instance entry')
    literal('488B4B'+f'{path_corners_offset:02X}','rcx = named corners-array reference')
    literal('4885C9','test corners reference for null')
    branch('0F84',null_failure_va,'if corners reference is null branch to failure block')
    count_program_start=offset
    literal('48634118','rax = sign-extended dword at array+24')
    literal('488D50FF','rdx = signed count - 1, as 64-bit address arithmetic')
    literal('FFC8','decrement eax as 32-bit value, zero-extending rax')
    literal('3B4118','compare decremented eax with a second dword at array+24')
    branch('0F83',bounds_failure_va,'unsigned JAE rejects index >= second count')
    literal('488D0452','rax = rdx + 2*rdx; multiply signed index by three')
    literal('C645FF01','set local output byte zero to one')
    literal('F20F10448120','read eight bytes at array+32+4*rax')
    literal('0F57F6','zero xmm6 accumulation bits')
    literal('8B448128','read four bytes at array+40+4*rax')
    literal('89450B','write four value bytes at local output+12')
    literal('488B46'+f'{data_reference_offset:02X}','rax = selected receiver data reference')
    literal('F20F114503','write eight value bytes at local output+4')
    literal('4885C0','test data reference for null')
    branch('74',null_failure_va,'if data is null branch to failure block',short=True)
    literal('8078'+f'{distance_flag_offset:02X}'+'00','compare named distance-check byte with zero')
    branch('0F85',distance_path_va,'if enabled branch to separate distance path')
    return_offset=offset
    for h,m in [('0F1045FF','read all sixteen local output bytes'),('0F28B424A0000000','restore incoming xmm6'),
        ('488BC7','rax = saved incoming output pointer'),('4C8BAC24F0000000','restore incoming r13'),
        ('4C8BA424E8000000','restore incoming r12'),('488B9C24E0000000','restore incoming rbx'),
        ('0F1107','write sixteen bytes to saved incoming output pointer'),
        ('4881C4B0000000','restore allocated rsp frame'),('415F','restore r15'),('415E','restore r14'),
        ('5F','restore rdi'),('5E','restore rsi'),('5D','restore rbp'),('C3','return to entry return address')]:literal(h,m)
    if offset!=len(raw):raise ValueError(f'nullable-vector3-path.terminal: expectedBytes={offset} actualBytes={len(raw)}')
    return {'status':'complete-nullable-vector3-hot-path-return-program-proved',
        'programBytes':len(raw),'programSha256':hashlib.sha256(raw).hexdigest().upper(),'program':rows,
        'incomingAliases':{'output':'rcx -> rdi','receiver':'rdx -> rsi','sourcePosition':'r8 -> r15','expectPosition':'r9 -> r14'},
        'frame':{'rbpFromEntryRsp':-71,'allocatedRspFromEntryRsp':-216,
                 'pathEntryStackOffset':40,'pathRbpOffset':111,'localReturnRbpOffset':-1},
        'countProgramOffset':count_program_start,'returnProgramOffset':return_offset,
        'countReadBits':32,'countInitiallySignExtended':True,'decrementBits':32,'boundsComparisonUnsigned':True,
        'indexExpression':'signExtend32(firstCount)-1','sourceAddressExpression':'array+32+12*(signExtend32(firstCount)-1)',
        'tagByte':1,'valueByteOffset':4,'valueBytesCopied':12,'returnBytesCopied':16,
        'paddingBytesZeroFromFullLocalInitialization':True,'returnedOutputRegister':'rax',
        'distanceFlagOffset':distance_flag_offset,'initializationFlagVa':flag_va,'patchCheckId':patch_id,
        'namedArrayHeaderOrActualCountProved':False,'completeClosedNullableSizeProved':False,
        'wholeManagedMethodOrColdPathsProved':False,'calculatedCornerValuesOrWritesProved':False,'runtimeExecutionKnown':False,
        'conditions':['Selected original primary/continuation program and Win64 calling convention',
            'Initialization guard takes its nonzero path and patch check returns zero normally',
            'CalculateCorners returns normally and callees preserve Win64 nonvolatile registers',
            'Non-null readable selected path, corners array and typed receiver data',
            'Both dword count reads are stable and in [1,2147483647]',
            'The selected typed array uses header count at +24 and twelve-byte elements at +32; header schema remains external',
            'Readable element bytes and valid writable output/home/frame memory without incompatible aliasing',
            'Distance-check byte is zero for the normal direct return'],
        'evidenceBoundary':'Complete hot byte program, buffer/tag writes, incoming pointer aliases, frame restoration and return. Last-corner interpretation is conditional on a stable positive signed dword count and the external array-header schema. Cold initialization, IFix, distance fallback, actual CalculateCorners writes, total closed type size and gameplay execution are not promoted.'}

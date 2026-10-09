"""Observed physical list-reset programs, independent of managed body identity.

Direct evidence: the caller's Int32 append index is written to zero and its
version slot incremented before the old-count branch. A nonpositive count
returns without any call. The selected positive rank-one/null-bounds path
passes array data, zero and the sign-extended Int32 product of old count and
an observed class slot to a span helper, then restores its frame and returns.

That call's implementation, other array paths and managed Clear body parity
are unresolved here. In particular, this proof does not claim the positive
array has been cleared or admit a stored element, list or root.
"""
from __future__ import annotations

import struct
from typing import Any, Callable

from scripts.game_data.memorypack.reference_conversion_sources import validate_program, _target


LOCAL_OPS = {'F7DE':'neg esi', '2BEF':'sub ebp, edi', '0FAFC7':'imul eax, edi',
             '480FAFC8':'imul rcx, rax', '4803CB':'add rcx, rbx'}


def validate_physical_list_reset(image: Any, programs: dict, offsets: dict,
                                 caller_layout: dict, entry: int, *, fail: Callable) -> dict:
    """Join the actual called entry to the same caller index/version/items slots."""
    expected_keys = {'count','version','items','arrayLength','arrayData','arrayBounds',
                     'classRankByte','classStrideInt32'}
    if (set(programs) != {'empty','positive'} or set(offsets) != expected_keys
            or set(caller_layout) != {'count','version','items','arrayLength','arrayData'}
            or any(type(v) is not int or not 0 <= v <= 0xffff for v in offsets.values())
            or any(offsets[k] >= 128 for k in ('count','version','items','arrayLength','arrayData','arrayBounds'))
            or {k:offsets[k] for k in caller_layout} != caller_layout):
        fail('list-reset-layout-join','bounded physical slots joined to the actual append program',offsets)
    count, version, items = (offsets[k] for k in ('count','version','items'))
    if version != count + 4:
        fail('list-reset-version-slot','adjacent separate Int32 count/version slots',offsets)
    rank = struct.pack('<I',offsets['classRankByte']).hex().upper()
    stride = struct.pack('<I',offsets['classStrideInt32']).hex().upper()
    prefix = ['4057','4883EC30',f'8B79{count:02X}','33D2',f'FF41{version:02X}',
              f'8951{count:02X}','85FF',None]
    suffix = ['4883C430','5F','C3']
    positive = ['48895C2440',f'488B59{items:02X}','4889742450','4885DB',None,
        '483913',None,'488B03','3890'+rank,None,f'483953{offsets["arrayBounds"]:02X}',None,
        '8BF2','F7DE','483913',None,'488B03','3890'+rank,None,'48896C2448','4C89742458',
        f'483953{offsets["arrayBounds"]:02X}',None,f'488D6B{offsets["arrayLength"]:02X}','488B6D00',
        '41BE01000000','4438B0'+rank,None,'4C8B742458','2BEF','3BF5','488B6C2448',None,
        '488B03','33D2','486388'+stride,'8BC1','0FAFC7','4C63C0','4863C6','480FAFC8',
        f'4883C1{offsets["arrayData"]:02X}','4803CB',None,'488B742450','488B5C2440',None]
    for key, expected in (('empty',prefix+suffix),('positive',prefix+positive+suffix)):
        proof = programs[key]
        validate_program(image,proof,fail=fail,extra_opcodes=LOCAL_OPS)
        if proof['program'][0][0] != entry or len(proof['program']) != len(expected):
            fail('list-reset-called-body','complete program from the actual caller target',
                 {'entry':entry,'profile':len(expected),'actual':proof['program'][:1],'count':len(proof['program'])})
        for n, (actual,wanted) in enumerate(zip(proof['program'],expected,strict=True)):
            if wanted is not None and actual[1] != wanted:
                fail('list-reset-owned-transfer',{'position':n,'bytes':wanted},actual)
        guards = [(7,b'\x7f',key=='positive')]
        if key == 'positive':
            guards += [(n,opcode,False) for n,opcode in (
                (12,b'\x0f\x84'),(14,b'\x0f\x84'),(17,b'\x0f\x86'),(19,b'\x0f\x85'),
                (23,b'\x0f\x84'),(26,b'\x76'),(30,b'\x0f\x85'),(35,b'\x0f\x87'),(40,b'\x0f\x8f'))]
        for n, opcode, taken in guards:
            at, raw_hex = proof['program'][n]; raw = bytes.fromhex(raw_hex)
            if (raw[:len(opcode)] != opcode
                    or proof['program'][n+1][0] != (_target(at,raw) if taken else at+len(raw))):
                fail('list-reset-selected-guard',{'position':n,'taken':taken},proof['program'][n:n+2])
    rows = programs['positive']['program']; at, raw_hex = rows[51]; raw = bytes.fromhex(raw_hex)
    if len(raw) != 5 or raw[0] != 0xe8:
        fail('list-reset-span-call','one actual relative span helper',rows[51])
    if rows[:8] != programs['empty']['program'][:8] or rows[55:] != programs['empty']['program'][8:]:
        fail('list-reset-common-prefix-and-return','same count write/version increment and epilogue',rows)
    return {'calledEntryRva':entry,'sameCallerIndexOffset':count,'versionOffset':version,
        'indexWriteBits':32,'indexWrittenValue':0,'versionDeltaModulo32':1,
        'indexWrittenBeforePositiveBranch':True,'nonpositiveCountReturnsWithoutCall':True,
        'positiveSpanCall':{'targetRva':_target(at,raw),'destination':'items + arrayDataOffset',
            'arrayDataOffset':offsets['arrayData'],'fillValue':0,
            'length':'sign_extend_int32(oldCount * classStrideInt32)',
            'selectedArrayGuards':['nonnull array/class','class byte == 1','null bounds',
                'signed_int32(int32(arrayLength) - oldCount) >= 0'],
            'calleeEffects':'unresolved'},
        'namedManagedBodyParity':'unresolved','positiveListAdmitted':False}

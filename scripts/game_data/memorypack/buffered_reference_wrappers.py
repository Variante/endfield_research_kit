"""Complete selected buffered wrapper-null and constructor transfer programs.

The source null clears the wrapper byref itself. A constructor preserves its
receiver and stores an allocation return into the owned original-instance
field. Runtime invocation, initialized type cells, allocation behavior and the
barrier-disabled state are conditions; these algorithms admit no root/list.
"""
from __future__ import annotations

from typing import Any, Callable
from scripts.game_data.memorypack.reference_conversion_sources import validate_program,_target


def _profile(image: Any, proof: dict, expected: list, *, fail: Callable) -> None:
    validate_program(image,proof,fail=fail)
    rows=proof['program']
    if len(rows)!=len(expected):fail('source-wrapper-profile-size',len(expected),len(rows))
    for n,(row,wanted)in enumerate(zip(rows,expected,strict=True)):
        if wanted is not None and row[1]!=wanted:fail('source-wrapper-owned-transfer',{'position':n,'bytes':wanted},row)


def _branch(rows: list, n: int, opcode: bytes, taken: bool, *, fail: Callable) -> None:
    at,h=rows[n];raw=bytes.fromhex(h)
    if raw[:len(opcode)]!=opcode or rows[n+1][0]!=(_target(at,raw)if taken else at+len(raw)):
        fail('source-wrapper-selected-guard',{'position':n,'opcode':opcode.hex(),'taken':taken},rows[n:n+2])


def _global_zero(row: list, *, fail: Callable) -> int:
    at,h=row;raw=bytes.fromhex(h)
    if len(raw)!=7 or raw[:2]!=b'\x83\x3d'or raw[-1]!=0:
        fail('source-wrapper-global-guard','RIP-relative Int32 comparison with zero',row)
    return at+len(raw)+int.from_bytes(raw[2:6],'little',signed=True)


def validate_fast_reference_barrier(image: Any, proof: dict, *, fail: Callable) -> dict:
    """Actual disabled-barrier complete path copies the address and returns."""
    _profile(image,proof,[None,'4C8BC1',None,'C3'],fail=fail)
    rows=proof['program'];flag=_global_zero(rows[0],fail=fail)
    _branch(rows,2,b'\x74',True,fail=fail)
    return {'entryRva':rows[0][0],'disabledFlagRva':flag,'selectedMemoryWrites':0,
        'selectedCalls':0,'runtimeDisabledStateObserved':False}


def validate_buffered_wrapper_null(image: Any, proof: dict, offsets: dict, barrier: dict,
                                   *, layout: str, fail: Callable) -> dict:
    """One FF byte, four cursor updates, full wrapper clear and complete return."""
    if (set(offsets)!={'currentPtr','bufferLength','advancedCount','consumed'}
            or any(type(v)is not int or not 0<=v<128 for v in offsets.values())
            or len(set(offsets.values()))!=4):
        fail('source-wrapper-reader-layout','four distinct bounded Reader offsets',offsets)
    if layout not in('three-push-tail','one-push-call'):
        fail('source-wrapper-frame-layout','reviewed complete frame layout',layout)
    tail=layout=='three-push-tail'
    prefix=['48895C2420','55','56','57','4883EC20']if tail else ['48895C2410','48896C2418','4889742420','57','4883EC30']
    middle=[None,'488BFA','488BD9',None,f'837B{offsets["bufferLength"]:02X}01',None,
        f'488B43{offsets["currentPtr"]:02X}','0FB630',f'8B6B{offsets["bufferLength"]:02X}','83ED01',None,
        f'48FF43{offsets["currentPtr"]:02X}',f'FF43{offsets["advancedCount"]:02X}',f'FF43{offsets["consumed"]:02X}',
        f'896B{offsets["bufferLength"]:02X}','4080FEFF',None,'488BCF','48C70700000000']
    suffix=['488B5C2458','4883C420','5F','5E','5D',None]+[r[1]for r in barrier['program']]if tail else [None,None,'488B5C2448','488B6C2450','488B742458','4883C430','5F','C3']
    _profile(image,proof,prefix+middle+suffix,fail=fail)
    rows=proof['program'];raw=bytes.fromhex(rows[5][1])
    if len(raw)!=7 or raw[:2]!=b'\x80\x3d'or raw[-1]!=0:
        fail('source-wrapper-initialization-guard','actual byte initialization flag',rows[5])
    for n,opcode in((8,b'\x75'),(10,b'\x7d'),(15,b'\x79'),(21,b'\x0f\x84')):
        _branch(rows,n,opcode,True,fail=fail)
    fast=validate_fast_reference_barrier(image,barrier,fail=fail)
    n=29 if tail else 24;at,h=rows[n];call=bytes.fromhex(h)
    if len(call)!=5 or call[0]!=(0xe9 if tail else 0xe8)or _target(at,call)!=fast['entryRva']:
        fail('source-wrapper-barrier-target','same independently proved physical barrier',rows[n])
    if tail and rows[30:]!=barrier['program']:
        fail('source-wrapper-tail-return','same complete barrier suffix after restored caller frame',rows[30:])
    if not tail:
        at,h=rows[25];jump=bytes.fromhex(h)
        if len(jump)!=2 or jump[0]!=0xeb or _target(at,jump)!=rows[26][0]:
            fail('source-wrapper-null-epilogue','same caller epilogue after barrier normal return',rows[25])
    return {'markerHex':'FF','wireBytes':1,'readerCounterStores':4,'runtimeReferenceBytes':8,
        'nullOutput':'wrapper reference itself','underlyingInstanceWritten':False,'sourceFieldsRead':0,
        'barrierDisabledCondition':True,'completeReturnProved':True}


def validate_wrapper_constructor_transfer(image: Any, proof: dict, allocation: dict, barrier: dict,
                                          *, instance_offset: int, fail: Callable) -> dict:
    """Non-null allocation RAX is stored in the same saved wrapper receiver."""
    if type(instance_offset)is not int or not 0<=instance_offset<128:
        fail('source-wrapper-instance-offset','bounded owned field offset',instance_offset)
    expected=['48895C2410','57','4883EC20',None,'488BF9',None,None,None,'4885C0',None,None,
        f'488947{instance_offset:02X}',None,'488B5C2438','4883C420','5F','C3']
    _profile(image,proof,expected,fail=fail);rows=proof['program']
    raw=bytes.fromhex(rows[3][1])
    if len(raw)!=7 or raw[:2]!=b'\x80\x3d'or raw[-1]!=0:
        fail('source-wrapper-constructor-init','actual byte initialization flag',rows[3])
    _branch(rows,5,b'\x75',True,fail=fail);_branch(rows,9,b'\x74',False,fail=fail);_branch(rows,12,b'\x74',True,fail=fail)
    if rows[6]!=[allocation['instructionRva'],allocation['instructionHex']]or bytes.fromhex(rows[6][1])[:3]!=b'\x48\x8b\x0d':
        fail('source-wrapper-allocation-argument','owned original-type load into allocation RCX',rows[6])
    at,h=rows[7];raw=bytes.fromhex(h)
    if len(raw)!=5 or raw[0]!=0xe8:fail('source-wrapper-allocation-call','actual direct allocation call',rows[7])
    flag=_global_zero(rows[10],fail=fail);fast=validate_fast_reference_barrier(image,barrier,fail=fail)
    if flag!=fast['disabledFlagRva']:fail('source-wrapper-constructor-barrier-flag','same physical disabled barrier flag',flag)
    return {'allocationTargetRva':_target(at,raw),'instanceOffset':instance_offset,'storedBits':64,
        'sameReceiverPreserved':True,'sameNonNullAllocationReturnStored':True,
        'completeReturnProved':True,'allocationEffectsProved':False,'runtimeConstructorInvocationObserved':False}

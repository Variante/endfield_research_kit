"""Complete guarded 32/64-bit Nullable getter programs from original bytes.

Only one raw flag byte and one payload word are given storage meaning. The
caller proves the selected method, closed generic context and failure callee.
Bytes between these reads are unclaimed. A named Nullable field layout, a live
has-value state and child failure effects are not inferred.
"""
from __future__ import annotations

from .context import relative_branch_target


def prove_guarded_nullable_getter(raw: bytes, *, entry_va: int,
                                 expected_failure_target_va: int) -> dict:
    def fail(check):
        raise ValueError('nullable-value-getter.'+check)
    if (not isinstance(raw, bytes) or not 0 < len(raw) <= 64
            or any(type(v) is not int or not 0 < v < 1<<64
                   for v in (entry_va,expected_failure_target_va))
            or entry_va+len(raw) >= 1<<64):
        fail('program')
    if raw[:3] != b'\x48\x83\xec' or len(raw)<9:
        fail('frame-subtraction')
    frame = int.from_bytes(raw[3:4],'little',signed=True)
    if frame<32 or frame%16 != 8:
        fail('aligned-shadow-frame')
    if raw[4:7] != b'\x80\x39\x00' or raw[7] != 0x74:
        fail('raw-zero-guard')
    branch_target = 9+int.from_bytes(raw[8:9],'little',signed=True)
    at=9
    if raw[at:at+3] == b'\x48\x8b\x41':
        width=8;at+=3;zero_extends=False
    elif raw[at:at+2] == b'\x8b\x41':
        width=4;at+=2;zero_extends=True
    else:
        fail('payload-register-width')
    if at>=len(raw):fail('payload-displacement')
    displacement = int.from_bytes(raw[at:at+1],'little',signed=True);at+=1
    if displacement<1:fail('payload-overlaps-flag')
    if raw[at:at+5] != b'\x48\x83\xc4'+bytes([frame])+b'\xc3':
        fail('normal-restore-return')
    normal_return=at+4;at+=5
    if branch_target != at:fail('failure-branch-target')
    if raw[at:at+3] != b'\x33\xc9\xe8' or len(raw)!=at+8 or raw[-1]!=0xcc:
        fail('failure-call-trap-partition')
    failure_call=at+2
    target = relative_branch_target(raw[failure_call:failure_call+5],entry_va+failure_call,
                                   source='nullable getter')
    if target!=expected_failure_target_va:fail('failure-call-target')
    return {'status':'complete-guarded-nullable-word-getter-validated',
            'checkedProgramBytes':len(raw),'checkedInstructions':9,
            'flagRead':{'offset':0,'bytes':1,'zeroSelectsFailure':True},
            'payloadRead':{'offset':displacement,'bytes':width,
                           'returnedRegister':'rax','zeroExtendsToRax':zero_extends},
            'normalReturnOffset':normal_return,'normalReturnStackBalanced':True,
            'failureCallOffset':failure_call,'failureCallTargetVa':target,
            'failureArgumentRcx':0,'trapIfFailureCallReturns':True,
            'ordinaryReturnOnZeroFlagPath':False,'callFrameBytes':frame,
            'explicitDataStores':0,'completeClosedNullableLayoutProved':False,
            'conditions':'Selected entry with valid readable RCX flag and payload ranges. On the failure path the selected callee returns normally or transfers control; its effects are separate.',
            'runtimeExecutionKnown':False}

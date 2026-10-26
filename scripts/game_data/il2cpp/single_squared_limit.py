"""Prove two Single field reads, their product, COMISS and exact JA targets.

This is a byte-program proof. Its caller owns receiver/field identity and the
incoming low xmm0 value. COMISS and JA semantics follow Intel's instruction
reference; floating exceptions and the actual MXCSR remain runtime conditions.
"""
from __future__ import annotations

import hashlib


def prove_single_squared_limit_branch(program: bytes, start_va: int, *, field_offset: int) -> dict:
    """Accept only the complete load/multiply/compare/above-branch window."""
    if (not isinstance(program,bytes) or type(start_va) is not int or not 0<=start_va<1<<64
            or type(field_offset) is not int or not 0<=field_offset<1<<31):
        raise ValueError('single-square-limit.coordinates: bytes and bounded integer coordinates required')
    if field_offset==0:
        operand=b'\x09'
    elif field_offset<=127:
        operand=b'\x49'+field_offset.to_bytes(1,'little')
    else:
        operand=b'\x89'+field_offset.to_bytes(4,'little',signed=True)
    load=b'\xf3\x0f\x10'+operand
    multiply=b'\xf3\x0f\x59'+operand
    compare=b'\x0f\x2f\xc1'
    prefix=load+multiply+compare
    if not program.startswith(prefix):
        raise ValueError(f'single-square-limit.operands: expected={prefix.hex().upper()} actual={program.hex().upper()[:128]}')
    branch=program[len(prefix):]
    if len(branch)==2 and branch[0]==0x77:
        displacement=int.from_bytes(branch[1:],'little',signed=True)
    elif len(branch)==6 and branch[:2]==b'\x0f\x87':
        displacement=int.from_bytes(branch[2:],'little',signed=True)
    else:
        raise ValueError(f'single-square-limit.branch: exact short or near JA required; actual={branch.hex().upper()[:96]}')
    fallthrough=start_va+len(program);target=fallthrough+displacement
    if not 0<=target<1<<64 or not 0<fallthrough<1<<64:
        raise ValueError('single-square-limit.target: instruction end or target exceeds unsigned 64-bit coordinates')
    return {'schema':'endfield.single-squared-limit-branch-proof.v1',
        'programSha256':hashlib.sha256(program).hexdigest().upper(),'programBytes':len(program),
        'startVa':start_va,'endVa':fallthrough,'branchVa':start_va+len(prefix),
        'takenTargetVa':target,'fallthroughVa':fallthrough,'fieldOffset':field_offset,
        'fieldReadBytes':4,'fieldReadCount':2,'fieldBaseRegister':'rcx',
        'limitOperand':'Single(first field read times second field read)',
        'sameEffectiveFieldAddress':True,'squareOfOneValueRequiresStableField':True,
        'comparedInputLowLane':'xmm0','computedLimitLowLane':'xmm1',
        'branchCondition':'CF=0 and ZF=0','comparisonInstruction':'COMISS xmm0,xmm1',
        'orderedGreaterTakesBranch':True,'equalTakesFallthrough':True,
        'orderedLessTakesFallthrough':True,'unorderedTakesFallthroughAfterNormalComparison':True,
        'floatingEnvironmentOrActualValuesObserved':False,'receiverOrNamedFieldIdentityProved':False,
        'evidenceBoundary':'Exact complete instruction window proves raw field-load/product, operand order and JA target/fallthrough. Caller aliases and the named field must be independently joined. A stable field is required to call the two reads one squared value. Unordered fallthrough applies only if COMISS completes normally; floating exceptions and MXCSR are unresolved.'}

"""Complete failure-output block around an independently proved Vector3 zero call."""
from __future__ import annotations

import hashlib


def prove_vector3_failure_output(raw: bytes, entry_va: int, *, zero_callee_va: int,
                                epilogue_va: int, temporary_slot: int,
                                output_pointer_slot: int) -> dict:
    """Prove complete output-buffer copies, XOR AL,AL and exact return branch."""
    if not isinstance(raw,bytes) or any(type(v) is not int or not 0 < v < 1 << 64
            for v in (entry_va,zero_callee_va,epilogue_va)):
        raise ValueError('vector3-failure.coordinates: bytes and positive uint64 addresses required')
    if any(type(v) is not int or not -128 <= v <= 127 for v in (temporary_slot,output_pointer_slot)):
        raise ValueError('vector3-failure.frame-slot: signed-byte offsets required')
    if max(temporary_slot,output_pointer_slot) < min(temporary_slot+12,output_pointer_slot+8):
        raise ValueError('vector3-failure.frame-alias: temporary and pointer slots must not overlap')
    grammar=[(bytes.fromhex('488D4D')+bytes([temporary_slot&255]), 'RCX addresses the zero-return buffer'),
             (None, 'direct call to separately proved zero leaf'),
             (bytes.fromhex('488B4D')+bytes([output_pointer_slot&255]), 'read incoming output pointer into RCX'),
             (bytes.fromhex('F20F1000'), 'read returned buffer first eight bytes into XMM0'),
             (bytes.fromhex('8B5008'), 'read returned buffer last four bytes into EDX'),
             (bytes.fromhex('32C0'), 'clear low return byte AL after both returned-buffer reads'),
             (bytes.fromhex('F20F1101'), 'write first eight bytes through output RCX'),
             (bytes.fromhex('895108'), 'write last four bytes through output RCX+8'),
             (b'', 'unconditional short jump to exact epilogue')]
    if len(raw)!=31 or entry_va+len(raw)>=1 << 64:
        raise ValueError('vector3-failure.program: complete bounded thirty-one-byte block required')
    rows=[];offset=0
    for n,(expected,operation) in enumerate(grammar):
        size=5 if expected is None else 2 if n==8 else len(expected)
        actual=raw[offset:offset+size]
        target=None
        if expected is None:
            target=entry_va+offset+5+int.from_bytes(actual[1:],'little',signed=True)
            if actual[0]!=0xe8 or target!=zero_callee_va:
                raise ValueError('vector3-failure.zero-call: exact selected direct CALL required')
        elif n==8:
            target=entry_va+offset+2+int.from_bytes(actual[1:],'little',signed=True)
            if actual[0]!=0xeb or target!=epilogue_va:
                raise ValueError('vector3-failure.epilogue-branch: exact unconditional short target required')
        elif actual!=expected:
            raise ValueError(f'vector3-failure.instruction: offset={offset} expected={expected.hex()} actual={actual.hex()}')
        row={'offset':offset,'rawHex':actual.hex().upper(),'operation':operation}
        if target is not None:row['targetVa']=target
        rows.append(row);offset+=size
    return {'schema':'endfield.vector3-failure-output-program-proof.v1',
        'programBytes':len(raw),'programSha256':hashlib.sha256(raw).hexdigest().upper(),'program':rows,
        'temporaryFrameSlot':temporary_slot,'outputPointerFrameSlot':output_pointer_slot,
        'returnLowByte':0,'outputCopiedBytes':12,'returnPointerReadBeforeLowByteClear':True,
        'zeroCalleeProvedHere':False,'epilogueProgramProvedHere':False,'runtimeExecutionKnown':False,
        'evidenceBoundary':'Exact failure block calls the selected leaf, copies its returned twelve-byte buffer to the incoming output, clears AL only after reading the returned pointer, and jumps to the exact epilogue. Independent zero/return/frame proofs and valid memory are required; branch selection and executed values are not observed.'}

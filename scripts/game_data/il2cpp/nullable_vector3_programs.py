"""Complete canonical Nullable<Vector3> interface programs, with bounded roles.

These strict byte grammars prove a one-byte tag and a twelve-byte copy at +4
through named interfaces supplied by the caller. They do not substitute open
generic field offsets, certify total closed instance size, follow adjustors,
select live MethodInfo objects or infer a failure helper's effects. The caller
authenticates its NativeImage and exact closed MethodSpec before composition.
"""
from __future__ import annotations

import hashlib

from .context import relative_branch_target


def prove_nullable_vector3_program(raw: bytes, *, operation: str, entry_va: int,
                                  failure_target_va: int | None = None) -> dict:
    """Refuse any changed instruction, branch target or incomplete terminal."""
    if (not isinstance(raw, bytes) or type(entry_va) is not int
            or not 0 < entry_va < (1 << 64) - len(raw)):
        raise ValueError('nullable-vector3.program: original bytes and bounded entry required')
    programs = {
        'constructor': [
            ('F20F1002', 'read input bytes 0..7 into xmm0'),
            ('8B4208', 'read input bytes 8..11 into eax'),
            ('F20F114104', 'copy eight bytes to receiver+4'),
            ('89410C', 'copy four bytes to receiver+12'),
            ('C60101', 'set receiver byte 0 to one'), ('C3', 'return')],
        'has-value': [('0FB601', 'zero-extend receiver byte 0 into eax'), ('C3', 'return')],
        'value-or-default': [
            ('8B420C', 'read receiver bytes 12..15 into eax'),
            ('F20F104204', 'read receiver bytes 4..11 into xmm0'),
            ('F20F1101', 'copy eight bytes to output'),
            ('894108', 'copy four bytes to output+8'),
            ('488BC1', 'return output pointer in rax'), ('C3', 'return')],
        'value': [
            ('4883EC28', 'allocate 40-byte Win64 call frame'),
            ('803A00', 'compare receiver byte 0 with zero'),
            ('7417', 'if zero branch to failure block'),
            ('8B420C', 'read receiver bytes 12..15 into eax'),
            ('F20F104204', 'read receiver bytes 4..11 into xmm0'),
            ('F20F1101', 'copy eight bytes to output'),
            ('894108', 'copy four bytes to output+8'),
            ('488BC1', 'return output pointer in rax'),
            ('4883C428', 'restore 40-byte frame'), ('C3', 'return'),
            ('33C9', 'zero ecx before failure call'), (None, 'call selected failure helper'),
            ('CC', 'int3 after failure helper')],
        'value-or-supplied-default': [
            ('803A00', 'compare receiver byte 0 with zero'),
            ('740A', 'if zero branch to supplied-default read'),
            ('F20F104204', 'read receiver bytes 4..11 into xmm0'),
            ('8B420C', 'read receiver bytes 12..15 into eax'),
            ('EB09', 'jump to shared output block'),
            ('F2410F1000', 'read supplied input bytes 0..7 into xmm0'),
            ('418B4008', 'read supplied input bytes 8..11 into eax'),
            ('F20F1101', 'copy eight bytes to output'),
            ('894108', 'copy four bytes to output+8'),
            ('488BC1', 'return output pointer in rax'), ('C3', 'return')],
    }
    if operation not in programs:
        raise ValueError('nullable-vector3.operation: supported named interface required')
    if operation == 'value':
        if type(failure_target_va) is not int or not 0 < failure_target_va < 1 << 64:
            raise ValueError('nullable-vector3.failure-target: selected helper required')
    elif failure_target_va is not None:
        raise ValueError('nullable-vector3.failure-target: unexpected helper')
    offset = 0
    rows = []
    for literal, meaning in programs[operation]:
        if literal is None:
            expected_length = 5
            current = raw[offset:offset+5]
            if (len(current) != 5 or current[0] != 0xe8
                    or relative_branch_target(current, entry_va+offset,
                        source='Nullable Vector3 failure call') != failure_target_va):
                raise ValueError('nullable-vector3.failure-call: exact selected direct CALL required')
        else:
            expected = bytes.fromhex(literal)
            expected_length = len(expected)
            current = raw[offset:offset+expected_length]
            if current != expected:
                raise ValueError(f'nullable-vector3.instruction: offset={offset} '
                                 f'expected={literal} actual={current.hex().upper()}')
        rows.append({'offset':offset,'rawHex':current.hex().upper(),'operation':meaning})
        offset += expected_length
    if offset != len(raw):
        raise ValueError(f'nullable-vector3.terminal: expectedBytes={offset} actualBytes={len(raw)}')
    if operation == 'value':
        if 9 + int.from_bytes(raw[8:9], 'little', signed=True) != 32:
            raise ValueError('nullable-vector3.guard-join: failure block differs')
    if operation == 'value-or-supplied-default':
        if (5 + int.from_bytes(raw[4:5], 'little', signed=True) != 15
                or 15 + int.from_bytes(raw[14:15], 'little', signed=True) != 24):
            raise ValueError('nullable-vector3.default-join: selected copy/output block differs')
    return {'status':'complete-canonical-nullable-vector3-interface-program-proved',
        'operation':operation,'programBytes':len(raw),'programSha256':hashlib.sha256(raw).hexdigest().upper(),
        'program':rows,'tagByteOffset':0,'copiedValueOffset':4 if operation != 'has-value' else None,
        'copiedValueBytes':12 if operation != 'has-value' else 0,
        'maxReceiverByteTouched':0 if operation == 'has-value' else 15,
        'zeroTagBranchOffset':32 if operation == 'value' else 15 if operation == 'value-or-supplied-default' else None,
        'constructorWritesPaddingBytes':False,'returnedOutputRegister':'rax' if operation not in ('constructor','has-value') else None,
        'completeClosedInstanceSizeOrPrivateFieldOffsetsProved':False,'adjustorEntryProved':False,
        'failureCalleeEffectsProved':False,'runtimeExecutionKnown':False,
        'conditions':['Selected exact closed MethodSpec and original canonical entry',
            'Valid readable receiver and argument memory and writable output when used',
            'Win64 canonical unboxed calling convention and normal memory accesses',
            'Receiver/output/source non-overlap, or equivalent reads-before-writes preservation'],
        'evidenceBoundary':'Exact canonical interface byte/tag/copy behavior. Total closed value size, private field identity, boxed adjustor, live MethodInfo selection and failure-helper effects remain separate obligations.'}

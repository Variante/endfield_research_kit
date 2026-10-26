"""Check explicit Vector3 buffer transfers around two direct Win64 calls.

These byte programs require separately proved subtraction/square callees. They
bind caller buffers and saved output lanes, not a navigation routine's meaning
or a game's executed values. Frame offsets and call targets are supplied by the
selected caller, rather than stored build addresses.
"""
from __future__ import annotations

import hashlib


def _address(value: int, label: str) -> None:
    if type(value) is not int or not 0 < value < 1 << 64:
        raise ValueError(f'vector3-distance.{label}: positive uint64 required')


def _slot(value: int, *, vector: bool) -> bytes:
    upper = 119 if vector else 127
    if type(value) is not int or not -128 <= value <= upper:
        raise ValueError('vector3-distance.frame-slot: bounded signed-byte offset required')
    return bytes([value & 255])


def _program(raw: bytes, entry_va: int, pieces: list[tuple[bytes | int, str]]) -> dict:
    if not isinstance(raw, bytes):
        raise ValueError('vector3-distance.program: bytes required')
    _address(entry_va, 'entry')
    length = sum(len(code) if isinstance(code, bytes) else 5 for code, _ in pieces)
    if len(raw) != length or entry_va + length >= 1 << 64:
        raise ValueError('vector3-distance.program: complete bounded program required')
    instructions = []; offset = 0
    for code, meaning in pieces:
        size = len(code) if isinstance(code, bytes) else 5
        actual = raw[offset:offset + size]
        target = None
        if isinstance(code, bytes):
            if actual != code:
                raise ValueError(f'vector3-distance.instruction: offset={offset} expected={code.hex()} actual={actual.hex()}')
        else:
            _address(code, 'callee')
            if actual[0] != 0xe8:
                raise ValueError(f'vector3-distance.direct-call: offset={offset}')
            target = entry_va + offset + 5 + int.from_bytes(actual[1:], 'little', signed=True)
            if target != code:
                raise ValueError(f'vector3-distance.call-target: offset={offset} expected={code} actual={target}')
        row = {'offset':offset, 'rawHex':actual.hex().upper(), 'operation':meaning}
        if target is not None:
            row['calleeVa'] = target
        instructions.append(row); offset += size
    return {'programBytes':length, 'programSha256':hashlib.sha256(raw).hexdigest().upper(),
            'program':instructions}


def prove_vector3_distance_call_sequence(raw: bytes, entry_va: int, *,
                                        subtraction_va: int, square_va: int,
                                        input_slot: int, result_slot: int,
                                        navigation_slot: int) -> dict:
    """Prove saved navigation bytes, left-minus-right buffers and square input.

    RBX supplies the incoming input pointer. Each Vector3 stack buffer contains
    twelve bytes. The navigation buffer is saved before becoming subtraction's
    output; XMM4 and R9D retain its original 8 + 4 bytes under the callee facts.
    """
    slots = [input_slot, result_slot, navigation_slot]
    for slot in slots:
        _slot(slot, vector=True)
    if any(max(a, b) < min(a + 12, b + 12) for n, a in enumerate(slots) for b in slots[n + 1:]):
        raise ValueError('vector3-distance.frame-alias: three nonoverlapping twelve-byte slots required')
    i, r, n = [_slot(slot, vector=True) for slot in slots]
    iz, rz, nz = [_slot(slot + 8, vector=False) for slot in slots]
    pieces = [
        (bytes.fromhex('F20F1003'), 'read input first eight bytes from RBX into XMM0'),
        (bytes.fromhex('4C8D45') + i, 'right pointer R8 addresses the input copy'),
        (bytes.fromhex('F20F1065') + n, 'save post-navigation first eight bytes in XMM4'),
        (bytes.fromhex('488D55') + r, 'left pointer RDX addresses the navigation copy'),
        (bytes.fromhex('8B4308'), 'read input last four bytes into EAX'),
        (bytes.fromhex('488D4D') + n, 'output pointer RCX addresses the navigation buffer'),
        (bytes.fromhex('448B4D') + nz, 'save post-navigation last four bytes in R9D'),
        (bytes.fromhex('F20F1145') + i, 'store input first eight bytes at right buffer'),
        (bytes.fromhex('F20F1165') + r, 'store saved navigation first eight bytes at left buffer'),
        (bytes.fromhex('8945') + iz, 'store input last four bytes at right buffer'),
        (bytes.fromhex('44894D') + rz, 'store saved navigation last four bytes at left buffer'),
        (subtraction_va, 'call separately proved twelve-byte left-minus-right leaf'),
        (bytes.fromhex('488D4D') + i, 'square input RCX addresses the input-copy buffer'),
        (bytes.fromhex('F20F1018'), 'read subtraction returned buffer first eight bytes into XMM3'),
        (bytes.fromhex('8B4008'), 'read subtraction returned buffer last four bytes into EAX'),
        (bytes.fromhex('F20F115D') + i, 'store difference first eight bytes in square input'),
        (bytes.fromhex('8945') + iz, 'store difference last four bytes in square input'),
        (square_va, 'call separately proved square/sum leaf on the copied difference'),
    ]
    return {**_program(raw, entry_va, pieces),
        'schema':'endfield.vector3-distance-call-sequence-proof.v1',
        'frameSlots':{'inputCopy':input_slot, 'navigationCopy':result_slot,
                      'navigationThenDifference':navigation_slot},
        'navigationSavedBeforeSubtraction':{'firstEightBytes':'xmm4', 'lastFourBytes':'r9d'},
        'differenceOperandOrder':['post-navigation-buffer-bytes', 'input-bytes-read-after-navigation'],
        'squareInput':'complete twelve-byte returned subtraction value',
        'requiredCalleeFacts':{'subtractionReturnsIncomingOutputPointer':True,
                              'subtractionAndSquarePreserveSavedXmm4AndR9':True},
        'calleeProgramsProvedHere':False, 'navigationAlgorithmProved':False,
        'runtimeExecutionKnown':False,
        'evidenceBoundary':'Exact original call-block bytes bind three distinct caller stack buffers, both direct call targets and saved navigation lanes. Leaf results and preserved lanes are conditional on independent complete callee proofs. Valid input/frame memory, actual navigation writes and floating completion remain separate obligations.'}


def prove_vector3_navigation_call_setup(raw: bytes, entry_va: int, *,
                                        navigation_va: int, input_slot: int,
                                        destination_slot: int,
                                        navigation_slot: int) -> dict:
    """Prove complete 8 + 4-byte input copies and the navigation call arguments."""
    slots = [input_slot, destination_slot, navigation_slot]
    for slot in slots:
        _slot(slot, vector=True)
    if any(max(a, b) < min(a + 12, b + 12) for n, a in enumerate(slots) for b in slots[n + 1:]):
        raise ValueError('vector3-distance.frame-alias: three nonoverlapping twelve-byte slots required')
    i, d, n = [_slot(slot, vector=True) for slot in slots]
    iz, dz = [_slot(slot + 8, vector=False) for slot in slots[:2]]
    pieces = [
        (bytes.fromhex('F20F1007'), 'read destination first eight bytes from RDI'),
        (bytes.fromhex('4C8D45') + n, 'third argument R8 addresses the navigation buffer'),
        (bytes.fromhex('8B4708'), 'read destination last four bytes'),
        (bytes.fromhex('488D55') + d, 'second argument RDX addresses the destination copy'),
        (bytes.fromhex('488364242000'), 'clear the fifth-argument qword stack slot'),
        (bytes.fromhex('488D4D') + i, 'first argument RCX addresses the input copy'),
        (bytes.fromhex('F20F1145') + d, 'store destination first eight bytes'),
        (bytes.fromhex('458BCE'), 'fourth argument R9D receives saved R14D'),
        (bytes.fromhex('F20F1003'), 'read input first eight bytes from RBX'),
        (bytes.fromhex('8945') + dz, 'store destination last four bytes'),
        (bytes.fromhex('8B4308'), 'read input last four bytes'),
        (bytes.fromhex('F20F1145') + i, 'store input first eight bytes'),
        (bytes.fromhex('8945') + iz, 'store input last four bytes'),
        (navigation_va, 'call the separately selected navigation entry'),
    ]
    return {**_program(raw, entry_va, pieces),
        'schema':'endfield.vector3-navigation-call-setup-proof.v1',
        'arguments':{'rcx':{'frameSlot':input_slot, 'copiedBytes':12, 'source':'rbx'},
                     'rdx':{'frameSlot':destination_slot, 'copiedBytes':12, 'source':'rdi'},
                     'r8':{'frameSlot':navigation_slot, 'pointerOnly':True},
                     'r9d':{'source':'r14d', 'rawBits':32},
                     'fifthStackQword':{'rspOffset':32, 'value':0}},
        'incomingParameterOwnershipProvedHere':False, 'navigationAlgorithmProved':False,
        'navigationWritesProved':False, 'runtimeExecutionKnown':False,
        'evidenceBoundary':'Exact selected setup copies both twelve-byte values and sets all four register arguments and the zero fifth stack qword before the direct call. Declared parameter identity, saved input-register aliases, output direction and navigation effects require independent evidence.'}


def prove_vector3_saved_output_branch(raw: bytes, entry_va: int, *,
                                      output_pointer_slot: int,
                                      epilogue_va: int) -> dict:
    """Prove a true return and the saved twelve-byte output through a short JMP."""
    _address(entry_va, 'entry'); _address(epilogue_va, 'epilogue')
    slot = _slot(output_pointer_slot, vector=False)
    expected = bytes.fromhex('488B4D') + slot + bytes.fromhex('B001F20F112144894908')
    if not isinstance(raw, bytes) or len(raw) != len(expected) + 2 or raw[:-2] != expected or raw[-2] != 0xeb:
        raise ValueError('vector3-distance.saved-output: complete pointer/true/8+4-byte-store/short-jump program required')
    if entry_va + len(raw) >= 1 << 64:
        raise ValueError('vector3-distance.saved-output: bounded program required')
    target = entry_va + len(raw) + int.from_bytes(raw[-1:], 'little', signed=True)
    if target != epilogue_va:
        raise ValueError(f'vector3-distance.epilogue-target: expected={epilogue_va} actual={target}')
    return {'schema':'endfield.vector3-saved-output-branch-proof.v1',
        'programBytes':len(raw), 'programSha256':hashlib.sha256(raw).hexdigest().upper(),
        'outputPointerFromFrameSlot':output_pointer_slot, 'returnLowByte':1,
        'outputStores':[{'offset':0, 'bytes':8, 'source':'low64-xmm4'},
                        {'offset':8, 'bytes':4, 'source':'low32-r9'}],
        'takenTargetVa':target, 'savedLaneOwnershipProvedHere':False,
        'epilogueProgramProvedHere':False, 'runtimeExecutionKnown':False,
        'evidenceBoundary':'Exact selected success block writes saved raw lanes through the incoming output pointer and sets AL to one before the exact epilogue branch. Saved-lane origin, pointer validity and the epilogue require independent proofs.'}

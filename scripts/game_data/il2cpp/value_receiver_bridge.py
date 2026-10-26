"""Prove complete RCX address returns and matching receiver tail bridges.

Named exports, selected entry points and typed declarations are caller
obligations. These checks prove the original byte programs and their affine
address relation, without assigning a boxing layout from a method name or a
candidate registration table. Pointer validity and nonwrapping addresses are
explicit conditions; no execution or downstream field meaning is inferred.
"""
from __future__ import annotations

import struct

from .integer_addressing import decode_lea_address


def _selection(raw: bytes, entry_va: int) -> None:
    if (not isinstance(raw, bytes) or not 0 < len(raw) <= 32
            or type(entry_va) is not int or not 0 < entry_va < 1 << 64
            or entry_va + len(raw) >= 1 << 64):
        raise ValueError('value-receiver-bridge.program: bounded bytes and nonwrapping entry required')


def _lea_shift(raw: bytes, entry_va: int, destination: str) -> tuple[int, int]:
    decoded = decode_lea_address(raw, 0, entry_va)
    if decoded is None:
        raise ValueError('value-receiver-bridge.lea: complete LEA required')
    row, length = decoded
    fact = row['addressOperation']
    if (fact['destination'] != destination or fact['destinationBits'] != 64
            or fact['base'] != 'rcx' or fact['index'] is not None
            or fact['ripRelative'] or fact['scale'] != 1
            or not 0 < fact['displacement'] <= 1 << 20):
        raise ValueError('value-receiver-bridge.address: positive full-width RCX displacement required')
    return fact['displacement'], length


def prove_rcx_address_return(raw: bytes, *, entry_va: int) -> dict:
    """Check a complete LEA RAX,[RCX+delta]; RET program."""
    _selection(raw, entry_va)
    shift, length = _lea_shift(raw, entry_va, 'rax')
    if raw[length:] != b'\xc3':
        raise ValueError('value-receiver-bridge.return: plain terminal RET and no suffix required')
    return {'status': 'complete-affine-address-return-validated',
            'checkedProgramBytes': len(raw), 'sourceRegister': 'rcx',
            'returnedRegister': 'rax', 'shiftBytes': shift,
            'memoryReads': 0, 'memoryWrites': 0, 'flagsModified': False,
            'conditionalSelection': 'Entered at the selected entry with a valid nonwrapping RCX address.',
            'runtimeExecutionKnown': False}


def prove_rcx_shift_tail_jump(raw: bytes, *, entry_va: int,
                            expected_target_va: int) -> dict:
    """Check one full-width RCX shift followed by a direct terminal JMP."""
    _selection(raw, entry_va)
    if type(expected_target_va) is not int or not 0 < expected_target_va < 1 << 64:
        raise ValueError('value-receiver-bridge.target: positive target address required')
    if raw[:3] in (b'\x48\x83\xc1', b'\x48\x81\xc1'):
        width = 1 if raw[1] == 0x83 else 4
        length = 3 + width
        if len(raw) < length:
            raise ValueError('value-receiver-bridge.add: truncated immediate')
        shift = int.from_bytes(raw[3:length], 'little', signed=True)
        if not 0 < shift <= 1 << 20:
            raise ValueError('value-receiver-bridge.add: positive bounded signed immediate required')
        flags_modified = True
    else:
        shift, length = _lea_shift(raw, entry_va, 'rcx')
        flags_modified = False
    if len(raw) != length + 5 or raw[length] != 0xe9:
        raise ValueError('value-receiver-bridge.jump: exact terminal near JMP required')
    target = entry_va + len(raw) + struct.unpack_from('<i', raw, length + 1)[0]
    if not 0 < target < 1 << 64 or target != expected_target_va:
        raise ValueError('value-receiver-bridge.jump-target: selected direct target differs')
    return {'status': 'complete-affine-receiver-tail-jump-validated',
            'checkedProgramBytes': len(raw), 'receiverRegister': 'rcx',
            'shiftBytes': shift, 'terminalTargetVa': target,
            'otherRegistersUnchanged': True, 'stackUnchanged': True,
            'memoryReads': 0, 'memoryWrites': 0, 'flagsModified': flags_modified,
            'conditionalSelection': 'Entered at the selected entry with a valid nonwrapping RCX address; direct target identity is proved by the caller.',
            'runtimeExecutionKnown': False}


def prove_matched_address_receiver_bridge(return_raw: bytes, *, return_entry_va: int,
                                         bridge_raw: bytes, bridge_entry_va: int,
                                         expected_target_va: int) -> dict:
    """Require identical complete return and tail-call receiver shifts."""
    address_return = prove_rcx_address_return(return_raw, entry_va=return_entry_va)
    tail_bridge = prove_rcx_shift_tail_jump(bridge_raw, entry_va=bridge_entry_va,
                                          expected_target_va=expected_target_va)
    if address_return['shiftBytes'] != tail_bridge['shiftBytes']:
        raise ValueError('value-receiver-bridge.shift-match: return and receiver shifts differ')
    return {'status': 'complete-matched-address-receiver-bridge-validated',
            'shiftBytes': address_return['shiftBytes'],
            'addressReturn': address_return, 'receiverBridge': tail_bridge,
            'registrationTableSchemaProved': False,
            'boxedFieldOwnershipProved': False, 'runtimeExecutionKnown': False}

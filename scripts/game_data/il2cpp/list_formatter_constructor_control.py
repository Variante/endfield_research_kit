"""Complete two-range shared reference-list constructor control.

The native owner authenticates the declared exception ranges. This primitive
checks the conditional indirect call and its ordinary return successor without
assigning semantic names to the anonymous context slots or callee effects.
"""
from __future__ import annotations


def validate_list_formatter_constructor_control(primary: bytes, cold: bytes, *,
        primary_va: int, cold_va: int) -> dict:
    label = 'listFormatterConstructorControl'
    if (not isinstance(primary, bytes) or not isinstance(cold, bytes)
            or any(type(x) is not int or not 0 <= x < 1 << 64 for x in (primary_va, cold_va))):
        raise ValueError(label + '.input-domain')
    if len(primary) != 35 or len(cold) != 23:
        raise ValueError(label + '.complete-range-length')
    if (primary_va + 35 >= 1 << 64 or cold_va + 23 >= 1 << 64
            or max(primary_va, cold_va) < min(primary_va + 35, cold_va + 23)):
        raise ValueError(label + '.disjoint-bounded-ranges')
    if primary[:24] != bytes.fromhex('4883EC28488B4220488B88C0000000488B41384883782000'):
        raise ValueError(label + '.context-read-and-zero-guard')
    if primary[24:26] != b'\x0f\x84':
        raise ValueError(label + '.zero-context-branch')
    if primary_va + 30 + int.from_bytes(primary[26:30], 'little', signed=True) != cold_va:
        raise ValueError(label + '.cold-branch-target')
    if primary[30:] != bytes.fromhex('4883C428C3'):
        raise ValueError(label + '.normal-frame-return')
    if cold[:18] != bytes.fromhex('488B4220488B88C0000000488B4138FF1090'):
        raise ValueError(label + '.cold-context-reread-and-indirect-call')
    if cold[18] != 0xe9 or cold_va + 23 + int.from_bytes(cold[19:], 'little', signed=True) != primary_va + 30:
        raise ValueError(label + '.cold-return-successor')
    return {
        'status': 'complete-shared-list-constructor-control-validated',
        'instructionsChecked': 14,
        'primaryBytesChecked': 35,
        'coldBytesChecked': 23,
        'explicitDataStores': 0,
        'entryReceiverDereferenced': False,
        'guardReadChain': ['entry RDX + 32', 'loaded QWORD + 192', 'loaded QWORD + 56', 'loaded QWORD + 32'],
        'nonzeroGuardReturnsWithoutCall': True,
        'zeroGuardReReadsContextThenCallsSlotZero': True,
        'coldIndirectCallTarget': 'QWORD at the final re-read context pointer',
        'coldCallRcx': 'QWORD loaded at the first re-read context pointer + 192',
        'normalReturnRestoresEntryStack': True,
        'anonymousSlotSemanticsProved': False,
        'indirectCallEffectsProved': False,
        'runtimeExecutionKnown': False,
        'conditions': 'Readable compatible context chain; architectural ordinary control. The cold call must return normally with Win64 stack preservation to reach the restored return. Re-read storage may differ from the initial guard; no stable-context or call-effect claim is implied.'}

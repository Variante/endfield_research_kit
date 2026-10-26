"""Concrete getter entries and complete repeated interface lookup programs.

These are conditional static transfers. Runtime interface tables, provider
results, allocation state and the effects of returning callees remain external.
"""
from __future__ import annotations

from typing import Any, Callable
from scripts.game_data.memorypack.reference_conversion_sources import (
    validate_program, validate_interface_conversion, _target,
)
from scripts.game_data.memorypack.generated_formatter_routes import authenticate


def validate_getter_entry(image: Any, proof: dict, *, kind: str,
                          target_rva: int | None, field_offset: int | None,
                          fail: Callable) -> dict:
    program = proof['program']
    if len(program) != 2:
        fail('original-getter-entry-size', 'complete two-instruction entry', len(program))
    authenticate(image, proof, [None, None], taken=set(), fail=fail)
    first, last = (bytes.fromhex(row[1]) for row in program)
    if kind == 'tail-to-cached-instance':
        if (first != b'\x33\xd2' or len(last) != 5 or last[0] != 0xe9
                or target_rva is None or _target(program[1][0], last) != target_rva):
            fail('original-getter-cache-tail', 'same receiver, null companion and actual cached-instance tail', program)
        return {'sameWrapperReceiver': True, 'companionIsNull': True,
                'stackFrameUnchanged': True, 'tailToCurrentCachedInstanceGetter': True,
                'cachedGetterEffectsOwnedByLifecycle': True, 'directOutputFieldRead': False}
    if kind != 'direct-instance-return' or field_offset is None or not 0 <= field_offset < 128:
        fail('original-getter-entry-kind', 'bounded direct-instance-return or cached-instance tail', kind)
    if first != b'\x48\x8b\x41' + bytes((field_offset,)) or last != b'\xc3':
        fail('original-getter-direct-reference', 'one full reference load and complete return', program)
    return {'sameWrapperReceiver': True, 'stackFrameUnchanged': True,
            'directOutputFieldRead': True, 'fieldOffset': field_offset,
            'fullReferenceReturn': True, 'callerHeapWrites': 0}


def validate_repeated_interface_lookup(image: Any, proof: dict, template: dict, *,
                                       ordinal: int, pairs: list, type_index: int,
                                       getter_rva: int, fail: Callable) -> dict:
    """Prove every failed probe before the actual typed interface and return.

The existing one-miss validator owns the common instruction template and
complete suffix. Its ordinal-one result is not used as the selected ordinal:
the complete expanded path and all earlier metadata pairs are checked here.
"""
    if type(ordinal) is not int or not 1 <= ordinal < len(pairs) <= 65535:
        fail('original-interface-ordinal-range', 'bounded nonzero owned interface ordinal', ordinal)
    if (pairs[ordinal]['typeIndex'] != type_index
            or any(row['typeIndex'] == type_index for row in pairs[:ordinal])
            or sum(row['typeIndex'] == type_index for row in pairs) != 1):
        fail('original-interface-selected-pair', 'one exact typed pair after every earlier nonmatching pair', pairs)
    validate_program(image, proof, fail=fail)
    canonical = template['program']
    expected = canonical[:18] + canonical[18:25] * ordinal + canonical[18:22] + canonical[29:]
    if proof['program'] != expected:
        fail('original-interface-complete-loop', 'zero-start loop increments through every failed probe and complete suffix',
             {'ordinal': ordinal, 'expectedInstructions': len(expected), 'actualInstructions': len(proof['program'])})
    common = validate_interface_conversion(image, template, [getter_rva], fail=fail)
    common.pop('interfaceOrdinal')
    return {**common, 'interfaceOrdinal': ordinal, 'failedProbes': ordinal,
            'successfulProbe': ordinal, 'completeExpandedProgramInstructions': len(expected),
            'allEarlierPairsChecked': True, 'completeCallerReturnProved': True,
            'interfaceMetadataCompatibilityConditional': True, 'liveInterfaceTableObserved': False}

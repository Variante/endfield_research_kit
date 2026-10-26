"""Compose proved scalar caller and selected managed lookup at their call boundary.

The dependencies authenticate both programs. This checks the actual callee,
argument aliases, stack separation, saved registers and result forwarding. No
receiver contents, dispatch state or execution is supplied by this relation.
"""
from __future__ import annotations
from typing import Callable
from scripts.game_data.memorypack import blackboard_number_lookup, closed_scalar_consumers


def _same(row, expected, *, fail, check):
    if row[1] != expected:
        fail(check, expected, row)


def _disp(row, prefix, width, *, fail, check):
    raw = bytes.fromhex(row[1]); op = bytes.fromhex(prefix)
    if len(raw) != len(op) + width or not raw.startswith(op):
        fail(check, prefix + ' plus unsigned displacement', row)
    return int.from_bytes(raw[len(op):], 'little')


def compose(caller: dict, callee: dict, consumer: dict, lookup: dict, *, fail: Callable) -> dict:
    if (caller.get('mode') != closed_scalar_consumers.MODE or callee.get('mode') != blackboard_number_lookup.MODE
            or consumer.get('selectedConcreteConsumerFieldFlowProved') is not True
            or consumer.get('runtimeGenericTemplateOffsetsUsed') is not False):
        fail('composition-dependency-scope', 'proved concrete consumer and complete managed lookup', [consumer, lookup])
    required = ('completeSelectedManagedLookupCfgProved', 'arbitraryLoopProved',
                'lookupPrefixCallbackAndCompleteLoopComposed', 'allSelectedReturnsRestoreSavedRegistersAndFrame',
                'lengthMismatchAndUnequalKeysContinue', 'matchingNonNumericValuesContinue')
    if (not all(lookup.get(k) is True for k in required) or lookup.get('outputWriteBytes') != 8
            or lookup.get('numericConversionPerformed') is not False):
        fail('composition-lookup-scope', required, lookup)
    keyed = consumer['records']['tryKeyed']
    if (keyed.get('completeSelectedReturnProved') is not True or keyed.get('selectorNonzeroCondition') is not True
            or keyed.get('outputWriteBytes') != 8 or keyed.get('lookupDoubleCopiedToOriginalOutput') is not True):
        fail('composition-keyed-scope', 'complete nonzero-selector eight-byte forwarding caller', keyed)
    method = callee['method']
    if caller['numberLookupMethod'] != method or keyed['lookupMethod'] != method:
        fail('composition-callee-identity', method, [caller['numberLookupMethod'], keyed['lookupMethod']])
    rows = caller['records']['tryValue']['keyed']['program']
    if len(rows) != 53:
        fail('composition-caller-size', 53, len(rows))
    for i, h in [(0, '48895C2408'), (1, '4889742410'), (2, '57'), (4, '488BD9'),
                 (5, '498BF0'), (7, '488BFA'), (19, '0F57C0'), (42, '4533C9'), (43, '488BCF')]:
        _same(rows[i], h, fail=fail, check='composition-caller-input-alias')
    frame = _disp(rows[3], '4883EC', 1, fail=fail, check='composition-caller-frame')
    temporary = _disp(rows[20], 'F20F114424', 1, fail=fail, check='composition-temporary-init')
    key = _disp(rows[40], '488B53', 1, fail=fail, check='composition-key-source')
    if key != keyed['keyOffset'] or rows[38][1] != '807B' + f'{keyed["selectorOffset"]:02X}' + '00':
        fail('composition-key-selector-cells', [keyed['keyOffset'], keyed['selectorOffset']], [key, rows[38]])
    if (frame < 32 or frame % 16 or not 32 <= temporary <= frame - 8 or temporary % 8):
        fail('composition-temporary-separation', 'aligned Double wholly beyond shadow area and within caller allocation', [frame, temporary])
    if _disp(rows[41], '4C8D4424', 1, fail=fail, check='composition-temporary-address') != temporary:
        fail('composition-temporary-address', temporary, rows[41])
    raw = bytes.fromhex(rows[44][1])
    if len(raw) != 5 or raw[0] != 0xe8 or rows[44][0] + 5 + int.from_bytes(raw[1:], 'little', signed=True) != method[3]:
        fail('composition-physical-call', method, rows[44])
    if _disp(rows[45], 'F20F104424', 1, fail=fail, check='composition-temporary-result') != temporary:
        fail('composition-temporary-result', temporary, rows[45])
    jump = bytes.fromhex(rows[46][1])
    if len(jump) != 2 or jump[0] != 0xeb or rows[46][0] + 2 + int.from_bytes(jump[1:], 'little', signed=True) != rows[47][0]:
        fail('composition-result-copy-edge', rows[47], rows[46])
    # These complete post-call instructions never write AL or call another body.
    suffix = ['F20F1106', '488B5C24' + f'{frame+16:02X}', '488B7424' + f'{frame+24:02X}',
              '4883C4' + f'{frame:02X}', '5F', 'C3']
    for row, h in zip(rows[47:], suffix, strict=True):
        _same(row, h, fail=fail, check='composition-boolean-output-and-caller-return')
    entry = callee['blocks']['entry']; epilogue = callee['blocks']['epilogue']
    for i, h in [(0, '4056'), (1, '57'), (2, '4155'), (5, '488BF9'), (7, '4D8BE8'), (9, '488BF2')]:
        _same(entry[i], h, fail=fail, check='composition-callee-input-alias')
    nested_frame = _disp(entry[3], '4881EC', 4, fail=fail, check='composition-callee-frame')
    # At the physical call, callee RSP = caller RSP - return slot - pushes - allocation.
    nested_delta = -(8 + 3 * 8 + nested_frame)
    if nested_frame < 32 or nested_frame % 16:
        fail('composition-callee-frame', 'aligned private allocation with Win64 shadow area', nested_frame)
    saved = [(14, '48899C24', 4, 8, 'rbx', 5, '488B9C24'),
             (15, '4889AC24', 4, 8, 'rbp', 4, '488BAC24'),
             (16, '4C89A424', 4, 8, 'r12', 3, '4C8BA424'),
             (18, '4C89B424', 4, 8, 'r14', 2, '4C8BB424'),
             (19, '4C89BC24', 4, 8, 'r15', 1, '4C8BBC24'),
             (20, '0F297424', 1, 16, 'xmm6', 0, '0F287424')]
    writes = []
    for at, store, width, size, register, restore, load in saved:
        offset = _disp(entry[at], store, width, fail=fail, check='composition-callee-saved-register')
        restored = _disp(epilogue[restore], load, width, fail=fail, check='composition-callee-register-restore')
        if offset != restored:
            fail('composition-callee-register-restore', [register, offset], restored)
        writes.append({'kind': 'saved-' + register, 'callerRspRelativeStart': nested_delta + offset, 'bytes': size})
    for at in (8, 10):
        offset = _disp(entry[at], '0F114424', 1, fail=fail, check='composition-callee-pair-init')
        writes.append({'kind': 'pair-init', 'callerRspRelativeStart': nested_delta + offset, 'bytes': 16})
    for at, prefix in [(11, '0F114424'), (14, '0F114C24')]:
        offset = _disp(callee['blocks']['loadPair'][at], prefix, 1, fail=fail, check='composition-callee-pair-copy')
        writes.append({'kind': 'pair-copy', 'callerRspRelativeStart': nested_delta + offset, 'bytes': 16})
    for write in writes:
        a = write['callerRspRelativeStart']; b = a + write['bytes']
        if not (nested_delta <= a < b <= -8 - 3 * 8 or 0 <= a < b <= 32):
            fail('composition-callee-write-ownership', 'callee private allocation or caller-provided shadow area', write)
        if a < temporary + 8 and temporary < b:
            fail('composition-temporary-overlap', [temporary, temporary + 8], write)
    expected_epilogue = ['4881C4' + nested_frame.to_bytes(4, 'little').hex().upper(), '415D', '5F', '5E', 'C3']
    if [r[1] for r in epilogue[6:]] != expected_epilogue:
        fail('composition-callee-push-and-frame-restore', expected_epilogue, epilogue[6:])
    if lookup['inputOriginsProved'] != {'rdi': 'incoming Blackboard rcx', 'rsi': 'incoming key rdx', 'r13': 'incoming double-output address r8'}:
        fail('composition-lookup-input-origins', 'same independently proved arguments', lookup['inputOriginsProved'])
    return {'selectedKeyedConsumerAndManagedLookupComposed': True,
        'actualLookupMethod': method, 'keySourceOffset': key, 'selectorSourceOffset': keyed['selectorOffset'],
        'argumentOrigins': {'rcx': 'incoming Blackboard via saved rdi', 'rdx': 'same scalar stored key',
                            'r8': 'caller temporary Double address', 'r9': 'null companion'},
        'callerStackFrameBytes': frame, 'temporaryCallerRspOffset': temporary,
        'calleeStackAllocationBytes': nested_frame, 'calleeRspRelativeToCallerRsp': nested_delta,
        'calleeNonOutputWrites': writes, 'temporaryDisjointFromShadowAndCalleeFrameProved': True,
        'calleeRestoresCallerOutputAliasAndFrameProved': True, 'outputWriteBytes': 8,
        'postCallAlPreservationProved': True, 'keyedNumericConversionPerformed': False,
        'storedFloat32FallbackPerformed': False,
        'conditionalFoundRelation': 'First equal-length ASCII-folded key with null/empty valueStr: valueDouble bits copied via temporary to original output; AL=true.',
        'conditionalMissingRelation': 'Exhausted coherent list: zero 64-bit bits copied via temporary to original output; AL=false; stored Float32 is not read.',
        'normalManagedLookupConditionsInherited': True,
        'conditions': ['The selected consumer guards and complete selected managed lookup guards complete normally.',
            'Every reached Burst getter returns false ordinarily; its effects preserve the caller/callee frames and stable referents.',
            'Scalar key/selector, list, array, Strings and dispatch referents are coherent and stable where read.',
            'Caller and callee have valid isolated Win64 frames; the final writable output does not alias their active frames.',
            'The stored-field join applies only if deserialization and consumer entry refer to the same scalar with unchanged fields.'],
        'evidenceBoundary': 'conditional', 'actualInputStateOrFoundValueKnown': False,
        'dataInstanceToConsumerInstanceCorrespondenceProved': False, 'publicGetValueEndToEndProved': False,
        'providerSelectionProved': False, 'allDispatchAndFailureEffectsProved': False,
        'runtimeExecutionKnown': False, 'wholeActionAdmitted': False, 'wholeRootAdmitted': False}

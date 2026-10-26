"""Complete carrier resolution control and selected physical pointer flows.

Opaque child results and anonymous cache globals are not concrete sharing or
live MethodInfo evidence. Register/key origins assume ordinary Win64 returns
and stable, valid, disjoint frame, cache, input and output storage.
"""
from __future__ import annotations

from collections import deque

from .backward_copy_instructions import decode_legacy_vector_move
from .integer_addressing import decode_lea_address
from .integer_effects import decode_immediate_memory_store
from .memory_moves import decode_memory_move
from .method_carrier_control import _Grammar
from .method_carrier_instructions import (
    decode_carrier_vector_byte_shift, decode_carrier_vector_transfer)
from .relation_control import transfer


def complete_control(rows, entry):
    by_at = {int(r['va'], 16): r for r in rows}
    if len(by_at) != len(rows) or entry not in by_at:
        raise ValueError('carrierResolution.entry-or-duplicate')
    edges = {}
    calls = []
    returns = []
    for at, row in by_at.items():
        flow = transfer(row)
        kind = flow['kind']
        targets = []
        if kind in ('next', 'conditional', 'call', 'indirectCall'):
            targets.append(at+len(bytes.fromhex(row['bytes'])))
        if kind in ('jump', 'conditional'):
            targets.append(flow['target'])
        if kind in ('call', 'indirectCall'):
            calls.append({'site': at, **flow})
        elif kind == 'return':
            returns.append(at)
        elif kind not in ('next', 'conditional', 'jump'):
            raise ValueError('carrierResolution.unhandled-transfer:'+row['bytes'])
        if any(target not in by_at for target in targets):
            raise ValueError('carrierResolution.local-instruction-boundary:'+row['va'])
        edges[at] = targets
    reached = set()
    pending = [entry]
    while pending:
        at = pending.pop()
        if at in reached:
            continue
        reached.add(at)
        pending.extend(edges[at])
    if reached != set(by_at):
        raise ValueError('carrierResolution.unreachable-owned-instructions')
    states = {entry: (0, None)}
    pending = deque([entry])
    while pending:
        at = pending.popleft()
        row = by_at[at]
        sp, bp = states[at]
        head, _, operands = row['text'].partition(' ')
        destination = operands.split(',')[0]
        if head not in ('cmp', 'test') and destination in ('esp', 'sp', 'spl'):
            raise ValueError('carrierResolution.partial-stack-pointer-write')
        if head == 'push':
            if operands == 'rsp':
                raise ValueError('carrierResolution.push-rsp')
            sp -= 8
        elif head == 'pop':
            if operands == 'rsp':
                raise ValueError('carrierResolution.pop-rsp')
            sp += 8
            if operands == 'rbp':
                bp = None
        elif destination == 'rsp':
            if head in ('add', 'sub') and operands.startswith('rsp, 0x'):
                amount = int(operands.split(', ')[1], 16)
                sp += amount if head == 'add' else -amount
            elif head == 'mov' and operands == 'rsp, rbp' and bp is not None:
                sp = bp
            elif head == 'lea':
                raw = bytes.fromhex(row['bytes'])
                result = decode_lea_address(raw, 0, at)
                fact = result[0]['addressOperation'] if result else {}
                if result is None or result[1] != len(raw) or fact.get('destinationBits') != 64 or fact.get('index') is not None or fact.get('ripRelative'):
                    raise ValueError('carrierResolution.dynamic-stack-address')
                source = sp if fact.get('base') == 'rsp' else bp if fact.get('base') == 'rbp' else None
                if source is None:
                    raise ValueError('carrierResolution.unbound-stack-source')
                sp = source+fact['displacement']
            else:
                raise ValueError('carrierResolution.dynamic-rsp')
        elif destination == 'rbp':
            bp = sp if head == 'mov' and operands == 'rbp, rsp' else None
        elif head not in ('cmp', 'test') and destination in ('ebp', 'bp', 'bpl'):
            bp = None
        kind = transfer(row)['kind']
        if kind in ('call', 'indirectCall') and ((8+sp)%16 or -sp < 32):
            raise ValueError('carrierResolution.call-frame')
        if kind == 'return' and sp != 0:
            raise ValueError('carrierResolution.return-frame')
        for target in edges[at]:
            new = (sp, bp)
            if target in states and states[target] != new:
                raise ValueError('carrierResolution.frame-join')
            if target not in states:
                states[target] = new
                pending.append(target)
    return {'instructions': len(rows), 'reachableInstructions': len(reached),
            'directOrIndirectCalls': calls, 'normalReturnSites': returns,
            'allLocalEdgesOnInstructionBoundaries': True, 'normalCallHomeSpaceAndAlignmentChecked': True,
            'allNormalReturnsRestoreEntryRsp': True, 'calleeEffectsOrTerminationProved': False}


def _memory(g, direction, register, size, receiver, offset):
    row = g.row()
    raw = bytes.fromhex(row['bytes'])
    result = decode_memory_move(raw, 0, int(row['va'], 16))
    if result is None:
        result = decode_carrier_vector_transfer(raw, 0, int(row['va'], 16))
    if result is None:
        result = decode_legacy_vector_move(raw, 0, int(row['va'], 16))
    fact = result[0]['memoryOperation'] if result else {}
    address = fact.get('address', {})
    expected = (direction, register, size, receiver, None, offset, False)
    actual = (fact.get('direction'), fact.get('register'), fact.get('memoryBytes'), address.get('base'),
              address.get('index'), address.get('displacement'), address.get('ripRelative'))
    if result is None or result[1] != len(raw) or actual != expected:
        g.fail('memory-operand', expected, row)


def _global(g, register, size, target):
    row = g.row()
    raw = bytes.fromhex(row['bytes'])
    result = decode_memory_move(raw, 0, int(row['va'], 16))
    fact = result[0]['memoryOperation'] if result else {}
    if result is None or result[1] != len(raw) or (fact.get('direction'), fact.get('register'),
            fact.get('memoryBytes'), fact.get('address', {}).get('absoluteAddress')) != ('load', register, size, target):
        g.fail('global-load', (register, size, target), row)


def _indexed(g, register, receiver, index):
    row = g.row()
    raw = bytes.fromhex(row['bytes'])
    result = decode_memory_move(raw, 0, int(row['va'], 16))
    fact = result[0]['memoryOperation'] if result else {}
    address = fact.get('address', {})
    if result is None or result[1] != len(raw) or (fact.get('direction'), fact.get('register'),
            fact.get('memoryBytes'), address.get('base'), address.get('index'), address.get('scale'),
            address.get('displacement'), address.get('ripRelative')) != ('load', register, 8, receiver, index, 8, 0, False):
        g.fail('indexed-qword-load', (register, receiver, index), row)


def _zero(g, receiver, offset):
    row = g.row()
    raw = bytes.fromhex(row['bytes'])
    result = decode_immediate_memory_store(raw, 0, int(row['va'], 16))
    fact = result[0]['immediateMemoryStoreOperation'] if result else {}
    address = fact.get('destinationAddress', {})
    if result is None or result[1] != len(raw) or (fact.get('memoryWriteBytes'), fact.get('immediateWord'),
            address.get('base'), address.get('index'), address.get('displacement'), address.get('ripRelative')) != (8, 0, receiver, None, offset, False):
        g.fail('zero-qword-store', (receiver, offset), row)


def _project(rows, base, c):
    g = _Grammar(rows, label='carrierResolution.projection')
    layout = c['projectionLayout']
    _memory(g, 'store', 'rbx', 8, 'rsp', layout['savedRbxHome'])
    _global(g, 'r11', 8, base+c['globals']['codeRegistrationCellRva'])
    g.take('movzx ebx, r8b', 'mov r10, rcx')
    _memory(g, 'load', 'eax', 4, 'r11', layout['primaryCount'])
    g.take('cmp dword [rdx], eax')
    g.branch('jae', 'invalid')
    _memory(g, 'load', 'eax', 4, 'r11', layout['invokerCount'])
    g.take('cmp dword [rdx+0x4], eax')
    g.branch('jae', 'invalid')
    g.take('cmp dword [rdx+0x8], -0x1', 'movsxd r9, dword [rdx]')
    _memory(g, 'load', 'rax', 8, 'r11', layout['primaryPointers'])
    _indexed(g, 'r8', 'rax', 'r9')
    g.branch('je', 'reusePrimary')
    g.take('movsxd rcx, dword [rdx+0x8]')
    _memory(g, 'load', 'rax', 8, 'r11', layout['adjustorPointers'])
    _indexed(g, 'r9', 'rax', 'rcx')
    g.branch('jmp', 'publish')
    g.mark('reusePrimary')
    g.take('mov r9, r8')
    g.mark('publish')
    _memory(g, 'load', 'rax', 8, 'r11', layout['invokerPointers'])
    g.take('movsxd rcx, dword [rdx+0x4]')
    _memory(g, 'store', 'r8', 8, 'r10', 0)
    _memory(g, 'store', 'r9', 8, 'r10', 8)
    _memory(g, 'store', 'bl', 1, 'r10', 24)
    _indexed(g, 'rcx', 'rax', 'rcx')
    g.take('mov rax, r10')
    _memory(g, 'store', 'rcx', 8, 'r10', 16)
    _memory(g, 'load', 'rbx', 8, 'rsp', layout['savedRbxHome'])
    g.take('ret')
    g.mark('invalid')
    _memory(g, 'load', 'rbx', 8, 'rsp', layout['savedRbxHome'])
    g.take('xor eax, eax')
    for offset in (0, 8, 16):
        _memory(g, 'store', 'rax', 8, 'rcx', offset)
    _memory(g, 'store', 'al', 1, 'rcx', 24)
    g.take('mov rax, r10', 'ret')
    g.finish()
    return {'primaryAndInvokerIndicesCheckedUnsignedAgainstDwordCounts': True,
            'acceptedIndicesThenSignExtendedForAddressing': True,
            'acceptedIndicesNonnegativeRequiresCountsBelow2Pow31': True,
            'adjustorMinusOneReusesPrimary': True, 'otherAdjustorIndexHasNoLocalBoundsCheck': True,
            'adjustorBoundsRequireIndependentRegistrationRecordValidation': True,
            'outputQwordByteOffsets': [0, 8, 16], 'outputFlagByteOffset': 24,
            'outputBytesWritten': 25, 'outputPaddingBytes25Through31Initialized': False,
            'flagSource': 'only incoming R8b; upper R8 bits ignored',
            'invalidPrimaryOrInvokerWritesThreeZeroQwordsAndZeroFlag': True,
            'bothPathsReturnOriginalRcxOutputPointer': True,
            'globalRegistrationCellStartupBindingOrLiveContentsProved': False}


def _segment(programs, base, c, key):
    span = c['segments'][key]
    rows = [r for r in programs[span['function']] if base+span['startRva'] <= int(r['va'], 16) < base+span['endRva']]
    if not rows or int(rows[0]['va'], 16) != base+span['startRva'] or int(rows[-1]['va'], 16)+len(bytes.fromhex(rows[-1]['bytes'])) != base+span['endRva']:
        raise ValueError('carrierResolution.segment-boundaries:'+key)
    return _Grammar(rows, label='carrierResolution.'+key)


def _normalization(g, base, c, *, second):
    layout = c['selectionLayout']
    context = c['contextQwordOffsets']
    if second:
        _memory(g, 'load', 'rcx', 8, 'r13', layout['methodClassPointer'])
        _memory(g, 'load', 'rdx', 8, 'rdi', context[0])
        _memory(g, 'load', 'rcx', 8, 'rcx', layout['classNormalizationDescriptor'])
    else:
        _memory(g, 'load', 'rcx', 8, 'rdi', context[0])
    first = g.call(base+c['calls']['secondNormalization' if second else 'firstNormalization'])
    _memory(g, 'load', 'rdx' if second else 'rcx', 8, 'rdi', context[1])
    if second:
        _memory(g, 'load', 'rcx', 8, 'r13', layout['methodNormalizationDescriptor'])
    _memory(g, 'store', 'rax', 8, 'rsp', layout['firstResultLocal'])
    second_call = g.call(base+c['calls']['secondNormalization' if second else 'firstNormalization'])
    _global(g, 'rsi', 8, base+c['globals']['tableBeginCellRva'])
    g.take('mov r12, rax')
    row = g.row()
    raw = bytes.fromhex(row['bytes'])
    target = int(row['va'], 16)+len(raw)+int.from_bytes(raw[3:], 'little', signed=True)
    if len(raw) != 7 or raw[:3] != b'\x48\x39\x35' or target != base+c['globals']['tableEndCellRva']:
        g.fail('fresh-table-end-compare', base+c['globals']['tableEndCellRva'], row)
    _memory(g, 'store', 'rax', 8, 'rsp', layout['secondResultLocal'])
    g.branch('je')
    g.finish()
    return {'callSitesRva': [int(r['va'], 16)-base for r in (first, second_call)],
            'inputContextQwordOffsets': context, 'resultLocalOffsets': [layout['firstResultLocal'], layout['secondResultLocal']],
            'secondResultAlsoSavedInR12': True,
            'classAndMethodDescriptorsRead': second, 'childReturnTypesOrValuesProved': False}


def _selector(programs, base, c):
    normal_one = _normalization(_segment(programs, base, c, 'firstNormalization'), base, c, second=False)
    normal_two = _normalization(_segment(programs, base, c, 'secondNormalization'), base, c, second=True)
    layout = c['selectionLayout']
    g = _segment(programs, base, c, 'originalHitProjection')
    _memory(g, 'load', 'rdx', 8, 'rdx', layout['tableValuePointer'])
    g.take('xor r8d, r8d', 'mov rcx, rbx')
    original = g.call(base+c['calls']['projection'])
    g.take('mov rax, rbx')
    g.branch('jmp')
    g.finish()
    g = _segment(programs, base, c, 'normalizedHitProjection')
    g.take('xor r8d, r8d')
    _memory(g, 'load', 'rdx', 8, 'rdx', layout['tableValuePointer'])
    _memory(g, 'load', 'rcx', 8, 'rsp', layout['outputPointerHome'])
    normalized = g.call(base+c['calls']['projection'])
    _memory(g, 'load', 'rax', 8, 'rsp', layout['outputPointerHome'])
    _memory(g, 'load', 'rbx', 8, 'rsp', layout['savedRbxHome'])
    g.take(f'add rsp, 0x{layout["localFrameBytes"]:x}', 'pop r15', 'pop r14', 'pop r13',
           'pop r12', 'pop rdi', 'pop rsi', 'pop rbp', 'ret')
    g.finish()
    g = _segment(programs, base, c, 'lastHitMode')
    g.take('mov r8b, 0x1')
    tail = g.branch('jmp')
    destination = c['segments']['normalizedHitProjection']['startRva']+len(bytes.fromhex(
        next(r['bytes'] for r in programs['selection'] if int(r['va'], 16) == base+c['segments']['normalizedHitProjection']['startRva'])))
    if tail['target'] != base+destination:
        g.fail('last-hit-shared-projection-join', base+destination, tail)
    g.finish()
    g = _segment(programs, base, c, 'allMissOutput')
    _memory(g, 'load', 'rbx', 8, 'rsp', layout['outputPointerHome'])
    g.take('xor eax, eax')
    for offset in (0, 8, 16):
        _zero(g, 'rbx', offset)
    _memory(g, 'store', 'rax', 8, 'rbx', 24)
    g.branch('jmp')
    g.finish()
    return {'firstNormalization': normal_one, 'secondNormalization': normal_two,
            'originalAndFirstNormalizedHitsPassLowFlagZero': True,
            'lastNormalizedHitPassesLowFlagOneOnly': True,
            'lastHitUpperR8BitsProved': False, 'projectionCallSitesRva': [int(r['va'], 16)-base for r in (original, normalized)],
            'lastHitJoinsSameProjectionCall': True, 'allMissWritesFourZeroQwords': True,
            'allMissOutputBytesWritten': 32, 'normalizationHasSelectedConcreteGenericArguments': False,
            'threeLookupPassesOrCacheContentsSemanticallyProved': False}


def _address(g, register, receiver, offset, *, absolute=None):
    row = g.row()
    raw = bytes.fromhex(row['bytes'])
    result = decode_lea_address(raw, 0, int(row['va'], 16))
    fact = result[0]['addressOperation'] if result else {}
    expected = (register, 64, receiver, None, offset, absolute is not None)
    actual = (fact.get('destination'), fact.get('destinationBits'), fact.get('base'),
              fact.get('index'), fact.get('displacement'), fact.get('ripRelative'))
    # A RIP-relative displacement changes when the instruction is rebased.
    if absolute is not None:
        expected = (register, 64, None, None, True, absolute)
        actual = (fact.get('destination'), fact.get('destinationBits'), fact.get('base'),
                  fact.get('index'), fact.get('ripRelative'), fact.get('absoluteAddress'))
    if result is None or result[1] != len(raw) or actual != expected:
        g.fail('pointer-address', expected, row)


def _lane(g, source, destination, bits):
    row = g.row()
    raw = bytes.fromhex(row['bytes'])
    result = decode_carrier_vector_transfer(raw, 0, int(row['va'], 16))
    fact = result[0].get('vectorLaneTransferOperation', {}) if result else {}
    expected = (source, destination, bits, True, bits == 32, False)
    actual = (fact.get('sourceRegister'), fact.get('destinationRegister'), fact.get('sourceLowBits'),
              fact.get('destinationIsGeneralRegister'), fact.get('zeroExtendsGp32To64'), fact.get('writesFlags'))
    if result is None or result[1] != len(raw) or actual != expected:
        g.fail('vector-to-gp-lane', expected, row)


def _carrier(programs, base, c):
    """Check the caller's complete selected transfer and fresh flag-update slice.

    The incoming carrier, method and destination registers are slice inputs.
    Child calls have opaque side effects; later memory reads are fresh reads,
    not claims that those calls preserve the destination's fields.
    """
    g = _segment(programs, base, c, 'carrierOutputTransfer')
    layout = c['carrierLayout']
    _address(g, 'r8', 'r12', layout['contextInCarrier'])
    g.take('mov rdx, r13')
    _address(g, 'rcx', 'rbp', layout['outputLocalFromRbp'])
    selected = g.call(base+c['functions']['selection']['entryRva'])
    _memory(g, 'load', 'xmm1', 16, 'rax', 0)
    _memory(g, 'load', 'xmm2', 16, 'rax', 16)
    _memory(g, 'store', 'xmm2', 16, 'rbp', layout['savedTailFromRbp'])
    _memory(g, 'load', 'xmm0', 8, 'rax', 8)
    _memory(g, 'store', 'xmm0', 8, 'rdi', 8)
    _lane(g, 'xmm1', 'rax', 64)
    _memory(g, 'store', 'rax', 8, 'rdi', 0)
    g.take('test rax, rax')
    g.branch('je', 'missingPrimary')
    _memory(g, 'store', 'xmm2', 8, 'rdi', 16)
    g.branch('jmp', 'readFlag')
    g.mark('missingPrimary')
    _address(g, 'rax', None, None, absolute=base+c['globals']['missingPrimaryFallbackRva'])
    _memory(g, 'store', 'rax', 8, 'rdi', 16)
    g.take(f'test byte [rdi+0x{layout["sourceFlags"]:x}], 0x10')
    g.branch('jne', 'readFlag')
    g.take('mov rcx, rdi')
    first_fallback = g.call(base+c['calls']['missingPrimaryAdapter'])
    _memory(g, 'store', 'rax', 8, 'rdi', 8)
    _memory(g, 'load', 'xmm2', 16, 'rbp', layout['savedTailFromRbp'])
    g.mark('readFlag')
    row = g.row()
    raw = bytes.fromhex(row['bytes'])
    shifted = decode_carrier_vector_byte_shift(raw, 0, int(row['va'], 16))
    fact = shifted[0]['vectorByteShiftOperation'] if shifted else {}
    if shifted is None or shifted[1] != len(raw) or (
            fact.get('register'), fact.get('effectiveByteCount'), fact.get('zeroFillsHighBits')) != ('xmm2', 8, True):
        g.fail('flag-lane-shift', ('xmm2', 8, True), row)
    _lane(g, 'xmm2', 'eax', 32)
    g.take('test al, al')
    g.branch('je', 'clearBit8')
    _memory(g, 'load', 'rcx', 8, 'r12', 0)
    predicate = g.call(base+c['calls']['methodFlagPredicate'])
    g.take('test al, al')
    g.branch('je', 'clearBit8')
    g.take('mov cl, 0x8')
    g.branch('jmp', 'writeBit8')
    g.mark('clearBit8')
    g.take('xor cl, cl')
    g.mark('writeBit8')
    g.take(f'movzx eax, byte [rdi+0x{layout["destinationFlags"]:x}]', 'and al, 0xf7', 'or al, cl')
    _memory(g, 'store', 'al', 1, 'rdi', layout['destinationFlags'])
    g.take('test al, 0x8')
    g.branch('jne', 'setBit16')
    g.take(f'test byte [rdi+0x{layout["sourceFlags"]:x}], 0x10')
    g.branch('je', 'clearBit16')
    g.take('cmp qword [rdi], 0x0')
    g.branch('je', 'setBit16')
    g.mark('clearBit16')
    g.take('xor cl, cl')
    g.branch('jmp', 'writeBit16')
    g.mark('setBit16')
    g.take('mov cl, 0x10')
    g.mark('writeBit16')
    g.take('and al, 0xef', 'or al, cl')
    _memory(g, 'store', 'al', 1, 'rdi', layout['destinationFlags'])
    row = g.row()
    step = row.get('memoryStepOperation', {})
    if (step.get('operation'), step.get('bits'), step.get('locked'),
            step.get('destinationAddress', {}).get('absoluteAddress')) != (
            'inc', 64, True, base+c['globals']['creationCounterRva']):
        g.fail('locked-counter', 'current QWORD global LOCK INC', row)
    row = g.row()
    compare = row.get('memoryImmediateComparisonOperation', {})
    if (compare.get('bits'), compare.get('immediateValue'),
            compare.get('sourceAddress', {}).get('absoluteAddress')) != (
            64, 0, base+c['globals']['extendedPointerGateRva']):
        g.fail('fresh-extended-pointer-gate', 'current QWORD global compare with zero', row)
    g.branch('je', 'extendedDone')
    g.take(f'test byte [rdi+0x{layout["destinationFlags"]:x}], 0x8')
    g.branch('je', 'useStoredPointer')
    g.take(f'test byte [rdi+0x{layout["sourceFlags"]:x}], 0x10')
    g.branch('jne', 'useStoredPointer')
    g.take('mov rcx, rdi')
    second_fallback = g.call(base+c['calls']['missingPrimaryAdapter'])
    g.branch('jmp', 'writeExtended')
    g.mark('useStoredPointer')
    _memory(g, 'load', 'rax', 8, 'rdi', 8)
    g.mark('writeExtended')
    _memory(g, 'store', 'rax', 8, 'rdi', layout['extendedPointer'])
    g.mark('extendedDone')
    g.finish()
    return {'checkedInstructions': len(g.rows), 'selectionCallSiteRva': int(selected['va'], 16)-base,
            'sliceInputs': {'r12': 'current carrier', 'r13': 'method pointer', 'rdi': 'destination storage'},
            'contextAddressFromCarrier': layout['contextInCarrier'],
            'outputLocalFromRbp': layout['outputLocalFromRbp'],
            'aggregateReadBytes': 32, 'qwordInitialDestinationOffsets': [0, 8, 16],
            'nonzeroPrimaryCopiesThirdQword': True,
            'zeroPrimaryWritesStaticFallbackAt16': True,
            'zeroPrimaryAndFreshSourceBit16ClearReplacesOffset8WithOpaqueAdapterResult': True,
            'opaqueAdapterCallSitesRva': [int(r['va'], 16)-base for r in (first_fallback, second_fallback)],
            'tailVectorSavedAndRestoredAcrossFirstAdapterCall': True,
            'flagDecisionUsesOnlyAggregateByte24': True,
            'paddingBytes25Through31ReadButNotUsedByFlagPredicate': True,
            'bit8ReplacedWithAggregateFlagNonzeroAndOpaquePredicateLowByteNonzero': True,
            'bit16ReplacedWithBit8OrFreshSourceBit16AndFreshPrimaryQwordZero': True,
            'flagUpdateByteOffset': layout['destinationFlags'],
            'lockedQwordCounterIncrementChecked': True,
            'conditionalExtendedPointerOffset': layout['extendedPointer'],
            'extendedPointerIsFreshStoredOffset8OrOpaqueAdapterResult': True,
            'opaqueChildrenPreserveDestinationFields': False,
            'wholeMethodCreationOrCacheInsertionSemanticsProved': False}


def validate_carrier_resolution(programs, *, image_base, contract):
    if set(programs) != {'miss', 'selection', 'projection'}:
        raise ValueError('carrierResolution.function-set')
    if contract['calls']['projection'] != contract['functions']['projection']['entryRva']:
        raise ValueError('carrierResolution.projection-target-join')
    controls = {key: complete_control(rows, image_base+contract['functions'][key]['entryRva'])
                for key, rows in programs.items()}
    projection = _project(programs['projection'], image_base, contract)
    selector = _selector(programs, image_base, contract)
    carrier = _carrier(programs, image_base, contract)
    return {'completeControls': controls, 'pointerProjection': projection, 'selectedSelectorArgumentFlow': selector,
            'carrierOutputTransfer': carrier,
            'distinctCompleteInstructions': sum(len(rows) for rows in programs.values()),
            'concreteGenericSharingSelected': False, 'runtimeMethodInfoOrProviderObserved': False,
            'runtimeExecutionKnown': False}

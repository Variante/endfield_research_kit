"""Complete selected anonymous selector/field adapter control.

The selector remains an anonymous DWORD read through the incoming pointer.
This proves local field/argument/normal-return transfers, not a class identity,
an interface meaning, valid receiver storage or effects of the fallback call.
"""
from __future__ import annotations

import hashlib
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar
from scripts.game_data.il2cpp.memory_moves import decode_memory_move
from scripts.game_data.il2cpp.relation_control import transfer, explicit_memory_effect
from scripts.game_data.il2cpp.relation_import_control import _graph
from scripts.game_data.il2cpp.class_ancestry_control import _frame

LABEL = 'contextAdapterControl'
DWORD_MASK = (1 << 32) - 1


def _take(g, text, raw):
    row = g.take(text)
    if bytes.fromhex(row['bytes']) != raw:
        g.fail('instruction-encoding', raw.hex(), row)
    return row


def _load(g, register, bits, receiver, *, displacement=None):
    row = g.row(); raw = bytes.fromhex(row['bytes'])
    decoded = decode_memory_move(raw, 0, int(row['va'], 16))
    if decoded is None or decoded[1] != len(raw):
        g.fail('complete-load', (register, receiver, bits), row)
    fact = decoded[0]['memoryOperation']; address = fact['address']
    expected = ('load', register, bits, bits//8, receiver, None, 1, False, 64)
    actual = (fact['direction'], fact['register'], fact['registerBits'],
              fact['memoryBytes'], address['base'], address['index'],
              address['scale'], address['ripRelative'], address['addressBits'])
    if actual != expected or row['text'] != decoded[0]['text']:
        g.fail('physical-load', expected, row)
    if displacement is not None and address['displacement'] != displacement:
        g.fail('load-displacement', displacement, address)
    if bits == 32 and fact['upperRegisterEffect'] != 'zero upper 32 bits':
        g.fail('selector-zero-extension', 'zero upper 32 bits', fact)
    return {'siteVa': int(row['va'], 16), 'displacement': address['displacement'],
            'memoryBytes': bits//8, 'destinationRegister': register}


def _arithmetic(g, operation, *, full_immediate):
    row = g.row(); raw = bytes.fromhex(row['bytes'])
    opcode = 0x3d if operation == 'cmp' else 0x2d
    modrm = 0xf8 if operation == 'cmp' else 0xe8
    if full_immediate and len(raw) == 5 and raw[0] == opcode:
        immediate = int.from_bytes(raw[1:], 'little')
    elif not full_immediate and len(raw) == 3 and raw[:2] == bytes((0x83, modrm)) and raw[2] < 0x80:
        immediate = raw[2]
    else:
        g.fail('dword-arithmetic-encoding', (operation, full_immediate), row)
    if row['text'] != f'{operation} eax, 0x{immediate:x}':
        g.fail('dword-arithmetic-decoding', (operation, immediate), row)
    return immediate


def _partition(rows, windows, base, entry_rva):
    if len(windows) != 2 or len({w['startRva'] for w in windows}) != 2:
        raise ValueError(LABEL + '.two-owned-fragments-required')
    ordered = sorted(windows, key=lambda w: w['startRva'])
    if ordered[0]['endRva'] > ordered[1]['startRva']:
        raise ValueError(LABEL + '.overlapping-owned-fragments')
    starts = [int(row['va'], 16) for row in rows]
    if len(set(starts)) != len(starts):
        raise ValueError(LABEL + '.duplicate-instruction-boundary')
    grouped = {}; assigned = set()
    for window in windows:
        start = base + window['startRva']; end = base + window['endRva']
        raw = bytes.fromhex(window['rawHex'])
        if end <= start or len(raw) != end-start or hashlib.sha256(raw).hexdigest().upper() != window['sha256'].upper():
            raise ValueError(LABEL + '.owned-window-bytes-or-hash')
        group = sorted((row for row in rows if start <= int(row['va'], 16) < end), key=lambda row: int(row['va'], 16))
        at = start
        for row in group:
            value = bytes.fromhex(row['bytes'])
            if not value or int(row['va'], 16) != at or raw[at-start:at-start+len(value)] != value:
                raise ValueError(LABEL + '.owned-instruction-partition')
            at += len(value); assigned.add(int(row['va'], 16))
        if at != end:
            raise ValueError(LABEL + '.uncovered-owned-window-tail')
        grouped[window['startRva']] = group
    if assigned != set(starts) or entry_rva not in grouped:
        raise ValueError(LABEL + '.outside-instruction-or-entry')
    primary = grouped.pop(entry_rva)
    return primary, next(iter(grouped.values()))


def prove_context_adapter_control(rows, windows, base, entry_rva):
    """Prove every owned instruction of the selected two-fragment grammar."""
    primary, cold = _partition(rows, windows, base, entry_rva)
    main = ProgramGrammar(primary, label=LABEL + '.primary')
    tail = ProgramGrammar(cold, label=LABEL + '.cold')
    main.labels = tail.labels = {}
    row = main.row(); raw = bytes.fromhex(row['bytes'])
    if len(raw) != 4 or raw[:3] != b'\x48\x83\xec' or not 32 <= raw[3] < 0x80:
        main.fail('frame-allocation', 'positive SUB RSP imm8 with shadow space', row)
    frame = raw[3]
    if row['text'] != f'sub rsp, 0x{frame:x}' or (8-frame) % 16:
        main.fail('frame-alignment', 'aligned ordinary Win64 call frame', row)
    receiver = _load(main, 'rax', 64, 'rcx', displacement=0)
    selector = _load(main, 'eax', 32, 'rax')
    comparison = _arithmetic(main, 'cmp', full_immediate=True)
    main.branch('je', 'comparisonField')
    first = _arithmetic(main, 'sub', full_immediate=True)
    main.branch('je', 'firstSubtractField')
    second = _arithmetic(main, 'sub', full_immediate=True)
    main.branch('je', 'secondSubtractField')
    third = _arithmetic(main, 'sub', full_immediate=False)
    main.branch('jne', 'coldEntry')
    fields = {'thirdSubtractField': _load(main, 'rax', 64, 'rcx')}
    def restore(g):
        _take(g, f'add rsp, 0x{frame:x}', b'\x48\x83\xc4' + bytes((frame,)))
        return int(_take(g, 'ret', b'\xc3')['va'], 16)
    returns = {'thirdSubtractField': restore(main)}
    main.mark('comparisonField'); fields['comparisonField'] = _load(main, 'rax', 64, 'rcx')
    main.mark('sharedRestore'); returns['comparisonField'] = restore(main)
    main.mark('secondSubtractField'); fields['secondSubtractField'] = _load(main, 'rax', 64, 'rcx')
    returns['secondSubtractField'] = restore(main)
    main.mark('firstSubtractField'); fields['firstSubtractField'] = _load(main, 'rax', 64, 'rcx')
    returns['firstSubtractField'] = restore(main)
    tail.mark('coldEntry'); cold_comparison = _arithmetic(tail, 'cmp', full_immediate=False)
    tail.branch('je', 'coldField')
    argument_move = _take(tail, 'mov r8, rcx', b'\x4c\x8b\xc1')
    call = tail.row(); call_fact = transfer(call)
    if call_fact['kind'] != 'call' or call['text'] != f'call 0x{call_fact["target"]:x}':
        tail.fail('direct-fallback-call', 'complete E8 direct call', call)
    if any(base+w['startRva'] <= call_fact['target'] < base+w['endRva'] for w in windows):
        tail.fail('fallback-call-outside-owned-body', 'external callee', call)
    _take(tail, 'nop', b'\x90'); tail.branch('jmp', 'sharedRestore')
    tail.mark('coldField'); fields['coldField'] = _load(tail, 'rax', 64, 'rcx')
    tail.branch('jmp', 'sharedRestore')
    main.finish(); tail.finish()
    values = {'comparisonField': comparison, 'firstSubtractField': first,
              'secondSubtractField': (first+second) & DWORD_MASK,
              'thirdSubtractField': (first+second+third) & DWORD_MASK,
              'coldField': (first+second+third+cold_comparison) & DWORD_MASK}
    if len(set(values.values())) != len(values):
        raise ValueError(LABEL + '.colliding-selector-cases')
    ordered = sorted(rows, key=lambda row: int(row['va'], 16))
    try:
        edges = _graph(ordered, {'tables': []}, base)
        frames = _frame(ordered, edges, base+entry_rva)
    except ValueError as error:
        raise ValueError(LABEL + '.complete-cfg-or-normal-frame: ' + str(error)) from error
    if any(explicit_memory_effect(row) is not None for row in ordered):
        raise ValueError(LABEL + '.unreviewed-explicit-memory-store')
    cases = [{'selectorWord': value, 'returnKind': 'fresh-QWORD-input-field',
              'inputByteOffset': fields[role]['displacement'],
              'loadRva': fields[role]['siteVa']-base,
              'returnRva': returns.get(role, returns['comparisonField'])-base}
             for role, value in values.items()]
    return {'completeOwnedControlProved': True, 'checkedInstructions': len(ordered),
            'ownedBytes': sum(w['endRva']-w['startRva'] for w in windows),
            'localBranches': sum(transfer(row)['kind'] in ('conditional', 'jump') for row in ordered),
            'checkedFrameInstructionSites': len(frames), 'frameBytes': frame,
            'normalReturnFrameRestored': True, 'allOwnedInstructionsStaticallyReachable': True,
            'unconditionalInputReads': [{'receiver': 'incoming RCX', 'byteOffset': 0, 'memoryBytes': 8, 'siteRva': receiver['siteVa']-base},
                {'receiver': 'fresh QWORD loaded from incoming RCX', 'byteOffset': selector['displacement'], 'memoryBytes': 4, 'siteRva': selector['siteVa']-base}],
            'selectorArithmeticBits': 32, 'selectorSubtractions': [first, second, third],
            'selectorSubtractionsWrapModulo32': True, 'selectorWritesZeroExtendRax': True,
            'fiveCasesDistinct': True, 'selectorCases': cases,
            'fallback': {'selectorWords': 'every DWORD except the five listed cases',
                'callRva': int(call['va'], 16)-base, 'targetRva': call_fact['target']-base,
                'argumentMoveRva': int(argument_move['va'], 16)-base,
                'rcx': 'original incoming RCX', 'r8': 'original incoming RCX',
                'rdxAndR9': 'incoming physical values, untouched by the local prefix; meaning unresolved',
                'raxAtCall': 'zero-extended DWORD (selector minus all three subtractions modulo 2^32)',
                'normalResult': 'fresh normal child RAX forwarded to the common RET',
                'returnRva': returns['comparisonField']-base,
                'childTerminationOrSideEffectsProved': False},
            'explicitPayloadStoreInstructions': 0,
            'implicitCallStackWriteAndReturnStackRead': True,
            'totalMemoryWritesProvedAbsent': False, 'inputNullOrCapacityGuardPresent': False,
            'runtimeClassIdentityProved': False, 'runtimeContextIdentityProved': False,
            'selectorSemanticMeaningProved': False, 'wholeConditionExecutionProved': False,
            'wholeRootAdmitted': False,
            'conditions': ['Readable incoming pointer/QWORD/anonymous DWORD and selected QWORD fields.',
                'Ordinary Win64 frame/nonvolatile-register behavior and normal fallback return when that path is selected.',
                'Selected native inputs, complete ownership and original bytes are independently authenticated.']}

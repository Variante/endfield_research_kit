"""Checked zero-member wrapper/header programs with original local edges.

Called lifecycle/allocation routines retain their normal-return and disjoint
source conditions. This proves selected buffered wire framing and caller
output flow, not provider execution, lifecycle effects or target selection.
"""
from __future__ import annotations
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar


def _rip(g, text):
    row = g.pattern(text + r' \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    prefix = {'lea rcx,': '488d0d', 'mov rcx,': '488b0d', 'mov rbx,': '488b1d'}[text]
    raw = bytes.fromhex(row['bytes'])
    if len(raw) != 7 or raw[:3] != bytes.fromhex(prefix): g.fail('rip-operand-width', prefix, row)
    return row


def _exact(g, text, raw_hex):
    row = g.take(text)
    if bytes.fromhex(row['bytes']) != bytes.fromhex(raw_hex): g.fail('operand-encoding', raw_hex, row)
    return row


def _branch(g, name):
    if name in ('je', 'jne', 'jmp', 'ja'): return g.branch(name)
    row = g.row(); raw = bytes.fromhex(row['bytes']); at = int(row['va'], 16)
    code = {'jl': 12, 'js': 8, 'jae': 3}[name]
    if len(raw) == 2 and raw[0] == 0x70 + code: relative = raw[1:]
    elif len(raw) == 6 and raw[:2] == bytes((15, 0x80 + code)): relative = raw[2:]
    else: g.fail('branch-predicate', name, row)
    target = at + len(raw) + int.from_bytes(relative, 'little', signed=True)
    if row['text'] not in (f'{name} 0x{target:x}', f'jcc 0x{target:x}'): g.fail('branch-decoding', hex(target), row)
    return {**row, 'target': target, 'predicate': name}


class Joins:
    def __init__(self, label): self.label = label; self.labels = {}; self.edges = []
    def mark(self, name, g):
        if name in self.labels: g.fail('duplicate-label', 'unique label', name)
        self.labels[name] = int(g.rows[g.cursor]['va'], 16)
    def edge(self, name, row): self.edges.append((name, row))
    def finish(self):
        for name, row in self.edges:
            if row['target'] != self.labels.get(name):
                raise ValueError(f'{self.label}.local-edge:{name}: expected={self.labels.get(name)} actual={row}')
        return [{'name': name, 'targetVA': row['target'], 'predicate': row['predicate']} for name, row in self.edges]


def _ret(g):
    g.take('mov rbx, [rsp+0x30]', 'add rsp, 0x20', 'pop rdi', 'ret')


def _flag(g):
    row = g.pattern(r'cmp \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\], 0x0')
    raw = bytes.fromhex(row['bytes'])
    if len(raw) != 7 or raw[:2] != b'\x80\x3d' or raw[-1] != 0: g.fail('byte-initialization-flag', 'byte CMP zero', row)
    return int(row['va'], 16) + 7 + int.from_bytes(raw[2:6], 'little', signed=True)


def _init(g, count, flag, symbols):
    for _ in range(count): _rip(g, 'lea rcx,'); g.call(symbols['metadataInit'])
    row = g.pattern(r'mov \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\], 0x1'); raw = bytes.fromhex(row['bytes'])
    if (len(raw) != 7 or raw[:2] != b'\xc6\x05' or raw[-1] != 1
            or int(row['va'], 16) + 7 + int.from_bytes(raw[2:6], 'little', signed=True) != flag):
        g.fail('same-byte-initialization-store', flag, row)


def prove_buffered_header(primary, cold, symbols, *, label='objectHeader'):
    g = ProgramGrammar(primary, label=label); c = ProgramGrammar(cold, label=label + '.cold'); j = Joins(label)
    g.take('mov [rsp+0x8], rbx', 'mov [rsp+0x10], rsi', 'push rdi', 'sub rsp, 0x20',
        'cmp [rcx+0x30], 0x1', 'mov rsi, rdx', 'mov rbx, rcx')
    j.edge('refill', _branch(g, 'jl')); j.mark('source', g)
    g.take('mov rax, [rbx+0x50]'); _exact(g, 'movzx ecx, [rax]', '0fb608')
    _exact(g, 'mov [rsi], cl', '880e'); g.take('mov edi, [rbx+0x30]', 'sub edi, 0x1')
    j.edge('advanceFallback', _branch(g, 'js')); j.mark('advance', g)
    for text, raw_hex in (('inc [rbx+0x50]', '48ff4350'), ('inc [rbx+0x40]', 'ff4340'), ('inc [rbx+0x44]', 'ff4344')):
        row = g.take(text)
        if bytes.fromhex(row['bytes']) != bytes.fromhex(raw_hex): g.fail('cursor-width', raw_hex, row)
    g.take('mov [rbx+0x30], edi'); j.mark('result', g)
    _exact(g, 'cmp [rsi], -0x1', '803eff')
    g.take('mov rbx, [rsp+0x30]', 'mov rsi, [rsp+0x38]', 'setne al', 'add rsp, 0x20', 'pop rdi', 'ret')
    g.finish()
    j.mark('refill', c); c.take('xor r8d, r8d', 'mov edx, 0x1'); c.call(symbols['getNextSpan']); c.take('nop')
    j.edge('source', _branch(c, 'jmp'))
    j.mark('advanceFallback', c); c.take('mov edx, 0x1', 'mov rcx, rbx'); c.call(symbols['advanceFallback'])
    c.take('test al, al'); j.edge('result', _branch(c, 'jne')); j.edge('advance', _branch(c, 'jmp')); c.finish()
    return {'completeOriginalHeaderAndColdEdgesChecked': True, 'localJoins': j.finish(),
        'conditionalBufferedSingleByteReadProved': True, 'conditionalSourceAndCountersAdvanceExactlyOneProved': True,
        'conditionalHeaderReturnEqualsByteNotFFProved': True,
        'selection': 'signed available-byte operand >=1; valid stable disjoint source/output/reader/frame; counters and pointer permit one increment without overflow; supported normal entry; selected fast buffer branch',
        'refillOrAdvanceFallbackEffectsProved': False, 'runtimeExecutionObserved': False}


def prove_zero_wrapper_reader(primary, cold, symbols, *, label='zeroWrapper'):
    g = ProgramGrammar(primary, label=label); j = Joins(label)
    g.take('mov [rsp+0x8], rbx', 'push rdi', 'sub rsp, 0x20')
    flag = _flag(g); g.take('mov rbx, rdx', 'mov rdi, rcx')
    inline_init = bytes.fromhex(g.rows[g.cursor]['bytes'])[0] == 0x75
    j.edge('common' if inline_init else 'init', _branch(g, 'jne' if inline_init else 'je'))
    if inline_init: _init(g, 3, flag, symbols)
    j.mark('common', g); g.take('mov rcx, [rbx]'); _exact(g, 'mov [rsp+0x38], 0x0', 'c644243800'); g.take('test rcx, rcx')
    embedded_cold = not cold
    if embedded_cold:
        j.edge('header', _branch(g, 'je')); g.take('xor edx, edx'); g.call(symbols['onDeserialized'])
    else:
        j.edge('existing', _branch(g, 'jne'))
    j.mark('header', g); g.take('lea rdx, [rsp+0x38]', 'mov rcx, rdi'); header_call = g.call(symbols['header'])
    g.take('test al, al'); j.edge('null', _branch(g, 'je'))
    _exact(g, 'cmp [rbx], 0x0', '48833b00'); j.edge('count', _branch(g, 'jne'))
    _rip(g, 'mov rcx,'); g.call(symbols['allocate']); g.take('mov rdi, rax', 'test rax, rax')
    if embedded_cold:
        j.edge('constructor', _branch(g, 'jne')); g.call(symbols['nullThrow']); g.take('int3'); j.mark('constructor', g)
        g.take('xor edx, edx', 'mov rcx, rdi')
    else:
        j.edge('allocationError', _branch(g, 'je')); g.take('xor edx, edx', 'mov rcx, rax')
    g.call(symbols['constructor']); g.take('mov rcx, rbx'); _exact(g, 'mov [rbx], rdi', '48893b'); g.call(symbols['barrier'])
    j.mark('count', g)
    _exact(g, 'mov dil, [rsp+0x38]' if embedded_cold else 'movzx edi, [rsp+0x38]',
        '408a7c2438' if embedded_cold else '0fb67c2438')
    g.take('test dil, dil')
    if embedded_cold:
        j.edge('return', _branch(g, 'je')); j.mark('invalidCount', g)
        _rip(g, 'mov rcx,'); _rip(g, 'mov rbx,'); g.call(symbols['classInitDirect'])
        g.take('xor edx, edx', 'mov rcx, rbx'); g.call(symbols['getTypeFromHandle'])
        g.take('xor r9d, r9d', 'mov r8b, dil', 'xor edx, edx', 'mov rcx, rax'); g.call(symbols['invalidPropertyCount']); g.take('int3')
        j.mark('null', g); _exact(g, 'and [rbx], 0x0', '48832300'); g.take('mov rcx, rbx'); g.call(symbols['barrier'])
        j.mark('return', g); _ret(g)
    else:
        j.edge('invalidCount', _branch(g, 'jne')); j.mark('return', g); _ret(g)
        if not inline_init:
            j.mark('init', g); _init(g, 3, flag, symbols); j.edge('common', _branch(g, 'jmp'))
        j.mark('allocationError', g); g.call(symbols['nullThrow']); g.take('int3')
        c = ProgramGrammar(cold, label=label + '.cold')
        j.mark('existing', c); c.take('xor edx, edx'); c.call(symbols['onDeserialized']); c.take('nop'); j.edge('header', _branch(c, 'jmp'))
        j.mark('invalidCount', c); _rip(c, 'mov rcx,'); _rip(c, 'mov rbx,'); c.take('cmp [rcx+0xe0], 0x0')
        j.edge('countTypeReady', _branch(c, 'jne')); c.call(symbols['classInit']); j.mark('countTypeReady', c)
        c.take('xor edx, edx', 'mov rcx, rbx'); c.call(symbols['getTypeFromHandle'])
        c.take('xor r9d, r9d', 'movzx r8d, dil', 'xor edx, edx', 'mov rcx, rax'); c.call(symbols['invalidPropertyCount']); c.take('int3')
        j.mark('null', c); c.take('mov rcx, rbx'); _exact(c, 'mov [rbx], 0x0', '48c70300000000'); c.call(symbols['barrier']); c.take('nop')
        j.edge('return', _branch(c, 'jmp')); c.finish()
    g.finish()
    return {'completeOriginalReaderAndColdEdgesChecked': True, 'localJoins': j.finish(), 'headerCall': header_call,
        'conditionalZeroHeaderNormalReturnProved': True, 'conditionalFFClearsFullOutputReferenceProved': True,
        'otherPropertyCountsJoinThrowProved': True,
        'readerForwarding': 'incoming RCX saved in RDI; byref wrapper output incoming RDX saved in RBX; header receives saved reader and distinct one-byte stack output; lifecycle hook receives wrapper and zero hidden context, with no reader parameter forwarded',
        'selection': 'selected buffered header proof; lifecycle/constructor/allocation/barrier/initialization calls complete normally with required ABI register preservation and no interference with reader, byte output or frame; valid compatible disjoint storage; null allocation and invalid-count trap/throw paths are excluded from normal return',
        'lifecycleOrAllocationEffectsProved': False, 'runtimeExecutionObserved': False}


def prove_zero_wrapper_forwarder(rows, symbols, reader_entry, *, label='zeroForwarder'):
    g = ProgramGrammar(rows, label=label); j = Joins(label)
    g.take('mov [rsp+0x8], rbx', 'push rdi', 'sub rsp, 0x20')
    flag = _flag(g); g.take('mov rbx, r8', 'mov rdi, rdx')
    inline_init = bytes.fromhex(g.rows[g.cursor]['bytes'])[0] == 0x75
    j.edge('class' if inline_init else 'init', _branch(g, 'jne' if inline_init else 'je'))
    if inline_init: _init(g, 1, flag, symbols)
    j.mark('class', g); _rip(g, 'mov rcx,'); g.take('cmp [rcx+0xe0], 0x0')
    inline_class = bytes.fromhex(g.rows[g.cursor]['bytes'])[0] == 0x75
    if inline_class:
        j.edge('forward', _branch(g, 'jne')); g.call(symbols['classInit'])
    else:
        j.edge('classInit', _branch(g, 'je'))
    j.mark('forward', g)
    g.take('xor r8d, r8d', 'mov rdx, rbx', 'mov rcx, rdi', 'mov rbx, [rsp+0x30]', 'add rsp, 0x20', 'pop rdi')
    tail = _branch(g, 'jmp')
    if tail['target'] != reader_entry: g.fail('actual-reader-tailcall', reader_entry, tail)
    if not inline_init:
        j.mark('init', g); _init(g, 1, flag, symbols); j.edge('class', _branch(g, 'jmp'))
    if not inline_class:
        j.mark('classInit', g); g.call(symbols['classInit']); j.edge('forward', _branch(g, 'jmp'))
    g.finish()
    return {'completeOriginalForwarderChecked': True, 'localJoins': j.finish(), 'actualReaderTailcall': tail,
        'conditionalReaderAndOutputForwardingProved': True,
        'selection': 'normal initialization calls preserve saved reader/output and valid matched frame; default concrete formatter selected',
        'runtimeFormatterProviderSelectionProved': False}


def prove_finder_short_union_prefix(rows, *, image_base, table_rva, count, label='finderUnionPrefix'):
    """Complete warm buffered short-tag path through the actual table jump."""
    if type(count) is not int or not 1 <= count <= 250: raise ValueError(f'{label}.table-count')
    g = ProgramGrammar(rows, label=label)
    g.take('mov [rsp+0x8], rbx', 'mov [rsp+0x10], rbp', 'mov [rsp+0x18], rsi', 'push rdi', 'sub rsp, 0x20')
    _flag(g); g.take('mov rsi, r8', 'mov rbx, rdx'); init = _branch(g, 'je')
    _flag(g); header_init = _branch(g, 'je')
    _exact(g, 'cmp [rbx+0x30], 0x1', '837b3001'); refill = _branch(g, 'jl')
    g.take('mov rax, [rbx+0x50]'); _exact(g, 'movzx ebp, [rax]', '0fb628')
    g.take('mov edi, [rbx+0x30]', 'sub edi, 0x1'); advance = _branch(g, 'js')
    _exact(g, 'inc [rbx+0x50]', '48ff4350'); _exact(g, 'inc [rbx+0x40]', 'ff4340'); _exact(g, 'inc [rbx+0x44]', 'ff4344')
    g.take('mov [rbx+0x30], edi'); _exact(g, 'cmp bpl, -0x6', '4080fdfa'); extended = _branch(g, 'jae')
    _exact(g, 'movzx edi, ebp', '0fb7fd'); _exact(g, 'movzx eax, edi', '0fb7c7')
    _exact(g, f'cmp eax, 0x{count-1:x}', '83f8' + (count-1).to_bytes(1, 'little').hex()); invalid = _branch(g, 'ja')
    row = g.pattern(r'lea rdx, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]'); raw = bytes.fromhex(row['bytes'])
    if len(raw) != 7 or raw[:3] != b'\x48\x8d\x15' or int(row['va'], 16) + 7 + int.from_bytes(raw[3:], 'little', signed=True) != image_base:
        g.fail('actual-image-base', image_base, row)
    _exact(g, f'mov ecx, [rdx+0x{table_rva:x}+rax*4]', '8b8c82' + table_rva.to_bytes(4, 'little').hex())
    _exact(g, 'add rcx, rdx', '4803ca'); _exact(g, 'jmp rcx', 'ffe1'); g.finish()
    return {'completeConditionalShortPrefixProved': True, 'readerRegister': 'rbx', 'wrapperOutputRegister': 'rsi',
        'wireTagBits': 8, 'tableEntryBits': 32, 'tableEntrySigned': False, 'tableIndexScale': 4,
        'availableByteCounterDelta': -1, 'currentPointerDelta': 1, 'otherCursorCounterDeltas': [1, 1],
        'excludedBranches': [init, header_init, refill, advance, extended, invalid],
        'selection': 'both initialization flags warmed; selected canonical short tag below table count; signed buffered length at least one; valid disjoint stable reader/output/source/frame; cursor increment bounds and Win64 ABI',
        'extendedOrReservedTagWireProved': False, 'initializationRefillOrErrorEffectsProved': False}


def _context_load(g, register):
    row = g.pattern(register + r', \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    raw = bytes.fromhex(row['bytes']); prefix = {'mov rdx': b'\x48\x8b\x15', 'mov r8': b'\x4c\x8b\x05'}[register]
    if len(raw) != 7 or raw[:3] != prefix: g.fail('context-register', register, row)
    return row


def prove_finder_case(case, new, existing, new_shared, existing_shared, symbols, *, label='finderCase'):
    """Both current case alternatives reach a complete checked caller RET.

    Closed generic contexts and type usage are independently checked by the
    caller. Both ReadPackable overloads, class-predicate and barrier effects retain
    their normal-return/ABI/non-interference conditions.
    """
    g = ProgramGrammar(case, label=label); j = Joins(label)
    g.take('mov rcx, [rsi]', 'test rcx, rcx'); j.edge('new', _branch(g, 'je'))
    type_load = _context_load(g, 'mov rdx'); g.take('mov rcx, [rcx]'); g.call(symbols['typePredicate'])
    g.take('test al, al'); raw = bytes.fromhex(g.rows[g.cursor]['bytes'])
    out_of_line_existing = raw[0] == 0x75 or raw[:2] == b'\x0f\x85'
    j.edge('existing' if out_of_line_existing else 'new', _branch(g, 'jne' if out_of_line_existing else 'je'))
    inline = new if out_of_line_existing else existing
    if g.rows[g.cursor:] != inline: g.fail('same-inline-case-block', inline, g.rows[g.cursor:])
    j.mark('new' if out_of_line_existing else 'existing', g)
    _context_load(g, 'mov rdx' if out_of_line_existing else 'mov r8')
    j.edge('newShared' if out_of_line_existing else 'existingShared', _branch(g, 'jmp')); g.finish()
    other = ProgramGrammar(existing if out_of_line_existing else new, label=label + '.other')
    j.mark('existing' if out_of_line_existing else 'new', other)
    _context_load(other, 'mov r8' if out_of_line_existing else 'mov rdx')
    j.edge('existingShared' if out_of_line_existing else 'newShared', _branch(other, 'jmp')); other.finish()
    n = ProgramGrammar(new_shared, label=label + '.newShared'); j.mark('newShared', n)
    n.take('mov rcx, rbx'); n.call(symbols['readPackable']); _exact(n, 'mov [rsi], rax', '488906')
    n.take('mov rcx, rsi'); n.call(symbols['barrier']); j.edge('return', _branch(n, 'jmp')); n.finish()
    e = ProgramGrammar(existing_shared, label=label + '.existingShared'); j.mark('existingShared', e)
    e.take('mov rdx, rsi', 'mov rcx, rbx'); e.call(symbols['readPackableByref']); j.mark('return', e)
    e.take('mov rbx, [rsp+0x30]', 'mov rbp, [rsp+0x38]', 'mov rsi, [rsp+0x40]', 'add rsp, 0x20', 'pop rdi', 'ret'); e.finish()
    return {'completeSelectedCaseAlternativesAndReturnsProved': True, 'localJoins': j.finish(), 'typeLoad': type_load,
        'conditionalReaderAndOutputThroughBothGenericCallerReturnsProved': True,
        'directReaderCursorWritesInCase': 0, 'sameReadPackableFullReturnStoredToWrapperOutputProved': True,
        'selection': 'selected prefix establishes saved reader RBX and wrapper output RSI; class predicate/closed typed value-return or byref ReadPackable/barrier calls return normally, preserve Win64 ABI and matched frame/source aliases; default concrete child formatter is selected separately',
        'genericProviderOrLifecycleEffectsProved': False, 'runtimeTargetSelectionObserved': False}

"""Complete physical byref reader bridges, with original local control edges.

These byte grammars prove Reader/output/MethodInfo forwarding under stable
compatible contexts, normal non-interfering helper returns and the Win64 ABI.
They do not name anonymous bodies, observe a live provider result or prove
initialization, provider, formatter or global effects.
"""
from __future__ import annotations
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar


def _exact(g, text, encoding):
    row = g.take(text)
    if bytes.fromhex(row['bytes']) != bytes.fromhex(encoding):
        g.fail('operand-encoding', encoding, row)
    return row


def _save(g):
    for text, encoding in (
        ('mov [rsp+0x8], rbx', '48895c2408'), ('mov [rsp+0x10], rsi', '4889742410'),
        ('push rdi', '57'), ('sub rsp, 0x20', '4883ec20'),
        ('cmp [r8+0x38], 0x0', '4983783800'), ('mov rbx, r8', '498bd8'),
        ('mov rdi, rdx', '488bfa'), ('mov rsi, rcx', '488bf1')):
        _exact(g, text, encoding)


def _restore(g):
    for text, encoding in (
        ('mov rbx, [rsp+0x30]', '488b5c2430'), ('mov rsi, [rsp+0x38]', '488b742438'),
        ('add rsp, 0x20', '4883c420'), ('pop rdi', '5f')):
        _exact(g, text, encoding)


def prove_packable_byref_bridge(rows, *, context_init, read_value_entry, label='packableByrefBridge'):
    g = ProgramGrammar(rows, label=label); _save(g)
    g.branch('jne', 'contextReady'); _exact(g, 'mov rcx, rbx', '488bcb'); g.call(context_init)
    g.mark('contextReady')
    for text, encoding in (
        ('mov r8, [rbx+0x38]', '4c8b4338'), ('mov rdx, rdi', '488bd7'),
        ('mov rcx, rsi', '488bce'), ('mov r8, [r8]', '4d8b00')):
        _exact(g, text, encoding)
    _restore(g); tail = g.branch('jmp'); g.finish()
    if tail['target'] != read_value_entry:
        g.fail('actual-read-value-tail', read_value_entry, tail)
    return {'completePhysicalEntryAndTailChecked': True,
        'conditionalSameReaderOutputAndSlotZeroContextForwarded': True,
        'readerRegister': 'rcx', 'outputRegister': 'rdx', 'contextRegister': 'r8',
        'nestedContextSlot': 0, 'frameRestoredBeforeTail': True,
        'directReaderCursorWrites': 0, 'runtimeContextInflationObserved': False,
        'contextInitializerEffectsProved': False}


def _rip(g, *, lea):
    prefix = b'\x48\x8d\x0d' if lea else b'\x48\x8b\x0d'
    row = g.pattern(('lea' if lea else 'mov') + r' rcx, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    raw = bytes.fromhex(row['bytes'])
    if len(raw) != 7 or raw[:3] != prefix: g.fail('class-cell-encoding', prefix.hex(), row)
    return int(row['va'], 16)+7+int.from_bytes(raw[3:], 'little', signed=True)


def prove_read_value_byref_bridge(rows, symbols, *, label='readValueByrefBridge'):
    g = ProgramGrammar(rows, label=label); _save(g); g.branch('je', 'contextInit')
    g.mark('classCheck'); class_cell = _rip(g, lea=False)
    _exact(g, 'cmp [rcx+0xe0], 0x0', '83b9e000000000'); g.branch('je', 'classInit')
    g.mark('provider'); _exact(g, 'mov rax, [rbx+0x38]', '488b4338')
    _exact(g, 'mov rcx, [rax]', '488b08'); g.call(symbols['provider'])
    _exact(g, 'test rax, rax', '4885c0'); g.branch('je', 'return')
    for text, encoding in (
        ('mov ecx, 0x5', 'b905000000'), ('mov r9, rdi', '4c8bcf'),
        ('mov r8, rsi', '4c8bc6'), ('mov rdx, rax', '488bd0')):
        _exact(g, text, encoding)
    g.call(symbols['formatterDispatch']); g.mark('return'); _restore(g); _exact(g, 'ret', 'c3')
    g.mark('contextInit')
    if _rip(g, lea=True) != class_cell: g.fail('same-class-cell', class_cell, rows[g.cursor-1])
    g.call(symbols['metadataInit']); _exact(g, 'cmp [rbx+0x38], 0x0', '48837b3800')
    g.branch('jne', 'classCheck'); _exact(g, 'mov rcx, rbx', '488bcb')
    g.call(symbols['contextInit']); g.branch('jmp', 'classCheck')
    g.mark('classInit'); g.call(symbols['classInit']); g.branch('jmp', 'provider'); g.finish()
    return {'completePhysicalEntryAndAllLocalEdgesChecked': True,
        'conditionalNonNullFormatterReceivesSameReaderOutputAndReturns': True,
        'conditionalNullFormatterSkipsDispatchWithoutDirectOutputStore': True,
        'providerContextSlot': 0, 'formatterSlot': 5,
        'dispatchReaderRegister': 'r8', 'dispatchOutputRegister': 'r9',
        'directReaderCursorWrites': 0, 'directOutputStores': 0,
        'initializationAndProviderEffectsProved': False, 'runtimeProviderSelectionObserved': False}


def prove_terminal_entry_jump(row, target, *, label='referenceReaderEntryJump'):
    g = ProgramGrammar([row], label=label); jump = g.branch('jmp'); g.finish()
    if len(bytes.fromhex(row['bytes'])) != 5 or jump['target'] != target:
        g.fail('terminal-entry-transfer', target, jump)
    return {'conditionalAllIncomingRegistersAndStackForwarded': True,
        'instructionBits': 40, 'namedBodyIdentityProved': False,
        'adjacentBytesOrFunctionExtentProved': False}

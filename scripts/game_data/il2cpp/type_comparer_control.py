"""Closed selected comparison/search programs and conditional non-stack silence.

Finite normal calls, valid disjoint recursive stack storage and no concurrent
interference are conditions. Read-only input behavior does not make comparator
zero mean complete type-record equality or bind a returned runtime class.
"""
from __future__ import annotations

from collections import deque

from .field_setup_control import _frames, _projection, setup_memory_effect
from .initializer_control import _ALIASES, control_transfer
from .integer_addressing import decode_lea_address
from .method_carrier_control import _Grammar
from .method_carrier_resolution import _address, _memory

LABEL = 'typeComparerControl'
_NO_IMPLICIT_MEMORY_UPDATE = {'mov', 'movzx', 'movsx', 'movsxd', 'lea', 'cmp', 'test',
    'xor', 'and', 'add', 'sub', 'shr', 'shl', 'sar', 'imul', 'inc', 'dec', 'cdqe',
    'cmovb', 'cmovl', 'cmove', 'cmovne', 'nop', 'pop'}


def _grammar(rows, base, window, role):
    return _Grammar(_projection(rows, base, window), label=LABEL + '.' + role)


def _graph(rows, base, f, entries):
    by_at = {int(row['va'], 16): row for row in rows}
    if len(by_at) != len(rows):
        raise ValueError(LABEL + '.duplicate-instruction')
    edges, calls, stores, branches, returns = {}, [], [], [], []
    table = f.get('table')
    for at, row in by_at.items():
        flow = control_transfer(row)
        kind = flow['kind']
        targets = set()
        if kind in ('jump', 'conditional'):
            targets.add(flow['target'])
            branches.append({'siteRva': at - base, **flow})
        if kind in ('next', 'conditional', 'call'):
            targets.add(at + len(bytes.fromhex(row['bytes'])))
        if kind == 'call':
            if flow['target'] not in entries:
                raise ValueError(LABEL + '.call-not-closed:' + row['va'])
            calls.append({'siteRva': at - base, **flow})
        elif kind == 'tableJump':
            if table is None or at != base + table['jumpRva']:
                raise ValueError(LABEL + '.unlisted-table-jump')
            targets.update(base + rva for rva in table['targetRvas'])
        elif kind == 'return':
            returns.append(at - base)
        elif kind not in ('next', 'jump', 'conditional'):
            raise ValueError(LABEL + '.unreviewed-transfer:' + row['va'])
        if not targets <= by_at.keys():
            raise ValueError(LABEL + '.target-boundary:' + row['va'])
        edges[at] = targets
        effect = setup_memory_effect(row)
        if effect:
            stores.append({'siteRva': at - base, **effect})
        elif kind == 'next' and row['text'].split(' ')[0] not in _NO_IMPLICIT_MEMORY_UPDATE | {'push'}:
            raise ValueError(LABEL + '.unreviewed-implicit-memory-effects:' + row['va'])
    for key, actual in (('calls', calls), ('explicitStores', stores), ('localBranches', branches), ('returnRvas', returns)):
        if f[key] != actual:
            raise ValueError(LABEL + '.' + key)
    reached, pending = set(), [base + f['entryRva']]
    while pending:
        at = pending.pop()
        if at not in reached:
            reached.add(at)
            pending.extend(edges[at] - reached)
    if reached != by_at.keys():
        raise ValueError(LABEL + '.unreachable-code-or-padding')
    return edges, calls, stores


def _stack_writes(rows, stores, states, base):
    writes = []
    for item in stores:
        facts = item['facts']
        address = facts.get('address', facts.get('destinationAddress', {}))
        width = facts.get('memoryBytes', facts.get('memoryWriteBytes'))
        if address.get('base') != 'rsp' or address.get('index') is not None or address.get('ripRelative') or type(width) is not int or width <= 0:
            raise ValueError(LABEL + '.non-stack-memory-write:' + hex(item['siteRva']))
        sp = states[base + item['siteRva']][0]
        begin = sp + address['displacement']
        if begin < sp or begin + width > 40:
            raise ValueError(LABEL + '.write-outside-frame-and-entry-homes')
        writes.append({'siteRva': item['siteRva'], 'entrySpOffset': begin, 'bytes': width, 'kind': 'explicit'})
    for row in rows:
        at = int(row['va'], 16)
        kind = control_transfer(row)['kind']
        if row['text'].startswith('push ') or kind == 'call':
            writes.append({'siteRva': at - base, 'entrySpOffset': states[at][0] - 8, 'bytes': 8,
                           'kind': 'push' if row['text'].startswith('push ') else 'normal-call-return-address'})
    return writes


def _count_leaf(rows, base, c):
    f = c['functions']['countLeaf']
    g = _Grammar(rows, label=LABEL + '.closedCountLeaf')
    _memory(g, 'load', 'eax', 4, 'rdx', c['layout']['count'])
    g.take('mov r8, rcx', 'cmp dword [rcx], eax')
    g.branch('jne', 'different')
    g.take('xor eax, eax', 'ret')
    g.mark('different')
    _memory(g, 'load', 'ecx', 4, 'rdx', c['layout']['count'])
    g.take('mov eax, 0x1', 'cmp dword [r8], ecx', 'mov r9d, 0xffffffff', 'cmovb eax, r9d', 'ret')
    g.finish()
    if f['ownershipKind'] != 'closedEntryProgram' or f['paddingWindows'] or f.get('table'):
        raise ValueError(LABEL + '.closed-leaf-shape')
    return {'closedEntryInstructions': len(rows), 'exceptionOwnedExtentClaimed': False,
            'memoryUpdates': 0, 'childCalls': 0,
            'preservedRegisters': ['rdx', 'r10', 'r11', 'rbx', 'rsi', 'rdi', 'rbp', 'rsp', 'r12', 'r13', 'r14', 'r15'],
            'initialEqualDwordReadsReturnZero': True,
            'initialDifferenceSelectsFreshUnsignedDwordOrdering': True,
            'initialAndFreshCountReadsAssumedIdentical': False}


def _table(rows, edges, base, c):
    f = c['functions']['typeComparer']
    t = f['table']
    l = c['layout']
    g = _grammar(rows, base, t['guardWindow'], 'typeTable')
    g.take(f'movsx eax, byte [r10+0x{l["kind"]:x}]', f'add eax, {hex(-t["kindBias"])}',
           f'cmp eax, 0x{len(t["targetRvas"])-1:x}')
    guard = g.branch('ja')
    g.take('cdqe', f'mov ecx, [rdx+rax*4+0x{t["startRva"]:x}]', 'add rcx, rdx')
    jump = g.take('jmp rcx')
    g.finish()
    if guard['target'] != base + t['defaultRva'] or int(jump['va'], 16) != base + t['jumpRva'] or bytes.fromhex(jump['bytes']) != b'\xff\xe1':
        raise ValueError(LABEL + '.table-targets')
    start, end = base + t['guardWindow']['startRva'], base + t['guardWindow']['endRva']
    for at in sorted(edges):
        if start < at < end:
            previous = next(int(r['va'], 16) for r in rows if int(r['va'], 16) + len(bytes.fromhex(r['bytes'])) == at)
            if {p for p, targets in edges.items() if at in targets} != {previous}:
                raise ValueError(LABEL + '.guard-interior-entry')
    # Carry a finite RDX fact through every ordinary continuation. Calls and
    # every direct/partial RDX write kill it; pointer-recursion paths retain it.
    by_at = {int(r['va'], 16): r for r in rows}
    entry = base + f['entryRva']
    incoming, pending = {entry: frozenset({'unknown'})}, deque([entry])
    while pending:
        at = pending.popleft()
        row = by_at[at]
        raw = bytes.fromhex(row['bytes'])
        head, _, rest = row['text'].partition(' ')
        value = incoming[at]
        if control_transfer(row)['kind'] == 'call':
            value = frozenset({'unknown'})
        elif _ALIASES.get(rest.split(',')[0]) == 'rdx' and head not in ('cmp', 'test', 'push'):
            decoded = decode_lea_address(raw, 0, at) if head == 'lea' else None
            facts = decoded[0].get('addressOperation', {}) if decoded else {}
            value = frozenset({'imageBase'}) if decoded and decoded[1] == len(raw) and (
                facts.get('destinationBits'), facts.get('ripRelative'), facts.get('absoluteAddress')) == (64, True, base) else frozenset({'unknown'})
        for target in edges[at]:
            merged = incoming.get(target, frozenset()) | value
            if merged != incoming.get(target):
                incoming[target] = merged
                pending.append(target)
    if incoming[base + t['loadRva']] != frozenset({'imageBase'}):
        raise ValueError(LABEL + '.table-base-not-preserved')
    domain = []
    for stored_byte in range(256):
        signed = stored_byte if stored_byte < 128 else stored_byte - 256
        index = (signed - t['kindBias']) & 0xffffffff
        if index < len(t['targetRvas']):
            domain.append([stored_byte, index, t['targetRvas'][index]])
    return {'entries': len(t['targetRvas']), 'selectedByteDomain': domain,
            'guardInteriorBypassesExcluded': True, 'imageBasePreservedAtEveryTableLoad': True,
            'kindMeaningOrRuntimeCaseObserved': False}


def _restore(g, frame):
    _memory(g, 'load', 'rbx', 8, 'rsp', frame['savedRbx'])
    g.take(f'add rsp, 0x{frame["bytes"]:x}', 'ret')


def _selected_comparisons(rows, base, c):
    l, p, frame = c['layout'], c['projections'], c['comparerFrame']
    g = _grammar(rows, base, p['entry'], 'entry')
    g.take(f'sub rsp, 0x{frame["bytes"]:x}', 'mov r11, rdx')
    _memory(g, 'store', 'rbx', 8, 'rsp', frame['savedRbx'])
    _address(g, 'rdx', None, None, absolute=base)
    g.take('mov r10, rcx', 'nop')
    g.finish()
    g = _grammar(rows, base, p['header'], 'header')
    g.labels.update(kindMismatch=base + p['kindMismatch']['startRva'], flagMismatch=base + p['flagMismatch']['startRva'])
    g.take(f'movzx eax, byte [r11+0x{l["kind"]:x}]', f'cmp [r10+0x{l["kind"]:x}], al')
    g.branch('jne', 'kindMismatch')
    _memory(g, 'load', 'eax', 4, 'r11', l['flagWord'])
    _memory(g, 'load', 'ecx', 4, 'r10', l['flagWord'])
    g.take(f'shr eax, 0x{l["flagBit"]:x}', f'shr ecx, 0x{l["flagBit"]:x}', 'and eax, 0x1', 'and ecx, 0x1', 'cmp ecx, eax')
    g.branch('jne', 'flagMismatch')
    g.finish()
    g = _grammar(rows, base, p['kindMismatch'], 'kindMismatch')
    _memory(g, 'load', 'rbx', 8, 'rsp', frame['savedRbx'])
    g.take('mov eax, 0x1', 'mov edx, 0xffffffff', 'cmovl eax, edx', f'add rsp, 0x{frame["bytes"]:x}', 'ret')
    g.finish()
    g = _grammar(rows, base, p['flagMismatch'], 'flagMismatch')
    g.take('mov eax, 0x1', 'mov edx, 0xffffffff', 'cmovb eax, edx')
    _restore(g, frame)
    g.finish()
    g = _grammar(rows, base, p['defaultZero'], 'defaultZero')
    g.take('xor eax, eax')
    _restore(g, frame)
    g.finish()
    g = _grammar(rows, base, p['qword'], 'qword')
    _memory(g, 'load', 'rax', 8, 'r11', l['data'])
    g.take('cmp qword [r10], rax')
    g.branch('jne', 'different')
    g.take('xor ebx, ebx', 'mov eax, ebx')
    _restore(g, frame)
    g.mark('different')
    g.take('cmp qword [r10], rax', 'mov ebx, 0x1', 'mov edx, 0xffffffff', 'cmovb ebx, edx', 'mov eax, ebx')
    _restore(g, frame)
    g.finish()
    table = c['functions']['typeComparer']['table']
    kinds = [kind for kind in range(256) if 0 <= kind - table['kindBias'] < len(table['targetRvas'])
             and table['targetRvas'][kind - table['kindBias']] == p['qword']['startRva']]
    if not kinds or l['data'] != 0:
        raise ValueError(LABEL + '.qword-case-layout')
    # Both records reach the proved QWORD-equality return, despite one ignored
    # low flag bit differing. This witness proves zero is not raw-record equality.
    left = bytearray(l['recordBytes'])
    left[l['kind']] = kinds[0]
    right = bytearray(left)
    right[l['flagWord']] ^= 1
    if (left[l['kind']] != right[l['kind']] or
        ((int.from_bytes(left[l['flagWord']:l['flagWord']+4], 'little') ^ int.from_bytes(right[l['flagWord']:l['flagWord']+4], 'little')) >> l['flagBit']) & 1 or
        left[l['data']:l['data']+8] != right[l['data']:l['data']+8] or left == right):
        raise ValueError(LABEL + '.zero-result-witness')
    return {'kindMismatchUsesSignedByteOrdering': True, 'selectedFlagBit': l['flagBit'],
            'flagMismatchUsesUnsignedSelectedBitOrdering': True, 'qwordCaseKinds': kinds,
            'qwordMismatchUsesFreshLeftUnsignedOrdering': True,
            'qwordInitialAndFreshLeftReadsAssumedIdentical': False,
            'zeroDoesNotEstablishWholeTypeRecordEquality': True,
            'zeroWitness': {'leftHex': left.hex().upper(), 'rightHex': right.hex().upper(), 'selectedResult': 0,
                            'sameKindFlagAndData': True, 'completeRecordsEqual': False}}


def validate_type_comparer(programs, *, image_base, contract):
    c, base = contract, image_base
    if set(programs) != {'search', 'typeComparer', 'countLeaf'} or set(c['functions']) != set(programs):
        raise ValueError(LABEL + '.function-set')
    entries = {base + f['entryRva'] for f in c['functions'].values()}
    controls, graphs = {}, {}
    for role, rows in programs.items():
        f = c['functions'][role]
        actual = [[int(r['va'], 16) - base, bytes.fromhex(r['bytes']).hex().upper()] for r in rows]
        if actual != f['program'] or len(rows) != f['checkedInstructionCount']:
            raise ValueError(LABEL + '.complete-code-inventory:' + role)
        edges, calls, stores = _graph(rows, base, f, entries)
        states = _frames(rows, edges, base, f)
        writes = _stack_writes(rows, stores, states, base)
        controls[role] = {'instructions': len(rows), 'actualClosedCalls': calls, 'stackWrites': writes,
                          'nonStackMemoryWrites': 0, 'allCodeReachable': True, 'normalFramesChecked': True}
        graphs[role] = edges
    leaf = _count_leaf(programs['countLeaf'], base, c)
    table = _table(programs['typeComparer'], graphs['typeComparer'], base, c)
    selected = _selected_comparisons(programs['typeComparer'], base, c)
    return {'completeControls': controls, 'completeCodeInstructions': sum(len(rows) for rows in programs.values()),
            'closedCountLeaf': leaf, 'typeDispatch': table, 'selectedComparisons': selected,
            'allDirectCallsRemainInsideCheckedFamily': True,
            'finiteNormalFamilyOnlyWritesItsDisjointRecursiveStack': True,
            'inputTypeCopyPreservedAcrossSelectedSearchCallConditionallyProved': True,
            'recursiveTerminationProved': False, 'wholeTypedComparisonResultProved': False,
            'constructorOtherCallsOrAliasesPreserveCopyProved': False,
            'runtimeTypeOrCacheIdentityProved': False, 'concreteDamageTypeSharingSelected': False,
            'wholeRootAdmitted': False, 'runtimeExecutionKnown': False}

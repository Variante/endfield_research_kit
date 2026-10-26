"""Complete anonymous encoded-method and carrier normal control programs.

The recursive probe's preservation of RDX/R8 follows from its complete body,
including both self calls, conditional on finite normal returns. Physical
carrier fields and encoded kinds do not select managed generic arguments.
"""
from __future__ import annotations

from collections import deque

from .integer_addressing import decode_lea_address
from .memory_moves import decode_memory_move
from .owned_partition import BranchGrammar
from .relation_control import transfer


class _Grammar(BranchGrammar):
    def branch(self, condition, label=None):
        if condition != 'jle':
            return super().branch(condition, label)
        row = self.row()
        edge = transfer(row)
        if edge.get('kind') != 'conditional' or edge.get('conditionCode') != 14:
            self.fail('branch-predicate', 'signed less or equal', row)
        if label is not None:
            self.edges.append((edge['target'], label, row))
        return {**row, 'target': edge['target'], 'predicate': condition}


def _graph(rows, entry, tails):
    by_at = {int(r['va'], 16): r for r in rows}
    if len(by_at) != len(rows) or entry not in by_at:
        raise ValueError('methodCarrierControl.instruction-entry-or-duplicate')
    edges = {}
    calls = []
    exits = []
    for at, row in by_at.items():
        flow = transfer(row)
        end = at + len(bytes.fromhex(row['bytes']))
        kind = flow['kind']
        targets = []
        if kind in ('next', 'conditional', 'call'):
            targets.append(end)
        if kind in ('jump', 'conditional'):
            target = flow['target']
            if kind == 'jump' and target in tails:
                exits.append((at, 'tail', target))
            else:
                targets.append(target)
        if kind == 'call':
            calls.append((at, flow['target']))
        elif kind == 'return':
            exits.append((at, 'return', None))
        elif kind not in ('next', 'jump', 'conditional'):
            raise ValueError('methodCarrierControl.unreviewed-transfer:' + row['bytes'])
        if any(target not in by_at for target in targets):
            raise ValueError('methodCarrierControl.local-instruction-boundary:' + row['va'])
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
        raise ValueError('methodCarrierControl.unreachable-owned-instructions')
    frames = {entry: 0}
    pending = deque([entry])
    exits_at = {at for at, _, _ in exits}
    while pending:
        at = pending.popleft()
        row = by_at[at]
        sp = frames[at]
        head, _, operands = row['text'].partition(' ')
        if head == 'push':
            if operands == 'rsp':
                raise ValueError('methodCarrierControl.push-rsp')
            sp -= 8
        elif head == 'pop':
            if operands == 'rsp':
                raise ValueError('methodCarrierControl.pop-rsp')
            sp += 8
        elif operands.split(',')[0] == 'rsp':
            if head not in ('add', 'sub') or not operands.startswith('rsp, 0x'):
                raise ValueError('methodCarrierControl.dynamic-frame')
            amount = int(operands.split(', ')[1], 16)
            sp += amount if head == 'add' else -amount
        if transfer(row)['kind'] == 'call' and ((8 + sp) % 16 or -sp < 32):
            raise ValueError('methodCarrierControl.call-frame')
        if at in exits_at and sp != 0:
            raise ValueError('methodCarrierControl.exit-frame')
        for target in edges[at]:
            if target in frames and frames[target] != sp:
                raise ValueError('methodCarrierControl.frame-join')
            if target not in frames:
                frames[target] = sp
                pending.append(target)
    return {'instructions': len(rows), 'allOwnedInstructionsReachable': True,
            'allLocalTargetsAreInstructionBoundaries': True,
            'normalCallsHaveAlignedHomeSpace': True,
            'allNormalReturnsAndTailsRestoreEntryRsp': True,
            'directCalls': calls, 'exits': exits}


def _lea(g, register, absolute):
    row = g.row()
    result = decode_lea_address(bytes.fromhex(row['bytes']), 0, int(row['va'], 16))
    fact = result[0]['addressOperation'] if result else {}
    if result is None or result[1] != len(bytes.fromhex(row['bytes'])) or (
            fact.get('destination'), fact.get('destinationBits'), fact.get('absoluteAddress')) != (
            register, 64, absolute):
        g.fail('absolute-address', (register, absolute), row)


def _limit(g, absolute):
    row = g.row()
    result = decode_memory_move(bytes.fromhex(row['bytes']), 0, int(row['va'], 16))
    fact = result[0]['memoryOperation'] if result else {}
    if result is None or result[1] != len(bytes.fromhex(row['bytes'])) or (
            fact.get('direction'), fact.get('register'), fact.get('memoryBytes'),
            fact.get('address', {}).get('absoluteAddress')) != ('load', 'edx', 4, absolute):
        g.fail('fresh-dword-limit', absolute, row)


def _load(g, register, size, receiver, offset):
    row = g.row()
    raw = bytes.fromhex(row['bytes'])
    result = decode_memory_move(raw, 0, int(row['va'], 16))
    fact = result[0]['memoryOperation'] if result else {}
    address = fact.get('address', {})
    if result is None or result[1] != len(raw) or (
            fact.get('direction'), fact.get('register'), fact.get('memoryBytes'),
            address.get('base'), address.get('index'), address.get('displacement'),
            address.get('ripRelative')) != ('load', register, size, receiver, None, offset, False):
        g.fail('memory-load', (register, size, receiver, offset), row)


def _gate(g, absolute):
    row = g.row()
    raw = bytes.fromhex(row['bytes'])
    target = int(row['va'], 16) + len(raw) + int.from_bytes(raw[3:7], 'little', signed=True)
    if len(raw) != 8 or raw[:3] != b'\x48\x83\x3d' or raw[7:] != b'\x00' or target != absolute:
        g.fail('fresh-qword-gate', absolute, row)


def _lookup(rows, base, c):
    g = _Grammar(rows, label='methodCarrierControl.lookup')
    calls = c['calls']
    g.take('sub rsp, 0x28', 'mov eax, ecx', 'shr ecx, 0x1d',
           'shr eax, 0x1', 'and eax, 0xfffffff', 'test ecx, ecx')
    g.branch('je', 'zeroKind')
    g.take('cmp ecx, 0x3')
    g.branch('je', 'plainIndex')
    g.take('cmp ecx, 0x6')
    g.branch('jne', 'nullReturn')
    g.take('mov ecx, eax')
    indexed = g.call(base + calls['encodedCarrierIndex'])
    g.take('xor edx, edx', 'mov rcx, rax', 'add rsp, 0x28')
    tail = g.branch('jmp')
    if tail['target'] != base + calls['carrierLookup']:
        g.fail('kind-six-tail', base + calls['carrierLookup'], tail)
    g.mark('plainIndex')
    g.take('mov ecx, eax', 'add rsp, 0x28')
    tail = g.branch('jmp')
    if tail['target'] != base + calls['plainMethodIndex']:
        g.fail('kind-three-tail', base + calls['plainMethodIndex'], tail)
    g.mark('zeroKind')
    g.take('test eax, eax')
    g.branch('je', 'nullReturn')
    g.take('cmp eax, 0x1')
    g.branch('jne', 'nullReturn')
    _lea(g, 'rax', base + c['globals']['specialMethodAddressRva'])
    g.take('add rsp, 0x28', 'ret')
    g.mark('nullReturn')
    g.take('xor eax, eax', 'add rsp, 0x28', 'ret')
    g.finish()
    tails = {base + calls[k] for k in ('carrierLookup', 'plainMethodIndex')}
    graph = _graph(rows, base + c['functions']['lookup']['entryRva'], tails)
    if {target for _, kind, target in graph['exits'] if kind == 'tail'} != tails:
        g.fail('external-tail-set', tails, graph['exits'])
    return {'control': graph, 'inputBits': 32, 'kindBits': [29, 31],
            'indexBits': [1, 28], 'lowBitDiscarded': True,
            'indexFormula': '(uint32(entry ECX) >> 1) & 0x0fffffff',
            'kindFormula': 'uint32(entry ECX) >> 29',
            'kindSix': {'indexPassedInEcx': True, 'indexedCallRva': int(indexed['va'], 16)-base,
                        'returnedCarrierPassedInRcx': True, 'lookupEdxCleared': True},
            'kindThree': 'tail to plain index target with computed ECX index',
            'kindZero': 'index one returns the recorded anonymous static address; other indices return zero',
            'otherKinds': 'return zero', 'metadataUsageKindNamesOrTableBoundsProved': False}


def _depth(rows, base, c):
    entry = base + c['functions']['depth']['entryRva']
    g = _Grammar(rows, label='methodCarrierControl.depth')
    g.take('push rbp', 'sub rsp, 0x20', 'mov rbp, rcx', 'test rcx, rcx')
    g.branch('jne', 'nonNull')
    g.take('xor eax, eax', 'add rsp, 0x20', 'pop rbp', 'ret')
    g.mark('nonNull')
    g.take('mov [rsp+0x30], rbx', 'mov [rsp+0x48], r14', 'xor r14d, r14d',
           'mov ebx, r14d', 'cmp dword [rcx], ebx')
    g.branch('jbe', 'finish')
    g.take('mov [rsp+0x38], rsi', 'mov [rsp+0x40], rdi', 'nop', 'nop')
    g.mark('loop')
    g.take('mov rax, [rbp+0x8]', 'mov rcx, [rax+rbx*8]', 'cmp byte [rcx+0xa], 0x15')
    g.branch('jne', 'increment')
    g.take('mov rdi, [rcx]', 'mov rcx, [rdi+0x8]')
    g.call(entry)
    g.take('mov rcx, [rdi+0x10]', 'mov esi, eax')
    g.call(entry)
    g.take('cmp esi, eax', 'cmovl esi, eax', 'cmp r14d, esi',
           'cmovge esi, r14d', 'mov r14d, esi')
    g.mark('increment')
    _load(g, 'eax', 4, 'rbp', 0)
    g.take('inc rbx', 'cmp rbx, rax')
    g.branch('jb', 'loop')
    g.take('mov rdi, [rsp+0x40]', 'mov rsi, [rsp+0x38]')
    g.mark('finish')
    g.take('mov rbx, [rsp+0x30]', 'lea eax, [r14+0x1]',
           'mov r14, [rsp+0x48]', 'add rsp, 0x20', 'pop rbp', 'ret')
    g.finish()
    graph = _graph(rows, entry, set())
    if len(graph['directCalls']) != 2 or any(target != entry for _, target in graph['directCalls']):
        g.fail('recursive-call-closure', 'only two direct self calls', graph['directCalls'])
    aliases = {'rdx', 'edx', 'dx', 'dl', 'dh', 'r8', 'r8d', 'r8w', 'r8b'}
    read_only = {'cmp', 'test', 'push', 'ret', 'nop', 'call', 'jcc', 'je', 'jne', 'jbe', 'jb'}
    for row in rows:
        head, _, operands = row['text'].partition(' ')
        destination = operands.split(',')[0]
        write = row.get('write') or {}
        if write.get('register') in aliases or head not in read_only and destination in aliases:
            g.fail('recursive-probe-register-preservation', 'no RDX/R8 alias write', row)
    return {'control': graph, 'recursiveSelfCalls': 2,
            'preservedRegisters': ['rdx', 'r8'], 'preservationBits': 64,
            'preservationProof': 'Complete body never writes either register or an alias; both calls target this same complete body. Induction over finite normally returning self calls preserves all bits.',
            'preservationRequiresFiniteNormalReturn': True,
            'nullInputReturnEax': 0, 'nonNullReturn': 'saved accumulator plus one modulo 2^32',
            'selectedRecursiveRecordKindByte': 21, 'signedAccumulatorComparisons': True,
            'runtimeDepthValueOrTerminationProved': False}


def _inflate(rows, base, c, depth):
    g = _Grammar(rows, label='methodCarrierControl.inflate')
    calls = c['calls']
    g.take('mov [rsp+0x8], rbx', 'mov [rsp+0x10], rsi', 'push rdi', 'sub rsp, 0x20',
           'mov rsi, rcx', 'mov r8b, 0x1', 'mov rcx, [rcx+0x8]', 'mov rbx, rdx')
    first = g.call(base + calls['childInflation'])
    g.take('mov rcx, [rsi+0x10]', 'mov r8b, 0x1', 'mov rdx, rbx', 'mov rdi, rax')
    second = g.call(base + calls['childInflation'])
    _gate(g, base + c['globals']['depthGateCellRva'])
    g.take('mov r8, rax')
    g.branch('jne', 'compose')
    g.take('mov rcx, rdi')
    g.call(base + calls['depthProbe'])
    _limit(g, base + c['globals']['depthLimitCellRva'])
    g.take('cmp eax, edx')
    g.branch('jg', 'reject')
    g.take('mov rcx, r8')
    g.call(base + calls['depthProbe'])
    g.take('cmp eax, edx')
    g.branch('jle', 'compose')
    g.mark('reject')
    g.take('xor eax, eax', 'mov rbx, [rsp+0x30]', 'mov rsi, [rsp+0x38]',
           'add rsp, 0x20', 'pop rdi', 'ret')
    g.mark('compose')
    g.take('mov rcx, [rsi]', 'mov rdx, rdi', 'mov rbx, [rsp+0x30]',
           'mov rsi, [rsp+0x38]', 'add rsp, 0x20', 'pop rdi')
    tail = g.branch('jmp')
    if tail['target'] != base + calls['carrierComposition']:
        g.fail('composition-tail', base + calls['carrierComposition'], tail)
    g.finish()
    if depth['preservedRegisters'] != ['rdx', 'r8'] or depth['preservationBits'] != 64:
        g.fail('depth-register-proof', 'complete RDX/R8 recursive preservation', depth)
    graph = _graph(rows, base + c['functions']['inflate']['entryRva'], {tail['target']})
    return {'control': graph, 'carrierInputQwordOffsets': [0, 8, 16],
            'childCalls': [{'siteRva': int(row['va'], 16)-base, 'carrierQwordOffset': offset}
                           for row, offset in ((first, 8), (second, 16))],
            'sameIncomingRdxContextPassedToBothChildren': True,
            'childFlagIsLowR8bOneOnly': True, 'upperR8BitsAtChildCallsProved': False,
            'firstChildResultSavedInRdi': True, 'secondChildResultSavedInR8': True,
            'depthGateReadBytes': 8, 'depthLimitReadBytes': 4,
            'limitIsFreshBetweenFirstAndSecondProbes': True,
            'depthComparisonsSigned32': True,
            'secondResultSurvivesFirstProbeAndBothResultsReachComposition': True,
            'sameLimitSurvivesSecondProbe': True,
            'gatePredicate': 'Fresh gate nonzero bypasses probes; gate zero returns zero if either signed probe result exceeds the one freshly loaded signed DWORD limit; otherwise tail composition receives carrier[0], first child result, second child result.',
            'compositionArguments': {'rcx': 'fresh original carrier[0]',
                                     'rdx': 'first child returned QWORD', 'r8': 'second child returned QWORD'},
            'childResultIdentityEffectsOrSharingProved': False}


def validate_method_carrier_control(programs, *, image_base, contract):
    """Validate complete decoded lookup, inflation and recursive probe bodies."""
    if set(programs) != {'lookup', 'inflate', 'depth'}:
        raise ValueError('methodCarrierControl.function-set')
    if contract['calls']['depthProbe'] != contract['functions']['depth']['entryRva']:
        raise ValueError('methodCarrierControl.same-depth-target')
    depth = _depth(programs['depth'], image_base, contract)
    lookup = _lookup(programs['lookup'], image_base, contract)
    inflation = _inflate(programs['inflate'], image_base, contract, depth)
    return {'lookup': lookup, 'depthProbe': depth, 'carrierInflation': inflation,
            'distinctInstructions': sum(len(rows) for rows in programs.values()),
            'concreteGenericArgumentsOrCompiledSharingSelected': False,
            'runtimeMethodInfoOrProviderObserved': False, 'runtimeExecutionKnown': False}

"""Selected relation import arguments and physical counter control.

The parent proves the complete owned CFG. This lane checks all selected
import sites, their argument/control grammar, and a finite constant analysis
over that CFG. Normal ABI-compatible returns are a condition, not a live
binding or synchronization receipt. A context child receives a stack-slot
address; the subsequent pointer load is deliberately treated as a fresh value.

Conditional (under the Microsoft x64 calling convention): the constant
analysis preserves RDI/RBP/R14 and invalidates R9 at every call.

Checked counter grammar (conditional):

- acquire saves the thread ID and compares it with the QWORD owner; an equal
  owner increments the DWORD reentry count; otherwise LOCK XADD -1, then a
  signed-positive skip or an acquire call with RCX = the context handle
  QWORD; the continuation stores the ID and DWORD 1;
- release reloads the fresh stack slot, then bypasses, decrements or clears
  the owner, using DWORD arithmetic with a signed clamp and a CMPXCHG retry
  loop; on a negative previous count CMOVGE selects the negated count, then
  RCX = handle and EDX = release count;
- the Baselib thread-ID body visibly zero-extends a DWORD.

None of this names the lock, proves mutual exclusion, or selects a live callee.
"""
from __future__ import annotations
from collections import deque
from scripts.game_data.il2cpp.integer_addressing import decode_lea_address
from scripts.game_data.il2cpp.memory_moves import decode_memory_move, _register
from scripts.game_data.il2cpp.relation_control import _partition, transfer
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar

_TRACKED = ('rdi', 'rbp', 'r14', 'r9')
_ALIASES = {name: (backing, bits) for backing, names in {
    'rdi': ('rdi', 'edi', 'di', 'dil'), 'rbp': ('rbp', 'ebp', 'bp', 'bpl'),
    'r14': ('r14', 'r14d', 'r14w', 'r14b'), 'r9': ('r9', 'r9d', 'r9w', 'r9b')
}.items() for name, bits in zip(names, (64, 32, 16, 8))}
_READ_ONLY = {'cmp', 'test', 'push', 'nop', 'ret', 'cdqe'}
_WRITERS = {'mov', 'movzx', 'movsx', 'movsxd', 'lea', 'xor', 'add', 'sub',
            'and', 'inc', 'dec', 'shl', 'shr', 'sar', 'neg', 'cmovge', 'sete'}


def _effect(row):
    """Conservative writes to four registers in the closed instruction lane."""
    text = row['text']; head, _, rest = text.partition(' ')
    if head == 'call':
        return {'kind': 'call', 'clobber': 'r9'}
    if head in _READ_ONLY or head.startswith('j'):
        return None
    if head == 'lock':
        f = row['lockedMemoryExchangeOperation']
        # CMPXCHG writes RAX; XADD writes its explicit source. Neither may be
        # silently treated as preserving a tracked source in a future variant.
        source = f['sourceRegister'] if f['operation'] == 'xadd' else 'eax'
        return {'kind': 'unknown', 'destination': _ALIASES[source][0]} if source in _ALIASES else None
    if head == 'imul':
        if ',' not in rest:  # The accepted one-operand form writes RAX/RDX.
            return None
        head = 'sub'  # Conservative explicit first-operand overwrite.
    if head == 'pop':
        destination = rest
        if destination not in _ALIASES:
            return None
        return {'kind': 'unknown', 'destination': _ALIASES[destination][0]}
    if head not in _WRITERS:
        raise ValueError('relationImports.unhandled-register-effect:' + text)
    destination = rest.split(',')[0]
    if destination not in _ALIASES:
        return None
    backing, bits = _ALIASES[destination]
    raw = bytes.fromhex(row['bytes']); at = 0; rex = 0
    if raw[0] == 0x66:
        at += 1
    if 0x40 <= raw[at] <= 0x4f:
        rex = raw[at]; at += 1
    opcode = raw[at]; width = 64 if rex & 8 else 16 if raw[0] == 0x66 else 32
    if head == 'mov' and 0xb8 <= opcode <= 0xbf and bits in (32, 64):
        number = (opcode - 0xb8) | ((rex & 1) << 3)
        name = _register(number, width, bool(rex))[0]
        encoded = raw[at + 1:]
        if name != destination or len(encoded) != width // 8:
            raise ValueError('relationImports.constant-mov-encoding')
        return {'kind': 'constant', 'destination': backing, 'value': int.from_bytes(encoded, 'little')}
    if head in ('mov', 'xor') and opcode in (0x8b, 0x89, 0x33, 0x31) and len(raw) == at + 2:
        modrm = raw[at + 1]
        if modrm >> 6 == 3:
            reg = _register(((modrm >> 3) & 7) | ((rex & 4) << 1), width, bool(rex))[0]
            rm = _register((modrm & 7) | ((rex & 1) << 3), width, bool(rex))[0]
            dst, src = (reg, rm) if opcode in (0x8b, 0x33) else (rm, reg)
            if text != f'{head} {dst}, {src}' or dst != destination:
                raise ValueError('relationImports.register-move-encoding')
            if width in (32, 64) and head == 'xor' and dst == src:
                return {'kind': 'constant', 'destination': backing, 'value': 0}
            if width in (32, 64) and head == 'mov' and src in _ALIASES:
                return {'kind': 'copy', 'destination': backing, 'source': _ALIASES[src][0], 'bits': width}
    if head == 'lea':
        decoded = decode_lea_address(raw, 0, int(row['va'], 16))
        if decoded is None or decoded[1] != len(raw):
            raise ValueError('relationImports.constant-lea-encoding')
        f = decoded[0]['addressOperation']
        if f['destination'] != destination or f['destinationBits'] != bits:
            raise ValueError('relationImports.constant-lea-register')
        if f['ripRelative'] and bits == 64:
            return {'kind': 'constant', 'destination': backing, 'value': f['absoluteAddress']}
    return {'kind': 'unknown', 'destination': backing}


def _graph(rows, parent, base):
    tables = {base + t['jumpRva']: t for t in parent['tables']}
    edges = {}
    for row in rows:
        at = int(row['va'], 16); f = transfer(row); end = at + len(bytes.fromhex(row['bytes']))
        targets = []
        if f['kind'] in ('jump', 'conditional'):
            targets.append(f['target'])
        if f['kind'] in ('next', 'conditional', 'call', 'indirectCall'):
            targets.append(end)
        if f['kind'] == 'tableJump':
            targets.extend(base + rva for rva in tables[at]['targetValues'])
        edges[at] = set(targets)
    if any(target not in edges for targets in edges.values() for target in targets):
        raise ValueError('relationImports.cfg-boundary')
    return edges


def _constants(rows, edges, entry):
    by_at = {int(row['va'], 16): row for row in rows}
    effects = {at: _effect(row) for at, row in by_at.items()}
    incoming = {entry: (None,) * len(_TRACKED)}; pending = deque([entry])
    while pending:
        at = pending.popleft(); state = list(incoming[at]); f = effects[at]
        if f:
            destination = f.get('destination', f.get('clobber'))
            slot = _TRACKED.index(destination)
            if f['kind'] == 'constant':
                state[slot] = f['value']
            elif f['kind'] == 'copy':
                value = state[_TRACKED.index(f['source'])]
                state[slot] = None if value is None else value & ((1 << f['bits']) - 1)
            else:
                state[slot] = None
        outgoing = tuple(state)
        for target in edges[at]:
            old = incoming.get(target)
            new = outgoing if old is None else tuple(a if a == b else None for a, b in zip(old, outgoing))
            if new != old:
                incoming[target] = new; pending.append(target)
    return incoming, effects


def _memory(g, direction, register, size, *, absolute=None, base=None, displacement=0):
    row = g.row(); raw = bytes.fromhex(row['bytes'])
    decoded = decode_memory_move(raw, 0, int(row['va'], 16))
    if decoded is None or decoded[1] != len(raw):
        g.fail('memory-encoding', 'complete GP move', row)
    f = decoded[0]['memoryOperation']; address = f['address']
    if (f['direction'], f['register'], f['memoryBytes']) != (direction, register, size):
        g.fail('memory-width-register', (direction, register, size), f)
    _address(g, address, absolute=absolute, base=base, displacement=displacement)
    return row


def _address(g, address, *, absolute=None, base=None, displacement=0):
    if absolute is not None:
        correct = address['ripRelative'] and address.get('absoluteAddress') == absolute
    else:
        correct = (not address['ripRelative'] and
                   (address['base'], address['index'], address['displacement']) == (base, None, displacement))
    if not correct:
        g.fail('physical-address', (absolute, base, displacement), address)


def _lea(g, register, *, absolute=None, displacement=None):
    row = g.row(); raw = bytes.fromhex(row['bytes'])
    decoded = decode_lea_address(raw, 0, int(row['va'], 16))
    if decoded is None or decoded[1] != len(raw):
        g.fail('lea-encoding', 'complete LEA', row)
    f = decoded[0]['addressOperation']
    if (f['destination'], f['destinationBits']) != (register, 64):
        g.fail('lea-register', register, f)
    _address(g, f, absolute=absolute, base='rsp', displacement=displacement or 0)
    return row


def _branch(g, kind, target):
    row = g.row(); f = transfer(row)
    codes = {'je': 4, 'jne': 5, 'jg': 15, 'jle': 14, 'jns': 9}
    expected_kind = 'jump' if kind == 'jmp' else 'conditional'
    if f['kind'] != expected_kind or f.get('target') != target or (
            kind != 'jmp' and f.get('conditionCode') != codes[kind]):
        g.fail('branch-predicate-target', (kind, target), f)
    return row


def _import(g, slot):
    row = g.row(); f = transfer(row)
    if f != {'kind': 'indirectCall', 'cell': slot}:
        g.fail('selected-import-call', slot, f)
    return row


def _exchange(g, operation, register, *, absolute=None, displacement=0):
    row = g.row(); f = row.get('lockedMemoryExchangeOperation', {})
    if (f.get('operation'), f.get('bits'), f.get('sourceRegister'), f.get('locked')) != (operation, 32, register, True):
        g.fail('locked-dword-exchange', (operation, register), f)
    _address(g, f['destinationAddress'], absolute=absolute, base='r8', displacement=displacement)
    return row


def _step(g, operation, *, absolute=None, displacement=0):
    row = g.row(); f = row.get('memoryStepOperation', {})
    if (f.get('operation'), f.get('bits'), f.get('locked')) != (operation, 32, False):
        g.fail('memory-dword-step', operation, f)
    _address(g, f['destinationAddress'], absolute=absolute, base='r8', displacement=displacement)


def _slice(rows, base, start, end):
    selected = [row for row in rows if base + start <= int(row['va'], 16) < base + end]
    if not selected or int(selected[0]['va'], 16) != base + start or (
            int(selected[-1]['va'], 16) + len(bytes.fromhex(selected[-1]['bytes'])) != base + end):
        raise ValueError('relationImports.selected-block-boundary')
    return selected


def _no_bypass(selected, edges, entries):
    cohort = {int(row['va'], 16) for row in selected}
    for source, targets in edges.items():
        if source in cohort:
            continue
        if any(target in cohort and target not in entries for target in targets):
            raise ValueError('relationImports.selected-block-interior-entry')


def validate_relation_import_control(index, parent, contract, parent_summary):
    rows = _partition(index, parent); base = index.pe.image_base
    edges = _graph(rows, parent, base)
    states, effects = _constants(rows, edges, base + parent['entryRva'])
    if len(states) != parent_summary['staticPossibleReachableInstructions']:
        raise ValueError('relationImports.constant-cfg-coverage')
    slots = {row['role']: base + row['slotRva'] for row in contract['imports']}
    if set(slots) != {'ThreadId', 'Acquire', 'Release'} or len(set(slots.values())) != 3:
        raise ValueError('relationImports.import-roles')
    offsets = contract['contextOffsets']; context = base + contract['globalContextRva']
    owner = context + offsets['owner']; counter = context + offsets['reentry']; count = context + offsets['count']
    checked = []; expected_sites = []; blocks = []
    for block in contract['blocks']:
        a = _slice(rows, base, block['acquisitionStartRva'], block['acquisitionEndRva'])
        b = _slice(rows, base, block['sameOwnerStartRva'], block['contextCallEndRva'])
        r = _slice(rows, base, block['releaseStartRva'], block['releaseEndRva'])
        cohort = {int(row['va'], 16) for row in a + b + r}
        if any(base + call['targetRva'] in cohort for call in parent['directCalls']):
            raise ValueError('relationImports.direct-call-enters-selected-block')
        _no_bypass(a + b + r, edges, {base + block['acquisitionStartRva']})
        g = ProgramGrammar(a, label='relationImports.acquire.' + block['role'])
        if block['contextSource'] == 'rax':
            _lea(g, 'rax', absolute=context)
        elif block['contextSource'] != 'r9':
            g.fail('context-source', 'rax or r9', block['contextSource'])
        store = _memory(g, 'store', block['contextSource'], 8, base='rsp', displacement=block['stackOffset'])
        if block['contextSource'] == 'r9':
            checked.append((int(store['va'], 16), 'r9', context))
        thread_call = _import(g, slots['ThreadId']); g.take('mov rbx, rax')
        _memory(g, 'load', 'rcx', 8, absolute=owner)
        if block['counterInit'] == 'ebp-before-compare':
            g.take('mov ebp, 0x1')
        g.take('cmp rax, rcx'); _branch(g, 'je', base + block['sameOwnerStartRva'])
        reg = block['decrementRegister']
        if block['decrementSource'] == 'immediate':
            g.take(f'mov {reg}, 0xffffffff')
        elif block['decrementSource'] == 'r14d':
            move = g.take(f'mov {reg}, r14d'); checked.append((int(move['va'], 16), 'r14', 0xffffffff))
        else:
            g.fail('decrement-source', 'immediate or r14d', block['decrementSource'])
        _exchange(g, 'xadd', reg, absolute=count); g.take(f'test {reg}, {reg}')
        _branch(g, 'jg', base + block['ownerStoreRva'])
        _memory(g, 'load', 'rcx', 8, absolute=context); acquire_call = _import(g, slots['Acquire'])
        owner_store = _memory(g, 'store', 'rbx', 8, absolute=owner)
        if int(owner_store['va'], 16) != base + block['ownerStoreRva']:
            g.fail('owner-store-join', block['ownerStoreRva'], owner_store)
        if block['counterInit'] == 'immediate-store':
            row = g.row(); f = row.get('immediateMemoryStoreOperation', {})
            if (f.get('bits'), f.get('immediateWord')) != (32, 1):
                g.fail('counter-literal-one', 'DWORD one', f)
            _address(g, f['destinationAddress'], absolute=counter)
        elif block['counterInit'] in ('ebp-before-compare', 'ebp-from-prefix'):
            row = _memory(g, 'store', 'ebp', 4, absolute=counter)
            checked.append((int(row['va'], 16), 'rbp', 1))
        else:
            g.fail('counter-init', 'checked counter initializer', block['counterInit'])
        _branch(g, 'jmp', base + block['contextJoinRva']); g.finish()
        g = ProgramGrammar(b, label='relationImports.context.' + block['role'])
        _step(g, 'inc', absolute=counter)
        if int(b[1]['va'], 16) != base + block['contextJoinRva']:
            g.fail('same-owner-join', block['contextJoinRva'], b[1])
        _lea(g, 'rdx', displacement=block['stackOffset'])
        if block['childReceiver'] == 'r13':
            g.take('mov rcx, r13')
        elif block['childReceiver'] == 'stack':
            _memory(g, 'load', 'rcx', 8, base='rsp', displacement=block['childReceiverStackOffset'])
        else:
            g.fail('child-receiver', 'r13 or stack', block['childReceiver'])
        g.call(base + block['childRva']); g.take('nop'); g.finish()
        if block['contextCallEndRva'] != block['releaseStartRva']:
            raise ValueError('relationImports.context-to-fresh-load')
        g = ProgramGrammar(r, label='relationImports.release.' + block['role'])
        _memory(g, 'load', 'r8', 8, base='rsp', displacement=block['stackOffset'])
        tail = base + block['releaseEndRva']; field = offsets['reentry']
        g.take(f'cmp dword [r8+0x{field:x}], 0x0'); _branch(g, 'jle', tail)
        g.take(f'cmp dword [r8+0x{field:x}], 0x1'); _branch(g, 'jne', base + block['decrementReentryRva'])
        for register, size, offset in [('rdi', 8, offsets['owner']), ('edi', 4, field)]:
            row = _memory(g, 'store', register, size, base='r8', displacement=offset)
            checked.append((int(row['va'], 16), 'rdi', 0))
        step = block['releaseStepRegister']
        if block['releaseStepSource'] == 'one':
            g.take('mov r9d, 0x1')
        elif block['releaseStepSource'] == 'ebp':
            row = g.take('mov r9d, ebp'); checked.append((int(row['va'], 16), 'rbp', 1))
        elif block['releaseStepSource'] != 'existing-ebp':
            g.fail('release-step-source', 'one, ebp or existing-ebp', block['releaseStepSource'])
        row = _memory(g, 'load', 'edx', 4, base='r8', displacement=offsets['count'])
        if block['releaseStepSource'] == 'existing-ebp':
            checked.append((int(row['va'], 16), 'rbp', 1))
        if g.cursor < len(g.rows) and g.rows[g.cursor]['text'] == 'nop':
            g.take('nop')
        if int(g.rows[g.cursor]['va'], 16) != base + block['retryRva']:
            g.fail('retry-entry', block['retryRva'], g.rows[g.cursor])
        g.take(f'cmp edx, [r8+0x{offsets["limit"]:x}]'); _branch(g, 'je', tail)
        backing = 'rbp' if step == 'ebp' else 'r9'
        g.take(f'lea eax, [rdx+{backing}*1]', f'cmp eax, [r8+0x{offsets["limit"]:x}]')
        _branch(g, 'jle', base + block['exchangeCandidateRva'])
        _memory(g, 'load', step, 4, base='r8', displacement=offsets['limit']); g.take(f'sub {step}, edx')
        if int(g.rows[g.cursor]['va'], 16) != base + block['exchangeCandidateRva']:
            g.fail('clamp-join', block['exchangeCandidateRva'], g.rows[g.cursor])
        g.take(f'lea ecx, [rdx+{backing}*1]', 'mov eax, edx')
        _exchange(g, 'cmpxchg', 'ecx', displacement=offsets['count'])
        _branch(g, 'je', base + block['exchangeSuccessRva']); g.take('mov edx, eax')
        _branch(g, 'jmp', base + block['retryRva'])
        if int(g.rows[g.cursor]['va'], 16) != base + block['exchangeSuccessRva']:
            g.fail('exchange-success-join', block['exchangeSuccessRva'], g.rows[g.cursor])
        g.take('test edx, edx'); _branch(g, 'jns', tail)
        g.take('neg edx', f'cmp {step}, edx', f'cmovge {step}, edx', f'mov edx, {step}')
        _memory(g, 'load', 'rcx', 8, base='r8', displacement=offsets['handle'])
        release_call = _import(g, slots['Release']); _branch(g, 'jmp', tail)
        if int(g.rows[g.cursor]['va'], 16) != base + block['decrementReentryRva']:
            g.fail('decrement-reentry-join', block['decrementReentryRva'], g.rows[g.cursor])
        _step(g, 'dec', displacement=field); g.finish()
        for role, row in [('ThreadId', thread_call), ('Acquire', acquire_call), ('Release', release_call)]:
            expected_sites.append({'siteRva': int(row['va'], 16) - base, 'cellRva': slots[role] - base})
        blocks.append({'role': block['role'], 'checkedGrammarInstructions': len(a) + len(b) + len(r),
                       'childRva': block['childRva'], 'postChildContextPointerTreatedAsFresh': True})
    actual = parent_summary['indirectCallStorageSites']
    if sorted(expected_sites, key=lambda r: r['siteRva']) != actual:
        raise ValueError('relationImports.complete-selected-site-coverage')
    requirements = []
    for at, register, expected in checked:
        actual_value = states.get(at, (None,) * len(_TRACKED))[_TRACKED.index(register)]
        if actual_value != expected:
            raise ValueError(f'relationImports.constant-flow: site={at-base} register={register} expected={expected} actual={actual_value}')
        requirements.append({'siteRva': at - base, 'register': register, 'value': expected})
    return {'completeParentControlRechecked': True, 'constantFlowCfgInstructions': len(states),
        'checkedGrammarInstructions': sum(b['checkedGrammarInstructions'] for b in blocks),
        'checkedImportCallSites': expected_sites, 'checkedBlocks': blocks,
        'checkedIncomingConstantRequirements': requirements,
        'trackedRegisterWriteSites': [{'siteRva': at-base, **f} for at, f in effects.items() if f and f['kind'] != 'call'],
        'counterReleaseArithmeticBits': 32, 'releaseCountUsesSignedClampAndNegatedPreviousCounter': True,
        'compareExchangeFailureReloadsPreviousCounterAndRetries': True,
        'acquireConditionalOnDifferentOwnerAndNonpositivePreviousCounter': True,
        'sameOwnerPathIncrementsDwordReentryWithoutAcquire': True,
        'conditionalZeroOwnerAndReentryStoresProved': True,
        'postChildContextPointerEqualsOriginalGlobalProved': False,
        'childSlotMutationOrFullEffectsProved': False, 'liveIatValueOrCalleeSelected': False,
        'synchronizationInitializationOrLiveOutcomeProved': False, 'recursiveTerminationProved': False,
        'callbackCursorEqualityProved': False, 'positiveListAdmitted': False, 'wholeRootAdmitted': False}

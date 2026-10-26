"""Literal nonvolatile zero provenance over a complete ordinary code graph.

Every computed dispatch comes from the caller's proved code/table partition.
All ordinary edges are considered; branch feasibility is never invented.
Normal called Win64 helpers preserving the selected nonvolatile register is
an explicit condition. Exception/resumption entries remain outside this graph.
"""
import re

from .initializer_control import _ALIASES

LABEL = 'constantRegisterSource'
REGISTERS = {'rbx': 3, 'rbp': 5, 'r12': 12, 'r13': 13, 'r14': 14, 'r15': 15}


def need(check, condition, detail=None):
    if not condition:
        raise ValueError(LABEL + '.' + check + ':' + str(detail)[:600])


def _reached(edges, entry, blocked):
    pending = [entry]; seen = set()
    while pending:
        at = pending.pop()
        if at in seen or at in blocked:
            continue
        seen.add(at); pending.extend(edges[at] - seen)
    return seen


def _writes(row, register):
    from .body_claims import _writes_register
    from .initializer_control import control_transfer
    op = row['text'].partition(' ')[0]
    ordinary = op in ('mov', 'movzx', 'movsx', 'movsxd', 'lea', 'push', 'pop',
        'cmp', 'test', 'xor', 'and', 'or', 'add', 'sub', 'adc', 'sbb', 'inc', 'dec',
        'shl', 'shr', 'sar', 'rol', 'ror', 'rcl', 'rcr', 'imul', 'mul', 'bt', 'bts', 'btr', 'btc',
        'cdqe', 'cdq', 'cqo', 'cwd', 'nop', 'prefetch', 'int3', 'jmp', 'call',
        'movaps', 'movups', 'movsd', 'movss', 'movdqa', 'movdqu', 'xorps', 'pxor')
    atomic = bool(row.get('implicitMemoryExchangeOperation') or row.get('lockedMemoryExchangeOperation'))
    transfer = control_transfer(row)['kind'] in ('call', 'indirectCall', 'registerCall', 'jump', 'conditional', 'return')
    need('complete-instruction-register-effect', ordinary or atomic or transfer or op.startswith(('cmov', 'set')), row)
    if _writes_register(row, register):
        return True
    operands = row['text'].partition(' ')[2]
    destination = _ALIASES.get(operands.partition(',')[0], operands.partition(',')[0])
    if (op.startswith(('cmov', 'set')) or op in ('bts', 'btr', 'btc', 'rol', 'ror', 'rcl', 'rcr')) and destination == register:
        return True
    for key in ('implicitMemoryExchangeOperation', 'lockedMemoryExchangeOperation'):
        effect = row.get(key, {})
        written = []
        if effect.get('operation') in ('xchg', 'xadd'):
            written += [effect.get('register'), effect.get('sourceRegister')]
        if effect.get('operation') == 'cmpxchg':
            written += [effect.get('accumulatorRegister')]
        if any(_ALIASES.get(r, r) == register for r in written if r):
            return True
    # A register xchg has two destinations. The ordinary mapper does not give
    # this component a complete two-register effect; refuse any such use.
    mentioned = register in {_ALIASES.get(r, r) for r in re.findall(
        r'\b(?:r(?:1[0-5]|[89])(?:d|w|b)?|[re]?[abcd]x|[re]?(?:si|di|bp|sp)|[abcd][lh])\b', row['text'])}
    if mentioned:
        known = op in ('mov', 'movzx', 'movsx', 'movsxd', 'lea', 'push', 'pop',
            'cmp', 'test', 'xor', 'and', 'or', 'add', 'sub', 'adc', 'sbb', 'inc', 'dec',
            'shl', 'shr', 'sar', 'rol', 'ror', 'rcl', 'rcr', 'imul', 'mul', 'bt', 'bts', 'btr', 'btc',
            'call', 'jmp', 'prefetch') or op.startswith(('cmov', 'set'))
        modeled_atomic = bool(row.get('implicitMemoryExchangeOperation') or row.get('lockedMemoryExchangeOperation'))
        need('complete-explicit-register-use', known or modeled_atomic, row)
    return False


def prove(part, *, entry, register, sites, image_base):
    """Prove full zero on every ordinary path to each requested instruction."""
    from scripts.game_data.memorypack.generated_owned_code_sources import base_certificate
    need('explicit-nonvolatile-domain', register in REGISTERS)
    need('bounded-distinct-sites', type(sites) is list and 0 < len(sites) <= 64 and
         all(type(at) is int for at in sites) and len(set(sites)) == len(sites))
    # Current source reports serialize integer dictionary keys as decimal
    # strings. Rebuilding that representation does not supply missing edges.
    jumps = part.get('computedJumpTargets', {})
    need('literal-computed-site-keys', all(type(at) is int or type(at) is str and at.isdecimal()
                                          for at in jumps))
    converted = {int(at): targets for at, targets in jumps.items()}
    need('unique-computed-site-keys', len(converted) == len(jumps))
    part = dict(part, computedJumpTargets=converted)
    dispatch = base_certificate(part, entry=entry, image_base=image_base)
    need('current-literal-computed-dispatch-bases', dispatch['allTableGuardsCannotBeBypassed'] is True and
         dispatch['allDispatchBasesEqualSelectedImageBase'] is True)
    return _prove_graph(part['rows'], dispatch['ordinaryEntry']['fullGraph'], entry=entry,
        register=register, sites=sites, certificates=dispatch['certificates'])


def _prove_graph(rows, graph, *, entry, register, sites, certificates):
    edges = graph['edges']
    reachable = set(graph['reachableInstructions']); targets = set(sites)
    need('reachable-requested-sites', targets <= reachable)
    number = REGISTERS[register]
    modrm = bytes((0xc0 | ((number & 7) << 3) | (number & 7),))
    prefix = b'\x45' if number >= 8 else b''
    zero32 = prefix + b'\x33' + modrm
    zero64 = (b'\x4d' if number >= 8 else b'\x48') + b'\x33' + modrm
    definitions = []; kills = []
    for row in rows:
        at = int(row['va'], 16)
        if at not in reachable:
            continue
        if bytes.fromhex(row['bytes']) in (zero32, zero64):
            definitions.append(at)
        elif _writes(row, register):
            kills.append(at)
    need('literal-whole-register-zero-definition', bool(definitions))
    blocked = set(definitions)
    need('zero-definitions-dominate-requested-sites', not targets & _reached(edges, entry, blocked))
    for at in kills:
        bypass = set().union(*(_reached(edges, following, blocked) for following in edges[at])) if edges[at] else set()
        need('no-nonzero-write-reaches-site-without-reset', not targets & bypass,
             dict(write=hex(at), targets=[hex(t) for t in sorted(targets & bypass)]))
    return dict(register=register, value=0, sites=sites,
        literalZeroInstructions=[[at, next(row['bytes'] for row in rows if int(row['va'], 16) == at)]
                                 for at in definitions],
        explicitWritesChecked=kills, completeOrdinaryGraphProved=True,
        zeroOnEveryOrdinaryPath=True, computedDispatchGuardsProved=True,
        literalDispatchBasesProved=certificates,
        normalCalleesPreserveNonvolatileRequired=True,
        exceptionOrResumptionAdmitted=False, runtimeValueObserved=False,
        condition='Ordinary current entry, complete guarded code/table graph and normal ABI-preserving called helpers. Every path to the requested instruction crosses a literal whole-register zero and no later nonzero write can reach it without another zero.')


def prove_ordinary_family(rows, *, entry, register, sites, owned_ranges):
    'Full discontiguous ordinary byte/edge/frame graph with no computed jump.'
    from .consumer_entry_program import ordinary_consumer_entry
    need('explicit-nonvolatile-domain', register in REGISTERS)
    need('bounded-distinct-sites', type(sites) is list and 0 < len(sites) <= 64 and
         all(type(at) is int for at in sites) and len(set(sites)) == len(sites))
    ordinary = ordinary_consumer_entry(rows, entry=entry, owned_ranges=owned_ranges)
    result = _prove_graph(rows, ordinary['fullGraph'], entry=entry,
        register=register, sites=sites, certificates=[])
    result.update(ordinaryFamilyRanges=[list(pair) for pair in owned_ranges],
        computedDispatchesPresent=False, ordinaryControlAndStackFramesProved=True)
    return result


def disabled_guard(row, zero, *, flag_va):
    """Join one actual DWORD RIP compare with the independently proved zero."""
    op = row.get('memoryRegisterComparisonOperation', {})
    address = op.get('memoryAddress', {})
    need('actual-zero-guard', zero.get('zeroOnEveryOrdinaryPath') is True and
         zero.get('value') == 0 and int(row['va'], 16) in zero.get('sites', []) and
         op.get('bits') == 32 and _ALIASES.get(op.get('register')) == zero.get('register') and
         op.get('memoryReadBytes') == 4 and op.get('memoryWriteBytes') == 0 and
         op.get('memoryIsLeftOperand') is True and op.get('preservesRegisters') is True and
         address.get('ripRelative') is True and address.get('absoluteAddress') == flag_va)
    return dict(instruction=[int(row['va'], 16), row['bytes']], flagVa=flag_va,
                compareBytes=4, register=zero['register'], comparedValue=0,
                zeroProof=zero, disabledOutcomeObserved=False)

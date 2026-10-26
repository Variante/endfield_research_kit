"""Finite cached factories with initialized ancestors and scalar defaults.

The selected path owns every executed byte, actual allocation/constructor and
holder argument, both successful same-class predicates, and the restored frame.
Each inlined scalar store must equal an independently proved Original default.
Metadata initialization, allocation/constructor effects, compatible predicates
and disabled collectors remain conditions. No wire or parent grammar is granted.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL = 'generatedConditionFactory'
LARGE_PROFILE = 'initialized-ancestor-rsi-inline-collector-factory.v1'
SMALL_PROFILE = 'called-ancestor-literal-class-factory.v1'


def need(check, condition, detail=None):
    if not condition:
        raise ValueError(LABEL + '.' + check + ':' + str(detail)[:700])


def _peek(g, count=1):
    need('owned-lookahead', all(g.at+i in g.bytes for i in range(count)), hex(g.at))
    return bytes(g.bytes[g.at+i] for i in range(count))


def _initialized(g):
    from scripts.game_data.memorypack.generated_lifecycle_sources import _initialized as select
    select(g)


def _flag(g):
    cell = g.relative('803d') + 1
    g.take('00')
    return cell


def _defaults(initializers):
    need('finite-independent-Original-defaults', type(initializers) is list and 0 < len(initializers) <= 32)
    expected = {}; occupied = set()
    for store in initializers:
        offset, width, bits = store.get('offset'), store.get('bytes'), store.get('constantHex')
        need('literal-default', type(offset) is int and 16 <= offset < 2**31
             and type(width) is int and width in (1, 2, 4)
             and type(bits) is str and len(bits) == width*2)
        raw = bytes.fromhex(bits); span = set(range(offset, offset+width))
        need('disjoint-defaults', not occupied & span)
        occupied.update(span); expected[(offset, width)] = raw
    return expected


def _inline_defaults(g, initializers, *, ctor):
    expected = _defaults(initializers); arguments = set(); stores = []
    g.take('4533c0'); arguments.add('r8')
    if not ctor:
        g.take('48897c2450')
    for _ in range(64):
        if not expected and arguments == {'r8', 'rdx', 'rcx'}:
            return stores
        prefix = _peek(g, 3)
        if prefix == bytes.fromhex('488bd0'):
            need('one-unchanged-allocation-argument', 'rdx' not in arguments)
            g.take('488bd0'); arguments.add('rdx'); continue
        if prefix == bytes.fromhex('488bce'):
            need('one-wrapper-receiver', 'rcx' not in arguments)
            g.take('488bce'); arguments.add('rcx'); continue
        at = g.at; width = 2 if prefix[:1] == b'\x66' else 1 if prefix[:1] == b'\xc6' else 4
        if width == 2:
            g.take('66')
        g.take('c6' if width == 1 else 'c7'); modrm = g.read(1)[0]
        need('only-immediate-same-allocation-store', modrm in (0x40, 0x80))
        offset = int.from_bytes(g.read(1 if modrm == 0x40 else 4), 'little', signed=True)
        value = g.read(width); key = (offset, width)
        need('same-independent-Original-default', key in expected and expected[key] == value,
             (key, value.hex(), [(k, v.hex()) for k, v in expected.items()]))
        del expected[key]
        stores.append(dict(instructionVa=at, offset=offset, bytes=width, constantHex=value.hex().upper()))
    raise ValueError(LABEL + '.bounded-default-and-argument-program')


def _large_prefix(g, *, ctor, image_base):
    extra = False
    if not ctor:
        g.take('48895c2410', '48896c2420', '56', '4883ec40'); profile = 'create-frame64'
    elif _peek(g, 3) == bytes.fromhex('488bc4'):
        g.take('488bc4', '53', '55', '56', '57', '4883ec58'); profile = 'constructor-frame88'; extra = True
    elif _peek(g, 2) == bytes.fromhex('4053'):
        g.take('4053', '55', '56', '57', '4883ec48'); profile = 'constructor-frame72'
    else:
        g.take('48895c2408', '48896c2410', '56', '57', '4154', '4156', '4157', '4883ec70')
        profile = 'constructor-frame112'
    flag = _flag(g)
    need('literal-image-base', g.relative('488d2d') == image_base)
    unused = []
    if extra:
        g.take('4c896008'); unused.append(g.relative('488d1d'))
        g.take('4c897010'); unused.append(g.relative('4c8d25')); g.take('4c8978d8', '488bf1', '49bf')
        g.read(8); g.take('49be'); g.read(8)
    else:
        g.take('488bf1')
        if profile == 'constructor-frame112':
            unused.append(g.relative('488d3d')); g.take('49be'); g.read(8)
            unused.append(g.relative('4c8d25')); g.take('49bf'); g.read(8)
    _initialized(g)
    return profile, flag, unused


def large_program(regions, entry, *, ctor, original_ctor, base_slot, cache_slot,
                  image_base, disabled, original_initializers=None, base_ctor=None):
    """Own one initialized large-factory path; caller binds all nominal roles."""
    need('literal-role-domain', type(ctor) is bool and type(base_slot) is int and type(cache_slot) is int
         and 16 <= base_slot < cache_slot < 128 and all(type(n) is int and n > 0 for n in (image_base, disabled))
         and (original_ctor is None or type(original_ctor) is int and original_ctor > 0)
         and (base_ctor is None or ctor and type(base_ctor) is int and base_ctor > 0))
    g = BytesPath(regions, entry); frame, flag, unused = _large_prefix(g, ctor=ctor, image_base=image_base)
    flags = [flag]; ancestors = []; base_called = False; restored_extra = False
    for _ in range(8):
        if _peek(g, 2) == b'\x80\x3d':
            flags.append(_flag(g)); _initialized(g); continue
        if _peek(g, 3) == bytes.fromhex('33d248'):
            need('one-explicit-owned-base-constructor', base_ctor is not None and not base_called)
            g.take('33d2', '488bce'); g.call(base_ctor); base_called = True; continue
        site = g.at; cell = g.relative('488b0d'); usage = dict(site=site, cell=cell)
        if _peek(g, 5) == bytes.fromhex('4c8b7c2450'):
            need('one-exact-extra-register-restoration', frame == 'constructor-frame88' and not restored_extra)
            g.take('4c8b7c2450', '4c8bb42488000000', '4c8ba42480000000'); restored_extra = True
        if _peek(g, 2) == bytes.fromhex('83b9'):
            g.take('83b9e000000000'); _initialized(g); ancestors.append(usage); continue
        allocation = usage; allocate = g.relative('e8'); break
    else:
        raise ValueError(LABEL + '.bounded-initialized-ancestor-program')
    need('exact-base-constructor-invocation', base_called == (base_ctor is not None))
    need('all-extra-registers-restored', restored_extra == (frame == 'constructor-frame88'))
    from scripts.game_data.memorypack.generated_lifecycle_sources import _nonnull
    if original_ctor is None:
        g.take('4885c0'); _nonnull(g)
        stores = _inline_defaults(g, original_initializers, ctor=ctor)
    else:
        g.take('488bd8', '4885c0'); _nonnull(g); g.take('33d2')
        if not ctor:
            g.take('48897c2450')
        g.take('488bc8'); g.call(original_ctor)
        g.take('4533c0', '488bd3', '488bce'); stores = None
    setter = g.relative('e8'); b, c = bytes((base_slot,)).hex(), bytes((cache_slot,)).hex()
    g.take('488b5e'+b); usages = []; predicates = []
    site = g.at; cell = g.relative('488b3d'); usages.append(dict(site=site, cell=cell))
    g.take('4885db'); _nonnull(g)
    for ordinal in range(2):
        g.take('488b0b', '488bd7'); predicates.append(g.relative('e8')); g.take('84c0')
        _initialized(g)
        if not ordinal:
            g.take('48895e'+c); site = g.at; cell = g.relative('488b3d'); usages.append(dict(site=site, cell=cell))
    need('same-actual-class-and-predicate', predicates[0] == predicates[1]
         and all(u['cell'] == allocation['cell'] for u in usages))
    g.jump('e9'); need('same-disabled-collector', g.relative('833d')+1 == disabled)
    g.take('00'); g.branch('74', True, 1)
    if frame == 'create-frame64':
        g.take('488b7c2450', '488b5c2458', '488b6c2468', '4883c440', '5e', 'c3')
    elif frame == 'constructor-frame72':
        g.take('4883c448', '5f', '5e', '5d', '5b', 'c3')
    elif frame == 'constructor-frame88':
        g.take('4883c458', '5f', '5e', '5d', '5b', 'c3')
    else:
        g.take('4c8d5c2470', '498b5b30', '498b6b38', '498be3', '415f', '415e', '415c', '5f', '5e', 'c3')
    restored = ['rbx', 'rbp', 'rsi', 'rdi']
    if frame in ('constructor-frame88', 'constructor-frame112'):
        restored += ['r12', 'r14', 'r15']
    result = dict(selectedBytes=g.seen, factoryProfile=LARGE_PROFILE, frameProfile=frame,
                  holderSourceProfile='rsi-wrapper-rbp-image-base-inline-collector', initializedFlag=flag,
                  initializedFlags=flags, unusedInitializerAddresses=unused, constructor=ctor,
                  allocation=allocation, allocationTarget=allocate, baseClassUsage=None,
                  ancestorClassUsages=ancestors, baseReady=None, baseConstructorTarget=base_ctor,
                  instanceSetter=setter, strictCast=None, classUsages=usages,
                  inlineStrictCasts=dict(sameBaseReferenceCached=True, successfulPredicateConditional=True,
                      runtimePredicateOutcomeObserved=False, predicateTarget=predicates[0], entryRspRestored=True,
                      nonvolatilesRestored=restored), baseHolderOffset=base_slot, typedCacheOffset=cache_slot,
                  originalConstructorCalled=original_ctor is not None, originalConstructorTarget=original_ctor,
                  originalConstructorEffectsProved=False, normalReturnViaBarrier=False,
                  disabledCollectorCell=disabled, disabledCollectorRequired=True, entryRspRestored=True,
                  nonvolatileRegistersRestored=restored, metadataInitializerExecutionClaimed=False,
                  parentOrWireGrammarAdmitted=False, condition=__doc__)
    if stores is not None:
        result.update(inlinedOriginalInitializers=original_initializers, actualDefaultStores=stores)
    return result


def literal_program(regions, entry, barrier, *, ctor, original_ctor, base_slot, cache_slot, base_ctor=None):
    """Exact small literal-class path with an optional actual ancestor call."""
    from scripts.game_data.memorypack.generated_lifecycle_sources import _nonnull
    need('literal-small-roles', type(ctor) is bool and type(original_ctor) is int and original_ctor > 0
         and type(base_slot) is int and type(cache_slot) is int and 16 <= base_slot < cache_slot < 128
         and type(barrier) is int and barrier > 0
         and (base_ctor is None or ctor and type(base_ctor) is int and base_ctor > 0))
    g = BytesPath(regions, entry); g.take('48895c2408', '57', '4883ec20')
    flag = _flag(g); g.take('488bd9'); _initialized(g); ancestor = None
    if ctor:
        site = g.at; cell = g.relative('488b0d'); ancestor = dict(site=site, cell=cell)
        g.take('83b9e000000000'); _initialized(g)
        need('explicit-actual-base-constructor', base_ctor is not None)
        g.take('33d2', '488bcb'); g.call(base_ctor)
    site = g.at; cell = g.relative('488b0d'); allocation = dict(site=site, cell=cell)
    allocate = g.relative('e8'); g.take('488bf8', '4885c0'); _nonnull(g); g.take('33d2')
    g.take('488bc8' if ctor else '488bcf'); g.call(original_ctor)
    g.take('4533c0', '488bd7', '488bcb'); setter = g.relative('e8')
    b, c = bytes((base_slot,)).hex(), bytes((cache_slot,)).hex()
    g.take('488b4b'+b); usages = []; comparisons = []
    site = g.at; cell = g.relative('488b15'); usages.append(dict(site=site, cell=cell))
    g.take('4885c9'); _nonnull(g); comparisons.append(g.at); g.take('483911'); g.branch('75', False, 1)
    g.take('48894b'+c if ctor else '488bc1')
    if not ctor:
        g.take('488943'+c)
    site = g.at; cell = g.relative('488b15'); usages.append(dict(site=site, cell=cell))
    if not ctor:
        g.take('4885c9'); _nonnull(g)
    comparisons.append(g.at); g.take('483911'); g.branch('75' if ctor else '74', not ctor, 1)
    need('same-actual-literal-class', all(u['cell'] == allocation['cell'] for u in usages))
    g.take('488d4b'+c, '488b5c2430', '4883c420', '5f'); need('same-restored-barrier', g.relative('e9') == barrier)
    return dict(selectedBytes=g.seen, factoryProfile=SMALL_PROFILE, initializedFlag=flag, constructor=ctor,
                allocation=allocation, allocationTarget=allocate, baseClassUsage=ancestor, baseReady=None,
                baseConstructorTarget=base_ctor, instanceSetter=setter, strictCast=None, classUsages=usages,
                inlineStrictCasts=dict(predicateMode='literal-class-equality', comparisonSites=comparisons,
                    sameBaseReferenceCached=True, successfulPredicateConditional=True,
                    runtimePredicateOutcomeObserved=False, entryRspRestored=True, nonvolatilesRestored=['rbx', 'rdi']),
                baseHolderOffset=base_slot, typedCacheOffset=cache_slot, originalConstructorCalled=True,
                originalConstructorTarget=original_ctor, originalConstructorEffectsProved=False,
                normalReturnViaBarrier=True, entryRspRestored=True, nonvolatileRegistersRestored=['rbx', 'rdi'],
                metadataInitializerExecutionClaimed=False, parentOrWireGrammarAdmitted=False, condition=__doc__)

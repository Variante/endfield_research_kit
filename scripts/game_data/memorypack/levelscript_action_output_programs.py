"""Exact ParamOutput call schedules; no value-of-T wire inference."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check, condition):
    if not condition:
        raise ValueError('actionOutputProgram.'+check)


def _call(g, calls, name):
    at = g.at
    target = g.relative('e8')
    calls.append(dict(role=name, instructionVa=at, targetVa=target))
    return target


def _peek(g, size):
    try:
        return bytes(g.bytes[g.at+i] for i in range(size))
    except KeyError as error:
        raise ValueError('actionOutputProgram.unowned-byte') from error


def factory_program(regions, entry):
    """Both selected typed Original allocation forms, with no invented ctor."""
    g = BytesPath(regions, entry); calls = []
    g.take('4053', '4883ec20'); flag = g.relative('803d')+1
    g.take('00', '488bd9')
    split = _peek(g, 1) == b'\x74'
    g.branch('74' if split else '75', not split, 1)
    site = g.at; cell = g.relative('488b0d')
    _call(g, calls, 'allocateOriginal'); g.take('4885c0')
    g.branch('74' if split else '75', not split, 1)
    g.take('488d4b10', '48894310', '4883c420', '5b')
    barrier = g.relative('e9')
    return dict(selectedBytes=g.seen, initializedFlagCellVa=flag,
        allocationInstructionVa=site, allocationCellVa=cell, calls=calls,
        barrierTargetVa=barrier, holderOffset=16, returnedOriginalStoredWhole8=True,
        originalConstructorCalled=False, originalFieldWrites=[],
        normalTypedZeroInitializedAllocationRequired=True,
        normalReturn=True, entryRspRestored=True, allNonvolatilesRestored=True,
        frameBytes=40, pushedNonvolatiles=['rbx'], initializedMetadataRequired=True)


def reader_program(regions, entry, *, existing, null):
    need('literal-four-path-choice', type(existing) is bool and type(null) is bool)
    g = BytesPath(regions, entry)
    if _peek(g, 5) == bytes.fromhex('48895c2410'):
        return reader77(regions, entry, existing=existing, null=null)
    calls = []
    g.take('48895c2418', '57', '4883ec20'); flag = g.relative('803d')+1
    g.take('00', '488bda', '488bf9')
    split = _peek(g, 2) == bytes.fromhex('0f84')
    g.branch('0f84' if split else '75', not split, 4 if split else 1)
    g.take('488d542430', 'c644243000', '488bcf')
    _call(g, calls, 'header'); g.take('84c0'); g.branch('0f84', null)
    allocation = None
    if null:
        g.take('488bcb', '48c70300000000'); _call(g, calls, 'barrier')
        g.take('90'); g.jump('e9')
    else:
        g.take('4889742438', '48833b00'); g.branch('0f84', not existing)
        if not existing:
            at = g.at; cell = g.relative('488b0d')
            allocator = _call(g, calls, 'allocateWrapper')
            allocation = dict(instructionVa=at, typeCellVa=cell, allocatorTargetVa=allocator)
            g.take('488bf0', '4885c0'); g.branch('0f84', False)
            g.take('33d2', '488bc8')
            allocation['constructorTargetVa'] = _call(g, calls, 'wrapperConstructor')
            g.take('488bcb', '488933'); _call(g, calls, 'barrier')
            g.take('90'); g.jump('e9')
        g.take('0fb6742430', '4080fe02'); g.branch('0f85', False)
        g.take('488b33', '488bcf'); _call(g, calls, 'target')
        g.take('4885f6'); g.branch('74', False, 1)
        g.take('4533c0', '8bd0', '488bce'); _call(g, calls, 'setTarget')
        g.take('488b1b', '488bcf'); _call(g, calls, 'path')
        g.take('4885db')
        branch = _peek(g, 1)
        need('exact-path-holder-guard', branch in (b'\x74', b'\x75'))
        g.branch('74' if branch == b'\x74' else '75', branch == b'\x75', 1)
        g.take('4533c0', '488bd0', '488bcb'); _call(g, calls, 'setPath')
        g.take('488b742438')
    g.take('488b5c2440', '4883c420', '5f', 'c3')
    return dict(selectedBytes=g.seen, profile='param-output-split52' if split else 'param-output51',
        existing=existing, null=null, initializedFlagCellVa=flag, calls=calls, wrapperAllocation=allocation,
        memberCount=None if null else 2, memberOrder=[] if null else ['paramTarget', 'path'],
        targetResult='eax', targetSetterArgument='edx', pathResult='rax', pathSetterArgument='rdx',
        originalTypeArgumentRead=False, originalTypeArgumentWireGrammarAdmitted=False,
        sameReader=True, outputSlotArgument='entry.rdx', headerLocalRspOffset=48,
        calleeHomeByteRange=[0, 32], frameBytes=40,
        savedEntryHomes=dict(rbx=[24, 32], **({} if null else dict(rsi=[16, 24]))),
        pushedNonvolatiles=['rdi'], nonvolatileRsiUntouched=null,
        nullOutputBytes=8 if null else 0, nullOutputIsZero=null,
        entryRspRestored=True, allNonvolatilesRestored=True, normalReturn=True,
        initializedMetadataRequired=True, compatibleCallsRequired=True,
        wrapperConstructorEffectsAdmitted=False, parentFieldAdmitted=False)


def reader77(regions, entry, *, existing, null):
    """Initialized-metadata MC2/FF paths with exact full frame restoration.

    Output's own T is not read here. The only member results are EAX target
    and RAX pooled path; the allocated wrapper is distinct from its Original
    holder and therefore its ctor must be proved independently.
    """
    need('literal-four-path-choice', type(existing) is bool and type(null) is bool)
    g = BytesPath(regions, entry); calls = []
    g.take('48895c2410', '4889742418', '57', '4883ec20')
    flag = g.relative('803d')+1
    g.take('00', '488bda', '488bf1'); g.branch('75', True, 1)
    g.take('488d542430', 'c644243000', '488bce')
    _call(g, calls, 'header'); g.take('84c0'); g.branch('0f84', null)
    allocation = None
    if null:
        g.take('488bcb', '48c70300000000'); _call(g, calls, 'barrier')
    else:
        g.take('48833b00'); g.branch('75', existing, 1)
        if not existing:
            at = g.at; cell = g.relative('488b0d')
            allocator = _call(g, calls, 'allocateWrapper')
            allocation = dict(instructionVa=at, typeCellVa=cell, allocatorTargetVa=allocator)
            g.take('488bf8', '4885c0'); g.branch('74', False, 1)
            g.take('33d2', '488bc8')
            allocation['constructorTargetVa'] = _call(g, calls, 'wrapperConstructor')
            g.take('488bcb', '48893b'); _call(g, calls, 'barrier')
        g.take('807c243002'); g.branch('75', False, 1)
        g.take('488b3b', '488bce'); _call(g, calls, 'target')
        g.take('4885ff'); g.branch('74', False, 1)
        g.take('4533c0', '8bd0', '488bcf'); _call(g, calls, 'setTarget')
        g.take('488b1b', '488bce'); _call(g, calls, 'path')
        g.take('4885db'); g.branch('74', False, 1)
        g.take('4533c0', '488bd0', '488bcb'); _call(g, calls, 'setPath')
        g.jump('eb', 1)
    g.take('488b5c2438', '488b742440', '4883c420', '5f', 'c3')
    return dict(selectedBytes=g.seen, profile='param-output-77', existing=existing, null=null,
        initializedFlagCellVa=flag, calls=calls, wrapperAllocation=allocation,
        memberCount=None if null else 2, memberOrder=[] if null else ['paramTarget', 'path'],
        targetResult='eax', targetSetterArgument='edx', pathResult='rax', pathSetterArgument='rdx',
        originalTypeArgumentRead=False, originalTypeArgumentWireGrammarAdmitted=False,
        sameReader=True, outputSlotArgument='entry.rdx', headerLocalRspOffset=48,
        calleeHomeByteRange=[0, 32], frameBytes=40,
        savedEntryHomes=dict(rbx=[16, 24], rsi=[24, 32]), pushedNonvolatiles=['rdi'],
        nullOutputBytes=8 if null else 0, nullOutputIsZero=null,
        entryRspRestored=True, allNonvolatilesRestored=True, normalReturn=True,
        initializedMetadataRequired=True, compatibleCallsRequired=True,
        wrapperConstructorEffectsAdmitted=False, parentFieldAdmitted=False)

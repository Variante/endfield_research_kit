"""Exact GlobalBuff Param/ObjectPtr wrapper schedules; no nominal aliases."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def _scope(null, allocated):
    if type(null) is not bool or type(allocated) is not bool or null and allocated:
        raise ValueError('globalBuffParam.selected-wrapper-path')


def _call(g, calls, role):
    at = g.at
    target = g.relative('e8')
    calls.append(dict(role=role, instructionVa=at, targetVa=target))
    return target


def param_program(regions, entry, *, null=False, allocated=False):
    _scope(null, allocated)
    g = BytesPath(regions, entry); calls = []
    g.take('48895c2410', '4889742418', '57', '4883ec30')
    flag = g.relative('803d') + 1
    g.take('00', '488bda', '488bf1'); g.branch('75', True, 1)
    g.take('488d542440', 'c644244000', '488bce'); _call(g, calls, 'header')
    g.take('84c0'); g.branch('0f84', null)
    allocation = None; usage = None
    if null:
        g.take('488bcb', '48c70300000000'); _call(g, calls, 'barrier')
    else:
        g.take('48833b00'); g.branch('75', not allocated, 1)
        if allocated:
            allocation = g.at; cell = g.relative('488b0d'); _call(g, calls, 'allocate')
            g.take('488bf8', '4885c0'); g.branch('0f84', False)
            g.take('33d2', '488bc8'); _call(g, calls, 'constructor')
            g.take('488bcb', '48893b'); _call(g, calls, 'barrier')
        g.take('807c244004'); g.branch('0f85', False)
        usage = g.at; g.relative('4c8b05')
        g.take('488d4c2420', '488b3b', '488bd6'); _call(g, calls, 'value16')
        g.take('4885ff'); g.branch('74', False, 1)
        g.take('0f28442420', '488d542420', '4533c0', '660f7f442420', '488bcf')
        _call(g, calls, 'constValue')
        for name in ('idRef', 'paramSource'):
            g.take('488b3b', '488bce'); _call(g, calls, 'integer')
            g.take('4885ff'); g.branch('74', False, 1)
            g.take('4533c0', '8bd0', '488bcf'); _call(g, calls, name)
        g.take('488b1b', '488bce'); _call(g, calls, 'pool')
        g.take('4885db'); g.branch('74', False, 1)
        g.take('4533c0', '488bd0', '488bcb'); _call(g, calls, 'path'); g.jump('eb', 1)
    g.take('488b5c2448', '488b742450', '4883c430', '5f', 'c3')
    return dict(selectedBytes=g.seen, null=null, allocated=allocated, calls=calls,
                initializedFlagCell=flag, allocationUsageSite=allocation, valueUsageSite=usage,
                memberCount=None if null else 4, constantStoredBytes=16, headerLocalRspOffset=64,
                hiddenLocalByteRange=[32, 48], calleeHomeByteRange=[0, 32], sameReaderRsi=True,
                sameHiddenLocalToNamedSetter=True, fullHiddenValueSelfCopy=True,
                normalReturn=True, entryRspRestored=True, nonvolatilesRestored=['rbx', 'rsi', 'rdi'])


def object_program(regions, entry, *, null=False, allocated=False):
    _scope(null, allocated)
    g = BytesPath(regions, entry); calls = []
    g.take('48895c2410', '4889742418', '57', '4883ec20')
    flag = g.relative('803d') + 1
    g.take('00', '488bda', '488bf9'); g.branch('75', True, 1)
    g.take('488d542430', 'c644243000', '488bcf'); _call(g, calls, 'header')
    g.take('84c0'); g.branch('0f84', null)
    allocation = None; usage = None
    if null:
        g.take('488bcb', '48c70300000000'); _call(g, calls, 'barrier')
    else:
        g.take('48833b00'); g.branch('75', not allocated, 1)
        if allocated:
            allocation = g.at; g.relative('488b0d'); _call(g, calls, 'allocate')
            g.take('4885c0'); g.branch('74', False, 1)
            g.take('0f57c0', '488bcb', '0f114010', '488903'); _call(g, calls, 'barrier')
        g.take('807c243002'); g.branch('75', False, 1)
        g.take('488b33', '488bcf'); _call(g, calls, 'integer')
        g.take('4885f6'); g.branch('74', False, 1)
        g.take('894618', '488bcf'); usage = g.at; g.relative('488b15')
        g.take('488b1b'); _call(g, calls, 'reference')
        g.take('4885db'); g.branch('74', False, 1)
        g.take('4533c0', '488bd0', '488bcb'); _call(g, calls, 'obj'); g.jump('eb', 1)
    g.take('488b5c2438', '488b742440', '4883c420', '5f', 'c3')
    return dict(selectedBytes=g.seen, null=null, allocated=allocated, calls=calls,
                initializedFlagCell=flag, allocationUsageSite=allocation, referenceUsageSite=usage,
                memberCount=None if null else 2, managedBytes=16,
                wireFieldOrder=['cachedUid', 'obj'], uidManagedOffset=8, referenceManagedOffset=0,
                newWrapperCompleteValueZeroed=allocated, fullReferenceToNamedSetter=True,
                normalReturn=True, entryRspRestored=True, nonvolatilesRestored=['rbx', 'rsi', 'rdi'])


def global_program(regions, entry, *, null=False, allocated=False):
    _scope(null, allocated)
    g = BytesPath(regions, entry); calls = []
    g.take('48895c2410', '57', '4883ec20')
    flag = g.relative('803d') + 1
    g.take('00', '488bda', '488bf9'); g.branch('75', True, 1)
    g.take('488d542430', 'c644243000', '488bcf'); _call(g, calls, 'header')
    g.take('84c0'); g.branch('74', null, 1)
    allocation = None
    if null:
        g.take('488bcb', '48c70300000000'); _call(g, calls, 'barrier')
    else:
        g.take('48833b00'); g.branch('75', not allocated, 1)
        if allocated:
            allocation = g.at; g.relative('488b0d'); _call(g, calls, 'allocate')
            g.take('488bf8', '4885c0'); g.branch('75', True, 1)
            g.take('33d2', '488bcf'); _call(g, calls, 'constructor')
            g.take('488bcb', '48893b'); _call(g, calls, 'barrier')
        g.take('408a7c2430', '4084ff'); g.branch('74', True, 1)
    g.take('488b5c2438', '4883c420', '5f', 'c3')
    return dict(selectedBytes=g.seen, null=null, allocated=allocated, calls=calls,
                initializedFlagCell=flag, allocationUsageSite=allocation,
                memberCount=None if null else 0, headerBytes=1, returnedReferenceBytes=8,
                noSerializedRuntimeBuffFields=True, normalReturn=True, entryRspRestored=True,
                nonvolatilesRestored=['rbx', 'rdi'])


def param_factory_program(regions, entry):
    g = BytesPath(regions, entry); calls = []
    g.take('4053', '4883ec20'); flag = g.relative('803d') + 1
    g.take('00', '488bd9'); g.branch('75', True, 1)
    usage = g.at; cell = g.relative('488b0d'); _call(g, calls, 'allocate')
    g.take('4885c0'); g.branch('75', True, 1)
    g.take('c74030ffffffff', '488d4b10', '48894310', '4883c420', '5b')
    barrier = g.relative('e9')
    return dict(selectedBytes=g.seen, initializedFlagCell=flag, allocationUsageSite=usage,
                allocationClassCell=cell, calls=calls, barrierTarget=barrier,
                holderOffset=16, idRefOffset=48, defaultIdRef=-1,
                normalReturn=True, entryRspRestored=True, nonvolatilesRestored=['rbx'])


def param_const_setter(regions, entry):
    g = BytesPath(regions, entry)
    g.take('4883ec28', '488b4910', '4885c9'); g.branch('75', True, 1)
    g.take('0f1002', '0f114120', '4883c120', '4883c428'); barrier = g.relative('e9')
    return dict(selectedBytes=g.seen, barrierTarget=barrier, storedBytes=16,
                holderOffset=16, originalFieldOffset=32, actualReferenceBarrierOffset=0,
                completeSourceToOwnedField=True, normalReturn=True, entryRspRestored=True)

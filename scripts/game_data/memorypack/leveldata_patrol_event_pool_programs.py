"""Actual EventParams generic/ObjectPool recycling without nominal aliases."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag


def need(check,condition):
    if not condition:raise ValueError('patrolEventPool.'+check)


def recycle_program(regions,entry,*,context_type,type_from_context,action,push,below_max=True,below_min=False):
    need('literal-recycle-count-paths',type(below_max)is bool and type(below_min)is bool and(not below_max or not below_min))
    g=BytesPath(regions,entry)
    g.take('4053','57','4156','4883ec20','4c8bf1','488bda','488b4a20');g.call(context_type)
    g.take('33d2','488b88c0000000');g.call(type_from_context)
    g.take('83b8e000000000');g.branch('75',True,1)
    g.take('488b4b20');g.call(context_type)
    g.take('33d2','488b88c0000000');g.call(type_from_context)
    g.take('488b88b8000000','488b39','4885ff');g.branch('0f84',False)
    g.take('488b4b20');g.call(context_type)
    g.take('488b88c0000000','488b4150','4883782000');g.branch('75',True,1)
    g.take('488b4b20');g.call(context_type)
    ready=flag(g);g.take('488b88c0000000','488b5950');g.branch('75',True,1)
    at=g.at;class_cell=g.relative('488b0d');g.take('83b9e000000000');g.branch('75',True,1)
    ready2=flag(g);g.branch('75',True,1)
    need('same-pool-temporary-class-2',g.relative('488b0d')==class_cell)
    g.take('83b9e000000000');g.branch('75',True,1)
    need('same-pool-temporary-class-3',g.relative('488b05')==class_cell)
    g.take('488b88b8000000','4c897110');collector=flag(g,'833d');g.branch('74',True,1)
    g.take('4889742450','488b4710','4885c0');g.branch('0f84',False)
    g.take('48837f2000','8b7018');g.branch('74',False,1)
    g.take('488b4320','48896c2448','488b6f20','488b90c0000000','488b82a0000000','4883782000');g.branch('75',True,1)
    g.take('488b4320','498bd6','488bcd','4c8b80c0000000','4d8b80a0000000');g.call(action)
    g.take('488b6c2448','3b7730');g.branch('0f8c',below_max)
    min_class=None
    if not below_max:
        g.take('488b4320','488b88c0000000','488b81a8000000','f6803801000001');g.branch('75',True,1)
        g.take('83b8e000000000');g.branch('75',True,1)
        g.take('488b4320','488b88c0000000','488b81a8000000','f6803801000001');g.branch('75',True,1)
        g.take('488b80b8000000','3b30');g.branch('7c',below_min,1)
        if not below_min:
            g.take('488b4320','488b88c0000000','488b4168','4883782000');g.branch('75',True,1)
            g.take('488b4320','8b7738','488b88c0000000','488b8198000000','4883782000');g.branch('75',True,1)
            g.take('8d46ff','488b742450','894738','4883c420','415e','5f','5b','c3')
    push_site=push_cell=None
    retained=below_max or below_min
    if retained:
        g.take('488b4f10','4885c9');g.branch('74',False,1)
        push_site=g.at;push_cell=g.relative('4c8b05')
        g.take('498bd6','488b742450','4883c420','415e','5f','5b')
        need('same-actual-pool-Stack-Push-tail',g.relative('e9')==push)
    return dict(selectedBytes=g.seen,closedPoolClassContextSlot=0,existingPoolStaticFieldOffset=0,
        requiredExistingPoolNonNull=True,readyMethodContextSlot=10,metadataReadyFlagVa=ready,
        temporaryClassSiteVa=at,temporaryClassCellVa=class_cell,temporaryReadyFlagVa=ready2,
        temporaryStaticFieldOffset=16,temporaryStaticReceivesSameEventReference=True,
        collectorDisabledFlagVa=collector,poolStackFieldOffset=16,poolOnRecycleDelegateFieldOffset=32,
        requiredOnRecycleDelegateNonNull=True,delegateMethodContextSlot=20,
        sameEventReferencePassedToDelegate=True,requiredCountBelowMax=below_max,
        requiredCountBelowGlobalMinimum=below_min,maximumFieldOffset=48,
        stackSizeFieldOffset=24,retainsEventInPool=retained,dropsEventFromPool=not retained,
        droppedEventCountAllOffset=56,droppedCountDecrement=0 if retained else 1,
        stackPushMethodInfoSiteVa=push_site,stackPushMethodInfoCellVa=push_cell,
        callbackAndSelectedStackPushEffectsRequired=True,entryRspRestoredBeforeTail=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r14'],runtimePoolStorageObserved=False)

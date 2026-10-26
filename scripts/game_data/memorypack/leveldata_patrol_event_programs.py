"""Byte programs for checkpoint event-manager control and callback transfer."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check,condition):
    if not condition:raise ValueError('patrolEvent.'+check)


def raise_event(regions,entry,s,*,released=False,key_found=True,listener=True):
    need('literal-raise-selections',all(type(v)is bool for v in(released,key_found,listener)))
    g=BytesPath(regions,entry)
    g.take('48895c2410','4889742418','57','4883ec40');root=g.relative('488b05')
    g.take('488bd9','498bf0','8bfa','488b4860','4885c9');g.branch('0f85',False)
    g.take('48896c2450','33ed','896c2430','4038ab80000000');g.branch('75',released,1)
    usage=None
    if not released:
        usage=g.at;cls=g.relative('488b0d');g.take('39a9e0000000');g.branch('74',False,1)
        g.take('4533c0','488d542430','8bcf');g.call(s['key'])
        g.take('84c0');g.branch('74',not key_found,1)
        if key_found:
            g.take('8b542430','4533c0','488bcb');g.call(s['listener'])
            g.take('84c0');g.branch('75',listener,1)
            if listener:
                g.take('8b542430','4c8bce','448bc7','48896c2420','488bcb');g.call(s['trigger']);g.jump('eb',1)
    g.take('488b6c2450','488b5c2458','488b742460','4883c440','5f','c3')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,managerReleasedOffset=128,
        released=released,keyFound=key_found,hasListener=listener,keyClassUsageInstructionVa=usage,
        keyArguments=dict(ecx='unchanged incoming EDX event enum',rdx='disjoint local CombineKey4 out',r8=0),
        listenerArguments=dict(rcx='same incoming manager',edx='same key out',r8=0),
        triggerRequested=not released and key_found and listener,
        triggerArguments=dict(rcx='same manager',edx='same key out',r8d='same incoming event enum',r9='same EventParams',stackArgument5=0),
        entryRspRestored=True,frameBytes=72,restoredNonvolatiles=['rbx','rsi','rdi','rbp'],
        condition='Selected absent replacement, stable compatible manager/EventParams/stack; canonical ready key class; exact normally returning key/listener/trigger helper programs. Callback registration, live manager fields, event delivery and execution are not observed.')


def key_cache(regions,entry,*,initialize):
    g=BytesPath(regions,entry)
    # This is the selected ready static-array return. Its own cold cache-builder
    # and replacement paths are intentionally not granted by this byte program.
    g.take('4883ec28');root=g.relative('488b05')
    g.take('488bd1','488b4868','4885c9');g.branch('0f85',False)
    site=g.at;cls=g.relative('488b0d');g.take('83b9e000000000');g.branch('74',False,1)
    g.take('33c9');g.call(initialize)
    need('same-cache-class',g.relative('488b05')==cls)
    g.take('488b80b8000000','488b4018')
    g.take('4883c428','c3')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,classCellVa=cls,
        classUsageInstructionVa=site,staticFieldsPointerOffset=184,cacheFieldOffset=24,returnedReference='same ready nonnull static CombineKey array',
        entryRspRestored=True,frameBytes=40,nonframeWrites=0)


def key_ready(regions,entry):
    g=BytesPath(regions,entry);g.take('4883ec28');root=g.relative('488b05')
    g.take('488bd1','488b4868','4885c9');g.branch('0f85',False)
    site=g.at;cls=g.relative('488b05');g.take('83b8e000000000');g.branch('0f84',False)
    g.take('488b88b8000000','80790100');g.branch('74',False,1)
    g.take('4883c428','c3')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,classCellVa=cls,classUsageInstructionVa=site,
        staticFieldsPointerOffset=184,readyFlagOffset=1,readyFlagMustBeNonzero=True,
        nonframeWrites=0,entryRspRestored=True,frameBytes=40,
        condition='Absent replacement, ready own class and nonzero actual initialized-cache byte in coherent stable static storage; cold cache construction is a separate branch.')


def try_key(regions,entry,*,cache):
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');root=g.relative('488b05')
    g.take('488bfa','8bd9','488b4868','4885c9');g.branch('0f85',False)
    g.take('81fb');limit=int.from_bytes(g.read(4),'little');g.branch('0f83',False)
    site=g.at;cls=g.relative('488b0d');g.take('83b9e000000000');g.branch('74',False,1)
    g.take('33c9');g.call(cache);g.take('4885c0');g.branch('74',False,1)
    g.take('3b5818');g.branch('73',False,1)
    g.take('8b549820','b001','8917','488b5c2430','4883c420','5f','c3')
    need('positive-native-key-limit',0<limit<1<<16)
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,classCellVa=cls,classUsageInstructionVa=site,
        enumMaximumExclusive=limit,keyArrayLengthOffset=24,keyArrayDataOffset=32,elementBytes=4,
        inputIndexRegister='ecx',outputPointerRegister='rdx',outputValue='exact ready cache[event enum] DWORD',
        returnBool=True,entryRspRestored=True,frameBytes=40,restoredNonvolatiles=['rbx','rdi'],
        condition='Absent replacement and ready own key class, exact cache getter; unsigned event index below native limit and ready array length; compatible nonnull disjoint out storage. Actual cache contents and static binding remain runtime conditions.')


def trigger_setup(regions,entry,*,found=True):
    need('literal-trigger-lookup-outcome',type(found)is bool)
    g=BytesPath(regions,entry);calls={};usages={}
    def use(role,prefix):
        at=g.at;cell=g.relative(prefix);usages[role]=dict(instructionVa=at,cellVa=cell);return cell
    def call(role):
        at=g.at;target=g.relative('e8');calls[role]=dict(instructionVa=at,targetVa=target);return target
    g.take('48895c2408','4889742410','48897c2418','4c89642420','4155','4156','4157','4881ecc0000000',
        '4d8be1','458be8','488bf9');root=g.relative('488b05')
    g.take('488b4860','4885c9');g.branch('74',True,1)
    g.take('33f6','4889742468','4889742458','0f57c0','0f11842488000000','0f57c9','0f118c2498000000',
        '488bbf88000000','4885ff');g.branch('0f84',False)
    use('dictionaryTryGetValue','4c8b0d');g.take('4c8d442468','488bcf');call('dictionaryTryGetValue')
    g.take('84c0');g.branch('74',not found,1)
    if found:
        use('listPoolClass','488b0d');g.take('39b1e0000000');g.branch('75',True,1)
        use('listPoolAllocate','488b0d');call('listPoolAllocate')
        g.take('4889442458','4889742478','488d5c2458','48899c2480000000','488b4c2458','4885c9');g.branch('0f84',False)
        use('listClear','488b15');call('listClear')
        g.take('488b7c2458','488b4c2468','4885c9');g.branch('0f84',False)
        use('dictionaryValues','488b15');call('dictionaryValues');g.take('4885ff');g.branch('0f84',False)
        use('listAddRange','4c8b05');g.take('488bd0','488bcf');call('listAddRange')
        g.take('448bfe','488b442458','4885c0');g.branch('0f84',False)
        g.take('8b4818','894c2460','660f1f440000')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,actualCalls=calls,typedUsageSites=usages,
        dictionaryFound=found,continuationInstructionVa=g.at,managerListenerDictionaryOffset=136,
        lookupArguments=dict(rcx='manager listener dictionary',rdx='same incoming key',r8='disjoint out inner dictionary',r9='own closed MethodInfo'),
        clearedSnapshotList='exact same ListPool allocation reference at stack88',
        snapshotValues='exact found inner dictionary Values to the same cleared list AddRange',
        eventParamsRetainedInR12=True,eventEnumRetainedInR13d=True,initialSnapshotIndex=0,
        snapshotCountFieldOffset=24,copyElementBytes=16,
        helperEffectsProved=False)


def listener_setup(regions,entry,*,found=True):
    need('literal-listener-lookup-outcome',type(found)is bool)
    g=BytesPath(regions,entry);calls={};usages={}
    def call(role):
        at=g.at;target=g.relative('e8');calls[role]=dict(instructionVa=at,targetVa=target);return target
    def use(role,prefix):
        at=g.at;cell=g.relative(prefix);usages[role]=dict(instructionVa=at,cellVa=cell);return cell
    g.take('48895c2408','4889742410','48897c2418','4156','4881ec90000000','8bda','488bf1');root=g.relative('488b05')
    g.take('488b4860','4885c9');g.branch('74',True,1)
    g.take('4533f6','4c89b424b8000000','0f57c0','0f11442468','0f11442478','0f11442428','0f57c9','0f114c2438',
        '488bb688000000','4885f6');g.branch('0f84',False)
    use('dictionaryMethod','488b3d');g.take('488b4720','488b88c0000000','488b81b0000000','4c397020');g.branch('75',True,1)
    g.take('488b4720','4c8b80c0000000','4d8b80b0000000','8bd3','488bce');call('dictionaryFindEntry')
    g.take('4863f8','85c0');g.branch('0f88',not found)
    if found:
        g.take('488b5e18','4885db');g.branch('0f84',False)
        g.take('3b7b18');g.branch('0f83',False)
        g.take('488d0c7f','488d04cb','488b4030','48898424b8000000','488d8c24b8000000');call('barrier')
        g.take('488b9c24b8000000','4885db');g.branch('0f84',False)
        use('dictionaryValues','488b15');g.take('488bcb');call('dictionaryValues')
        g.take('4885c0');g.branch('0f84',False)
        g.take('488b5810','0f57c0','f30f7f442450','4c89742460','48895c2448','488d4c2448')
        need('same-listener-disabled-barrier-call',call('barrierAgain')==calls['barrier']['targetVa'])
        g.take('4885db');g.branch('0f84',False)
        g.take('8b432c','89442454','4489742450','0f57c9','0f10442448','0f11442468','0f114c2478',
            '4c89742448','488d442468','4889442450','66660f1f840000000000')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,actualCalls=calls,typedUsageSites=usages,
        dictionaryFound=found,continuationInstructionVa=g.at,managerListenerDictionaryOffset=136,
        dictionaryEntryBytes=24,dictionaryValueOffset=16,innerEnumerationSlotBytes=32,
        innerObjectPtrOffset=16,enumVersionLocalOffset=116,enumIndexLocalOffset=112,
        helperEffectsProved=False)

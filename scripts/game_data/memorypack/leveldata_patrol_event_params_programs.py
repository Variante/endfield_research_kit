"""Finite selected EventParams and ScopeStack source programs.

Only byte programs live here. Nominal fields, caller MethodSpecs and actual
callee effects are joined by the separate source owner.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag


def need(check,condition):
    if not condition:raise ValueError('patrolEventParams.'+check)


def allocate_program(regions,entry,*,pool_allocate,barrier,scope_getter,push):
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec30');root=g.relative('488b05')
    g.take('488bda','488bf9','488b5068','4885d2');g.branch('0f85',False)
    class_site=g.at;pool_class=g.relative('488b0d');g.take('83b9e000000000');g.branch('74',False,1)
    pool_site=g.at;pool_context=g.relative('488b0d');g.call(pool_allocate)
    g.take('488bcb','488903');g.call(barrier);g.take('33c9');g.call(scope_getter)
    g.take('4885c0');g.branch('74',False,1)
    push_site=g.at;push_context=g.relative('4c8b0d')
    g.take('488d4c2420','4c8b03','488bd0');g.call(push)
    g.take('0f10442420','488b5c2440','488bc7','0f1107','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,replacementReceiverOffset=104,
        poolClassCellVa=pool_class,poolClassSiteVa=class_site,poolMethodInfoCellVa=pool_context,poolMethodInfoSiteVa=pool_site,
        pushMethodInfoCellVa=push_context,pushMethodInfoSiteVa=push_site,
        samePoolReferenceWrittenToOutReference=True,sameOutReferencePassedToPush=True,
        scopeLocalOffset=32,scopeManagedBytes=16,wholeScopeCopiedToHiddenResult=True,
        resultReferenceRegister='incoming RDX',hiddenScopeResultRegister='incoming RCX',
        returnsSameHiddenResult=True,entryRspRestored=True,restoredNonvolatiles=['rbx','rdi'],
        poolAllocationAndPushEffectsRequired=True,runtimeInvocationObserved=False)


def scope_getter_program(regions,entry):
    g=BytesPath(regions,entry);g.take('4883ec28');root=g.relative('488b05')
    g.take('488bd1','488b4868','4885c9');g.branch('0f85',False)
    class_site=g.at;own_class=g.relative('488b05')
    g.take('48895c2430','4889742438','48897c2420','488b88b8000000','48833900');g.branch('74',False,1)
    g.take('488b80b8000000','488b742438','488b5c2430','488b7c2420','488b00','4883c428','c3')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,replacementReceiverOffset=104,
        ownClassCellVa=own_class,ownClassSiteVa=class_site,staticFieldsOffset=184,staticFieldOffset=0,
        existingScopeStackRequiredNonnull=True,sameStaticReferenceReturned=True,memoryWrites=0,
        entryRspRestored=True,restoredNonvolatiles=['rbx','rsi','rdi'],coldScopeStackConstructionProved=False)


def generic_allocate_program(regions,entry,*,context_type,type_from_context,allocate):
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','488bd9','488b4920');g.call(context_type)
    g.take('33d2','488b88c0000000');g.call(type_from_context)
    g.take('83b8e000000000');g.branch('74',False,1)
    g.take('488b4b20');g.call(context_type);g.take('33d2','488b88c0000000');g.call(type_from_context)
    g.take('488b88b8000000','488b39','4885ff');g.branch('74',False,1)
    g.take('488b4b20');g.call(context_type)
    g.take('488b88c0000000','488b4138','4883782000');g.branch('0f84',False)
    g.take('488b4b20');g.call(context_type)
    g.take('488bcf','488b90c0000000','488b5238','488b5c2430','4883c420','5f')
    need('actual-ObjectPool-Allocate-tail',g.relative('e9')==allocate)
    return dict(selectedBytes=g.seen,staticPoolClassContextSlot=0,staticPoolFieldOffset=0,
        objectPoolAllocateContextSlot=7,sameExistingPoolReceiverPassed=True,
        returnedReferenceUnchanged=True,entryRspRestored=True,restoredNonvolatiles=['rbx','rdi'],
        runtimePoolOrMethodInfoObserved=False)


def object_pool_allocate_program(regions,entry,*,reuse,factory_invoke,create_instance,
                                 factory=False,on_allocate=True,new_count_larger=True):
    need('literal-ObjectPool-selections',all(type(x)is bool for x in(reuse,factory,on_allocate,new_count_larger)))
    g=BytesPath(regions,entry);g.take('48895c2418','4889742420','57','4883ec20')
    ready=flag(g);g.take('488bda','488bf9');g.branch('75',True,1)
    g.take('488b7710','4885f6');g.branch('0f84',False)
    g.take('837e1800','48896c2438');g.branch('0f84',not reuse)
    collector=None;stack_context=None
    if reuse:
        g.take('4885f6');g.branch('0f84',False)
        g.take('48635618','488b4e10');stack_context=g.relative('488b2d')
        g.take('448d42ff','4885c9');g.branch('0f84',False)
        g.take('443b4118');g.branch('0f83',False)
        g.take('ff461c','44894618','488d72ff','3b7118');g.branch('0f83',False)
        collector=flag(g,'833d')
        g.take('488d42ff','488b74f120','48c744c12000000000');g.branch('0f84',True)
    else:
        g.take('488b7728','4885f6');g.branch('74',not factory,1)
        if factory:
            g.take('488b4320','488b90c0000000','488b8280000000','4883782000');g.branch('75',True,1)
            g.take('488b4320','488bce','488b90c0000000','488b9280000000');g.call(factory_invoke)
            g.take('488bf0','4885c0');g.branch('75',True,1)
        else:
            g.take('488b4320','488b88c0000000','488b8990000000');g.call(create_instance);g.take('488bf0')
        g.take('488b4320','488b88c0000000','488b4168','4883782000');g.branch('75',True,1)
        g.take('488b4320','8b6f38','488b88c0000000','488b8198000000','4883782000');g.branch('75',True,1)
        g.take('8d4501','8b6f34','894738','488b4320','488b88c0000000','488b4168','4883782000');g.branch('75',True,1)
        g.take('3b6f38');g.branch('7e',new_count_larger,1)
        if new_count_larger:
            g.take('488b4320','488b88c0000000','488b4168','4883782000');g.branch('75',True,1)
            g.take('8b4738')
        else:g.take('8b4734');g.jump('eb',1)
        g.take('894734')
    g.take('48837f1800');g.branch('74',not on_allocate,1)
    if on_allocate:
        g.take('488b4320','488b7f18','488b90c0000000','488b82a0000000','4883782000');g.branch('75',True,1)
        g.take('4c8b4f18','488bd6','4c8b4728','488b4f40','41ffd1')
    g.take('488b6c2438','488bc6','488b742448','488b5c2440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,reuse=reuse,factoryDelegateUsed=not reuse and factory,
        fallbackActivatorUsed=not reuse and not factory,onAllocateDelegateUsed=on_allocate,
        metadataReadyFlagVa=ready,stackFieldOffset=16,createDelegateFieldOffset=40,onAllocateDelegateFieldOffset=24,
        stackArrayFieldOffset=16,stackSizeFieldOffset=24,stackVersionFieldOffset=28,
        stackElementBytes=8,stackTopSameReferenceReturned=reuse,poppedCellCleared=reuse,
        stackPopMethodInfoCellVa=stack_context,collectorDisabledFlagVa=collector,
        countAllFieldOffset=56,peakCountFieldOffset=52,countAllIncrement=0 if reuse else 1,
        peakCountUpdatedToMaximum=not reuse,creationEffectsRequired=not reuse,resetCallbackEffectsRequired=on_allocate,
        sameSelectedValuePassedToResetAndReturned=True,actualAllocationCapacityOrCallbackObserved=False,
        entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi'])


def dispose_program(regions,entry,*,context_type,pop,barrier,empty=False):
    need('literal-scope-state',type(empty)is bool)
    g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20','4883790800','488bfa','488bd9');g.branch('74',empty,1)
    if not empty:
        g.take('4889742430','488b7108','488b4a20');g.call(context_type)
        g.take('488b88c0000000','488b4108','4883782000');g.branch('0f84',False)
        g.take('488b4f20');g.call(context_type)
        g.take('488bce','488b90c0000000','488b5208');g.call(pop)
        g.take('488d4b08','48c7430800000000');g.call(barrier);g.take('488b742430')
    g.take('488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,alreadyDisposed=empty,stackReferenceFieldOffset=8,
        scopeValueFieldOffset=0,scopeValueUntouched=True,scopeStackPopContextSlot=1,
        sameStackReferencePassed=not empty,stackReferenceSetNull=not empty,
        popEffectsRequired=not empty,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rdi']if empty else['rbx','rsi','rdi'],
        canonicalPhysicalPointerEquivalenceProved=False,runtimeInvocationObserved=False)


def push_program(regions,entry):
    """Actual whole Scope16 append into a selected list with spare capacity."""
    g=BytesPath(regions,entry)
    g.take('488bc4','48895810','48896818','48897020','57','4883ec50')
    collector=flag(g,'833d');table=g.relative('488d2d')
    g.take('0f57c0','0f2970e8','0f1101','498bf9','48c740d000000000','488bda','4c8940c8','488bf1');g.branch('74',True,1)
    need('same-push-collector',flag(g,'833d')==collector)
    g.take('48895c2428');g.branch('74',True,1)
    g.take('488b5b10','0f28742420','0f1136','4885db');g.branch('0f84',False)
    g.take('498b4120','488b88c0000000','488b4120','4883782000');g.branch('75',True,1)
    g.take('488b4720','488b5310','488b88c0000000','488b7920','ff431c','4885d2');g.branch('0f84',False)
    g.take('48634b18','3b4a18');g.branch('72',True,1)
    g.take('8d4101','894318','3b4a18');g.branch('0f83',False)
    g.take('488d4102','4803c0');need('same-push-store-collector',flag(g,'833d')==collector)
    g.take('0f1134c2');g.branch('74',True,1)
    g.take('488b5c2468','488bc6','488b742478','488b6c2470','0f28742440','4883c450','5f','c3')
    return dict(selectedBytes=g.seen,scopeValueSourceLocalOffset=32,scopeStackSourceLocalOffset=40,
        scopeValueAndStackPairBytes=16,outputScopeEqualsStoredScope=True,
        scopeStackListFieldOffset=16,listArrayFieldOffset=16,listCountFieldOffset=24,listVersionFieldOffset=28,
        arrayLengthOffset=24,arrayDataOffset=32,elementStride=16,countIncrement=1,versionIncrementModulo2Pow32=1,
        incomingValueAndStackReferencesUnchanged=True,nonnullListArrayAndSpareCapacityRequired=True,
        collectorDisabledFlagVa=collector,unusedCollectorTableVa=table,
        entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','xmm6'],xmmSaveRestoreBytes=16,
        coldListGrowthProved=False,runtimeInvocationObserved=False)


def pop_program(regions,entry,*,action_invoke,barrier,callback=True):
    need('literal-before-pop-callback',type(callback)is bool)
    g=BytesPath(regions,entry)
    g.take('48895c2408','48896c2410','4889742418','48897c2420','4156','4883ec40',
        '4c8b7118','488bfa','488bf1','4d85f6');g.branch('0f84',not callback)
    if callback:
        g.take('488b5910','4885db');g.branch('0f84',False)
        g.take('488b4220','488b90c0000000','488b4208','4883782000');g.branch('0f84',False)
        g.take('488b4720','48636b18','488b88c0000000','488b4110','4883782000');g.branch('0f84',False)
        g.take('8d45ff','3b4318');g.branch('0f83',False)
        g.take('488b4b10','4885c9');g.branch('0f84',False)
        g.take('8d45ff','3b4118');g.branch('0f83',False)
        g.take('488d4501','4803c0','0f1004c1','488b4720','0f11442430',
            '488b88c0000000','488b4130','4883782000');g.branch('0f84',False)
        g.take('488b4720','66480f7ec2','498bce','4c8b80c0000000','4d8b4030');g.call(action_invoke)
    g.take('488b5e10','4885db');g.branch('0f84',False)
    g.take('488b4720','488b88c0000000','488b4108','4883782000');g.branch('0f84',False)
    g.take('488b4720','8b7318','488b88c0000000','488b4138','4883782000');g.branch('0f84',False)
    g.take('448d4eff','443b4b18');g.branch('73',False,1)
    g.take('8b4318','ffc8','894318','443bc8');g.branch('0f8c',False)
    g.take('488b5310','0f57c0','48634b18','4885d2');g.branch('74',False,1)
    g.take('3b4a18');g.branch('73',False,1)
    g.take('488d4102','4883c102','4803c0','48c1e104','4803ca','0f1104c2');g.call(barrier)
    g.take('ff431c','488b5c2450','488b6c2458','488b742460','488b7c2468','4883c440','415e','c3')
    return dict(selectedBytes=g.seen,beforePopCallbackSelected=callback,callbackGetsLastScopeValue=callback,
        callbackEffectsRequired=callback,scopeStackListFieldOffset=16,beforePopFieldOffset=24,
        listArrayFieldOffset=16,listCountFieldOffset=24,listVersionFieldOffset=28,
        selectedLastIndexRequired=True,positiveListCountRequired=True,elementStride=16,
        listCountDecrement=1,wholeRemovedScopeSetZero=True,versionIncrementModulo2Pow32=1,
        otherElementsUntouched=True,elementShiftOrArrayCopyCalled=False,
        entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','r14'],runtimeInvocationObserved=False)


def before_pop_program(regions,entry,*,invoke,empty=False):
    need('literal-callback-value-state',type(empty)is bool)
    g=BytesPath(regions,entry);g.take('4885d2');g.branch('74',empty,1)
    root=None
    if not empty:
        g.take('53','4883ec20');root=g.relative('488b05')
        g.take('488bda','488b4810','4885c9');g.branch('0f85',False)
        g.take('b90a000000');g.call(invoke)
        g.take('b909000000','488bd3');g.call(invoke)
        g.take('4883c420','5b')
    g.take('c3')
    return dict(selectedBytes=g.seen,nullValue=empty,replacementRootCellVa=root,
        replacementReceiverOffset=16,orderedVirtualSelectors=[]if empty else[10,9],
        sameEventParamsPassedToClearAndRecycle=not empty,callbackEffectsRequired=not empty,
        entryRspRestored=True,restoredNonvolatiles=[]if empty else['rbx'],runtimeCallbackObserved=False)


def recycle_program(regions,entry,*,recycle):
    g=BytesPath(regions,entry);g.take('4053','4883ec20');root=g.relative('488b05')
    g.take('488bd9','488b4868','4885c9');g.branch('0f85',False)
    site=g.at;own_class=g.relative('488b0d');g.take('83b9e000000000');g.branch('74',False,1)
    use=g.at;context=g.relative('488b15')
    g.take('488bcb','4883c420','5b');need('own-recycle-pool-tail',g.relative('e9')==recycle)
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,replacementReceiverOffset=104,
        poolClassCellVa=own_class,poolClassSiteVa=site,recycleMethodInfoCellVa=context,recycleMethodInfoSiteVa=use,
        sameEventParamsReferencePassed=True,entryRspRestored=True,restoredNonvolatiles=['rbx'],
        poolRecycleEffectsRequired=True,runtimeCallbackObserved=False)


def virtual_event_program(regions,entry,*,prepare,callback,slot):
    need('exact-EventParams-selector',type(slot)is int and slot in(7,9,10))
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec40','0fb7d9','488bfa','488b0a','0f29742430');g.call(prepare)
    g.take('488b07','488d4b14','4803c9','4c8b04c8','488b54c808');excluded=[]
    for opcode,width in(('74',1),('74',1),('0f84',4)):
        excluded.append(g.relative('488d05'));g.take('4c3bc0');g.branch(opcode,False,width)
    need('own-EventParams-callback-outside-inline-alternatives',type(callback)is int and callback>0 and callback not in excluded)
    g.take('488bcf','41ffd0');g.jump('eb',1)
    g.take('488b5c2450','488b742458','0f28742430','4883c440','5f','c3')
    return dict(selectedBytes=g.seen,slot=slot,callbackByteOffset=320+slot*16,methodInfoByteOffset=328+slot*16,
        selectedCallbackRequired=callback,excludedInlineCallbacks=excluded,
        sameIncomingReceiverAndSelectedMethodInfoPassed=True,
        entryRspRestored=True,restoredNonvolatiles=['rbx','rsi','rdi','xmm6'],xmmSaveRestoreBytes=16,
        runtimeCallbackObserved=False)


def disabled_barrier_program(regions,entry):
    g=BytesPath(regions,entry);collector=flag(g,'833d');g.take('4c8bc1');g.branch('74',True,1);g.take('c3')
    return dict(selectedBytes=g.seen,collectorDisabledFlagVa=collector,memoryWrites=0,calls=0,
        entryRspAndNonvolatilesUntouched=True,physicalFunctionExtentProved=False)


def action_program(regions,entry,*,callback):
    g=BytesPath(regions,entry)
    g.take('4053','57','4883ec38','488b4118','488bda','488b7928');excluded=[g.relative('488d15')]
    g.take('488b4940','483bc2');g.branch('75',True,1)
    excluded.append(g.relative('488d15'));g.take('483bc2');g.branch('0f85',True)
    excluded.append(g.relative('488d15'));g.take('483bc2');g.branch('75',True,1)
    need('actual-EventParams-delegate-callback',type(callback)is int and callback>0 and callback not in excluded)
    g.take('4c8bc7','488bd3','4883c438','5f','5b','48ffe0')
    return dict(selectedBytes=g.seen,selectedCallbackRequired=callback,excludedInlineCallbacks=excluded,
        callbackArgumentRegisters=dict(rcx='same delegate target at64',rdx='same incoming EventParams reference',
            r8='same delegate MethodInfo at40'),tailResultUnchanged=True,
        entryRspRestored=True,restoredNonvolatiles=['rbx','rdi'],runtimeCallbackObserved=False)

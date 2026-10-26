"""Selected EventParams/ordinary ParamVariable reset and recycle effects."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag


def need(check,condition):
    if not condition:raise ValueError('patrolEventCleanup.'+check)


def blackboard_allocate_program(regions,entry,*,barrier):
    g=BytesPath(regions,entry);g.take('4053','4883ec20');root=g.relative('488b05')
    g.take('488bd9','488b4810','4885c9');g.branch('0f85',False)
    g.take('488b4878','4885c9');g.branch('0f85',False)
    serial=g.relative('488b05');g.take('83b8e000000000');g.branch('74',False,1)
    ready=flag(g);g.branch('74',False,1)
    g.take('83b8e000000000');g.branch('74',False,1)
    g.take('488b88b8000000','8b11','ffc2','8911','895310','4533c9','4c894b18')
    site=g.at;empty=g.relative('488b05')
    g.take('488b88b8000000','488b01','488d4b20','48894320');g.call(barrier)
    g.take('44894b38','4883c420','5b','c3')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,requiredAbsentReplacementReceiverOffsets=[16,120],
        serialClassCellVa=serial,serialClassInitializedOffset=224,metadataReadyFlagVa=ready,
        serialStaticFieldsOffset=184,serialCounterStaticOffset=0,serialIncrementModulo2Pow32=1,serialFieldOffset=16,
        debugSegmentIdFieldOffset=24,debugSegmentIdSetZero=True,debugContextKeyFieldOffset=32,
        debugContextKeyClassSiteVa=site,debugContextKeyClassCellVa=empty,debugContextKeyStaticFieldOffset=0,
        debugContextCategoryFieldOffset=56,debugContextCategorySetZero=True,
        variableDictionaryFieldUntouched=True,subBlackboardDictionaryFieldUntouched=True,
        entryRspRestored=True,restoredNonvolatiles=['rbx'],runtimeInvocationObserved=False)


def reusable_recycle_program(regions,entry):
    g=BytesPath(regions,entry);g.take('4883ec28');root=g.relative('488b05')
    g.take('4c8b4878','4d85c9');g.branch('0f85',False)
    g.take('c7411000000000','4883c428','c3')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,replacementReceiverOffset=120,
        serialFieldOffset=16,serialSetZero=True,otherNonframeWrites=0,entryRspRestored=True,
        nonvolatilesUntouched=True,runtimeInvocationObserved=False)


def variable_recycle_reset_program(regions,entry):
    g=BytesPath(regions,entry);g.take('4053','4883ec20');root=g.relative('488b05')
    g.take('488bd9','488b4810','4885c9');g.branch('74',True,1)
    need('same-variable-recycle-root',g.relative('488b05')==root)
    g.take('48897c2430','33ff','488b4810','4885c9');g.branch('74',True,1)
    collector=g.relative('8b05');table=g.relative('4c8d0d')
    g.take('48897b18','85c0');g.branch('74',True,1)
    g.take('48897b20','897b30','48897b28','85c0');g.branch('74',True,1)
    g.take('4889bb88000000','85c0');g.branch('74',True,1)
    need('same-variable-recycle-tail-root',g.relative('488b05')==root)
    g.take('488b4878','4885c9');g.branch('74',True,1)
    g.take('897b10','488b7c2430','4883c420','5b','c3')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,requiredAbsentReplacementReceiverOffsets=[16,120],
        collectorDisabledFlagVa=collector,unusedCollectorTableVa=table,
        zeroedReferenceOffsets=[24,40,136],zeroedScalarSpans=[[16,20],[32,40],[48,52]],
        constantValueFieldUntouched=True,nextOnAllocateValueResetRequired=True,
        entryRspRestored=True,restoredNonvolatiles=['rbx','rdi'],calls=0,runtimeInvocationObserved=False)


def variable_reset_invoker_program(regions,entry,*,prepare,callback):
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec40','0fb7d9','488bfa','488b0a','0f29742430');g.call(prepare)
    g.take('488b07','488d4b14','4803c9','4c8b04c8','488b54c808');excluded=[]
    for opcode,width in(('74',1),('74',1),('0f84',4)):
        excluded.append(g.relative('488d05'));g.take('4c3bc0');g.branch(opcode,False,width)
    need('own-variable-OnRecycle-callback',type(callback)is int and callback>0 and callback not in excluded)
    g.take('488bcf','41ffd0');g.jump('eb',1)
    g.take('488b5c2450','488b742458','0f28742430','4883c440','5f','c3')
    return dict(selectedBytes=g.seen,selector=8,selectedCallbackRequired=callback,excludedInlineCallbacks=excluded,
        callbackByteOffset=448,methodInfoByteOffset=456,sameReceiverAndSelectedMethodInfoPassed=True,
        entryRspRestored=True,restoredNonvolatiles=['rbx','rsi','rdi','xmm6'],xmmSaveRestoreBytes=16,
        runtimeCallbackObserved=False)


def variable_pool_recycle_program(regions,entry,*,type_from_context,assignable,invoke,singleton,push):
    g=BytesPath(regions,entry)
    g.take('48895c2410','57','4883ec20','498b4820','488bfa','ba0c000000','498bd8','488b89c0000000');g.call(type_from_context)
    g.take('4885ff');g.branch('0f84',False)
    g.take('488b0f','488bd0');g.call(assignable);g.take('84c0');g.branch('0f84',False)
    g.take('b908000000','4889742430','488bd7');g.call(invoke)
    g.take('488b4320','488b88c0000000','488b4948');g.call(singleton)
    g.take('4885c0');g.branch('74',False,1)
    g.take('488b7010','4885f6');g.branch('74',False,1)
    g.take('488b4320','488b90c0000000','488b4270','4883782000');g.branch('0f84',False)
    g.take('488b4320','488bd7','488bce','4c8b80c0000000','4d8b4070');g.call(push)
    g.take('488b742430','488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,typedVariableClassContextSlot=12,ownVariableClassMatchRequired=True,
        resetSelector=8,singletonContextSlot=9,poolStackFieldOffset=16,pushReadyContextSlot=14,
        sameVariablePassedToResetAndStackPush=True,selectedStackPushDoesNotReadMethodInfoRequired=True,
        resetAndStackPushEffectsRequired=True,entryRspRestored=True,restoredNonvolatiles=['rbx','rsi','rdi'],
        runtimePoolOrCallbackObserved=False)


def stack_push_program(regions,entry):
    g=BytesPath(regions,entry)
    g.take('48895c2410','48896c2418','56','57','4156','4883ec20','488b7110','498be8','48637918',
        '4c8bf2','488bd9','4885f6');g.branch('0f84',False)
    g.take('3b7e18');g.branch('72',True,1)
    collector=flag(g,'833d');g.take('4c8974fe20');g.branch('74',True,1)
    g.take('ff431c','8d4701','894318','488b5c2448','488b6c2450','4883c420','415e','5f','5e','c3')
    return dict(selectedBytes=g.seen,arrayFieldOffset=16,sizeFieldOffset=24,versionFieldOffset=28,
        arrayLengthOffset=24,arrayDataOffset=32,referenceElementBytes=8,
        writesSameInputReferenceAtPriorSize=True,sizeIncrement=1,versionIncrementModulo2Pow32=1,
        nonnullArrayAndSpareCapacityRequired=True,collectorDisabledFlagVa=collector,
        incomingMethodInfoNotReadOnSelectedPath=True,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r14'],resizeEffectsProved=False)


def ordinary_not_assignable_program(regions,entry,*,prepare,shallower=False):
    """The actual ready-class hierarchy test, for a nonmatching ordinary value."""
    g=BytesPath(regions,entry)
    g.take('48895c2410','57','4883ec20','488bfa','488bd9','0fb6813a010000','90','a804');g.branch('75',True,1)
    g.take('488bcf');g.call(prepare)
    g.take('0fb68732010000','388332010000');g.branch('72',shallower,1)
    if not shallower:
        g.take('0fb6c8','488b83c8000000','48397cc8f8');g.branch('75',True,1)
    g.take('32c0','488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,receiverReadyFlagOffset=314,receiverReadyFlagMask=4,
        expectedPrepareTarget=prepare,classDepthOffset=306,hierarchyPointerOffset=200,
        hierarchyCellBytes=8,requiredReceiverDepthBelowExpected=shallower,
        requiredHierarchyEntryDiffersFromExpected=not shallower,returnsLiteralFalse=True,
        entryRspRestored=True,restoredNonvolatiles=['rbx','rdi'],memoryWrites=0,
        actualRuntimeClassObserved=False)


def dictionary_move_next_program(regions,entry,*,context_type,skipped=0,found=True):
    need('finite-enumerator-witness',type(skipped)is int and 0<=skipped<=3 and type(found)is bool)
    g=BytesPath(regions,entry)
    g.take('48895c2418','56','57','4156','4883ec30','488b19','488bf9','8b7108','4885db');g.branch('0f84',False)
    g.take('3b732c');g.branch('0f85',False)
    g.take('48896c2458','0f1f00');loop=g.at
    for i in range(skipped+1):
        need('same-enumerator-loop',g.at==loop)
        g.take('488b07','4885c0');g.branch('0f84',False)
        g.take('488bc8','8b4020','39470c');g.branch('0f83',not found and i==skipped)
        if not found and i==skipped:break
        g.take('4863770c','488b5918','8d4601','89470c','4885db');g.branch('0f84',False)
        g.take('3b7318');g.branch('0f83',False)
        g.take('488d0c76','837ccb2000','488d2ccb');g.branch('7c',i<skipped,1)
    if found:
        g.take('488b4a20','0f57c0','488b5d28','488b7530','0f11442420');g.call(context_type)
        collector=g.relative('8b05');table=g.relative('4c8d0d')
        g.take('48895c2420','85c0');g.branch('74',True,1)
        g.take('4889742428','85c0');g.branch('74',True,1)
        g.take('0f10442420','0f114710','85c0');g.branch('74',True,1)
        g.take('b001','488b6c2458')
    else:
        collector=table=None
        g.take('8b4120','0f57c0','ffc0','89470c','32c0','0f114710');g.jump('eb',1)
        g.take('488b6c2458')
    g.take('488b5c2460','4883c430','415e','5f','5e','c3')
    return dict(selectedBytes=g.seen,enumeratorDictionaryOffset=0,enumeratorVersionOffset=8,
        enumeratorIndexOffset=12,enumeratorCurrentOffset=16,currentPairBytes=16,
        dictionaryVersionOffset=44,dictionaryCountOffset=32,dictionaryEntriesOffset=24,
        arrayDataOffset=32,arrayLengthOffset=24,entryStride=24,entryHashOffset=0,
        entryKeyOffset=8,entryValueOffset=16,indexIncrementPerExaminedEntry=1,
        negativeHashEntriesSkipped=skipped,returnsFound=found,
        occupiedPairCopiedUnchanged=found,eofIndexEqualsCountPlusOne=not found,
        eofCurrentPairZeroed=not found,versionMatchAndValidStorageRequired=True,
        collectorDisabledFlagVa=collector,unusedCollectorTableVa=table,
        contextTypeReturnUnused=True,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r14'])


def dictionary_enumerator_paths(regions,entry,*,context_type,count_limit=4096):
    need('finite-enumerator-domain',type(count_limit)is int and 0<count_limit<=4096)
    witnesses=[dictionary_move_next_program(regions,entry,context_type=context_type,skipped=n,found=found)
        for n in range(4)for found in(False,True)]
    return dict(witnesses=witnesses,countLimit=count_limit,
        induction=dict(indexStartsNonnegativeRequired=True,indexIncrementsExactlyOne=True,
            dictionaryCountAndVersionImmutableRequired=True,allNonnegativeHashEntriesReturnedOnce=True,
            negativeHashEntriesSkipWithoutYield=True,remainingMeasure='dictionary count minus index',
            exhaustionReturnsFalseAndClearsCurrent=True),runtimeStorageObserved=False)


def dictionary_clear_program(regions,entry,*,fill,positive):
    need('boolean-clear-path',type(positive)is bool)
    g=BytesPath(regions,entry)
    g.take('48895c2410','48896c2418','56','57','4154','4156','4157','4883ec30','8b7920','488bd9','85ff')
    g.branch('7f',positive,1)
    if positive:
        g.take('488b7110','4885f6');g.branch('0f84',False)
        g.take('448b6618','4585e4');g.branch('0f88',False)
        g.take('48833e00');g.branch('0f84',False)
        g.take('488b06','80b83401000000');g.branch('0f86',False)
        g.take('4533f6','4c397610');g.branch('0f85',False)
        g.take('418bee','f7dd','4c3936');g.branch('0f84',False)
        g.take('488b06','4438b034010000');g.branch('0f86',False)
        g.take('4c896c2460','4c397610');g.branch('0f85',False)
        g.take('4c8d7e18','4d8b3f','41bd01000000','4438a834010000');g.branch('0f87',False)
        g.take('4c8b6c2460','452bfc','413bef');g.branch('0f8f',False)
        g.take('488b06','33d2','4883c620','48638800010000','8bc1','410fafc4','4c63c0','4863c5','480fafc8','4803ce');g.call(fill)
        g.take('488b7318','44897320','c74324ffffffff','44897328','4885f6');g.branch('0f84',False)
        g.take('4c3936');g.branch('0f84',False)
        g.take('488b06','4438b034010000');g.branch('0f86',False)
        g.take('4c397610');g.branch('0f85',False)
        g.take('418bee','f7dd','4c3936');g.branch('0f84',False)
        g.take('488b06','4438b034010000');g.branch('0f86',False)
        g.take('4c397610');g.branch('75',False,1)
        g.take('4c8d7618','80b83401000001','4d8b36');g.branch('0f87',False)
        g.take('442bf7','413bee');g.branch('0f8f',False)
        g.take('488b06','33d2','48638800010000','8bc1','0fafc7','4c63c0','4863c5','480fafc8','4883c120','4803ce');g.call(fill)
        g.jump('e9')
    g.take('ff432c','488b5c2468','488b6c2470','4883c430','415f','415e','415c','5f','5e','c3')
    return dict(selectedBytes=g.seen,positivePriorCount=positive,countOffset=32,freeListOffset=36,
        freeCountOffset=40,versionOffset=44,versionIncrementModulo2Pow32=1,
        positiveCountSetsCountAndFreeCountZero=positive,positiveCountSetsFreeListMinusOne=positive,
        bucketsFieldOffset=16,entriesFieldOffset=24,arrayDataOffset=32,
        requiredRank=1,requiredBoundsPointerNull=True,requiredBucketsComponentBytes=4,
        requiredEntryComponentBytes=24,requiredBucketLengthNonnegative=True,
        requiredPriorCountWithinEntriesLength=True,
        fillCalls=([dict(region='entire buckets array',valueByte=0),
                    dict(region='first prior count entries',valueByte=0)]if positive else[]),
        ownFillEffectsRequired=positive,incomingMethodInfoUnused=True,
        entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'])


def blackboard_clear_program(regions,entry,*,clear_variables,clear_dictionary,subdictionary=True):
    need('nonnull-subdictionary-normal-path',subdictionary is True)
    g=BytesPath(regions,entry);g.take('4053','4883ec20');root=g.relative('488b05')
    g.take('488bd9','488b4810','4885c9');g.branch('0f85',False)
    g.take('33d2','488bcb');g.call(clear_variables)
    g.take('488b4b30','4885c9');g.branch('74',not subdictionary,1)
    site=method=None
    if subdictionary:
        site=g.at;method=g.relative('488b15');g.take('4883c420','5b')
        need('own-subdictionary-Clear-tail',g.relative('e9')==clear_dictionary)
    else:g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,replacementReceiverOffset=16,
        variableClearBeforeSubdictionaryClear=True,subdictionaryFieldOffset=48,
        subdictionaryRequiredNonNull=subdictionary,subdictionaryMethodInfoSiteVa=site,
        subdictionaryMethodInfoCellVa=method,entryRspRestoredBeforeTail=True,
        restoredNonvolatiles=['rbx'],nestedBlackboardsRecursivelyCleared=False)


def clear_variables_program(regions,entry,*,barrier,move_next,assignable,recycle,clear_dictionary,count=0):
    need('bounded-clear-loop-witness',type(count)is int and 0<=count<=3)
    g=BytesPath(regions,entry)
    g.take('488bc4','48895810','48897020','48894808','57','4154','4155','4156','4157',
        '4881eca0000000','0f2970c8','488bda','4c8be9')
    ready=flag(g);g.branch('75',True,1)
    root=g.relative('488b05');g.take('488b4810','4885c9');g.branch('74',True,1)
    g.take('0f57c0','33c0','0f11442460','0f11442470','4889842480000000','498b5d28','4885db');g.branch('0f84',False)
    g.take('f30f7f442440','0f57c9','f30f7f4c2450','48895c2438','488d4c2438');g.call(barrier)
    g.take('4885db');g.branch('0f84',False)
    g.take('8b432c','89442440','4533e4','4489642444','c744245802000000','0f114c2448',
        '0f10442438','0f11442460','0f114c2470','f20f10442458','f20f11842480000000',
        '4c89642428','488d442460','4889442430')
    image_base=g.relative('4c8d35');unused_helper=g.relative('488d35');g.take('0f1f840000000000')
    loop=g.at;enum_site=global_site=map_site=clear_site=None;enum_cell=global_cell=map_cell=clear_cell=None
    for i in range(count+1):
        need('same-variable-loop',g.at==loop)
        enum_site=g.at;enum_cell=g.relative('488b15');g.take('488d4c2460');g.call(move_next)
        g.take('84c0');g.branch('0f84',i==count)
        if i==count:break
        g.take('0f10742470','660f6fc6','660f73d808','66480f7ec3','4885db');g.branch('74',False,1)
        global_site=g.at;global_cell=g.relative('488b15');g.take('488b0b');g.call(assignable)
        g.take('84c0');g.branch('74',True,1)
        g.take('660f73de08','66490f7ef7','4d85ff');g.branch('0f84',False)
        map_site=g.at;map_cell=g.relative('488b15');g.take('498b0f');g.call(assignable)
        g.take('84c0');g.branch('0f84',True)
        g.take('33d2','498bcf');g.call(recycle);g.jump('e9')
    g.jump('eb',1)
    g.take('498b4d28','4885c9');g.branch('74',False,1)
    clear_site=g.at;clear_cell=g.relative('488b15');g.call(clear_dictionary);g.jump('e9')
    g.take('4c8d9c24a0000000','498b5b38','498b7348','410f2873f0','498be3','415f','415e','415d','415c','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlagVa=ready,replacementRootCellVa=root,
        requiredAbsentReplacementReceiverOffset=16,variableDictionaryFieldOffset=40,
        dictionaryVersionOffset=44,enumeratorStackOffset=96,enumeratorBytes=40,
        enumeratorInitializedDictionary=True,enumeratorIndexInitializedZero=True,
        enumeratorCurrentInitializedZero=True,enumeratorKindInitializedTwo=True,
        moveNextMethodInfoSiteVa=enum_site,moveNextMethodInfoCellVa=enum_cell,
        excludedGlobalVariableClassSiteVa=global_site,excludedGlobalVariableClassCellVa=global_cell,
        excludedMapVariableClassSiteVa=map_site,excludedMapVariableClassCellVa=map_cell,
        dictionaryClearMethodInfoSiteVa=clear_site,dictionaryClearMethodInfoCellVa=clear_cell,
        selectedOrdinaryValueCount=count,eachNonNullValueRecycledBeforeDictionaryClear=True,
        requiredEveryValueOutsideGlobalAndMapVariableClasses=True,
        requiredRecyclerLeavesEnumeratedDictionaryUnchanged=True,
        temporaryDisposalListRemainsNull=True,unusedImageBaseVa=image_base,
        unusedColdHelperVa=unused_helper,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rsi','rdi','r12','r13','r14','r15','xmm6'],xmmSaveRestoreBytes=16,
        specializedGlobalAndMapBranchesProved=False,exceptionCleanupEffectsProved=False)


def clear_variable_paths(regions,entry,*,barrier,move_next,assignable,recycle,clear_dictionary,count_limit=4096):
    need('finite-variable-clear-domain',type(count_limit)is int and 0<count_limit<=4096)
    witnesses=[clear_variables_program(regions,entry,barrier=barrier,move_next=move_next,
        assignable=assignable,recycle=recycle,clear_dictionary=clear_dictionary,count=n)for n in range(4)]
    return dict(witnesses=witnesses,countLimit=count_limit,
        induction=dict(ownMoveNextInductionRequired=True,oneRecyclerCallPerReturnedOrdinaryValue=True,
            currentValueCopiedUnchanged=True,loopReturnsToExactMoveNextSite=True,
            dictionaryCountVersionAndEntriesImmutableUntilFinalClearRequired=True,
            nonthrowingRecyclerEffectsRequired=True,finalOwnDictionaryClearRequired=True),
        runtimeInvocationObserved=False)


def object_pool_callback_program(regions,entry,*,compatible,dispatch,recycle):
    need('boolean-pool-callback',type(recycle)is bool)
    g=BytesPath(regions,entry)
    g.take('48895c2410','57','4883ec20');interface=g.relative('488b3d')
    g.take('488bda','4885d2');g.branch('74',False,1)
    g.take('4889742430','488bcf','488b32','488bd6');g.call(compatible)
    g.take('84c0');g.branch('74',False,1)
    need('same-pool-callback-interface',g.relative('488b35')==interface)
    g.take('488b3b','488bce','488bd7');g.call(compatible)
    g.take('84c0');g.branch('74',False,1)
    if recycle:g.take('33d2')
    g.take('488bcb','488b742430','488b5c2438','4883c420','5f')
    need('own-interface-dispatch-tail',g.relative('e9')==dispatch)
    return dict(selectedBytes=g.seen,interfaceClassCellVa=interface,
        sameNonNullIncomingValueUsedForBothCompatibilityChecks=True,
        sameValuePassedToSelectedInterfaceCallback=True,recycle=recycle,
        selectedInterfaceCompatibilityEffectsRequired=True,selectedDispatchEffectsRequired=True,
        entryRspRestoredBeforeTail=True,restoredNonvolatiles=['rbx','rsi','rdi'])


def variable_type_program(regions,entry,*,from_handle):
    g=BytesPath(regions,entry);g.take('4053','4883ec20','488b4220');site=g.at;type_class=g.relative('488b0d')
    g.take('488b98c0000000','83b9e000000000','488b1b');g.branch('74',False,1)
    g.take('33d2','488bcb','4883c420','5b')
    need('own-Type-GetTypeFromHandle-tail',g.relative('e9')==from_handle)
    return dict(selectedBytes=g.seen,typeClassSiteVa=site,typeClassCellVa=type_class,
        ownMethodInfoClassContextSlot=0,closedTypeHandlePassedUnchanged=True,
        canonicalCorrespondingTypeResultRequired=True,entryRspRestoredBeforeTail=True,
        restoredNonvolatiles=['rbx'],runtimeTypeHandleObjectObserved=False)


def variable_type_invoker_program(regions,entry,*,prepare,callback):
    g=BytesPath(regions,entry)
    g.take('48895c2408','55','56','57','4154','4155','4156','4157','4883ec50','488bfa','0fb7d9','488b0a');g.call(prepare)
    g.take('488d4b14','4803c9','488b07','4c8b04c8','488b54c808');excluded=[]
    for _ in range(2):
        excluded.append(g.relative('488d05'));g.take('4c3bc0');g.branch('0f85',True)
    excluded.append(g.relative('488d05'));g.take('488bcf','4c3bc0');g.branch('75',True,1)
    need('own-type-getter-outside-inline-alternatives',type(callback)is int and callback>0 and callback not in excluded)
    g.take('41ffd0','488bd8','488bc3','488b9c2490000000','4883c450','415f','415e','415d','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,selector=9,selectedCallbackRequired=callback,
        callbackByteOffset=464,methodInfoByteOffset=472,excludedInlineCallbacks=excluded,
        sameVariableAndMethodInfoPassed=True,wholeRaxResultReturnedUnchanged=True,
        entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'])


def ordinary_variable_recycler_program(regions,entry,*,get_type_invoke,context_type,type_from_context,
        try_get,prepare,recycle_typed,assignable,singleton,push,mode,misses=0):
    need('finite-ordinary-recycle-arm',mode in('first-direct','second-direct','entity-interface'))
    need('bounded-pool-interface-index',type(misses)is int and 0<=misses<=3)
    g=BytesPath(regions,entry);g.take('4057','4883ec40');root=g.relative('488b05')
    g.take('488bf9','488b4810','4885c9');g.branch('74',True,1)
    g.take('48895c2450','33db','48895c2420','48895c2468','4885ff');g.branch('0f84',False)
    g.take('4889742438','395f10');g.branch('0f84',False)
    g.take('48896c2458','b909000000','488bd7');g.call(get_type_invoke)
    registry_site=g.at;registry=g.relative('488b2d');g.take('488bf0','488b4d20');g.call(context_type)
    g.take('33d2','488b88c0000000');g.call(type_from_context)
    g.take('488b90b8000000','48391a');g.branch('75',True,1)
    g.take('488b4d20');g.call(context_type)
    g.take('33d2','488b88c0000000');g.call(type_from_context)
    g.take('488b88b8000000','488b29','4885ed');g.branch('0f84',False)
    g.take('488b6d10','4885ed');g.branch('0f84',False)
    lookup_site=g.at;lookup=g.relative('4c8b0d')
    g.take('4c8d442420','488bd6','4c89742430','488bcd');g.call(try_get)
    g.take('84c0');g.branch('0f85',True)
    g.take('488b742420','4885f6');g.branch('0f84',False)
    g.take('488b0e','8b911c010000','81ea');first=int.from_bytes(g.read(4),'little',signed=True)
    g.branch('0f84',mode=='first-direct')
    interface_site=interface=None;callback=None;collector=None;steps=[]
    if mode!='first-direct':
        g.take('83fa01');g.branch('0f84',mode=='second-direct')
    if mode!='entity-interface':
        g.call(prepare);g.take('4c8b06','488bd7','488bce','4d8b8098010000');g.call(recycle_typed);g.jump('e9')
    else:
        interface_site=g.at;interface=g.relative('488b2d');g.take('4c8bf1');g.call(prepare)
        g.take('410fb78e30010000','663bd9');g.branch('73',False,1)
        g.take('498b96b0000000');loop=g.at
        for i in range(misses+1):
            need('same-recycle-interface-loop',g.at==loop);start=len(g.seen)
            g.take('0fb7c3','4803c0','48392cc2');g.branch('0f84',i==misses)
            if i<misses:g.take('66ffc3','663bd9');g.branch('72',True,1)
            steps.append(g.seen[start:])
        g.take('0fb7cb','4803c9','8b44ca08','ffc0','4898','4883c014','48c1e004','4903c6');g.jump('e9')
        g.take('4c8b08','488b5808');excluded=[]
        for _ in range(2):
            excluded.append(g.relative('488d05'));g.take('4c3bc8');g.branch('0f85',True)
        callback=g.relative('488d05');g.take('4c3bc8');g.branch('75',False,1)
        need('own-Entity-recycle-callback',callback==recycle_typed and callback not in excluded)
        g.take('488b4320','488b88c0000000','488b4160','f6803801000001');g.branch('75',True,1)
        g.take('488b0f','488bd0');g.call(assignable);g.take('84c0');g.branch('0f85',True)
        g.take('488b0f');g.call(prepare)
        g.take('488b17','488bcf','488b82c0010000','488b92c8010000','ffd0',
            '488b4320','488b88c0000000','488b4948');g.call(singleton)
        g.take('4885c0');g.branch('0f84',False)
        g.take('488b7010','4885f6');g.branch('0f84',False)
        g.take('488b4320','488b90c0000000','488b4270','4883782000');g.branch('75',True,1)
        g.take('488b4320','488bd7','488bce','4c8b80c0000000','4d8b4070');g.call(push);g.jump('e9')
    g.take('4c8b742430','488b6c2458','488b742438','488b5c2450','4883c440','5f','c3')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,replacementReceiverOffset=16,
        incomingVariableRequiredNonNull=True,incomingVariableSerialRequiredNonZeroOffset=16,
        getTypeSelector=9,registryMethodInfoSiteVa=registry_site,registryMethodInfoCellVa=registry,
        registrySingletonRequiredWarmNonNull=True,registryDictionaryFieldOffset=16,
        lookupMethodInfoSiteVa=lookup_site,lookupMethodInfoCellVa=lookup,
        canonicalCorrespondingSystemTypeKeyRequired=True,lookupRequiredHitNonNullPool=True,
        classDiscriminatorOffset=284,requiredDirectClassDiscriminator=(first+(mode=='second-direct'))if mode!='entity-interface'else None,
        requiredDiscriminatorOutsideDirectPair=mode=='entity-interface',metadataTypeIndexEquivalenceProved=False,
        interfaceClassSiteVa=interface_site,interfaceClassCellVa=interface,firstMatchingInterfaceIndex=misses,
        interfaceMethodOrdinal=1,interfaceEntryStride=16,failedSearchPrograms=steps[:-1],
        selectedRecycleCallbackRequired=recycle_typed,selectedEntityInlineArmProved=mode=='entity-interface',
        entityResetSelector=8 if mode=='entity-interface'else None,
        entitySelectedVirtualResetEffectsRequired=mode=='entity-interface',sameVariableRecycled=True,
        registryLookupEffectsRequired=True,closedTypedRecycleEffectsRequired=True,
        entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','r14'],
        coldRegistryCreationOrMissingEntryEffectsProved=False,runtimePoolSelectionObserved=False)

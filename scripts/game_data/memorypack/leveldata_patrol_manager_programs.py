"""Finite byte programs for the event executor manager's post-invoke path."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check, condition):
    if not condition:
        raise ValueError('patrolManager.' + check)


def on_invoked(regions, entry):
    """The not-finished, empty-child-list branch, including its Tick request."""
    g=BytesPath(regions,entry);calls={};uses={}
    def call(role):
        at=g.at;target=g.relative('e8');calls[role]=dict(instructionVa=at,targetVa=target)
    def use(role,prefix):
        at=g.at;cell=g.relative(prefix);uses[role]=dict(instructionVa=at,cellVa=cell);return cell
    g.take('4057','4883ec40');ready=g.relative('803d')+1
    g.take('00','488bf9');g.branch('0f84',False)
    g.take('807f6900','0f57c0','0f11442420','48895c2450');g.branch('0f85',False)
    cls=use('listPoolClass','488b0d');g.take('83b9e000000000');g.branch('0f84',False)
    use('listPoolAllocate','488b0d');call('allocate')
    g.take('488bd8','4885c0');g.branch('0f84',False)
    use('listAddRange','4c8b05');g.take('488bc8','488b5760','4889742458');call('addRange')
    g.take('8b7318','83ee01');g.branch('0f89',False)
    use('listClear','488b15');g.take('488bcb');call('clear')
    need('same-ListPool-class-cell',use('listPoolClassAgain','488b0d')==cls)
    g.take('488b742458','83b9e000000000');g.branch('0f84',False)
    use('listPoolRecycle','488b15');g.take('488bcb');call('recycle')
    use('timeSingleton','488b0d');call('time')
    g.take('4885c0');g.branch('74',False,1)
    g.take('f30f10482c','4533c0','488bcf');call('tick')
    g.take('488b5c2450','4883c440','5f','c3')
    return dict(selectedBytes=g.seen,actualCalls=calls,typedUsageSites=uses,
        metadataReadyFlagVa=ready,isFinishedOffset=105,isFinishedRequired=False,
        childListFieldOffset=96,childListRequiredNonnull=True,childListCountRequired=0,
        rentedListInitiallyEmptyRequired=True,rentedListCountAfterAddRange=0,
        recursiveChildrenInvoked=0,timeDeltaFieldOffset=44,
        tickArguments=dict(rcx='same incoming executor',xmm1='unchanged selected time singleton field44 Single',r8d=0),
        frameBytes=72,entryRspRestored=True,restoredNonvolatiles=['rbx','rsi','rdi'])


def tick(regions,entry):
    g=BytesPath(regions,entry)
    g.take('48895c2410','4889742418','48894c2408','57','4154','4155','4156','4157','4883ec50','4533c0')
    at=g.at;target=g.relative('e8')
    g.take('90','4c8d5c2450','498b5b38','498b7340','498be3','415f','415e','415d','415c','5f','c3')
    return dict(selectedBytes=g.seen,logicTickCall=dict(instructionVa=at,targetVa=target),
        sameExecutorAndDelta=True,thirdArgument=0,frameBytes=120,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rsi','rdi','r12','r13','r14','r15'])


def recycle_wrapper(regions,entry):
    g=BytesPath(regions,entry);calls=[]
    def call(role):
        at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
    g.take('48895c2408','4889742410','57','4883ec20','488bf1','488bda','488b4a20')
    ready=call('ready');g.take('33d2','488b88c0000000');indexed=call('indexed')
    g.take('83b8e000000000');g.branch('74',False,1)
    g.take('488b4b20');need('same-recycle-ready',call('ready')==ready)
    g.take('33d2','488b88c0000000');need('same-recycle-indexed',call('indexed')==indexed)
    g.take('488b88b8000000','488b39','4885ff');g.branch('74',False,1)
    g.take('488b4b20');need('same-recycle-ready',call('ready')==ready)
    g.take('488b88c0000000','488b4130','4883782000');g.branch('0f84',False)
    g.take('488b4b20');need('same-recycle-ready',call('ready')==ready)
    g.take('488bd6','488bcf','4c8b80c0000000','4d8b4030','488b5c2430','488b742438','4883c420','5f')
    target=g.relative('e9')
    return dict(selectedBytes=g.seen,calls=calls,backendTargetVa=target,backendContextSlotOffset=48,
        arguments=dict(rcx='same initialized ObjectPool',rdx='same incoming list',r8='own Recycle MethodInfo'),
        frameBytes=40,entryRspRestored=True,restoredNonvolatiles=['rbx','rsi','rdi'])


def time_getter(regions,entry):
    g=BytesPath(regions,entry);g.take('4883ec28','488b4920');ready=g.relative('e8')
    g.take('33d2','488b88c0000000');indexed=g.relative('e8')
    g.take('488b80b8000000','488b00','4883c428','c3')
    return dict(selectedBytes=g.seen,readyTargetVa=ready,indexedTargetVa=indexed,
        contextSlot=0,staticFieldOffset=0,result='same initialized singleton reference',
        frameBytes=40,entryRspRestored=True,nonframeWrites=0)


def _walk(regions,entry,steps):
    g=BytesPath(regions,entry);calls={};sites={}
    for step in steps:
        if step[0]=='take':g.take(step[1])
        elif step[0]=='branch':g.branch(step[1],step[2],step[3])
        elif step[0]=='jump':g.jump(step[1],step[2])
        elif step[0]=='call':
            at=g.at;target=g.relative('e8');calls[step[1]]=dict(instructionVa=at,targetVa=target)
        elif step[0]=='cell':
            _,role,prefix,tail=step;at=g.at;cell=g.relative(prefix)+len(bytes.fromhex(tail));g.take(tail)
            sites[role]=dict(instructionVa=at,cellVa=cell)
        else:raise ValueError('patrolManager.unknown-instruction-profile')
    return dict(selectedBytes=g.seen,actualCalls=calls,sourceSites=sites)


def logic_tick(regions,entry):
    p=_walk(regions,entry,_TICK_STEPS)
    p.update(entryRspRestored=True,frameBytes=408,
        restoredNonvolatiles=['rbx','rsi','rdi','r12','r13','r14','r15','xmm6','xmm7','xmm8'],
        inputState=dict(isStarted=True,isFinished=False,timer=0,executeTimeStamp=0,
            delayToNextTick=False,delayToNextTickAllowDeltaTimeZero=False,ticking=False,ticked=False,
            currentAction=None,cursorCount=1,previousResultCount=1,previousResult=True,iteratedNodeCount=0),
        selectedState=dict(deltaTime=0,executorUidNonzero=True,contextPtrValid=True,
            selectedActionExecutorPtr='same stable executor reference and nonzero UID',
            initialCursor='nonnegative header next-node ID',actionMapNode='same indexed nonnull ActionBase',
            priorActionPhase=0,iterationDictionary='initialized empty with spare slot and null default comparer',
            actionCallbackNormalReturn=True,actionResult=True,actionNextId='nonnegative Int32',
            actionReservedId=-1,extraThreadCount=0,waitUidList=None,
            actionFinishThread=False,actionDelayToNextTick=False,actionDelayAllowZero=False,
            actionDelay='finite positive Single greater than the actual positive timer epsilon'),
        outputState=dict(isStarted=True,isFinished=False,timer=0,ticking=False,ticked=False,
            currentAction='same selected ActionBase',cursorCount=1,previousResultCount=1,
            previousResult=True,iteratedNodeCount=1,executeTimeStamp='same selected positive action delay',
            delayToNextTick=False,delayToNextTickAllowDeltaTimeZero=False),
        executedCursorIterations=1,recursiveChildrenInvoked=0,scopeDisposedExactlyOnce=True,
        condition='Same tracked executor and context remain stable; actual ordinary action callbacks return normally, leave the stated protected fields unchanged, and publish the stated action result/next/delay fields. Their identity and authored effects remain unobserved.')
    return p


def timer_predicate(regions,entry):
    g=BytesPath(regions,entry);g.take('4883ec48');root=g.relative('488b05')
    g.take('4c8b4828','4d85c9');g.branch('0f85',False)
    g.take('0f57c0','0f2f4178');g.branch('77',False,1)
    g.take('0f29742430','f30f107178','0f297c2420','f30f10796c')
    cls=g.relative('488b0d');g.take('83b9e000000000');g.branch('74',False,1)
    epsilon=g.relative('f30f5c35')
    g.take('0f2ff7','0f287c2420','0f28742430','0f97c0','4883c448','c3')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,readyClassCellVa=cls,
        epsilonVa=epsilon,timerOffset=108,executeTimeStampOffset=120,
        result='ordered (executeTimeStamp - actual epsilon) > timer',
        initialZeroStateResult=False,positiveDelayGreaterThanEpsilonResult=True,
        noOpaqueCalls=True,nonframeWrites=0,frameBytes=72,entryRspRestored=True,
        restoredNonvolatiles=['xmm6','xmm7'])


def queue_add(regions,entry):
    g=BytesPath(regions,entry)
    g.take('48895c2410','48896c2418','56','57','4156','4883ec30','ff411c','498be8',
        '488b7110','4c8bf2','48635918','488bf9','4885f6');g.branch('0f84',False)
    g.take('3b5e18');g.branch('72',True,1)
    g.take('8d4301','894118','3b5e18');g.branch('73',False,1)
    g.take('0f1002','488d4302','4803c0');collector=g.relative('833d')+1
    g.take('00','0f1104c6');g.branch('74',True,1)
    g.take('488b5c2458','488b6c2460','4883c430','415e','5f','5e','c3')
    return dict(selectedBytes=g.seen,collectorFlagVa=collector,collectorDisabledRequired=True,
        spareCapacityRequired=True,entryBytes=16,sourceBytes=16,allObjectPtrBitsPreserved=True,
        sizeFieldOffset=24,sizeDelta=1,versionFieldOffset=28,versionDelta=1,
        arrayFieldOffset=16,arrayDataOffset=32,elementBytes=16,
        frameBytes=72,entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','r14'])


def before_enter(regions,entry):
    g=BytesPath(regions,entry);g.take('4883ec28');root=g.relative('488b05')
    g.take('4c8b4808','4d85c9');g.branch('0f85',False)
    g.take('83794c01');g.branch('74',False,1)
    g.take('ff4148','33c0','c7414c01000000','4883c428','c3')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,initialNodePhase=0,
        nodePhaseOffset=76,nodePhaseAfter=1,enterCountOffset=72,enterCountDeltaMod32=1,
        returnedInt32=0,frameBytes=40,entryRspRestored=True,normalCalls=0)


def reset_execute_result(regions,entry):
    g=BytesPath(regions,entry);g.take('4883ec28');root=g.relative('488b05')
    g.take('4c8b4828','4d85c9');g.branch('0f85',False)
    g.take('488b5178','4533c0','8b4160','66c741640100','894168','c7416cffffffff',
        '44894170','6644894174','4885d2');g.branch('74',False,1)
    g.take('ff421c','44894218','4c898180000000','4883e980','4883c428');target=g.relative('e9')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,tailBarrierTargetVa=target,
        initialExtraThreadListRequiredNonnull=True,extraThreadCountAfter=0,
        actionResultOffset=100,actionResultAfter=True,finishThreadOffset=101,finishThreadAfter=False,
        nextIdOffset=104,nextIdSourceOffset=96,reservedIdOffset=108,reservedIdAfter=-1,
        delayOffset=112,delayAfter=0,delayTickOffsets=[116,117],delayTicksAfter=False,
        waitUidListOffset=128,waitUidListAfter=None,frameBytes=40,entryRspRestored=True)


def action_enter(regions,entry):
    g=BytesPath(regions,entry);calls={};sites={}
    def call(role):
        at=g.at;target=g.relative('e8');calls[role]=dict(instructionVa=at,targetVa=target)
    def use(role,prefix):
        at=g.at;cell=g.relative(prefix);sites[role]=dict(instructionVa=at,cellVa=cell)
    g.take('4053','4883ec60','488bd9');use('replacement','488b05')
    g.take('488b4828','4885c9');g.branch('74',True,1)
    g.take('0f57c0','0f11442438','0f57c9','0f114c2428','33d2','488bcb');call('beforeEnter')
    g.take('83f802');g.branch('0f84',False);g.take('85c0');g.branch('0f85',False)
    g.take('48c7838800000000000000','488d8b88000000');call('barrier')
    g.take('c783c000000000000000','0f104328','0f11442438');use('objectPtrClass','488b0d')
    g.take('488b4920');call('ready')
    g.take('488b90c0000000','488b5208','488d4c2438');call('valid')
    g.take('84c0');g.branch('74',False,1);g.take('488b542438','4885d2');g.branch('74',False,1)
    g.take('4533c0','488d4c2448');call('pushContext')
    g.take('0f1000','0f11442428','48c744244800000000','488d442428','4889442450','488b0b');call('prepare')
    g.take('488b13','488b8240020000','488b9248020000','488bcb');callback=g.at;g.take('ffd0','90')
    use('scopeDispose','488b15');g.take('488d4c2428');call('scopeDispose');g.jump('eb',1)
    g.take('b001','4883c460','5b','c3')
    return dict(selectedBytes=g.seen,actualCalls=calls,sourceSites=sites,callbackInstructionVa=callback,
        callbackSlot=16,callbackOffset=576,methodInfoOffset=584,
        callbackArguments=dict(rcx='same selected ActionBase',rdx='actual slot16 MethodInfo'),
        callbackNormalReturnRequired=True,authoredCallbackEffectsProved=False,returnedBool=True,
        actionExecutorPtrOffset=40,actionExecutorPtrValidRequired=True,
        waitStartParamOffset=136,waitStartParamAfter=None,waitStartTimeOffset=192,waitStartTimeAfter=0,
        scopeBytes=16,scopeHome=[40,56],scopeDisposedExactlyOnce=True,frameBytes=104,
        entryRspRestored=True,restoredNonvolatiles=['rbx'])


def action_execute(regions,entry):
    g=BytesPath(regions,entry);calls={};sites={}
    def call(role):
        at=g.at;target=g.relative('e8');calls[role]=dict(instructionVa=at,targetVa=target)
    def use(role,prefix):
        at=g.at;cell=g.relative(prefix);sites[role]=dict(instructionVa=at,cellVa=cell)
    g.take('48895c2408','57','4883ec70','0f29742460','0f28f1','488bd9');use('replacement','488b05')
    g.take('488b4828','4885c9');g.branch('74',True,1)
    g.take('0f57c0','0f11442438','0f57c9','0f114c2428','33d2','488bcb');call('resetExecuteResult')
    g.take('40b701','4088bc2498000000','0f104328','0f11442438');use('objectPtrClass','488b0d')
    g.take('488b4920');call('ready')
    g.take('488b90c0000000','488b5208','488d4c2438');call('valid')
    g.take('84c0');g.branch('0f84',False);g.take('488b542438','4885d2');g.branch('0f84',False)
    g.take('4533c0','488d4c2448');call('pushContext')
    g.take('0f1000','0f11442428','48c744244800000000','488d442428','4889442450','488b0b');call('prepare')
    g.take('4c8b03','498b8030020000','4d8b8038020000','0f28ce','488bcb');callback=g.at;g.take('ffd0')
    g.take('0fb67b64','4088bc2498000000');use('scopeDispose','488b15')
    g.take('488d4c2428');call('scopeDispose');g.jump('eb',1)
    g.take('400fb6c7','488b9c2480000000','0f28742460','4883c470','5f','c3')
    return dict(selectedBytes=g.seen,actualCalls=calls,sourceSites=sites,callbackInstructionVa=callback,
        callbackSlot=15,callbackOffset=560,methodInfoOffset=568,
        callbackArguments=dict(rcx='same selected ActionBase',xmm1='unchanged incoming Single delta',r8='actual slot15 MethodInfo'),
        callbackNormalReturnRequired=True,authoredCallbackEffectsProved=False,
        actionResultFieldOffset=100,returnsSameActionResultByte=True,
        actionExecutorPtrOffset=40,actionExecutorPtrValidRequired=True,
        scopeBytes=16,scopeHome=[40,56],scopeDisposedExactlyOnce=True,
        frameBytes=120,entryRspRestored=True,restoredNonvolatiles=['rbx','rdi','xmm6'])


def iteration_find(regions,entry):
    p=_walk(regions,entry,_ITERATION_FIND_STEPS)
    p.update(dictionary='actual Dictionary<Int32,Int32>',bucketsRequiredNonnull=True,
        bucketLengthRequiredPositive=True,selectedBucketRequiredZero=True,entriesRequiredNonnull=True,
        comparerRequiredNull=True,hash='raw input UInt32 with sign bit cleared',
        bucket='signed remainder of nonnegative hash by positive bucket length',
        entriesVisited=0,result=-1,nonframeWrites=0,opaqueCalls=0,
        frameBytes=88,entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'])
    return p


def iteration_insert(regions,entry):
    p=_walk(regions,entry,_ITERATION_INSERT_STEPS)
    p.update(dictionary='actual Dictionary<Int32,Int32>',initialCount=0,initialFreeCount=0,
        selectedBucketRequiredZero=True,bucketLengthRequiredPositive=True,bucketLengthExcluded=3,
        entriesCapacityRequiredPositive=True,comparerRequiredNull=True,
        entryBytes=16,hashOffset=0,nextOffset=4,keyOffset=8,valueOffset=12,
        hash='raw input UInt32 with sign bit cleared',
        insertedEntryIndex=0,countAfter=1,entryNextAfter=-1,selectedBucketAfter=1,
        fullInputKeyAndValueBitsPreserved=True,versionOffset=44,versionDeltaMod32=1,
        returns=True,normalCalls=0,frameBytes=104,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'])
    return p


def push_action_context(regions,entry):
    g=BytesPath(regions,entry);calls={};sites={}
    def call(role):
        at=g.at;target=g.relative('e8');calls[role]=dict(instructionVa=at,targetVa=target)
    g.take('4889742410','57','4883ec30');root=g.relative('488b05')
    g.take('488bf2','488bf9','488b5028','4885d2');g.branch('0f85',False)
    g.take('33d2','48895c2440','488bce');call('getContext')
    g.take('4533c0','488d4c2420','488bd0');call('pushBlackboardContext')
    g.take('33d2','488bce','0f1000','0f1107');call('getContextAgain')
    at=g.at;cell=g.relative('4c8b05');sites['implicit']=dict(instructionVa=at,cellVa=cell)
    g.take('488d4c2420','488bd6','488bd8');call('implicit')
    g.take('4885db');g.branch('74',False,1)
    g.take('0f10442420','488d4b48','0f114348');call('barrier')
    g.take('488b5c2440','488b742448','488bc7','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,actualCalls=calls,sourceSites=sites,
        replacementRootCellVa=root,contextRequiredNonnull=True,
        sameContextAndTrackedExecutorRequired=True,contextExecutorPtrOffset=72,
        storedExecutorPtrBytes=16,returnedSameHiddenScope16=True,
        frameBytes=56,entryRspRestored=True,restoredNonvolatiles=['rbx','rsi','rdi'])


def push_blackboard_context(regions,entry):
    g=BytesPath(regions,entry);calls={};sites={}
    def call(role):
        at=g.at;target=g.relative('e8');calls[role]=dict(instructionVa=at,targetVa=target)
    g.take('48895c2408','57','4883ec30');root=g.relative('488b05')
    g.take('488bda','488bf9','488b5010','4885d2');g.branch('0f85',False)
    g.take('4885db');g.branch('74',False,1)
    g.take('b90b000000','488bd3');call('contextPushDispatch')
    g.take('33c9');call('getScopeStack')
    g.take('4885c0');g.branch('74',False,1)
    at=g.at;cell=g.relative('4c8b0d');sites['scopePush']=dict(instructionVa=at,cellVa=cell)
    g.take('488d4c2420','4c8bc3','488bd0');call('scopePush')
    g.take('0f10442420','0f1107','488b5c2440','488bc7','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,actualCalls=calls,sourceSites=sites,replacementRootCellVa=root,
        selector=11,sameIncomingContextPassedToCallbackAndScope=True,
        sameCachedScopeStackRequiredNonnull=True,returnsSameScope16=True,
        frameBytes=56,entryRspRestored=True,restoredNonvolatiles=['rbx','rdi'])


def context_push_dispatch(regions,entry):
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec40','0fb7d9','488bfa','488b0a','0f29742430')
    prepare=g.relative('e8')
    g.take('488b07','488d4b14','4803c9','4c8b04c8','488b54c808');excluded=[]
    for op,width in(('74',1),('74',1),('0f84',4)):
        excluded.append(g.relative('488d05'));g.take('4c3bc0');g.branch(op,False,width)
    g.take('488bcf');at=g.at;g.take('41ffd0');g.jump('eb',1)
    g.take('488b5c2450','488b742458','0f28742430','4883c440','5f','c3')
    return dict(selectedBytes=g.seen,prepareTargetVa=prepare,selectorRequired=11,
        callbackSlot=11,callbackOffset=496,methodInfoOffset=504,excludedInlineCallbacks=excluded,
        callbackInstructionVa=at,callbackArguments=dict(rcx='same actual ActionContext',rdx='actual slot11 MethodInfo'),
        callbackIdentityAndNormalReturnRequired=True,authoredCallbackEffectsProved=False,
        frameBytes=72,entryRspRestored=True,restoredNonvolatiles=['rbx','rsi','rdi','xmm6'])


def list_count(regions,entry):
    g=BytesPath(regions,entry);g.take('8b4118','c3')
    return dict(selectedBytes=g.seen,sizeFieldOffset=24,result='same List.size Int32',
        nonframeWrites=0,calls=0,entryRspAndNonvolatilesUntouched=True,
        physicalMethodExtentProved=False)


# One cursor/action, stable tracked executor, positive action delay.
_TICK_STEPS = (
    ('take', '488bc4'),
    ('take', 'f30f114810'),
    ('take', '48894808'),
    ('take', '53'),
    ('take', '56'),
    ('take', '57'),
    ('take', '4154'),
    ('take', '4155'),
    ('take', '4156'),
    ('take', '4157'),
    ('take', '4881ec60010000'),
    ('take', '0f2970b8'),
    ('take', '0f2978a8'),
    ('take', '440f294098'),
    ('take', '0f28f9'),
    ('take', '488bf9'),
    ('take', '48898c24a0000000'),
    ('take', '48898c24b8000000'),
    ('cell', 'site18', '488b05', ''),
    ('take', '488b4828'),
    ('take', '4885c9'),
    ('branch', '74', True, 1),
    ('take', '0f57c0'),
    ('take', '0f118424d0000000'),
    ('take', '4533ff'),
    ('take', '4c897c2440'),
    ('take', '0f11842480000000'),
    ('take', '0f11842490000000'),
    ('take', '450f57c0'),
    ('take', '410f2ef8'),
    ('branch', '7a', False, 1),
    ('branch', '74', True, 1),
    ('take', '4488bf80000000'),
    ('take', '4489bf84000000'),
    ('take', '44387f68'),
    ('branch', '0f84', False, 4),
    ('take', '44387f69'),
    ('branch', '0f85', False, 4),
    ('take', '44387f7c'),
    ('branch', '74', True, 1),
    ('take', '33d2'),
    ('take', '488bcf'),
    ('call', 'timerBefore'),
    ('take', '84c0'),
    ('branch', '0f85', False, 4),
    ('take', '488b5f40'),
    ('take', '4885db'),
    ('branch', '0f84', False, 4),
    ('take', '44397b18'),
    ('branch', '0f84', False, 4),
    ('cell', 'site80', '488b0d', ''),
    ('take', '4439b9e0000000'),
    ('branch', '75', True, 1),
    ('take', '4533c0'),
    ('take', '488bd7'),
    ('take', '488d8c2420010000'),
    ('call', 'pushExecutor'),
    ('take', '0f1000'),
    ('take', '0f118424d0000000'),
    ('take', '4c89bc24a8000000'),
    ('take', '488d9c24d0000000'),
    ('take', '48899c24b0000000'),
    ('cell', 'site93', '4c8d25', ''),
    ('take', '0f1f8000000000'),
    ('take', '488b4740'),
    ('take', '4885c0'),
    ('branch', '0f84', False, 4),
    ('take', '83781800'),
    ('branch', '0f8e', False, 4),
    ('take', 'ff8784000000'),
    ('take', '4885c0'),
    ('branch', '0f84', False, 4),
    ('take', '4c636818'),
    ('take', '458d75ff'),
    ('take', '4489b424b8010000'),
    ('take', '488bc8'),
    ('take', '48635018'),
    ('take', '8d42ff'),
    ('take', '3b4118'),
    ('branch', '0f83', False, 4),
    ('take', '488b4910'),
    ('take', '4885c9'),
    ('branch', '0f84', False, 4),
    ('take', '8d42ff'),
    ('take', '3b4118'),
    ('branch', '0f83', False, 4),
    ('take', '486374911c'),
    ('cell', 'site118', '488b15', ''),
    ('take', '488b4a28'),
    ('take', '4885c9'),
    ('branch', '74', True, 1),
    ('take', '0f104720'),
    ('take', '0f118424e0000000'),
    ('cell', 'site142', '488b05', ''),
    ('take', '488b4020'),
    ('take', 'f6803801000001'),
    ('branch', '75', True, 1),
    ('take', '488b90c0000000'),
    ('take', '488b5208'),
    ('take', '488d8c24e0000000'),
    ('call', 'contextValid'),
    ('take', '0fb6c8'),
    ('take', '498bc7'),
    ('take', '84c9'),
    ('take', '480f458424e0000000'),
    ('take', '4885c0'),
    ('branch', '0f84', False, 4),
    ('take', '488b4070'),
    ('take', '4885c0'),
    ('branch', '0f84', False, 4),
    ('take', '85f6'),
    ('branch', '0f88', False, 4),
    ('cell', 'site163', '488b05', ''),
    ('take', '488b4828'),
    ('take', '4885c9'),
    ('branch', '74', True, 1),
    ('take', '0f104720'),
    ('take', '0f118424f0000000'),
    ('cell', 'site188', '488b05', ''),
    ('take', '488b4020'),
    ('take', 'f6803801000001'),
    ('branch', '75', True, 1),
    ('take', '488b90c0000000'),
    ('take', '488b5208'),
    ('take', '488d8c24f0000000'),
    ('call', 'contextValidAgain'),
    ('take', '0fb6c8'),
    ('take', '498bc7'),
    ('take', '84c9'),
    ('take', '480f458424f0000000'),
    ('take', '4885c0'),
    ('branch', '0f84', False, 4),
    ('take', '488b4870'),
    ('take', '4885c9'),
    ('branch', '0f84', False, 4),
    ('cell', 'site207', '488b05', ''),
    ('take', '4c8b5028'),
    ('take', '4d85d2'),
    ('branch', '74', True, 1),
    ('take', '4883793000'),
    ('branch', '0f84', False, 4),
    ('take', '488b4130'),
    ('take', '397018'),
    ('branch', '0f8e', False, 4),
    ('branch', '0f86', False, 4),
    ('take', '488b44f020'),
    ('take', '4889442440'),
    ('cell', 'site232', '833d', '00'),
    ('branch', '74', True, 1),
    ('take', '4885c0'),
    ('branch', '0f84', False, 4),
    ('take', '81bf8400000000040000'),
    ('branch', '0f8f', False, 4),
    ('take', '4885c0'),
    ('branch', '0f84', False, 4),
    ('take', '0f107028'),
    ('take', '0f57c0'),
    ('take', '0f11442450'),
    ('cell', 'site256', '488b05', ''),
    ('take', '488b4820'),
    ('take', 'f6813801000001'),
    ('branch', '75', True, 1),
    ('take', '488bcf'),
    ('call', 'executorUid'),
    ('take', '85c0'),
    ('branch', '74', False, 1),
    ('take', '48897c2450'),
    ('cell', 'site266', '833d', '00'),
    ('branch', '74', True, 1),
    ('take', '488bcf'),
    ('call', 'executorUidAgain'),
    ('take', '89442458'),
    ('jump', 'eb', 1),
    ('cell', 'site288', '488b05', ''),
    ('take', '488b4020'),
    ('take', 'f6803801000001'),
    ('branch', '75', True, 1),
    ('take', '488b80c0000000'),
    ('take', '488b7028'),
    ('take', '0f28442450'),
    ('take', '660f7f442450'),
    ('take', '660f7f742470'),
    ('take', '488b4620'),
    ('take', 'f6803801000001'),
    ('branch', '75', True, 1),
    ('take', '488b90c0000000'),
    ('take', '488b5208'),
    ('take', '488d4c2470'),
    ('call', 'actionExecutorValid'),
    ('take', '440fb6f0'),
    ('take', '488b4620'),
    ('take', 'f6803801000001'),
    ('branch', '75', True, 1),
    ('take', '488b90c0000000'),
    ('take', '488b5208'),
    ('take', '488d4c2450'),
    ('call', 'executorValid'),
    ('take', '443af0'),
    ('branch', '75', False, 1),
    ('take', '8b442458'),
    ('take', '39442478'),
    ('branch', '0f84', True, 4),
    ('take', '488b4770'),
    ('take', '4839442440'),
    ('branch', '0f84', False, 4),
    ('take', '4885c0'),
    ('branch', '74', True, 1),
    ('take', '488b442440'),
    ('take', '48894770'),
    ('cell', 'site415', '833d', '00'),
    ('branch', '74', True, 1),
    ('take', '488b7738'),
    ('take', '488b4770'),
    ('take', '4885c0'),
    ('branch', '0f84', False, 4),
    ('take', '448b7810'),
    ('take', '4885f6'),
    ('branch', '0f84', False, 4),
    ('cell', 'site437', '4c8b35', ''),
    ('take', '498b4620'),
    ('take', '488b88c0000000'),
    ('take', '488b81b0000000'),
    ('take', '4883782000'),
    ('branch', '75', True, 1),
    ('take', '498b4620'),
    ('take', '4c8b80c0000000'),
    ('take', '4d8b80b0000000'),
    ('take', '418bd7'),
    ('take', '488bce'),
    ('call', 'iterationFind'),
    ('take', '85c0'),
    ('branch', '78', True, 1),
    ('take', '488b4f70'),
    ('take', '4885c9'),
    ('branch', '0f84', False, 4),
    ('take', '33d2'),
    ('call', 'resetActionIteration'),
    ('take', '4c8b7738'),
    ('take', '488b4770'),
    ('take', '4885c0'),
    ('branch', '0f84', False, 4),
    ('take', '448b7810'),
    ('take', '4d85f6'),
    ('branch', '0f84', False, 4),
    ('cell', 'site493', '488b35', ''),
    ('take', '488b4620'),
    ('take', '488b88c0000000'),
    ('take', '488b81c0000000'),
    ('take', '4883782000'),
    ('branch', '75', True, 1),
    ('take', '488b4620'),
    ('take', '4c8b80c0000000'),
    ('take', '498b80c0000000'),
    ('take', '4889442420'),
    ('take', '41b101'),
    ('take', '418d75ff'),
    ('take', '448bc6'),
    ('take', '418bd7'),
    ('take', '498bce'),
    ('call', 'iterationInsert'),
    ('take', '488b4748'),
    ('take', '4885c0'),
    ('branch', '0f84', False, 4),
    ('take', '3b7018'),
    ('branch', '0f83', False, 4),
    ('take', '488b4810'),
    ('take', '4885c9'),
    ('branch', '0f84', False, 4),
    ('take', '3b7118'),
    ('branch', '0f83', False, 4),
    ('take', '41807c0d1f00'),
    ('branch', '0f84', False, 4),
    ('take', '488b4f70'),
    ('take', '4885c9'),
    ('branch', '0f84', False, 4),
    ('take', '33d2'),
    ('call', 'enter'),
    ('take', '84c0'),
    ('branch', '0f84', False, 4),
    ('take', 'c6878000000001'),
    ('take', '488b4f70'),
    ('take', '4885c9'),
    ('branch', '0f84', False, 4),
    ('take', '4533c0'),
    ('take', '0f28cf'),
    ('call', 'execute'),
    ('take', '807f6800'),
    ('branch', '0f84', False, 4),
    ('take', '807f6900'),
    ('branch', '0f85', False, 4),
    ('take', 'c6878000000000'),
    ('take', '488b4f48'),
    ('take', '4885c9'),
    ('branch', '0f84', False, 4),
    ('take', '4c63ac24b8010000'),
    ('take', '443b6918'),
    ('branch', '0f83', False, 4),
    ('take', '488b5110'),
    ('take', '4885d2'),
    ('branch', '0f84', False, 4),
    ('take', '443b6a18'),
    ('branch', '0f83', False, 4),
    ('take', '4188441520'),
    ('take', 'ff411c'),
    ('take', '488b4770'),
    ('take', '4885c0'),
    ('branch', '0f84', False, 4),
    ('take', '448b406c'),
    ('take', '488b8c24a0000000'),
    ('take', '488b4940'),
    ('take', '4585c0'),
    ('branch', '79', False, 1),
    ('take', '448b4068'),
    ('take', '4885c9'),
    ('branch', '0f84', False, 4),
    ('take', '443b6918'),
    ('branch', '0f83', False, 4),
    ('take', '488b5110'),
    ('take', '4885d2'),
    ('branch', '0f84', False, 4),
    ('take', '443b6a18'),
    ('branch', '0f83', False, 4),
    ('take', '468944aa20'),
    ('take', 'ff411c'),
    ('cell', 'site577', '4c8d2d', ''),
    ('take', '4533f6'),
    ('jump', 'e9', 4),
    ('take', '488b4770'),
    ('take', '4885c0'),
    ('branch', '0f84', False, 4),
    ('take', '4c8b7878'),
    ('take', '0f1f840000000000'),
    ('take', '418bf6'),
    ('take', '4d85ff'),
    ('branch', '0f84', False, 4),
    ('take', '413b7718'),
    ('branch', '0f8d', True, 4),
    ('take', '488b4770'),
    ('take', '4885c0'),
    ('branch', '0f84', False, 4),
    ('take', '4c8bb080000000'),
    ('cell', 'site971', '488b35', ''),
    ('take', '48837e3800'),
    ('branch', '75', True, 1),
    ('take', '4d85f6'),
    ('branch', '0f84', True, 4),
    ('take', '488b4770'),
    ('take', '4885c0'),
    ('branch', '0f84', False, 4),
    ('take', '80786500'),
    ('branch', '0f85', False, 4),
    ('take', 'f30f104778'),
    ('take', '410f2fc0'),
    ('branch', '72', False, 1),
    ('take', '0fb64874'),
    ('take', '884f7c'),
    ('take', '4885c0'),
    ('branch', '0f84', False, 4),
    ('take', '0fb64075'),
    ('take', '88477d'),
    ('take', '488b8424b8000000'),
    ('take', 'f30f10406c'),
    ('take', '84c9'),
    ('branch', '75', False, 1),
    ('take', '488b4770'),
    ('take', '4885c0'),
    ('branch', '0f84', False, 4),
    ('take', 'f30f584070'),
    ('take', 'f30f114778'),
    ('take', '33d2'),
    ('take', '488bcf'),
    ('call', 'timerAfter'),
    ('take', '84c0'),
    ('cell', 'site1051', '4c8d25', ''),
    ('take', '41bf00000000'),
    ('branch', '0f84', False, 4),
    ('jump', 'eb', 1),
    ('take', 'c6878000000000'),
    ('take', 'f30f587f6c'),
    ('take', 'f30f117f6c'),
    ('cell', 'site1091', '488b15', ''),
    ('take', '488bcb'),
    ('call', 'scopeDispose'),
    ('jump', 'e9', 4),
    ('take', '4c8d9c2460010000'),
    ('take', '410f2873f0'),
    ('take', '410f287be0'),
    ('take', '450f2843d0'),
    ('take', '498be3'),
    ('take', '415f'),
    ('take', '415e'),
    ('take', '415d'),
    ('take', '415c'),
    ('take', '5f'),
    ('take', '5e'),
    ('take', '5b'),
    ('take', 'c3'),
)


_ITERATION_FIND_STEPS = (
    ('take', '48895c2410'),
    ('take', '48896c2418'),
    ('take', '4889742420'),
    ('take', '57'),
    ('take', '4154'),
    ('take', '4155'),
    ('take', '4156'),
    ('take', '4157'),
    ('take', '4883ec30'),
    ('take', '4d8be8'),
    ('take', '448bf2'),
    ('take', '488b7910'),
    ('take', 'bbffffffff'),
    ('take', '488b7118'),
    ('take', '4885ff'),
    ('branch', '0f84', False, 4),
    ('take', '488b6930'),
    ('take', '4885ed'),
    ('branch', '0f85', False, 4),
    ('take', '8bea'),
    ('take', '0fbaf51f'),
    ('take', '8bc5'),
    ('take', '99'),
    ('take', 'f77f18'),
    ('take', '3b5718'),
    ('branch', '0f83', False, 4),
    ('take', '660f1f440000'),
    ('take', '4863da'),
    ('take', '4533ff'),
    ('take', '8b5c9f20'),
    ('take', 'ffcb'),
    ('take', '4885f6'),
    ('branch', '0f84', False, 4),
    ('take', '3b5e18'),
    ('branch', '73', True, 1),
    ('take', '488b6c2470'),
    ('take', '8bc3'),
    ('take', '488b5c2468'),
    ('take', '488b742478'),
    ('take', '4883c430'),
    ('take', '415f'),
    ('take', '415e'),
    ('take', '415d'),
    ('take', '415c'),
    ('take', '5f'),
    ('take', 'c3'),
)

_ITERATION_INSERT_STEPS = (
    ('take', '44884c2420'),
    ('take', '4489442418'),
    ('take', '53'),
    ('take', '55'),
    ('take', '56'),
    ('take', '57'),
    ('take', '4154'),
    ('take', '4155'),
    ('take', '4883ec38'),
    ('take', '418bf8'),
    ('take', '448bea'),
    ('take', '488bd9'),
    ('take', 'ff412c'),
    ('take', '4883791000'),
    ('branch', '0f84', False, 4),
    ('take', '4c8b6330'),
    ('take', '488b7318'),
    ('take', '4d85e4'),
    ('branch', '0f85', False, 4),
    ('take', '418bed'),
    ('take', '4c8b4310'),
    ('take', '0fbaf51f'),
    ('take', '4c89742478'),
    ('take', '4c897c2430'),
    ('take', '4d85c0'),
    ('branch', '0f84', False, 4),
    ('take', '4183781803'),
    ('branch', '0f85', True, 4),
    ('take', '8bc5'),
    ('take', '99'),
    ('take', '41f77818'),
    ('jump', 'e9', 4),
    ('take', '413b5018'),
    ('branch', '0f83', False, 4),
    ('take', '4c63fa'),
    ('take', '4983c708'),
    ('take', '478b34b8'),
    ('take', '4f8d3cb8'),
    ('take', '41ffce'),
    ('take', '4d85e4'),
    ('branch', '0f85', False, 4),
    ('take', '33c9'),
    ('take', '894c2470'),
    ('take', '4885f6'),
    ('branch', '0f84', False, 4),
    ('take', '443b7618'),
    ('branch', '0f82', False, 4),
    ('take', '32c9'),
    ('take', '4532f6'),
    ('take', '837b2800'),
    ('branch', '0f8f', False, 4),
    ('take', '8b7b20'),
    ('take', '3b7e18'),
    ('branch', '0f84', False, 4),
    ('take', '488b7318'),
    ('take', '8d4701'),
    ('take', '894320'),
    ('take', '84c9'),
    ('branch', '0f85', False, 4),
    ('take', '4885f6'),
    ('branch', '0f84', False, 4),
    ('take', '3b7e18'),
    ('branch', '0f83', False, 4),
    ('take', '4863cf'),
    ('take', '4883c102'),
    ('take', '48c1e104'),
    ('take', '4803ce'),
    ('take', '4584f6'),
    ('branch', '75', False, 1),
    ('take', '8b942480000000'),
    ('take', '8929'),
    ('take', '418b07'),
    ('take', 'ffc8'),
    ('take', '44896908'),
    ('take', '894104'),
    ('take', '8d4701'),
    ('take', '89510c'),
    ('take', '418907'),
    ('take', 'b001'),
    ('take', '4c8b7c2430'),
    ('take', '4c8b742478'),
    ('take', '4883c438'),
    ('take', '415d'),
    ('take', '415c'),
    ('take', '5f'),
    ('take', '5e'),
    ('take', '5d'),
    ('take', '5b'),
    ('take', 'c3'),
)

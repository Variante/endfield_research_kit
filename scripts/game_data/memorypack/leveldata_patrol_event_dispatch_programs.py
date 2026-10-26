"""Event listener iteration, filters and actual action request transfers."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def listener_loop(regions,entry,s,*,mode='delegate'):
    modes={'exhausted','free','invalid','null','other-kind','no-delegate','delegate','invalid-trigger','null-trigger','inactive-trigger','script'}
    if mode not in modes:raise ValueError('eventListener.mode')
    g=BytesPath(regions,entry);usages={}
    def use(role,prefix):
        at=g.at;cell=g.relative(prefix);usages[role]=dict(instructionVa=at,cellVa=cell)
    g.take('488b542468','4885d2');g.branch('0f84',False)
    g.take('8b422c','39442474');g.branch('0f85',False)
    g.take('8b4c2470','90');inner=g.at
    g.take('4885d2');g.branch('0f84',False)
    g.take('3b4a20');g.branch('0f83',mode=='exhausted')
    if mode=='exhausted':
        g.take('8b4220','ffc0','89442470','0f57c0','0f11442478');g.jump('eb',1)
        return dict(selectedBytes=g.seen,mode=mode,typedUsageSites=usages,continuationVa=g.at,returnedBool=False)
    g.take('4c8b4218','4c63c9','ffc1','894c2470','4d85c0');g.branch('0f84',False)
    g.take('453b4818');g.branch('0f83',False)
    g.take('498d4101','48c1e005','42833c0000');g.branch('7c',mode=='free',1)
    if mode=='free':
        if g.at!=inner:raise ValueError('eventListener.free-backedge')
        return dict(selectedBytes=g.seen,mode=mode,typedUsageSites=usages,continuationVa=g.at,enumerationIndexStep=1)
    g.take('498bc1','48c1e005','420f10440030','0f11442478','488d4c2478');g.call(s['barrier'])
    g.take('0f10442478','0f11442428');use('listenerLock','488b05')
    g.take('488b4020','f6803801000001');g.branch('75',True,1)
    g.take('488b90c0000000','488b5208','488d4c2428');g.call(s['valid'])
    g.take('84c0');g.branch('0f84',mode=='invalid')
    if mode=='invalid':return dict(selectedBytes=g.seen,mode=mode,typedUsageSites=usages,continuationVa=g.at)
    g.take('488b442428','4885c0');g.branch('0f84',mode=='null')
    if mode=='null':return dict(selectedBytes=g.seen,mode=mode,typedUsageSites=usages,continuationVa=g.at)
    script=mode in('invalid-trigger','null-trigger','inactive-trigger','script')
    g.take('83781800');g.branch('74',script,1)
    if not script:
        g.take('83781801');g.branch('0f85',mode=='other-kind')
        if mode=='other-kind':return dict(selectedBytes=g.seen,mode=mode,typedUsageSites=usages,continuationVa=g.at)
        g.take('4883783800');g.branch('0f84',mode=='no-delegate')
        if mode=='no-delegate':return dict(selectedBytes=g.seen,mode=mode,typedUsageSites=usages,continuationVa=g.at)
        g.jump('eb',1)
    else:
        g.take('0f104028','0f11442438');use('triggerLock','488b05')
        g.take('488b4020','f6803801000001');g.branch('75',True,1)
        g.take('488b90c0000000','488b5208','488d4c2438');g.call(s['valid'])
        g.take('84c0');g.branch('0f84',mode=='invalid-trigger')
        if mode=='invalid-trigger':return dict(selectedBytes=g.seen,mode=mode,typedUsageSites=usages,continuationVa=g.at)
        g.take('488b442438','4885c0');g.branch('0f84',mode=='null-trigger')
        if mode=='null-trigger':return dict(selectedBytes=g.seen,mode=mode,typedUsageSites=usages,continuationVa=g.at)
        g.take('80b89000000000');g.branch('0f84',mode=='inactive-trigger')
        if mode=='inactive-trigger':return dict(selectedBytes=g.seen,mode=mode,typedUsageSites=usages,continuationVa=g.at)
    g.take('b001');g.jump('eb',1)
    return dict(selectedBytes=g.seen,mode=mode,typedUsageSites=usages,continuationVa=g.at,returnedBool=True)


def listener_return(regions,entry,*,false=False):
    g=BytesPath(regions,entry)
    if false:g.take('32c0')
    g.take('4c8d9c2490000000','498b5b10','498b7318','498b7b20','498be3','415e','c3')
    return dict(selectedBytes=g.seen,entryRspRestored=True,frameBytes=152,restoredNonvolatiles=['rbx','rsi','rdi','r14'])





def trigger_loop(regions,entry,s,*,mode='delegate',filter_present=True):
    modes={'exhausted','invalid','null','other-kind','no-action','predicate-false','delegate',
        'invalid-trigger','null-trigger','inactive-trigger','event-mismatch','missing-action','script'}
    if mode not in modes or type(filter_present)is not bool:raise ValueError('eventTrigger.mode')
    g=BytesPath(regions,entry);usages={};calls=[]
    def use(role,prefix):
        at=g.at;cell=g.relative(prefix);usages[role]=dict(instructionVa=at,cellVa=cell);return cell
    def call(role):
        at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target))
        if role in s and target!=s[role]:raise ValueError('eventTrigger.target:'+role)
    def done(**kw):return dict(selectedBytes=g.seen,mode=mode,filterPresent=filter_present,
        typedUsageSites=usages,actualCalls=calls,continuationVa=g.at,**kw)
    def next_index():
        g.take('41ffc7','488b442458','8b4c2460');g.jump('e9')
        if g.at!=entry:raise ValueError('eventTrigger.loop-backedge')
    g.take('443bf9');g.branch('0f8d',mode=='exhausted')
    if mode=='exhausted':return done()
    g.take('4885c0');g.branch('0f84',False)
    g.take('443b7818');g.branch('0f83',False)
    g.take('488b4810','4885c9');g.branch('0f84',False)
    g.take('443b7918');g.branch('0f83',False)
    g.take('4963c7','4883c002','4803c0','0f1004c1','0f11842488000000');use('listenerLock','488b05')
    g.take('488b4020','f6803801000001');g.branch('75',True,1)
    g.take('488b90c0000000','488b5208','488d8c2488000000');call('valid')
    g.take('84c0');g.branch('74',mode=='invalid',1)
    if mode=='invalid':next_index();return done()
    g.take('488bbc2488000000','4885ff');g.branch('74',mode=='null',1)
    if mode=='null':next_index();return done()
    script=mode in('invalid-trigger','null-trigger','inactive-trigger','event-mismatch','missing-action','script')
    g.take('837f1800');g.branch('74',script,1)
    if not script:
        g.take('837f1801');g.branch('75',mode=='other-kind',1)
        if mode=='other-kind':next_index();return done()
        g.take('48837f4000');g.branch('74',not filter_present,1)
        if filter_present:
            g.take('488b4f40','488b4118','4c8b4128','498bd4','488b4940','ffd0','84c0')
            g.branch('74',mode=='predicate-false',1)
            if mode=='predicate-false':next_index();return done(predicateCall=True,actionCall=False)
        g.take('48837f3800');g.branch('74',mode=='no-action',1)
        if mode!='no-action':g.take('498bd4','488b4f38');call('action')
        next_index();return done(predicateCall=filter_present,actionCall=mode!='no-action',
            predicateArguments=dict(rcx='same filter delegate target',rdx='same incoming EventParams',r8='same delegate MethodInfo'),
            actionArguments=dict(rcx='same listener Action<EventParams> reference',rdx='same incoming EventParams'))
    g.take('0f104728','0f11842498000000');use('triggerLock','488b05')
    g.take('488b4020','f6803801000001');g.branch('75',True,1)
    g.take('488b90c0000000','488b5208','488d8c2498000000');call('valid')
    g.take('84c0');g.branch('74',mode=='invalid-trigger',1)
    if mode=='invalid-trigger':next_index();return done()
    g.take('488bbc2498000000','4885ff');g.branch('74',mode=='null-trigger',1)
    if mode=='null-trigger':next_index();return done()
    replacement=g.relative('488b05');g.take('488b4830','4885c9');g.branch('74',True,1)
    g.take('80bf9000000000');g.branch('0f84',mode=='inactive-trigger')
    if mode=='inactive-trigger':next_index();return done()
    g.take('4885c9');g.branch('74',True,1)
    g.take('488b9798000000','4885d2');g.branch('0f84',False)
    g.take('b90f000000');call('eventType')
    g.take('413bc5','0f94c0','84c0');g.branch('0f84',mode=='event-mismatch')
    if mode=='event-mismatch':next_index();return done(replacementRootCellVa=replacement)
    cls=use('gameInstanceClass','488b05');g.take('83b8e000000000');g.branch('75',True,1)
    g.take('488b80b8000000','4c8b7028','488b8798000000','4885c0');g.branch('0f84',False)
    g.take('48637010','4d85f6');g.branch('0f84',False)
    if g.relative('488b05')!=replacement:raise ValueError('eventTrigger.same-replacement-root')
    g.take('488b4828','4885c9');g.branch('74',True,1)
    g.take('48c744245000000000','4885c9');g.branch('74',True,1)
    g.take('0f104720','0f118424a8000000');use('contextLock','488b05')
    g.take('488b4020','f6803801000001');g.branch('75',True,1)
    g.take('488b90c0000000','488b5208','488d8c24a8000000');call('valid')
    g.take('0fb6c8','33c0','84c9','480f458424a8000000','4885c0');g.branch('0f84',False)
    g.take('488b4870','4885c9');g.branch('0f84',False)
    if g.relative('488b05')!=replacement:raise ValueError('eventTrigger.same-context-replacement-root')
    g.take('4c8b5028','4d85d2');g.branch('74',True,1)
    g.take('4883792000');g.branch('0f84',False)
    g.take('488b4120','397018');g.branch('0f8e',False)
    g.take('85f6');g.branch('0f88',False)
    g.take('3b7018');g.branch('0f83',False)
    g.take('488b4cf020','48894c2450');barrier=g.relative('833d')+1;g.take('00');g.branch('74',True,1)
    g.take('4885c9');g.branch('0f84',mode=='missing-action')
    if mode=='missing-action':next_index();return done(replacementRootCellVa=replacement,barrierFlagVa=barrier)
    g.take('897718','33f6','4889b788000000')
    if g.relative('3935')!=barrier:raise ValueError('eventTrigger.same-disabled-barrier')
    g.branch('74',True,1)
    g.take('4088777e','4889742420','4533c9','4d8bc4','488bd7','498bce');call('invokeExecutor')
    g.jump('e9')
    next_index()
    return done(replacementRootCellVa=replacement,barrierFlagVa=barrier,
        startNodeIdFromHeaderOffset=16,actionMapOwnerContextOffset=112,nodeArrayFieldOffset=32,
        executorStateWrites=[dict(offset=24,width=4,value='same selected header start-node Int32'),dict(offset=136,width=8,value=0),dict(offset=126,width=1,value=0)],
        executorArguments=dict(rcx='same GameInstance static field40 ActionExecutorManager',rdx='same selected EventActionTrigger',r8='same incoming EventParams',r9d=0,stackArgument5=0))


def ordinary_action(regions,entry):
    g=BytesPath(regions,entry);g.take('4c89442418','53','56','57','4883ec30','488b4118','488bfa','488b7128','488b5940')
    excluded=[g.relative('488d0d')];g.take('483bc1');g.branch('75',True,1)
    excluded.append(g.relative('488d0d'));g.take('48896c2458','483bc1');g.branch('74',False,1)
    excluded.append(g.relative('488d0d'));g.take('483bc1');g.branch('0f84',False)
    g.take('4c8bc6','488bcb','ffd0','488b6c2458');g.jump('eb',1)
    g.take('4883c430','5f','5e','5b','c3')
    return dict(selectedBytes=g.seen,excludedInlineTargets=excluded,invokePointerOffset=24,methodInfoOffset=40,targetOffset=64,
        arguments=dict(rcx='same delegate target',rdx='same incoming EventParams',r8='same delegate MethodInfo'),
        entryRspRestored=True,frameBytes=72,restoredNonvolatiles=['rbx','rbp','rsi','rdi'],
        condition='Compatible stable delegate whose invoke pointer differs from the three explicit optimized targets; selected callback returns normally with ordinary Win64 ABI. Its identity and effects remain dynamic.')


def uint_slot(regions,entry,*,slot,callback):
    if type(slot)is not int or not 0<=slot<65536:raise ValueError('eventUIntSlot.selector')
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','0fb7d9','488bfa','488b0a')
    prepare=g.relative('e8')
    g.take('488d4b14','48c1e104','48030f','488b01','488b5108');excluded=[]
    for _ in range(3):
        target=g.relative('488d0d');excluded.append(target)
        if target==callback:raise ValueError('eventUIntSlot.callback-enters-independent-inline-program')
        g.take('483bc1');g.branch('74',False,1)
    g.take('488bcf','ffd0','488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,slot=slot,prepareTargetVa=prepare,
        callbackRequiredVa=callback,excludedInlineTargets=excluded,
        vtableBase=320,slotStride=16,callbackOffset=320+16*slot,methodInfoOffset=328+16*slot,
        arguments=dict(rcx='same incoming RDX header reference',rdx='same selected slot MethodInfo'),
        result='unchanged selected callback UInt32 bits',frameBytes=40,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rdi'],
        condition='Incoming low16 selector equals the selected slot; compatible nonnull current header/class and exact slot callback/MethodInfo pair; normal preparation ABI and stable disjoint storage. Source bytes do not observe the live callback pair.')


def level_header_enum(regions,entry,*,dispatch_target):
    g=BytesPath(regions,entry);g.take('4883ec28');root=g.relative('488b05')
    g.take('4c8bc2','488bd1','488b4830','4885c9');g.branch('0f85',False)
    g.take('b91a000000','4883c428')
    if g.relative('e9')!=dispatch_target:raise ValueError('eventLevelHeader.same-UInt32-dispatcher')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,selectedNullReplacementRootFieldOffset=48,
        selectedSlot=26,headerReferenceUnchanged=True,entryRspRestored=True,frameBytes=40,
        tailArguments=dict(ecx=26,rdx='same incoming header reference'),returnedUInt32BitsUnchanged=True)


def checkpoint_header_key(regions,entry):
    g=BytesPath(regions,entry);g.take('4883ec28');root=g.relative('488b05')
    g.take('4c8bc9','488b4830','4885c9');g.branch('74',True,1)
    g.take('b8');value=int.from_bytes(g.read(4),'little');g.take('4883c428','c3')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,selectedNullReplacementRootFieldOffset=48,
        returnedUInt32=value,frameBytes=40,entryRspRestored=True,nonframeWrites=0,
        condition='Exact nominal OnNpcPatrolCheckpointReach getter with its selected replacement receiver absent; actual listener/header selection remains a runtime condition.')


def invoke_executor(regions,entry,*,invoked=False,removed=False,delayed=False,next_frame=False):
    if any(type(v)is not bool for v in(invoked,removed,delayed,next_frame))or removed and not invoked:
        raise ValueError('eventInvokeExecutor.mode')
    g=BytesPath(regions,entry);calls={};usages={}
    def call(role):
        at=g.at;target=g.relative('e8');calls[role]=dict(instructionVa=at,targetVa=target);return target
    def use(role,prefix):
        at=g.at;cell=g.relative(prefix);usages[role]=dict(instructionVa=at,cellVa=cell)
    g.take('48895c2408','4889742410','57','4883ec50');root=g.relative('488b05')
    g.take('488bf9','450fb6d1','4d8bd8','488bda','488b4828','4885c9');g.branch('0f85',False)
    g.take('c644243000','4885db');g.branch('0f84',False)
    g.take('4c8d4c2430','48c744242000000000','450fb6c2','498bd3','488bcb');call('tryToInvoke')
    g.take('84c0');g.branch('75',invoked,1)
    if invoked:
        g.take('33d2','488bcb');call('onInvoked')
        g.take('807b6900');g.branch('74',not removed,1)
        if removed:
            g.take('33d2','488bcb');call('removeInvoked')
            g.take('488b5c2460','33c0','488b742468','4883c450','5f','c3')
            return dict(selectedBytes=g.seen,actualCalls=calls,typedUsageSites=usages,returnedReference=None,
                replacementRootCellVa=root,invoked=invoked,removed=removed,delayed=delayed,nextFrame=next_frame,
                entryRspRestored=True,frameBytes=88,restoredNonvolatiles=['rbx','rsi','rdi'],
                invocationEffectsProved=False)
    g.take('807c243000');g.branch('0f85',delayed)
    queue_field=144
    if delayed:
        use('logicFrameClass','488b0d');g.take('83b9e000000000');g.branch('75',True,1)
        call('logicFrame');g.take('488d4c2440');use('objectPtrImplicit','4c8b05')
        g.take('488bd3','3b4770');g.branch('7f',next_frame,1)
        if next_frame:
            queue_field=136;g.take('488bbf88000000');call('objectPtrImplicit')
            g.take('4885ff');g.branch('0f84',False);g.jump('e9')
        else:
            queue_field=128;g.take('488bbf80000000');call('objectPtrImplicit')
            g.take('4885ff');g.branch('0f84',False);g.jump('e9')
    else:
        use('objectPtrImplicit','4c8b05');g.take('488d4c2440','488bbf90000000','488bd3');call('objectPtrImplicit')
        g.take('4885ff');g.branch('74',False,1)
    g.take('0f28442440','488d542440');use('listAdd','4c8b05')
    g.take('488bcf','660f7f442440');call('listAdd')
    g.take('488bc3','488b5c2460','488b742468','4883c450','5f','c3')
    return dict(selectedBytes=g.seen,actualCalls=calls,typedUsageSites=usages,
        replacementRootCellVa=root,invoked=invoked,removed=removed,delayed=delayed,nextFrame=next_frame,
        tryArguments=dict(rcx='same selected ActionExecutor',rdx='same incoming EventParams',r8d='same incoming wait Bool',r9='disjoint local out delay Bool',stackArgument5=0),
        queueFieldOffset=queue_field,queuedValue='same complete ObjectPtr<ActionExecutor>16 result',
        returnedReference='unchanged incoming ActionExecutor',entryRspRestored=True,frameBytes=88,
        restoredNonvolatiles=['rbx','rsi','rdi'],invocationEffectsProved=False,
        condition='Absent replacement; compatible manager/executor/EventParams and ordinary helper ABI; actual TryToInvoke/output-delay/removal state and frame comparison match the selected witnesses. Exact independent ObjectPtr/List semantics and live queue/activation remain separate.')

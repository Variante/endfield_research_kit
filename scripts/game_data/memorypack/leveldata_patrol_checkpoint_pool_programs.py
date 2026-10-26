"""Selected typed ParamVariable pool/reset source programs for checkpoints."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag


def need(check,condition):
    if not condition:raise ValueError('patrolCheckpointPool.'+check)


def base_reset_program(regions,entry):
    g=BytesPath(regions,entry);g.take('4053','4883ec20');root=g.relative('488b05')
    g.take('488bd9','488b4810','4885c9');g.branch('74',True,1)
    g.take('488b4878','4885c9');g.branch('74',True,1)
    serial_class=g.relative('488b15');g.take('83bae000000000');g.branch('75',True,1)
    ready=flag(g);g.branch('75',True,1)
    g.take('83bae000000000');g.branch('75',True,1)
    g.take('488b82b8000000','8b08','ffc1','8908','894b10')
    need('same-reset-replacement-root',g.relative('488b05')==root)
    g.take('488b4810','4885c9');g.branch('74',True,1)
    collector=g.relative('8b05');table=g.relative('4c8d15')
    g.take('4533c9','4c894b18','85c0');g.branch('74',True,1)
    g.take('4c894b20','44894b30','4c894b28','85c0');g.branch('74',True,1)
    g.take('4c898b88000000','85c0');g.branch('74',True,1)
    g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,
        requiredAbsentReplacementReceiverOffsets=[16,120],metadataReadyFlagVa=ready,
        serialCounterClassCellVa=serial_class,serialClassInitializedOffset=224,
        staticFieldsOffset=184,serialStaticFieldOffset=0,serialBytes=4,
        serialIncrementModulo2Pow32=1,storedSerialFieldOffset=16,
        zeroedReferenceOffsets=[24,40,136],zeroedScalarSpans=[[32,40],[48,52]],
        observerCounterFieldOffset=48,observerCounterSetZero=True,bothObserverReferencesSetNull=True,
        keySetNull=True,collectorDisabledFlagVa=collector,unusedCollectorTableVa=table,
        entryRspRestored=True,restoredNonvolatiles=['rbx'],calls=0,runtimeStateObserved=False)


def typed_reset_program(regions,entry,*,kind,base_reset):
    need('finite-reset-kind',kind in('int','UnityEngine.Vector3','Beyond.Gameplay.Core.EntityPtr'))
    g=BytesPath(regions,entry);g.take('4053','4883ec20','488bd9','4885c9');g.branch('74',False,1)
    g.take('33d2');g.call(base_reset)
    if kind=='int':g.take('33c0','898390000000')
    elif kind=='UnityEngine.Vector3':g.take('33c0','48898390000000','898398000000')
    else:g.take('0f57c0','33c0','0f118390000000','0f1183a0000000','488983b0000000')
    g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,kind=kind,baseReceiverUnchanged=True,baseMethodInfoArgumentZero=True,
        valueFieldOffset=144,wholeValueBytes=4 if kind=='int'else 12 if kind=='UnityEngine.Vector3'else 40,
        wholeValueSetZero=True,entryRspRestored=True,restoredNonvolatiles=['rbx'],
        baseResetEffectsRequired=True,runtimeCallbackSelectionObserved=False)


def reset_invoker_program(regions,entry,*,prepare,callback):
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec40','0fb7d9','488bfa','488b0a','0f29742430');g.call(prepare)
    g.take('488b07','488d4b14','4803c9','4c8b04c8','488b54c808');excluded=[]
    for opcode,width in(('74',1),('74',1),('0f84',4)):
        excluded.append(g.relative('488d05'));g.take('4c3bc0');g.branch(opcode,False,width)
    need('own-OnAllocate-outside-inline-alternatives',type(callback)is int and callback>0 and callback not in excluded)
    g.take('488bcf','41ffd0');g.jump('eb',1)
    g.take('488b5c2450','488b742458','0f28742430','4883c440','5f','c3')
    return dict(selectedBytes=g.seen,slot=7,callbackByteOffset=432,methodInfoByteOffset=440,
        selectedCallbackRequired=callback,excludedInlineCallbacks=excluded,
        sameIncomingReceiverPassed=True,selectedMethodInfoPassed=True,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rsi','rdi','xmm6'],xmmSaveRestoreBytes=16,runtimeSelectionObserved=False)


def singleton_program(regions,entry,*,context_type,type_from_context):
    g=BytesPath(regions,entry);g.take('4053','4883ec20','488bd9','488b4920');g.call(context_type)
    g.take('33d2','488b88c0000000');g.call(type_from_context)
    g.take('488b88b8000000','48833900');g.branch('74',False,1)
    g.take('488b4b20');g.call(context_type)
    g.take('33d2','488b88c0000000');g.call(type_from_context)
    g.take('488b80b8000000','488b00','4883c420','5b','c3')
    return dict(selectedBytes=g.seen,contextSlot=0,staticFieldsOffset=184,staticFieldOffset=0,
        existingSingletonRequiredNonnull=True,sameSingletonReturned=True,memoryWrites=0,
        entryRspRestored=True,restoredNonvolatiles=['rbx'],coldSingletonConstructionProved=False)


def stack_pop_program(regions,entry):
    g=BytesPath(regions,entry)
    g.take('48895c2410','48896c2418','56','57','4156','4883ec20','48636918',
        '488bf2','488b5910','488bf9','448d75ff','4885db');g.branch('0f84',False)
    g.take('443b7318');g.branch('0f83',False)
    g.take('ff411c','4c8d4dff','44897118','443b4b18');g.branch('0f83',False)
    g.take('4e8b4ccb20','488d45ff','3b4318');g.branch('0f83',False)
    collector=flag(g,'833d');g.take('48c744c32000000000');g.branch('74',True,1)
    g.take('488b5c2448','498bc1','488b6c2450','4883c420','415e','5f','5e','c3')
    return dict(selectedBytes=g.seen,stackArrayFieldOffset=16,stackCountFieldOffset=24,
        stackVersionFieldOffset=28,versionIncrementModulo2Pow32=1,countDecrement=1,
        arrayLengthOffset=24,arrayDataOffset=32,elementBytes=8,
        returnedReference='unchanged prior element at old count minus1',poppedCellSetNull=True,
        positiveCountAndValidStorageRequired=True,collectorDisabledFlagVa=collector,
        entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','r14'])


def allocate_program(regions,entry,*,context_type,type_from_context,singleton,pop,
                     reset_invoke,object_new,reuse):
    need('literal-pool-reuse-selection',type(reuse)is bool)
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','488bda','84c9');g.branch('0f84',False)
    g.take('488b4a20');g.call(context_type)
    g.take('488b88c0000000','488b4948');g.call(singleton)
    g.take('4885c0');g.branch('0f84',False)
    g.take('488b7810','4885ff');g.branch('0f84',False)
    g.take('488b4b20');g.call(context_type)
    g.take('488b88c0000000','488b4150','4883782000');g.branch('0f84',False)
    g.take('488b4b20');g.call(context_type)
    g.take('837f1800');g.branch('0f8e',not reuse)
    if reuse:
        g.take('488b4b20');g.call(context_type)
        g.take('488b88c0000000','488b4948');g.call(singleton)
        g.take('4885c0');g.branch('0f84',False)
        g.take('488b7810','4885ff');g.branch('0f84',False)
        g.take('488b4b20');g.call(context_type)
        g.take('488b88c0000000','488b4158','4883782000');g.branch('0f84',False)
        g.take('488b4b20');g.call(context_type)
        g.take('488bcf','488b90c0000000','488b5258');g.call(pop)
        g.take('488bf8','4885c0');g.branch('0f84',False)
    else:
        g.take('488b4b20');g.call(context_type)
        g.take('ba0c000000','488b88c0000000');g.call(type_from_context)
        g.take('488bc8');g.call(object_new)
        g.take('488bf8','4885c0');g.branch('74',False,1)
        g.take('488b4b20');g.call(context_type)
        g.take('488b88c0000000','488b4168','4883782000');g.branch('0f84',False)
        g.take('488b4b20');g.call(context_type);g.jump('e9')
    g.take('b907000000','488bd7');g.call(reset_invoke)
    g.take('488b4b20');g.call(context_type)
    g.take('488b88c0000000','488b4948');g.call(singleton)
    g.take('4885c0');g.branch('0f84',False)
    g.take('8b4818','894f20','488b4b20');g.call(context_type)
    g.take('488b88c0000000','488b4948');g.call(singleton)
    g.take('4885c0');g.branch('74',False,1)
    g.take('8b481c','488bc7','488b5c2430','894f24','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,reuseAllowed=True,reusedStackElement=reuse,
        poolStackFieldOffset=16,positiveStackCountRequired=reuse,
        ownClassContextSlots=dict(singleton=9,count=10,pop=11,newClass=12,constructor=13),
        stackPopOutputUnchanged=reuse,newClassPassedToActualAllocator=not reuse,
        ownCtorReadyGate=not reuse,constructorBodyInlineEffectRequired=not reuse,
        resetSelector=7,sameSelectedReferencePassedToReset=True,
        poolSourceDwordOffsets=[24,28],resultDwordOffsets=[32,36],
        returnsSameResetReference=True,entryRspRestored=True,restoredNonvolatiles=['rbx','rdi'],
        actualRuntimePoolOrMethodInfoObserved=False,actualObjectAllocationOrCapacityProved=False)

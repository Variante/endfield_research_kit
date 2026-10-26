"""Selected actual object payload initialization and Event constructors."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag


def need(check,condition):
    if not condition:raise ValueError('patrolEventInitialization.'+check)


def object_new_program(regions,entry,*,ready,allocate,fill,class_init,instance_bytes,generic_class=False):
    need('finite-aligned-instance-extent',type(instance_bytes)is int and 24<=instance_bytes<=256 and instance_bytes%8==0)
    need('literal-generic-class-presence',type(generic_class)is bool)
    g=BytesPath(regions,entry);g.take('4053','57','4883ec58','488bf9');g.call(ready)
    g.take('48837f6000');g.branch('74',not generic_class,1)
    if generic_class:g.take('f6873801000008');g.branch('74',True,1)
    g.take('f6873801000020');g.branch('0f85',False)
    g.take('8b8ff8000000');g.call(allocate)
    g.take('33c9','488bd8','488938','4c8d4810','48894808','81bff800000080000000','448b87f8000000')
    g.branch('73',instance_bytes>=128,1)
    if instance_bytes<128:
        g.take('4903c0','4c8bc0','4d2bc1','4983c007','49c1e803','4c3bc8','4c0f47c1','4d85c0');g.branch('74',False,1)
        g.take('49c1e003','33d2','498bc9');g.call(fill)
    else:g.take('4983c0f0','33d2','498bc9');g.call(fill)
    counter=g.relative('f048ff05');g.jump('e9')
    g.take('f6873901000002');g.branch('74',True,1)
    profiling=g.relative('f605')+1;g.take('80');g.branch('74',True,1)
    g.take('488bcf');g.call(class_init)
    g.take('488bc3','4883c458','5f','5b','c3')
    payload=instance_bytes-16
    need('small-object-rounded-fill-exact-on-aligned-extent',instance_bytes>=128 or ((payload+7)//8)*8==payload)
    return dict(selectedBytes=g.seen,instanceBytes=instance_bytes,actualClassSizeFieldOffset=248,
        genericClassPointerRequiredPresent=generic_class,genericClassPointerOffset=96,
        genericDefinitionRedirectFlagRequiredClear=(dict(offset=312,mask=8)if generic_class else None),
        allocatorClassFlagRequiredClear=dict(offset=312,mask=32),
        finalizerClassFlagRequiredClear=dict(offset=313,mask=2),profilingFlagVa=profiling,profilingMaskRequiredClear=128,
        rawAllocationArgumentBytes=instance_bytes,actualRawAllocationCapacityRequired=True,
        classHeaderOffset=0,monitorHeaderOffset=8,monitorHeaderSetZero=True,
        initializedPayloadSpan=[16,instance_bytes],zeroFillBytes=payload,
        allObjectBytesEstablishedByHeaderAndActualZeroFill=True,allocatorZeroStateAssumed=False,
        allocationCounterCellVa=counter,allocationCounterIncrementModulo2Pow64=1,
        allocationCounterNoninterferenceRequired=True,readyClassInitEffectsRequired=True,
        returnsSameRawAllocatedReference=True,entryRspRestored=True,restoredNonvolatiles=['rbx','rdi'],
        otherClassFlagAllocationBranchesProved=False,runtimeAllocationOrCapacityObserved=False)


def initialized_class_program(regions,entry):
    g=BytesPath(regions,entry)
    g.take('48895c2418','4889742420','55','57','4154','4156','4157','488bec','4883ec70','0f29742460',
        '488bf1','4533f6','44897530','4439b1e0000000');g.branch('0f85',True)
    g.take('4c8d5c2470','498b5b40','498b7348','0f28742460','498be3','415f','415e','415c','5f','5d','c3')
    return dict(selectedBytes=g.seen,classInitializedFieldOffset=224,classInitializedRequiredNonzero=True,
        nonframeWrites=0,calls=0,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r14','r15','xmm6'],xmmSaveRestoreBytes=16)


def dictionary_ctor_program(regions,entry,*,default_comparer):
    g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec20','488b4220','488bda','488bf9','4c8b80c0000000','498b00','4883782000');g.branch('75',True,1)
    g.take('488b4320','488b88c0000000','488b01','488b4820','488b89c0000000','488b4910');g.call(default_comparer)
    g.take('4885c0');g.branch('74',False,1)
    collector=flag(g,'833d');g.take('48c7473000000000');g.branch('74',True,1)
    g.take('488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,constructorReadyContextSlot=0,nestedKeyComparerContextSlot=2,
        selectedDefaultComparerResultRequiredNonNull=True,comparerFieldOffset=48,comparerSetZero=True,
        collectorDisabledFlagVa=collector,otherPayloadFieldsUntouched=True,
        priorPayloadInitializationRequired=True,entryRspRestored=True,restoredNonvolatiles=['rbx','rdi'])


def blackboard_ctor_program(regions,entry,*,object_new,dictionary_ctor,barrier):
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');empty_class=g.relative('488b05')
    g.take('488bd9','488b88b8000000','488b01','488d4b20','48894320');g.call(barrier)
    fields=[]
    for class_prefix,field_address,store in(('488b0d','488d4b28','48897b28'),('488b0d','488d4b30','48897b30')):
        class_site=g.at;class_cell=g.relative(class_prefix);g.call(object_new)
        g.take('488bf8','4885c0');g.branch('74',False,1)
        method_site=g.at;method_cell=g.relative('488b15');g.take('488bc8');g.call(dictionary_ctor)
        g.take(field_address,store)
        fields.append(dict(classSiteVa=class_site,classCellVa=class_cell,
            constructorMethodInfoSiteVa=method_site,constructorMethodInfoCellVa=method_cell))
        if len(fields)==1:g.call(barrier)
    g.take('488b5c2430','4883c420','5f');need('actual-last-field-barrier-tail',g.relative('e9')==barrier)
    return dict(selectedBytes=g.seen,emptyStringClassCellVa=empty_class,emptyStringStaticFieldOffset=0,
        debugContextKeyFieldOffset=32,variableDictionaryFieldOffset=40,subBlackboardDictionaryFieldOffset=48,
        dictionaries=fields,bothActualNewDictionaryReferencesStoredUnchanged=True,
        sameObjectNewClassAndOwnConstructorRequired=True,entryRspRestoredBeforeTail=True,
        restoredNonvolatiles=['rbx','rdi'],otherPayloadStateComesFromActualObjectInitializationRequired=True)


def event_ctor_program(regions,entry,*,base_ctor):
    g=BytesPath(regions,entry);g.take('33d2');need('own-Event-base-constructor-tail',g.relative('e9')==base_ctor)
    return dict(selectedBytes=g.seen,sameIncomingEventReceiverPassed=True,baseConstructorMethodInfoArgumentZero=True,
        entryRspAndNonvolatilesUntouched=True,physicalFunctionExtentProved=False)

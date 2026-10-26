"""Finite selected blackboard and ParamVariable programs used by checkpoints.

These programs authenticate instructions and complete normal-return transfers.
They do not observe live dispatch, replacement tables, dictionary contents or
observer registrations. Calls whose effects need another owner stay explicit.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag

KINDS=('int','UnityEngine.Vector3','Beyond.Gameplay.Core.EntityPtr')


def need(check,condition):
    if not condition:raise ValueError('patrolCheckpointCallees.'+check)


def getter_program(regions,entry,*,kind):
    need('finite-value-kind',kind in KINDS);g=BytesPath(regions,entry)
    if kind=='int':g.take('8b8190000000','c3')
    elif kind=='UnityEngine.Vector3':
        g.take('8b8298000000','f20f108290000000','f20f1101','894108','488bc1','c3')
    else:
        g.take('0f108290000000','488bc1','0f108aa0000000','0f1101',
            'f20f1082b0000000','0f114910','f20f114120','c3')
    return dict(selectedBytes=g.seen,kind=kind,valueFieldOffset=144,
        valueBytes=4 if kind=='int'else 12 if kind=='UnityEngine.Vector3'else 40,
        copyBytes=[4]if kind=='int'else[8,4]if kind=='UnityEngine.Vector3'else[16,16,8],
        valueBitsUnchanged=True,returns='EAX value'if kind=='int'else'same incoming hidden output pointer',
        receiverRegister='rcx'if kind=='int'else'rdx',nonvalueWrites=0,calls=0,
        entryRspAndNonvolatilesUntouched=True,physicalFunctionExtentProved=False,
        runtimeCallbackSelectionObserved=False)


def set_value_program(regions,entry,*,kind):
    """Original, nonnull, no-observer branch of slot-17 SetValue<T>."""
    need('finite-value-kind',kind in KINDS);g=BytesPath(regions,entry)
    integer=kind=='int';vector=kind=='UnityEngine.Vector3';entity=not integer and not vector
    if vector:
        g.take('488bc4','48895810','55','56','57','4154','4155','4156','4157',
            '488d68a1','4881ecb0000000','0f2970b8','0f57c0','0f2978a8','0f57c9',
            '4d8bf8','488bda','488bf9','0f1145c7','0f114dd7','0f1145e7','0f114df7')
    else:
        g.take('48895c2410','55','56','57','4154','4155','4156','4157',
            '488bec'if integer else'488d6c24e0',
            '4883ec70'if integer else'4881ec20010000','0f57c0','0f57c9',
            '4d8be8'if integer else'4d8bf8','8bf2'if integer else'488bfa','488bd9')
        g.take(*(['0f1145c0','0f114dd0','0f1145e0','0f114df0']if integer else
            ['0f11442440','0f114c2450','0f11442460','0f114c2470']))
    g.take('4885c9');g.branch('0f84',False)
    root=g.relative('488b05');g.take('488b4810','4885c9');g.branch('74',True,1)
    g.take('837f3000'if vector else'837b3000',
        '400f9fc7'if integer else'400f9fc6','488b4810','4885c9');g.branch('74',True,1)
    g.take('4883bf8800000000'if vector else'4883bb8800000000',
        '410f97c5'if vector else'410f97c4','410fb6c5'if vector else'410fb6c4')
    if entity:g.take('44886560')
    g.take('400ac7'if integer else'400ac6');g.branch('0f85'if entity else'75',False,4 if entity else 1)
    collector=None
    if integer:g.take('89b390000000','488b9c24b8000000','4883c470')
    elif vector:
        g.take('f20f1003','8b4308','f20f118790000000','898798000000',
            '4c8d9c24b0000000','498b5b48','410f2873f0','410f287be0','498be3')
    else:
        collector=flag(g,'833d')
        g.take('0f1007','0f104f10','0f118390000000','f20f104720',
            '0f118ba0000000','f20f1183b0000000');g.branch('74',True,1)
        g.take('488b9c2468010000','4881c420010000')
    g.take('415f','415e','415d','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,kind=kind,valueFieldOffset=144,
        valueBytes=4 if integer else 12 if vector else 40,
        copyBytes=[4]if integer else[8,4]if vector else[16,16,8],
        exactInputBitsStored=True,replacementRootCellVa=root,replacementContextFieldOffset=16,
        replacementContextRequiredNull=True,observerCounterFieldOffset=48,observerCounterRequiredNonpositive=True,
        secondObserverFieldOffset=136,secondObserverRequiredNull=True,
        collectorDisabledFlagVa=collector,collectorDisabledRequired=entity,
        entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],
        restoredNonvolatileXmm=['xmm6','xmm7']if vector else[],
        xmmSavedEntryRspSpans=[[-72,-56],[-88,-72]]if vector else[],
        frameBytes=168 if integer else 232 if vector else 344,callCount=0,
        runtimeObserverStateObserved=False,otherObserverOrReplacementPathsProved=False,
        opaqueValueTail=[24,40]if entity else None,runtimeReferenceLayoutAdmitted=False)


def try_get_program(regions,entry,*,find,found):
    need('literal-lookup-result',type(found)is bool);g=BytesPath(regions,entry)
    g.take('48895c2408','48896c2418','4889742420','57','4883ec20',
        '498b4120','498bf9','498bd8','488bf2','488be9',
        '4c8b90c0000000','498b82b0000000','4883782000');g.branch('75',True,1)
    g.take('488b4720','488bd6','488bcd','4c8b80c0000000','4d8b80b0000000');g.call(find)
    g.take('4863f0','85c0');g.branch('79',found,1);collector=None
    if found:
        g.take('488b7d18','4885ff');g.branch('74',False,1)
        g.take('3b7718');g.branch('73',False,1);collector=flag(g,'833d')
        g.take('488d0c76','488d04cf','488b44cf30','488903');g.branch('74',True,1)
        g.take('b001')
    else:g.take('33c0','488903');g.jump('eb',1)
    g.take('488b5c2430','488b6c2440','488b742448','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,found=found,findEntryContextSlot=22,
        sameDictionaryAndStringKeyPassed=True,entryStride=24,entryValueOffset=16,
        outputBytes=8,output='unchanged selected entry reference'if found else'zero reference',
        returnedBool=found,collectorDisabledFlagVa=collector,
        entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi'],
        findEntryEffectsRequired=True,runtimeLookupObserved=False)


def get_or_create_program(regions,entry,*,kind,lookup,type_from_context,assignable,
                          found,new_value=None,allocate=None,barrier=None,invoke=None,set_item=None):
    """Compatible hit or miss, with the actual miss-side callees left named."""
    need('finite-get-or-create-mode',kind in KINDS and type(found)is bool)
    g=BytesPath(regions,entry);integer=kind=='int';entity=kind.endswith('EntityPtr')
    if integer:
        g.take('48895c2418','4889742420','57','4883ec20','4983783800','498bd8','488bf2','488bf9')
        g.branch('74',False,1)
        g.take('488b4f28','48c744243000000000','4885c9');g.branch('74',False,1)
    elif entity:
        g.take('48895c2418','4889742420','57','4881ec80000000',
            '4983783800','498bd8','488bfa','488bf1');g.branch('0f84',False)
        g.take('488b4e28','4c89b42498000000','48c784249000000000000000','4885c9');g.branch('0f84',False)
    else:
        g.take('4053','56','57','4883ec30','4983783800','498bd8','488bf2','488bf9');g.branch('0f84',False)
        g.take('488b4f28','48c744245000000000','4885c9');g.branch('0f84',False)
    site=g.at;cell=g.relative('4c8b0d')
    g.take('4c8d842490000000'if entity else'4c8d442430'if integer else'4c8d442450',
        '488bd7'if entity else'488bd6')
    if not entity:g.take('4c89742438'if integer else'4c89742460')
    g.call(lookup);g.take('84c0');g.branch('0f85',found)
    if found:
        g.take('488b4b38','33d2','4c8bb42490000000'if entity else'4c8b742430'if integer else'4c8b742450')
        g.call(type_from_context);g.take('4d85f6');g.branch('0f84',False)
        g.take('498b0e','488bd0');g.call(assignable);g.take('84c0');g.branch('0f84',False)
        g.take('498bc6');g.jump('e9')
    elif integer:
        g.take('488b4338','488b4808','4883792000');g.branch('74',False,1)
        g.take('4c8b4b38','4533c0','488bd6','488bcf','4d8b4908');g.call(new_value)
    elif not entity:
        g.take('488b4338','48896c2458','33ed','48896c2420','488b4808','48396920');g.branch('74',False,1)
        g.take('4c8b4b38','4c8d442420','f20f10442420','488bd6','488bcf',
            'f20f11442420','896c2428','4d8b4908');g.call(new_value)
        g.take('488b6c2458')
    else:
        g.take('33c0','4889442470','488b4338','488b4808','4883792000');g.branch('0f84',False)
        g.take('488b4338','488b5808','48837b3800');g.branch('0f84',False)
        g.take('488b5338','b101','488b12');g.call(allocate)
        g.take('488bd8','4885c0');g.branch('74',False,1)
        g.take('488d4818','48897818');g.call(barrier)
        g.take('0f57c0','4c8d442420','0f29442420','b90f000000','0f29442430',
            '488bd3','f20f10442470','f20f11442440');g.call(invoke)
        g.take('488b4e28','4885c9');g.branch('74',False,1)
        set_site=g.at;set_cell=g.relative('4c8b0d');g.take('4c8bc3','488bd7');g.call(set_item)
        g.take('488bc3')
    if entity:
        g.take('4c8bb42498000000','4c8d9c2480000000','498b5b20','498b7328','498be3','5f','c3')
    elif integer:
        g.take('4c8b742438','488b5c2440','488b742448','4883c420','5f','c3')
    else:g.take('4c8b742460','4883c430','5f','5e','5b','c3')
    return dict(selectedBytes=g.seen,kind=kind,compatibleHit=found,
        lookupContextSiteVa=site,lookupContextCellVa=cell,blackboardTableFieldOffset=40,
        methodContextOffset=56,expectedTypeContextSlot=0,newValueContextSlot=1,
        hitReturnsSameReference=found,missReturnsNewValueResultUnchanged=not found,
        defaultValueBytes=None if found else 4 if integer else 40 if entity else 12,
        defaultValueAllZero=not found,createdKeyFieldOffset=24 if entity and not found else None,
        initializerSlot=15 if entity and not found else None,
        tableSetterContextSiteVa=set_site if entity and not found else None,
        tableSetterContextCellVa=set_cell if entity and not found else None,
        entryRspRestored=True,restoredNonvolatiles=['rbx','rsi','rdi','r14']+(['rbp']if not integer and not entity and not found else[]),
        lookupTypeAssignmentAndCreationEffectsRequired=True,runtimeSelectionObserved=False)


def new_variable_program(regions,entry,*,kind,allocate,barrier,invoke,set_item):
    need('finite-new-variable-kind',kind in('int','UnityEngine.Vector3'))
    integer=kind=='int';frame=32 if integer else 48;g=BytesPath(regions,entry)
    g.take('48895c2408','48896c2410','4889742418','57','4883ec'+bytes((frame,)).hex(),
        '4983793800','498bd9','418bf0'if integer else'498bf0','488bfa','488be9');g.branch('74',False,1)
    g.take('488b5338','b101','488b12');g.call(allocate)
    g.take('488bd8','4885c0');g.branch('74',False,1)
    g.take('488d4818','48897818');g.call(barrier)
    if integer:g.take('b90f000000','448bc6','488bd3')
    else:g.take('f20f1006','4c8d442420','8b4608','b90f000000','488bd3','f20f11442420','89442428')
    g.call(invoke);g.take('488b4d28','4885c9');g.branch('74',False,1)
    site=g.at;cell=g.relative('4c8b0d');g.take('4c8bc3','488bd7');g.call(set_item)
    g.take('488b6c24'+bytes((frame+24,)).hex(),'488bc3','488b5c24'+bytes((frame+16,)).hex(),
        '488b7424'+bytes((frame+32,)).hex(),'4883c4'+bytes((frame,)).hex(),'5f','c3')
    return dict(selectedBytes=g.seen,kind=kind,createdKeyFieldOffset=24,initializerSlot=15,
        initializerValueBytes=4 if integer else 12,initializerCopies=[4]if integer else[8,4],
        allocationAllowsReuse=True,allocationContextSlot=0,tableFieldOffset=40,
        tableSetterContextSiteVa=site,tableSetterContextCellVa=cell,
        returnsSameCreatedReference=True,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi'],calleeEffectsRequired=True)


def set_item_program(regions,entry,*,insert):
    g=BytesPath(regions,entry)
    g.take('48895c2408','48896c2410','4889742418','57','4883ec30',
        '498b4120','498bd9','498bf8','488bf2','488be9','4c8b88c0000000',
        '498b81c0000000','4883782000');g.branch('0f84',False)
    g.take('488b4320','41b101','4c8bc7','488bd6','488b88c0000000',
        '488b81c0000000','488bcd','4889442420');g.call(insert)
    g.take('488b5c2440','488b6c2448','488b742450','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,tryInsertMode=1,sameTableKeyAndReference=True,
        ownClassContextSlot=24,calleeEffectsRequired=True,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi'])


def find_string_program(regions,entry,*,hash_invoke,comparer_getter,equality_invoke,
                        failures=(),found=True,buckets_present=True):
    """Own default string-comparer chain; callback effects are another join."""
    need('finite-string-chain-witness',isinstance(failures,(tuple,list))and len(failures)<=3
        and all(x in('hash','key')for x in failures)and type(found)is bool and type(buckets_present)is bool
        and(buckets_present or(not failures and not found)))
    g=BytesPath(regions,entry)
    g.take('4053','55','56','57','4157','4883ec30','4d8bf8','488bea','4885d2');g.branch('0f84',False)
    g.take('488b7910','bbffffffff','488b7118','4c89642460','4c896c2468','4c89742470','4885ff')
    g.branch('0f84',not buckets_present);iterations=[]
    if buckets_present:
        g.take('4c8b7130','4d85f6');g.branch('0f85',False)
        g.take('b902000000');g.call(hash_invoke)
        g.take('448bf0','410fbaf61f','418bc6','99','f77f18','3b5718');g.branch('0f83',False)
        g.take('4863da','8b5c9f20','ffcb','498b4720','488b88c0000000','488b4910');g.call(comparer_getter)
        g.take('488bf8','6690','4533e4','4885f6');g.branch('0f84',False);loop=g.at
        for reason in[*failures,None]:
            need('same-string-loop-entry',g.at==loop);begin=len(g.seen)
            g.take('3b5e18');miss=reason is None and not found;g.branch('73',miss,1)
            if miss:break
            g.take('4863c3','488d0c40','443974ce20');g.branch('75',reason=='hash',1)
            if reason!='hash':
                g.take('4863c3','488d0c40','4c8d04ce','4885ff');g.branch('0f84',False)
                g.take('4d8b4028','b908000000','4c8bcd','488bd7');g.call(equality_invoke)
                g.take('84c0');g.branch('74',reason=='key',1)
            if reason is not None:
                g.take('3b5e18');g.branch('0f83',False)
                g.take('4863c3','488d1c40','8b5cde24','443b6618');g.branch('0f8d',False)
                g.take('41ffc4');g.jump('eb',1)
                iterations.append(dict(reason=reason,selectedBytes=g.seen[begin:],nextIndexOffset=4,
                    counterRegister='r12d',counterIncrement=1))
    g.take('4c8b742470','8bc3','4c8b6c2468','4c8b642460','4883c430','415f','5f','5e','5d','5b','c3')
    return dict(selectedBytes=g.seen,failedProbes=list(failures),failedProbePrograms=iterations,
        found=found,bucketsPresent=buckets_present,keyBytes=8,keyKind='string reference',
        comparerRequiredNull=True,bucketFieldOffset=16,entryArrayFieldOffset=24,comparerFieldOffset=48,
        entryStride=24,entryHashOffset=0,entryNextOffset=4,entryKeyOffset=8,entryValueOffset=16,
        hashInvocationSlot=2,equalityInvocationSlot=8,hashMask=2147483647,
        hashArguments=dict(rdx='same incoming nonnull string key'),
        equalityArguments=dict(rdx='same selected comparer',r8='selected entry string key',r9='same incoming string key'),
        returnedIndex='first selected matching entry index'if found else-1,
        noDictionaryWrites=True,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],
        actualStringHashAndEqualityEffectsRequired=True,runtimeCallbackSelectionObserved=False)


def find_string_paths(regions,entry,*,hash_invoke,comparer_getter,equality_invoke,count_limit=4096):
    import itertools
    need('bounded-string-chain-domain',type(count_limit)is int and 3<=count_limit<=4096)
    symbols=dict(hash_invoke=hash_invoke,comparer_getter=comparer_getter,equality_invoke=equality_invoke)
    paths=[find_string_program(regions,entry,**symbols,failures=failures,found=found)
        for count in range(4)for failures in itertools.product(('hash','key'),repeat=count)for found in(False,True)]
    paths.append(find_string_program(regions,entry,**symbols,found=False,buckets_present=False))
    arms={}
    for reason in('hash','key'):
        bodies=[s['selectedBytes']for p in paths for s in p['failedProbePrograms']if s['reason']==reason]
        need('same-string-failed-probe-'+reason,bool(bodies)and all(b==bodies[0]for b in bodies));arms[reason]=bodies[0]
    certificate=dict(schema='endfield.patrol-string-reference-chain-induction.v1',countLimit=count_limit,
        failedProbeArms=arms,allMixedWitnessesThroughThree=True,counterRegister='r12d',counterInitial=0,
        counterIncrement=1,nextIndexEntryOffset=4,entryStride=24,
        invariant='At the shared chain entry EBX is the signed current entry index; R12D counts all prior failed hash/key probes. Both arms independently load the same entry next-index, compare the preserved counter to stable entry-array length, increment exactly once and return to the same entry. Normal hash/equality helpers preserve the nonvolatile dictionary/index/counter registers. The complete found/miss return therefore extends to each valid finite acyclic chain within countLimit.',
        conditions='Nonnull stable string key, default comparer field null, valid stable dictionary bucket/entry invariants and positive bucket length; finite acyclic chain within the bounded Int32 count; exact selected string hash/equality and comparer/context effects. Custom comparer, cold setup, malformed or concurrently mutated storage remain separate.')
    return paths,certificate


def property_set_program(regions,entry,*,kind,invoke):
    """Slot15 copies its own whole input and invokes slot17, never a raw alias."""
    need('finite-property-kind',kind in KINDS);g=BytesPath(regions,entry)
    if kind=='int':
        g.take('488bc1','448bc2','488bd0','b911000000')
        need('property-actual-tail-invoker',g.relative('e9')==invoke)
    elif kind=='UnityEngine.Vector3':
        g.take('4883ec38','f20f1002','4c8d442420','8b4208','4c8bc9',
            '498bd1','f20f11442420','b911000000','89442428');g.call(invoke)
        g.take('4883c438','c3')
    else:
        g.take('4883ec58','0f1002','488bc1','b911000000','0f104a10',
            '4c8d442420','0f29442420','f20f104220','488bd0',
            'f20f11442440','0f294c2430');g.call(invoke);g.take('4883c458','c3')
    return dict(selectedBytes=g.seen,kind=kind,propertySlot=15,invocationSelector=17,
        sameReceiver=True,wholeInputBytes=4 if kind=='int'else 12 if kind=='UnityEngine.Vector3'else 40,
        sameInputBits=True,entryRspRestored=True,nonvolatilesUntouched=True,
        physicalFunctionExtentProved=False,selectedSlot17EffectsRequired=True)


def virtual_set_program(regions,entry,*,kind,prepare,callback,slot):
    need('finite-virtual-set-kind-slot',kind in KINDS and type(slot)is int and slot in(15,17))
    g=BytesPath(regions,entry);excluded=[]
    if kind=='int':
        g.take('4053','57','4157','4881eca0000000','0fb7d9','458bf8','488b0a','488bfa');g.call(prepare)
        g.take('488b07','488d4b14','4803c9','4c8b0cc8','4c8b44c808')
        for branch,width in(('75',1),('75',1),('0f85',4)):
            excluded.append(g.relative('488d05'));g.take('4c3bc8');g.branch(branch,True,width)
        g.take('418bd7','488bcf','41ffd1','4881c4a0000000','415f','5f','5b','c3')
    elif kind=='UnityEngine.Vector3':
        g.take('48895c2408','4889742418','48897c2420','55','488bec','4883ec40',
            '0fb7d9','498bf0','488b0a','488bfa');g.call(prepare)
        g.take('f20f1006','4c8d4b14','8b4e08');excluded.append(g.relative('488d15'))
        g.take('49c1e104','4c030f','498b01','f20f1145e0','894de8','498b5908','483bc2');g.branch('74',slot==15,1)
        if slot==15:
            need('own-inlined-vector-property',callback==excluded[0])
            g.take('894df8','4c8d45f0','b911000000','f20f1145f0','488bd7');g.call(entry);g.jump('eb',1)
        else:
            for _ in range(2):
                excluded.append(g.relative('488d15'));g.take('483bc2');g.branch('74',False,1)
            g.take('4c8bc3','488d55e0','488bcf','ffd0')
        g.take('488b5c2450',
            '488b742460','488b7c2468','4883c440','5d','c3')
    else:
        g.take('48895c2408','4889742410','57','4881ec80000000',
            '0fb7f9','498bd8','488b0a','488bf2');g.call(prepare)
        g.take('488b06','488d4f14','0f1003','4803c9','0f104b10',
            '4c8b0cc8','0f29442450','f20f104320','f20f11442470','0f294c2460','4c8b44c808')
        excluded.append(g.relative('488d05'));g.take('4c3bc8');g.branch('74',slot==15,1)
        if slot==15:
            need('own-inlined-entity-property',callback==excluded[0])
            g.take('0f1003','b911000000','4c8d442420','488bd6','0f294c2430',
                '0f29442420','f20f104320','f20f11442440');g.call(entry);g.jump('eb',1)
        else:
            excluded.append(g.relative('488d05'));g.take('4c3bc8');g.branch('74',False,1)
            g.take('488d542450','488bce','41ffd1')
        g.take('4c8d9c2480000000',
            '498b5b10','498b7318','498be3','5f','c3')
    need('own-virtual-callback-outside-inline-alternatives',type(callback)is int and callback>0
        and(callback not in excluded or(slot==15 and kind!='int'and callback==excluded[0])))
    return dict(selectedBytes=g.seen,kind=kind,selector=slot,callbackByteOffset=320+slot*16,
        methodInfoByteOffset=328+slot*16,excludedInlineCallbacks=excluded,
        selectedCallbackRequired=callback,wholeValueBytes=4 if kind=='int'else 12 if kind=='UnityEngine.Vector3'else 40,
        callbackArguments=dict(rcx='same incoming receiver',rdx='same Int32 bits'if kind=='int'else'whole copied incoming value',r8='same selected slot MethodInfo'),
        entryRspRestored=True,inlinedPropertyRecallsSameInvokerAtSelector17=slot==15 and kind!='int',
        runtimeCallbackSelectionObserved=False,normalReadyClassPreparationRequired=True)


def try_insert_program(regions,entry,*,prepare,comparer_getter,element_address,
                       failures=(),found=True):
    """Set-item mode1: update, or no-free-entry insertion with spare capacity."""
    need('finite-insert-witness',isinstance(failures,(tuple,list))and len(failures)<=3
        and all(x in('hash','key')for x in failures)and type(found)is bool)
    g=BytesPath(regions,entry)
    g.take('44884c2420','4c89442418','4889542410','48894c2408','57','4154','4157',
        '4883ec70','488bfa','4c8bf9','4885d2');g.branch('75',True,1)
    g.take('41ff472c','4533e4','48895c2468','48896c2460','4889742458',
        '4c896c2450','4c89742448','4d396710');g.branch('0f85',True)
    g.take('498b6f30','498b5f18','4885ed');g.branch('75',False,1)
    g.take('4885ff');g.branch('0f84',False);g.take('488b0f');g.call(prepare)
    g.take('488b17','488bcf','488b8260010000','488b9268010000','ffd0');g.jump('eb',1)
    g.take('448bf0','498b4f10','410fbaf61f','4885c9');g.branch('0f84',False)
    g.take('418bc6','99','f77918','3b5118');g.branch('0f83',False)
    g.take('4c63ea','4983c508','428b3ca9','4e8d2ca9','ffcf','4885ed');g.branch('0f84',True)
    g.take('488bac24b0000000','488b4520','488b88c0000000','488b4910');g.call(comparer_getter)
    g.take('488bf0','4885db');g.branch('0f84',False);loop=g.at;iterations=[]
    for reason in[*failures,None]:
        need('same-insert-chain-entry',g.at==loop);begin=len(g.seen)
        g.take('3b7b18');miss=reason is None and not found;g.branch('0f83',miss)
        if miss:break
        g.take('4863cf','488d1449','443974d320');g.branch('75',reason=='hash',1)
        if reason!='hash':
            g.take('4863c7','488d0c40','488b6ccb28','4885f6');g.branch('0f84',False)
            g.take('488b0e');g.call(prepare)
            g.take('4c8b0e','488bd5','4c8b842498000000','488bce',
                '498b81c0010000','4d8b89c8010000','ffd0','84c0');g.branch('75',reason is None,1)
        if reason is not None:
            g.take('3b7b18');g.branch('0f83',False)
            g.take('4863c7','488d0c40','8b7ccb24','443b6318');g.branch('0f8d',False)
            g.take('41ffc4');g.jump('eb',1)
            iterations.append(dict(reason=reason,selectedBytes=g.seen[begin:],counterRegister='r12d',counterIncrement=1,nextIndexOffset=4))
    collector=None;table=None
    if found:
        g.take('0fb68424a8000000','3c01');g.branch('74',True,1)
        g.take('4863d7','488bcb');g.call(element_address)
        g.take('488b8c24a0000000','4863d7','48894810','488bcb');g.call(element_address)
        collector=flag(g,'833d');g.take('4c8d4010');g.branch('0f84',True)
    else:
        g.take('32c9','4032f6','41837f2800');g.branch('0f8f',False)
        g.take('418b7f20','3b7b18');g.branch('75',True,1)
        g.take('498b5f18','8d4701','41894720','84c9');g.branch('74',True,1)
        g.take('4885db');g.branch('0f84',False)
        g.take('3b7b18');g.branch('0f83',False)
        g.take('4863c7','488d0c40','4c8d0ccb','4084f6');g.branch('74',True,1)
        g.take('45897120');table=g.relative('4c8d15')
        g.take('418b4500','ffc8','41894124','488b842498000000','49894128')
        collector=g.relative('8b05');g.take('85c0');g.branch('74',True,1)
        g.take('488b8c24a0000000','49894930','85c0');g.branch('74',True,1)
        g.take('8d4701','41894500');g.jump('e9')
    g.take('b001','4c8b742448','4c8b6c2450','488b742458','488b6c2460',
        '488b5c2468','4883c470','415f','415c','5f','c3')
    return dict(selectedBytes=g.seen,found=found,failedProbes=list(failures),failedProbePrograms=iterations,
        mode=1,nonnullStringKeyRequired=True,defaultComparerRequired=True,
        versionFieldOffset=44,versionIncrementModulo2Pow32=1,
        bucketFieldOffset=16,entryArrayFieldOffset=24,countFieldOffset=32,
        freeListCountFieldOffset=40,entryStride=24,entryHashOffset=0,entryNextOffset=4,
        entryKeyOffset=8,entryValueOffset=16,hashMask=2147483647,
        hashCallbackOffset=352,hashMethodInfoOffset=360,equalityCallbackOffset=448,equalityMethodInfoOffset=456,
        replacementValueSameIncomingReference=True,keyFieldWritten=not found,countIncrement=0 if found else 1,
        bucketStoresInsertedIndexPlusOne=not found,entryNextStoresPriorBucketMinusOne=not found,
        noFreeEntriesAndSpareCapacityRequired=not found,collectorDisabledFlagVa=collector,
        unusedCollectorTableVa=table,returnsLiteralTrue=True,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],
        selectedHashEqualityAndAddressEffectsRequired=True,resizeAndFreeListReuseProved=False,
        runtimeStorageObserved=False)


def try_insert_paths(regions,entry,*,prepare,comparer_getter,element_address,count_limit=4096):
    import itertools
    need('bounded-insert-chain-domain',type(count_limit)is int and 3<=count_limit<=4096)
    symbols=dict(prepare=prepare,comparer_getter=comparer_getter,element_address=element_address)
    paths=[try_insert_program(regions,entry,**symbols,failures=failures,found=found)
        for count in range(4)for failures in itertools.product(('hash','key'),repeat=count)for found in(False,True)]
    arms={}
    for reason in('hash','key'):
        bodies=[s['selectedBytes']for p in paths for s in p['failedProbePrograms']if s['reason']==reason]
        need('same-insert-failed-probe-'+reason,bool(bodies)and all(b==bodies[0]for b in bodies));arms[reason]=bodies[0]
    return paths,dict(schema='endfield.patrol-string-reference-insert-induction.v1',countLimit=count_limit,
        failedProbeArms=arms,counterRegister='r12d',counterInitial=0,counterIncrement=1,
        entryStride=24,allMixedWitnessesThroughThree=True,
        invariant='Both failed hash/key probes read the exact entry next-index, preserve and increment R12D once and return to the same chain entry. Under stable valid acyclic bounded storage, the first matching entry is updated, or the chain end selects the independently proved no-free-entry/spare-capacity insertion. Only the version counter changes before chain selection; mode1 update preserves count/key/links, while insertion writes the complete masked hash/next/key/value, advances count and publishes index+1 in the same bucket.',
        conditions='Nonnull stable string key, nonnull valid buckets and entries, default comparer, ready own typed context and same hash/equality callbacks, disabled collector, normal ABI, bounded finite acyclic chain. New insertion requires freeCount<=0 and count<entry-array length. Concurrent mutation, malformed storage, custom comparers, cold initialization, resize and free-list reuse are separate.')


def ready_context_type_program(regions,entry,*,inner):
    g=BytesPath(regions,entry);g.take('488bc1','4863ca','488b0cc8')
    need('same-actual-context-type-tail',g.relative('e9')==inner);g.at=inner
    g.take('f6813801000001');g.branch('74',False,1)
    g.take('488bc1');g.jump('eb',1);g.take('c3')
    return dict(selectedBytes=g.seen,contextIndexArgument='signed incoming EDX',
        contextCellBytes=8,selectedClassFlagOffset=312,selectedClassFlagMask=1,
        selectedFlagRequiredSet=True,returnsSameSelectedContextClass=True,
        entryRspAndNonvolatilesUntouched=True,memoryWrites=0,calls=0,
        physicalFunctionExtentProved=False,coldResolutionProved=False)


def class_ready_program(regions,entry):
    g=BytesPath(regions,entry)
    g.take('4053','4883ec20','488bd9','0fb6813a010000','90','a804');g.branch('75',True,1)
    g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,selectedClassFlagOffset=314,selectedClassFlagMask=4,
        selectedFlagRequiredSet=True,entryRspRestored=True,restoredNonvolatiles=['rbx'],memoryWrites=0,calls=0)


def assignable_program(regions,entry,*,prepare):
    g=BytesPath(regions,entry)
    g.take('48895c2410','57','4883ec20','488bfa','488bd9','0fb6813a010000','90','a804');g.branch('75',True,1)
    g.take('488bcf');g.call(prepare)
    g.take('0fb68732010000','388332010000');g.branch('72',False,1)
    g.take('0fb6c8','488b83c8000000','48397cc8f8');g.branch('75',False,1)
    g.take('b001','488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,receiverClassArgument='RCX',expectedClassArgument='RDX',
        receiverReadyFlagOffset=314,receiverReadyFlagMask=4,expectedPrepareTarget=prepare,
        classDepthOffset=306,hierarchyPointerOffset=200,hierarchyCellBytes=8,
        requiredReceiverDepthAtLeastExpected=True,requiredHierarchyEntryEqualsExpected=True,
        hierarchyIndex='expected unsigned-byte depth minus one',returnsLiteralTrue=True,
        entryRspRestored=True,restoredNonvolatiles=['rbx','rdi'],memoryWrites=0,
        actualClassSelectionObserved=False,unmatchedHierarchyPathsProved=False)


def entry_address_program(regions,entry):
    g=BytesPath(regions,entry);g.take('4883ec28','3b5118');g.branch('73',False,1)
    g.take('488d4202','488d0442','488d04c1','4883c428','c3')
    return dict(selectedBytes=g.seen,indexArgument='zero-extended nonnegative EDX',
        arrayArgument='RCX',arrayLengthOffset=24,elementStride=24,
        returns='incoming array plus32 plus24 times incoming index',
        indexRequiredBelowArrayLength=True,memoryWrites=0,calls=0,entryRspRestored=True,nonvolatilesUntouched=True)


def string_hash_program(regions,entry,*,units):
    need('bounded-owned-nonzero-UTF16-string',isinstance(units,list)and len(units)<=64
        and all(type(v)is int and 1<=v<=65535 for v in units))
    g=BytesPath(regions,entry);g.take('488d4114','ba05150000','0fb708','448bc2','85c9')
    g.branch('74',not units,1);a=b=5381;index=0
    if units:
        while True:
            g.take('6bd221','33d1');a=((a*33)^units[index])&0xffffffff
            g.take('0fb74802','85c9');g.branch('74',index+1==len(units),1)
            if index+1==len(units):break
            g.take('456bc021','4883c004','4433c1');b=((b*33)^units[index+1])&0xffffffff
            g.take('0fb708','85c9');index+=2;g.branch('75',index<len(units),1)
            if index==len(units):break
    g.take('4169c0658b585d','03c2','c3')
    return dict(selectedBytes=g.seen,utf16Units=list(units),firstCharOffset=20,
        terminatorRequiredImmediatelyAfterUnits=True,embeddedZeroExcluded=True,
        resultBits=(a+b*1566083941)&0xffffffff,arithmeticBits=32,
        alternatingAccumulatorInitial=5381,accumulatorMultiply=33,finalSecondAccumulatorMultiply=1566083941,
        memoryWrites=0,calls=0,entryRspAndNonvolatilesUntouched=True,
        physicalFunctionExtentProved=False,runtimeStringStorageObserved=False)


def integer_get_invoker_program(regions,entry,*,prepare,callback,slot=14):
    need('exact-Int32-getter-slot',type(slot)is int and slot==14)
    g=BytesPath(regions,entry)
    g.take('48895c2408','55','56','57','4154','4155','4156','4157',
        '4883ec50','4c8bf2','0fb7d9','488b0a');g.call(prepare)
    g.take('488d4b14','4803c9','498b06','4c8b04c8','488b54c808');excluded=[]
    for branch,width in(('0f85',4),('75',1),('75',1)):
        excluded.append(g.relative('488d05'));g.take('4c3bc0');g.branch(branch,True,width)
    need('own-Int32-getter-outside-inlined-alternatives',type(callback)is int and callback>0 and callback not in excluded)
    g.take('498bce','41ffd0','488b9c2490000000','4883c450','415f','415e','415d','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,slot=slot,callbackByteOffset=320+slot*16,
        methodInfoByteOffset=328+slot*16,selectedCallbackRequired=callback,
        excludedInlineCallbacks=excluded,callbackArguments=dict(rcx='same incoming receiver',rdx='same selected slot MethodInfo'),
        returnedEaxBitsUnchanged=True,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],runtimeSelectionObserved=False)


def byte_equality_program(regions,entry,*,count,mismatch=None):
    """Complete actual equality for one bounded length and first unequal chunk."""
    need('bounded-byte-equality-length',type(count)is int and 0<=count<=128)
    chunks=([*range(0,count-8,8),count-8]if count>=8 else list(range(count)))
    need('finite-first-mismatch',mismatch is None or(type(mismatch)is int and mismatch in chunks))
    g=BytesPath(regions,entry)
    g.take('48895c2408','48896c2410','4889742418','48897c2420','4154','4156','4157',
        '4883ec20','488bfa','4c8be1','483bca');g.branch('0f84',False)
    g.take('4983f808');g.branch('72',count<8,1);checked=[];class_cells=[]
    if count>=8:
        g.take('498d70f8','4885f6');g.branch('74',count==8,1)
        if count>8:
            g.take('4c8bf9','488bda','4c2bfa');loop=g.at
            for offset in range(0,count-8,8):
                need('same-byte-equality-qword-loop',g.at==loop)
                class_cells.append(g.relative('488b0d'))
                g.take('4a8b2c3b','4c8b33','83b9e000000000');g.branch('74',False,1)
                g.take('493bee');bad=mismatch==offset;g.branch('75',bad,1);checked.append([offset,8])
                if bad:break
                g.take('4883c308','488bc3','482bc7','483bf0');g.branch('77',offset+8<count-8,1)
            else:bad=False
        else:bad=False
        if bad:
            g.take('32c0');g.jump('eb',1)
        else:
            class_cells.append(g.relative('488b0d'))
            g.take('4a8b1c26','488b3c3e','83b9e000000000');g.branch('74',False,1)
            g.take('483bdf','0f94c0');checked.append([count-8,8])
    else:
        g.take('4d85c0');g.branch('74',count==0,1)
        if count:
            g.take('488bcf','4c2be7');loop=g.at
            for offset in range(count):
                need('same-byte-equality-byte-loop',g.at==loop)
                g.take('0fb601','42380421');bad=mismatch==offset;g.branch('75',bad,1);checked.append([offset,1])
                if bad:break
                g.take('48ffc1','488bc1','482bc7','4c3bc0');g.branch('77',offset+1<count,1)
            if bad:g.take('32c0');g.jump('eb',1)
            else:g.take('b001');g.jump('eb',1)
        else:g.take('b001');g.jump('eb',1)
    g.take('488b5c2440','488b6c2448','488b742450','488b7c2458','4883c420','415f','415e','415c','c3')
    need('same-ready-comparison-class-cell',not class_cells or len(set(class_cells))==1)
    need('all-equality-read-spans-within-length',all(0<=a and a+n<=count for a,n in checked))
    return dict(selectedBytes=g.seen,byteCount=count,firstUnequalChunkOffset=mismatch,
        readSpans=checked,equal=mismatch is None,allEarlierChunksRequiredEqual=True,
        completeInputByteCoverage=sorted({i for a,n in checked for i in range(a,a+n)})==list(range(count)),
        readyClassCellVa=class_cells[0]if class_cells else None,readyClassFlagOffset=224,
        memoryWrites=0,calls=0,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r14','r15'],
        condition='Stable valid disjoint or same-content byte extents of the exact bounded count, coherent existing comparison class already initialized, normal Win64 ABI; earlier chunks equal and the selected first mismatch if any. No collation, normalization or ignore-case transform occurs.')


def string_equals_program(regions,entry,*,compare,mode):
    need('finite-string-equality-mode',mode in('same-reference','null','different-class','different-length','content'))
    g=BytesPath(regions,entry);g.take('483bca');g.branch('74',mode=='same-reference',1);class_cell=None
    if mode=='same-reference':g.take('b001');g.jump('eb',1);g.take('c3')
    else:
        g.take('4885d2');g.branch('74',mode=='null',1)
        if mode!='null':
            class_cell=g.relative('488b05');g.take('483902');g.branch('75',mode=='different-class',1)
            if mode!='different-class':
                g.take('8b4210','394110');g.branch('75',mode=='different-length',1)
                if mode=='content':
                    g.take('4c634110','4883c214','4d03c0','4883c114','4533c9')
                    need('same-actual-ordinal-byte-comparison-tail',g.relative('e9')==compare)
                    return dict(selectedBytes=g.seen,mode=mode,stringClassCellVa=class_cell,
                        lengthFieldOffset=16,firstCharFieldOffset=20,comparisonBytes='twice same signed nonnegative UTF16 length',
                        comparisonArguments=dict(rcx='same receiver UTF16 data',rdx='same argument UTF16 data',r8='length times2',r9d=0),
                        tailResultReturnedUnchanged=True,entryRspAndNonvolatilesUntouched=True,memoryWrites=0,
                        physicalFunctionExtentProved=False)
        g.take('32c0','c3')
    return dict(selectedBytes=g.seen,mode=mode,stringClassCellVa=class_cell,
        returnedBool=mode=='same-reference',memoryWrites=0,calls=0,
        entryRspAndNonvolatilesUntouched=True,physicalFunctionExtentProved=False)


def default_comparer_program(regions,entry,*,type_from_context,context_type):
    g=BytesPath(regions,entry);g.take('4057','4883ec20','488bf9','488b4920');g.call(context_type)
    g.take('33d2','488b88c0000000');g.call(type_from_context)
    g.take('488b80b8000000','488b00','f0830c2400','4885c0');g.branch('74',False,1)
    g.take('4883c420','5f','c3')
    return dict(selectedBytes=g.seen,methodInfoClassOffset=32,classContextOffset=192,
        contextSlot=0,staticFieldsOffset=184,staticFieldOffset=0,
        selectedStaticSingletonRequiredNonnull=True,returnsSameStaticSingleton=True,
        entryRspRestored=True,restoredNonvolatiles=['rdi'],coldSingletonCreationProved=False,
        runtimeComparerClassOrContentsObserved=False)


def string_hash_invoker_program(regions,entry,*,prepare,callback,units):
    need('bounded-owned-hash-invoker-string',isinstance(units,list)and len(units)<=64
        and all(type(v)is int and 1<=v<=65535 for v in units))
    g=BytesPath(regions,entry)
    g.take('48895c2408','55','56','57','4154','4155','4156','4157',
        '4883ec50','4c8bf2','0fb7d9','488b0a');g.call(prepare)
    g.take('488d4b14','4803c9','498b06','4c8b04c8','488b54c808');excluded=[]
    for branch,width in(('0f85',4),('75',1)):
        excluded.append(g.relative('488d05'));g.take('4c3bc0');g.branch(branch,True,width)
    actual=g.relative('488d05');need('actual-string-hash-selected-inline-callback',callback==actual and callback not in excluded)
    g.take('4c3bc0');g.branch('75',False,1)
    g.take('b905150000','8bd1','498d4614','440fb700','4585c0');g.branch('74',not units,1)
    a=b=5381;index=0
    if units:
        g.take('0f1f4000','0f1f840000000000')
        while True:
            g.take('6bc921','4133c8');a=((a*33)^units[index])&0xffffffff
            g.take('440fb74002','4585c0');g.branch('74',index+1==len(units),1)
            if index+1==len(units):break
            g.take('6bd221','4133d0','4883c004');b=((b*33)^units[index+1])&0xffffffff
            g.take('440fb700','4585c0');index+=2;g.branch('75',index<len(units),1)
            if index==len(units):break
    g.take('69c2658b585d','03c1');g.jump('eb',1)
    g.take('488b9c2490000000','4883c450',
        '415f','415e','415d','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,slot=2,selectedCallbackRequired=callback,
        excludedInlineCallbacks=excluded,utf16Units=list(units),resultBits=(a+b*1566083941)&0xffffffff,
        firstCharOffset=20,terminatorRequiredImmediatelyAfterUnits=True,embeddedZeroExcluded=True,
        entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],
        callbackArgumentSameIncomingString=True,runtimeCallbackSelectionObserved=False)


def erased_comparer_equals_program(regions,entry,*,invoke):
    g=BytesPath(regions,entry);g.take('4885d2');g.branch('74',False,1)
    g.take('4d85c0');g.branch('74',False,1)
    g.take('33c9');need('same-erased-comparer-equals-tail',g.relative('e9')==invoke)
    return dict(selectedBytes=g.seen,invocationSelector=0,firstKeyRegister='rdx',secondKeyRegister='r8',
        bothKeysRequiredNonnull=True,entryRspAndNonvolatilesUntouched=True,memoryWrites=0,
        closedCanonicalPointerEquivalenceProved=False,physicalFunctionExtentProved=False,
        actualRuntimeComparerNominalRequired='System.Collections.Generic.GenericEqualityComparer`1<string>')


def comparer_equals_invoker_program(regions,entry,*,prepare,callback,invoke):
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','48897c2418','4156','4883ec20',
        '0fb7d9','498bf1','488b0a','498bf8','4c8bf2');g.call(prepare)
    g.take('498b06','488d4b14','4803c9','4c8b14c8','4c8b4cc808')
    need('actual-selected-erased-comparer-callback',g.relative('488d05')==callback)
    g.take('4c3bd0');g.branch('75',False,1)
    g.take('4885ff');g.branch('0f84',False)
    g.take('4885f6');g.branch('0f84',False)
    g.take('33c9','4c8bc6','488bd7');g.call(invoke)
    g.take('488b5c2430','488b742438','488b7c2440','4883c420','415e','c3')
    return dict(selectedBytes=g.seen,slot=8,selectedCallbackRequired=callback,
        firstKeyRequiredNonnull=True,secondKeyRequiredNonnull=True,nestedInvocationSelector=0,
        sameBothInputStringReferencesPassed=True,returnedBoolBitsUnchanged=True,
        entryRspRestored=True,restoredNonvolatiles=['rbx','rsi','rdi','r14'],
        closedCanonicalPointerEquivalenceProved=False,runtimeCallbackSelectionObserved=False)


def string_equals_invoker_program(regions,entry,*,prepare,callback):
    g=BytesPath(regions,entry)
    g.take('48895c2408','55','56','57','4154','4155','4156','4157',
        '4883ec40','498bf0','488bfa','0fb7d9','488b0a');g.call(prepare)
    g.take('488d4b14','4803c9','488b07','4c8b0cc8','4c8b44c808');excluded=[]
    for branch,taken,width in(('75',True,1),('74',False,1),('0f85',True,4)):
        excluded.append(g.relative('488d05'));g.take('4c3bc8');g.branch(branch,taken,width)
    need('own-String-Equals-outside-inline-alternatives',type(callback)is int and callback>0 and callback not in excluded)
    g.take('488bd6','488bcf','41ffd1');g.jump('e9')
    g.take('488b9c2480000000','4883c440','415f','415e','415d','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,slot=0,callbackByteOffset=320,methodInfoByteOffset=328,
        selectedCallbackRequired=callback,excludedInlineCallbacks=excluded,
        callbackArguments=dict(rcx='same incoming first string',rdx='same incoming second string',r8='same selected MethodInfo'),
        returnedBoolBitsUnchanged=True,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],
        runtimeCallbackSelectionObserved=False)

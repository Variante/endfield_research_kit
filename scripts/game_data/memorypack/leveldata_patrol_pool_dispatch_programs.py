"""Selected IReusable interface fallback in the actual pool dispatchers.

The class discriminator predicate is a source condition, not an assertion that
the runtime field contains a metadata type index. Other inline class arms and
the dynamic interface resolver remain outside these programs.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check,condition):
    if not condition:raise ValueError('patrolPoolDispatch.'+check)


def program(regions,entry,*,recycle,prepare,callback,misses=0):
    need('literal-interface-mode',type(recycle)is bool)
    need('bounded-interface-witness',type(misses)is int and 0<=misses<=3)
    need('own-selected-callback',type(callback)is int and callback>0)
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742418','48897c2420','55','4156','4157')
    if recycle:g.take('488d6c24b9','4881ecf0000000','488b01','488bd9','33f6','8b881c010000')
    else:g.take('488bec','4883ec40','488b01','488bd9','8b881c010000')
    # This finite path excludes both neighboring inline subtrees. Immediates
    # come from the authenticated compares, never a nominal index constant.
    g.take('81f9');lower=int.from_bytes(g.read(4),'little',signed=True)+1
    g.branch('0f8f',True);g.take('81f9');upper=int.from_bytes(g.read(4),'little',signed=True)-1
    g.branch('0f8f',False)
    g.branch('74'if recycle else'0f84',False,1 if recycle else 4)
    g.take('81e9');subtract=int.from_bytes(g.read(4),'little',signed=True)
    g.take('83f9');last=int.from_bytes(g.read(1),'little',signed=True)
    need('nonwrapping-selected-class-interval',0<=subtract<=lower<=upper<2**31 and 0<=last<128)
    lower=max(lower,subtract+last+1);need('nonempty-selected-class-interval',lower<=upper)
    g.branch('0f87',True);g.take('4c8b33')
    site=g.at;interface=g.relative('488b3d'if recycle else'488b35')
    g.take('498bce');g.call(prepare);g.take('410fb78e30010000')
    if recycle:g.take('663bf1')
    else:g.take('33ff','663bf9')
    g.branch('73',False,1);g.take('498b96b0000000')
    if not recycle:g.take('66660f1f840000000000')
    loop=g.at;steps=[]
    for index in range(misses+1):
        need('same-interface-search-loop',g.at==loop);start=len(g.seen)
        g.take('0fb7c6'if recycle else'0fb7c7','4803c0','48393cc2'if recycle else'483934c2')
        g.branch('74',index==misses,1)
        if index<misses:
            g.take('66ffc6'if recycle else'66ffc7','663bf1'if recycle else'663bf9');g.branch('72',True,1)
        steps.append(g.seen[start:])
    if recycle:g.take('0fb7ce','4803c9','8b44ca08','ffc0','4898')
    else:g.take('0fb7cf','4803c9','486344ca08')
    g.take('4883c014','48c1e004','4903c6');g.jump('eb',1)
    g.take('4c8b00','488bcb','488b5008','41ffd0')
    if recycle:
        g.take('4c8d9c24f0000000','498b5b20','498b7330','498b7b38','498be3','415f','415e','5d','c3')
    else:g.take('488b5c2460','488b742470','488b7c2478','4883c440','415f','415e','5d','c3')
    return dict(selectedBytes=g.seen,recycle=recycle,requiredSignedClassDiscriminatorInterval=[lower,upper],
        classDiscriminatorFieldOffset=284,metadataTypeIndexEquivalenceProved=False,
        interfaceClassSiteVa=site,interfaceClassCellVa=interface,interfaceCountFieldOffset=304,
        interfaceTableFieldOffset=176,interfaceEntryStride=16,interfaceKeyOffset=0,interfaceSlotBaseOffset=8,
        firstMatchingInterfaceIndex=misses,failedSearchPrograms=steps[:-1],interfaceMethodOrdinal=1 if recycle else 0,
        matchingInterfaceRequiredWithinCount=True,selectedCallbackRequired=callback,
        sameReceiverAndSelectedMethodInfoPassed=True,callbackEffectsRequired=True,
        entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','r14','r15'],
        runtimeClassInterfaceOrCallbackObserved=False,dynamicInterfaceResolverProved=False)


def paths(regions,entry,*,recycle,prepare,callback,count_limit=4096):
    need('literal-interface-count-domain',type(count_limit)is int and count_limit==4096)
    values=[program(regions,entry,recycle=recycle,prepare=prepare,callback=callback,misses=i)for i in range(4)]
    arm=values[1]['failedSearchPrograms'][0]
    need('same-interface-search-step-all-witnesses',all(a==arm for p in values for a in p['failedSearchPrograms']))
    return values,dict(countLimit=count_limit,indexInitial=0,indexIncrement=1,indexBits=16,
        counterRegister='si'if recycle else'di',interfaceEntryStride=16,failedSearchStep=arm,
        invariant='Each failed key comparison preserves the same interface class/table, increments the bounded 16-bit index exactly once and returns to the owned loop. Under stable valid entries and the matching index below the declared count, the selected slot base plus the exact method ordinal supplies the callback/MethodInfo pair.',
        runtimeInterfaceSelectionObserved=False)


def interface_compatibility_program(regions,entry,*,ready_type,prepare,misses=0):
    need('bounded-compatible-interface-witness',type(misses)is int and 0<=misses<=3)
    g=BytesPath(regions,entry)
    g.take('48895c2420','4889542410','48894c2408','55','56','57','4154','4155','4156','4157',
        '4883ec20','4c8be2','4c8bf9','483bca');g.branch('0f84',False)
    g.take('0f1f00','498bcf');g.call(ready_type);g.take('498bcc');g.call(ready_type)
    g.take('498bcf');g.call(prepare);g.take('498bcc');g.call(prepare)
    g.take('41f6871401000020');g.branch('0f85',True)
    g.take('49837f6000');g.branch('0f84',True)
    g.take('4d85e4');g.branch('0f84',False)
    g.take('33db','0f1f840000000000','6641399c242e010000');g.branch('76',True,1)
    g.take('0fb7cb','410fb794242e010000','663bda');g.branch('73',True,1)
    g.take('498bcc');g.call(prepare)
    g.take('0fb7cb','410fb7942430010000','663bda');g.branch('73',False,1)
    g.take('4d8b8424b0000000','66660f1f840000000000');loop=g.at;steps=[]
    for index in range(misses+1):
        need('same-compatible-interface-loop',g.at==loop);start=len(g.seen)
        g.take('0fb7c1','4803c0','4d393cc0');g.branch('0f84',index==misses)
        if index<misses:g.take('66ffc1','663bca');g.branch('72',True,1)
        steps.append(g.seen[start:])
    g.take('b001','488b5c2478','4883c420','415f','415e','415d','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,expectedInterfaceRegister='incoming RCX',actualClassRegister='incoming RDX',
        expectedInterfaceFlagOffset=276,expectedInterfaceFlagMask=32,expectedGenericContextRequiredNullOffset=96,
        actualDirectInterfaceCountRequiredZeroOffset=302,actualInterfaceCountOffset=304,actualInterfaceTableOffset=176,
        firstMatchingInterfaceIndex=misses,interfaceEntryStride=16,failedSearchPrograms=steps[:-1],
        returnsLiteralTrue=True,memoryWrites=0,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],
        runtimeClassInterfaceOrStorageObserved=False)


def ready_type_program(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20','488bd9','f6813801000002');g.branch('0f85',True)
    g.take('488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,requiredClassFlagOffset=312,requiredClassFlagMask=2,
        memoryWrites=0,calls=0,entryRspRestored=True,restoredNonvolatiles=['rbx','rdi'])

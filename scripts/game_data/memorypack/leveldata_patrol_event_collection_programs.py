"""Exact selected event dictionary and listener snapshot collection programs."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check,condition):
    if not condition:raise ValueError('patrolEventCollections.'+check)


def find_entry(regions,entry,*,empty=False,misses=(),hit=True,special_bucket=False):
    need('finite-FindEntry-witness',all(type(x)is bool for x in(empty,hit,special_bucket))and type(misses)in(tuple,list)
        and len(misses)<=4096 and all(type(x)is bool for x in misses))
    g=BytesPath(regions,entry);calls=[];uses=[];marker=None
    def call(role):
        at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target))
    def use():
        at=g.at;cell=g.relative('488b0d');uses.append(dict(instructionVa=at,cellVa=cell));return cell
    g.take('48895c2408','48896c2410','4889742418','57','4154','4155','4156','4157','4883ec30',
        '4d8be8','8bfa','488b5910','beffffffff','488b6918','4885db');g.branch('0f84',empty)
    cls=None
    if not empty:
        g.take('4c8b7930','4d85ff');g.branch('0f85',False);cls=use()
        g.take('4439b9e0000000');g.branch('0f84',False)
        g.take('448bff','410fbaf71f','817b1897030000');g.branch('0f85',not special_bucket)
        if special_bucket:
            g.take('b843e59f8e','41f7ef','4103d7','c1fa09','8bc2','c1e81f','03d0','69c297030000','418bd7','2bd0')
            # The emitted reciprocal quotient is exact over the whole cleared
            # Int32 hash range, rather than a sample of table keys.
            a=0x8e9fe543;d=1<<41;need('whole-31bit-reciprocal-bound',a*919>=d and ((1<<31)-1)*(a*919-d)<d)
        else:g.take('418bc7','99','f77b18');g.jump('e9')
        g.take('3b5318');g.branch('0f83',False)
        g.take('66660f1f840000000000','4863f2','4533f6','8b74b320','ffce','4885ed');g.branch('0f84',False);head=g.at
        sequence=list(misses)+([True]if hit else[])
        if not sequence:g.take('3b7518');g.branch('0f83',True)
        for i,equal_hash in enumerate(sequence):
            need('own-FindEntry-loop-head',g.at==head);final=hit and i==len(sequence)-1
            g.take('3b7518');g.branch('0f83',False)
            g.take('4863c6','488d0c40','44397ccd20');g.branch('0f85',not equal_hash)
            if equal_hash:
                g.take('498b4520','488b88c0000000','488b4910');call('defaultComparer')
                g.take('4c8be0','3b7518');g.branch('0f83',False)
                g.take('4863c6','488d1c40','8b5cdd28','4d85e4');g.branch('0f84',False)
                g.take('498b0c24');call('prepareComparer')
                g.take('498b0424','4c8b90c0010000','4c8b88c8010000')
                current=g.relative('488d05');need('same-own-CombineKey-inline-equality',marker is None or marker==current);marker=current
                g.take('4c3bd0');g.branch('0f85',False)
                need('same-default-key-class-cell',use()==cls);g.take('83b9e000000000');g.branch('74',False,1)
                g.take('3bdf','0f94c0','84c0');g.branch('74',not final,1)
                if final:break
            g.take('3b7518');g.branch('73',False,1)
            g.take('4863c6','488d3440','8b74f524','443b7518');g.branch('7d',False,1)
            g.take('41ffc6');g.jump('e9')
            if i==len(sequence)-1:g.take('3b7518');g.branch('0f83',True)
    g.take('488b5c2460','8bc6','488b742470','488b6c2468','4883c430','415f','415e','415d','415c','5f','c3')
    return dict(selectedBytes=g.seen,calls=calls,classUsages=uses,defaultComparerFieldOffset=48,defaultComparerRequiredNull=not empty,
        bucketsFieldOffset=16,entriesFieldOffset=24,arrayLengthOffset=24,arrayDataOffset=32,bucketElementBytes=4,
        entryBytes=24,entryHashOffset=0,entryNextOffset=4,entryKeyOffset=8,entryValueOffset=16,
        inputKeyRegister='edx',inputKeyBytes=4,hashIsKeyBitsWithSignBitCleared=True,selectedInlineEqualityMarkerVa=marker,
        keyComparisonIsRawDWORD=True,equalityCallbackSlot=8,equalityMethodInfoClassOffset=456,
        positiveBucketLengthRequired=not empty,specialBucketLength=919 if special_bucket else None,
        specialReciprocalValidForAll31bitHashes=True,selectedMisses=list(misses),found=hit and not empty,
        result='matching nonnegative entry index'if hit and not empty else'literal minus one',
        sourceEntryIndexGuard='unsigned index less than entries.Length',sourceCollisionGuard='visited count less than entries.Length',
        invalidOrCyclicStorageEffectsProved=False,frameBytes=88,callShadow=[0,32],entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],nonframeWrites=0,
        selectedNormalDefaultComparerAndInlineCallbackRequired=True,liveContentsObserved=False)


def try_get_value(regions,entry,*,found=True):
    need('literal-TryGetValue-outcome',type(found)is bool);g=BytesPath(regions,entry)
    g.take('48895c2408','48896c2410','4889742418','57','4883ec20','498b4120','8bda','498bf1','498bf8','488be9',
        '488b90c0000000','488b82b0000000','4883782000');g.branch('75',True,1)
    g.take('488b4620','8bd3','488bcd','4c8b80c0000000','4d8b80b0000000');callsite=g.at;find=g.relative('e8')
    g.take('4863f0','85c0');g.branch('79',found,1);collector=None
    if not found:g.take('33c0','488907');g.jump('eb',1)
    else:
        g.take('488b5d18','4885db');g.branch('74',False,1);g.take('3b7318');g.branch('73',False,1)
        collector=g.relative('833d')+1;g.take('00','488d0c76','488d04cb','488b44cb30','488907');g.branch('74',True,1);g.take('b001')
    g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,findEntryInstructionVa=callsite,findEntryTargetVa=find,
        ownFindEntryContextSlotOffset=176,findEntryContextReadyOffset=32,inputDictionaryRegister='rcx',inputKeyRegister='edx',
        outputPointerRegister='r8',outputBytes=8,entryBytes=24,entryValueOffset=16,valueBitsUnchanged=True,
        output='same successful entry reference'if found else'literal null',result=found,returnsNormalizedBool=True,
        collectorFlagVa=collector,collectorDisabledRequired=found,frameBytes=40,callShadow=[0,32],entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi'],lookupAndCoherentOwnContextRequired=True)


def cached_values(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','4883794000','488bfa','488bd9');g.branch('74',False,1)
    g.take('488b4340','488b5c2430','488b742438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,cachedCollectionFieldOffset=64,cachedCollectionRequiredNonnull=True,
        returnedReference='same cached ValueCollection',dictionaryContentsUnchanged=True,nonframeWrites=0,effectCalls=0,
        frameBytes=40,entryRspRestored=True,restoredNonvolatiles=['rbx','rsi','rdi'],cacheCreationProved=False)


def list_pool_allocate(regions,entry):
    g=BytesPath(regions,entry);calls=[]
    def call(role):
        at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
    g.take('48895c2408','57','4883ec20','488bd9','488b4920');ready=call('readyContext')
    g.take('33d2','488b88c0000000');indexed=call('indexedContext')
    g.take('83b8e000000000');g.branch('74',False,1)
    g.take('488b4b20');need('same-pool-ready',call('readyContext')==ready)
    g.take('33d2','488b88c0000000');need('same-pool-indexed',call('indexedContext')==indexed)
    g.take('488b88b8000000','488b39','4885ff');g.branch('74',False,1)
    g.take('488b4b20');need('same-pool-ready',call('readyContext')==ready)
    g.take('488b88c0000000','488b4128','4883782000');g.branch('0f84',False)
    g.take('488b4b20');need('same-pool-ready',call('readyContext')==ready)
    g.take('488bcf','488b90c0000000','488b5228','488b5c2430','4883c420','5f');target=g.relative('e9')
    return dict(selectedBytes=g.seen,calls=calls,backendTargetVa=target,backendContextSlotOffset=40,
        poolStaticFieldOffset=0,poolRequiredNonnull=True,frameBytes=40,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rdi'],ownCoherentReadyContextsRequired=True)


def add_range(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2408','48896c2410','4889742418','57','4883ec20','498b4020','498bd8',
        '8b6918','488bf2','488bf9','4c8b80c0000000','498b4078','4883782000');g.branch('0f84',False)
    g.take('488b4320','4c8bc6','8bd5','488bcf','4c8b88c0000000','4d8b4978','488b5c2430','488b6c2438','488b742440','4883c420','5f')
    target=g.relative('e9')
    return dict(selectedBytes=g.seen,insertRangeTargetVa=target,insertRangeContextSlotOffset=120,
        arguments=dict(rcx='same destination List',edx='same incoming List size',r8='same incoming collection',r9='own closed InsertRange MethodInfo'),
        frameBytes=40,entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi'],ownContextReadyRequired=True)


def default_comparer(regions,entry):
    g=BytesPath(regions,entry);calls=[]
    def call(role):
        at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
    g.take('4057','4883ec20','488bf9','488b4920');ready=call('readyContext')
    g.take('33d2','488b88c0000000');indexed=call('indexedContext')
    g.take('488b80b8000000','488b00','f0830c2400','4885c0');g.branch('74',False,1)
    g.take('4883c420','5f','c3')
    return dict(selectedBytes=g.seen,calls=calls,contextSlot=0,staticCachedComparerOffset=0,
        returnedReference='same ready cached comparer',cachedComparerNonnullRequired=True,
        ownCoherentContextRequired=True,frameBytes=40,entryRspRestored=True,restoredNonvolatiles=['rdi'],nonframeWrites=0)


def spare_pool_allocate(regions,entry,*,spare_count=1):
    need('finite-positive-spare-count',type(spare_count)is int and 1<=spare_count<=4096)
    g=BytesPath(regions,entry);g.take('48895c2418','4889742420','57','4883ec20')
    ready=g.relative('803d')+1;g.take('00','488bda','488bf9');g.branch('75',True,1)
    g.take('488b7710','4885f6');g.branch('0f84',False);g.take('837e1800','48896c2438');g.branch('0f84',False)
    g.take('4885f6');g.branch('0f84',False)
    g.take('48635618','488b4e10');site=g.at;cell=g.relative('488b2d')
    g.take('448d42ff','4885c9');g.branch('0f84',False);g.take('443b4118');g.branch('0f83',False)
    g.take('ff461c','44894618','488d72ff','3b7118');g.branch('0f83',False)
    collector=g.relative('833d')+1;g.take('00','488d42ff','488b74f120','48c744c12000000000');g.branch('0f84',True)
    g.take('48837f1800');g.branch('74',True,1)
    g.take('488b6c2438','488bc6','488b742448','488b5c2440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,spareCount=spare_count,metadataReadyFlagVa=ready,
        spareListFieldOffset=16,listItemsFieldOffset=16,listSizeFieldOffset=24,listVersionFieldOffset=28,
        spareArrayElementBytes=8,selectedIndex=spare_count-1,spareSizeAfter=spare_count-1,
        poppedSlotZeroed=True,returnedReference='same previous last spare reference',spareReferenceNonnullRequired=True,
        listVersionIncrementMod32=1,onGetFieldOffset=24,onGetRequiredNull=True,classUsage=dict(instructionVa=site,cellVa=cell),
        collectorFlagVa=collector,collectorDisabledRequired=True,frameBytes=40,callShadow=[0,32],entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi'],coldOrEmptyPoolCreationProved=False,livePoolContentsObserved=False)


def list_clear(regions,entry,*,old_count=0):
    need('finite-old-list-size',type(old_count)is int and 0<=old_count<=4096)
    g=BytesPath(regions,entry);zero=None
    g.take('4057','4883ec30','8b7918','33d2','ff411c','895118','85ff');g.branch('7f',old_count>0,1)
    if old_count:
        g.take('48895c2440','488b5910','4889742450','4885db');g.branch('0f84',False)
        g.take('483913');g.branch('0f84',False);g.take('488b03','389034010000');g.branch('0f86',False)
        g.take('48395310');g.branch('0f85',False);g.take('8bf2','f7de','483913');g.branch('0f84',False)
        g.take('488b03','389034010000');g.branch('0f86',False)
        g.take('48896c2448','4c89742458','48395310');g.branch('75',False,1)
        g.take('488d6b18','488b6d00','41be01000000','4438b034010000');g.branch('0f87',False)
        g.take('4c8b742458','2bef','3bf5','488b6c2448');g.branch('0f8f',False)
        g.take('488b03','33d2','48638800010000','8bc1','0fafc7','4c63c0','4863c6','480fafc8','4883c120','4803cb')
        at=g.at;target=g.relative('e8');zero=dict(instructionVa=at,targetVa=target)
        g.take('488b742450','488b5c2440');g.jump('e9')
    g.take('4883c430','5f','c3')
    return dict(selectedBytes=g.seen,oldCount=old_count,sizeFieldOffset=24,sizeAfter=0,versionFieldOffset=28,versionIncrementMod32=1,
        zeroCall=zero,zeroArguments=None if not old_count else dict(rcx='same backing array+32',edx=0,r8=old_count*16),
        selectedArrayRank=1,selectedBoundsPointerRequiredNull=True,elementSizeClassOffset=256,elementBytesRequired=16,
        oldCountAtMostArrayLengthRequired=True,allOldElementBitsZeroedIfOwnZeroHelperProved=bool(old_count),
        frameBytes=56,callShadow=[0,32],callerProvidedHomeSpaceUsed=[[8,40]],entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r14']if old_count else['rdi'],liveListObserved=False)


def scope_dispose(regions,entry,*,nonnull=True):
    need('literal-scope-selection',type(nonnull)is bool);g=BytesPath(regions,entry)
    g.take('6690','488b01','48833800');g.branch('74',not nonnull,1);usage=None;target=None
    if nonnull:
        g.take('4c8b00','33c9');at=g.at;cell=g.relative('488b15');usage=dict(instructionVa=at,cellVa=cell)
        target=g.relative('e9')
    else:g.take('c3')
    return dict(selectedBytes=g.seen,nonnull=nonnull,scopeFieldOffset=0,scopeFieldIsPointerToListLocal=True,
        interfaceUsage=usage,tailTargetVa=target,tailArguments=None if not nonnull else dict(ecx=0,rdx='actual IDisposable class',r8='same nonnull referenced list'),
        inputFrameAndNonvolatilesUntouched=True,physicalScopeFunctionExtentProved=False,
        disposeCallbackEffectsRequired=nonnull)


def insert_range_snapshot(regions,entry,*,count=1,interface_steps=0):
    need('finite-snapshot-count',type(count)is int and 0<=count<=4096 and type(interface_steps)is int and 0<=interface_steps<=64)
    g=BytesPath(regions,entry);calls=[];excluded=[];copy_site=None
    def call(role):
        at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
    g.take('4c894c2420','4c89442418','48894c2408','53','56','57','4154','4155','4156','4157','4881ec80000000','0f29742470',
        '498bf1','498bd8','448be2','4c8bf1','4533ed','4c896c2430','4d85c0');g.branch('75',True,1)
    g.take('453b6618');g.branch('0f87',False)
    g.take('488b4e20','ba02000000','488b89c0000000');resolve=call('indexedContext')
    g.take('488bf8','4885db');g.branch('0f84',False)
    g.take('4c8b3b','498bd7','488bc8');call('compatibleCollection');g.take('84c0');g.branch('75',True,1)
    g.take('488b4e20','ba02000000','488b89c0000000');need('same-snapshot-indexed-context',call('indexedContext')==resolve)
    g.take('488bd0','33c9','4c8bc3');call('collectionCount')
    g.take('448bf8','898424c8000000','85c0');g.branch('0f8e',count==0)
    if count:
        g.take('418b7e18','488b4e20','488b91c0000000','488b4a60','4c396920');g.branch('75',True,1)
        g.take('488b4620','488b88c0000000','4c8b6960','4103ff','4d8b7e10','4d85ff');g.branch('0f84',False)
        g.take('41397f18');g.branch('7d',True,1)
        g.take('448bac24c8000000','33ff','453b6618');g.branch('7d',True,1)
        g.take('4d8b7e10','4c3bf3');g.branch('0f84',False)
        g.take('488b4e20','ba02000000','488b89c0000000');need('same-snapshot-indexed-context',call('indexedContext')==resolve)
        g.take('488bf8','488b33','488bce');call('prepareCollection')
        g.take('4533db','410fb7cb','440fb78630010000','66453bd8');g.branch('73',False,1)
        g.take('488b96b0000000','90');head=g.at
        for i in range(interface_steps+1):
            need('same-snapshot-CopyTo-interface-head',g.at==head)
            g.take('0fb7c1','4803c0','48393cc2');g.branch('74',i==interface_steps,1)
            if i<interface_steps:g.take('66ffc1','66413bc8');g.branch('72',True,1)
        g.take('0fb7c9','4803c9','8b44ca08','83c005','4898','4883c014','48c1e004','4803c6');g.jump('eb',1)
        g.take('4c8b10','4c8b4808')
        excluded.append(g.relative('488d05'));g.take('4c3bd0');g.branch('75',True,1)
        excluded.append(g.relative('488d05'));g.take('4c3bd0');g.branch('75',True,1)
        g.take('458bc4','498bd7','488bcb');copy_site=g.at;g.take('41ffd2','45016e18');g.jump('e9')
    g.take('41ff461c','0f28742470','4881c480000000','415f','415e','415d','415c','5f','5e','5b','c3')
    return dict(selectedBytes=g.seen,count=count,calls=calls,
        destinationInitiallyEmptyRequired=True,insertIndex=0,destinationCapacityAtLeastCountRequired=True,
        collectionRequiredNonnull=True,collectionCompatibleWithOwnClosedICollectionRequired=True,
        collectionCountResultRequired=count,countResultStableThroughCopyRequired=True,copyToInstructionVa=copy_site,
        copyToInterfaceSlot=5,copyToExcludedInlineTargets=excluded,
        copyToArguments=None if not count else dict(rcx='same ValueCollection',rdx='same List backing array',r8d=0,r9='actual selected CopyTo MethodInfo'),
        actualOwnValueCollectionCopyToCallbackRequired=bool(count),elementBytes=16,
        sizeFieldOffset=24,sizeAfter=count,versionFieldOffset=28,versionIncrementMod32=1,
        savedXmm6Home=[112,128],fullXmm6SavedAndRestored=True,frameBytes=184,callShadow=[0,32],entryRspRestored=True,
        restoredNonvolatiles=['rbx','rsi','rdi','r12','r13','r14','r15','xmm6'],arrayGrowthAndSelfInsertProved=False,
        liveSnapshotOrCallbackSelectionObserved=False)


def values_count(regions,entry):
    g=BytesPath(regions,entry);g.take('4053','4883ec20','488b5910','4885db');g.branch('74',False,1)
    g.take('488b4220','488b88c0000000','488b4118','4883782000');g.branch('0f84',False)
    g.take('8b4320','2b4328','4883c420','5b','c3')
    return dict(selectedBytes=g.seen,dictionaryFieldOffset=16,countFieldOffset=32,freeCountFieldOffset=40,
        returns='same dictionary count minus freeCount',dictionaryNonnullAndOwnContextReadyRequired=True,
        frameBytes=40,entryRspRestored=True,restoredNonvolatiles=['rbx'],nonframeWrites=0)


def values_copy_to(regions,entry,*,active=(True,)):
    need('finite-opaque16-copy-pattern',type(active)in(tuple,list)and len(active)<=4096 and all(type(x)is bool for x in active))
    g=BytesPath(regions,entry);writes=[];barrier=None
    g.take('48895c2418','55','56','4156','4883ec20','4963d8','4d8bf1','488bea','488bf1','4885d2');g.branch('0f84',False)
    g.take('48897c2440','4c897c2448','85db');g.branch('0f88',False)
    g.take('4885ed');g.branch('0f84',False);g.take('3b5d18');g.branch('0f8f',False)
    g.take('488b7e10','4885ff');g.branch('0f84',False)
    g.take('498b4620','488b88c0000000','488b4118','4883782000');g.branch('0f84',False)
    g.take('8b4f20','8b4518','2b4f28','2bc3','3bc1');g.branch('0f8c',False)
    g.take('488b4e10','4885c9');g.branch('0f84',False)
    g.take('488b4610','48634920','4c8b7018','85c9');g.branch('7e',len(active)==0,1)
    if active:
        g.take('4c8bf9','498d4630','0f1f4000','0f1f840000000000','4533c9','4c8bd0','418bf9','488bf3','448bdb','4d85f6');g.branch('74',False,1);head=g.at
        for i,live in enumerate(active):
            need('same-ValueCollection-physical-entry-head',g.at==head)
            g.take('453b4e18');g.branch('73',False,1)
            g.take('8378f000');g.branch('7c',not live,1)
            if live:
                g.take('4963cb','488bc6','41ffc3','48ffc6','3b5d18');g.branch('73',False,1)
                g.take('410f1002','4883c102','4883c002','4803c0','48c1e104','4803cd','0f1144c500')
                site=g.at;target=g.relative('e8');need('same-copy-output-barrier',barrier is None or barrier['targetVa']==target)
                barrier=dict(instructionVa=site,targetVa=target);writes.append(i)
            g.take('4983c220','41ffc1','48ffc7','498bc2','493bff');g.branch('7c',i+1<len(active),1)
            if i+1<len(active):g.take('418bdb');g.jump('eb',1)
    g.take('4c8b7c2448','488b7c2440','488b5c2450','4883c420','415e','5e','5d','c3')
    return dict(selectedBytes=g.seen,physicalEntryCount=len(active),activePattern=list(active),activeCount=sum(active),
        dictionaryFieldOffset=16,countFieldOffset=32,freeCountFieldOffset=40,entriesFieldOffset=24,
        entryBytes=32,entryHashOffset=0,entryValueOffset=16,negativeHashSlotsSkipped=True,
        outputStartIndex=0,outputElementBytes=16,outputElementToPhysicalEntry=writes,
        everyOpaque16BitPreserved=True,arrayDataOffset=32,outputCapacityAtLeastActiveCountRequired=True,
        sameDictionaryCountEntriesAndVersionStableRequired=True,sourceDoesNotCheckDictionaryVersion=True,
        outputBarrier=barrier,selectedDisabledBarrierEffectsRequired=bool(writes),
        sourceEntryArrayIndexGuard=True,sourceDestinationArrayIndexGuard=True,
        invariant='physical index i advances once per entry; output index advances once iff hash is nonnegative; value source=entries+32+32*i+16; destination=array+32+16*outputIndex',
        inductionPhysicalEntryBound=4096,frameBytes=56,callShadow=[0,32],callerProvidedHomeSpaceUsed=[[8,24]],
        entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','r14','r15'],liveDictionaryOrListenerObserved=False)


def interface_effect_dispatch(regions,entry,*,kind='count',interface_steps=0):
    need('finite-selected-interface-effect',kind in('count','dispose')and type(interface_steps)is int and 0<=interface_steps<=64)
    g=BytesPath(regions,entry)
    g.take('48895c2408','48896c2410','4889742418','48897c2420','4156','4883ec30','498b30',
        '498bf8'if kind=='count'else'498bd8','0fb7e9','488bda'if kind=='count'else'488bfa','488bce')
    prepare=g.relative('e8');g.take('440fb78630010000','4533f6','410fb7c6','66453bf0');g.branch('73',False,1)
    g.take('488b96b0000000');head=g.at
    for i in range(interface_steps+1):
        need('same-effect-interface-head',g.at==head)
        g.take('0fb7c8','4803c9','48391cca'if kind=='count'else'48393cca');g.branch('74',i==interface_steps,1)
        if i<interface_steps:g.take('66ffc0','66413bc0');g.branch('72',True,1)
    g.take('0fb7d0','488b86b0000000','4803d2','8b44d008','03c5','4898','4883c014','48c1e004','4803c6','4c8b00',
        '488b5008'if kind=='count'else'488b7808')
    excluded=[]
    edges=[('74',False,1),('74',False,1),('0f84',False,4)]if kind=='count'else[('0f85',True,4),('74',False,1),('0f84',False,4)]
    for opcode,taken,width in edges:
        excluded.append(g.relative('488d05'));g.take('4c3bc0');g.branch(opcode,taken,width)
    if kind=='count':g.take('488bcf');site=g.at;g.take('41ffd0','8bd8','488b6c2448','8bc3')
    else:g.take('488bd7','488bcb');site=g.at;g.take('41ffd0')
    g.take('488b5c2440')
    if kind=='dispose':g.take('488b6c2448')
    g.take('488b742450','488b7c2458','4883c430','415e','c3')
    return dict(selectedBytes=g.seen,kind=kind,preparationTargetVa=prepare,interfaceSlot=0,
        interfaceMisses=interface_steps,excludedInlineTargets=excluded,selectedCallInstructionVa=site,
        callbackArguments=dict(rcx='same actual object',rdx='same selected MethodInfo'),
        result='same selected callback Int32'if kind=='count'else'void',
        actualSelectedCallbackAndMethodInfoRequired=True,frameBytes=56,callShadow=[0,32],entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r14'],runtimeCallbackSelectionObserved=False)


def pooled_list_dispose(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','488b7128','488bda','488bf9','4885f6');g.branch('74',False,1)
    g.take('488b4220','488b90c0000000','488b4218','4883782000');g.branch('0f84',False)
    g.take('488b4320','488bd7','488bce','4c8b80c0000000','4d8b4018','488b5c2430','488b742438','4883c420','5f')
    target=g.relative('e9')
    return dict(selectedBytes=g.seen,objectPoolFieldOffset=40,objectPoolRequiredNonnull=True,recycleTargetVa=target,
        recycleContextSlotOffset=24,recycleArguments=dict(rcx='same stored pool',rdx='same list',r8='own selected Recycle MethodInfo'),
        frameBytes=40,entryRspRestored=True,restoredNonvolatiles=['rbx','rsi','rdi'],ownContextReadyRequired=True)


def release_invoke(regions,entry):
    """The selected non-inline Action<T> branch, retaining its actual target/MI."""
    g=BytesPath(regions,entry);g.take('4053','57','4883ec38','488b4118','488bda','488b7928')
    excluded=[g.relative('488d15')];g.take('488b4940','483bc2');g.branch('75',True,1)
    excluded.append(g.relative('488d15'));g.take('483bc2');g.branch('0f85',True)
    excluded.append(g.relative('488d15'));g.take('483bc2');g.branch('75',True,1)
    g.take('4c8bc7','488bd3','4883c438','5f','5b');site=g.at;g.take('48ffe0')
    return dict(selectedBytes=g.seen,excludedInlineTargets=excluded,selectedCallInstructionVa=site,
        callbackTargetFieldOffset=24,callbackMethodInfoFieldOffset=40,callbackReceiverFieldOffset=64,
        callbackArguments=dict(rcx='same delegate stored receiver',rdx='same released list',r8='same delegate stored MethodInfo'),
        actualSelectedCallbackAndMethodInfoRequired=True,frameBytes=72,callShadow=[0,32],entryRspRestored=True,
        restoredNonvolatiles=['rbx','rdi'],runtimeCallbackSelectionObserved=False)


def release_lambda(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','498bd8','488bfa','4885d2');g.branch('74',False,1)
    g.take('498b4020','488b88c0000000','488b4120','4883782000');g.branch('0f84',False)
    g.take('488b4320','488bcf','488b90c0000000','488b5220','488b5c2430','4883c420','5f');target=g.relative('e9')
    return dict(selectedBytes=g.seen,clearTargetVa=target,clearContextSlotOffset=32,
        clearArguments=dict(rcx='same released list',rdx='same selected Clear MethodInfo'),
        inputListRequiredNonnull=True,ownContextReadyRequired=True,frameBytes=40,callShadow=[0,32],
        entryRspRestored=True,restoredNonvolatiles=['rbx','rdi'])


def recycle(regions,entry,*,release=True):
    need('recycle-release-choice',type(release)is bool);g=BytesPath(regions,entry);flags=[];classes=[]
    g.take('4053','55','57','4883ec20');flags.append(g.relative('803d')+1);g.take('00','498bd8','488bea','488bf9');g.branch('75',True,1)
    classes.append(g.relative('488b0d'));g.take('83b9e000000000');g.branch('75',True,1)
    flags.append(g.relative('803d')+1);g.take('00');g.branch('75',True,1)
    classes.append(g.relative('488b0d'));g.take('83b9e000000000');g.branch('75',True,1)
    classes.append(g.relative('488b05'));g.take('488b88b8000000','48896910');collector=g.relative('833d')+1;g.take('00');g.branch('74',True,1)
    g.take('4889742448','488b4710','4885c0');g.branch('0f84',False)
    g.take('48837f2000','8b7018');g.branch('74',not release,1);call=None
    if release:
        g.take('488b4320','4c89742450','4c8b7720','488b90c0000000','488b82a0000000','4883782000');g.branch('75',True,1)
        g.take('488b4320','488bd5','498bce','4c8b80c0000000','4d8b80a0000000');at=g.at;target=g.relative('e8');call=dict(instructionVa=at,targetVa=target)
        g.take('4c8b742450')
    g.take('3b7730');g.branch('0f8c',True)
    g.take('488b4f10','4885c9');g.branch('74',False,1);usage=g.relative('4c8b05');g.take('488bd5');at=g.at;push=g.relative('e8')
    g.take('488b742448','b001','4883c420','5f','5d','5b','c3')
    need('same-recycle-static-class',len(set(classes))==1)
    return dict(selectedBytes=g.seen,readyFlagCells=flags,staticClassCellVa=classes[0],collectorCellVa=collector,
        collectionDisabledRequired=True,staticCurrentlyRecyclingFieldOffset=16,staticWrite='same released list reference',
        stackFieldOffset=16,onReleaseFieldOffset=32,maxCapacityFieldOffset=48,sparePoolCapacityRequired=True,
        releaseAction=call,releaseActionRequiredNonnull=release,releaseContextSlotOffset=160,
        stackPush=dict(instructionVa=at,targetVa=push,methodInfoCellVa=usage),returns=True,
        frameBytes=56,callShadow=[0,32],callerProvidedHomeSpaceUsed=[[16,32]],entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rdi','rsi']+(['r14']if release else[]))


def stack_push(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2410','48896c2418','56','57','4156','4883ec20','488b7110','498be8','48637918','4c8bf2','488bd9','4885f6');g.branch('0f84',False)
    g.take('3b7e18');g.branch('72',True,1);collector=g.relative('833d')+1;g.take('00','4c8974fe20');g.branch('74',True,1)
    g.take('ff431c','8d4701','894318','488b5c2448','488b6c2450','4883c420','415e','5f','5e','c3')
    return dict(selectedBytes=g.seen,collectorCellVa=collector,collectionDisabledRequired=True,
        arrayFieldOffset=16,sizeFieldOffset=24,versionFieldOffset=28,arrayDataOffset=32,elementBytes=8,
        spareArrayCapacityRequired=True,write='same released list at array+32+8*oldSize',sizeDelta=1,versionDelta=1,
        frameBytes=56,entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','r14'])


def disabled_barrier(regions,entry):
    g=BytesPath(regions,entry);cell=g.relative('833d')+1;g.take('00','4c8bc1');g.branch('74',True,1);g.take('c3')
    return dict(selectedBytes=g.seen,collectorCellVa=cell,collectionDisabledRequired=True,
        nonframeWrites=0,effectCalls=0,stackAndNonvolatilesUntouched=True)


def rep_zero(regions,entry):
    g=BytesPath(regions,entry);g.take('57','8bc2','488bf9','498bc8','f3aa','498bc1','5f','c3')
    return dict(selectedBytes=g.seen,fillByteRequired=0,countInR8Required=True,
        zeroedByteRange='[destination,destination+count)',returnSameDestinationInRax=True,
        directionFlagClearRequired=True,entryRspRestored=True,restoredNonvolatiles=['rdi'],effectCalls=0)


def rep_dispatch(regions,entry,*,sse=False):
    need('literal-REP-CPU-route',type(sse)is bool);g=BytesPath(regions,entry)
    g.take('488bc1','4c8bc9');base=g.relative('4c8d15')
    g.take('0fb6d2','49bb0101010101010101','4c0fafda','66490f6ec3','4983f80f');g.branch('0f87',True)
    g.take('660f6cc0','4983f820');g.branch('77',True,1)
    cpu=g.relative('833d')+1;g.take('03');g.branch('0f82',sse)
    first=g.relative('4c3b05');g.branch('76',False,1);second=None
    if not sse:second=g.relative('4c3b05');g.branch('77',False,1)
    flag=g.relative('f605')+1;g.take('02');target=g.relative('0f85')
    return dict(selectedBytes=g.seen,imageBaseVa=base,cpuLevelCellVa=cpu,sseCPUSelected=sse,
        firstThresholdCellVa=first,secondThresholdCellVa=second,repFlagCellVa=flag,repFlagMask=2,
        repFlagSetRequired=True,countGreaterThan32Required=True,repTargetVa=target,
        repArguments=dict(rcx='same destination',edx=0,r8='same byte count',r9='same destination'),
        stackAndNonvolatilesUntouched=True)


def zero_fill(regions,entry,*,image_base,count,alignment=0,mode='sse'):
    """Selected SSE2/AVX2 fill paths, including zero to65536 bytes in16-byte units.

    Jump-table data must be independently authenticated alongside the code.
    CPU/threshold dispatch is a condition. Each normal selected store interval
    is checked to stay in the destination and their union covers it exactly.
    """
    need('finite-zero-vector-domain',type(count)is int and 16<=count<=65536 and count%16==0
        and type(alignment)is int and 0<=alignment<32 and mode in('sse','avx','nt'))
    g=BytesPath(regions,entry);writes=[];flags={};position=0;remaining=count
    def store(at,width):
        need('zero-write-in-destination',0<=at and at+width<=count);writes.append([at,at+width])
    g.take('488bc1','4c8bc9');need('zero-own-image-base',g.relative('4c8d15')==image_base)
    g.take('0fb6d2','49bb0101010101010101','4c0fafda','66490f6ec3','4983f80f');g.branch('0f87',True)
    g.take('660f6cc0','4983f820');g.branch('77',count>32,1)
    table=None;index=None;selected='small'
    if count<=32:
        g.take('f30f7f01','f3420f7f4401f0','c3');store(0,16);store(count-16,16)
    else:
        flags['cpuLevelCellVa']=g.relative('833d')+1;g.take('03');g.branch('0f82',mode=='sse')
        if mode=='sse':
            flags['thresholdCellVa']=g.relative('4c3b05');g.branch('76',True,1)
            g.take('4c8bc9','4983e10f','4983e910','492bc9','492bd1','4d03c1')
            advance=16-alignment%16;position=advance;remaining=count-advance
            g.take('4981f880000000');g.branch('76',remaining<=128,1)
            if remaining>128:
                g.take('66666666660f1f840000000000');head=g.at
                while True:
                    need('same-zero-SSE-loop-head',g.at==head)
                    g.take('660f7f01','660f7f4110','660f7f4120','660f7f4130','660f7f4140','660f7f4150','660f7f4160','660f7f4170')
                    for x in range(0,128,16):store(position+x,16)
                    g.take('4881c180000000','4981e880000000','4981f880000000');position+=128;remaining-=128;g.branch('73',remaining>=128,1)
                    if remaining<128:break
            g.take('4d8d480f','4983e1f0','4d8bd9','49c1eb04','478b9c9a');table=int.from_bytes(g.read(4),'little');index=(remaining+15)//16
            g.take('4d03da','41ffe3');after=g.at;g.at=image_base+table+index*4;target=image_base+int.from_bytes(g.read(4),'little');g.at=target
            round_bytes=(remaining+15)&~15
            offsets=[-128,-112,-96,-80,-64,-48,-32]
            enc=['f3420f7f440980','f3420f7f440990','f3420f7f4409a0','f3420f7f4409b0','f3420f7f4409c0','f3420f7f4409d0','f3420f7f4409e0']
            starts=[]
            for opcode in enc:starts.append(bytes.fromhex(opcode))
            while bytes(g.bytes.get(g.at+i,0)for i in range(7))in starts:
                b=bytes(g.bytes[g.at+i]for i in range(7));k=starts.index(b);g.take(enc[k]);store(position+round_bytes+offsets[k],16)
            if bytes(g.bytes.get(g.at+i,0)for i in range(7))==bytes.fromhex('f3420f7f4401f0'):
                g.take('f3420f7f4401f0');store(position+remaining-16,16)
            g.take('f30f7f00','c3');store(0,16);selected='sse2'
        else:
            flags['firstThresholdCellVa']=g.relative('4c3b05');g.branch('76',mode=='avx',1)
            if mode=='nt':flags['secondThresholdCellVa']=g.relative('4c3b05');g.branch('77',True,1)
            g.take('c4e37d18c001','4c8bc9','4983e11f','4983e920','492bc9','492bd1','4d03c1')
            advance=32-alignment;position=advance;remaining=count-advance
            g.take('4981f800010000');g.branch('76',remaining<=256,1)
            if remaining>256:
                flags['nonTemporalThresholdCellVa']=g.relative('4c3b05');g.branch('0f87',mode=='nt')
                if mode=='avx':g.take('6666666666660f1f840000000000')
                else:need('reachable-nonTemporal-zero-loop',remaining>256)
                head=g.at
                while True:
                    need('same-zero-AVX-loop-head',g.at==head)
                    prefix='c5fde7'if mode=='nt'else'c5fd7f'
                    g.take(prefix+'01',prefix+'4120',prefix+'4140',prefix+'4160',prefix+'8180000000',prefix+'81a0000000',prefix+'81c0000000',prefix+'81e0000000')
                    for x in range(0,256,32):store(position+x,32)
                    g.take('4881c100010000','4981e800010000','4981f800010000');position+=256;remaining-=256;g.branch('73',remaining>=256,1)
                    if remaining<256:break
            else:need('nonTemporal-mode-must-reach-own-loop',mode=='avx')
            g.take('4d8d481f','4983e1e0','4d8bd9','49c1eb05','478b9c9a');table=int.from_bytes(g.read(4),'little');index=(remaining+31)//32
            g.take('4d03da','41ffe3');g.at=image_base+table+index*4;target=image_base+int.from_bytes(g.read(4),'little');g.at=target
            rounded=(remaining+31)&~31;tail='c4a17de7'if mode=='nt'else'c4a17e7f'
            offsets=[-256,-224,-192,-160,-128,-96,-64]
            enc=[tail+'840900ffffff',tail+'840920ffffff',tail+'840940ffffff',tail+'840960ffffff',tail+'440980',tail+'4409a0',tail+'4409c0']
            while True:
                found=[(k,b)for k,b in enumerate(enc)if bytes(g.bytes.get(g.at+i,0)for i in range(len(bytes.fromhex(b))))==bytes.fromhex(b)]
                if not found:break
                k,b=found[0];g.take(b);store(position+rounded+offsets[k],32)
            if bytes(g.bytes.get(g.at+i,0)for i in range(7))==bytes.fromhex('c4a17e7f4401e0'):
                g.take('c4a17e7f4401e0');store(position+remaining-32,32)
            g.take('c5fe7f00');store(0,32)
            if mode=='nt':g.take('0faef8')
            g.take('c5f877','c3');selected='avx2-nonTemporal'if mode=='nt'else'avx2'
    union=[]
    for lo,hi in sorted(writes):
        if union and lo<=union[-1][1]:union[-1][1]=max(union[-1][1],hi)
        else:union.append([lo,hi])
    need('exact-zero-destination-coverage',union==[[0,count]])
    return dict(selectedBytes=g.seen,count=count,alignmentModulo32=alignment,mode=selected,dispatchCells=flags,
        fillByteRequired=0,zeroedByteRanges=union,allStoresInsideDestination=True,returnSameDestinationInRax=True,
        selectedJumpTableRva=table,selectedJumpTableIndex=index,normalCPUAndThresholdSelectionRequired=True,
        stackAndNonvolatilesUntouched=True,effectCalls=0,volatileVectorRegistersOnly=True,
        nonTemporalStoresFenced=selected=='avx2-nonTemporal',otherDispatchPathsProved=False)

"""Actual cached Bundle proxy key and default Int64/reference lookup paths."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check,condition):
    if not condition:raise ValueError('patrolBundleCache.'+check)


def caller(regions,entry):
    g=BytesPath(regions,entry);g.take('4c89442418','53','55','57','4156','4881ecb8000000')
    root=g.relative('488b05');g.take('4c8bf1','498bd9','498be8','488bfa','488b4878','4885c9');g.branch('74',True,1)
    collector=g.relative('833d')+1;g.take('00','0f57c0','4889b424e0000000','4c89a424e8000000');g.relative('4c8d25')
    g.take('4c89bc24b0000000','0f11442460','49c70100000000','0f11442470','0f11842480000000','0f11842490000000','0f118424a0000000');g.branch('74',True,1)
    seedSite=g.at;seedClass=g.relative('488b0d');g.take('488b37','83b9e000000000');g.branch('75',True,1)
    g.take('4533c0','4c89ac24f8000000','488bd5','488bce');at=g.at;key=g.relative('e8')
    g.take('498b4e28','4c8bf8','4889442450','4885c9');g.branch('0f84',False)
    requestSite=g.at;requestCell=g.relative('4c8b0d');g.take('4c8bc3','488bd0');lookupSite=g.at;lookup=g.relative('e8')
    g.take('84c0');g.branch('0f85',True)
    configSite=g.at;config=g.relative('488b0d');g.take('83b9e000000000');g.branch('75',True,1)
    g.take('488b81b8000000','80781400');g.branch('74',True,1)
    g.take('4c8bac24f8000000','4c8ba424e8000000','488bb424e0000000','4c8bbc24b0000000','4881c4b8000000','415e','5f','5d','5b','c3')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,collectorFlagVa=collector,
        keyCall=dict(instructionVa=at,targetVa=key),lookupCall=dict(instructionVa=lookupSite,targetVa=lookup),
        typedSites=dict(keyClass=dict(instructionVa=seedSite,cellVa=seedClass),lookup=dict(instructionVa=requestSite,cellVa=requestCell),config=dict(instructionVa=configSite,cellVa=config)),
        assetInfoKeyOffset=0,assetInfoKeyBytes=8,assetPoolFieldOffset=40,outputReferenceInitiallyZeroed=True,
        sameOutputReferenceAddressUsedForLookup=True,debugConfigStaticByteOffset=20,debugConfigRequiredFalse=True,
        effect='write initial null, then same cached proxy reference selected by unchanged computed key; no creation call on hit',
        frameBytes=216,entryRspRestored=True,allNonvolatilesRestored=True,liveCacheContentsObserved=False)


def key(regions,entry):
    g=BytesPath(regions,entry);calls=[];classes=[];flags=[]
    def cls(opcode='488b0d'):classes.append(g.relative(opcode))
    def ready():g.take('83b9e000000000');g.branch('0f84',False)
    def call(role):
        at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target))
    def flag():flags.append(g.relative('803d')+1);g.take('00');g.branch('0f84',False)
    g.take('48895c2418','56','4883ec20');root=g.relative('488b05')
    g.take('488bf1','488bda','488b4878','4885c9');g.branch('0f85',False)
    cls();g.take('48896c2430','48897c2438');ready();typeSite=g.at;typeCell=g.relative('488b0d')
    g.take('4883793800');g.branch('0f84',False)
    g.take('488bfe','48c1ff20','33fe','4885db');g.branch('0f84',False)
    g.take('b902000000','488bd3');call('typeHash');g.take('8be8');cls();ready();cls();ready();cls('488b05')
    g.take('488b88b8000000','8b19','81c3b9675616');flag();cls()
    g.take('69c7c3514d3d','2bd8');ready()
    g.take('8bc3','c1e311','c1e80f','0bc3','69d82febd427');flag();cls()
    g.take('69c5c3514d3d','2bd8');ready();g.take('8bc3','c1e311','c1e80f','0bc3','69c82febd427');call('mixFinal')
    secondSite=g.at;secondCell=g.relative('488b0d');g.take('4863e8','4883793800');g.branch('0f84',False)
    cls();g.take('488bfe','48c1ff20','33fe');ready();cls();ready();cls('488b05')
    g.take('488b98b8000000','8b1b','81c3b5675616');flag();cls()
    g.take('69c7c3514d3d','488b7c2438','2bd8');ready()
    g.take('8bc3','c1e311','c1e80f','0bc3','69c82febd427');call('mixFinal')
    g.take('48c1e520','8bc0','480bc5','488b6c2430','488b5c2440','4883c420','5e','c3')
    need('same-hash-code-class-and-ready-flags',len(set(classes))==len(set(flags))==1)
    return dict(selectedBytes=g.seen,calls=calls,replacementRootCellVa=root,hashCodeClassCellVa=classes[0],metadataReadyFlagVa=flags[0],
        typeContextSites=[dict(instructionVa=typeSite,cellVa=typeCell),dict(instructionVa=secondSite,cellVa=secondCell)],
        seedStaticOffset=0,typeArgumentRequiredNonnull=True,longHash='low32(value) XOR high32(value)',
        result='UInt64(MixFinal(QueueRound(QueueRound(seed+0x165667b9,longHash),actualTypeHash)))<<32 | MixFinal(QueueRound(seed+0x165667b5,longHash))',
        queueRound='ROL32(accumulator-input*0x3d4d51c3,17)*0x27d4eb2f modulo2^32',
        sameStableSeedRequired=True,liveSeedOrTypeHashObserved=False,entryRspRestored=True,allNonvolatilesRestored=True)


def mix_final(regions,entry):
    g=BytesPath(regions,entry);g.take('8bc1','c1e80f','33c1','69c877caeb85','8bc1','c1e80d','33c1','69c83daeb2c2','8bc1','c1e810','33c1','c3')
    return dict(selectedBytes=g.seen,effect='x^=x>>15; x*=0x85ebca77; x^=x>>13; x*=0xc2b2ae3d; x^=x>>16; all UInt32',entryRspRestored=True)


def try_get(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2408','48896c2418','4889742420','57','4883ec20','498b4120','498bf9','498bd8','488bf2','488be9',
        '4c8b90c0000000','498b82b0000000','4883782000');g.branch('75',True,1)
    g.take('488b4720','488bd6','488bcd','4c8b80c0000000','4d8b80b0000000');at=g.at;find=g.relative('e8')
    g.take('4863f0','85c0');g.branch('79',True,1);g.take('488b7d18','4885ff');g.branch('74',False,1)
    g.take('3b7718');g.branch('73',False,1);collector=g.relative('833d')+1
    g.take('00','488d0c76','488d04cf','488b44cf30','488903');g.branch('74',True,1)
    g.take('b001','488b5c2430','488b6c2440','488b742448','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,findCall=dict(instructionVa=at,targetVa=find),findMethodInfoClassSlot=22,
        collectorFlagVa=collector,slotStride=24,slotValueOffset=16,arrayDataOffset=32,
        effect='store same selected eight-byte reference from entries[index].value to unchanged caller outref; return true',
        entryRspRestored=True,allNonvolatilesRestored=True)


def find(regions,entry,*,misses=()):
    need('bounded-chain-witness',type(misses)is tuple and len(misses)<=3 and all(x in('hash','key')for x in misses))
    g=BytesPath(regions,entry);calls=[]
    def call(role):
        at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target))
    g.take('48895c2410','48896c2418','4889742420','57','4154','4155','4156','4157','4883ec30','4d8be8','4c8bfa','488b6910',
        'bbffffffff','488b7118','4885ed');g.branch('0f84',False);g.take('4c8b7130','4d85f6');g.branch('0f85',False)
    g.take('488bfa','48c1ff20','4133ff','0fbaf71f','8bc7','99','f77d18','3b5518');g.branch('0f83',False)
    g.take('0f1f4000','66660f1f840000000000','4863da','4533e4','8b5c9d20','ffcb','4885f6');g.branch('0f84',False);head=g.at;failed=[]
    for i in range(len(misses)+1):
        start=len(g.seen);kind=misses[i]if i<len(misses)else'hit'
        g.take('3b5e18');g.branch('0f83',False);g.take('4863c3','488d0c40','397cce20');g.branch('0f85',kind=='hash')
        if kind!='hash':
            g.take('498b4520','488b88c0000000','488b6910','488b4d20');call('readyContext')
            g.take('33d2','488b88c0000000');call('indexedContext')
            g.take('488b88b8000000','4c8b31','f0830c2400','4d85f6');g.branch('0f84',False)
            g.take('3b5e18');g.branch('0f83',False);g.take('4863c3','488d0c40','488b6cce28','4d85f6');g.branch('74',False,1)
            g.take('498b0e');call('prepareComparer')
            g.take('498b06','4c8b90c0010000','4c8b88c8010000');marker=g.relative('488d05')
            g.take('4c3bd0');g.branch('75',False,1);g.take('493bef','0f94c0','84c0');g.branch('74',kind=='key',1)
        if kind=='hit':break
        g.take('3b5e18');g.branch('73',False,1);g.take('4863c3','488d1c40','8b5cde24','443b6618');g.branch('0f8d',False)
        g.take('41ffc4');back=g.relative('e9');need('same-entry-chain-loop',back==head);g.at=back;failed.append(g.seen[start:])
    g.take('488b6c2470','8bc3','488b5c2468','488b742478','4883c430','415f','415e','415d','415c','5f','c3')
    return dict(selectedBytes=g.seen,calls=calls,selectedEqualityCallbackVa=marker,misses=list(misses),failedProbeBodies=failed,
        keyBytes=8,bucketsOffset=16,entriesOffset=24,comparerOffset=48,initialComparerRequiredNull=True,
        slotStride=24,slotHashOffset=0,slotNextOffset=4,slotKeyOffset=8,slotValueOffset=16,
        effect='use (low32(key)^high32(key))&0x7fffffff bucket; first matching full Int64 returns unchanged slot index',
        positiveBucketCountAndValidAcyclicChainRequired=True,chainCounterGuardUsesEntriesLength=True,
        liveComparerOrContentsObserved=False,entryRspRestored=True,allNonvolatilesRestored=True)

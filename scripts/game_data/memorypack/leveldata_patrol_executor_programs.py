"""Byte-exact selected executor paths; virtual selections remain explicit."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check,condition):
    if not condition:raise ValueError('patrolExecutor.'+check)


def call(g,calls,role):
    at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target


def cell(g,sites,role,prefix,tail=0):
    at=g.at;target=g.relative(prefix)+tail
    need('one-site:'+role,role not in sites)
    sites[role]=dict(instructionVa=at,cellVa=target);return target


def result(g,calls,sites,**kw):return dict(selectedBytes=g.seen,calls=calls,typedSites=sites,**kw)


def try_invoke(regions,entry,*,start_mode="zero",force=False):
    need("literal-force-mode",type(force)is bool)
    need("finite-start-node-mode",start_mode in("zero","node-uid-null","node-uid-empty","node-uid-unregistered"))
    """Header hit, constant true validation, spare containers and finite node UID paths.

    Every direct call is a separately required source join. Indirect calls are
    exact class slots with their own receiver/context conditions. No instruction
    pointer or native hash is embedded in this algorithm.
    """
    g=BytesPath(regions,entry);calls=[];sites={}
    g.take('488bc4','48895810','48897018','48894808','57','4154','4155','4156')
    g.take('4157','4881ecc0000000','0f2970c8','4d8be1','450fb6e8','4c8bfa','488bf9')
    cell(g,sites,'replacementRoot','488b05')
    g.take('488b4828','4885c9')
    g.branch('74',True,1)  # 62
    g.take('33f6','4889742438','0f57c0','0f11842490000000','0f57c9','0f118c2480000000','418831','4038b790000000')
    g.branch('0f84',False)  # 158
    g.take('40387768')
    g.branch('0f85',False)  # 168
    g.take('488b5f40','4885db')
    g.branch('0f84',False)  # 181
    g.take('ff431c','897318','33d2','488bcf')
    call(g,calls,'getActionMap')
    g.take('448b7718','4885c0')
    g.branch('0f84',False)  # 210
    g.take('4533c9','4c8d442438','418bd6','488bc8')
    call(g,calls,'getHeader')
    g.take('84c0')
    g.branch('0f85',True)  # 237
    g.take('488b5c2438','4885db')
    g.branch('0f84',False)  # 596
    g.take('0f107328')
    cell(g,sites,'implicitInfo','4c8b05')
    g.take('488bd7','488d4c2460')
    call(g,calls,'implicit')
    g.take('0f28442460','660f7f442460','660f7f742450')
    cell(g,sites,'inequalityInfo','4c8b05')
    g.take('488d542460','488d4c2450')
    call(g,calls,'inequality')
    g.take('84c0')
    g.branch('74',False,1)  # 667
    g.take('488b5c2438','4885db')
    g.branch('0f84',False)  # 677
    g.take('4533c0','488bd7','488bcb')
    call(g,calls,'setup')
    g.take('488b5c2438','4885db')
    g.branch('0f84',False)  # 705
    g.take('33d2','488bcb')
    call(g,calls,'clean')
    g.take('4533c0','498bd7','488bcf')
    call(g,calls,'assign')
    cell(g,sites,'site3','488b0d')
    g.take('39b1e0000000')
    g.branch('75',True,1)  # 748
    g.take('4533c0','488bd7','488d4c2460')
    call(g,calls,'pushExecutor')
    g.take('0f1000','0f11842490000000','4889742470','488d842490000000','4889442478')
    cell(g,sites,'site4','488b05')
    g.take('488b4828','4885c9')
    g.branch('74',True,1)  # 814
    g.take('0f104720','0f11442440')
    cell(g,sites,'site5','488b05')
    g.take('488b4020','f6803801000001')
    g.branch('75',True,1)  # 875
    g.take('488b90c0000000','488b5208','488d4c2440')
    call(g,calls,'valid')
    g.take('488bde','84c0','480f455c2440')
    cell(g,sites,'site6','488b05')
    g.take('488b5010','4885d2')
    g.branch('74',True,1)  # 931
    g.take('4885db')
    g.branch('74',False,1)  # 973
    g.take('488b0b')
    call(g,calls,'prepare')
    g.take('488b13','488b82f0010000','488b92f8010000','488bcb','ffd0','33c9')
    call(g,calls,'getScopeStack')
    g.take('4885c0')
    g.branch('0f84',False)  # 1015
    cell(g,sites,'site7','4c8b0d')
    g.take('4c8bc3','488bd0','488d4c2460')
    call(g,calls,'scopePush')
    g.take('0f28442460')
    g.jump('eb',1)
    g.take('660f7f842480000000','4889742450','488d842480000000','4889442458','488b5c2438','4c8b7730','4885db')
    g.branch('0f84',False)  # 1093
    cell(g,sites,'site8','488b05')
    g.take('488b4828','4885c9')
    g.branch('74',True,1)  # 1113
    g.take('488b4808','4885c9')
    g.branch('74',True,1)  # 1187
    g.take('837b4c01')
    g.branch('74',False,1)  # 1222
    g.take('c7434c01000000','ff4348','8bc6')
    g.jump('eb',1)
    g.take('4584ed')
    g.branch('75',force,1)
    if not force:g.take('83f802');g.branch('75',True,1)
    g.take('488b0b')
    call(g,calls,'prepare')
    g.take('488b13','488b8240020000','488b9248020000','488bcb','ffd0','4d85f6')
    g.branch('0f84',False)  # 1337
    cell(g,sites,'eventKeySet','4c8b0d')
    g.take('4c8bc0')
    cell(g,sites,'objectKey','488b15')
    g.take('498bce')
    call(g,calls,'eventKeySet')
    g.take('4d8bc6','488bd3')
    call(g,calls,'headerProcess')
    g.take('84c0')
    g.branch('0f84',False)  # 1381
    g.take('488b4378','4885c0')
    g.branch('0f84',False)  # 1394
    g.take('837810ff')
    g.branch('74',False,1)  # 1404
    g.take('837810fe')
    g.branch('75',True,1)  # 1410
    g.take('4c8bf0')
    cell(g,sites,'site11','488b1d')
    g.take('48837b3800')
    g.branch('75',True,1)  # 1437
    g.take('c644243000','488b4338','488b4808','4883792000')
    g.branch('75',True,1)  # 1465
    g.take('41837e10ff')
    g.branch('74',False,1)  # 1474
    g.take('41837e10fe')
    g.branch('75',True,1)  # 1481
    g.take('4c8b4b38','4d8b4910','41b001','488d542430','498bce')
    call(g,calls,'paramTryGet')
    g.take('84c0')
    g.branch('74',False,1)  # 1516
    g.take('807c243000')
    g.branch('74',False,1)  # 1523
    cell(g,sites,'site12','488b15')
    g.take('488d8c2480000000')
    call(g,calls,'scopeDispose')
    g.take('90')
    cell(g,sites,'site13','488b15')
    g.take('488d8c2490000000')
    call(g,calls,'scopeDispose')
    g.jump('e9')
    g.take('488b5f40','488b442438','4885c0')
    g.branch('0f84',False)  # 1753
    g.take('448b7860','4885db')
    g.branch('0f84',False)  # 1766
    cell(g,sites,'site14','4c8b35')
    g.take('ff431c','488b5310','48634b18','4885d2')
    g.branch('0f84',False)  # 1793
    g.take('3b4a18')
    g.branch('72',True,1)  # 1802
    g.take('8d4101','894318','3b4a18')
    g.branch('0f83',False)  # 1880
    g.take('44897c8a20','66c747680100','66c787800000000000','89776c','897778','66c7477c0000','48897770')
    cell(g,sites,'site15','488d1d')
    cell(g,sites,'site16','833d',tail=1)
    g.take('00')
    g.branch('74',True,1)  # 1936
    g.take('488b4f38','4885c9')
    g.branch('0f84',False)  # 2018
    cell(g,sites,'site17','488b15')
    call(g,calls,'dictionaryClear')
    g.take('488b4f48','4885c9')
    g.branch('0f84',False)  # 2043
    g.take('ff411c','897118','4c8b7748','4d85f6')
    g.branch('0f84',False)  # 2062
    cell(g,sites,'site18','4c8b3d')
    g.take('41ff461c','498b5610','49634e18','4885d2')
    g.branch('0f84',False)  # 2090
    g.take('3b4a18')
    g.branch('72',True,1)  # 2099
    g.take('8d4101','41894618','3b4a18')
    g.branch('0f83',False)  # 2177
    g.take('c644112001')
    cell(g,sites,'site19','488b05')
    g.take('488b4828','4885c9')
    g.branch('74',True,1)  # 2202
    g.take('0f104720','0f11442460')
    cell(g,sites,'site20','488b05')
    g.take('488b4020','f6803801000001')
    g.branch('75',True,1)  # 2303
    g.take('488b90c0000000','488b5208','488d4c2460')
    call(g,calls,'valid')
    g.take('4c8bfe','84c0','4c0f457c2460','4d85ff')
    g.branch('0f84',False)  # 2348
    cell(g,sites,'site21','488b05')
    g.take('488b4828','4885c9')
    g.branch('74',True,1)  # 2368
    g.take('4889742440','0f57c0','0f11442450','4c637718','4585f6')
    g.branch('0f8e',start_mode=='zero')
    if start_mode!='zero':
        g.take('4885c9')
        g.branch('74',True,1)
        g.take('0f104720','0f11442470')
        cell(g,sites,'nodeSite22','488b05')
        g.take('488b4020','f6803801000001')
        g.branch('75',True,1)
        g.take('488b90c0000000','488b5208','488d4c2470')
        call(g,calls,'valid')
        g.take('488bce','84c0','480f454c2470','4885c9')
        g.branch('0f84',False)
        g.take('488b4970','4885c9')
        g.branch('0f84',False)
        cell(g,sites,'nodeSite23','488b05')
        g.take('4c8b5028','4d85d2')
        g.branch('74',True,1)
        g.take('4883792000')
        g.branch('0f84',False)
        g.take('488b4120','44397018')
        g.branch('0f8e',False)
        g.branch('0f86',False)
        g.take('4a8b44f020','4889442440')
        cell(g,sites,'nodeSite24','833d',tail=1)
        g.take('00')
        g.branch('74',True,1)
        g.take('4885c0')
        g.branch('0f84',False)
        g.take('4885c0')
        g.branch('0f84',False)
        g.take('488b7018','4885f6')
        g.branch('0f84',start_mode=='node-uid-null')
        if start_mode in('node-uid-empty','node-uid-unregistered'):
            g.take('837e1000');g.branch('0f86',start_mode=='node-uid-empty')
        if start_mode=='node-uid-unregistered':
            g.take('4d8b7768','4d85f6');g.branch('0f84',False)
            cell(g,sites,'nodeWaitDictionary','4c8b3d')
            g.take('498b4720','488b88c0000000','488b81b0000000','4883782000');g.branch('75',True,1)
            g.take('498b4720','4c8b80c0000000','4d8b80b0000000','488bd6','498bce')
            call(g,calls,'waitFind');g.take('85c0');g.branch('0f88',True)
    g.take('b001')
    g.jump('e9')
    g.take('4c8d9c24c0000000','498b5b38','498b7340','410f2873f0','498be3','415f','415e','415d')
    g.take('415c','5f','c3')
    return result(g,calls,sites,frameBytes=232,callShadow=[0,32],sameExecutorAndIncomingEventParams=True,
        clearedHeaderHome=[56,64],executorObjectPtrHome=[96,112],comparedHeaderObjectPtrHome=[80,96],
        executorScopeHome=[144,160],contextScopeHome=[128,144],scopeDisposeOrder=[128,144],
        savedFullXmm6EntryRange=[-56,-40],integerSavedEntryRanges={'rbx':[16,24],'rsi':[24,32]},
        pushedNonvolatiles=['rdi','r12','r13','r14','r15'],fullXmm6SavedAndRestored=True,entryRspRestored=True,
        outputDelayFlagInitiallyFalse=True,headerObjectPtrOffset=40,executorContextPtrOffset=32,
        actionContextActionMapOffset=112,headerNextNodeOffset=96,executorStartNodeOffset=24,
        cursorListOffset=64,previousResultListOffset=72,iteratedDictionaryOffset=56,
        selectedHeaderStateBefore=0,selectedHeaderStateAfter=1,selectedForceFlag=force,selectedHeaderEntryResult=0,headerInvocationCounterIncrementOffset=72,
        headerStateOffset=76,constantValidationKind=0,constantValidationByte=1,
        cursorAppendValue='same header._nextID Int32 bits',previousResultAppendValue=1,
        executorStores={'isStarted104':1,'isFinished105':0,'timer108':0,'currentAction112':0,
            'executeTimeStamp120':0,'delay124':0,'delayAllow125':0,'ticking128':0,'ticked129':0},
        selectedStartNodeID=0 if start_mode=='zero'else'positive in own nodeArray bounds',startMode=start_mode,
        selectedNodeUid='not inspected'if start_mode=='zero'else'null'if start_mode=='node-uid-null'else'empty string'if start_mode=='node-uid-empty'else'nonempty UID absent from empty wait dictionary',
        nodeArrayFieldOffset=32,nodeUidFieldOffset=24,stringLengthFieldOffset=16,
        optionalSubExecutorLookupSelected=start_mode=='node-uid-unregistered',actionNodeIterationSelected=False,returnsLiteralTrue=True,
        requiredVirtualCalls=[{'owner':'same valid ActionContext','slot':11,'callbackOffset':496,'methodInfoOffset':504,'receiverRegister':'rcx'},
            {'owner':'same selected header','slot':16,'callbackOffset':576,'methodInfoOffset':584,'receiverRegister':'rcx'}],
        conditions=['Absent replacement tables; active unstarted executor and valid coherent context pointer; stable UID values, ready contexts/classes, collector disabled.',
            'Header lookup hits index zero with a nonnull header; previous header executor differs. Header state initially not one; false force follows the explicit EAX0-not2 continuation. Header Process returns true under its separately proved selected callback path.',
            'Header validate is a nonnull constant Param<bool> kind zero with stored byte one. Scope stacks are cached, nonnull, initially valid with spare list capacity; scope pop delegate is null.',
            'Cursor and previous-result lists have nonnull spare arrays. Iterated dictionary count is zero. Start-node value is zero, or a positive in-bounds node with null/empty UID, or nonempty UID with a null-bucket wait dictionary. No sub-executor link is installed.'],
        assignEffectsSeparatelyRequired=True,eventKeySetEffectsSeparatelyRequired=True,runtimeInvocationObserved=False)


def action_map(regions,entry):
    g=BytesPath(regions,entry);calls=[];sites={}
    g.take('4883ec28')
    cell(g,sites,'site0','488b05')
    g.take('4c8b4828','4d85c9')
    g.branch('0f85',False)
    g.take('33d2')
    call(g,calls,'getContext')
    g.take('4885c0')
    g.branch('74',False,1)
    g.take('488b4070','4883c428','c3')
    return result(g,calls,sites,entryRspRestored=True,frameBytes=40,contextNonnullRequired=True,contextActionMapField=112,returnsSameMapReference=True)


def get_context(regions,entry):
    g=BytesPath(regions,entry);calls=[];sites={}
    g.take('4883ec38','488bc1')
    cell(g,sites,'site0','488b0d')
    g.take('488b4928','4885c9')
    g.branch('0f85',False)
    g.take('0f104020')
    cell(g,sites,'site1','488b0d')
    g.take('0f11442420','488b4920')
    call(g,calls,'ready')
    g.take('488d4c2420','488b90c0000000','488b5208')
    call(g,calls,'valid')
    g.take('33c9','84c0','480f454c2420','488bc1','4883c438','c3')
    return result(g,calls,sites,entryRspRestored=True,frameBytes=56,objectPtrField=32,copyHome=[32, 48],copyBytes=16,returnsReferenceIfUidMatchesOtherwiseNull=True)


def header_hit(regions,entry):
    g=BytesPath(regions,entry);calls=[];sites={}
    g.take('4883ec38')
    cell(g,sites,'site0','488b05')
    g.take('4d8bd0','4c8b5828','4d85db')
    g.branch('0f85',False)
    g.take('4883792800')
    g.branch('0f84',False)
    g.take('488b4128','395018')
    g.branch('0f8e',False)
    g.take('85d2')
    g.branch('0f88',False)
    g.take('488bc8','4885c0')
    g.branch('74',False,1)
    g.take('3b5018')
    g.branch('73',False,1)
    g.take('4863c2','488b4cc120','498908','498bca')
    call(g,calls,'barrier')
    g.take('49833a00','0f97c0','4883c438','c3')
    return result(g,calls,sites,entryRspRestored=True,frameBytes=56,arrayFieldOffset=40,elementStride=8,outputReferenceUnchanged=True,indexNonnullInRangeRequired=True,returnsReferenceNonnullBool=True)


def scope_stack_cached(regions,entry):
    g=BytesPath(regions,entry);calls=[];sites={}
    g.take('4883ec28')
    cell(g,sites,'site0','488b05')
    g.take('488bd1','488b4810','4885c9')
    g.branch('0f85',False)
    cell(g,sites,'site1','488b05')
    g.take('48895c2430','48896c2438','4889742440','488b88b8000000','48897c2420','4883790800')
    g.branch('74',False,1)
    g.take('488b80b8000000','488b742440','488b6c2438','488b5c2430','488b4008','488b7c2420','4883c428','c3')
    return result(g,calls,sites,entryRspRestored=True,frameBytes=40,staticFieldOffset=8,cachedNonnullRequired=True,returnsCachedSameReference=True)


def scope_push(regions,entry):
    g=BytesPath(regions,entry);calls=[];sites={}
    g.take('488bc4','48895810','48896818','48897020','57','4883ec50')
    cell(g,sites,'site0','833d',tail=1)
    g.take('00')
    cell(g,sites,'site1','488d2d')
    g.take('0f57c0','0f2970e8','0f1101','498bf9','48c740d000000000','488bda','4c8940c8','488bf1')
    g.branch('74',True,1)
    cell(g,sites,'site2','833d',tail=1)
    g.take('00','48895c2428')
    g.branch('74',True,1)
    g.take('488b5b10','0f28742420','0f1136','4885db')
    g.branch('0f84',False)
    g.take('498b4120','488b88c0000000','488b4120','4883782000')
    g.branch('75',True,1)
    g.take('488b4720','488b5310','488b88c0000000','488b7920','ff431c','4885d2')
    g.branch('0f84',False)
    g.take('48634b18','3b4a18')
    g.branch('72',True,1)
    g.take('8d4101','894318','3b4a18')
    g.branch('0f83',False)
    g.take('488d4102','4803c0')
    cell(g,sites,'site3','833d',tail=1)
    g.take('00','0f1134c2')
    g.branch('74',True,1)
    g.take('488b5c2468','488bc6','488b742478','488b6c2470','0f28742440','4883c450','5f','c3')
    return result(g,calls,sites,entryRspRestored=True,frameBytes=88,valueBytes=8,scopeBytes=16,parentStackReferenceOffset=8,scopeValueOffset=0,listOffset=16,elementStride=16,listSizeOffset=24,listVersionOffset=28,spareArrayRequired=True,fullXmm6SavedAndRestored=True,collectorDisabledRequired=True,appendsSameScopeValueAndParentStack=True)


def scope_dispose(regions,entry):
    g=BytesPath(regions,entry);calls=[];sites={}
    g.take('48895c2410','57','4883ec20','4883790800','488bfa','488bd9')
    g.branch('74',False,1)
    g.take('4889742430','488b7108','488b4a20')
    call(g,calls,'ready')
    g.take('488b88c0000000','488b4108','4883782000')
    g.branch('0f84',False)
    g.take('488b4f20')
    call(g,calls,'ready')
    g.take('488bce','488b90c0000000','488b5208')
    call(g,calls,'scopePop')
    g.take('488d4b08','48c7430800000000')
    call(g,calls,'barrier')
    g.take('488b742430','488b5c2438','4883c420','5f','c3')
    return result(g,calls,sites,entryRspRestored=True,frameBytes=40,nonnullStackRequired=True,stackFieldOffset=8,sameStackPassedToPop=True,clearsStackFieldAfterPop=True)


def scope_pop(regions,entry):
    g=BytesPath(regions,entry);calls=[];sites={}
    g.take('48895c2408','48896c2410','4889742418','48897c2420','4156','4883ec40','4c8b7118','488bfa')
    g.take('488bf1','4d85f6')
    g.branch('0f84',True)
    g.take('488b5e10','4885db')
    g.branch('0f84',False)
    g.take('488b4720','488b88c0000000','488b4108','4883782000')
    g.branch('0f84',False)
    g.take('488b4720','8b7318','488b88c0000000','488b4138','4883782000')
    g.branch('0f84',False)
    g.take('448d4eff','443b4b18')
    g.branch('73',False,1)
    g.take('8b4318','ffc8','894318','443bc8')
    g.branch('0f8c',False)
    g.take('488b5310','0f57c0','48634b18','4885d2')
    g.branch('74',False,1)
    g.take('3b4a18')
    g.branch('73',False,1)
    g.take('488d4102','4883c102','4803c0','48c1e104','4803ca','0f1104c2')
    call(g,calls,'barrier')
    g.take('ff431c','488b5c2450','488b6c2458','488b742460','488b7c2468','4883c440','415e','c3')
    return result(g,calls,sites,entryRspRestored=True,frameBytes=72,onPopDelegateFieldOffset=24,onPopDelegateNullRequired=True,listFieldOffset=16,elementStride=16,positiveSizeRequired=True,selectedIndex='initial size minus one',decrementsSizeByOne=True,zerosFullRemovedSlot16=True,incrementsVersion=True)


def push_executor(regions,entry):
    g=BytesPath(regions,entry);calls=[];sites={}
    g.take('48895c2408','57','4883ec30')
    cell(g,sites,'site0','488b05')
    g.take('488bda','488bf9','488b5028','4885d2')
    g.branch('0f85',False)
    g.take('4885db')
    g.branch('74',False,1)
    cell(g,sites,'site1','488b05')
    g.take('83b8e000000000')
    g.branch('74',False,1)
    g.take('488b88b8000000','488b5108','4885d2')
    g.branch('74',False,1)
    cell(g,sites,'site2','4c8b0d')
    g.take('488d4c2420','4c8bc3')
    call(g,calls,'scopePush')
    g.take('0f10442420','0f1107','488b5c2440','488bc7','4883c430','5f','c3')
    return result(g,calls,sites,entryRspRestored=True,frameBytes=56,nonnullExecutorRequired=True,classAlreadyInitializedRequired=True,cachedStackNonnullRequired=True,returnsCopiedScope16=True)


def clean(regions,entry):
    g=BytesPath(regions,entry);calls=[];sites={}
    g.take('4053','4883ec50','488bd9')
    cell(g,sites,'site0','488b05')
    g.take('488b4808','4885c9')
    g.branch('74',True,1)
    g.take('0f57c0','0f11442428','48c7434800000000','4533c0','488b5338','488d4c2438')
    call(g,calls,'pushContext')
    g.take('0f1000','0f11442428','48c744243800000000','488d442428','4889442440','488b0b')
    call(g,calls,'prepare')
    g.take('488b13','488b82f0010000','488b92f8010000','488bcb','ffd0','90')
    cell(g,sites,'site1','488b15')
    g.take('488d4c2428')
    call(g,calls,'scopeDispose')
    g.jump('eb',1)
    g.take('4883c450','5b','c3')
    return result(g,calls,sites,entryRspRestored=True,frameBytes=88,clearsNodeField72=True,contextFieldOffset=56,selectedContextFieldNullRequired=True,scopeCopyHome=[40, 56],pushContextOutputHome=[56, 72],virtualCallbackSlot=11,callbackOffset=496,methodInfoOffset=504,normalCallbackRequired=True,scopeDisposedExactlyOnce=True)


def push_context_null(regions,entry):
    g=BytesPath(regions,entry);calls=[];sites={}
    g.take('48895c2408','57','4883ec30')
    cell(g,sites,'site0','488b05')
    g.take('488bda','488bf9','488b5010','4885d2')
    g.branch('0f85',False)
    g.take('4885db')
    g.branch('74',True,1)
    g.take('0f57c0','0f1101')
    g.jump('eb',1)
    g.take('488b5c2440','488bc7','4883c430','5f','c3')
    return result(g,calls,sites,entryRspRestored=True,frameBytes=56,incomingContextNullRequired=True,outputScopeBytes=16,outputZero=True,sameHiddenOutputReturnedInRax=True)


def header_check(regions,entry):
    g=BytesPath(regions,entry);calls=[];sites={}
    g.take('48895c2410','4889742418','66894c2408','57','4883ec30','488b0a','498bf8','488bda')
    call(g,calls,'prepare')
    g.take('488b03','4c8b8890020000','488bb098020000')
    cell(g,sites,'site0','488d05')
    g.take('4c3bc8')
    g.branch('0f85',True)
    cell(g,sites,'site1','488d05')
    g.take('4c3bc8')
    g.branch('74',False,1)
    cell(g,sites,'site2','488d05')
    g.take('4c3bc8')
    g.branch('74',True,1)
    cell(g,sites,'site3','488b05')
    g.take('488b4828','4885c9')
    g.branch('0f85',False)
    g.take('488b5c2448','b001','488b742450','4883c430','5f','c3')
    return result(g,calls,sites,entryRspRestored=True,frameBytes=56,virtualCallbackSlot=21,callbackOffset=656,methodInfoOffset=664,selectedThirdInlineTargetRequired=True,returnsLiteralTrue=True)


def dictionary_empty_clear(regions,entry):
    g=BytesPath(regions,entry);calls=[];sites={}
    g.take('48895c2410','48896c2418','56','57','4154','4156','4157','4883ec30')
    g.take('8b7120','488bd9','85f6')
    g.branch('0f8e',True)
    g.take('ff432c','488b5c2468','488b6c2470','4883c430','415f','415e','415c','5f')
    g.take('5e','c3')
    return result(g,calls,sites,entryRspRestored=True,frameBytes=88,countFieldOffset=32,countMustBeZero=True,noNonframeWrites=True)


def setup(regions,entry):
    g=BytesPath(regions,entry);calls=[];sites={}
    g.take('4053','4883ec30');cell(g,sites,'replacement','488b05')
    g.take('488bd9','488b4808','4885c9');g.branch('0f85',False)
    cell(g,sites,'implicit','4c8b05');g.take('488d4c2420');call(g,calls,'implicit')
    g.take('0f10442420','488d4b28','0f114328','4883c430','5b')
    at=g.at;tail=g.relative('e9');calls.append(dict(role='barrier',instructionVa=at,targetVa=tail,tail=True))
    return result(g,calls,sites,frameBytes=56,callShadow=[0,32],entryRspRestored=True,
        nodeExecutorPtrFieldOffset=40,valueBytes=16,argumentCopyHome=[32,48],restoredNonvolatiles=['rbx'],
        sameIncomingExecutorPassedToImplicit=True,storesSameReturnedObjectPtr16=True,tailBarrierFieldAddressOffset=40)


def inequality(regions,entry,*,validity_equal=True):
    need('literal-validity-mode',type(validity_equal)is bool)
    g=BytesPath(regions,entry);calls=[];sites={}
    g.take('48895c2408','4889742410','57','4883ec40','488bf9','488bda','498b4820');call(g,calls,'ready')
    g.take('0f1003','0f100f','4c8b80c0000000','0f29442420','0f294c2430','498b7028','488b4e20');call(g,calls,'ready')
    g.take('488d4c2430','488b90c0000000','488b5208');call(g,calls,'valid')
    g.take('488b4e20','0fb6d8');call(g,calls,'ready')
    g.take('488d4c2420','488b90c0000000','488b5208');call(g,calls,'valid')
    g.take('3ad8');g.branch('75',not validity_equal,1)
    if validity_equal:g.take('8b442428','39442438','0f95c0','488b5c2450')
    else:g.take('488b5c2450','b001')
    g.take('488b742458','4883c440','5f','c3')
    return result(g,calls,sites,frameBytes=72,callShadow=[0,32],entryRspRestored=True,
        inputCopies16=[[32,48],[48,64]],cachedUidOffset=8,validityResultsEqual=validity_equal,
        result='cached UID UInt32 values differ'if validity_equal else'literal true',
        returnsNormalizedBool=True,nonframeWrites=0,restoredNonvolatiles=['rbx','rsi','rdi'])


def param_constant(regions,entry):
    g=BytesPath(regions,entry);calls=[];sites={}
    g.take('48895c2418','4889542410','56','57','4154','4156','4157','4881ecd0000000',
        '498bf9','450fb6e0','488bf2','488bd9','4983793800');g.branch('0f84',False)
    g.take('33c0','4889842418010000','4889842400010000','0f57c0','0f118424a0000000',
        '0f118424b0000000','48898424c0000000','4885db');g.branch('0f84',False)
    g.take('488b4738','488b4808','4883792000');g.branch('0f84',False)
    g.take('837b1000');g.branch('75',False,1)
    g.take('0fb64320','8806','b001','488b9c2410010000','4881c4d0000000','415f','415e','415c','5f','5e','c3')
    return result(g,calls,sites,frameBytes=248,entryRspRestored=True,kindFieldOffset=16,requiredKind=0,
        valueFieldOffset=32,outputBytes=1,outputStoredByteUnchanged=True,returnsLiteralTrue=True,
        restoredNonvolatiles=['rbx','rsi','rdi','r12','r14','r15'],normalCalls=0)


def barrier_disabled(regions,entry):
    g=BytesPath(regions,entry);sites={};calls=[]
    cell(g,sites,'collector','833d',tail=1);g.take('00','4c8bc1');g.branch('74',True,1);g.take('c3')
    return result(g,calls,sites,collectorDisabledRequired=True,normalEffectCalls=0,nonframeWrites=0,
        integerNonvolatilesUntouched=True,entryRspRestored=True,physicalExtentProved=False)


def reusable_uid(regions,entry,*,image_base,case=0):
    """Own final discriminator-table branch returning the declared UInt32 UID.

    The literal live class discriminator is a condition, never equated to a
    metadata TypeDefinition index or inferred from the receiver's type name.
    """
    g=BytesPath(regions,entry)
    g.take('4053','55','56','57','4883ec68','488b01','488bd9','8b901c010000','81fa')
    lower=int.from_bytes(g.read(4),'little');g.branch('0f8f',True)
    g.take('81fa');upper=int.from_bytes(g.read(4),'little');g.branch('0f8f',True)
    g.take('81ea');start=int.from_bytes(g.read(4),'little');g.take('83fa');maximum=int.from_bytes(g.read(1),'little')
    need('bounded-final-UID-discriminator-table',0<=maximum<=64);g.branch('0f87',False)
    need('exact-selected-image-base',g.relative('488d35')==image_base)
    g.take('4863c2','8b8486');table=int.from_bytes(g.read(4),'little');g.take('4803c6','ffe0')
    tail=bytes.fromhex('8b43104883c4685f5e5d5bc3');selected=[]
    for i in range(maximum+1):
        try:
            at=image_base+int.from_bytes(bytes(g.bytes[image_base+table+4*i+j]for j in range(4)),'little')
            if bytes(g.bytes[at+j]for j in range(len(tail)))==tail:selected.append((i,at))
        except KeyError as error:raise ValueError('patrolExecutor.unowned-UID-table-selection')from error
    need('finite-own-UID-return-table-slots',selected and type(case)is int and 0<=case<len(selected));index,target=selected[case]
    need('selected-class-pivot-predicates',start+index>upper>lower)
    g.at=image_base+table+4*index;cell=int.from_bytes(g.read(4),'little');need('same-owned-UID-leaf',image_base+cell==target)
    g.at=target;g.take(tail.hex())
    return dict(selectedBytes=g.seen,frameBytes=136,callShadow=[0,32],entryRspRestored=True,
        selectedUidFieldOffset=16,returnedBytes=4,requiredClassDiscriminatorOffset=284,
        requiredClassDiscriminator=start+index,discriminatorNominalAliasProved=False,
        liveClassDiscriminatorObserved=False,tableMaximum=maximum,selectedTableIndex=index,allSelectedTableIndices=[i for i,_ in selected],
        nonframeWrites=0,normalEffectCalls=0,restoredNonvolatiles=['rbx','rbp','rsi','rdi'])


def wait_find_empty(regions,entry):
    g=BytesPath(regions,entry);calls=[];sites={}
    g.take('48895c2418','55','56','57','4156','4157','4883ec30','4d8bf8','488bea','488bd9','4885d2');g.branch('0f84',False)
    g.take('488b7310','bfffffffff','4c8b7318','4c89642460','4c896c2468','4885f6');g.branch('75',False,1)
    g.take('4c8b6c2468','8bc7','4c8b642460','488b5c2470','4883c430','415f','415e','5f','5e','5d','c3')
    return result(g,calls,sites,frameBytes=88,entryRspRestored=True,nonnullStringKeyRequired=True,
        bucketsFieldOffset=16,bucketsNullRequired=True,returnsInt32=-1,nonframeWrites=0,
        normalEffectCalls=0,closedContextSelectionRequired=True,canonicalPointerAliasProved=False,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'])

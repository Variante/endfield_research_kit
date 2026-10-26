"""Own normalized enum/reference dictionary count and exact selected loop.

Only the independently registered Int32Enum/reference body is replayed here.
The original closed enum/dictionary requests, callback selection, helper
contexts and element grammars are separate native composition requirements.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check,condition):
    if not condition:raise ValueError('levelwideDictionaryPrograms.'+check)


def enum_dictionary(regions,entry,offsets,*,count,same_comparer=True):
    need('bounded-literal-count-and-comparer',type(count)is int and -1<=count<=3 and type(same_comparer)is bool)
    o={k:bytes((offsets[k],)).hex()for k in ('currentPtr','bufferLength','advancedCount','consumed','totalLength')}
    g=BytesPath(regions,entry);symbols={};cells={};callbacks=[];adds=[]
    def call(name):
        target=g.relative('e8');need('same-actual-helper-'+name,name not in symbols or symbols[name]==target)
        symbols[name]=target
    def cell(name,prefix):
        target=g.relative(prefix);need('same-actual-cell-'+name,name not in cells or cells[name]==target)
        cells[name]=target
    g.take('4c89442418','53','55','57','4154','4155','4156','4157','4883ec50','33ff','498be9',
        '837a'+o['bufferLength']+'04','4d8be0','4c8bea','89bc2498000000','4c8bf1','48897c2438')
    g.branch('7d',True,1)
    g.take('498b45'+o['currentPtr'],'4c6338','44897c2430','418b5d'+o['bufferLength'],'83c3fc');g.branch('79',True,1)
    g.take('498345'+o['currentPtr']+'04','418345'+o['advancedCount']+'04','418345'+o['consumed']+'04',
        '41895d'+o['bufferLength'],'496345'+o['consumed'],'498b4d'+o['totalLength'],'482bc8','493bcf')
    g.branch('0f8c',False);g.take('4183ffff','0f95c0','84c0');g.branch('0f84',count==-1)
    if count==-1:
        g.take('498bcc','49893c24');call('barrier')
    else:
        g.take('4889b42490000000','49393c24');g.branch('74',True,1)
        g.take('488b4d20','ba03000000','4d8b7610','488b89c0000000');call('classResolve')
        g.take('488bc8');call('allocate');g.take('488bf0','4885c0');g.branch('0f84',False)
        g.take('488b4d20','488b91c0000000','488b4a20','48397920');g.branch('75',True,1)
        g.take('488b4520','488b88c0000000','488b5920','4585ff');g.branch('0f88',False);g.branch('7e',count==0,1)
        if count:
            g.take('488b4320','488b88c0000000','488b4108','48397820');g.branch('75',True,1)
            g.take('488b4320','418bd7','488bce','4c8b80c0000000','4d8b4008');call('initialize')
        g.take('488b4320','488b88c0000000','488b4910');call('defaultComparer')
        cell('imageBase','4c8d0d');g.take('4c3bf0');g.branch('74',same_comparer,1)
        if not same_comparer:
            cell('collector','393d');g.take('4c897630');g.branch('74',True,1)
        cell('collector','393d');g.take('49893424');g.branch('74',True,1)
        cell('providerClass','488b0d');g.take('39b9e0000000');g.branch('75',True,1)
        g.take('488b4520');cell('observedImmediate','488d35')
        # This literal is an implementation constant of this source program,
        # never a type/format or installed-build declaration.
        g.take('49bf65210b59c84216b2','488b88c0000000','4c8b6130','49397c2438');g.branch('0f85',True)
        cell('systemTypeClass','488b0d');g.take('498b5c2438','488b1b','39b9e0000000');g.branch('75',True,1)
        g.take('33d2','488bcb');call('typeFromHandle')
        cell('providerClass','488b0d');g.take('4c8bf0','39b9e0000000');g.branch('75',True,1)
        cell('providerReady','40383d');g.branch('0f85',True)
        cell('providerClass','488b0d');g.take('39b9e0000000');g.branch('75',True,1)
        g.take('498bce');call('providerBackend')
        g.take('498b4c2438','4c8bf8','488b4108','f6803801000001');g.branch('75',True,1)
        g.take('4d85ff');g.branch('0f84',False)
        g.take('498b0f','488bd0');call('assignable');g.take('84c0');g.branch('0f84',False)
        g.take('488b4520','488b88c0000000','488b4938');call('valueProvider')
        g.take('4c8be0','397c2430');g.branch('0f8e',count==0)
        loop=g.at
        for index in range(count):
            need('same-owned-loop-head',g.at==loop)
            g.take('488b4d20','488d442438','4c8d8c2498000000','4d8bc5','488b91c0000000','488b4a40',
                '498bd4','48894c2428','498bcf','4889442420')
            callbacks.append(g.at);call('keyValue')
            g.take('488b8424a0000000','8bb42498000000','4c8b742438','488b18','4885db');g.branch('0f84',False)
            g.take('488b4520','488b88c0000000','488b4148','4883782000');g.branch('75',True,1)
            g.take('488b4520','4d8bc6','8bd6','488bcb','4c8b88c0000000','4d8b4948')
            adds.append(g.at);call('Add');g.take('ffc7','3b7c2430')
            target=g.relative('0f8c');need('exact-owned-loop-backedge',target==loop)
            if index+1<count:g.at=target
        g.take('488bb42490000000')
    g.take('4883c450','415f','415e','415d','415c','5f','5d','5b','c3')
    return dict(selectedBytes=g.seen,countWitness=count,newDictionary=True,sameComparer=same_comparer,
        symbols=symbols,cells=cells,keyValueCallbackSites=callbacks,AddCallSites=adds,
        headerBytes=4,keyOutputBytes=4,valueOutputBytes=8,countSlot=48,counter='edi',
        keyBitsPassedToAdd=32,valueReferenceUnchanged=True,initiallyNullOutputRequired=True,
        entryRspRestored=True,normalReturn=True,closedPointerEquivalenceProved=False,
        frame=dict(entryRspDelta=-136,callShadow=[0,32],stackCallArguments=[[32,40],[40,48]],
            savedRsiHome=[8,16],originalOutputPointerHome=[24,32],keyOutputHome=[16,20],valueLocal=[-80,-72],
            savedCountLocal=[-88,-84],pushedNonvolatiles=['rbx','rbp','rdi','r12','r13','r14','r15']),
        conditions=['Buffered valid count and disjoint nonwrapping Reader/output/storage.',
            'Actual selected dictionary callback equals this independently registered normalized source with original coherent closed contexts.',
            'Selected context/class/provider ready paths and collector disabled; exact normal helper ABI/effects and unchanged caller nonvolatiles.',
            'Own key/value callbacks, constructor class/context slots, typed pair and Add/Initialize/comparer are independently joined.'],
        wireGrammarAdmitted=False,callbackSelectionObserved=False)


def enum_pair(regions,entry,offsets,*,callback):
    """Own exact pair helper; only a separately proved nominal raw4 callback."""
    need('literal-independent-callback-target',type(callback)is int and callback>0)
    o={k:bytes((offsets[k],)).hex()for k in ('currentPtr','bufferLength','advancedCount','consumed')}
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','48897c2418','4c89742420','4157','4883ec30',
        '488bf1','4d8bf9','488b4c2468','498bd8','488bfa','4883793800');g.branch('0f84',False)
    g.take('0f57c0','0f11442420','4c8b742460','33c0','418907','498906','4885f6');g.branch('0f84',False)
    g.take('488b0e');prepare=g.relative('e8')
    g.take('488b06','4c8b9090010000','4c8b8898010000');first=g.relative('488d05');g.take('4c3bd0')
    g.branch('75',callback!=first,1);second=None
    if callback!=first:
        second=g.relative('488d05');g.take('4c3bd0')
        need('selected-callback-is-actual-second-raw4-target',callback==second);g.branch('74',True,1)
    g.take('837b'+o['bufferLength']+'04');g.branch('0f8c',False)
    g.take('488b43'+o['currentPtr'],'8b00','418907','8b73'+o['bufferLength'],'83c6fc');g.branch('0f88',False)
    g.take('488343'+o['currentPtr']+'04','8343'+o['advancedCount']+'04','8343'+o['consumed']+'04','8973'+o['bufferLength'])
    g.take('4885ff');g.branch('74',False,1)
    g.take('b905000000','4d8bce','4c8bc3','488bd7');dispatch=g.relative('e8')
    g.take('488b5c2440','488b742448','488b7c2450','4c8b742458','4883c430','415f','c3')
    return dict(selectedBytes=g.seen,prepareTarget=prepare,valueDispatcher=dispatch,
        firstComparedCallback=first,secondComparedCallback=second,selectedEnumCallback=callback,
        keyOutputBytesZeroed=4,valueOutputBytesZeroed=8,keyWireBytes=4,valueWireBytes=None,
        incomingKeyFormatter='RCX',incomingValueFormatter='RDX',incomingReader='R8',incomingKeyOutput='R9',
        incomingValueOutput='entryRSP+40',incomingPairMethodInfo='entryRSP+48',sameReader=True,sameOutputs=True,
        valueSelector=5,valueFormatterRegister='rdx',valueReaderRegister='r8',valueOutputRegister='r9',
        callbackSelectionObserved=False,wireGrammarAdmitted=False,entryRspRestored=True,normalReturn=True,
        frame=dict(entryRspDelta=-56,callShadow=[0,32],zeroTemporary=[32,48],
            savedEntryHomes=dict(rbx=[8,16],rsi=[16,24],rdi=[24,32],r14=[32,40]),pushedNonvolatiles=['r15']))

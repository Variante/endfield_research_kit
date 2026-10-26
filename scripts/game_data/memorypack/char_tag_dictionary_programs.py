"""Exact reference-key/value4 dictionary and pair-copy programs.

These byte programs confer no nominal key, value, callback or provider grammar.
The two type parameters and every actual helper are joined by the source owner.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check,condition):
    if not condition:raise ValueError('charTagDictionaryProgram.'+check)


def symbols(regions,entry):
    """Read helpers from their exact following byte sequence, never a scan order."""
    patterns=dict(header='44897c2430e8',context='488b4918e8',allocate='488bc8e8',
        constructor='4d8b4920e8',barrier='48891ee8',keyProvider='488b4930e8',valueProvider='488b4938e8',
        keyValue='488bcbE8',Add='4d8b4948e8')
    # Only the pair call has a short common suffix; its actual full local/
    # argument sequence is part of the independent complete path below.
    patterns['keyValue']='488d4c243048894c2420488bcbe8'
    out={}
    for role,encoded in patterns.items():
        pattern=bytes.fromhex(encoded);found=[]
        for at,raw in regions:
            offset=raw.find(pattern)
            while offset>=0:
                operand=offset+len(pattern);need('complete-E8:'+role,operand+4<=len(raw))
                found.append(at+operand+4+int.from_bytes(raw[operand:operand+4],'little',signed=True))
                offset=raw.find(pattern,offset+1)
        need('one-owned-helper:'+role,len(set(found))==1);out[role]=found[0]
    return out


def program(regions,entry,s,*,count):
    need('finite-witness',type(count)is int and -1<=count<=3);g=BytesPath(regions,entry)
    g.take('48895c2408','4889742418','57','4154','4155','4156','4157','4883ec50','4533ff','498bf9')
    flag=g.relative('44383d');g.take('498bf0','4c8be2','488bd9');g.branch('75',True,1)
    g.take('488d942488000000','4489bc2488000000','498bcc','4c897c2438','44897c2430');g.call(s['header'])
    g.take('84c0');g.branch('0f84',count==-1);callbacks=[];adds=[];edges=[]
    if count==-1:g.take('488bce','4c893e');g.call(s['barrier'])
    else:
        g.take('488b4720','4c393e');g.branch('74',True,1)
        g.take('488b88c0000000','4c8b7310','488b4918');g.call(s['context']);g.take('488bc8');g.call(s['allocate'])
        g.take('488bd8','4885c0');g.branch('0f84',False)
        g.take('488b4f20','488b91c0000000','488b4a20','4c397920');g.branch('75',True,1)
        g.take('488b4720','4d8bc6','8b942488000000','488bcb','4c8b88c0000000','4d8b4920');g.call(s['constructor'])
        g.take('488bce','48891e');g.call(s['barrier']);owner=g.relative('488b0d');sentry=g.relative('e8')
        g.take('488b4720','488b88c0000000','488b4930');g.call(s['keyProvider'])
        g.take('488b4f20','488bd8','4889442440','488b89c0000000','488b4938');g.call(s['valueProvider'])
        g.take('458bf7','4889442448','4439bc2488000000');g.branch('0f8e',count==0)
        loop=g.at
        for i in range(count):
            need('same-loop-head',g.at==loop)
            g.take('488b4f20','4c8d4c2438','4d8bc4','488b91c0000000','488b4a40','488bd0','48894c2428',
                '488d4c2430','48894c2420','488bcb');callbacks.append(g.at);g.call(s['keyValue'])
            g.take('4c8b3e','4c8b6c2438','8b5c2430','4d85ff');g.branch('74',False,1)
            g.take('488b4720','488b88c0000000','488b4148','4883782000');g.branch('75',True,1)
            g.take('488b4720','448bc3','498bd5','498bcf','4c8b88c0000000','4d8b4948');adds.append(g.at);g.call(s['Add'])
            g.take('488b5c2440','41ffc6','488b442448','443bb42488000000');edges.append(g.at)
            g.branch('0f8c',i+1<count)
        if count:g.jump('eb',1)
    g.take('4c8d5c2450','498b5b30','498b7340','498be3','415f','415e','415d','415c','5f','c3')
    return dict(selectedBytes=g.seen,countWitness=count,newDictionary=True,headerBytes=4,
        keyManagedBytes=8,valueManagedBytes=4,elementCallbackSites=callbacks,AddCallSites=adds,backedgeSites=edges,
        initiallyNullOutputRequired=True,metadataReadyFlag=flag,normalReturn=True,entryRspRestored=True,
        allWin64IntegerNonvolatilesRestored=True,closedPointerEquivalenceProved=False,
        frame=dict(entryRspDelta=-120,keyLocal=[56,64],valueLocal=[48,52],countHome=[136,140],
            providerHomes=[[64,72],[72,80]],stackCallArguments=[[32,40],[40,48]],
            savedEntryHomes=dict(rbx=[8,16],rsi=[24,32]),pushedNonvolatiles=['rdi','r12','r13','r14','r15']))


def induction(programs,count_limit=4096):
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    need('bounded-count-domain',type(count_limit)is int and 3<=count_limit<=4096)
    positive=[p for p in programs if p['countWitness']>=0];one,=[p for p in positive if p['countWitness']==1]
    return prove_induction(positive,initial='458bf7',increment='41ffc6',comparison='443bb42488000000',
        counter='r14d',saved_count='signed Int32 stack136',max_count=count_limit,mode_key='newDictionary',backedge_sites=one['backedgeSites'])


def pair_program(regions,entry,*,key_dispatch,value_dispatch):
    g=BytesPath(regions,entry)
    g.take('488bc4','48895808','48896810','48897018','48897820','4156','4883ec30','488be9','4d8bf1',
        '488b4c2468','498bd8','488bfa','4883793800');g.branch('75',True,1)
    g.take('0f57c0','0f11442420','488b742460','33c0','498906','8906','4885ed');g.branch('74',False,1)
    g.take('8d4805','4d8bce','4c8bc3','488bd5');g.call(key_dispatch);g.take('4885ff');g.branch('74',False,1)
    g.take('4c8bce','4c8bc3','488bd7');g.call(value_dispatch)
    g.take('488b5c2440','488b6c2448','488b742450','488b7c2458','4883c430','415e','c3')
    return dict(selectedBytes=g.seen,keyOutputBytesZeroed=8,valueOutputBytesZeroed=4,keyDispatchSelector=5,
        valueDispatcherRcxSelectorRequired=False,valueDispatcherMustProveUnusedRcx=True,
        sameIncomingReader=True,normalReturn=True,entryRspRestored=True)


def constructor_program(regions,entry,s,*,positive,same_comparer):
    need('literal-constructor-paths',type(positive)is bool and type(same_comparer)is bool);g=BytesPath(regions,entry)
    g.take('48895c2408','48896c2410','4889742418','57','4883ec20','498be9','498bf8','8bf2','488bd9','85d2');g.branch('0f88',False)
    g.take('85d2');g.branch('0f8f',positive)
    if positive:
        g.take('498b4120','488b88c0000000','488b4108','4883782000');g.branch('75',True,1)
        g.take('488b4520','8bd6','488bcb','4c8b80c0000000','4d8b4008');g.call(s['initialize']);g.take('90');g.jump('e9')
    g.take('488b4520','488b88c0000000','488b4910');g.call(s['defaultComparer']);g.take('483bf8');g.branch('74',same_comparer,1)
    if not same_comparer:g.take('488d4b30','48897b30');g.call(s['barrier'])
    g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,positiveCapacity=positive,sameComparer=same_comparer,capacityUnchanged=True,
        comparerReferenceUnchanged=True,normalReturn=True,entryRspRestored=True,actualInitializeAndComparerNormalCompatibilityRequired=True)


def add_program(regions,entry,insert):
    g=BytesPath(regions,entry)
    g.take('48895c2408','48896c2410','4889742418','57','4883ec30','498b4120','418bd8','498bf9','488bf2','488be9',
        '4c8b80c0000000','498b80c0000000','4883782000');g.branch('0f84',False)
    g.take('488b4720','41b102','448bc3','488bd6','488b88c0000000','488b81c0000000','488bcd','4889442420');g.call(insert)
    g.take('488b5c2440','488b6c2448','488b742450','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,valueManagedBytes=4,completeIncomingR8DBitsStored=True,keyReferenceUnchanged=True,
        insertionBehaviorLiteral=2,actualInsertNormalCompatibilityRequired=True,normalReturn=True,entryRspRestored=True)

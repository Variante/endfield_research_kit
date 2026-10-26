"""Own SerializeReferenceDictionary static source with RBP/R13 control.

This is independent of SerializeFieldDictionary. The selected path starts with
a null output and uses distinct reference key/value locals and slot5 calls.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(key,condition):
    if not condition:raise ValueError('animationFallbackDictionaryProgram.'+key)


def program(regions,entry,*,count):
    need('finite-witness',type(count)is int and -1<=count<=3)
    g=BytesPath(regions,entry);symbols={};calls=[];keys=[];values=[];insertions=[];edges=[]
    def call(role):
        at=g.at;target=g.relative('e8');need('same-helper:'+role,role not in symbols or symbols[role]==target)
        symbols[role]=target;calls.append(dict(role=role,instructionVa=at,targetVa=target))
    g.take('48895c2410','55','56','57','4154','4155','4156','4157','488bec','4883ec40','4533ff','498bf8')
    ready=g.relative('44383d');g.take('488bda','4c8bf1');g.branch('75',True,1)
    g.take('488d5540','44887d40','498bce','44897de0','4c897de8','4c897df0');call('objectHeader')
    g.take('807d40ff');g.branch('0f84',count==-1);allocation=None;provider=None;count_context=None
    if count==-1:
        g.take('488bcb','4c893b');call('barrier')
    else:
        g.take('4c393b');g.branch('0f85',False)
        g.take('488b4f20');call('context');g.take('488b88c0000000','488b89e8000000');call('context')
        g.take('488bc8');allocation=g.at;call('allocate');g.take('488bf0','4885c0');g.branch('0f84',False)
        g.take('488b4f20');call('context');g.take('488b88c0000000','488b91f0000000','4c397a20');g.branch('75',True,1)
        g.take('488b4f20');call('context');g.take('488bce','488b90c0000000','488b92f0000000');call('constructor')
        g.take('488bcb','488933');call('barrier');provider=g.at;g.relative('488b0d');call('classReady')
        g.take('488b4f20');call('context');g.take('488b88c0000000','488b89f8000000');call('provider')
        g.take('488b4f20','488bf0');call('context');g.take('488b88c0000000','488b8900010000');call('provider')
        count_context=g.at;g.relative('4c8b05');g.take('488d55e0','498bce','4c8be0');call('count')
        g.take('458bef','44397de0');g.branch('0f8e',count==0)
        for index in range(count):
            g.take('4c897de8','4885f6');g.branch('0f84',False)
            g.take('b905000000','4c8d4de8','4d8bc6','488bd6');keys.append(g.at);call('dispatch')
            g.take('4c897df0','4d85e4');g.branch('0f84',False)
            g.take('b905000000','4c8d4df0','4d8bc6','498bd4');values.append(g.at);call('dispatch')
            g.take('488b45e8','4c8b3b','48894558','488b45f0','48894540','4d85ff');g.branch('74',False,1)
            g.take('488b4f20');call('context');g.take('488b88c0000000','488b8128010000','4883782000');g.branch('75',True,1)
            g.take('488b4f20');call('context');g.take('4c8b4540','498bcf','488b5558','4c8b88c0000000','4d8b8928010000')
            insertions.append(g.at);call('insert')
            g.take('41ffc5','41bf00000000','443b6de0');edges.append(g.at);g.branch('0f8c',index+1<count)
        if count:g.jump('eb',1)
    g.take('488b9c2488000000','4883c440','415f','415e','415d','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,countWitness=count,newDictionary=True,elementCallbacks=len(keys),
        keyCallbackSites=keys,valueCallbackSites=values,insertCallSites=insertions,backedgeSites=edges[-1:]if edges else[],
        symbols=symbols,helperCalls=calls,metadataReadyFlagVa=ready,providerClassInstructionVa=provider,
        countContextInstructionVa=count_context,allocationCallVa=allocation,markerBytes=1,countBytes=0 if count==-1 else 4,
        keyReferenceBytes=8,valueReferenceBytes=8,initiallyNullOutputRequired=True,referenceOutputBytes=8,
        normalReturn=True,entryRspRestored=True,allIntegerNonvolatilesRestored=True,callbackGrammarAdmitted=False,
        frame=dict(entryRspDelta=-120,rspToRbp=64,callShadowRsp=[0,32],countRbp=[-32,-28],keyRbp=[-24,-16],valueRbp=[-16,-8],
            keyArgumentEntryRsp=[32,40],valueArgumentEntryRsp=[8,16],headerThenValueArgumentEntryRsp=[8,16],
            savedEntryRbx=[16,24],pushedNonvolatiles=['rbp','rsi','rdi','r12','r13','r14','r15']))


def count_program(regions,entry,offsets):
    cur,rem,adv,used=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec20','8379'+rem+'04','488bfa','488bd9');g.branch('0f8c',False)
    g.take('488b41'+cur,'8b00','8907','8b7b'+rem,'83c7fc');g.branch('0f88',False)
    g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','897b'+rem,'488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,wireBytes=4,outputBytes=4,resultAbi='void-byref-output-rdx',
        readerRegister='rcx',allFourReaderUpdatesProved=True,rawBitsPreserved=True,entryRspRestored=True,
        nonvolatileRegistersRestored=['rbx','rdi'])


def insertion_program(regions,entry):
    g=BytesPath(regions,entry)
    g.take('48895c2408','48896c2410','4889742418','57','4883ec20','488b7910','498bd9','498bf0','488bea','4885ff')
    g.branch('75',True,1)
    g.take('498b4120','488b88c0000000','488b4130','4883782000');g.branch('75',True,1)
    g.take('488b4320','4c8bc6','488bd5','488bcf','4c8b88c0000000','4d8b4930',
        '488b5c2430','488b6c2438','488b742440','4883c420','5f')
    target=g.relative('e9')
    return dict(selectedBytes=g.seen,innerDictionaryFieldOffset=16,underlyingSetterTargetVa=target,
        sameKeyAndValueReferences=True,sameMethodInfoContextSlot=6,normalTailReturn=True,entryRspRestored=True,
        insertionOutcomeAdmitted=False)

"""Exact Boolean list programs; callbacks, layouts and contexts are separate.

Only a fresh list with count-sized capacity, initialized coherent contexts,
normal helper effects and the independently selected callback is admitted.
No reused list, growth, refill or effective runtime provider choice is proved.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(key,condition):
    if not condition:raise ValueError('actionValueListProgram.'+key)


def boolean(regions,entry,s,*,count):
    need('Boolean-count-witness',type(count)is int and count in(-1,0,1,2,3))
    g=BytesPath(regions,entry)
    g.take('4053','55','56','57','4883ec38');flag=g.relative('803d');g.take('00','498be9','498bd8','488bf2');g.branch('74',False,1)
    g.take('33ff','488d542420','488bce','897c2420','40887c2468');g.call(s['header']);g.take('84c0');g.branch('0f85',count!=-1)
    cell=None;loop=backedge=None
    if count==-1:
        g.take('488bcb','48893b');g.call(s['barrier'])
    else:
        g.take('4c89642460','4c896c2470','4c89742430','48393b');g.branch('74',True,1)
        g.take('488b4d20','33d2','488b89c0000000');g.call(s['context']);g.take('488bc8');g.call(s['allocate'])
        g.take('4c8bf0','4885c0');g.branch('0f84',False)
        g.take('488b4d20','488b91c0000000','488b4a08','48397920');g.branch('75',True,1)
        g.take('488b4520','498bce','8b542420','4c8b80c0000000','4d8b4008');g.call(s['constructor'])
        g.take('488bcb','4c8933');g.call(s['barrier']);cell=g.relative('488b0d')
        g.take('39b9e0000000');g.branch('75',True,1)
        g.take('488b4520','488b88c0000000','488b4918');g.call(s['provider']);g.take('4c8bf0','397c2420');g.branch('7e',count==0,1)
        loop=g.at
        for index in range(max(count,0)):
            need('Boolean-same-loop-head',g.at==loop)
            g.take('c644246800','4d85f6');g.branch('74',False,1)
            g.take('4c8d4c2468','4c8bc6','498bd6');g.call(s['dispatch'])
            g.take('4c8b23','440fb66c2468','4d85e4');g.branch('74',False,1)
            g.take('488b4520','4c8b80c0000000','498b4030','4883782000');g.branch('75',True,1)
            g.take('488b4520','410fb6d5','498bcc','4c8b80c0000000','4d8b4030');g.call(s['add'])
            g.take('ffc7','3b7c2420');backedge=g.at;g.branch('7c',index+1<count,1)
        g.take('4c8b6c2470','4c8b642460','4c8b742430');g.jump('e9')
    g.take('4883c438','5f','5e','5d','5b','c3')
    return dict(selectedBytes=g.seen,countWitness=count,newList=True,elementReads=max(count,0),
        providerClassCell=cell,loopHead=loop,backedge=backedge,managedElementBytes=1,
        initializedFlag=flag,elementTemporaryOffset=104,elementBitsPreserved=8,
        counter='edi',savedCount='entry stack + 32 after prologue',completeFrameRestored=True)




def capacity(regions,entry,s,*,boolean,positive):
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec20','8bda','498bf8','488bf1','85d2');g.branch('0f88',False)
    g.take('498b4820','488b89c0000000');g.branch('0f84'if boolean else'74',not positive,4 if boolean else 1)
    if positive:
        g.take('ba01000000');g.call(s['context']);g.take('8bd3','488bc8');g.call(s['arrayAllocate'])
    else:
        g.take('33d2');g.call(s['context']);g.take('83b8e000000000');g.branch('75'if boolean else'74',boolean,1)
        g.take('488b4f20','33d2','488b89c0000000');g.call(s['context']);g.take('488b88b8000000','488b01');g.jump('e9'if boolean else'eb',4 if boolean else 1)
    g.take('488d4e10','48894610','488b5c2430','488b742438','4883c420','5f')
    need('capacity-same-barrier',g.relative('e9')==s['barrier'])
    return dict(selectedBytes=g.seen,positiveCapacity=positive,requestedCapacityUnchanged=True,
        itemsSlot=16,countWrites=0,versionWrites=0,normalReturnViaBarrier=True)


def provider(regions,entry,s,*,boolean):
    g=BytesPath(regions,entry)
    if boolean:g.take('48895c2408','4889742410','57','4883ec20','4883793800','488bf9');g.branch('75',True,1);g.take('488b5f38')
    else:g.take('48895c2410','57','4883ec20','4883793800','488bf9');g.branch('74',False,1)
    tc=g.relative('488b0d')
    if boolean:g.take('488b1b');g.call(s['classInit'])
    else:g.take('488b5f38','83b9e000000000','488b1b');g.branch('0f84',False)
    g.take('33d2','488bcb');g.call(s['typeHandle']);pc=g.relative('488b0d');g.take('488bd8')
    if boolean:g.call(s['classInit'])
    else:g.take('83b9e000000000');g.branch('74',False,1)
    g.take('488bcb');g.call(s['backend']);g.take('488b4f38','ba01000000','488bd8');g.call(s['context'])
    g.take('488bd0','488bcb');g.call(s['cast']);g.take('4885c0');g.branch('0f85'if boolean else'0f84',boolean)
    if boolean:g.take('488b5c2430','488b742438')
    else:g.take('488b5c2438')
    g.take('4883c420','5f','c3')
    return dict(selectedBytes=g.seen,typeClassCell=tc,providerClassCell=pc,
        typeContextSlot=0,resultTypeContextSlot=1,backendReferenceReturnedUnchanged=True)


def boolean_callback(regions,entry,offsets,advance):
    g=BytesPath(regions,entry);rem=bytes((offsets['bufferLength'],)).hex();cur=bytes((offsets['currentPtr'],)).hex()
    g.take('48895c2408','57','4883ec20','837a'+rem+'01','498bf8','488bda');g.branch('7d',True,1)
    g.take('488b42'+cur,'0fb600','ba01000000','488bcb','8807','488b5c2430','4883c420','5f')
    need('Boolean-same-Advance',g.relative('e9')==advance)
    return dict(selectedBytes=g.seen,wireBytes=1,outputBytes=1,preservedBits=8,
        numericNormalization=False,normalReturnViaProvedAdvance=True)


def boolean_add(regions,entry):
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec20','ff411c','488bd9','488b4910','498bf0','0fb6fa','4c634b18','4885c9');g.branch('74',False,1)
    g.take('443b4918');g.branch('72',True,1)
    g.take('418d4101','894318','443b4918');g.branch('73',False,1)
    g.take('41887c0920');g.jump('eb',1)
    g.take('488b5c2430','488b742438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,arrayStrideBytes=1,arrayElementOffset=32,storedBits=8,
        sizeIncrement=1,versionIncrement=1,normalReturn=True,spareCapacityRequired=True)

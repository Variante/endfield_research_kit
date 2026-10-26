"""Exact selected ASCII UTF8 programs; no runtime invocation or Unicode grant."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check,condition):
    if not condition:raise ValueError('patrolEncoding.'+check)


def cached_getter_program(regions,entry):
    g=BytesPath(regions,entry);g.take('4053','4883ec20');site=g.at;cell=g.relative('488b05')
    g.take('488b88b8000000','488b4120','f0830c2400','4885c0');g.branch('74',False,1)
    site2=g.at;need('same-cached-Encoding-class-cell',g.relative('488b05')==cell)
    g.take('488b88b8000000','488b4120','f0830c2400','4883c420','5b','c3')
    return dict(selectedBytes=g.seen,classUsages=[dict(instructionVa=at,cellVa=cell,typeName='System.Text.Encoding')for at in(site,site2)],
        staticStorageClassOffset=184,cachedFieldOffset=32,cachedFieldBytes=8,sameCachedReferenceReturned=True,
        cachedReferenceNonnullAndStableRequired=True,frameBytes=40,callShadow=[0,32],entryRspRestored=True,
        restoredNonvolatiles=['rbx'],effectCalls=0,coldCacheCreationProved=False,liveEncodingClassObserved=False)


def string_wrapper_program(regions,entry,*,length):
    need('finite-ASCII-length',type(length)is int and 0<=length<=127)
    g=BytesPath(regions,entry);calls=[];uses=[]
    def call(role):
        at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target))
    g.take('48895c2410','48896c2418','4889742420','57','4154','4157','4883ec40',
        '488bbc2480000000','418bf1','4963e8','4c8bfa','4c8be1','4885d2');g.branch('0f84',False)
    g.take('4885ff');g.branch('0f84',False);g.take('4585c0');g.branch('0f88',False)
    g.take('4585c9');g.branch('0f88',False);g.take('8b4210','2bc5','413bc1');g.branch('0f8c',False)
    g.take('48639c2488000000','85db');g.branch('0f88',False);g.take('3b5f18');g.branch('0f8f',False)
    g.take('4c89742460','448b7718','442bf3');at=g.at;cell=g.relative('488b0d');uses.append(dict(instructionVa=at,cellVa=cell,role='spanImplicit'))
    g.take('488b4920');call('readyContext');ready=g.relative('803d')+1;g.take('00');g.branch('0f84',False)
    at=g.at;cell=g.relative('488b0d');uses.append(dict(instructionVa=at,cellVa=cell,role='memoryReference'));g.take('4883793800');g.branch('74',False,1)
    g.take('498b0c24');call('prepareEncodingClass')
    g.take('498b0c24','488d450a','498d1447','448bc6','4c8d4b20','4c03cf','488b8198020000',
        '4c8b9190020000','498bcc','4889842490000000','48c784248800000000000000','4489b42480000000',
        '4c8b742460','488b5c2468','488b6c2470','488b742478','4883c440','415f','415c','5f')
    tail=g.at;g.take('49ffe2')
    return dict(selectedBytes=g.seen,length=length,calls=calls,contextUsages=uses,metadataReadyFlagVa=ready,
        inputStringNonnullRequired=True,inputByteArrayNonnullRequired=True,stringIndex=0,stringCount=length,byteIndex=0,
        inputStringLengthEqualsCountRequired=True,byteArrayCapacityAtLeastCountRequired=True,
        utf16CharacterDataOffset=20,byteArrayDataOffset=32,internalTailInstructionVa=tail,
        internalCallbackClassOffset=656,internalMethodInfoClassOffset=664,internalLogicalSlot=21,
        internalArguments=dict(rcx='same actual Encoding receiver',rdx='same string+20',r8d='same length',
            r9='same byte array+32',stack5='same byte-array capacity',stack6=0,stack7='same actual slot21 MethodInfo'),
        tailRestoresEntryRspAndOwnNonvolatiles=True,frameBytes=88,callShadow=[0,32],callerProvidedHomeSpaceUsed=[[8,32]],
        outgoingTailArgumentHomes=[[40,44],[48,56],[56,64]],normalContextAndClassPreparationRequired=True,
        actualInternalCallbackIdentityRequired=True,runtimeCallbackSelectionObserved=False)


def ascii_internal_program(regions,entry,*,length,source_alignment):
    """Every payload code unit is universally constrained to unsigned0..127.

    The cursor tracks source/output indices symbolically. Packed DWORD loads
    select four UTF16 units; little-endian byte lanes map each to its own low
    byte. This does not enumerate concrete strings or accept non-ASCII data.
    """
    need('finite-ASCII-domain',type(length)is int and 0<=length<=127 and type(source_alignment)is int and source_alignment in(0,2))
    g=BytesPath(regions,entry);uses=[];written=[];chunks=[];i=j=0
    def use(prefix,name):
        at=g.at;cell=g.relative(prefix);uses.append(dict(instructionVa=at,cellVa=cell,typeName=name))
    def write(n,mode):
        nonlocal i,j
        start=i;written.extend(range(i,i+n));chunks.append(dict(sourceIndex=i,outputIndex=j,count=n,mode=mode));i+=n;j+=n
        need('bounded-symbolic-ASCII-copy',i<=length and j==i)
    def restore():
        g.take('33ff','4c8b7c2430','488bac2498000000','4d85ff');g.branch('0f85',False)
        g.take('488b9c2490000000','2bf5','8bc6','4883c440','415f','415e','415d','415c','5f','5e','5d','c3')
    g.take('48895c2418','4c894c2420','4889542410','48894c2408','55','56','57','4154','4155','4156','4157',
        '4883ec40','4c63a424a0000000','4533ed','4963c0','4d03e1','33ff','48c744243000000000',
        '4c8bf2','488bda','498bf1','4c8d3c42','488b8424a8000000','4885c0');g.branch('0f85',False);g.take('8bef')
    outer=g.at
    while True:
        need('same-owned-ASCII-outer-head',g.at==outer)
        g.take('493bdf');g.branch('0f83',i>=length)
        if i>=length:
            g.take('85ff');g.branch('0f85',False);g.take('4d85ed');g.branch('0f85',False);restore();break
        g.take('85ff');g.branch('0f8f',False);g.take('4d85ed');g.branch('0f85',False)
        g.take('0fb73b','4883c302');use('488b0d','System.Text.UTF8Encoding')
        g.take('83b9e000000000');g.branch('0f84',False)
        g.take('8d870028ffff','3dff030000');g.branch('76',False,1)
        use('488b0d','System.Text.UTF8Encoding');g.take('83b9e000000000');g.branch('0f84',False)
        g.take('8d870028ffff','3dff070000');g.branch('0f86',False)
        g.take('b901000000','83ff7f');g.branch('0f8f',False)
        g.take('498bc4','482bc1','483bf0');g.branch('0f87',False)
        g.take('83ff7f');g.branch('0f8f',False);g.take('40883e','48ffc6');write(1,'scalar')
        g.take('4d85ed');g.branch('0f85',False);use('488b0d','System.Text.UTF8Encoding')
        g.take('83b9e000000000');g.branch('0f84',False)
        g.take('418bc7','418bcc','2bc3','2bce','d1e8','83f80d');remaining=length-i;g.branch('77',remaining>13,1)
        g.take('3bc8');g.branch('0f8c',False)
        if remaining<=13:
            head=g.at
            while True:
                need('same-owned-ASCII-scalar-head',g.at==head)
                g.take('493bdf');g.branch('73',i>=length,1)
                if i>=length:restore();break
                g.take('0fb73b','4883c302','83ff7f');g.branch('0f87',False)
                g.take('40883e','48ffc6');write(1,'scalar');g.jump('eb',1)
            break
        g.take('4c63f0','4983c6fb','4e8d3473','493bde');limit=length-5;g.branch('0f83',i>=limit)
        need('long-ASCII-peel-required',i<limit)
        g.take('0fb73b','4883c302','83ff7f');g.branch('0f87',False)
        g.take('40883e','48ffc6');write(1,'alignment-scalar')
        g.take('f6c302');unaligned=(source_alignment+i*2)&2;g.branch('0f85',bool(unaligned))
        if unaligned:
            g.take('0fb73b','4883c302','83ff7f');g.branch('0f87',False)
            g.take('40883e','48ffc6');write(1,'alignment-scalar');g.jump('e9')
        g.take('493bde');g.branch('73',i>=limit,1)
        if i<limit:
            g.take('660f1f440000');head=g.at
            while True:
                need('same-owned-ASCII-packed-head',g.at==head and (source_alignment+i*2)%4==0)
                g.take('8b6b04','8bc5','8b3b','0bc7','a980ff80ff');use('488b05','System.BitConverter')
                g.branch('0f85',False);g.take('83b8e000000000');g.branch('0f84',False)
                g.take('488b80b8000000','8bcf','8bd5','c1f910','c1fa10','803800');g.branch('0f84',False)
                g.take('40883e','884e01','40886e02','885603','4883c604','4883c308');write(4,'packed-little-endian')
                g.take('493bde');g.branch('72',i<limit,1)
                if i>=limit:break
            g.take('493bde');g.branch('0f82',False)
        g.take('4c8bb42488000000','33ff','488b6c2430');g.jump('e9')
    need('complete-ASCII-input-output-index-induction',i==j==length and written==list(range(length)))
    return dict(selectedBytes=g.seen,length=length,sourceAlignmentModulo4=source_alignment,classUsages=uses,
        characterDomain=dict(minimum=0,maximum=127,codeUnitBytes=2),byteOutputCount=length,
        outputByteToInputCodeUnit=written,copyChunks=chunks,asciiMask=0xff80ff80,
        packedLittleEndianStaticFlagRequired=any(c['mode']=='packed-little-endian'for c in chunks),
        exactOneLowBytePerInputCodeUnit=True,inputAndDestinationDisjointRequired=True,byteCapacityAtLeastLengthRequired=True,
        inputPointerLow32RangeDoesNotWrapRequired=True,destinationPointerLow32RangeDoesNotWrapRequired=True,
        nullEncoderStateRequired=True,selectedClassesAlreadyInitializedRequired=True,
        frameBytes=120,callShadow=[0,32],callerProvidedHomeSpaceUsed=[[8,40]],entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],effectCalls=0,
        unicodeFallbackProved=False,runtimeStringOrBufferObserved=False)

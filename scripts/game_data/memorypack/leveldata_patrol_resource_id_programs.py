"""Selected normal proxy handle construction and ID storage byte programs."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check,condition):
    if not condition:raise ValueError('patrolResourceIds.'+check)


def constructor(regions,entry,*,kind='bundle',compatibility='first',frame=True):
    need('finite-constructor-selection',kind in('bundle','prefab')and compatibility in('first','second','neither')and type(frame)is bool)
    g=BytesPath(regions,entry);calls=[];uses=[]
    def call(role):
        at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target))
    def usage(role,prefix):
        at=g.at;cell=g.relative(prefix);uses.append(dict(role=role,instructionVa=at,cellVa=cell));return cell
    g.take('48895c2408','4889742410','57','4883ec20','410fb6f0','488bda','488bf9','4885d2');g.branch('0f84',False)
    g.take('488b0a','8b911c010000','81ea');discriminator=int.from_bytes(g.read(4),'little');g.branch('0f84',kind=='prefab')
    if kind=='bundle':g.take('83fa01');g.branch('0f85',False);g.take('8b839c000000')
    else:g.take('8b83a0000000');g.jump('e9')
    g.take('894704','4088770d','c7471000000000');usage('firstType','488b15');g.take('488b0b');call('compatibleClass')
    g.take('84c0');g.branch('0f84',compatibility!='first')
    if compatibility=='first':g.take('8b83a0000000','894708');root=g.relative('488b05');g.take('c6470c00')
    else:
        usage('secondType','488b15');g.take('488b0b');call('compatibleClass');g.take('84c0');g.branch('74',compatibility=='neither',1)
        if compatibility=='second':g.take('8b83a4000000','894708','c6470c03')
        else:g.take('33c0','894708','c6470c02')
        g.jump('eb',1);root=None
    # The first-type path owns the replacement and optional frame load. The
    # other two paths jump directly to the shared GetID dispatch.
    if compatibility=='first':
        g.take('488b4878','4885c9');g.branch('0f85',False)
        g.take('0fb68380000000','84c0');g.branch('75',not frame,1)
        if frame:
            first=usage('versionClass','488b0d');g.take('83b9e000000000');g.branch('0f84',False)
            ready=g.relative('803d')+1;g.take('00');g.branch('0f84',False)
            need('same-version-class',usage('versionClass','488b0d')==first);g.take('83b9e000000000');g.branch('0f84',False)
            need('same-version-class',usage('versionClass','488b05')==first);g.take('488b88b8000000','8b01','894710')
        else:ready=None
    else:ready=None
    g.take('488b0b','8b911c010000','81ea');need('same-owned-class-discriminator',int.from_bytes(g.read(4),'little')==discriminator)
    g.branch('74',kind=='prefab',1)
    if kind=='bundle':g.take('83fa01');g.branch('0f85',False)
    g.take('33d2','488bcb');call('bundleRetainHandle'if kind=='bundle'else'prefabRetainHandle')
    if kind=='prefab':g.jump('eb',1)
    g.take('488b5c2430','488b742438','8907','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,calls=calls,typedUsages=uses,kind=kind,compatibility=compatibility,
        incomingProxyRequiredNonnull=True,classDiscriminatorOffset=284,requiredClassDiscriminator=discriminator+(kind=='bundle'),
        inputProxyFieldToOutput=[dict(sourceOffset=156 if kind=='bundle'else 160,outputOffset=4,bytes=4)]
            +([]if compatibility=='neither'else[dict(sourceOffset=160 if compatibility=='first'else 164,outputOffset=8,bytes=4)]),
        outputIdOffset=0,outputIdFromSameProxyRetainHandle=True,outputCategoryOffset=12,outputCategory={'first':0,'second':3,'neither':2}[compatibility],
        outputLogChannelOffset=13,outputLogChannelByteFromIncomingR8bUnchanged=True,mainVersionOffset=16,versionClassStaticFieldOffset=0,
        mainVersionFromSameReadyStaticInt32=compatibility=='first'and frame,mainVersionZeroOtherwise=True,
        metadataReadyFlagVa=ready,replacementRootCellVa=root,selectedReplacementAbsentRequired=compatibility=='first',
        outputBytes=20,outputPaddingByteRanges=[[14,16]],paddingUntouched=True,callerInitiallyZeroedOutputRequired=True,
        frameBytes=40,callShadow=[0,32],entryRspRestored=True,restoredNonvolatiles=['rbx','rsi','rdi'],runtimeProxyClassObserved=False)


def counter(regions,entry):
    g=BytesPath(regions,entry);g.take('4883ec28');ready=g.relative('803d')+1;g.take('00');g.branch('74',False,1)
    at=g.at;cls=g.relative('488b05');g.take('83b8e000000000');g.branch('74',False,1)
    g.take('488b88b8000000','448b01','418bc0','418d5001','8911','4883c428','c3')
    return dict(selectedBytes=g.seen,readyFlagCellVa=ready,classUsage=dict(instructionVa=at,cellVa=cls),staticFieldOffset=0,
        returns='previous Int32 counter bits',storedValue='previous counter plus one modulo2^32',counterAtomic=False,
        frameBytes=40,entryRspRestored=True,allNonvolatilesUnchanged=True,effectCalls=0,liveCounterOrUniquenessObserved=False)


def bundle_retain_handle(regions,entry,*,added=True):
    need('literal-compact-add-outcome',type(added)is bool);g=BytesPath(regions,entry);calls=[];uses=[]
    def call(role):
        at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target))
    def usage(role):
        at=g.at;cell=g.relative('488b0d');uses.append(dict(role=role,instructionVa=at,cellVa=cell));return cell
    g.take('4053','4881ecb0000000');root=g.relative('488b05');g.take('488bd9','488b4878','4885c9');g.branch('74',True,1)
    usage('counterClass');g.take('4c89bc2480000000','83b9e000000000');g.branch('75',True,1);call('counter')
    usage('poolClass');g.take('448bf8','83b9e000000000');g.branch('75',True,1)
    g.take('488d8bb0000000','418bd7');call('compactAdd');g.take('84c0');g.branch('0f84',not added)
    diagnostic=None
    if added:
        diagnostic=usage('diagnosticClass');g.take('83b9e000000000');g.branch('75',True,1)
        g.take('488b81b8000000','80781200');g.branch('0f84',True)
    g.take('418bc7','4c8bbc2480000000','4881c4b0000000','5b','c3')
    return dict(selectedBytes=g.seen,calls=calls,typedUsages=uses,replacementRootCellVa=root,selectedReplacementAbsentRequired=True,
        compactSetFieldOffset=176,compactInputIsCounterResult=True,compactAdded=added,returnedIdIsCounterResult=True,
        optionalDiagnosticClassCellVa=diagnostic,optionalDiagnosticStaticBoolOffset=18,diagnosticFlagRequiredFalse=added,
        frameBytes=184,callShadow=[0,32],entryRspRestored=True,restoredNonvolatiles=['rbx','r15'],runtimeIdOrDiagnosticFlagObserved=False)


def prefab_retain_handle(regions,entry,*,set_present=False):
    need('literal-prefab-ID-set-selection',type(set_present)is bool);g=BytesPath(regions,entry)
    g.take('4057','4883ec20');root=g.relative('488b05');g.take('488bf9','488b4878','4885c9');g.branch('0f85',False)
    at=g.at;cls=g.relative('488b0d');g.take('48895c2430','83b9e000000000');g.branch('74',False,1)
    callsite=g.at;count=g.relative('e8');g.take('4883bf9000000000','8bd8');g.branch('74',not set_present,1);add=None;usage=None
    if set_present:
        g.take('4889742438','488bb790000000');site=g.at;cell=g.relative('488b3d');usage=dict(instructionVa=site,cellVa=cell)
        g.take('488b4720','488b90c0000000','488b8280000000','4883782000');g.branch('0f84',False)
        g.take('488b4720','8bd3','488bce','4c8b80c0000000','4d8b8080000000');site=g.at;target=g.relative('e8')
        add=dict(instructionVa=site,targetVa=target);g.take('488b742438')
    g.take('8bc3','488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,selectedReplacementAbsentRequired=True,
        classUsage=dict(instructionVa=at,cellVa=cls),counterCall=dict(instructionVa=callsite,targetVa=count),
        idSetFieldOffset=144,setRequiredNonnull=set_present,addCall=add,addContextUsage=usage,addContextSlotOffset=128,
        setInputIsSameCounterResult=True,returnedIdIsCounterResult=True,
        frameBytes=40,callShadow=[0,32],entryRspRestored=True,restoredNonvolatiles=['rbx','rdi']+(['rsi']if set_present else[]))


def hierarchy_ready(regions,entry):
    g=BytesPath(regions,entry);g.take('4053','4883ec20','488bd9','0fb6813a010000','90','a804');g.branch('75',True,1)
    g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,requiredClassFlagOffset=314,requiredClassFlagMask=4,selectedFlagSetRequired=True,
        nonframeWrites=0,effectCalls=0,frameBytes=40,entryRspRestored=True,restoredNonvolatiles=['rbx'])


def compatible_class(regions,entry,*,matches=True):
    need('literal-class-compatible-selection',type(matches)is bool);g=BytesPath(regions,entry)
    g.take('48895c2410','57','4883ec20','488bfa','488bd9','0fb6813a010000','90','a804');g.branch('75',True,1)
    g.take('488bcf');at=g.at;target=g.relative('e8');g.take('0fb68732010000','388332010000');g.branch('72',False,1)
    g.take('0fb6c8','488b83c8000000','48397cc8f8');g.branch('75',not matches,1)
    g.take('b001'if matches else'32c0','488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,prepareHierarchyCall=dict(instructionVa=at,targetVa=target),
        sourceReadyFlagOffset=314,sourceReadyMask=4,classDepthOffset=306,sourceHierarchyOffset=200,
        targetDepthPositiveRequired=True,sourceDepthAtLeastTargetRequired=True,
        result=matches,selectedHierarchyElementIsTargetClass=matches,returnsNormalizedBool=True,
        frameBytes=40,entryRspRestored=True,restoredNonvolatiles=['rbx','rdi'],nonframeWrites=0)


def compact_add(regions,entry,*,count=0,match=0,overflow=False,added=True):
    need('finite-inline-compact-count',type(count)is int and 0<=count<=4 and type(match)is int and 0<=match<=count
        and type(overflow)is bool and type(added)is bool)
    need('existing-overflow-or-inline-spare',overflow or count<4 or match>0)
    g=BytesPath(regions,entry);g.take('48895c2420','57','4883ec20');flag=g.relative('803d')+1
    g.take('00','488bd9','8bfa');g.branch('0f84',False);g.take('48837b1800','48896c2430','4889742438');g.branch('75',overflow,1)
    add=None;usage=None
    if overflow:
        g.take('488b7318','4885f6');g.branch('0f84',False);at=g.at;cell=g.relative('488b2d');usage=dict(instructionVa=at,cellVa=cell)
        g.take('488b4520','488b90c0000000','488b8280000000','4883782000');g.branch('0f84',False)
        g.take('488b4520','8bd7','488bce','4c8b80c0000000','4d8b8080000000');at=g.at;target=g.relative('e8');add=dict(instructionVa=at,targetVa=target)
        g.take('84c0');g.branch('0f84',not added)
        if added:g.take('ff03');g.jump('eb',1)
    else:
        for i in range(1,5):
            g.take('833b'+bytes((i,)).hex());g.branch('7c'if i==1 else'0f8d',count<i if i==1 else count>=i,1 if i==1 else 4)
            if count<i:continue
            if i in(2,4):g.take('488b43'+('08'if i==2 else'10'),'48c1f820','3bc7');g.branch('0f85',match!=i)
            else:
                g.take('397b'+('08'if i==1 else'10'));g.branch('0f84'if i==1 else'0f85',match==i if i==1 else match!=i)
            if match==i:
                if i!=1:g.jump('e9')
                break
        if not match:
            g.take('833b00');g.branch('74',count==0,1)
            if count==0:g.take('48897b08','c70301000000')
            else:
                g.take('833b01');g.branch('0f85',count!=1)
                if count==1:g.take('488bc7','c70302000000','48c1e020','48094308');g.jump('eb',1)
                else:
                    g.take('833b02');g.branch('75',count!=2,1)
                    if count==2:g.take('48897b10','c70303000000');g.jump('e9')
                    else:g.take('833b03');g.branch('75',False,1);g.take('488bc7','c70304000000','48c1e020','48094310');g.jump('e9')
            g.take('b001')
    if overflow and added:g.take('b001')
    if match or(overflow and not added):g.take('32c0');g.jump('e9')
    g.take('488b742438','488b6c2430','488b5c2448','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,readyFlagCellVa=flag,overflowSetFieldOffset=24,overflowSelected=overflow,
        countFieldOffset=0,inlineIdFields=[[8,4],[12,4],[16,4],[20,4]],incomingIdRegister='edx',incomingIdBitsUnchanged=True,
        countBefore=count if not overflow else None,countAfter=count+1 if not overflow and not match else count if not overflow else None,
        matchedSlot=match,result=added if overflow else not bool(match),otherInlineBitsPreserved=True,
        unusedPackedHighHalfRequiredZero=not overflow and not match and count in(1,3),
        packedInvariant='The unused high32 half is zero in valid inline count1/3 state; low-half insertion writes a zero-extended full QWORD and high-half insertion ORs the incoming Int32 bits shifted32.',
        addCall=add,addContextUsage=usage,addContextSlotOffset=128,overflowCountIncrementIffAdded=overflow,
        overflowCreationOrResizeProved=False,frameBytes=40,callShadow=[0,32],entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi'])


def hashset_add(regions,entry,*,misses=(),duplicate=False,reuse_free=False,interface_steps=0):
    need('finite-int-set-chain',type(misses)in(tuple,list)and len(misses)<=4096 and all(type(x)is bool for x in misses)
        and type(duplicate)is bool and type(reuse_free)is bool and type(interface_steps)is int and 0<=interface_steps<=64)
    g=BytesPath(regions,entry);calls=[]
    def call(role):
        at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
    g.take('48895c2410','55','56','57','4154','4155','4156','4157','4883ec40','4533ed','4c63e2','4d8bf8','488bd9','41be01000000','4c396910');g.branch('0f84',False)
    g.take('498b4720','488b88c0000000','488b8188000000','4c396820');g.branch('0f84',False)
    g.take('498b4720','488b88c0000000','488b8988000000','488b7330','4885f6');g.branch('0f84',False)
    g.take('488b4920','ba12000000','488b89c0000000');resolve=call('indexedContext')
    g.take('488b2e','488bf8','488bcd');call('prepareClass')
    g.take('440fb78530010000','410fb7cd','66453be8');g.branch('73',False,1)
    g.take('488b95b0000000');head=g.at
    for i in range(interface_steps+1):
        need('same-HashSet-hash-interface-head',g.at==head);g.take('0fb7c1','4803c0','48393cc2');g.branch('74',i==interface_steps,1)
        if i<interface_steps:g.take('66ffc1','66413bc8');g.branch('72',True,1)
    g.take('0fb7c9','4803c9','8b44ca08','ffc0','4898','4883c014','48c1e004','4803c5','4c8b08','488b7808')
    other=g.relative('488d05');g.take('4c3bc8');g.branch('0f84',False)
    selected=g.relative('488d05');g.take('4c3bc8');g.branch('0f84',True)
    root=g.relative('488b05');g.take('488b4840','4885c9');g.branch('74',True,1)
    g.take('418bec');g.jump('e9')
    g.take('488b4b10','0fbaf51f','4885c9');g.branch('0f84',False)
    g.take('488b7b18','8bc5','99','f77918','4863f2','3b7118');g.branch('0f83',False)
    g.take('448b74b120','4183ee01');g.branch('0f89',bool(misses)or duplicate)
    sequence=list(misses)+([True]if duplicate else[]);loop=None;first=True
    for i,equal_hash in enumerate(sequence):
        if first:g.take('4885ff');g.branch('0f84',False);loop=g.at;first=False
        need('same-HashSet-collision-head',g.at==loop)
        g.take('443b7718');g.branch('0f83',False);g.take('4963c6','488d0c40','396c8f20');g.branch('0f84',equal_hash)
        final=duplicate and i==len(sequence)-1
        if equal_hash:
            g.take('4963c6','488d0c40','8b448f28','89842480000000','488b4330','4889842498000000','4885c0');g.branch('0f84',False)
            g.take('498b4f20','ba12000000','488b89c0000000');need('same-HashSet-equality-context',call('indexedContext')==resolve)
            g.take('448b8c2480000000','488bd0','4c8b842498000000','33c9','4489642420');call('keyEquals')
            g.take('84c0');g.branch('0f84',not final)
            if final:g.take('32c0');g.jump('e9');break
        g.take('443b6f18');g.branch('0f8d',False)
        g.take('41ffc5','443b7718');g.branch('0f83',False)
        g.take('4963c6','4883c003','488d0440','448b3487','4585f6');g.branch('0f88',i+1==len(sequence))
        if i+1<len(sequence):g.jump('eb',1)
    if not duplicate:
        g.take('837b2800');g.branch('0f8d',reuse_free)
        if reuse_free:
            g.take('48635328','4885ff');g.branch('0f84',False);g.take('3b5718');g.branch('0f83',False)
            g.take('488d4203','488d0440','8b0c87','894b28');g.jump('e9')
        else:
            g.take('8b4324','4885ff');g.branch('0f84',False);g.take('3b4718');g.branch('0f84',False)
            g.take('8b5324','ff4324','4885ff');g.branch('0f84',False);g.take('3b5718');g.branch('0f83',False)
        if reuse_free:g.take('3b5718');g.branch('0f83',False)
        g.take('4863c2','488d0c40','896c8f20','3b5718');g.branch('0f83',False)
        g.take('4863c2','488d0c40','4489648f28','488b4b10','4885c9');g.branch('0f84',False)
        g.take('3b7118');g.branch('0f83',False)
        g.take('4863c6','448b448120','41ffc8','3b5718');g.branch('0f83',False)
        g.take('4863c2','4883c003','488d0440','44890487','4c8b4310','4d85c0');g.branch('0f84',False)
        g.take('413b7018');g.branch('0f83',False)
        g.take('4863c6','8d4a01','41894c8020','b001','ff4320','ff4338')
    g.take('488b9c2488000000','4883c440','415f','415e','415d','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,calls=calls,bucketsOffset=16,slotsOffset=24,countOffset=32,lastIndexOffset=36,freeListOffset=40,
        comparerOffset=48,versionOffset=56,bucketBytes=4,slotBytes=12,slotHashOffset=0,slotNextOffset=4,slotValueOffset=8,
        inputInt32BitsUnchanged=True,selectedInt32HashCallbackVa=selected,excludedOtherHashCallbackVa=other,
        selectedReplacementRootCellVa=root,selectedReplacementReceiverOffset=64,selectedReplacementAbsentRequired=True,
        hashIsInt32BitsWithSignBitCleared=True,misses=list(misses),duplicate=duplicate,reuseFreeSlot=reuse_free,
        normalizedResult=not duplicate,countDelta=0 if duplicate else 1,versionDelta=0 if duplicate else 1,
        lastIndexDelta=0 if duplicate or reuse_free else 1,versionIncrementModulo32=True,sourceIndexAndCollisionGuards=True,
        insertionWrites='slot={hash,next=previous bucket-1,value=full input Int32}; bucket=slotIndex+1',
        duplicateHasNoNonframeWrites=duplicate,freeHeadAdvancesToSelectedSlotNext=reuse_free and not duplicate,
        nonemptyBucketsAndSpareSlotCapacityRequired=True,coherentStableAcyclicStorageRequired=True,
        storageCountBound=4096,induction='Each bounded collision follows one 12-byte slot next index; raw equality is tested only after matching cleared hash. A duplicate returns without mutation; a final negative next reaches exactly one insertion and count/version increment.',
        frameBytes=120,callShadow=[0,32],callerProvidedHomeSpaceUsed=[[8,40]],entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],allocationAndResizeProved=False,
        liveSetContentsOrComparerSelectionObserved=False)


def compact_promote(regions,entry):
    g=BytesPath(regions,entry);calls=[];uses=[]
    def call(role):
        at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
    def usage(role,prefix):
        at=g.at;cell=g.relative(prefix);uses.append(dict(role=role,instructionVa=at,cellVa=cell));return cell
    g.take('48895c2420','57','4883ec20');flag=g.relative('803d')+1
    g.take('00','488bd9','8bfa');g.branch('0f84',False)
    g.take('48837b1800','48896c2430','4889742438');g.branch('75',False,1)
    g.take('833b01');g.branch('7c',False,1);g.take('397b08');g.branch('0f84',False)
    g.take('833b02');g.branch('0f8d',True);g.take('488b4308','48c1f820','3bc7');g.branch('0f85',True)
    g.take('833b03');g.branch('0f8d',True);g.take('397b10');g.branch('0f85',True)
    g.take('833b04');g.branch('0f8d',True);g.take('488b4310','48c1f820','3bc7');g.branch('0f85',True)
    g.take('833b00');g.branch('74',False,1);g.take('833b01');g.branch('0f85',True)
    g.take('833b02');g.branch('75',True,1);g.take('833b03');g.branch('75',True,1)
    usage('compactClass','488b05');g.take('83b8e000000000');g.branch('0f84',False)
    g.take('488b80b8000000','488b08','4885c9');g.branch('0f84',False)
    usage('allocate','488b15');call('poolAllocate');g.take('488d4b18','48894318');call('barrier')
    g.take('488b7318','4885f6');g.branch('0f84',False);usage('ensureCapacity','488b2d')
    g.take('48837e1800');g.branch('0f84',False);g.take('488b4618','83781808');g.branch('0f8c',False)
    slots=[]
    for i in range(5):
        g.take('488b4b18')
        if i==1:g.take('488b5308')
        elif i==3:g.take('488b5310')
        g.take('4885c9');g.branch('74'if i==4 else'0f84',False,1 if i==4 else 4)
        usage('seedAdd','4c8b05')
        if i in(0,2):g.take('8b53'+('08'if i==0 else'10'))
        elif i in(1,3):g.take('48c1fa20')
        else:g.take('8bd7')
        call('seedAdd');slots.append([8,12,16,20,'incoming'][i])
    g.take('33c0','c70305000000','48894308','48894310');g.jump('e9')
    g.take('b001','488b742438','488b6c2430','488b5c2448','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,calls=calls,typedUsages=uses,readyFlagCellVa=flag,countBefore=4,countAfter=5,
        overflowSetInitiallyNullRequired=True,pooledSetRequiredNonnullAndEmpty=True,pooledSetSlotsCapacityAtLeast8Required=True,
        pairwiseDistinctOldAndNewIdsRequired=True,seedSourceByteOffsets=slots,seedIdsFullInt32BitsUnchanged=True,
        installedSetFieldOffset=24,packedFieldsZeroed=[[8,8],[16,8]],normalResult=True,
        ensureCapacityNotInvokedOnSelectedSparePath=True,frameBytes=40,callShadow=[0,32],entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi'],freshHeapAllocationOrPoolConstructionProved=False)


def seed_add(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','498b4020','498bd8','8bfa','488bf1',
        '4c8b80c0000000','498b8080000000','4883782000');g.branch('0f84',False)
    g.take('488b4320','8bd7','488bce','4c8b80c0000000','4d8b8080000000','488b5c2430','488b742438','4883c420','5f');target=g.relative('e9')
    return dict(selectedBytes=g.seen,addTargetVa=target,contextSlotOffset=128,sameSetAndInt32BitsPassedUnchanged=True,
        frameBytes=40,entryRspRestored=True,restoredNonvolatiles=['rbx','rsi','rdi'],tailCall=True)

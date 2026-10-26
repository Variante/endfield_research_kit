"""Exact selected proxy-storage lookup bytes, reusable at an owned caller cursor.

This parser proves relative storage effects and actual call arguments. It never
assigns a nominal type to a pointer, calls the game or invents an extent for a
leaf. The enclosing owner authenticates fields, contexts, complete windows and
the selected normal helper effects.
"""


def need(check,condition):
    if not condition:raise ValueError('patrolProxyStorage.'+check)


def proxy_table_program(g,*,output_home,context_home,interface_steps=0,misses=(),hit=True,profile='validity'):
    """Consume the default nonzero unsigned-ID TryGetValue source, leaving RSI/ref-out.

    Entry is the literal CMP DWORD [R12+8],0. ``misses`` selects either a hash
    mismatch (False) or matching hash/different key (True) before the final hit
    or null next node. Helpers are derived from actual E8s, never supplied as
    interchangeable aliases. A caller may replay the same grammar at its own
    exact entry and independently bind every returned role.
    """
    need('finite-caller-profile',profile in('validity','object-get','asset-get'))
    object_get=profile!='validity';asset_get=profile=='asset-get'
    need('finite-own-frame-and-chain',type(output_home)is int and 128<=output_home<256
        and (context_home is None if object_get else type(context_home)is int and 32<=context_home<256)
        and type(interface_steps)is int and 0<=interface_steps<=64
        and type(hit)is bool and isinstance(misses,(list,tuple))and len(misses)<=4096
        and all(type(v)is bool for v in misses))
    start=len(g.seen);calls=[];usages=[]
    def call(role):
        at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
    def use(prefix,role):
        at=g.at;cell=g.relative(prefix);usages.append(dict(role=role,instructionVa=at,cellVa=cell));return cell
    def stack(prefix,offset):return prefix+offset.to_bytes(4,'little').hex()
    g.take('44397708'if asset_get else'833900'if object_get else'41837c240800');g.branch('77',True,1)
    if object_get and not asset_get:g.take('486319')
    cls=use('488b0d','storageClass')
    if asset_get:g.take('48635f08')
    elif not object_get:g.take('49635c2408')
    g.take('4439b1e0000000'if asset_get else'83b9e000000000');g.branch('75',True,1)
    if asset_get:ready=g.relative('443835')
    else:ready=g.relative('803d')+1;g.take('00')
    g.branch('75',True,1)
    if asset_get:g.take('498bc6')
    else:g.take('33f6','8bc6')
    g.take(stack('48898424',output_home))
    need('same-storage-class-first',use('488b0d','storageClass')==cls);g.take('4439b1e0000000'if asset_get else'39b1e0000000');g.branch('75',True,1)
    need('same-storage-class-second',use('488b05','storageClass')==cls)
    g.take('488b88b8000000','4c8b29','4d85ed');g.branch('0f84',False)
    method=use('4c8b25'if object_get else'488b05','tryGetContext')
    if not object_get:
        if context_home<128:g.take('48894424'+bytes((context_home,)).hex())
        else:g.take(stack('48898424',context_home))
    g.take('498b7d18','4885ff');g.branch('0f84',False)
    g.take('498b4c2420'if object_get else'488b4820','ba0c000000','488b89c0000000');context=call('indexedContext')
    g.take('4c8b3f','488be8'if asset_get else'4c8bf0','498bcf');prepare=call('prepareClass')
    g.take('450fb78730010000','410fb7ce'if asset_get else'0fb7ce','be01000000'if asset_get else'bd01000000','66453bf0'if asset_get else'66413bf0');g.branch('73',False,1)
    g.take('498b97b0000000')
    # The two actual callers differ only in this fixed alignment spelling.
    if bytes(g.bytes.get(g.at+i,0)for i in range(4))==bytes.fromhex('0f1f4000'):g.take('0f1f4000')
    elif bytes(g.bytes.get(g.at+i,0)for i in range(10))==bytes.fromhex('66660f1f840000000000'):g.take('66660f1f840000000000')
    head=g.at
    for i in range(interface_steps+1):
        need('same-interface-head',g.at==head)
        g.take('0fb7c1','4803c0','48392cc2'if asset_get else'4c3934c2');g.branch('74',i==interface_steps,1)
        if i<interface_steps:g.take('66ffc1','66413bc8');g.branch('72',True,1)
    g.take('0fb7c9','4803c9','8b44ca08','ffc0','4898','4883c014','48c1e004','4903c7');g.jump('eb',1)
    g.take('4c8b08','4c8b7808');hash_callback=g.relative('488d05')
    g.take('4c3bc8');g.branch('75',False,1)
    g.take('498b4720','488b88c0000000','488b39','4c397738'if asset_get else'48837f3800');g.branch('75',True,1)
    g.take('488b4738','488b08','4c397138'if asset_get else'4883793800');g.branch('75',True,1)
    g.take('8beb'if asset_get else'448bf3');g.jump('e9')
    if not object_get:
        if context_home<128:g.take('488b7c24'+bytes((context_home,)).hex())
        else:g.take(stack('488bbc24',context_home))
    g.take('498b4c2420'if object_get else'488b4f20','488b91c0000000','488b8ae8000000','4c397120'if asset_get else'4883792000');g.branch('75',True,1)
    g.take('498b442420'if object_get else'488b4720','498b7d10','488b88c0000000')
    if object_get:g.take('4c8ba1e8000000')
    else:g.take('488b81e8000000',stack('48898424',output_home-8))
    fence='f044093424'if asset_get else'f0830c2400'
    g.take(fence,'4885ff');g.branch('0f84',False)
    g.take('488b7710'if asset_get else'488b6f10','4885f6'if asset_get else'4885ed');g.branch('0f84',False)
    g.take('498b4c2420'if object_get else'488b4820','ba02000000','488b89c0000000');need('same-indexed-context-second',call('indexedContext')==context)
    g.take('4439b0e0000000'if asset_get else'83b8e000000000');g.branch('75',True,1)
    g.take('488b7f10','4885ff');g.branch('0f84',False)
    g.take('8bc5'if asset_get else'418bc6','0fbaf01f','99','f77e18'if asset_get else'f77d18','3b5718');g.branch('0f83',False)
    g.take('4863c2','488b7cc720',fence,'4885ff')
    empty=not misses and not hit;g.branch('0f84'if object_get and not asset_get else'74',empty,4 if object_get and not asset_get else 1)
    if not empty and bytes(g.bytes.get(g.at+i,0)for i in range(3))==bytes.fromhex('0f1f00'):g.take('0f1f00')
    chain_head=g.at;equals=None
    for i,key_miss in enumerate([*misses,*([True]if hit else[])]):
        need('same-concurrent-node-head',g.at==chain_head)
        final=hit and i==len(misses)
        g.take('3b6f28'if asset_get else'443b7728');g.branch('75',not key_miss,1)
        if key_miss:
            g.take('498b7518'if asset_get else'498b6d18','448b7f10','4885f6'if asset_get else'4885ed');g.branch('0f84',False)
            if object_get:g.take('498b4c2420','ba0c000000','488b89c0000000')
            else:g.take(stack('488b8424',output_home-8),'ba0c000000','488b4820','488b89c0000000')
            need('same-indexed-context-third',call('indexedContext')==context)
            g.take('488bd0','895c2420','33c9','458bcf','4c8bc6'if asset_get else'4c8bc5');target=call('keyEquals')
            need('same-key-equality-dispatch',equals is None or equals==target);equals=target
            g.take('84c0');g.branch('75'if object_get and not asset_get else'0f85',final,1 if object_get and not asset_get else 4)
        if final:
            if asset_get:
                collector=g.relative('443935');g.take('488b4718',stack('48898424',output_home));g.branch('0f84',True)
            else:
                collector=g.relative('833d')+1;g.take('00','488b7718',stack('4889b424',output_home));g.branch('74'if object_get else'0f84',True,1 if object_get else 4)
        else:
            g.take('488b7f20',fence,'4885ff');g.branch('75',i+1<len(misses)or hit,1)
    if not hit:
        if asset_get:g.take('498bc6')
        elif object_get and not empty:g.jump('eb',1)
        elif not object_get:g.take('33c0',stack('48898424',output_home))
        collector=None
    return dict(selectedBytes=g.seen[start:],nextInstructionVa=g.at,calls=calls,classUsages=usages,
        metadataReadyFlagVa=ready,storageClassCellVa=cls,actualTryGetContextCellVa=method,
        selectedHashCallbackVa=hash_callback,selectedHashEffect='same incoming Int32 bits',
        contextTargetVa=context,preparationTargetVa=prepare,keyEqualityTargetVa=equals,
        interfaceMisses=interface_steps,nodeMisses=list(misses),found=hit,referenceOutputHome=[output_home,output_home+8],
        comparerFieldOffset=24,tablesFieldOffset=16,nodeHashOffset=40,nodeKeyOffset=16,nodeValueOffset=24,nodeNextOffset=32,
        nonzeroUnsignedProxyIdRequired=True,proxyIdOffset=8,proxyIdBytes=4,hashSignBitCleared=True,
        bucketsModuloPositiveLengthRequired=True,collectorFlagVa=collector,collectorDisabledRequired=hit,
        staticStorageAndContextsReadyRequired=True,nonnullStableTypedStorageRequired=True,
        selectedInterfaceCallbackAndMethodInfoPairRequired=True,chainAcyclicAndWithinFiniteBoundRequired=4096,
        actualClassOrTableSelectionObserved=False)


def key_equality_program(g,*,interface_steps=0):
    """Actual Int32 interface-Equals dispatcher, selected first inline body."""
    need('bounded-interface-witness',type(interface_steps)is int and 0<=interface_steps<=64)
    start=len(g.seen)
    g.take('48895c2408','48896c2410','4889742418','48897c2420','4156','4883ec30',
        '498b38','418bf1','0fb7e9','4d8bf0','488bcf','488bda')
    prepare=g.relative('e8')
    g.take('440fb79730010000','33c0','66413bc2');g.branch('73',False,1)
    g.take('488b97b0000000');head=g.at
    for i in range(interface_steps+1):
        need('same-key-equality-interface-head',g.at==head)
        g.take('0fb7c8','4803c9','48391cca');g.branch('74',i==interface_steps,1)
        if i<interface_steps:g.take('66ffc0','66413bc2');g.branch('72',True,1)
    g.take('0fb7d0','488b87b0000000','4803d2','8b44d008','03c5','4898','4883c014','48c1e004','4803c7','4c8b10','4c8b4808')
    callback=g.relative('488d05');g.take('4c3bd0');g.branch('75',False,1)
    g.take('3b742460','0f94c0','488b5c2440','488b6c2448','488b742450','488b7c2458','4883c430','415e','c3')
    return dict(selectedBytes=g.seen[start:],preparationTargetVa=prepare,selectedCallbackVa=callback,
        requiredSelector=0,interfaceMisses=interface_steps,incomingStoredKeyRegister='r9d',incomingRequestedKeyHome=[96,100],
        selectedResult='same two Int32 bits compare equal',returnsNormalizedBool=True,frameBytes=56,callShadow=[0,32],
        entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','r14'],nonframeWrites=0,
        selectedInterfaceCallbackAndMethodInfoPairRequired=True)


def disposed_program(g,*,kind='direct',state_disposed=False,replacement_present=False,wrapper_mode='null'):
    """Exact selected literal-class state/recursive-wrapper disposal predicate."""
    need('finite-proxy-disposal-modes',kind in('direct','wrapper')and type(state_disposed)is bool
        and type(replacement_present)is bool and wrapper_mode in('null','child-disposed','child-ready'))
    start=len(g.seen);entry=g.at
    g.take('4053','4883ec20','488b11','488bd9','8b821c010000','2d')
    class_start=int.from_bytes(g.read(4),'little');g.branch('74',kind=='wrapper',1)
    if kind=='direct':g.take('83f801');g.branch('0f85',False)
    root=g.relative('488b05');g.take('488b4878','4885c9');g.branch('0f85',replacement_present)
    if replacement_present:
        g.take('488b81'+('20c70000'if kind=='wrapper'else'a0da0000'),'4885c0');g.branch('0f84',True)
    recursive=None
    if kind=='direct':g.take('837b3804');g.branch('74',state_disposed,1)
    else:
        g.take('48837b1000');g.branch('74',wrapper_mode=='null',1)
        if wrapper_mode!='null':
            g.take('488b4b10','33d2');recursive=g.relative('e8');need('same-own-recursive-disposal-entry',recursive==entry)
            g.take('84c0');g.branch('75',wrapper_mode=='child-disposed',1)
    literal_true=state_disposed if kind=='direct'else wrapper_mode!='child-ready'
    if literal_true:g.take('b001');g.jump('eb',1)
    elif kind=='direct':g.take('32c0')
    else:g.take('0fb683b2000000')
    g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen[start:],requiredClassDiscriminator=class_start+(kind=='direct'),classDiscriminatorOffset=284,
        selectedReplacementRootCellVa=root,selectedReplacementAbsentRequired=True,kind=kind,
        stateFieldOffset=56 if kind=='direct'else 178,requiredDisposedState=4 if kind=='direct'else None,
        stateMatchesDisposed=state_disposed if kind=='direct'else None,wrapperMode=wrapper_mode if kind=='wrapper'else None,
        recursiveTargetVa=recursive,recursiveChildFieldOffset=16 if kind=='wrapper'else None,
        result='literal true'if literal_true else'literal false'if kind=='direct'else'own stored Bool byte zero-extended',
        frameBytes=40,callShadow=[0,32],entryRspRestored=True,restoredNonvolatiles=['rbx'],nonframeWrites=0,
        acyclicSelectedWrapperChainWithinFiniteBoundRequired=32 if kind=='wrapper'else 0,
        runtimeClassOrDisposalStateObserved=False)


def inline_ids_program(g,*,count=1,match=1):
    """Selected concrete proxy's inline ID set, no overflow HashSet selection."""
    need('finite-inline-proxy-ID-set',type(count)is int and 0<=count<=4 and type(match)is int and 0<=match<=count)
    start=len(g.seen);g.take('48895c2408','57','4883ec20','488bd9','8bfa','488b09','448b811c010000','4181e8')
    kind=int.from_bytes(g.read(4),'little')+1;g.branch('0f84',False)
    g.take('4183f801');g.branch('0f85',False)
    root=g.relative('488b05');g.take('488b4878','4885c9');g.branch('0f85',False)
    cls_site=g.at;cls=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
    ready=g.relative('803d')+1;g.take('00');g.branch('0f84',False)
    g.take('4883bbc800000000');g.branch('75',False,1)
    for i in range(1,5):
        g.take('83bbb0000000'+bytes((i,)).hex());g.branch('7c',count<i,1)
        if count<i:continue
        if i in(2,4):g.take('488b83'+('b8000000'if i==2 else'c0000000'),'48c1f820','3bc7')
        else:g.take('39bb'+('b8000000'if i==1 else'c0000000'))
        if i==1:g.branch('75',match!=1,1)
        else:g.branch('74'if i==2 else'0f84',match==i,1 if i==2 else 4)
        if match==i:break
    if not match:g.take('32c0');g.jump('e9')
    else:g.take('b001')
    g.take('488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen[start:],requiredClassDiscriminator=kind,classDiscriminatorOffset=284,
        replacementRootCellVa=root,selectedReplacementReceiverRequiredNull=True,classUsageInstructionVa=cls_site,classCellVa=cls,
        metadataReadyFlagVa=ready,requiredInlineCount=count,matchingSlot=match,
        overflowSetFieldOffset=200,overflowSetRequiredNull=True,countFieldOffset=176,
        inlineIdFields=[[184,4],[188,4],[192,4],[196,4]],inputIdRegister='edx',inputIdBitsUnchanged=True,
        result=bool(match),returnsNormalizedBool=True,frameBytes=40,callShadow=[0,32],entryRspRestored=True,
        restoredNonvolatiles=['rbx','rdi'],nonframeWrites=0,normalEffectCalls=0)


def compatible_interface_program(g,*,interface_steps=0):
    """Nonnull source class contains the exact nongeneric target interface."""
    need('bounded-assignable-interface-witness',type(interface_steps)is int and 0<=interface_steps<=64)
    start=len(g.seen);calls=[]
    def call(role):
        at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target))
    g.take('48895c2420','4889542410','48894c2408','55','56','57','4154','4155','4156','4157','4883ec20',
        '4c8be2','4c8bf9','483bca');g.branch('0f84',False)
    g.take('0f1f00','498bcf');call('prepareType');g.take('498bcc');call('prepareType')
    g.take('498bcf');call('prepareOffsets');g.take('498bcc');call('prepareOffsets')
    g.take('41f6871401000020');g.branch('0f85',True)
    g.take('49837f6000');g.branch('0f84',True)
    g.take('4d85e4');g.branch('0f84',False);g.take('33db','0f1f840000000000')
    g.take('6641399c242e010000');g.branch('76',False,1)
    g.take('498bcc');call('prepareInterfaces')
    g.take('0fb7cb','410fb794242e010000','663bda');g.branch('73',False,1)
    g.take('4d8b8424a8000000','0f1f4000');head=g.at
    for i in range(interface_steps+1):
        need('same-assignability-interface-head',g.at==head)
        g.take('0fb7c1','4d393cc0');g.branch('0f84',i==interface_steps)
        if i<interface_steps:g.take('66ffc1','663bca');g.branch('72',True,1)
    g.take('b001','488b5c2478','4883c420','415f','415e','415d','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen[start:],calls=calls,targetInterfaceRegister='rcx',sourceClassRegister='rdx',
        exactTypePointerMatchInOwnInterfaceArray=True,targetNongenericRequired=True,targetInterfaceFlagOffset=276,
        targetInterfaceFlagMask=32,sourceInterfaceCountOffset=302,sourceInterfaceArrayOffset=168,
        sourceInterfaceMisses=interface_steps,result=True,returnsNormalizedBool=True,frameBytes=88,callShadow=[0,32],
        entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],
        nonframeWrites=0,selectedNormalPreparationEffectsRequired=True)


def ready_program(g,*,role):
    """Three independently owned preparation functions' exact warm returns."""
    need('finite-ready-role',role in('type','offsets','interfaces'));start=len(g.seen)
    if role=='type':
        g.take('48895c2410','57','4883ec20','488bd9','f6813801000002');g.branch('0f85',True)
        g.take('488b5c2438','4883c420','5f','c3');offset=312;mask=2;frame=40;restored=['rbx','rdi']
    elif role=='interfaces':
        g.take('48895c2410','4889742418','57','4883ec20','488bf9','0fb6813a010000','90','a801');g.branch('0f85',True)
        g.take('488b5c2438','488b742440','4883c420','5f','c3');offset=314;mask=1;frame=40;restored=['rbx','rsi','rdi']
    else:
        g.take('48895c2418','55','56','57','4154','4155','4156','4157','4883ec30','488bd9','0fb6813a010000','90','a808');g.branch('0f85',True)
        g.take('488b9c2480000000','4883c430','415f','415e','415d','415c','5f','5e','5d','c3')
        offset=314;mask=8;frame=104;restored=['rbx','rbp','rsi','rdi','r12','r13','r14','r15']
    return dict(selectedBytes=g.seen[start:],role=role,literalReadyFlagOffset=offset,literalRequiredMask=mask,
        nonframeWrites=0,effectCalls=0,frameBytes=frame,callShadow=[0,32],entryRspRestored=True,
        restoredNonvolatiles=restored,coldPreparationEffectsProved=False,liveFlagStateObserved=False)


def hashset_program(g,*,empty_buckets=False,empty_bucket=False,misses=(),hit=True,interface_steps=0):
    """Actual closed Int32 HashSet.Contains selected inline callback paths.

    Miss witnesses independently choose unequal hash (False) or unequal key
    with equal hash (True). The source counter limits a corrupt chain by the
    actual slots length; finite replay witnesses do not impose a new wire cap.
    """
    need('finite-hashset-witness',type(interface_steps)is int and 0<=interface_steps<=64
        and type(misses)in(tuple,list)and len(misses)<=4096 and all(type(x)is bool for x in misses)
        and all(type(x)is bool for x in(empty_buckets,empty_bucket,hit)))
    start=len(g.seen);calls=[];markers={}
    def call(role):
        at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target))
    def restore():
        g.take('488b9c2490000000','4883c440','415f','415e','415d','415c','5f','5e','5d','c3')
    g.take('48895c2418','89542410','55','56','57','4154','4155','4156','4157','4883ec40',
        '4883791000','4d8bf8','4c63f2','488bd9');g.branch('0f84',empty_buckets)
    if not empty_buckets:
        g.take('498b4020','4c8b88c0000000','498b8188000000','4883782000');g.branch('0f84',False)
        g.take('498b4720','488b88c0000000','488b8988000000','488b7330','4885f6');g.branch('0f84',False)
        g.take('488b4920','ba12000000','488b89c0000000');call('indexedContext')
        g.take('488b2e','488bf8','488bcd');call('prepareClass')
        g.take('440fb78530010000','4533ed','410fb7cd','41bc01000000','66453be8');g.branch('73',False,1)
        g.take('488b95b0000000');head=g.at
        for i in range(interface_steps+1):
            need('hashset-own-hash-interface-head',g.at==head)
            g.take('0fb7c1','4803c0','48393cc2');g.branch('74',i==interface_steps,1)
            if i<interface_steps:g.take('66ffc1','66413bc8');g.branch('72',True,1)
        g.take('0fb7c9','4803c9','8b44ca08','ffc0','4898','4883c014','48c1e004','4803c5','4c8b08','488b7808')
        markers['hash']=g.relative('488d05');g.take('4c3bc8');g.branch('0f84',True)
        g.take('488b4720','488b88c0000000','488b39','4c396f38');g.branch('0f84',False)
        g.take('488b4738','488b08','4c396938');g.branch('0f84',False)
        g.take('418bee');g.jump('e9')
        g.take('4c8b4310','0fbaf51f','488b7318','4d85c0');g.branch('0f84',False)
        g.take('8bc5','99','41f77818','413b5018');g.branch('0f83',False)
        g.take('4863c2','418b7c8020','83ef01');g.branch('0f88',empty_bucket)
        if not empty_bucket:
            g.take('660f1f840000000000','4489ac2480000000','4885f6');g.branch('0f84',False);head=g.at
            sequence=list(misses)+([True]if hit else[])
            need('nonempty-hashset-selected-chain',bool(sequence))
            for i,equal_hash in enumerate(sequence):
                need('hashset-own-node-head',g.at==head)
                final=hit and i==len(sequence)-1
                g.take('3b7e18');g.branch('0f83',False)
                g.take('4863c7','488d0c40','396c8e20');g.branch('0f85',not equal_hash)
                if equal_hash:
                    g.take('4c8b6330','4863c7','488d0c40','448b6c8e28','4d85e4');g.branch('0f84',False)
                    g.take('498b4f20','ba12000000','488b89c0000000');call('indexedContext')
                    g.take('4d8b3424','498bce','4889842498000000');call('prepareClass')
                    g.take('450fb78630010000','33c0','4c8b8c2498000000','0fb7c8','66413bc0');g.branch('73',False,1)
                    g.take('498b96b0000000');eqhead=g.at
                    for j in range(interface_steps+1):
                        need('hashset-own-equality-interface-head',g.at==eqhead)
                        g.take('0fb7c1','4803c0','4c390cc2');g.branch('74',j==interface_steps,1)
                        if j<interface_steps:g.take('66ffc1','66413bc8');g.branch('72',True,1)
                    g.take('0fb7c9','4803c9','486344ca08','4883c014','48c1e004','4903c6','4c8b10','4c8b4808')
                    marker=g.relative('488d05');need('same-hashset-inline-equality-marker',markers.get('equals',marker)==marker);markers['equals']=marker
                    g.take('4c3bd0');g.branch('0f85',False)
                    g.take('443bac2488000000','0f94c0','84c0');g.branch('74',not final,1)
                    if final:g.take('b001');restore();break
                g.take('8b8c2480000000','3b4e18');g.branch('0f8d',False)
                g.take('ffc1','898c2480000000','3b7e18');g.branch('0f83',False)
                g.take('4863c7','4883c003','488d0440','8b3c86','85ff');g.branch('0f89',i<len(sequence)-1)
            if hit:
                return _hashset_result(g,start,calls,markers,misses,True,interface_steps)
    g.take('32c0');g.jump('eb',1);restore()
    result=_hashset_result(g,start,calls,markers,misses,False,interface_steps)
    result.update(bucketsRequiredNull=empty_buckets,selectedBucketEmpty=empty_bucket)
    return result


def _hashset_result(g,start,calls,markers,misses,hit,interface_steps):
    return dict(selectedBytes=g.seen[start:],calls=calls,selectedInlineCallbackMarkers=markers,
        bucketArrayFieldOffset=16,slotsArrayFieldOffset=24,comparerFieldOffset=48,
        bucketElementBytes=4,bucketIndexIsOneBased=True,slotElementBytes=12,
        slotFields=dict(hash=0,next=4,value=8),arrayDataOffset=32,arrayLengthOffset=24,
        hashClearsSignBit=True,hashIsInputInt32Bits=True,keyEqualityIsRawInt32Bits=True,
        selectedMisses=list(misses),interfaceMisses=interface_steps,result=hit,returnsNormalizedBool=True,
        sourceChainCounterGuard='visited count less than slots.Length before each next',
        sourceNodeIndexGuard='unsigned index less than slots.Length',cyclicOrInvalidStateEffectsProved=False,
        selectedReadyClosedContextRequired=True,selectedComparerCallbacksMatchOwnInlineMarkersRequired=True,
        frameBytes=120,callShadow=[0,32],callerProvidedHomeSpaceUsed=[[8,40]],entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],liveSetContentsObserved=False)


def set_ids_program(g,*,kind='direct',set_present=True):
    """ContainsID's own selected set field and exact restored tail ABI."""
    need('finite-set-proxy-kind',kind in('direct','wrapper')and type(set_present)is bool)
    start=len(g.seen);g.take('48895c2408','57','4883ec20','488bd9','8bfa','488b09','448b811c010000','4181e8')
    class_start=int.from_bytes(g.read(4),'little');g.branch('0f84',kind=='wrapper');usage=None;cls=None;ready=None
    if kind=='direct':
        need('direct-overflow-set-present',set_present)
        g.take('4183f801');g.branch('0f85',False)
        root=g.relative('488b05');g.take('488b4878','4885c9');g.branch('0f85',False)
        cls_at=g.at;cls=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
        ready=g.relative('803d')+1;g.take('00');g.branch('0f84',False)
        g.take('4883bbc800000000');g.branch('75',True,1)
        usage_at=g.at;cell=g.relative('4c8b05');g.take('8bd7','488b8bc8000000');field=200
    else:
        root=g.relative('488b05');g.take('488b4878','4885c9');g.branch('0f85',False)
        g.take('488b8b90000000','4885c9');g.branch('74',not set_present,1);field=144
        if set_present:
            usage_at=g.at;cell=g.relative('4c8b05')
        else:g.take('32c0');g.jump('e9')
    g.take('488b5c2430','4883c420','5f')
    if set_present:
        target=g.relative('e9');usage=dict(instructionVa=usage_at,cellVa=cell,contextRegister='r8')
    else:g.take('c3');target=None
    return dict(selectedBytes=g.seen[start:],kind=kind,requiredClassDiscriminator=class_start+(kind=='direct'),
        classDiscriminatorOffset=284,replacementRootCellVa=root,selectedReplacementReceiverRequiredNull=True,
        classUsage=None if cls is None else dict(instructionVa=cls_at,cellVa=cls),metadataReadyFlagVa=ready,
        setFieldOffset=field,setRequiredNonnull=set_present,hashSetUsage=usage,tailTargetVa=target,
        requestedInt32BitsUnchanged=True,returnsNormalizedBool=True,result=False if not set_present else'own HashSet.Contains result',
        frameBytes=40,entryRspRestored=True,restoredNonvolatiles=['rbx','rdi'],nonframeWrites=0)

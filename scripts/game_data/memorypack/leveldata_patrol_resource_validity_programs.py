"""Actual resource validity/getter callers with explicit selected child joins."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import leveldata_patrol_proxy_storage_programs as storage


def need(check,condition):
    if not condition:raise ValueError('patrolResourceValidity.'+check)


def object_getter_program(regions,entry,*,hit=True,misses=()):
    g=BytesPath(regions,entry);g.take('4883ec78');root=g.relative('4c8b05')
    g.take('498b4078','4885c0');g.branch('74',True,1)
    g.take('48899c2480000000','48896c2470','4889742468','48897c2460','4c89642458',
        '4c896c2450','4c89742448','4c897c2440','4885c0');g.branch('74',True,1)
    table=storage.proxy_table_program(g,output_home=152,context_home=None,profile='object-get',misses=misses,hit=hit)
    g.take('4c8b742448','488bc6','488b742468','4c8b6c2450','4c8b642458','488b7c2460',
        '488b6c2470','488b9c2480000000','4c8b7c2440','4883c478','c3')
    return dict(selectedBytes=g.seen,table=table,replacementRootCellVa=root,
        selectedReplacementReceiverAt120RequiredNull=True,inputIdPointerRegister='rcx',inputIdOffset=0,
        returnedReference='same selected table value'if hit else'literal null',frameBytes=120,callShadow=[0,32],
        callerProvidedHomeSpaceUsed=[[32,40]],entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],liveStorageObserved=False)


def proxy_getter_program(regions,entry,*,hit=True,misses=()):
    g=BytesPath(regions,entry);calls=[];usages=[]
    def call(role):
        at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target))
    g.take('48894c2408','57','4883ec70');root=g.relative('488b05')
    g.take('488bf9','488b4878','4885c9');g.branch('74',True,1)
    g.take('488d5708','4885c9');g.branch('74',True,1)
    g.take('833a00','0f97c1','48899c2488000000','48896c2468','4889742460','4c89642458','4c896c2450',
        '4c89742448','4c897c2440','84c9');g.branch('0f84',False)
    g.take('488b4878','4533f6','4885c9');g.branch('74',True,1)
    table=storage.proxy_table_program(g,output_home=152,context_home=None,profile='asset-get',misses=misses,hit=hit)
    g.take('488bbc2480000000','4885c0');g.branch('0f84',not hit)
    if hit:
        g.take('488d4f08','33d2');call('objectGet')
        at=g.at;cell=g.relative('488b1d');usages.append(dict(role='proxyInterface',instructionVa=at,cellVa=cell))
        g.take('488bf8','4885c0');g.branch('0f84',False)
        g.take('488b30','488bcb','488bd6');call('compatibleInterface')
        g.take('84c0');g.branch('0f85',True);g.take('488bc7');g.jump('eb',1)
    else:g.take('33c0')
    g.take('4c8b742448','4c8b6c2450','4c8b642458','488b742460','488b6c2468','488b9c2488000000',
        '4c8b7c2440','4883c470','5f','c3')
    return dict(selectedBytes=g.seen,table=table,calls=calls,classUsages=usages,replacementRootCellVa=root,
        selectedReplacementReceiverAt120RequiredNull=True,proxyIdOffset=8,
        sameInputIdPointerPassedToObjectGet=True,selectedInterfaceCompatibilityRequired=hit,
        returnedReference='same actual ObjectHandle.Get reference'if hit else'literal null',
        sameStableTableAndKeyRequired=True,frameBytes=120,callShadow=[0,32],callerProvidedHomeSpaceUsed=[[32,40]],
        entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],liveProxyObserved=False)


def validity_program(regions,entry,*,kind,outcome='valid',misses=(),object_kind='direct'):
    need('finite-validity-caller',kind in('created','output')and outcome in('zero-id','lookup-miss','membership-miss','asset-id-zero','object-id-mismatch','disposed','valid')and object_kind in('direct','wrapper'))
    g=BytesPath(regions,entry);calls=[];usages=[];table=None
    def call(role):
        at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target))
    def use(role,prefix):
        at=g.at;cell=g.relative(prefix);usages.append(dict(role=role,instructionVa=at,cellVa=cell));return cell
    if kind=='created':
        g.take('4889542410','4154','4883ec70');ready=g.relative('803d')+1
        g.take('00','4c8be1');g.branch('75',True,1);root=g.relative('488b05')
        g.take('48899c2480000000','48896c2468','4889742460','488b4878','48897c2458','4c896c2450','4c89742448','4c897c2440')
    else:
        g.take('4154','4883ec70');root=g.relative('488b05');g.take('4c8be1','488b4878','4885c9');g.branch('74',True,1)
        ready=g.relative('803d')+1;g.take('00');g.branch('75',True,1)
        g.take('488b4878','48899c2480000000','48896c2468','4889742460','48897c2458','4c896c2450','4c89742448','4c897c2440')
    g.take('4885c9');g.branch('74',True,1)
    g.take('498d542408','4885c9');g.branch('74',True,1)
    g.take('833a00','0f97c1','84c9');g.branch('74',outcome=='zero-id',1)
    failed=outcome=='zero-id'
    if not failed:
        g.take('488b4878','4885c9');g.branch('74',True,1)
        table=storage.proxy_table_program(g,output_home=144 if kind=='created'else 152,
            context_home=152 if kind=='created'else 48,hit=outcome!='lookup-miss',misses=misses)
        g.take('4885f6');g.branch('0f84',outcome=='lookup-miss');failed=outcome=='lookup-miss'
    if not failed:
        g.take('498d4c2408','33d2');call('objectGet');use('proxyInterface','488b1d')
        g.take('488bf8','4885c0');g.branch('0f84',False)
        g.take('488b30','488bcb','488bd6');call('compatibleInterface');g.take('84c0');g.branch('75',True,1)
        g.take('418b1424','488bcf');call('containsId');g.take('84c0');g.branch('0f84',outcome=='membership-miss')
        failed=outcome=='membership-miss'
    if not failed:
        use('assetIdClass','488b0d');g.take('83b9e000000000');g.branch('75',True,1)
        need('same-replacement-root-after-membership',g.relative('488b05')==root)
        g.take('4c8b4878','4d85c9');g.branch('0f84',True)
        g.take('83b9e000000000');g.branch('75',True,1)
        g.take('41837c240400');g.branch('0f86',outcome=='asset-id-zero');failed=outcome=='asset-id-zero'
    if not failed:
        g.take('33d2','498bcc');call('proxyGet');g.take('4885c0');g.branch('0f84',False)
        g.take('488b10','448b821c010000','4181e8');class_start=int.from_bytes(g.read(4),'little')
        g.branch('74',object_kind=='wrapper',1)
        if object_kind=='direct':g.take('4183f801');g.branch('74',True,1);g.take('8b989c000000');g.jump('eb',1)
        else:g.take('8b98a0000000')
        use('assetIdClass','488b0d');g.take('418b7c2404','83b9e000000000');g.branch('75',True,1)
        need('same-replacement-root-before-ID-compare',g.relative('488b05')==root)
        g.take('4c8b5078','4d85d2');g.branch('74',True,1)
        g.take('83b9e000000000');g.branch('75',True,1)
        g.take('3bdf');g.branch('0f85',outcome=='object-id-mismatch');failed=outcome=='object-id-mismatch'
    else:class_start=None
    if not failed:
        g.take('33d2','498bcc');call('proxyGet');g.take('4885c0');g.branch('74',False,1)
        g.take('488bc8');call('disposed');g.take('84c0')
        if kind=='created':g.take('0f94c0');g.jump('e9')
        else:
            g.branch('0f85',outcome=='disposed')
            if outcome!='disposed':g.take('b001');g.jump('e9')
            else:g.take('32c0')
    else:g.take('32c0')
    if kind=='created':g.take('4c8b7c2440','4c8b742448','4c8b6c2450','488b7c2458','488b742460','488b6c2468','488b9c2480000000')
    else:g.take('4c8b742448','4c8b6c2450','488b7c2458','488b742460','488b6c2468','488b9c2480000000','4c8b7c2440')
    g.take('4883c470','415c','c3')
    return dict(selectedBytes=g.seen,kind=kind,outcome=outcome,table=table,calls=calls,classUsages=usages,
        replacementRootCellVa=root,metadataReadyFlagVa=ready,selectedReplacementReceiverAt120RequiredNull=True,
        proxyIdOffset=8,inputMembershipIdOffset=0,assetObjectIdOffset=4,assetIdPositiveUnsignedRequired=outcome not in('zero-id','lookup-miss','membership-miss','asset-id-zero'),
        requiredProxyClassDiscriminator=None if class_start is None else class_start+(object_kind=='direct'),
        selectedProxyObjectIdOffset=None if class_start is None else 156 if object_kind=='direct'else 160,
        sameStableProxyTableAndKeyRequired=True,returnsNormalizedBool=True,result=outcome=='valid',
        frameBytes=120,callShadow=[0,32],entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],liveHandleValidityObserved=False)

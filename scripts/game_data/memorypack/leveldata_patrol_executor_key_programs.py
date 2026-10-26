"""Selected reference-value event-key storage, with no nominal pointer aliases."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag


def key_request(regions,entry,*,set_value):
    g=BytesPath(regions,entry);method_site=g.at;method_cell=g.relative('4c8b0d')
    g.take('4c8bc0');key_site=g.at;key_cell=g.relative('488b15');g.take('498bce');g.call(set_value)
    return dict(selectedBytes=g.seen,methodInfoSiteVa=method_site,methodInfoCellVa=method_cell,
        keySiteVa=key_site,keyCellVa=key_cell,value='same header string result in RAX',
        receiver='same executor EventParams retained in R14',completeCallerFrameProved=False)


def set_key(regions,entry,*,create,dispatch):
    g=BytesPath(regions,entry)
    g.take('48895c2408','48896c2410','4889742418','57','4883ec20','4983793800',
        '498bd9','498bf8','488bf2','488be9');g.branch('74',False,1)
    g.take('488b4338','4c8b08','4983792000');g.branch('74',False,1)
    g.take('4c8b4338','488bd6','488bcd','4d8b00');g.call(create)
    g.take('4885c0');g.branch('74',False,1)
    g.take('b911000000','4c8bc7','488bd0','488b5c2430','488b6c2438','488b742440','4883c420','5f')
    if g.relative('e9')!=dispatch:raise ValueError('executorKey.set-tail')
    return dict(selectedBytes=g.seen,contextSlot=0,selector=17,valueBytes=8,value='same incoming string reference',
        sameReceiverAndKey=True,entryRspRestored=True,frameBytes=40,tailDispatch=True)


def missing_variable(regions,entry,*,lookup,new):
    g=BytesPath(regions,entry)
    g.take('48895c2418','4889742420','57','4883ec20','4983783800','498bd8','488bf2','488bf9')
    g.branch('0f84',False);g.take('488b4f28','48c744243000000000','4885c9');g.branch('0f84',False)
    site=g.at;cell=g.relative('4c8b0d')
    g.take('4c8d442430','488bd6','4c89742438');g.call(lookup);g.take('84c0');g.branch('75',False,1)
    g.take('488b4338','488b4808','4883792000');g.branch('74',False,1)
    g.take('4c8b4b38','4533c0','488bd6','488bcf','4d8b4908');g.call(new)
    g.take('4c8b742438','488b5c2440','488b742448','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,tableFieldOffset=40,lookupMethodInfoSiteVa=site,lookupMethodInfoCellVa=cell,
        contextNewSlot=1,initializerReferenceNull=True,returnedReference='same new variable reference',
        entryRspRestored=True,frameBytes=40,condition='Own literal key absent from valid stable dictionary')


def new_variable(regions,entry,*,allocate,barrier,dispatch,set_item):
    g=BytesPath(regions,entry)
    g.take('48895c2408','48896c2410','4889742418','57','4883ec20','4983793800','498bd9',
        '498bf0','488bfa','488be9');g.branch('74',False,1)
    g.take('488b5338','b101','488b12');g.call(allocate)
    g.take('488bd8','4885c0');g.branch('74',False,1)
    g.take('488d4818','48897818');g.call(barrier)
    g.take('b90f000000','4c8bc6','488bd3');g.call(dispatch)
    g.take('488b4d28','4885c9');g.branch('74',False,1)
    site=g.at;cell=g.relative('4c8b0d');g.take('4c8bc3','488bd7');g.call(set_item)
    g.take('488b6c2438','488bc3','488b5c2430','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,poolReuseAllowed=True,poolMethodContextSlot=0,createdKeyFieldOffset=24,
        initializerSelector=15,initializerValueBytes=8,tableSetterMethodInfoSiteVa=site,tableSetterMethodInfoCellVa=cell,
        tableFieldOffset=40,returnsSameCreatedVariable=True,entryRspRestored=True,frameBytes=40)


def invoke_reference(regions,entry,*,prepare,callback,slot):
    if slot not in(15,17):raise ValueError('executorKey.reference-slot')
    g=BytesPath(regions,entry)
    g.take('48895c2410','4889742418','57','4883ec20','0fb7f9','498bf0','488b0a','488bda');g.call(prepare)
    g.take('488b03','488d4f14','4803c9','4c8b0cc8','488b7cc808');excluded=[]
    for opcode,width in(('74',1),('0f84',4),('0f84',4)):
        excluded.append(g.relative('488d05'));g.take('4c3bc8');g.branch(opcode,False,width)
    if callback in excluded:raise ValueError('executorKey.inline-callback-not-covered')
    g.take('4c8bc7','488bd6','488bcb','41ffd1','488b5c2438','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,selector=slot,callbackByteOffset=320+slot*16,methodInfoByteOffset=328+slot*16,
        requiredCallbackVa=callback,excludedInlineCallbacks=excluded,sameReceiverAndFullReference=True,
        selectedMethodInfoPassed=True,entryRspRestored=True,frameBytes=40)


def property_set(regions,entry,*,dispatch):
    g=BytesPath(regions,entry);g.take('488bc1','4c8bc2','488bd0','b911000000')
    if g.relative('e9')!=dispatch:raise ValueError('executorKey.property-tail')
    return dict(selectedBytes=g.seen,selector=17,valueBytes=8,sameReceiverAndReference=True,
        incomingMethodInfoUnread=True,tailCall=True,entryRspAndNonvolatilesUntouched=True)


def value_set(regions,entry):
    g=BytesPath(regions,entry)
    g.take('48895c2410','55','56','57','4154','4155','4156','4157','488bec','4883ec70',
        '0f57c0','0f57c9','4d8be8','488bfa','488bd9','0f1145b8','0f114dc8','0f1145d8','0f114de8','4885c9')
    g.branch('0f84',False);root=g.relative('488b05');g.take('488b4810','4885c9');g.branch('74',True,1)
    g.take('837b3000','410f9fc6','488b4810','4885c9');g.branch('74',True,1)
    g.take('4883bb8800000000','0f97c0','884540','410ac6');g.branch('75',False,1)
    collector=flag(g,'833d');g.take('4889bb90000000');g.branch('74',True,1)
    g.take('488b9c24b8000000','4883c470','415f','415e','415d','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,replacementReceiverOffset=16,
        valueFieldOffset=144,valueBytes=8,sameNullableReferenceStored=True,collectorDisabledFlagVa=collector,
        observerCounterOffset=48,observerCounterRequiredNonpositive=True,secondObserverOffset=136,secondObserverRequiredNull=True,
        entryRspRestored=True,frameBytes=168,callCount=0,actualObserverStateObserved=False)


def reset_reference(regions,entry,*,base_reset):
    g=BytesPath(regions,entry);g.take('4053','4883ec20','488bd9','4885c9');g.branch('74',False,1)
    g.take('33d2');g.call(base_reset);g.take('33c0','48898390000000','4883c420','5b','c3')
    return dict(selectedBytes=g.seen,valueFieldOffset=144,valueBytes=8,valueSetNull=True,
        baseResetRequired=True,entryRspRestored=True,frameBytes=40)

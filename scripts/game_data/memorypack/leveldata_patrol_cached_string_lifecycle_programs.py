"""Selected generic interface recycler arm for a cached String variable."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check,condition):
    if not condition:raise ValueError('cachedStringLifecycle.'+check)


def recycle_interface(regions,entry,*,get_type,context_type,type_from_context,lookup,prepare,callback,misses=0):
    need('bounded-interface-prefix',type(misses)is int and 0<=misses<=3)
    g=BytesPath(regions,entry)
    g.take('4057','4883ec40');root=g.relative('488b05')
    g.take('488bf9','488b4810','4885c9');g.branch('74',True,1)
    g.take('48895c2450','33db','48895c2420','48895c2468','4885ff');g.branch('0f84',False)
    g.take('4889742438','395f10');g.branch('0f84',False)
    g.take('48896c2458','b909000000','488bd7');g.call(get_type)
    registry_site=g.at;registry=g.relative('488b2d');g.take('488bf0','488b4d20');g.call(context_type)
    g.take('33d2','488b88c0000000');g.call(type_from_context)
    g.take('488b90b8000000','48391a');g.branch('75',True,1)
    g.take('488b4d20');g.call(context_type)
    g.take('33d2','488b88c0000000');g.call(type_from_context)
    g.take('488b88b8000000','488b29','4885ed');g.branch('0f84',False)
    g.take('488b6d10','4885ed');g.branch('0f84',False)
    lookup_site=g.at;lookup_cell=g.relative('4c8b0d')
    g.take('4c8d442420','488bd6','4c89742430','488bcd');g.call(lookup)
    g.take('84c0');g.branch('0f85',True)
    g.take('488b742420','4885f6');g.branch('0f84',False)
    g.take('488b0e','8b911c010000','81ea');direct=int.from_bytes(g.read(4),'little',signed=True)
    g.branch('0f84',False);g.take('83fa01');g.branch('0f84',False)
    interface_site=g.at;interface=g.relative('488b2d');g.take('4c8bf1');g.call(prepare)
    g.take('410fb78e30010000','663bd9');g.branch('73',False,1)
    g.take('498b96b0000000');loop=g.at;steps=[]
    for i in range(misses+1):
        need('exact-interface-backedge',g.at==loop);start=len(g.seen)
        g.take('0fb7c3','4803c0','48392cc2');g.branch('0f84',i==misses)
        if i<misses:g.take('66ffc3','663bd9');g.branch('72',True,1)
        steps.append(g.seen[start:])
    g.take('0fb7cb','4803c9','8b44ca08','ffc0','4898','4883c014','48c1e004','4903c6');g.jump('e9')
    g.take('4c8b08','488b5808');excluded=[]
    for _ in range(2):
        excluded.append(g.relative('488d05'));g.take('4c3bc8');g.branch('0f85',True)
    excluded.append(g.relative('488d05'));g.take('4c3bc8');g.branch('75',True,1)
    need('selected-callback-outside-three-inline-arms',callback not in excluded and callback>0)
    call=g.at;g.take('4c8bc3','488bd7','488bce','41ffd1');g.jump('e9')
    g.take('4c8b742430','488b6c2458','488b742438','488b5c2450','4883c440','5f','c3')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,replacementReceiverOffset=16,
        incomingVariableSerialRequiredNonzeroOffset=16,getTypeSelector=9,
        registryMethodInfoSiteVa=registry_site,registryMethodInfoCellVa=registry,
        lookupMethodInfoSiteVa=lookup_site,lookupMethodInfoCellVa=lookup_cell,
        interfaceClassSiteVa=interface_site,interfaceClassCellVa=interface,
        excludedDirectClassDiscriminators=[direct,direct+1],metadataTypeIndexAliasProved=False,
        selectedInterfaceIndex=misses,failedSearchPrograms=steps[:-1],interfaceMethodOrdinal=1,
        excludedInlineCallbacks=excluded,selectedCallbackRequired=callback,callbackInstructionVa=call+9,
        callbackArguments=dict(rcx='same selected String variable pool',rdx='same incoming String variable',r8='same actual interface MethodInfo'),
        dictionaryLookupRequiredHit=True,canonicalCorrespondingStringTypeKeyRequired=True,
        selectedTypedRecycleBodyRequired=True,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r14'],runtimeSelectionObserved=False)

"""Exact Radio dispatcher and listener-call source programs.

These programs transport the own key and EventData argument. They do not infer a
live dictionary, listener registration, callback selection or playback effect.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag


def need(check,condition):
 if not condition:raise ValueError('patrolRadioDispatch.'+check)


def play_dispatch(regions,entry,*,found):
 need('literal-lookup-result',type(found)is bool)
 g=BytesPath(regions,entry);calls=[]
 def call(role):
  site=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=site,targetVa=target))
 g.take('48895c2410','48896c2418','4889742420','57','4883ec20','4983793800','498bf9','498be8','8bda','488bf1')
 g.branch('75',True,1)
 g.take('488b7610','48c744243000000000','4885f6');g.branch('0f84',False)
 g.take('488b4720','488b88c0000000','488b4120','4883782000');g.branch('75',True,1)
 g.take('488b4720','4c8d442430','8bd3','488bce','4c8b88c0000000','4d8b4920');call('tryGetHandler')
 g.take('84c0');g.branch('74',not found,1)
 if found:
  g.take('488b5c2430','4885db');g.branch('74',False,1)
  g.take('488b4738','488b10','48837a2000');g.branch('75',True,1)
  g.take('4c8b4738','488bd5','488bcb','4d8b00');call('invokeHandler')
 g.take('488b5c2438','488b6c2440','488b742448','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,calls=calls,found=found,keyBytes=4,keyArgument='unchanged incoming EDX',
  dispatcherDictionaryFieldOffset=16,dictionaryTryGetClassContextSlot=4,handlerInvokeMethodContextSlot=0,
  handlerOutputLocalRsp=[48,56],handlerOutputInitiallyNull=True,payloadArgument='unchanged incoming R8 pointer',
  dictionaryAndHandlerRequiredNonnull=True,selectedMethodContextsAlreadyReadyRequired=True,
  callbackEffectsProved=False,entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi'])


def play_dispatch_call(regions,entry):
 g=BytesPath(regions,entry)
 g.take('488b4738','488b10','48837a2000');g.branch('75',True,1)
 g.take('4c8b4f38','4d8b09','4c8d442428','8bd3','498bce')
 site=g.at;target=g.relative('e8')
 return dict(selectedBytes=g.seen,actualDispatchCall=dict(instructionVa=site,targetVa=target),nextInstructionVa=g.at,
  requiredIncomingRegisters=dict(rdi='actual SendGlobal<RadioRuntimeData> MethodInfo',r14='actual Dispatcher<CombineKey> reference',ebx='unchanged CombineKey raw4'),
  sourceContextSlot=0,payloadLocalRsp=[40,96],surroundingFrameAndWholePayloadProofRequired=True)


def stop_inline_dispatch(regions,entry,*,found):
 """Own inline macro; caller supplies its exact cursor and surrounding frame."""
 need('literal-inline-lookup-result',type(found)is bool)
 g=BytesPath(regions,entry);calls=[]
 def call(role):
  site=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=site,targetVa=target))
 g.take('498b4638','488b30','48397e38');g.branch('75',True,1)
 g.take('4889bc24a0000000','4d8b7f10','4d85ff');g.branch('0f84',False)
 g.take('488b4620','488b88c0000000','488b4120','48397820');g.branch('75',True,1)
 g.take('488b4620','4c8b88c0000000','4d8b4920','4c8d8424a0000000','8bd3','498bcf');call('tryGetHandler')
 g.take('84c0');g.branch('74',not found,1)
 if found:
  g.take('4c8bbc24a0000000','4d85ff');g.branch('0f84',False)
  g.take('488b4638','488b10','48397a20');g.branch('75',True,1)
  g.take('4c8b4638','4d8b00','488d942498000000','498bcf');call('invokeHandler')
 return dict(selectedBytes=g.seen,calls=calls,found=found,nextInstructionVa=g.at,
  requiredIncomingRegisters=dict(r14='actual SendGlobal<string> MethodInfo',r15='selected Dispatcher<CombineKey> reference',
   ebx='unchanged incoming CombineKey raw4',rdi='zero'),
  selectedDispatchMethodFromSendContextSlot=0,dispatcherDictionaryFieldOffset=16,
  dictionaryTryGetClassContextSlot=4,handlerInvokeMethodContextSlot=0,
  handlerOutputLocalRsp=[160,168],handlerOutputInitiallyNull=True,payloadArgumentLocalRsp=[152,160],
  payloadArgument='address of unchanged EventData<string> local',keyBytes=4,
  selectedMethodContextsAlreadyReadyRequired=True,dictionaryAndHandlerRequiredNonnull=True,
  surroundingFrameAndPayloadLocalProofRequired=True,callbackEffectsProved=False)


def stop_handler(regions,entry,*,enabled=(),nested=False):
 need('finite-list-witness',isinstance(enabled,(tuple,list))and len(enabled)<=3 and all(type(v)is bool for v in enabled)and type(nested)is bool)
 g=BytesPath(regions,entry);calls=[];steps=[]
 def call(role):
  site=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=site,targetVa=target))
 g.take('4c89442418','4889542410','48894c2408','53','56','57','4154','4155','4156','4157','4883ec60',
  '4d8bf0','4c8be2','488bf1','4983783800');g.branch('0f84',False)
 g.take('33db','895c2450','488b4628','4885c0');g.branch('0f84',False)
 g.take('395818');g.branch('0f84',not enabled)
 if enabled:
  g.take('ff4610','899c24b8000000','4885c0');g.branch('0f84',False)
  g.take('448b7818','44897c2430');loop=g.at
  for flag in enabled:
   begin=len(g.seen);need('same-counted-list-loop',g.at==loop)
   g.take('413bdf');g.branch('0f8d',False)
   g.take('488b4628','4885c0');g.branch('0f84',False)
   g.take('3b5818');g.branch('0f83',False)
   g.take('488b4810','4885c9');g.branch('0f84',False)
   g.take('3b5918');g.branch('0f83',False)
   g.take('4863c3','4c8b6cc120','4d85ed');g.branch('0f84',False)
   g.take('41807d1800');g.branch('75',not flag,1)
   if flag:
    g.take('498b7d10','33d2','498b4e38');call('callbackType')
    g.take('488bd0','488bcf');call('compatibleCallback')
    g.take('488bf8','4885c0');g.branch('0f84',False)
    g.take('498b4e38','488b5110','48837a2000');g.branch('0f84',False)
    g.take('4d8b4638','4d8b4010','498bd4','488bcf');call('invokeListener')
    g.take('90')
   g.take('ffc3','899c24b8000000');g.jump('e9')
   steps.append(dict(enabled=flag,selectedBytes=g.seen[begin:]))
  g.take('413bdf');g.branch('0f8d',True)
  g.take('836e1001');g.branch('75',nested,1)
  if not nested:
   g.take('498b4620','488b88c0000000','488b4118','4883782000');g.branch('0f84',False)
   g.take('498b4620','488b90c0000000','488b5218','488bce');call('compactListeners')
 g.take('4883c460','415f','415e','415d','415c','5f','5e','5b','c3')
 return dict(selectedBytes=g.seen,calls=calls,listenerSteps=steps,count=len(enabled),enabled=list(enabled),nested=nested,
  listenerListFieldOffset=40,listItemsFieldOffset=16,listCountFieldOffset=24,arrayDataOffset=32,elementStride=8,
  listenerCallbackFieldOffset=16,listenerDisabledByteOffset=24,dispatchDepthFieldOffset=16,
  capturedCountRegister='r15d',counterRegister='ebx',counterInitial=0,counterIncrement=1,
  capturedCountImmutableRequired=True,stableListenerListAndBackingStorageRequired=True,
  callbackMutationMustPreserveCapturedBoundAndRemainingItems=True,
  unchangedEventDataPointerToEveryEnabledCallback=True,listenerCallbackMethodContextSlot=2,
  callbackTypeMethodContextSlot=0,compactMethodClassContextSlot=3,
  callbackSelectionAndEffectsProved=False,entryRspRestored=True,
  restoredNonvolatiles=['rbx','rsi','rdi','r12','r13','r14','r15'])


def stop_handler_paths(regions,entry,*,count_limit=4096):
 import itertools
 need('finite-list-induction-bound',type(count_limit)is int and 3<=count_limit<=4096)
 witnesses=[stop_handler(regions,entry,enabled=flags,nested=nested)
  for n in range(4)for flags in itertools.product((False,True),repeat=n)for nested in(False,True)]
 arms={}
 for flag in(False,True):
  values=[s['selectedBytes']for p in witnesses for s in p['listenerSteps']if s['enabled']==flag]
  need('same-exact-listener-arm-'+str(flag),values and all(v==values[0]for v in values));arms[str(flag)]=values[0]
 return dict(witnesses=witnesses,countLimit=count_limit,listenerArms=arms,
  induction=dict(counterInitial=0,counterIncrement=1,counterRegister='ebx',boundRegister='r15d',
   boundCapturedBeforeLoop=True,exactSignedComparison=True,noCounterOverflow=count_limit<2**31-1,
   invariant='At the same loop entry EBX counts prior visited entries and R15D retains the captured initial list count. Both enabled and disabled arms load exactly the indexed reference, advance EBX once, save it and return to that entry. Enabled callbacks receive the unchanged EventData pointer. Stable valid storage and callback preservation of the captured bound and remaining entries are required.'),
  runtimeListenerSelectionObserved=False)


def try_get_handler(regions,entry,*,found):
 need('literal-handler-find-result',type(found)is bool)
 g=BytesPath(regions,entry)
 g.take('48895c2408','48896c2410','4889742418','57','4883ec20','498b4120','8bda','498bf1','498bf8','488be9',
  '488b90c0000000','488b82b0000000','4883782000');g.branch('75',True,1)
 g.take('488b4620','8bd3','488bcd','4c8b80c0000000','4d8b80b0000000')
 site=g.at;target=g.relative('e8');g.take('4863f0','85c0');g.branch('79',found,1)
 collector=None
 if found:
  g.take('488b5d18','4885db');g.branch('74',False,1)
  g.take('3b7318');g.branch('73',False,1)
  collector=flag(g,'833d');g.take('488d0c76','488d04cb','488b44cb30','488907');g.branch('74',True,1)
  g.take('b001')
 else:g.take('33c0','488907');g.jump('eb',1)
 g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,findCall=dict(instructionVa=site,targetVa=target),found=found,
  keyBytes=4,sameIncomingRawKeyPassed=True,findMethodClassContextSlot=22,
  entryStride=24,entryValueOffset=16,outputBytes=8,
  output='unchanged selected handler reference'if found else'zero reference',returnedBool=found,
  collectorDisabledFlagVa=collector,findEntryAndNominalKeyEffectsRequired=True,
  entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi'])


def play_binding(regions,entry,*,enabled=(),nested=False):
 need('finite-value-list-witness',isinstance(enabled,(tuple,list))and len(enabled)<=3 and all(type(v)is bool for v in enabled)and type(nested)is bool)
 g=BytesPath(regions,entry);calls=[];steps=[];uses=[]
 def call(role):
  site=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=site,targetVa=target))
 g.take('4c89442418','4889542410','48894c2408','53','56','57','4154','4155','4156','4157','4883ec60',
  '498bf0','4c8bf1','33ff','49397838');g.branch('75',True,1)
 g.take('897c2450','498b4628','4885c0');g.branch('0f84',False)
 g.take('397818');g.branch('0f84',not enabled)
 if enabled:
  g.take('41ff4610','448bff','89bc24b8000000','4885c0');g.branch('0f84',False)
  g.take('448b6018','4489642430');loop=g.at
  for flag in enabled:
   begin=len(g.seen);need('same-value-counted-list-loop',g.at==loop)
   g.take('453bfc');g.branch('0f8d',False)
   g.take('498b4e28','4885c9');g.branch('0f84',False)
   site=g.at;cell=g.relative('4c8b05');uses.append(dict(role='listenerGetItem',instructionVa=site,cellVa=cell))
   g.take('418bd7');call('listenerGetItem')
   g.take('4c8be8','4885c0');g.branch('0f84',False)
   g.take('40387818');g.branch('0f85',not flag)
   if flag:
    g.take('488b5810','33d2','488b4e38');call('callbackType')
    g.take('488bd0','488bcb');call('compatibleCallback')
    g.take('488bd8','4885c0');g.branch('0f84',False)
    g.take('488b4e38','488b5110','48397a20');g.branch('75',True,1)
    g.take('488b4318','4c8b4328','488b9424a8000000','488b4b40')
    calls.append(dict(role='dynamicListener',instructionVa=g.at,targetRegister='rax',targetFieldOffset=24,
      methodInfoFieldOffset=40,receiverFieldOffset=64))
    g.take('ffd0','90');g.jump('eb',1)
   g.take('41ffc7','4489bc24b8000000');g.jump('e9')
   steps.append(dict(enabled=flag,selectedBytes=g.seen[begin:]))
  g.take('453bfc');g.branch('0f8d',True)
  g.take('41836e1001');g.branch('75',nested,1)
  if not nested:
   g.take('488b4620','488b88c0000000','488b4118','48397820');g.branch('75',True,1)
   g.take('488b4620','488b90c0000000','488b5218','498bce');call('compactListeners')
   g.jump('eb',1)
 g.take('4883c460','415f','415e','415d','415c','5f','5e','5b','c3')
 return dict(selectedBytes=g.seen,calls=calls,usageSites=uses,listenerSteps=steps,count=len(enabled),enabled=list(enabled),nested=nested,
  listenerListFieldOffset=40,listenerCallbackFieldOffset=16,listenerDisabledByteOffset=24,dispatchDepthFieldOffset=16,
  capturedCountRegister='r12d',counterRegister='r15d',counterInitial=0,counterIncrement=1,
  capturedCountImmutableRequired=True,stableListenerListAndBackingStorageRequired=True,
  callbackMutationMustPreserveCapturedBoundAndRemainingItems=True,
  unchangedEventDataPointerToEveryEnabledCallback=True,incomingArgumentHomeFromCurrentRsp=[168,176],
  callbackTypeMethodContextSlot=0,listenerCallbackMethodContextSlot=2,compactMethodClassContextSlot=3,
  callbackSelectionAndEffectsProved=False,entryRspRestored=True,
  restoredNonvolatiles=['rbx','rsi','rdi','r12','r13','r14','r15'])


def play_binding_paths(regions,entry,*,count_limit=4096):
 import itertools
 need('finite-value-list-induction-bound',type(count_limit)is int and 3<=count_limit<=4096)
 witnesses=[play_binding(regions,entry,enabled=flags,nested=nested)
  for n in range(4)for flags in itertools.product((False,True),repeat=n)for nested in(False,True)]
 arms={}
 for flag in(False,True):
  values=[s['selectedBytes']for p in witnesses for s in p['listenerSteps']if s['enabled']==flag]
  need('same-exact-value-listener-arm-'+str(flag),values and all(v==values[0]for v in values));arms[str(flag)]=values[0]
 return dict(witnesses=witnesses,countLimit=count_limit,listenerArms=arms,
  induction=dict(counterInitial=0,counterIncrement=1,counterRegister='r15d',boundRegister='r12d',
   boundCapturedBeforeLoop=True,exactSignedComparison=True,noCounterOverflow=count_limit<2**31-1,
   invariant='At the same loop entry R15D counts prior visited entries and R12D retains the captured initial listener count. Both arms use the independently proved actual reference GetItem, advance R15D once and return to that entry. Enabled callbacks receive the original EventData pointer saved at entry. Stable storage and callback preservation of the count and remaining entries are required.'),
  runtimeListenerSelectionObserved=False)


def pending_empty(regions,entry):
 g=BytesPath(regions,entry)
 g.take('48895c2408','48896c2410','4889742418','48897c2420','4154','4156','4157','4883ec30',
  '488b4118','488bfa','488be9','4885c0');g.branch('0f84',False)
 g.take('83781800');g.branch('0f8e',True)
 g.take('488b5c2450','488b6c2458','488b742460','488b7c2468','4883c430','415f','415e','415c','c3')
 return dict(selectedBytes=g.seen,pendingOperationsListFieldOffset=24,
  validPendingListRequiredNonnullAndCountZero=True,nonframeMemoryWrites=0,calls=0,
  entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r14','r15'])


def listener_get_item(regions,entry):
 g=BytesPath(regions,entry);g.take('4883ec28','3b5118');g.branch('73',False,1)
 g.take('488b4110','4885c0');g.branch('74',False,1)
 g.take('3b5018');g.branch('73',False,1)
 g.take('4863ca','488b44c820','4883c428','c3')
 return dict(selectedBytes=g.seen,listCountFieldOffset=24,listItemsFieldOffset=16,
  arrayLengthOffset=24,arrayDataOffset=32,elementStride=8,returnsSameIndexedReference=True,
  validListArrayAndIndexRequired=True,nonframeMemoryWrites=0,calls=0,entryRspRestored=True)


def compatible_callback(regions,entry):
 g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','57','4883ec20','488bfa','488bd9','4885c9');g.branch('74',False,1)
 g.take('488b31','488bcf','488bd6');site=g.at;target=g.relative('e8')
 g.take('84c0');g.branch('74',False,1)
 g.take('488bc3','488b5c2430','488b742438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,compatibilityCall=dict(instructionVa=site,targetVa=target),
  sameNonnullCallbackReturned=True,actualCallbackClassMustBeCompatibleWithContextType=True,
  compatibilityHelperEffectsRequired=True,nonframeMemoryWrites=0,entryRspRestored=True,
  restoredNonvolatiles=['rbx','rsi','rdi'])


def string_delegate_tail(regions,entry):
 g=BytesPath(regions,entry);excluded=[]
 g.take('4053','4883ec20','488b4118','4c8b4128','488b5940')
 for branch in('74','0f84','0f84'):
  excluded.append(g.relative('488d0d'));g.take('483bc1');g.branch(branch,False,1 if branch=='74'else 4)
 g.take('488bcb','4883c420','5b','48ffe0')
 return dict(selectedBytes=g.seen,excludedInlineCallbackTargets=excluded,
  selectedDynamicCallbackRequiredOutsideInlineTargets=True,targetFieldOffset=24,methodInfoFieldOffset=40,
  receiverFieldOffset=64,unchangedIncomingEventDataPointerInRdx=True,
  sameSelectedMethodInfoInR8=True,tailTargetRegister='rax',tailTargetEffectsProved=False,
  entryRspRestored=True,restoredNonvolatiles=['rbx'])


def same_callback_class(regions,entry):
 g=BytesPath(regions,entry)
 g.take('48895c2420','4889542410','48894c2408','55','56','57','4154','4155','4156','4157','4883ec20',
  '4c8be2','4c8bf9','483bca');g.branch('0f84',True)
 g.take('b001','488b5c2478','4883c420','415f','415e','415d','415c','5f','5e','5d','c3')
 return dict(selectedBytes=g.seen,actualCallbackClassRequiredIdenticalToContextDelegateType=True,returnedBool=True,
  nonframeMemoryWrites=0,calls=0,entryRspRestored=True,
  restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'])

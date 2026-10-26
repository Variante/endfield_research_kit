"""Exact full-handle retention caller and spare HashSet insertion transfer.

The same20 input bytes, including padding, reach the actual generic Add helper.
Hash/comparer selection and storage ownership are independent source joins.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check,condition):
 if not condition:raise ValueError('patrolRetain.'+check)


def retain(regions,entry,*,valid=True):
 need('literal-validity-result',type(valid)is bool);g=BytesPath(regions,entry)
 g.take('48895c2410','57','4883ec40');root=g.relative('488b05');g.take('488bd9','488bfa','488b4878','4885c9');g.branch('0f85',False)
 g.take('33d2','488bcf');site=g.at;validity=g.relative('e8');g.take('84c0');g.branch('74',not valid,1)
 if valid:
  g.take('488b5b18','4885db');g.branch('74',False,1);g.take('0f1007','8b7f10','4889742450')
  usage=g.at;context=g.relative('488b35')
  g.take('0f11442420','488b4620','488b88c0000000','488b8180000000','4883782000');g.branch('0f84',False)
  g.take('488b4620','488d542420','488bcb','0f29442420','897c2430','4c8b80c0000000','4d8b8080000000')
  add_site=g.at;add=g.relative('e8');g.take('488b742450')
 else:usage=context=add_site=add=None
 g.take('488b5c2458','4883c440','5f','c3')
 return dict(selectedBytes=g.seen,replacementRootCellVa=root,selectedReplacementReceiverAt120RequiredNull=True,
  validityCall=dict(instructionVa=site,targetVa=validity),selectedValid=valid,
  methodContextUsage=None if not valid else dict(instructionVa=usage,cellVa=context),
  addCall=None if not valid else dict(instructionVa=add_site,targetVa=add),inputBytes=20,
  copiedSlices=[]if not valid else[[0,16],[16,4]],addValueLocal=None if not valid else[32,52],
  sameEntireValueIncludingPaddingForwarded=valid,setReferenceFieldOffset=24,
  actualAddMethodInfoClassSlot=16,actualAddMethodInfoRequiredReady=valid,
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,
  validityOrAddEffectsRequireIndependentSource=True)


def spare_add(regions,entry):
 g=BytesPath(regions,entry);calls=[]
 def call(role):
  at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
 g.take('4053','56','57','4156','4883ec78','4883791000','498bf0','4c8bf2','488bd9');g.branch('0f84',False)
 g.take('488b4620','488b88c0000000','488b8188000000','4883782000');g.branch('0f84',False)
 g.take('488b4620','4889ac24a8000000','4c89a424b0000000','4c89ac24b8000000','488b88c0000000','4c897c2470',
  '488b8988000000','488b7b30','4885ff');g.branch('0f84',False)
 g.take('488b4920','ba12000000','410f1006','418b4610','89442440','488b89c0000000','0f29442430');call('indexedContext')
 g.take('488bd0','4c8d4c2430','b901000000','4c8bc7');call('hashInvoke')
 g.take('488b4b10','448bf8','410fbaf71f','4885c9');g.branch('0f84',False)
 g.take('488b7b18','418bc7','99','f77918','4863ea','3b6918');g.branch('0f83',False)
 g.take('448b64a920','4183ec01');g.branch('0f89',False)
 g.take('837b2800');g.branch('0f8d',False)
 g.take('8b4324','4885ff');g.branch('0f84',False);g.take('3b4718');g.branch('0f84',False)
 g.take('8b7324','ff4324','4885ff');g.branch('0f84',False);g.take('3b7718');g.branch('0f83',False)
 g.take('4863c6','486bc81c','44897c3920','3b7718');g.branch('0f83',False)
 g.take('410f1006','4863c6','486bc81c','418b4610','0f11443928','89443938','488b5310','4885d2');g.branch('0f84',False)
 g.take('3b6a18');g.branch('0f83',False)
 g.take('4863c5','8b548220','ffca','3b7718');g.branch('0f83',False)
 g.take('4863c6','486bc81c','89543924','488b5310','4885d2');g.branch('0f84',False)
 g.take('3b6a18');g.branch('0f83',False)
 g.take('4863c5','8d4e01','894c8220','b001','ff4320','ff4338','4c8b7c2470','4c8bac24b8000000',
  '4c8ba424b0000000','488bac24a8000000','4883c478','415e','5f','5e','5b','c3')
 return dict(selectedBytes=g.seen,calls=calls,valueBytes=20,inputPointerPreservedUntilFullStore=True,
  hashArguments=dict(selectorEcx=1,expectedInterface='actual own indexed class context18',receiver='same comparer field48',value='complete20-byte local'),
  returnedHashBits31Cleared=True,bucketPointerFieldOffset=16,slotArrayFieldOffset=24,comparerFieldOffset=48,
  slotStride=28,slotHashOffset=0,slotNextOffset=4,slotValueOffset=8,slotValueSlices=[[0,16],[16,4]],
  nextSlotIndexFieldOffset=36,elementCountFieldOffset=32,freeListFieldOffset=40,versionFieldOffset=56,
  selectedBucketRequiredZero=True,selectedFreeListRequiredNegative=True,selectedSpareSlotCapacityRequired=True,
  effect='slot.hash:=hash&0x7fffffff; slot.value:=same20bytes; slot.next:=old bucket-1; bucket:=old next-slot index+1; next-slot index/count/version +=1',
  returnBool=True,entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,
  hashCallbackEffectsRequireIndependentSource=True,actualSetStateOrCallbackIdentityObserved=False)


def hash_invoker(regions,entry,*,interface_steps=0):
 need('bounded-interface-witness',type(interface_steps)is int and 0<=interface_steps<=64)
 g=BytesPath(regions,entry);calls=[]
 def call(role):
  at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
 g.take('48895c2408','48896c2410','4889742418','48897c2420','4156','4883ec70',
  '498b38','498bf1','0fb7e9','4d8bf0','488bcf','488bda');call('prepareComparerClass')
 g.take('440fb78f30010000','33c0','66413bc1');g.branch('73',False,1)
 g.take('488b97b0000000');loop=g.at
 for i in range(interface_steps+1):
  g.take('0fb7c8','4803c9','48391cca');g.branch('74',i==interface_steps,1)
  if i<interface_steps:
   g.take('66ffc0','66413bc1');back=g.relative('72',1);need('same-interface-loop',back==loop);g.at=back
 g.take('0fb7d0','488b87b0000000','4803d2','8b44d008','03c5','4898','4883c014','48c1e004','4803c7','4c8b08',
  '0f1006','8b4e10','894c2430','0f29442420','4c8b4008');marker=g.relative('488d05')
 g.take('4c3bc8');g.branch('0f85',False)
 g.take('498b4820','33d2','488b89c0000000');call('indexedContext')
 g.take('0f28442420','488d4c2440','4889442440','33d2','8b442430','0f11442450','89442460','48c7442448ffffffff');call('valueHash')
 g.take('4c8d5c2470','498b5b10','498b6b18','498b7320','498b7b28','498be3','415e','c3')
 return dict(selectedBytes=g.seen,calls=calls,selectedInterfaceSteps=interface_steps,interfaceCountOffset=304,
  interfaceArrayOffset=176,interfaceRecordStride=16,selector='unchanged incoming CX; actual caller supplies1',
  inlineCallbackTargetVa=marker,selectedCallbackRequiredEqualMarker=True,contextClassSlot=0,
  actualVtableBaseOffset=320,actualSlotRecordBytes=16,
  constructedStackBox=dict(typeHeaderOffset=64,monitorHeaderOffset=72,monitorHeaderValue=-1,valueOffset=80,valueBytes=20,copiedSlices=[[0,16],[16,4]]),
  valueHashArguments=dict(rcx='same stack value box header RSP64',rdx=0),
  returnedActualValueHashInt32Unchanged=True,entryRspRestored=True,allNonvolatilesRestored=True,
  actualComparerCallbackOrContextObserved=False,valueHashEffectsRequireIndependentSource=True)


def value_hash_no_objects(regions,entry):
 g=BytesPath(regions,entry)
 g.take('48895c2408','48896c2410','4889742420','57','4883ec20','33db','488d542440','48895c2440')
 at=g.at;target=g.relative('e8')
 g.take('488b4c2440','8be8','4885c9');g.branch('74',True,1)
 g.take('488b5c2430','8bc5','488b6c2438','488b742448','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,internalHashCall=dict(instructionVa=at,targetVa=target),
  internalHashArguments=dict(rcx='unchanged incoming stack value box',rdx='address of initially null Object[] local RSP64'),
  selectedReturnedObjectArrayRequiredNull=True,returnsInternalHashInt32Unchanged=True,
  entryRspRestored=True,allNonvolatilesRestored=True,internalHashEffectsRequireIndependentSource=True)


def value_hash_objects(regions,entry,*,count=1,null_elements=()):
 need('bounded-object-hash-witness',type(count)is int and 0<=count<=64 and type(null_elements)is tuple
  and len(null_elements)==len(set(null_elements))and all(type(i)is int and 0<=i<count for i in null_elements))
 g=BytesPath(regions,entry);calls=[];objects=[]
 g.take('48895c2408','48896c2410','4889742420','57','4883ec20','33db','488d542440','48895c2440')
 at=g.at;target=g.relative('e8');calls.append(dict(role='internalHash',instructionVa=at,targetVa=target))
 g.take('488b4c2440','8be8','4885c9');g.branch('74',False,1)
 g.take('8bd3','be20000000');loop=g.at
 for index in range(count+1):
  g.take('3b5118');g.branch('7d',index==count,1)
  if index==count:break
  g.take('3b5918');g.branch('73',False,1)
  g.take('48833c0e00');g.branch('74',index in null_elements,1)
  if index not in null_elements:
   g.take('488b3c0e','488b0f');at=g.at;prep=g.relative('e8');calls.append(dict(role='prepareChildClass',instructionVa=at,targetVa=prep))
   g.take('488b17','488bcf','488b8260010000','488b9268010000');at=g.at;g.take('ffd0')
   objects.append(dict(index=index,callbackInstructionVa=at,receiver='same Object[] element',vtableSlot=2,callbackOffset=352,methodInfoOffset=360))
   g.take('488b4c2440','33e8')
  g.take('ffc3','4883c608','8bd3','4885c9');g.branch('74',False,1)
  back=g.relative('eb',1);need('same-object-hash-counted-loop',back==loop);g.at=back
 g.take('488b5c2430','8bc5','488b6c2438','488b742448','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,calls=calls,objectCallbacks=objects,objectCount=count,nullElements=list(null_elements),
  outputArrayRequiredNonnull=True,arrayLengthOffset=24,arrayDataOffset=32,elementStride=8,
  accumulator='actual InternalGetHashCode Int32 XOR each nonnull child GetHashCode Int32 in original array order',
  nullChildrenPreserveAccumulator=True,countedLoopEntryVa=loop,entryRspRestored=True,allNonvolatilesRestored=True,
  actualArrayContentsOrCallbackSelectionObserved=False,internalAndChildHashEffectsRequireIndependentSources=True)

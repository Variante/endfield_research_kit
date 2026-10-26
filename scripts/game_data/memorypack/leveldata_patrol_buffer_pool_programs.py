"""Actual byte ArrayPool cached TLS Rent/Return and owning guard transfers.

Only positive requested sizes through128 and an existing same-thread buffer are
selected. Bucket growth, clearing, per-core stacks and allocator paths remain
separate. Thread/TLS lookup and the actual callback identities are conditions.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check,condition):
 if not condition:raise ValueError('patrolBufferPool.'+check)


def bucket(size):
 need('bounded-positive-request',type(size)is int and 1<=size<=128)
 # Exact MOV/SHR/LEA/CMOV integer schedule authenticated below. The finite
 # domain includes every accepted request, not sampled representative lengths.
 edx=size-1;eax=edx>>4;ecx=0 if eax<=65535 else 16
 edx=eax if eax<=65535 else edx>>20
 if edx>255:edx>>=8;ecx+=8
 eax=ecx if edx<=15 else ecx+4;ecx=edx if edx<=15 else edx>>4
 r8=eax if ecx<=3 else eax+2;edx=ecx if ecx<=3 else ecx>>2
 eax=r8 if edx<=1 else r8+1;r12=edx if edx<=1 else edx>>1
 return r12+eax


def rent(regions,entry,*,size=128):
 index=bucket(size);g=BytesPath(regions,entry);calls=[]
 def call(role):
  at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
 g.take('488bc4','48894808','53','56','4155','4883ec60','4d8be8','8bda','488bf1','85d2');g.branch('0f88',False)
 g.take('85d2');g.branch('0f84',False)
 g.take('48896810','488978e0','4c8960d8','4c8970d0');cls=g.relative('488b05');g.take('83b8e000000000');g.branch('75',True,1)
 g.take('488b80b8000000','8d53ff','488b28','8bc2','c1e804','4889ac2498000000','4533f6','b910000000','3dffff0000','410f46ce',
  'c1ea14','3dffff0000','0f46d0','81faff000000');g.branch('76',True,1)
 g.take('8d4104','83fa0f','0f46c1','8bca','c1e904','83fa0f','0f46ca','83f903','448d4002','8bd1','440f46c0','c1ea02',
  '83f903','0f46d1','488b7e18','418d4001','448be2','41d1ec','83fa01','440f46e2','410f46c0','4403e0','4885ff');g.branch('0f84',False)
 g.take('498b4520','4c897c2440','488b88c0000000','443b6718');g.branch('0f8d',False)
 g.take('ba06000000');resolver=call('indexedContext');g.take('4439b0e0000000');g.branch('75',True,1)
 g.take('498b4d20','ba06000000','488b89c0000000');need('same-indexed-context',call('indexedContext')==resolver)
 thread_root=g.relative('488b0d');g.take('4863b810010000','8b09');tls=g.relative('ff15');g.take('488bd8','4885c0');g.branch('75',True,1)
 g.take('488b4310','488b4060','488b0cf8','488b19','4885db');g.branch('0f84',False)
 g.take('443b6318');g.branch('0f83',False)
 g.take('4e8b4ce320','4d85c9');g.branch('74',False,1);g.take('443b6318');g.branch('0f83',False)
 collector=g.relative('443935');g.take('4e8974e320');g.branch('74',True,1)
 g.take('4885ed');g.branch('0f84',False);g.take('498bc1');g.at=g.relative('e9')
 g.take('4c8b7c2440','4c8b642450','488b7c2458','488bac2488000000','4c8b742448','4883c460','415d','5e','5b','c3')
 return dict(selectedBytes=g.seen,calls=calls,requestSize=size,bucketIndex=index,bucketSize=16<<index,
  loggingClassCellVa=cls,loggingStaticReferenceRequiredNonnull=True,indexedContextSlot=6,threadRootCellVa=thread_root,tlsLookupIatCell=tls,
  selectedTlsClassInitializedRequired=True,tlsIndexClassOffset=272,tlsStoragePointerChain=[16,96],tlsReferenceSlotBytes=8,
  tlsArraySlotOffset=32,tlsArraySlotBytes=8,slotReferenceReadUnchanged=True,slotClearedToNull=True,
  selectedCollectorDisabledCellVa=collector,selectedBufferCapacityRequired=16<<index,
  returnsRemovedBufferUnchanged=True,entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,
  runtimeTlsOrBufferIdentityObserved=False)


def return_buffer(regions,entry,*,capacity=128):
 need('bounded-power-of-two-buffer',type(capacity)is int and capacity in(16,32,64,128));index=bucket(capacity)
 g=BytesPath(regions,entry);calls=[]
 def call(role):
  at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
 g.take('488bc4','53','56','57','4155','4883ec78','498bf9','410fb6f0','488bda','4c8be9','4885d2');g.branch('0f84',False)
 g.take('48896808','4c896018','4c897020','448b4a18','41ffc9','418bc1','c1e804','4533f6','ba10000000','3dffff0000','410f46d6',
  '41c1e914','3dffff0000','440f46c8','4181f9ff000000');g.branch('76',True,1)
 g.take('4183f90f','8d4204','418bc9','0f46c2','c1e904','4183f90f','410f46c9','83f903','448d4002','8bd1','440f46c0','c1ea02',
  '83f903','0f46d1','498b6d18','418d4001','448be2','41d1ec','83fa01','440f46e2','410f46c0','4403e0','4885ed');g.branch('0f84',False)
 g.take('4c897c2470','443b6518');g.branch('0f8d',False);g.take('4084f6');g.branch('74',True,1)
 g.take('498b7510','4885f6');g.branch('0f84',False);g.take('443b6618');g.branch('0f83',False)
 g.take('428b44a620','394318');g.branch('0f85',False)
 g.take('488b4f20','ba06000000','488b89c0000000');resolver=call('indexedContext');g.take('4439b0e0000000');g.branch('75',True,1)
 g.take('488b4f20','ba06000000','488b89c0000000');need('same-indexed-context',call('indexedContext')==resolver)
 thread_root=g.relative('488b0d');g.take('4863a810010000','8b09');tls=g.relative('ff15');g.take('488bf0','4885c0');g.branch('75',True,1)
 g.take('488b4610','488b4060','488b0ce8','488b31','4885f6');g.branch('0f84',False);g.take('443b6618');g.branch('0f83',False)
 g.take('4e8b4ce620','4c898c24a8000000');g.branch('0f83',False)
 collector=g.relative('443935');g.relative('488d2d');g.take('4a895ce620');g.branch('74',True,1)
 g.take('4d85c9');g.branch('0f84',True)
 cls=g.relative('488b05');g.take('83b8e000000000');g.branch('75',True,1)
 g.take('488b80b8000000','48833800');g.branch('0f84',False)
 g.at=g.relative('eb',1)
 g.take('4c8b7c2470','4c8ba424b0000000','488bac24a0000000','4c8bb424b8000000','4883c478','415d','5f','5e','5b','c3')
 return dict(selectedBytes=g.seen,calls=calls,arrayCapacity=capacity,bucketIndex=index,clearArrayRequiredFalse=True,
  indexedContextSlot=6,threadRootCellVa=thread_root,tlsLookupIatCell=tls,tlsIndexClassOffset=272,tlsStoragePointerChain=[16,96],
  loggingClassCellVa=cls,loggingStaticReferenceRequiredNonnull=True,selectedCollectorDisabledCellVa=collector,
  sameArrayStoredIntoTlsSlot=True,tlsArraySlotOffset=32,tlsArraySlotBytes=8,previousTlsSlotRequiredNull=True,
  bufferBytesPreserved=True,entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,runtimeTlsOrBufferIdentityObserved=False)


def guard(regions,entry):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','488b01','488b18','488b4108','488b38','4885db');g.branch('74',False,1)
 g.take('488b0b');at=g.at;prepare=g.relative('e8')
 g.take('4c8b0b','4533c0','488bd7','488bcb','498b8190010000','4d8b8998010000','488b5c2430','4883c420','5f','48ffe0')
 return dict(selectedBytes=g.seen,preparationCall=dict(instructionVa=at,targetVa=prepare),poolReference='QWORD at *guard[0]',
  bufferReference='QWORD at *guard[1]',callbackClassOffset=400,methodInfoClassOffset=408,clearArrayArgument=False,
  samePoolAndBufferForwardedUnchanged=True,entryRspRestored=True,nonvolatilesRestored=['rbx','rdi'],normalTail=True)

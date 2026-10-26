"""Own CombineKey/reference dictionary lookup programs and exact raw32 equality."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check,condition):
 if not condition:raise ValueError('patrolRadioDictionary.'+check)


def modulo_lemma():
 divisor=919;multiplier=0x8e9fe543;scale=2**41;maximum=2**31-1
 delta=multiplier*divisor-scale;max_quotient=maximum//divisor
 need('positive-hash-exact-reciprocal-division',multiplier==(scale+divisor-1)//divisor
  and 0<=delta<divisor and multiplier*(divisor-1)+delta*max_quotient<scale)
 return dict(divisor=divisor,multiplier=multiplier,scale=scale,maximumHash=maximum,
  productRemainder=delta,largestIntervalNumerator=multiplier*(divisor-1)+delta*max_quotient,
  exactAllHashValues=True,
  proof='For h=919*q+r, 0<=r<919, multiplier*h=q*2^41+delta*q+multiplier*r. The displayed upper bound is below 2^41 for all masked hash values, so the quotient is exactly q. The signed high-word multiply plus h equals floor(multiplier*h/2^32), its subsequent positive shift by nine is floor(multiplier*h/2^41). The quotient subtraction leaves h modulo919.')


def find(regions,entry,*,found=True,failures=(),buckets=True,fast=True):
 need('finite-combine-key-chain',all(type(v)is bool for v in(found,buckets,fast))and isinstance(failures,(tuple,list))
  and len(failures)<=3 and all(v in('hash','key')for v in failures)and(buckets or(not found and not failures)))
 g=BytesPath(regions,entry);calls=[];steps=[]
 def call(role):
  site=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=site,targetVa=target));return target
 g.take('48895c2408','48896c2410','4889742418','57','4154','4155','4156','4157','4883ec30',
  '4d8be8','8bfa','488b5910','beffffffff','488b6918','4885db');g.branch('0f84',not buckets)
 class_cell=None;class_site=None;callback=None
 if buckets:
  g.take('4c8b7930','4d85ff');g.branch('0f85',False)
  class_site=g.at;class_cell=g.relative('488b0d');g.take('4439b9e0000000');g.branch('0f84',False)
  g.take('448bff','410fbaf71f','817b1897030000');g.branch('0f85',not fast)
  if fast:
   g.take('b843e59f8e','41f7ef','4103d7','c1fa09','8bc2','c1e81f','03d0','69c297030000','418bd7','2bd0')
  else:g.take('418bc7','99','f77b18');g.jump('e9')
  g.take('3b5318');g.branch('0f83',False)
  g.take('66660f1f840000000000','4863f2','4533f6','8b74b320','ffce','4885ed');g.branch('0f84',False);loop=g.at
  for reason in[*failures,None]:
   begin=len(g.seen);need('same-exact-key-chain-loop',g.at==loop)
   g.take('3b7518');g.branch('0f83',reason is None and not found)
   if reason is None and not found:break
   g.take('4863c6','488d0c40','44397ccd20');g.branch('0f85',reason=='hash')
   if reason!='hash':
    g.take('498b4520','488b88c0000000','488b4910');call('defaultComparer')
    g.take('4c8be0','3b7518');g.branch('0f83',False)
    g.take('4863c6','488d1c40','8b5cdd28','4d85e4');g.branch('0f84',False)
    g.take('498b0c24');call('prepareComparerClass')
    g.take('498b0424','4c8b90c0010000','4c8b88c8010000');callback=g.relative('488d05')
    g.take('4c3bd0');g.branch('0f85',False)
    need('same-own-key-class',g.relative('488b0d')==class_cell)
    g.take('83b9e000000000');g.branch('74',False,1)
    g.take('3bdf','0f94c0','84c0');g.branch('74',reason=='key',1)
   if reason is not None:
    g.take('3b7518');g.branch('73',False,1)
    g.take('4863c6','488d3440','8b74f524','443b7518');g.branch('7d',False,1)
    g.take('41ffc6');g.jump('e9');steps.append(dict(reason=reason,selectedBytes=g.seen[begin:]))
 g.take('488b5c2460','8bc6','488b742470','488b6c2468','4883c430','415f','415e','415d','415c','5f','c3')
 return dict(selectedBytes=g.seen,calls=calls,failedProbePrograms=steps,found=found,failures=list(failures),
  bucketsPresent=buckets,fastBucket919=fast,keyClassInstructionVa=class_site,keyClassCellVa=class_cell,requiredEqualityCallbackVa=callback,
  keyBits=32,hashSignBitCleared=True,entryStride=24,entryHashOffset=0,entryNextOffset=4,
  entryKeyOffset=8,entryValueOffset=16,bucketArrayFieldOffset=16,entryArrayFieldOffset=24,comparerFieldOffset=48,
  comparerRequiredNull=True,sameCompleteKeyEqualityInlined=True,keyEquality='all32 bits equal',
  chainCounterRegister='r14d',chainCounterInitial=0,chainCounterIncrement=1,
  noDictionaryWrites=True,entryRspRestored=True,
  restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'])


def find_paths(regions,entry,*,count_limit=4096):
 import itertools
 need('finite-own-key-chain-bound',type(count_limit)is int and 3<=count_limit<=4096)
 witnesses=[find(regions,entry,found=found,failures=failures,fast=fast)
  for n in range(4)for failures in itertools.product(('hash','key'),repeat=n)for found in(False,True)for fast in(False,True)]
 witnesses.append(find(regions,entry,found=False,buckets=False))
 arms={}
 for reason in('hash','key'):
  values=[s['selectedBytes']for p in witnesses for s in p['failedProbePrograms']if s['reason']==reason]
  need('same-exact-chain-arm-'+reason,values and all(v==values[0]for v in values));arms[reason]=values[0]
 return dict(witnesses=witnesses,countLimit=count_limit,failedProbeArms=arms,fastModulo=modulo_lemma(),
  induction=dict(counterInitial=0,counterIncrement=1,counterRegister='r14d',entryStride=24,nextIndexOffset=4,
   stableValidAcyclicChainRequired=True,noCounterOverflow=True,
   invariant='Each failed hash or complete raw32 key arm follows the exact next index of the same entry, compares the preserved R14D counter with stable entry-array length, increments once and returns to the shared loop. A finite valid acyclic chain within countLimit reaches the first hash/key match or the negative end. Both generic signed division of a nonnegative masked hash and the independently proved fast919 modulo select that same bucket.'),
  actualDefaultComparerAndContextSelectionRequired=True,runtimeTableObserved=False)


def key_hash(regions,entry):
 g=BytesPath(regions,entry);g.take('8b01','c3')
 return dict(selectedBytes=g.seen,returnsEntireReceiverRaw32=True,payloadOffset=0,memoryWrites=0,calls=0,
  entryRspAndNonvolatilesUntouched=True)


def key_equals(regions,entry):
 g=BytesPath(regions,entry);g.take('3911','0f94c0','c3')
 return dict(selectedBytes=g.seen,completeReceiverRaw32EqualsIncomingEdx=True,payloadOffset=0,memoryWrites=0,calls=0,
  entryRspAndNonvolatilesUntouched=True)


def default_cached(regions,entry):
 g=BytesPath(regions,entry);calls=[]
 def call():
  site=g.at;target=g.relative('e8');calls.append(dict(instructionVa=site,targetVa=target));return target
 g.take('48895c2408','57','4883ec20','488bf9','488b4920');ready=call()
 g.take('488b88c0000000','488b09');need('same-comparer-ready-helper',call()==ready)
 g.take('488b90b8000000','488b1a','f0830c2400','4885db');g.branch('75',True,1)
 g.take('488bc3','488b5c2430','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,calls=calls,methodInfoClassOffset=32,classContextOffset=192,
  contextSlot=0,staticFieldsOffset=184,staticReferenceOffset=0,actualCachedComparerRequiredNonnull=True,
  returnsSameSelectedStaticReference=True,coldComparerCreationProved=False,
  entryRspRestored=True,restoredNonvolatiles=['rbx','rdi'])


def equality_callback(regions,entry):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');cell=g.relative('488b0d')
 g.take('418bd8','8bfa','83b9e000000000');g.branch('74',False,1)
 g.take('3bfb','488b5c2430','0f94c0','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,keyClassCellVa=cell,completeIncomingEdxEqualsR8d=True,
  selectedKeyClassReadyRequired=True,calls=0,nonframeMemoryWrites=0,entryRspRestored=True,
  restoredNonvolatiles=['rbx','rdi'])

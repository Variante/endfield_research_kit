"""Actual generic interface getter selection and warm MethodInfo cache paths.

The key and callback are source values. Their live closed class, MethodInfo and
cache identities are explicit conditions; a code pointer is not a nominal cast.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check,condition):
 if not condition:raise ValueError('patrolGenericGetter.'+check)


def resolution_wrapper(regions,entry):
 g=BytesPath(regions,entry);g.take('4883ec48','48894c2420','488d4c2420','4889542428','b201','4c89442430')
 site=g.at;target=g.relative('e8');g.take('4883c448','c3')
 return dict(selectedBytes=g.seen,actualCacheCall=dict(instructionVa=site,targetVa=target),
  keyLocal=[32,56],keyQwords=['incoming method definition RCX','incoming class instantiation RDX','incoming method instantiation R8'],
  cacheFlagDl=1,returnsSameCacheResult=True,entryRspRestored=True,nonvolatilesUntouched=True,normalReturn=True)


def cache_hit(regions,entry,*,misses=()):
 need('finite-cache-probes',isinstance(misses,(tuple,list))and len(misses)<=4096 and all(v in('tag','method','class','arguments')for v in misses))
 g=BytesPath(regions,entry);cells={}
 def rip(role,prefix):
  cell=g.relative(prefix);need('same-cache-cell:'+role,role not in cells or cells[role]==cell);cells[role]=cell;return cell
 g.take('48895c2408','48896c2410','4889742418','57','4154','4155','4156','4157','4883ec20',
  '0fb6ea','488bf9','4885c9');g.branch('0f84',False)
 rip('lock','488b0d');lock=g.relative('ff15')
 rip('sentinelCount','4c8b0d');rip('capacity','488b35');rip('slots','4c8b05');rip('occupied','4c390d');g.branch('0f84',False)
 g.take('33d2','488d5eff','488b07','8b4848','488b4708','48c1e803','4803c8','4869c1')
 multiplier=int.from_bytes(g.read(4),'little',signed=True)
 g.take('488b4f10','48c1e903','4803c1','4c8b3f');rip('sentinelKey','4c8b35');rip('sentinelTag','4c8b1d')
 rip('emptyKey','4c8b2d');rip('emptyTag','4c8b25');head=g.at;arms=[]
 for mode in(*misses,'hit'):
  need('same-probe-head',g.at==head);start=len(g.seen)
  g.take('4823c3','488d0c40','453b1cc8');g.branch('74',False,1);g.take('4d85c9');g.branch('0f85',False)
  g.take('488d0c40','41833cc800');g.branch('74',mode!='tag',1)
  if mode!='tag':
   g.take('4d8b54c808','4d3b3a');g.branch('75',mode=='method',1)
   if mode not in('method',):
    g.take('498b4a08','48394f08');g.branch('0f85',mode=='class')
    if mode!='class':
     g.take('498b4a10','48394f10');g.branch('0f85',mode=='arguments')
    if mode in('class','arguments'):g.take('32c9');g.at=g.relative('e9')
    else:g.take('b101')
    g.take('84c9');g.branch('74',mode!='hit',1)
  if mode=='hit':break
  g.take('48ffc2','4803c2');back=g.relative('eb',1);need('exact-quadratic-probe-backedge',back==head);g.at=back;arms.append(g.seen[start:])
 g.take('4883f8ff');g.branch('74',False,1)
 g.take('488d0c40','498d1cc8','488d0476','498d0cc0','483bd9');g.branch('0f85',True)
 g.take('488b5b10');rip('lock','488b0d');unlock=g.relative('ff15');g.take('90','488bc3');g.at=g.relative('eb',1)
 g.take('488b5c2450','488b6c2458','488b742460','4883c420','415f','415e','415d','415c','5f','c3')
 return dict(selectedBytes=g.seen,cells=cells,lockIatCell=lock,unlockIatCell=unlock,hashMultiplier=multiplier,
  hashExpression='((definition.token.u32 + (classInstantiation >> 3)) * signExtendedImmediate + (methodInstantiation >> 3)) modulo2^64',
  capacityPowerOfTwoRequired=True,capacityMask='capacity-1',slotStride=24,slotTagOffset=0,keyPointerOffset=8,resultOffset=16,
  selectedSentinelCountRequiredZero=True,selectedSentinelTagRequiredNonzero=True,selectedOccupiedGreaterThanSentinelCountRequired=True,
  keyComparisonQwords=[0,8,16],keyQwordsComparedUnchanged=True,failedProbeModes=list(misses),failedProbeArms=arms,
  probeStep='probe+=1; slot=(slot+probe)&(capacity-1)',boundedProbesRequired=4096,
  returnsMatchedSlotResultUnchanged=True,cacheMutationProved=False,selectedLockCallsNormallyReturnRequired=True,
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,actualRuntimeCacheIdentityObserved=False)


def invocation(regions,entry,*,interface_steps=0,inflated=True,inline=0,alternate_pointer=False):
 need('finite-interface-selection',type(interface_steps)is int and 0<=interface_steps<=64 and type(inflated)is bool
  and type(inline)is int and inline in(0,1,2,3)and type(alternate_pointer)is bool)
 g=BytesPath(regions,entry);calls=[]
 def call(role):
  at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
 g.take('48895c2408','48896c2410','4889742418','57','4156','4157','4883ec40','4c8bf2','488be9',
  '440fb77950','488b5920','488b3a','488bcf');call('prepareClass')
 g.take('33f6','0fb7c6','440fb78730010000','66413bf0');g.branch('73',False,1)
 g.take('488b97b0000000');head=g.at
 for n in range(interface_steps+1):
  need('same-interface-loop',g.at==head);g.take('0fb7c8','4803c9','48391cca');g.branch('74',n==interface_steps,1)
  if n<interface_steps:g.take('66ffc0','66413bc0');g.branch('72',True,1)
 g.take('0fb7d0','4803d2','488b87b0000000','8b44d008','4103c7','4898','4883c014','48c1e004','4803c7',
  '488b4808','488bd6','f6415402');g.branch('0f85',inflated)
 if inflated:g.take('488b4140','488b5008','488b08');g.at=g.relative('e9')
 g.take('4c8b4540','4d8b4010');call('resolveGenericMethod')
 g.take('488bf8','b958000000','b808000000');switch=g.relative('483935');g.take('0f45c1','4c8b0407','483937');g.branch('0f84',False)
 markers=[]
 for index in range(1,4):
  marker=g.relative('488d05');markers.append(marker);g.take('4c3bc0');g.branch('75'if index<3 else'0f85',inline!=index,1 if index<3 else 4)
  if inline==index:break
 if inline==0:
  g.take('488bd7','498bce','41ffd0','488bd8');g.at=g.relative('e9')
 else:
  g.take('48397738');g.branch('0f84'if inline<3 else'74',False,4 if inline<3 else 1)
  g.take({1:'498b9ed0000000',2:'498b5e30',3:'498b5e28'}[inline],'33d2','488b4f38');resolver=call('indexedContext')
  g.take('488be8')
  if inline==1:
   g.take('33d2','488b4f38');need('same-indexed-context',call('indexedContext')==resolver);g.take('4c8bf0','4885db');g.branch('0f84',False)
  else:g.take('4885db');g.branch('74',False,1)
  g.take('488b3b','488bd7','488bc8');compatible=call('compatibleClass');g.take('84c0')
  g.branch('0f84'if inline<3 else'75',inline==3,4 if inline<3 else 1)
  if inline==1:
   g.take('488b3b','488bd7','488bcd');need('same-compatible-class',call('compatibleClass')==compatible);g.take('84c0');g.branch('0f84',False)
  elif inline==2:g.take('488bf3','488bde');g.at=g.relative('eb',1)
  else:g.take('488bf3','488bde');g.at=g.relative('eb',1)
 g.take('488bc3','488b5c2460','488b6c2468','488b742470','4883c440','415f','415e','5f','c3')
 return dict(selectedBytes=g.seen,calls=calls,interfaceMisses=interface_steps,interfaceEntryBytes=16,
  interfaceMethodSlotOffset=80,declaringInterfaceOffset=32,selectedMethodInfoClassOffset='320 +16*(matched interface offset +incoming method.slot)',
  selectedMethodInfoInflatedBit=2,selectedMethodInfoInflated=inflated,actualMethodKeyOffset=64,
  resolutionArguments=dict(rcx='selected actual method definition',rdx='selected class-inst or zero',r8='incoming MethodInfo.key.methodInstantiation'),
  globalAlternatePointerCell=switch,selectedCallbackPointerOffset=88 if alternate_pointer else 8,
  callbackPointerSelectionRequired=alternate_pointer,inlineMarkerTargets=markers,selectedInline=inline,
  selectedFieldOffset={0:None,1:208,2:48,3:40}[inline],fieldReferenceReturnedUnchanged=inline!=0,
  ordinaryDynamicCallbackResultReturnedUnchanged=inline==0,selectedNonnullCompatibleFieldRequired=inline!=0,
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,actualRuntimeMethodInfoOrCallbackIdentityObserved=False)

"""Exact executor cached EventParams assignment and selected deep-copy programs."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

KINDS=('int','UnityEngine.Vector3','Beyond.Gameplay.Core.EntityPtr')


def need(check,condition):
 if not condition:raise ValueError('patrolExecutorCopy.'+check)


def assign(regions,entry,*,cached,incoming):
 need('literal-Assign-state',type(cached)is bool and type(incoming)is bool)
 g=BytesPath(regions,entry);calls=[]
 def call(role):
  site=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=site,targetVa=target))
 g.take('48895c2408','57','4883ec20');root=g.relative('488b05')
 g.take('488bd9','488bfa','488b4828','4885c9');g.branch('0f85',False)
 g.take('48837b3000');g.branch('74',not cached,1)
 if not cached:
  g.take('33c9');call('newEmpty')
  g.take('488d4b30','48894330');call('barrier');g.jump('eb',1)
 g.take('4885ff');g.branch('74',not incoming,1)
 if incoming:
  g.take('488b5330','4885d2');g.branch('74',False,1)
  g.take('b90a000000');call('clearInvoker')
  g.take('488b4b30','4533c0','488bd7');call('deepCopy')
 g.take('488b5c2430','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,calls=calls,cachedInitiallyNonnull=cached,incomingNonnull=incoming,
  replacementRootCellVa=root,replacementReceiverOffset=40,selectedReplacementRequiredAbsent=True,
  executorCachedEventFieldOffset=48,originalIncomingReferenceStoredInExecutor=False,
  newEmptyResultStoredOnlyWhenCachedNull=not cached,clearSelector=10 if incoming else None,
  clearBeforeDeepCopy=incoming,deepCopyArguments=dict(rcx='same cached executor EventParams',rdx='original incoming EventParams',r8=0)if incoming else None,
  incomingNonnullRequiresDestinationAndSourceDistinct=True,childEffectsRequired=True,
  entryRspRestored=True,restoredNonvolatiles=['rbx','rdi'])


def new_empty(regions,entry):
 g=BytesPath(regions,entry);g.take('4883ec28');root=g.relative('488b05')
 g.take('488bd1','488b4868','4885c9');g.branch('0f85',False)
 cls_site=g.at;cls=g.relative('488b0d');g.take('83b9e000000000');g.branch('74',False,1)
 context_site=g.at;context=g.relative('488b0d');g.take('4883c428');site=g.at;target=g.relative('e9')
 return dict(selectedBytes=g.seen,replacementRootCellVa=root,replacementReceiverOffset=104,
  selectedReplacementRequiredAbsent=True,classUsage=dict(instructionVa=cls_site,cellVa=cls),
  allocateUsage=dict(instructionVa=context_site,cellVa=context),
  allocateTail=dict(instructionVa=site,targetVa=target),samePoolEventReferenceReturned=True,
  selectedNonemptyPoolReuseEffectsRequired=True,freshFactoryOrActivatorEffectsProved=False,
  entryRspRestored=True,nonvolatilesUntouched=True)


def deep_copy(regions,entry,*,count=0):
 need('finite-own-ordinary-key-witness',type(count)is int and 0<=count<=5)
 g=BytesPath(regions,entry);calls=[];usages=[];steps=[]
 def call(role):
  site=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=site,targetVa=target))
 def usage(role,prefix):
  site=g.at;target=g.relative(prefix);usages.append(dict(role=role,instructionVa=site,cellVa=target))
 g.take('48895c2408','57','4881ec90000000','488bd9');root=g.relative('488b05')
 g.take('488b4810','4885c9');g.branch('74',True,1)
 g.take('0f57c0','33c0','0f11442438','0f11442448','4889442458','4885d2');g.branch('0f84',False)
 g.take('488b7a28','4885ff');g.branch('0f84',False)
 usage('getEnumerator','4c8b05');g.take('488bd7','488d4c2460');call('getEnumerator')
 g.take('0f10442460','0f11442438','0f104c2470','0f114c2448','f20f10842480000000','f20f11442458',
  '48c744242800000000','488d442438','4889442430');loop=g.at
 for _ in range(count):
  begin=len(g.seen);need('same-DeepCopy-loop',g.at==loop)
  usage('moveNext','488b15');g.take('488d4c2438');call('moveNext')
  g.take('84c0');g.branch('74',False,1)
  g.take('4885db');g.branch('74',False,1)
  g.take('4533c9','4c8b442450','488b542448','488bcb');call('setVariable')
  g.jump('eb',1);steps.append(g.seen[begin:])
 usage('moveNext','488b15');g.take('488d4c2438');call('moveNext')
 g.take('84c0');g.branch('74',True,1);g.jump('e9')
 g.take('488b9c24a0000000','4881c490000000','5f','c3')
 return dict(selectedBytes=g.seen,calls=calls,usageSites=usages,iterationPrograms=steps,count=count,
  replacementRootCellVa=root,replacementReceiverOffset=16,selectedReplacementRequiredAbsent=True,
  sourceDictionaryFieldOffset=40,enumeratorBytes=40,enumeratorLocalRsp=[56,96],
  exactEnumeratorCopies=[[0,16],[16,16],[32,8]],currentPairLocalRsp=[72,88],
  unchangedCurrentKeyAndValuePassedToSetVariable=True,sameDestinationOnEachCall=True,
  stableDistinctSourceDictionaryRequired=True,sourceEnumerationEffectsRequired=True,
  destinationSetVariableEffectsRequired=True,entryRspRestored=True,restoredNonvolatiles=['rbx','rdi'])


def deep_copy_paths(regions,entry):
 witnesses=[deep_copy(regions,entry,count=n)for n in range(6)]
 steps=[s for p in witnesses for s in p['iterationPrograms']]
 need('one-exact-DeepCopy-iteration',steps and all(s==steps[0]for s in steps))
 return dict(witnesses=witnesses,iteration=steps[0],maximumSelectedLiveKeys=5,
  induction=dict(terminationSuppliedByExactEnumerator=True,sourceSlotsBound=4096,
   sourceCountVersionAndEntriesMustRemainStable=True,eachOccupiedPairForwardedOnce=True,
   uniqueOwnKeyDomainRequired=True),sourceMutationOrAliasProved=False)


def set_variable(regions,entry,*,kind):
 need('exact-selected-Copy-kind',kind in KINDS)
 g=BytesPath(regions,entry);calls=[];uses=[];excluded=[]
 def call(role):
  site=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=site,targetVa=target))
 def use(role):
  site=g.at;target=g.relative('4c8b0d');uses.append(dict(role=role,instructionVa=site,cellVa=target))
 g.take('48896c2410','4889742418','57','4883ec40');root=g.relative('488b05')
 g.take('488be9','498bf8','488bf2','488b4810','4885c9');g.branch('0f85',False)
 g.take('48c744243000000000','4885ff');g.branch('0f84',False)
 g.take('48895c2450','488b4d28','4885c9');g.branch('0f84',False)
 use('lookup');g.take('4c8d442430');call('lookup')
 g.take('84c0');g.branch('0f85',False)
 g.take('488b0f');call('prepare')
 g.take('488b07','4c8b8000020000','488b9008020000')
 for index,branch in enumerate(('74','0f84','0f84')):
  excluded.append(g.relative('488d05'));g.take('4c3bc0');g.branch(branch,index==2 and kind=='int',1 if index==0 else 4)
 if kind=='int':
  g.take('488b4220','b101','488b90c0000000','488b5220');call('allocate')
  g.take('488bd8','488b4718','4885db');g.branch('74',False,1)
  g.take('488d4b18','48894318');call('barrier')
  g.take('b90e000000','488bd7');call('getInt')
  g.take('b90f000000','448bc0','488bd3');call('setInt');g.jump('e9')
 else:
  g.take('488bcf');calls.append(dict(role='copyVirtual',instructionVa=g.at,targetRegister='r8',methodInfoRegister='rdx',selector=12));g.take('41ffd0','488bd8')
 if kind!='int':
  g.take('4885c0');g.branch('0f84',False)
 g.take('488d4b18','48897318');call('barrier')
 g.take('488b4d28','4885c9');g.branch('0f84',False)
 use('setItem');g.take('4c8bc3','488bd6');call('setItem')
 g.take('488b5c2450','488b6c2458','488b742460','4883c440','5f','c3')
 return dict(selectedBytes=g.seen,calls=calls,usageSites=uses,kind=kind,
  replacementRootCellVa=root,replacementReceiverOffset=16,selectedReplacementRequiredAbsent=True,
  destinationDictionaryFieldOffset=40,destinationInitiallyClearedAndKeyAbsentRequired=True,
  sourceVariableNonnullRequired=True,copySelector=12,copyTargetOffset=512,copyMethodInfoOffset=520,
  optimizedCopyTargets=excluded,selectedCopyTargetMustMatchCanonicalKind=True,
  copiedSourceKeyOverwrittenByEnumeratedKey=True,newVariableKeyFieldOffset=24,
  getterSelector=14,setterSelector=15,wholeValueBytes=4 if kind=='int'else 12 if kind=='UnityEngine.Vector3'else 40,
  actualCopyAllocationResetAndValueCallbacksRequired=True,newVariableNotSourceOrExistingDestinationRequired=True,
  sameClonedVariableAndEnumeratedKeyPassedToSetItem=True,entryRspRestored=True,
  restoredNonvolatiles=['rbx','rbp','rsi','rdi'])


def copy_variable(regions,entry,*,kind):
 need('exact-Copy-source-kind',kind in KINDS)
 g=BytesPath(regions,entry);calls=[]
 def call(role):
  site=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=site,targetVa=target))
 frame=32 if kind=='int'else 64 if kind=='UnityEngine.Vector3'else 128
 g.take('48895c2408','57','4883ec'+bytes((frame,)).hex()if frame<128 else'4881ec80000000',
  '488b4220','488bf9'if kind!='UnityEngine.Vector3'else'488bd9','b101','488b90c0000000','488b5220');call('allocate')
 g.take('488bd8'if kind!='UnityEngine.Vector3'else'488bf8','4885ff'if kind!='UnityEngine.Vector3'else'4885db');g.branch('74',False,1)
 g.take('488b4718'if kind!='UnityEngine.Vector3'else'488b4318','4885db'if kind!='UnityEngine.Vector3'else'4885ff');g.branch('74',False,1)
 g.take('488d4b18'if kind!='UnityEngine.Vector3'else'488d4f18','48894318'if kind!='UnityEngine.Vector3'else'48894718');call('barrier')
 if kind=='int':
  g.take('b90e000000','488bd7');call('getInt')
  g.take('b90f000000','448bc0','488bd3');call('setValue')
  g.take('488bc3','488b5c2430','4883c420','5f','c3')
 elif kind=='UnityEngine.Vector3':
  g.take('488b0b');call('prepare')
  g.take('4c8b03','488d4c2430','488bd3','498b8020020000','4d8b8028020000')
  calls.append(dict(role='getVectorVirtual',instructionVa=g.at,targetRegister='rax',selector=14,hiddenResultLocalRsp=[48,60]))
  g.take('ffd0','b90f000000','4c8d442420','488bd7','f20f1000','8b4008','f20f11442420','89442428');call('setValue')
  g.take('488b5c2450','488bc7','4883c440','5f','c3')
 else:
  g.take('ba0e000000','488d4c2450','4c8bc7');call('getEntity')
  g.take('b90f000000','4c8d442420','488bd3','0f1000','0f104810','0f29442420','f20f104020','f20f11442440','0f294c2430');call('setValue')
  g.take('488bc3','488b9c2490000000','4881c480000000','5f','c3')
 return dict(selectedBytes=g.seen,calls=calls,kind=kind,allocateClassContextSlot=4,reusePoolArgument=True,
  sameSourceKeyReferenceCopied=True,keyFieldOffset=24,getterSelector=14,setterSelector=15,
  valueBytes=4 if kind=='int'else 12 if kind=='UnityEngine.Vector3'else 40,
  valueSlices=[]if kind=='int'else[[0,8],[8,4]]if kind=='UnityEngine.Vector3'else[[0,16],[16,16],[32,8]],
  returnedSameNewVariableReference=True,requiresSelectedAllocationAndGetSetEffects=True,
  sourceVariableUntouched=True,entryRspRestored=True,restoredNonvolatiles=['rbx','rdi'])


def enumerator_constructor(regions,entry):
 g=BytesPath(regions,entry)
 g.take('4883ec28','4533db','4c8bd2','4c895908','4c8bc1','4c895910','4c895918','4c895920')
 collector=g.relative('44391d');g.take('488911');g.branch('74',True,1)
 g.take('4d85d2');g.branch('74',False,1)
 g.take('418b422c','0f57c0','41894008','498bc0','4589580c','41c7402002000000','410f114010','4883c428','c3')
 return dict(selectedBytes=g.seen,collectorDisabledFlagVa=collector,inputDictionaryRequiredNonnull=True,
  outputBytes=40,sameDictionaryReferenceAtOffset0=True,versionLoadedFromDictionaryOffset44ToOutputOffset8=True,
  indexInitializedZeroAtOffset12=True,currentPairZero16AtOffset16=True,returnTypeTagAtOffset32=2,
  outputPaddingBytes36To40InitiallyZeroed=True,selectedMethodInfoArgumentUnused=True,
  returnsSameIncomingHiddenResultPointer=True,entryRspRestored=True,nonvolatilesUntouched=True)


def int_get_invoker(regions,entry,*,prepare,callback):
 g=BytesPath(regions,entry);g.take('48895c2408','55','56','57','4154','4155','4156','4157','4883ec50',
  '4c8bf2','0fb7d9','488b0a');g.call(prepare)
 g.take('488d4b14','4803c9','498b06','4c8b04c8','488b54c808');excluded=[]
 for branch in('0f85','75','75'):
  excluded.append(g.relative('488d05'));g.take('4c3bc0');g.branch(branch,True,4 if branch=='0f85'else 1)
 need('actual-Int32-getter-outside-inline-alternatives',callback not in excluded)
 g.take('498bce','41ffd0','488b9c2490000000','4883c450','415f','415e','415d','415c','5f','5e','5d','c3')
 return dict(selectedBytes=g.seen,selector=14,actualCallbackRequired=callback,excludedInlineCallbacks=excluded,
  sameIncomingReceiverAndSelectedMethodInfoPassed=True,returnsSameCallbackEaxBits=True,
  selectedCallbackEffectsRequired=True,entryRspRestored=True,
  restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'])


def entity_get_invoker(regions,entry,*,prepare):
 g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','57','4883ec50','488bf1','0fb7da','498b08','498bf8');g.call(prepare)
 g.take('488b07','4c8d4314','4d03c0','488d4c2420','488bd7','4e8b0cc0','4e8b44c008','41ffd1',
  '488b5c2460','0f1000','0f104810','0f1106','f20f104020','488bc6','0f114e10','f20f114620',
  '488b742468','4883c450','5f','c3')
 return dict(selectedBytes=g.seen,selector=14,hiddenCallbackResultLocalRsp=[32,72],
  actualGetterSourceAndMethodInfoRequired=True,whole40BitsCopiedToSameIncomingHiddenOutput=True,
  slices=[[0,16],[16,16],[32,8]],runtimeReferenceLayoutAdmitted=False,
  entryRspRestored=True,restoredNonvolatiles=['rbx','rsi','rdi'])

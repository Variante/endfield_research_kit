"""Exact generic Lead handle Get caller, with its own register/frame profile.

The storage algorithm is replayed in the actual caller; no other handle body's
registers, nominal type or callback claims are substituted. Actual callee effect
and runtime context/class identities are joined by the enclosing native owner.
"""

def need(check,condition):
 if not condition:raise ValueError('patrolLeadGet.'+check)

def table_program(g,*,interface_steps=0,misses=(),hit=True):
 need('finite-selected-chain',type(interface_steps)is int and 0<=interface_steps<=64 and type(hit)is bool and
  isinstance(misses,(tuple,list))and len(misses)<=4096 and all(type(v)is bool for v in misses))
 start=len(g.seen);calls=[];usages=[]
 def call(role):
  at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
 def use(prefix,role):
  at=g.at;cell=g.relative(prefix);usages.append(dict(role=role,instructionVa=at,cellVa=cell));return cell
 g.take('45397c2408');g.branch('77',True,1)
 cls=use('488b0d','storageClass');g.take('49635c2408','4439b9e0000000');g.branch('75',True,1)
 ready=g.relative('44383d');g.branch('75',True,1)
 g.take('498bc7','4889842498000000');need('same-storage-class-first',use('488b0d','storageClass')==cls)
 g.take('4439b9e0000000');g.branch('75',True,1);need('same-storage-class-second',use('488b05','storageClass')==cls)
 g.take('488b88b8000000','4c8b29','4d85ed');g.branch('0f84',False)
 context=use('488b05','tryGetContext');g.take('48898424a0000000','498b7d18','4885ff');g.branch('0f84',False)
 g.take('488b4820','ba0c000000','488b89c0000000');resolver=call('indexedContext')
 g.take('4c8b37','488be8','498bce');prepare=call('prepareClass')
 g.take('450fb78630010000','410fb7cf','be01000000','66453bf8');g.branch('73',False,1)
 g.take('498b96b0000000','0f1f440000');head=g.at
 for n in range(interface_steps+1):
  need('same-interface-loop-head',g.at==head);g.take('0fb7c1','4803c0','48392cc2');g.branch('74',n==interface_steps,1)
  if n<interface_steps:g.take('66ffc1','66413bc8');g.branch('72',True,1)
 g.take('0fb7c9','4803c9','8b44ca08','ffc0','4898','4883c014','48c1e004','4903c6');g.at=g.relative('eb',1)
 g.take('4c8b08','4c8b7008');marker=g.relative('488d05');g.take('4c3bc8');g.branch('75',False,1)
 g.take('498b4620','488b88c0000000','488b39','4c397f38');g.branch('75',True,1)
 g.take('488b4738','488b08','4c397938');g.branch('75',True,1);g.take('8beb');g.at=g.relative('e9')
 g.take('488bbc24a0000000','488b4f20','488b91c0000000','488b8ae8000000','4c397920');g.branch('75',True,1)
 g.take('488b4720','498b7d10','488b88c0000000','488b81e8000000','4889842490000000','f044093c24','4885ff');g.branch('0f84',False)
 g.take('488b7710','4885f6');g.branch('0f84',False)
 g.take('488b4820','ba02000000','488b89c0000000');need('same-indexed-context-second',call('indexedContext')==resolver)
 g.take('4439b8e0000000');g.branch('75',True,1)
 g.take('488b7f10','4885ff');g.branch('0f84',False)
 g.take('8bc5','0fbaf01f','99','f77e18','3b5718');g.branch('0f83',False)
 g.take('4863c2','488b7cc720','f044093c24','4885ff');empty=not misses and not hit;g.branch('74',empty,1)
 chain=g.at;equals=None;arms=[]
 for n,key_miss in enumerate([*misses,*([True]if hit else[])]):
  need('same-node-loop-entry',g.at==chain);begin=len(g.seen);final=hit and n==len(misses)
  g.take('3b6f28');g.branch('75',not key_miss,1)
  if key_miss:
   g.take('498b7518','448b7710','4885f6');g.branch('0f84',False)
   g.take('488b842490000000','ba0c000000','488b4820','488b89c0000000');need('same-indexed-context-third',call('indexedContext')==resolver)
   g.take('488bd0','895c2420','33c9','458bce','4c8bc6');target=call('keyEquals');need('same-key-equals-target',equals is None or equals==target);equals=target
   g.take('84c0');g.branch('0f85',final)
  if final:
   collector=g.relative('44393d');g.take('488b4718','4889842498000000');g.branch('0f84',True)
  else:
   g.take('488b7f20','f044093c24','4885ff');g.branch('75',n+1<len(misses)or hit,1);arms.append(g.seen[begin:])
 if not hit:g.take('33c0','4889842498000000');collector=None
 return dict(selectedBytes=g.seen[start:],nextInstructionVa=g.at,calls=calls,classUsages=usages,
  metadataReadyFlagVa=ready,storageClassCellVa=cls,actualTryGetContextCellVa=context,
  selectedHashCallbackVa=marker,selectedHashEffect='unchanged incoming proxy-ID Int32 bits',
  indexedContextTargetVa=resolver,preparationTargetVa=prepare,keyEqualityTargetVa=equals,
  interfaceMisses=interface_steps,nodeMisses=list(misses),found=hit,failedNodeArms=arms,
  referenceOutputHome=[152,160],contextHome=[160,168],nodeHashOffset=40,nodeKeyOffset=16,nodeValueOffset=24,nodeNextOffset=32,
  proxyIdOffset=8,proxyIdBytes=4,proxyIdPositiveRequired=True,hashSignBitCleared=True,
  collectorFlagVa=collector,collectorDisabledRequired=hit,stableBoundedAcyclicChainRequired=4096,
  actualCallbackContextOrTableIdentityObserved=False)

def program(regions,entry,*,positive=True,hit=True,interface_steps=0,misses=(),object_id_lane=156):
 from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
 need('finite-Lead-Get-profile',type(positive)is bool and type(hit)is bool and object_id_lane in(156,160))
 g=BytesPath(regions,entry);calls=[]
 def call(role):
  at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
 g.take('4053','56','4154','4157','4883ec68','48837a3800','488bda','4c8be1');g.branch('75',True,1)
 g.take('488b4338','488b30','4889b424a8000000','48837e3800');g.branch('75',True,1)
 ready=(g.relative('803d')+1);g.take('00');g.branch('75',True,1)
 root=g.relative('488b05');g.take('4533ff','48896c2460','48897c2458','4c896c2450','488b4878','4c89742448','4885c9');g.branch('74',True,1)
 g.take('498d542408','4885c9');g.branch('74',True,1);g.take('44393a','0f97c1','84c9');g.branch('74',not positive,1)
 table=None;generic_class=None
 if positive:
  g.take('488b4878','4885c9');g.branch('74',True,1)
  table=table_program(g,hit=hit,interface_steps=interface_steps,misses=misses)
  g.take('4885c0');g.branch('0f84',not hit)
  if hit:
   g.take('498d4c2408','33d2');call('objectGet')
   generic_class=g.relative('488b1d');g.take('488bf8','4885c0');g.branch('0f84',False)
   g.take('488b30','488bcb','488bd6');call('compatibleClass');g.take('84c0');g.branch('75',True,1)
   g.take('418b1424','488bcf');call('containsGeneration');g.take('84c0');g.branch('0f84',False)
   g.take('488bb424a8000000');own_class=g.relative('488b0d');g.take('4439b9e0000000');g.branch('75',True,1)
   need('same-replacement-root',g.relative('488b05')==root);g.take('4c8b4878','4d85c9');g.branch('0f84',True)
   g.take('4439b9e0000000');g.branch('75',True,1);g.take('45397c2404');g.branch('0f86',False)
   g.take('33d2','498bcc');call('proxyGet');g.take('4885c0');g.branch('0f84',False)
   g.take('488b10','448b821c010000','4181e8');class_id=int.from_bytes(g.read(4),'little')
   g.branch('74',object_id_lane==160,1)
   if object_id_lane==156:g.take('4183f801');g.branch('74',True,1);g.take('8b989c000000');g.at=g.relative('eb',1)
   else:g.take('8b98a0000000')
   need('same-own-class-cell',g.relative('488b0d')==own_class);g.take('418b7c2404','4439b9e0000000');g.branch('75',True,1)
   need('same-second-replacement-root',g.relative('488b05')==root);g.take('4c8b5078','4d85d2');g.branch('74',True,1)
   g.take('4439b9e0000000');g.branch('75',True,1);g.take('3bdf');g.branch('0f85',False)
   g.take('33d2','498bcc');call('proxyGet');g.take('4885c0');g.branch('0f84',False)
   g.take('488bc8');call('disposed');g.take('84c0');g.branch('0f85',False)
   g.take('33d2','498bcc');call('proxyGet');g.take('4885c0');g.branch('74',False,1)
   g.take('488b4e38','488bd0','488b09');call('invokeActualGenericGetter');g.take('4c8bf8');g.at=g.relative('e9')
 g.take('4c8b742448','498bc7','4c8b6c2450','488b7c2458','488b6c2460','4883c468','415f','415c','5e','5b','c3')
 return dict(selectedBytes=g.seen,entry=entry,positiveProxyId=positive,tableFound=hit if positive else None,table=table,calls=calls,
  actualOuterMethodContextAt56RequiredReady=True,actualElementMethodContextAt56RequiredReady=True,
  metadataReadyFlagVa=ready,replacementRootCellVa=root,selectedReplacementReceiverAt120RequiredNull=True,
  actualGenericClassCellVa=generic_class,objectIdFieldOffset=object_id_lane,actualLiteralObjectClassId=None if not(positive and hit)else class_id,
  exactObjectCompatibilityGenerationMembershipAndNotDisposedRequired=positive and hit,
  returnsActualGenericGetterResult=positive and hit,returnsNull=not(positive and hit),
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,
  actualLoadedObjectOrGenericContextIdentityObserved=False,calleeEffectsRequireIndependentSource=True)

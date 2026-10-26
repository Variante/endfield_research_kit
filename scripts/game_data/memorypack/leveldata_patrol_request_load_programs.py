"""Literal selected LoadAsset wrapper and state-two processing byte programs."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check,condition):
 if not condition:raise ValueError('patrolRequestLoad.'+check)


def cached_load(regions,entry):
 g=BytesPath(regions,entry);uses=[];calls=[]
 def use(role,prefix):
  at=g.at;cell=g.relative(prefix);uses.append(dict(role=role,instructionVa=at,cellVa=cell));return cell
 def call(role):
  at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
 g.take('4055','53','56','4156','4157','488d6c24d9','4881ecd0000000');root=g.relative('488b05')
 g.take('488bd9','450fb6f9','4d8bf0','488bf2','488b4878','4885c9');g.branch('0f85',False)
 cls=use('manager','4c8b05');g.take('0f57c0','4c89a42408010000','4533e4','4c8965af','0f1145d7','0f1145e7','0f1145f7','0f114507','0f114517',
  '4539a0e0000000');g.branch('0f84',False)
 g.take('488b4878','4889bc2400010000','4885c9');g.branch('0f85',False)
 g.take('4539a0e0000000');g.branch('0f84',False)
 g.take('498b80b8000000','8b481c','b8');multiplier=int.from_bytes(g.read(4),'little',signed=True)
 g.take('f7e9','c1fa');shift=int.from_bytes(g.read(1),'little');g.take('8bc2','c1e81f','03d0','69c2');divisor=int.from_bytes(g.read(4),'little',signed=True)
 g.take('2bc8','498b80b8000000','89481c')
 need('actual-domain-reciprocal-proof',multiplier>0 and 1<divisor<1<<31 and 0<=shift<31 and (divisor-1)*multiplier<1<<(32+shift))
 need('same-manager-class',use('manager','488b15')==cls)
 g.take('488b82b8000000','4439601c');g.branch('0f84',False)
 g.take('4439a2e0000000');g.branch('0f84',False)
 g.take('488b82b8000000','8b481c','ffc1','89481c');need('same-manager-class',use('manager','488b05')==cls)
 g.take('488b88b8000000','8b791c','488b4b10','4c89ac2410010000','4885c9');g.branch('0f84',False)
 g.take('4c8d4daf','4c89642420','4d8bc6','488bd6');call('getOrCreate')
 g.take('4c8b4daf','4d85c9');g.branch('0f84',False)
 need('same-root',g.relative('488b05')==root);g.take('488b4878','4885c9');g.branch('0f85',False)
 g.take('488b45af','83783804');g.branch('0f84',False)
 debug=use('configuration','488b05');g.take('83b8e000000000');g.branch('0f84',False)
 g.take('488b88b8000000','80791200');g.branch('0f85',False)
 g.take('83b8e000000000');g.branch('0f84',False)
 g.take('488b88b8000000','80795000');g.branch('0f85',False)
 g.take('8b4577','450fb6cf','488b55af','448bc7','4c89642428','488bcb','89442420');call('process')
 g.take('4c8bac2410010000','488bbc2400010000','4c8ba42408010000','4881c4d0000000','415f','415e','5e','5b','5d','c3')
 return dict(selectedBytes=g.seen,usageSites=uses,calls=calls,replacementRootCellVa=root,managerClassCellVa=cls,configurationClassCellVa=debug,
  counterFieldOffset=28,divisor=divisor,multiplier=multiplier,shift=shift,
  arithmetic=dict(incomingCounterMinimum=1,incomingCounterMaximum=divisor-1,quotient=0,remainder='same incoming counter',finalCounter='incoming counter+1',
   maximumProduct=(divisor-1)*multiplier,quotientShiftPower=1<<(32+shift),nonnegativeSignedMultiplyAndShiftExact=True),
  cacheReceiverFieldOffset=16,infoBytes=80,cacheOutputHome='RBP-81 reference8',cacheOutputRequiredNonnull=True,
  selectedProxyStateOffset=56,excludedProxyStateLiteral=4,configurationFlagsRequiredZero=[18,80],
  getOrCreateArguments=dict(rcx='own manager.container16',rdx='same AssetInfoPack80 address',r8='same requested Type',r9='output reference local',stack5=0),
  processArguments=dict(rcx='same manager',rdx='same cached proxy',r8d='same incremented operation counter',r9d='same zero-extended incoming bool',stack5='unchanged incoming priority',stack6=0),
  returnValue='unchanged actual process result',entryRspRestored=True,allNonvolatilesRestored=True,
  counterUniquenessOrAtomicityProved=False,actualCacheOrAssetObserved=False)


def process_state_two(regions,entry):
 g=BytesPath(regions,entry)
 g.take('44884c2420','4489442418','4889542410','48894c2408','53','56','57','4154','4155','4156','4157','4881eca0010000',
  '410fb6d9','458bf0','488bfa','488bf1');root=g.relative('488b05')
 g.take('488b4878','4885c9');g.branch('74',True,1)
 g.take('0f57c0','0f118424e0000000','0f118424f0000000','0f11842400010000','0f11842410010000','0f11842420010000','4885ff');g.branch('0f84',False)
 g.take('4885c9');g.branch('74',True,1)
 g.take('837a3802');g.branch('0f84',True)
 g.take('488bc7');g.jump('e9')
 g.take('4881c4a0010000','415f','415e','415d','415c','5f','5e','5b','c3')
 return dict(selectedBytes=g.seen,replacementRootCellVa=root,selectedReplacementReceiverAt120RequiredNull=True,
  selectedProxyRequiredNonnull=True,selectedProxyStateOffset=56,selectedProxyStateLiteral=2,
  sameIncomingProxyReturned=True,noCallsOnSelectedPath=True,noNonframeWritesOnSelectedPath=True,
  entryRspRestored=True,allNonvolatilesRestored=True,runtimeProxyStateObserved=False)

"""Actual cached resource-request and temporary string-block source programs.

The chosen request uses an existing proxy whose literal state is not three.
This is a byte predicate, not a named loading/ready state. Callee effects and
live resource identities require independent joins.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check,condition):
 if not condition:raise ValueError('patrolRequest.'+check)


def request(regions,entry):
 g=BytesPath(regions,entry);calls=[];uses=[]
 def call(role):
  at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
 def use(prefix='488b0d'):
  at=g.at;cell=g.relative(prefix);uses.append(dict(instructionVa=at,cellVa=cell));return cell
 g.take('48895c2408','4889742418','4889542410','57','4156','4157','4881ecf0000000',
  '450fb6f9','4d8bf0','488bda','488bf1');root=g.relative('488b05')
 g.take('488b4878','4885c9');g.branch('74',True,1)
 g.take('33ff','48897c2448','0f57c0','0f118424a0000000','0f118424b0000000','0f118424c0000000',
  '0f118424d0000000','0f118424e0000000','48897c2440','48897c2468')
 use();g.take('39b9e0000000');g.branch('75',True,1);g.take('33c9');call('stringBlock')
 g.take('4889442448','48897c2458','488d442448','4889442460','48837e2800');g.branch('0f84',False)
 g.take('4533c9','4c8d8424a0000000','488bd3','488b4e28');call('info')
 g.take('84c0');g.branch('0f84',False);g.take('488b4e20','4885c9');g.branch('0f84',False)
 g.take('48897c2428','8b842438010000','89442420','440fb68c2430010000','4d8bc6','488d9424a0000000');call('proxy')
 g.take('488bd8','4889442450','4885c0');g.branch('0f84',False)
 need('same-replacement-root',g.relative('488b05')==root);g.take('488b4878','4885c9');g.branch('74',True,1)
 g.take('837b3803');g.branch('0f85',True)
 g.take('488bfb','48895c2440','4c8b442448','4d85c0');g.branch('74',False,1)
 g.take('33c9');use('488b15');call('disposeStringBlock')
 g.jump('e9');g.take('488bc7','4c8d9c24f0000000','498b5b20','498b7330','498be3','415f','415e','5f','c3')
 return dict(selectedBytes=g.seen,calls=calls,usageSites=uses,replacementRootCellVa=root,
  selectedReplacementReceiverAt120RequiredNull=True,selectedProxyStateOffset=56,selectedProxyStateNotEqualLiteral=3,
  infoOutputZeroedBytes=80,requestHash='same incoming RDX',requestedType='same incoming R8',
  proxyArguments=dict(rcx='manager own field32',rdx='full80-byte successful info local',r8='same Type',
   r9d='zero extended incoming stack5 byte',stack5='unchanged incoming stack6 Int32',stack6=0),
  disposeArguments=dict(ecx=0,rdx='actual IDisposable class',r8='same HgStringBlock returned by actual getter'),
  returnValue='same nonnull proxy returned by actual cache helper',entryRspRestored=True,allNonvolatilesRestored=True,
  nonselectedStateThreeVirtualRequestProved=False,calleeEffectsRequireIndependentSource=True,runtimeAssetSelectionObserved=False)


def scope_cached(regions,entry):
 g=BytesPath(regions,entry);uses=[]
 def use(prefix='488b0d'):
  at=g.at;cell=g.relative(prefix);uses.append(dict(instructionVa=at,cellVa=cell));return cell
 g.take('4883ec28');root=g.relative('488b05');g.take('488bd1','488b8898000000','4885c9');g.branch('74',True,1)
 use();g.take('48895c2430','83b9e000000000');g.branch('75',True,1)
 g.take('488b81b8000000','488b18','4885db');g.branch('0f84',False)
 g.take('837b1800','48897c2420');g.branch('0f84',False)
 g.take('83b9e000000000');g.branch('75',True,1)
 g.take('488b81b8000000','488b18','4885db');g.branch('0f84',False)
 g.take('48635318','488b4b10');method_site=g.at;method=g.relative('488b3d')
 g.take('448d42ff','4885c9');g.branch('0f84',False);g.take('443b4118');g.branch('0f83',False)
 g.take('ff431c','488d42ff','44894318','3b4118');g.branch('0f83',False)
 collector=(g.relative('833d')+1);g.take('00');g.relative('4c8d15')
 g.take('4c8b4cc120','488bc2','48c744d11800000000');g.branch('74',True,1)
 use('488b05');g.take('488b88b8000000','4c894910')
 need('same-disabled-collector',(g.relative('833d')+1)==collector);g.take('00');g.branch('0f84',True)
 use('488b15');g.take('83bae000000000');g.branch('75',True,1)
 g.take('488b82b8000000','488b4808','4885c9');g.branch('74',False,1)
 action_site=g.at;action_context=g.relative('4c8b05');g.take('488b5010');call_site=g.at;action=g.relative('e8')
 use('488b05');g.take('488b7c2420','488b5c2430','488b80b8000000','488b4010','4883c428','c3')
 return dict(selectedBytes=g.seen,usageSites=uses,replacementRootCellVa=root,replacementReceiverOffset=152,
  stackMethodInfoSite=dict(instructionVa=method_site,cellVa=method),collectorDisabledFlagVa=collector,
  poolStaticFieldOffset=0,currentBlockStaticFieldOffset=16,activeStackStaticFieldOffset=8,activeStackRequiredNonnull=True,
  activePushCall=dict(instructionVa=call_site,targetVa=action),activePushMethodInfoSite=dict(instructionVa=action_site,cellVa=action_context),
  selectedExistingPoolCountRequiredPositive=True,poolItemStride=8,poolCountOffset=24,poolVersionOffset=28,
  effects='pool.count -=1; pool.version +=1; old last reference cleared; static current block := same popped reference; push same block to active stack; return same block',
  existingPoolArrayAndBoundsRequired=True,entryRspRestored=True,allNonvolatilesRestored=True,
  allocationOrColdInitializationProved=False)


def info_hit(regions,entry,*,failures=0):
 need('bounded-info-search-witness',type(failures)is int and 0<=failures<=3)
 g=BytesPath(regions,entry)
 g.take('48894c2408','55','53','4154','488d6c24b9','4881ecd0000000');root=g.relative('488b05')
 g.take('4c8be2','488bd1','498bd8','488b4878','4885c9');g.branch('74',True,1)
 g.take('0f57c0','4c89ac2408010000','4c8b6a10','0f1145a7','0f1145b7','0f1145c7','4d85ed');g.branch('0f84',False)
 ready=(g.relative('803d')+1);g.take('00','4889b424f8000000','4c89b424c8000000','4c89bc24c0000000');g.branch('75',True,1)
 g.take('49634d40','33d2','498bc4','4889bc2400010000','48f7f1','4533f6','c1e203','4863f2','49037550',
  '4533ff')
 loop=g.at;failed=[]
 for index in range(failures+1):
  start=len(g.seen);g.take('4885f6');g.branch('0f84',False);g.take('443b7604');g.branch('0f8d',False)
  g.take('486306','498bbd98000000','4803f8','4903ff');g.branch('0f84',False)
  g.take('4c3927');g.branch('74',index==failures,1)
  if index<failures:
   g.take('41ffc6','4983c718');back=g.relative('eb',1);need('same-info-search-loop',back==loop);g.at=back;failed.append(g.seen[start:])
 g.take('4c8b7d67','8b770c','4d8b7710','4d85f6');g.branch('0f84',False)
 need('same-info-replacement-root',g.relative('488b05')==root);g.take('488b4878','4885c9');g.branch('74',True,1)
 g.take('85f6');g.branch('0f88',False);g.take('413b7610');g.branch('0f8d',False)
 g.take('8d0476','c1e004','4863c8','498b4618','0f102401','0f1165a7','0f105c0110','0f115db7','0f10540120','0f1155c7',
  '0f100f');g.relative('4c8d0d');g.take('498b4718','f20f104710','4889452f');collector=g.relative('8b05')
 g.take('0f294de7','f20f1145f7','0f1165ff','0f115d0f','0f11551f','85c0');g.branch('74',True,1)
 g.take('0f2845f7','0f110b','0f284d07','0f114310','0f284517','0f114b20','0f284d27','0f114330','0f114b40','85c0');g.branch('74',True,1)
 g.take('b001');g.jump('e9')
 g.take('488bbc2400010000','488bb424f8000000','4c8bb424c8000000','4c8bbc24c0000000','4c8bac2408010000',
  '4881c4d0000000','415c','5b','5d','c3')
 return dict(selectedBytes=g.seen,replacementRootCellVa=root,metadataReadyFlagVa=ready,collectorDisabledFlagVa=collector,
  failedRecords=failures,failedProbeBodies=failed,loopEntryVa=loop,bucketCountOffset=64,bucketBaseOffset=80,
  bucketStride=8,bucketRecordStartOffset=0,bucketRecordCountOffset=4,recordBaseOffset=152,recordStride=24,
  keyOffset=0,keyBytes=8,typeInfoIndexOffset=12,typeDataOwnerOffset=16,typeDataCountOffset=16,typeDataBaseOffset=24,
  typeDataStride=48,sourceOwnerReferenceOffset=24,outputBytes=80,
  output='same record24 +same indexed type-data48 +same owner reference8',
  selectedTypeIndexRequiredNonnegativeAndBelowCount=True,typeIndexTimes48RequiredSigned32Nonwrapping=True,
  positiveBucketCountAndStableBoundedRecordExtentsRequired=True,
  returnBool=True,entryRspRestored=True,allNonvolatilesRestored=True,wireGrammarAdmitted=False,
  actualIndexContentsOrAssetIdentityObserved=False)


def block_push(regions,entry):
 g=BytesPath(regions,entry)
 g.take('48895c2410','48896c2418','56','57','4156','4883ec20','488b7110','498be8','48637918','4c8bf2','488bd9',
  '4885f6');g.branch('0f84',False);g.take('3b7e18');g.branch('72',True,1)
 collector=(g.relative('833d')+1);g.take('00','4c8974fe20');g.branch('74',True,1)
 g.take('ff431c','8d4701','894318','488b5c2448','488b6c2450','4883c420','415e','5f','5e','c3')
 return dict(selectedBytes=g.seen,collectorDisabledFlagVa=collector,arrayFieldOffset=16,countFieldOffset=24,versionFieldOffset=28,
  value='unchanged incoming RDX reference',effect='array[old count] := same reference; version +=1; count := old count+1',
  nonnullSpareArrayAndNonwrappingCountsRequired=True,entryRspRestored=True,allNonvolatilesRestored=True,allocationOrGrowthProved=False)


def dispose_empty_block(regions,entry):
 """Own second inline IDisposable marker, empty block and balanced active stack."""
 g=BytesPath(regions,entry);calls=[];uses=[]
 def call(role):
  at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
 def use(role,prefix='488b05'):
  at=g.at;cell=g.relative(prefix);uses.append(dict(role=role,instructionVa=at,cellVa=cell));return cell
 g.take('48895c2408','48896c2410','4889742418','48897c2420','4156','4883ec30',
  '498b30','498bd8','0fb7e9','488bfa','488bce');call('prepareBlockClass')
 g.take('440fb78630010000','4533f6','410fb7c6','66453bf0');g.branch('73',False,1)
 g.take('488b96b0000000','0fb7c8','4803c9','48393cca');g.branch('74',True,1)
 g.take('0fb7d0','488b86b0000000','4803d2','8b44d008','03c5','4898','4883c014','48c1e004','4803c6','4c8b00','488b7808')
 excluded=g.relative('488d05');g.take('4c3bc0');g.branch('0f85',True)
 marker=g.relative('488d05');g.take('4c3bc0');g.branch('74',True,1)
 root=g.relative('488b05');g.take('488b8898000000','4885c9');g.branch('0f85',False)
 g.take('488b4310','4885c0');g.branch('0f84',False);g.take('44397018');g.branch('0f8f',False)
 use('class');g.take('4439b0e0000000');g.branch('0f84',False)
 g.take('488b80b8000000','488b38','4885ff');g.branch('0f84',False)
 g.take('488b4f10');use('poolPush','488b2d');g.take('48637718','4885c9');g.branch('0f84',False)
 g.take('3b7118');g.branch('0f83',False)
 g.take('488bd6','4c8bc3');call('arrayStore')
 g.take('ff471c','8d4601','894718');use('class')
 g.take('488b88b8000000','488b4908','4885c9');g.branch('0f84',False)
 use('activePop','488b15');call('activePop')
 use('class','488b0d');g.take('488b81b8000000','488b5008','4885d2');g.branch('0f84',False)
 g.take('44397218');g.branch('0f8e',True)
 g.take('4439b1e0000000');g.branch('0f84',False)
 g.take('488b81b8000000','4c897010');g.jump('e9')
 use('class');g.take('488b88b8000000','4883c110');call('barrier');g.jump('e9')
 g.take('488b5c2440','488b6c2448','488b742450','488b7c2458','4883c430','415e','c3')
 return dict(selectedBytes=g.seen,calls=calls,usageSites=uses,selectedCallbackTargetVa=marker,excludedEarlierCallbackTargetVa=excluded,
  interfaceSelectorRequired=0,actualVtableBaseOffset=320,actualVtableRecordBytes=16,selectedFirstInterfaceRecordRequired=True,
  replacementRootCellVa=root,replacementReceiverOffset=152,selectedBlockStackRequiredEmpty=True,
  selectedActiveStackRequiredCountBeforePop=1,selectedActiveStackRequiredEmptyAfterPop=True,
  effects='push same block to spare pool; pop active stack; set current block null; restore whole caller frame',
  temporaryStringsCreatedOrRecycled=False,entryRspRestored=True,allNonvolatilesRestored=True,
  helpersRequireIndependentSource=True,actualRuntimeCallbackOrPoolIdentityObserved=False)


def array_store(regions,entry):
 g=BytesPath(regions,entry);g.take('4883ec28','3b5118');g.branch('73',False,1)
 collector=(g.relative('833d')+1);g.take('00','4c8944d120');g.branch('74',True,1);g.take('4883c428','c3')
 return dict(selectedBytes=g.seen,collectorDisabledFlagVa=collector,arrayLengthOffset=24,dataOffset=32,elementBytes=8,
  effect='same array[index] := unchanged incoming R8 reference',unsignedIndexBoundsCheckedBeforeStore=True,
  entryRspRestored=True,allNonvolatilesUntouched=True,normalReturn=True)


def block_pop(regions,entry):
 g=BytesPath(regions,entry)
 g.take('48895c2410','48896c2418','56','57','4156','4883ec20','48636918','488bf2','488b5910','488bf9','448d75ff','4885db');g.branch('0f84',False)
 g.take('443b7318');g.branch('0f83',False)
 g.take('ff411c','4c8d4dff','44897118','443b4b18');g.branch('0f83',False)
 g.take('4e8b4ccb20','488d45ff','3b4318');g.branch('0f83',False)
 collector=(g.relative('833d')+1);g.take('00','48c744c32000000000');g.branch('74',True,1)
 g.take('488b5c2448','498bc1','488b6c2450','4883c420','415e','5f','5e','c3')
 return dict(selectedBytes=g.seen,collectorDisabledFlagVa=collector,arrayFieldOffset=16,countFieldOffset=24,versionFieldOffset=28,
  arrayDataOffset=32,elementBytes=8,nonnullArrayAndPositiveValidCountRequired=True,
  effect='version +=1; count -=1; same old final reference returned; old final slot cleared',
  sameFinalReferenceReturned=True,entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True)

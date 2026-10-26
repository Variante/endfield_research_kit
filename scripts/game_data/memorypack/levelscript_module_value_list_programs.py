"""Exact EffectInfo48/AirWallPtr24 list schedules, without nominal admission.

Each caller must separately authenticate its closed value carrier, callback,
constructor and operational Add storage. Managed copy sizes never specify the
element wire grammar. Only fresh count-sized lists are selected here.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.levelscript_module_value_transfer_programs import EFFECT,AIRWALL,_calls

WIDTHS={EFFECT:48,AIRWALL:24}


def need(key,condition):
 if not condition:raise ValueError('moduleValueListProgram.'+key)


def list_program(regions,entry,*,type_name,count,symbols=None):
 need('finite-profile',type_name in WIDTHS and type(count)is int and -1<=count<=3)
 g=BytesPath(regions,entry);roles,call=_calls(g,symbols);effect=type_name==EFFECT
 callbacks=[];adds=[];provider=None;provider_site=None;backedge=None
 if effect:
  g.take('48895c2408','4889742418','55','57','4154','4155','4157','488d6c24c9','4881ecb0000000','4533ed','498bd9')
  ready=g.relative('44382d');g.take('498bf8','4c8be2');g.branch('75',True,1)
  g.take('0f57c0','44896d6f','488d556f','498bcc','0f1145a7','0f1145b7','0f1145c7');call('header')
 else:
  g.take('4053','55','4154','4156','4883ec68');ready=g.relative('803d');g.take('00','498bd9','4d8bf0','4c8be2');g.branch('0f84',False)
  g.take('0f57c0','488d942498000000','33c0','33ed','498bcc','89ac2498000000','0f11442440','4889442450');call('header')
 g.take('84c0');g.branch('0f84',count==-1)
 if count==-1:
  g.take('488bcf'if effect else'498bce','4c892f'if effect else'49892e');call('barrier')
 else:
  if effect:
   g.take('488b4320','4c392f');g.branch('74',True,1)
   g.take('488b88c0000000','488b09');call('context');g.take('488bc8');call('allocate')
   g.take('488bf0','4885c0');g.branch('0f84',False)
   g.take('488b4b20','488b91c0000000','488b4a08','4c396920');g.branch('75',True,1)
   g.take('488b4320','488bce','8b556f','4c8b80c0000000','4d8b4008');call('constructor')
   g.take('488bcf','488937');call('barrier');provider_site=g.at;provider=g.relative('488b0d');call('classInit')
   g.take('488b4320','488b88c0000000','488b4918');call('provider')
   g.take('488bf0','458bfd','44396d6f');g.branch('0f8e',count==0)
  else:
   g.take('4c897c2460','4889b42490000000','4889bc24a0000000','448bbc2498000000','49392e');g.branch('0f85',False)
   g.take('488b4b20','33d2','488b89c0000000');call('context');g.take('488bc8');call('allocate')
   g.take('488bf8','4885c0');g.branch('75',True,1)
   g.take('488b4b20','488b91c0000000','488b4a08','48396920');g.branch('0f84',False)
   g.take('488b4320','418bd7','488bcf','4c8b80c0000000','4d8b4008');call('constructor')
   g.take('498bce','49893e');call('barrier');provider_site=g.at;provider=g.relative('488b0d')
   g.take('39a9e0000000');g.branch('0f84',False)
   g.take('488b4320','488b88c0000000','488b4918');call('provider');g.take('488bf8','4585ff');g.branch('0f8e',count==0)
  for index in range(count):
   if effect:
    g.take('0f57c0','0f1145a7','0f1145b7','0f1145c7','4885f6');g.branch('0f84',False)
    g.take('4c8d4da7','4d8bc4','488bd6');callbacks.append(call('dispatch'))
    g.take('0f1045a7','4c8b2f','0f104db7','0f1055c7','0f1145d7','0f114de7','0f1155f7','4d85ed');g.branch('74',False,1)
    g.take('488b4320','488b88c0000000','488b4130','4883782000');g.branch('75',True,1)
    g.take('488b4320','488d5507','498bcd','0f294507','0f294d17','0f295527','4c8b80c0000000','4d8b4030')
    adds.append(call('Add'));g.take('41ffc7','443b7d6f');backedge=g.at;g.branch('0f8c',index+1<count)
   else:
    g.take('33c0','0f57c0','4889442450','0f11442440','4885ff');g.branch('0f84',False)
    g.take('4c8d4c2440','4d8bc4','488bd7');callbacks.append(call('dispatch'))
    g.take('0f10442440','498b36','f20f104c2450','f20f118c2498000000','0f11442420','4885f6');g.branch('0f84',False)
    g.take('488b4320','488b88c0000000','488b4130','4883782000');g.branch('0f84',False)
    g.take('488b4320','488d542420','488bce','0f29442420','f20f114c2430','4c8b80c0000000','4d8b4030')
    adds.append(call('Add'));g.take('ffc5','413bef');backedge=g.at;g.branch('0f8c',index+1<count)
  if effect:
   if count:g.jump('eb',1)
  else:g.take('488bbc24a0000000','488bb42490000000','4c8b7c2460')
 if effect:g.take('4c8d9c24b0000000','498b5b30','498b7340','498be3','415f','415d','415c','5f','5d','c3')
 else:g.take('4883c468','415e','415c','5d','5b','c3')
 return dict(selectedBytes=g.seen,symbolTargets=roles,typeName=type_name,countWitness=count,newList=count!=-1,
  metadataReadyFlagVa=ready,providerClassCell=provider,providerClassInstructionVa=provider_site,
  headerBytes=4,managedElementBytes=WIDTHS[type_name],elementWireBytes=None,elementCallbackSites=callbacks,AddCallSites=adds,
  backedgeInstructionVa=backedge,initiallyNullListRequired=True,wholeCallbackValueCopied=True,
  callbackOutputZeroBytes=WIDTHS[type_name],normalReturn=True,entryRspRestored=True,allNonvolatilesRestored=True,
  frame=(dict(entryRspDelta=-216,rbpEntryOffset=-95,callShadow=[0,32],callbackLocal=[32,80],captureLocal=[80,128],
   AddLocal=[128,176],savedCountEntryHome=[16,20],savedEntryHomes=dict(rbx=[8,16],rsi=[24,32]),pushed=['rbp','rdi','r12','r13','r15'])if effect else
   dict(entryRspDelta=-136,callShadow=[0,32],callbackLocal=[64,88],AddLocal=[32,56],highCaptureEntryHome=[16,24],
    highCaptureReusesDeadCountHome=True,savedCountRegister='r15d',counterRegister='ebp',
    savedPositiveHomes=dict(r15=[-40,-32],rsi=[8,16],rdi=[24,32]),pushed=['rbx','rbp','r12','r14'])),
  growthAdmitted=False,elementGrammarAdmitted=False,nominalAdmissionGranted=False)


def effect_add_forwarder(regions,entry,*,target):
 g=BytesPath(regions,entry)
 g.take('4883ec58','0f1002','0f104a10','0f29442420','0f104220','488d542420','0f294c2430','0f29442440')
 site=g.at;g.call(target);g.take('4883c458','c3')
 return dict(selectedBytes=g.seen,managedArgumentBytes=48,copiedSlices=[[0,16],[16,16],[32,16]],
  sameIncomingReceiverAndMethodInfo=True,delegateInstructionVa=site,delegateTargetVa=target,
  frame=dict(entryRspDelta=-88,callShadow=[0,32],argumentLocal=[32,80]),
  entryRspRestored=True,normalReturn=True,pointerEquivalenceClaimed=False)


def effect_add_core(regions,entry,*,storage):
 g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','57','4883ec50','ff411c','488bd9','488b4910','488bf2','498bf8','48635318','4885c9')
 g.branch('75',True,1);g.take('3b5118');g.branch('72',True,1)
 g.take('0f1006','8d4201','0f104e10','4c8d442420','894318','0f29442420','0f104620','0f294c2430','0f29442440')
 site=g.at;g.call(storage);g.take('488b5c2460','488b742468','4883c450','5f','c3')
 return dict(selectedBytes=g.seen,managedElementBytes=48,sizeOffset=24,versionOffset=28,itemsOffset=16,
  versionIncrement=1,sizeIncrement=1,wholeArgumentCopiedBytes=48,storageCallInstructionVa=site,
  storageArguments=dict(rcx='same List items array',rdx='initial nonnegative List size',r8='own copied48 local'),
  frame=dict(entryRspDelta=-88,callShadow=[0,32],argumentLocal=[32,80]),
  growthAdmitted=False,entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True)


def effect_storage(regions,entry,*,barrier):
 g=BytesPath(regions,entry)
 g.take('4883ec28','3b5118');g.branch('72',True,1)
 g.take('410f2800','488d0452','410f284810','4803c0','0f1144c120','410f284020','0f114cc130','0f1144c140',
  '488d0452','4883c120','48c1e004','4803c8','4883c428')
 need('same-element-start-reference-barrier',g.relative('e9')==barrier)
 return dict(selectedBytes=g.seen,arrayStride=48,arrayDataOffset=32,arrayLengthOffset=24,
  completeStoredBytes=48,sourceSlices=[[0,16],[16,16],[32,16]],stores=[[0,16],[16,16],[32,16]],
  selectedBarrierOffset=0,referenceLaneOffsets=[0],sameArrayIndexUnchanged=True,
  normalReturnViaBarrier=True,entryRspRestored=True,allNonvolatilesRestored=True)


def airwall_add(regions,entry):
 g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','57','4883ec40','ff411c','488bd9','4c8b4910','498bf0','48634918','488bfa','4d85c9')
 g.branch('0f84',False);g.take('413b4918');g.branch('73',False,1)
 g.take('8d4101','894318','413b4918');g.branch('0f83',False)
 g.take('0f1002','488d0c49','f20f104a10','410f1144c920','f2410f114cc930',
  '488b5c2450','488b742458','4883c440','5f','c3')
 return dict(selectedBytes=g.seen,arrayStride=24,arrayDataOffset=32,sourceSlices=[[0,16],[16,8]],
  stores=[[0,16],[16,8]],completeStoredBytes=24,itemsOffset=16,sizeOffset=24,versionOffset=28,
  sizeIncrement=1,versionIncrement=1,growthAdmitted=False,entryRspRestored=True,normalReturn=True,
  allNonvolatilesRestored=True,referenceLaneOffsets=[])


def airwall_capacity(regions,entry,*,positive,symbols=None):
 need('literal-capacity-mode',type(positive)is bool);g=BytesPath(regions,entry);roles,call=_calls(g,symbols)
 g.take('48895c2408','4889742410','57','4883ec20','8bda','498bf8','488bf1','85d2');g.branch('0f88',False)
 g.take('498b4820','488b89c0000000');g.branch('0f84',not positive)
 if positive:g.take('ba01000000');call('context');g.take('8bd3','488bc8');call('arrayAllocate')
 else:
  g.take('33d2');call('context');g.take('83b8e000000000');g.branch('75',True,1)
  g.take('488b4f20','33d2','488b89c0000000');call('context');g.take('488b88b8000000','488b01');g.jump('e9')
 g.take('488d4e10','48894610','488b5c2430','488b742438','4883c420','5f');target=g.relative('e9')
 need('actual-barrier-tail',symbols is None or symbols.get('barrier')==target);roles['barrier']=target
 return dict(selectedBytes=g.seen,symbolTargets=roles,positiveCapacity=positive,requestedCapacityUnchanged=True,
  itemsOffset=16,directSizeOrVersionWrites=False,arrayTypeContextSlot=1,emptyArrayContextSlot=0,
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturnViaBarrier=True)


def airwall_provider(regions,entry,*,symbols=None):
 g=BytesPath(regions,entry);roles,call=_calls(g,symbols)
 g.take('48895c2410','57','4883ec20','4883793800','488bf9');g.branch('75',True,1)
 type_site=g.at;type_cell=g.relative('488b0d');g.take('488b5f38','83b9e000000000','488b1b');g.branch('75',True,1)
 g.take('33d2','488bcb');call('typeHandle');provider_site=g.at;provider_cell=g.relative('488b0d')
 g.take('488bd8','83b9e000000000');g.branch('75',True,1)
 g.take('488bcb');call('backend');g.take('488b4f38','ba01000000','488bd8');call('context')
 g.take('488bd0','488bcb');call('cast');g.take('4885c0');g.branch('0f84',False)
 g.take('488b5c2438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,symbolTargets=roles,typeClassInstructionVa=type_site,typeClassCell=type_cell,
  providerClassInstructionVa=provider_site,providerClassCell=provider_cell,typeContextSlot=0,formatterContextSlot=1,
  sameFullBackendReferenceReturned=True,normalReturn=True,entryRspRestored=True,allNonvolatilesRestored=True)


def airwall_dispatch(regions,entry,*,canonical,symbols=None,null=False,create=True):
 """The actual callback equality selects an owned inlined canonical24 body."""
 need('literal-inline-path',type(null)is bool and type(create)is bool and type(canonical)is int)
 g=BytesPath(regions,entry);roles,call=_calls(g,symbols)
 g.take('48895c2408','48896c2410','4889742418','57','4883ec20','488b0a','498be9','498bf0','488bda');call('prepare')
 g.take('488b3b');selected=g.relative('488d0d');need('actual-canonical-equality',selected==canonical)
 g.take('488b8790010000','488bbf98010000','483bc1');g.branch('0f85',False)
 ready=g.relative('803d');g.take('00');g.branch('0f84',False)
 g.take('488b4720','488bce','488b90c0000000','488b12');call('readNull');g.take('84c0');g.branch('0f85',null)
 type_site=type_cell=None
 if null:g.take('0f57c0','33c0','0f114500','48894510');g.jump('e9')
 else:
  g.take('488b4720');type_site=g.at;type_cell=g.relative('488b0d')
  g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('74',False,1)
  g.take('33d2','488bcb');call('typeHandle');g.take('4885c0');g.branch('74',False,1)
  g.take('33d2','488bc8');call('creationTest');g.take('84c0');g.branch('75',not create,1)
  if create:g.take('488b4720','488b88c0000000','488b4958');call('activate')
  else:g.take('33c0');g.jump('eb',1)
  g.take('488b4f20','4c8bc0','488bd5','4c8b89c0000000','488bce','4d8b4918');call('nonnull')
 g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,symbolTargets=roles,selectedCanonicalVa=canonical,metadataReadyFlagVa=ready,
  typeClassInstructionVa=type_site,typeClassCellVa=type_cell,canonicalFF=null,defaultZeroBytes=24 if null else 0,
  incomingReader='R8 -> RSI',incomingOutput='R9 -> RBP',sameCanonicalMethodInfo='slot5 MethodInfo -> RDI',
  fullManagedOutputBytes=24,normalReturn=True,entryRspRestored=True,allNonvolatilesRestored=True,
  actualCallbackEqualsCanonicalRequired=True,otherCallbackAdmitted=False,nominalAdmissionGranted=False)

"""GameAction radio request, exact value56 payload and static-cache programs."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check,condition):
 if not condition:raise ValueError('patrolRadioRequest.'+check)


def play(regions,entry,*,nonnull=True,nonempty=True):
 need('literal-string-path',type(nonnull)is bool and type(nonempty)is bool and(nonnull or not nonempty))
 g=BytesPath(regions,entry);calls=[];uses=[]
 def call(role):
  at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
 def use(role):
  at=g.at;cell=g.relative('488b0d');uses.append(dict(role=role,instructionVa=at,cellVa=cell));return cell
 g.take('488bc4','48895808','48897010','48897818','55','4156','4157','488d68a9','4881ecf0000000')
 ready=(g.relative('803d')+1);g.take('00','418af1','458bf0','448afa','488bf9');g.branch('75',True,1)
 root=g.relative('488b05');g.take('488b4828','4885c9');g.branch('74',True,1)
 g.take('0f57c0','33c0','488945c7','0f114597','0f1145a7','0f1145b7','4885ff');g.branch('0f84',not nonnull)
 if nonnull:g.take('394710');g.branch('0f86',not nonempty)
 if nonnull and nonempty:
  use('predefinedKeySingleton');call('singleton');g.take('4885c0');g.branch('75',True,1)
  g.take('8b980c050000','488d4d97','48c744243000000000','458bce','48c744242800000000','458ac7',
   '488bd7','48c744242000000000');call('payloadConstructor')
  g.take('0f104597');use('eventManagerClass')
  g.take('408875c7','0f1145cf','0f1045a7','0f1145df','0f1045b7','0f1145ef','f20f1045c7','f20f11458f');call('readyEventManager')
  g.take('0f1045cf','488d55ff','8bcb','0f104ddf','0f2945ff','0f1045ef','0f294d0f','0f29451f','f20f10458f','f20f11452f');call('sendWrapper')
 g.take('4c8d9c24f0000000','498b5b20','498b7328','498b7b30','498be3','415f','415e','5d','c3')
 return dict(selectedBytes=g.seen,calls=calls,usageSites=uses,metadataReadyCellVa=ready,replacementRootCellVa=root,
  selectedReplacementReceiverAt40RequiredNull=True,inputNonnull=nonnull,inputNonempty=nonempty,
  predefinedKeyFieldOffset=1292,predefinedKeyBytes=4,payloadBytes=56,payloadInitiallyZeroedBytes=56,
  payloadConstructorArguments=dict(rcx='zeroed56-byte local',rdx='unchanged incoming radioId string',r8b='unchanged incoming fromBegin DL',
   r9d='unchanged incoming index R8D',stack5=0,stack6=0,stack7=0),
  finalPayloadNoFlushByteOffset=48,finalPayloadNoFlushByte='unchanged incoming R9B',
  sendArguments=dict(ecx='unchanged actual SHOW_RADIO field raw4',rdx='complete unchanged16+16+16+8 payload after noFlush update'),
  output='no request'if not(nonnull and nonempty)else'actual typed global radio request',
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,actualRadioPlaybackObserved=False)


def stop(regions,entry,*,nonnull=True,nonempty=True):
 need('literal-string-path',type(nonnull)is bool and type(nonempty)is bool and(nonnull or not nonempty))
 g=BytesPath(regions,entry);calls=[];uses=[]
 def call(role):
  at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
 def use(role,prefix='488b0d'):
  at=g.at;cell=g.relative(prefix);uses.append(dict(role=role,instructionVa=at,cellVa=cell));return cell
 g.take('48895c2408','57','4883ec20');ready=(g.relative('803d')+1);g.take('00','488bda','488bf9');g.branch('75',True,1)
 root=g.relative('488b05');g.take('488b4828','4885c9');g.branch('74',True,1)
 g.take('4885ff');g.branch('74',not nonnull,1)
 if nonnull:g.take('837f1000');g.branch('76',not nonempty,1)
 if nonnull and nonempty:
  use('predefinedKeySingleton');call('singleton');g.take('4885c0');g.branch('75',True,1)
  use('eventManagerClass');g.take('8b9810050000');call('readyEventManager')
  use('sendMethodInfo','4c8b05');g.take('488bd7','8bcb');call('sendString')
 g.take('488b5c2430','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,calls=calls,usageSites=uses,metadataReadyCellVa=ready,replacementRootCellVa=root,
  selectedReplacementReceiverAt40RequiredNull=True,inputNonnull=nonnull,inputNonempty=nonempty,
  predefinedKeyFieldOffset=1296,predefinedKeyBytes=4,sendArguments=dict(ecx='unchanged actual MANUAL_STOP_RADIO field raw4',
   rdx='unchanged incoming radioId string',r8='unchanged actual closed SendGlobal<string> MethodInfo'),
  output='no request'if not(nonnull and nonempty)else'actual typed global stop request',
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,actualRadioPlaybackObserved=False)


def payload_constructor(regions,entry):
 g=BytesPath(regions,entry);calls=[]
 def barrier():
  at=g.at;target=g.relative('e8');calls.append(dict(instructionVa=at,targetVa=target));return target
 g.take('4883ec28','458ad0','488911','4c8bd9');target=barrier()
 g.take('488b442450','498d4b18','49894318','45885308','45894b0c');need('same-barrier2',barrier()==target)
 g.take('4c8b4c2458','498d4b10','4d894b10');need('same-barrier3',barrier()==target)
 g.take('4533c9','41c7432c24000000','b80000803f','6645894b20','41894324','41894328','45884b30','4883c428','c3')
 return dict(selectedBytes=g.seen,barrierCalls=calls,payloadReferenceOffsets=[0,16,24],
  writes=[dict(offset=0,bytes=8,value='incoming radioId RDX'),dict(offset=8,bytes=1,value='incoming fromBegin R8B'),
   dict(offset=12,bytes=4,value='incoming index R9D'),dict(offset=16,bytes=8,value='incoming entity stack6'),
   dict(offset=24,bytes=8,value='incoming callback stack5'),dict(offset=32,bytes=2,value=0),
   dict(offset=36,bytes=4,value=0x3f800000),dict(offset=40,bytes=4,value=0x3f800000),dict(offset=44,bytes=4,value=36),dict(offset=48,bytes=1,value=0)],
  otherBytesPreserved=True,selectedBarriersRequiredNoCallsOrMemoryWritesAndPreserveR10R11=True,
  entryRspRestored=True,allNonvolatilesUntouched=True,normalReturn=True)


def send56_wrapper(regions,entry):
 g=BytesPath(regions,entry);g.take('4883ec68','0f1002');at=g.at;context=g.relative('4c8b05')
 g.take('0f104a10','0f29442420','0f104220','0f294c2430','f20f104a30','488d542420','0f29442440','f20f114c2450')
 site=g.at;target=g.relative('e8');g.take('4883c468','c3')
 return dict(selectedBytes=g.seen,methodInfoSite=dict(instructionVa=at,cellVa=context),
  actualSendCall=dict(instructionVa=site,targetVa=target),copiedSlices=[[0,16],[16,16],[32,16],[48,8]],copiedBytes=56,
  outgoingArguments=dict(ecx='unchanged incoming CombineKey raw4',rdx='same complete56-byte local RSP32',r8='actual closed MethodInfo'),
  entryRspRestored=True,allNonvolatilesUntouched=True,normalReturn=True)


def singleton_cached(regions,entry):
 g=BytesPath(regions,entry);calls=[]
 def call(role):
  at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
 g.take('4053','4883ec20','488bd9','488b4920');ready=call('readyContext')
 g.take('33d2','488b88c0000000');indexed=call('indexedContext')
 g.take('488b88b8000000','48833900');g.branch('74',False,1)
 g.take('488b4b20');need('same-ready-helper',call('readyContext')==ready)
 g.take('33d2','488b88c0000000');need('same-indexed-helper',call('indexedContext')==indexed)
 g.take('488b80b8000000','488b00','4883c420','5b','c3')
 return dict(selectedBytes=g.seen,calls=calls,incomingMethodInfoClassOffset=32,classContextOffset=192,indexedSlot=0,
  staticFieldsOffset=184,staticReferenceOffset=0,selectedStaticReferenceRequiredNonnull=True,
  returnedSameStaticReferenceUnchanged=True,entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True)


def class_ready(regions,entry):
 g=BytesPath(regions,entry);g.take('4883ec28','83b9e000000000');g.branch('74',False,1);g.take('4883c428','c3')
 return dict(selectedBytes=g.seen,selectedActualClassInitializedRequired=True,nonframeMemoryWrites=0,calls=0,
  entryRspRestored=True,allNonvolatilesUntouched=True,normalReturn=True)

"""Exact UInt64/Int32 dictionary and aggregate entry instruction programs."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check,condition):
 if not condition:raise ValueError('runeDictionaryProgram.'+check)


def dictionary(regions,entry,*,count):
 need('finite-count-witness',type(count)is int and -1<=count<=3)
 g=BytesPath(regions,entry);calls=[];contexts=[];loops=[];edges=[]
 def call(role):
  at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
 g.take('48895c2408','4889742418','57','4154','4155','4156','4157','4883ec40','4533e4','498bd9')
 ready=g.relative('443825');g.take('498bf8','4c8bfa','488bf1');g.branch('75',True,1)
 g.take('488d542478','4489642478','498bcf','4c89642438','4489642430');call('header')
 g.take('84c0');g.branch('0f84',count==-1)
 if count==-1:
  g.take('488bcf','4c8927');call('barrier')
 else:
  g.take('488b4320','4c3927');g.branch('74',True,1)
  g.take('488b88c0000000','4c8b7610','488b4918');call('class-resolution');g.take('488bc8');call('allocate')
  g.take('488bf0','4885c0');g.branch('0f84',False)
  g.take('488b4b20','488b91c0000000','488b4a20','4c396120');g.branch('75',True,1)
  g.take('488b4320','4d8bc6','8b542478','488bce','4c8b88c0000000','4d8b4920');call('dictionary-constructor')
  g.take('488bcf','488937');call('barrier');at=g.at;cell=g.relative('488b0d');contexts.append(dict(role='provider-class',instructionVa=at,cellVa=cell));call('provider-class-initialization')
  g.take('488b4320','488b88c0000000','488b4930');call('key-provider')
  g.take('488b4b20','4c8be0','488b89c0000000','488b4938');call('value-provider')
  g.take('33f6','4c8be8','39742478');g.branch('0f8e',count==0)
  if count:
   loop=g.at
   for i in range(count):
    need('same-actual-entry-loop',g.at==loop);before=len(g.seen)
    g.take('488b4b20','488d442430','4c8d4c2438','4d8bc7','488b91c0000000','488b4a40','498bd5',
     '48894c2428','498bcc','4889442420');call('key-value-pair')
    g.take('4c8b37','4d85f6');g.branch('74',False,1)
    g.take('488b4320','488b88c0000000','488b4148','4883782000');g.branch('75',True,1)
    g.take('488b4320','498bce','448b442430','488b542438','4c8b88c0000000','4d8b4948');call('add')
    g.take('ffc6','3b742478');edges.append(g.at);g.branch('0f8c',i+1<count);loops.append(g.seen[before:])
   g.jump('eb',1)
 g.take('4c8d5c2440','498b5b30','498b7340','498be3','415f','415e','415d','415c','5f','c3')
 return dict(selectedBytes=g.seen,countWitness=count,newDictionary=True,initiallyNullOutputRequired=True,
  metadataReadyFlagVa=ready,calls=calls,contexts=contexts,loopBodies=loops,backedgeSites=edges,
  elementCallbacks=len(loops),countHome=[120,124],keyHome=[56,64],valueHome=[48,52],pairMethodInfoArgument=[40,48],
  valueOutputArgument=[32,40],sameReader=True,samePublishedDictionaryUsedForAdd=True,
  keyBits=64,valueBits=32,entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,reusedDictionaryAdmitted=False)


def header(regions,entry,o):
 b=lambda k:bytes((o[k],)).hex();g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','57','4883ec20','8379'+b('bufferLength')+'04','488bfa','488bd9');g.branch('0f8c',False)
 g.take('488b43'+b('currentPtr'),'8b08','890f','8b73'+b('bufferLength'),'83c6fc');g.branch('0f88',False)
 g.take('488343'+b('currentPtr')+'04','8343'+b('advancedCount')+'04','8343'+b('consumed')+'04','8973'+b('bufferLength'),
  '486343'+b('consumed'),'488b4b'+b('totalLength'),'448b07','482bc8','4963c0','483bc8');g.branch('0f8c',False)
 g.take('488b5c2430','4183f8ff','488b742438','0f95c0','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,headerBytes=4,signedCountStoredUnchanged=True,returnedBoolFalseExactlyForCountMinusOne=True,
  remainingTotalBytesAtLeastSignedCountRequired=True,allFourReaderUpdatesProved=True,
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,refillOrMalformedCountsAdmitted=False)


def pair(regions,entry):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec30','488b5c2468','498bf9','498bf0','48837b3800');g.branch('75',True,1)
 g.take('4c8b4338','488d542420','0f57c0','488bce','0f11442420','4d8b00');site=g.at;target=g.relative('e8')
 g.take('488b442420','488b4c2460','488b5c2440','488b742448','488907','8b442428','8901','4883c430','5f','c3')
 return dict(selectedBytes=g.seen,rawReaderTargetVa=target,rawReaderInstructionVa=site,
  internalReaderMethodContextSlot=0,MethodInfoContextOffset=56,sameReader=True,
  aggregateLocal=[32,48],keySourceRange=[0,8],valueSourceRange=[8,12],transportedUnusedPaddingRange=[12,16],
  keyOutput='unchanged incoming R9',valueOutput='unchanged incoming stack argument5',
  individualKeyOrValueFormatterInvoked=False,keyAndValueFormatterArgumentsUnused=True,
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True)


def raw_pair(regions,entry,o):
 b=lambda k:bytes((o[k],)).hex();g=BytesPath(regions,entry)
 g.take('48895c2408','57','4883ec20','8379'+b('bufferLength')+'10','488bfa','488bd9');g.branch('7d',True,1)
 g.take('488b41'+b('currentPtr'),'0f1000','ba10000000','488bcb','0f1107','488b5c2430','4883c420','5f');target=g.relative('e9')
 return dict(selectedBytes=g.seen,wireBytes=16,outputBytes=16,reader='incoming RCX',output='incoming RDX',
  advanceTargetVa=target,signedAdvanceCount=16,allAggregateBitsPreserved=True,paddingBytesCopied=True,
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturnViaOwnedAdvance=True,refillAdmitted=False)


def add(regions,entry):
 g=BytesPath(regions,entry);g.take('48895c2408','48896c2410','4889742418','57','4883ec30','498b4120','498bd9','418bf8','488bf2','488be9',
  '4c8b88c0000000','498b81c0000000','4883782000');g.branch('0f84',False)
 g.take('488b4320','41b102','448bc7','488bd6','488b88c0000000','488b81c0000000','488bcd','4889442420');target=g.relative('e8')
 g.take('488b5c2440','488b6c2448','488b742450','4883c430','5f','c3')
 return dict(selectedBytes=g.seen,insertTargetVa=target,insertContextSlot=24,keyBits=64,valueBits=32,
  unchangedKeyRdx=True,unchangedValueR8d=True,unchangedDictionaryRcx=True,insertBehaviorLiteral=2,
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,hashMapOrDuplicateSemanticsProved=False)

"""Exact static Reader/out-reference source for the finite gait/Single map.

This is SerializeFieldDictionary.DeserializeV2, with its own object header and
signed count. It is neither a Reader.ReadValue result nor a normal Dictionary
collection header. Child callback framing and runtime helper selection remain
independent of the literal source program below.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='skillGaitDictionaryProgram'


def need(key,condition):
 if not condition:raise ValueError(LABEL+'.'+key)


def program(regions,entry,offsets,symbols,*,count):
 need('bounded-literal-count',type(count)is int and -1<=count<=3)
 keys=('currentPtr','bufferLength','advancedCount','consumed')
 need('four-owned-reader-offsets',set(offsets)>=set(keys)and
  len({offsets[k]for k in keys})==4 and all(type(offsets[k])is int and 0<=offsets[k]<128 for k in keys))
 o={k:bytes((offsets[k],)).hex()for k in keys};s=symbols
 g=BytesPath(regions,entry)
 g.take('4053','56','57','4157','4883ec58','803d');flag=g.at+5+int.from_bytes(g.read(4),'little',signed=True);g.take('00')
 g.take('498bf8','488bf2','488bd9');g.branch('0f84',False)
 g.take('4533ff','c684248000000000','488d942480000000','44897c2420','488bcb','44897c2424');g.call(s['header'])
 g.take('80bc2480000000ff');g.branch('0f84',count==-1)
 provider=None;keys_read=[];values_read=[];stores=[];backedges=[]
 if count==-1:
  g.take('488bce','4c893e');g.call(s['barrier']);g.take('90');g.jump('e9')
 else:
  g.take('4889ac2488000000','4c89642450','4c896c2448','4c89742440','0f29742430','4c393e');g.branch('75',False,1)
  g.take('488b4f20');g.call(s['context']);g.take('ba15000000','488b88c0000000');g.call(s['type'])
  g.take('488bc8');g.call(s['allocate']);g.take('488be8','4885c0');g.branch('0f84',False)
  g.take('488b4f20');g.call(s['context']);g.take('488b88c0000000','488b91b0000000','4c397a20');g.branch('0f84',False)
  g.take('488b4f20');g.call(s['context']);g.take('488bcd','488b90c0000000','488b92b0000000');g.call(s['constructor'])
  g.take('488bce','48892e');g.call(s['barrier']);provider=g.relative('488b0d')
  g.take('4439b9e0000000');g.branch('0f84',False)
  g.take('488b4f20');g.call(s['context']);g.take('488b88c0000000','488b89b8000000');g.call(s['keyProvider'])
  g.take('488b4f20','4c8be0');g.call(s['context']);g.take('488b88c0000000','488b89c0000000');g.call(s['valueProvider'])
  g.take('837b'+o['bufferLength']+'04','4c8be8');g.branch('0f8c',False)
  g.take('488b43'+o['currentPtr'],'448b30','8b6b'+o['bufferLength'],'83c5fc');g.branch('0f88',False)
  for code,key in(('488343','currentPtr'),('8343','advancedCount'),('8343','consumed')):g.take(code+o[key]+'04')
  g.take('896b'+o['bufferLength'],'418bef','4585f6');g.branch('0f8e',count==0)
  for index in range(count):
   g.take('44897c2420','4d85e4');g.branch('0f84',False)
   g.take('4c8d4c2420','4c8bc3','498bd4');keys_read.append(g.at);g.call(s['keyDispatch'])
   g.take('c744242400000000','4d85ed');g.branch('0f84',False)
   g.take('4c8d4c2424','4c8bc3','498bd5');values_read.append(g.at);g.call(s['valueDispatch'])
   g.take('4c8b3e','8b442420','f30f10742424','89842480000000','4d85ff');g.branch('74',False,1)
   g.take('488b4f20');g.call(s['context']);g.take('488b88c0000000','488b4128','4883782000');g.branch('0f84',False)
   g.take('488b4f20');g.call(s['context']);g.take('8b942480000000','0f28d6','498bcf','4c8b88c0000000','4d8b4928')
   stores.append(g.at);g.call(s['setItem'])
   g.take('ffc5','41bf00000000','413bee');backedges.append(g.at);g.branch('0f8c',index+1<count)
  g.take('4c8b742440','4c8b6c2448','4c8b642450','488bac2488000000','0f28742430')
 g.take('4883c458','415f','5f','5e','5b','c3')
 return dict(selectedBytes=g.seen,countWitness=count,newDictionary=True,metadataReadyFlag=flag,
  headerPredicate='FF'if count==-1 else'non-FF',nativeRequiresHeaderOne=False,
  initiallyNullOutputRequired=count!=-1,providerClassCell=provider,
  keyCallbackSites=keys_read,valueCallbackSites=values_read,elementCallbackSites=keys_read,
  setItemCallSites=stores,backedgeSites=backedges,duplicateKeyBehavior='actual owned set_Item call; callback/helper effects separately required',
  readerRegister='incoming RCX',outputRegister='incoming RDX',methodInfoRegister='incoming R8',
  outputAbi='void-byref-reference8',keyOutputBytes=4,valueOutputBytes=4,
  countBytes=0 if count==-1 else 4,normalReturn=True,entryRspRestored=True,
  allWin64IntegerNonvolatilesRestored=True,wholeXmm6Restored=count!=-1,
  frame=dict(entryRspDelta=-120,callShadow=[0,32],keyLocal=[32,36],valueLocal=[36,40],
   savedXmm6=[48,64],savedIntegerHomes=dict(r14=[64,72],r13=[72,80],r12=[80,88],rbp=[136,144]),
   pushedNonvolatiles=['rbx','rsi','rdi','r15'],headerThenKeyHome=[128,132]),
  wireGrammarAdmitted=False,condition='Initialized exact selected class/method contexts, provider state and ready helper methods; sufficient buffered input and nonwrapping counters, initially null out-reference for non-FF, disjoint storage and normal Win64 helper/callback returns. Exact nominal key and Single callbacks, actual helper context compatibility, provider choice and parent field transfer remain independent.')

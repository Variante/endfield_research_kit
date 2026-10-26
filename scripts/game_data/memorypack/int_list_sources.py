"""Selected initialized Int32 list programs; caller owns native/type/source gates."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def source(regions,entry,offsets,symbols,*,count=1,new=False,grow=False,null=False):
 if type(count) is not int or not 0<=count<=3:raise ValueError('intList.witness-count')
 g=BytesPath(regions,entry);g.take('48895c2420','56','4154','4155','4156','4157','4883ec50','4533f6','4d8be9','837a'+bytes((offsets['bufferLength'],4)).hex(),'4d8bf8','4c8be2','4489b42488000000');g.branch('7d',True,1)
 cur,rem,adv,used=(bytes((offsets[n],)).hex() for n in ('currentPtr','bufferLength','advancedCount','consumed'))
 total=bytes((offsets['totalLength'],)).hex()
 g.take('498b4424'+cur,'8b30','89742430','418b5c24'+rem,'83c3fc');g.branch('79',True,1)
 g.take('49834424'+cur+'04','41834424'+adv+'04','41834424'+used+'04','41895c24'+rem,'49634424'+used,'498b4c24'+total,'482bc8','4863c6','483bc8');g.branch('0f8c',False)
 g.take('83feff','4889ac2480000000','0f95c0','84c0');g.branch('0f84',null)
 if null:
  collector=g.relative('443935');g.take('4d8937');g.branch('74',True,1)
 else:
  g.take('4889bc2490000000');base=g.relative('488d2d');g.take('498b4520','488b88c0000000','4d3937');g.branch('74',new,1)
  if new:
   g.take('488b01','f6803801000001');g.branch('75',True,1);g.take('488bc8');g.call(symbols['allocate']);g.take('488bd8','4885c0');g.branch('0f84',False)
   g.take('498b4d20','488b91c0000000','488b4a08','4c397120');g.branch('75',True,1);g.take('498b4520','488b88c0000000','488b7908','85f6');g.branch('0f88',False);g.take('488b4720','488b80c0000000');g.branch('74',count==0,1)
   if count:
    g.take('488b4008','f6803801000001');g.branch('75',True,1);g.take('488bd6','488bc8');g.call(symbols['arrayAllocate']);collector=g.relative('443935');g.take('48894310');g.branch('0f84',True)
   else:
    g.take('488b00','f6803801000001');g.branch('75',True,1);g.take('4439b0e0000000');g.branch('75',True,1);g.take('488b4720','488b88c0000000','488b01','f6803801000001');g.branch('75',True,1);collector=g.relative('443935');g.take('488b80b8000000','488b08','48894b10');g.branch('74',True,1)
   same=g.relative('443935')
   if same!=collector:raise ValueError('intList.collector-identity')
   g.take('49891f');g.branch('74',True,1)
  else:
   g.take('488b4110','498b1f','4c397020');g.branch('75',True,1);g.take('ff431c','44897318');g.jump('e9')
  provider_class=g.relative('488b0d');g.take('4439b1e0000000');g.branch('75',True,1);g.take('498b4520');g.relative('488d3d');g.take('488b88c0000000','488b7118','4889742438','4c397638');g.branch('0f85',True)
  type_class=g.relative('488b0d');g.take('488b5e38','488b1b','4439b1e0000000');g.branch('75',True,1);g.take('33d2','488bcb');g.call(symbols['typeFromHandle']);same_provider=g.relative('488b0d');g.take('488bf0','4439b1e0000000');g.branch('75',True,1);flag=g.relative('443835');g.branch('0f85',True)
  last_provider=g.relative('488b0d');g.take('4439b1e0000000');g.branch('75',True,1);g.take('488bce');g.call(symbols['backend']);g.take('488b742438','4c8bf0','488b4e38','488b4108','f6803801000001');g.branch('75',True,1);g.take('4d85f6');g.branch('0f84',False);g.take('498b0e','488bd0');g.call(symbols['assignable']);g.take('84c0');g.branch('0f84',False);g.take('33f6','39742430');g.branch('0f8e',count==0)
  if provider_class!=same_provider or same_provider!=last_provider:raise ValueError('intList.provider-class')
  if count:g.take('0f1f00')
  for i in range(count):
   g.take('4c8d8c2488000000','c784248800000000000000','4d8bc4','498bd6');g.call(symbols['dispatcher']);g.take('498b1f','8bac2488000000','4885db');g.branch('0f84',False);g.take('498b4520','488b88c0000000','488b4130','4883782000');g.branch('75',True,1)
   g.take('498b4520','488b5310','488b88c0000000','488b7930','ff431c','48634b18','4885d2');g.branch('0f84',False);g.take('3b4a18');g.branch('0f82',not grow)
   if grow:
    g.take('488b4720','4c8b80c0000000','498b4058','4883782000');g.branch('75',True,1);g.take('488b4720','8bd5','488bcb','4c8b80c0000000','4d8b4058');g.call(symbols['grow']);g.jump('e9')
   else:g.take('8d4101','894318','3b4a18');g.branch('0f83',False);g.take('896c8a20')
   g.take('ffc6','3b742430');g.branch('0f8c',i+1<count)
  g.take('488bbc2490000000')
 g.take('488bac2480000000','488b9c2498000000','4883c450','415f','415e','415d','415c','5e','c3')
 return dict(selectedBytes=g.seen,count=None if null else count,newList=new,growthSelected=grow,headerWireBytes=4,elementWireBytes=4,collectorZeroCondition=collector if null or new else None,provider=None if null else dict(classCell=provider_class,typeClassCell=type_class,readyFlag=flag),normalReturn=True)


def integer(regions,entry,offsets):
 g=BytesPath(regions,entry);cur,rem,adv,used=(bytes((offsets[n],)).hex() for n in ('currentPtr','bufferLength','advancedCount','consumed'))
 g.take('48895c2408','57','4883ec20','837a'+rem+'04','498bf8','488bda');g.branch('0f8c',False);g.take('488b42'+cur,'8b00','8907','8b7b'+rem,'83c7fc');g.branch('0f88',False);g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','897b'+rem,'488b5c2430','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,wireBytes=4,preservedBits=32,reader='incoming RDX',output='incoming R8')


def dispatcher(regions,entry,offsets,*,prepare,callback):
 g=BytesPath(regions,entry);cur,rem,adv,used=(bytes((offsets[n],)).hex() for n in ('currentPtr','bufferLength','advancedCount','consumed'))
 g.take('48895c2408','4889742410','57','4883ec20','488b0a','498bf1','498bd8','488bfa');g.call(prepare);g.take('488b07','4c8b9090010000','4c8b8898010000')
 if g.relative('488d05')!=callback:raise ValueError('intList.dispatch-selected-callback')
 g.take('4c3bd0');g.branch('75',False,1);g.take('837b'+rem+'04');g.branch('0f8c',False);g.take('488b43'+cur,'8b00','8906','8b7b'+rem,'83c7fc');g.branch('0f88',False);g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','897b'+rem,'488b5c2430','488b742438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,slot=5,callback=callback,wireBytes=4,output='incoming R9',reader='incoming R8',preservedBits=32,normalReturn=True,condition='Ready receiver with slot-five callback equal to the independently proved Int32 formatter; stable disjoint valid buffered Reader/output storage; ordinary preparation ABI.')


def clear(regions,entry):
 g=BytesPath(regions,entry);g.take('ff411c','c7411800000000','c3');return dict(selectedBytes=g.seen,countSlot=24,versionSlot=28,keepsItems=True,normalReturn=True)


def add(regions,entry,*,grow=False,growth):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','ff411c','498bf8','4c8b5110','8bf2','4c634918','488bd9','4d85d2');g.branch('75',True,1);g.take('453b4a18');g.branch('72',not grow,1)
 if grow:
  g.take('498b4020','488b88c0000000','488b4158','4883782000');g.branch('75',True,1);g.take('488b4720','8bd6','488bcb','4c8b80c0000000','4d8b4058');g.call(growth);g.jump('eb',1)
 else:
  g.take('418d4101','894118','453b4a18');g.branch('72',True,1);g.take('4389748a20')
 g.take('488b5c2430','488b742438','4883c420','5f','c3');return dict(selectedBytes=g.seen,elementBits=32,arrayStride=4,countSlot=24,versionSlot=28,growthMethodContextSlot=11,growthSelected=grow,normalReturn=True)


def growth(regions,entry,calls,*,empty=False):
 g=BytesPath(regions,entry);g.take('89542410','53','55','56','57','4155','4883ec40','498b4020','498bd8','4c636918','8bea','488bf9','4c8b88c0000000','498b4160','4883782000');g.branch('75',True,1)
 g.take('488b4320','418d5d01','4c89a42480000000','4c89742438','4c897c2430','488b88c0000000','488b4710','488b7160','4885c0');g.branch('0f84',False);g.take('395818');g.branch('0f8d',False);g.take('4883781800','41bf04000000');g.branch('75',not empty,1)
 if empty:g.take('418bc7');g.jump('eb',1)
 else:g.take('8b4018','03c0','b9ffffef7f','3bc1','0f47c1')
 g.take('3bc3','0f4dd8','488b4620','488b88c0000000','488b81c0000000','4883782000');g.branch('75',True,1);g.take('488b4620','488b88c0000000','488bb1c0000000','3b5f18');g.branch('0f8c',False);g.take('488b4710','4885c0');g.branch('0f84',False);g.take('3b5818');g.branch('0f84',False);g.take('488b4e20','85db');g.branch('7f',True,1)
 g.take('488b89c0000000','41be01000000','418bd6');g.call(calls['resolveClass']);g.take('488bc8','448be3','488be8');g.call(calls['arrayClassReady']);g.take('81fbffffff7f');g.branch('0f87',False);g.take('8bb500010000','8bc3');bitmap=g.relative('488d1d');g.take('480faff0','4883c620','f6853801000020');g.branch('75',False,1);g.take('488bd5','488bce');g.call(calls['allocateRawArray']);g.take('4c8d46f0','33d2','488bd8','488d4810','48c7401000000000');g.call(calls['zeroMemory']);g.jump('e9');same_bitmap=g.relative('488d35')
 if bitmap!=same_bitmap:raise ValueError('intList.growth-bitmap')
 instrumentation=g.relative('f605');g.take('80','4c896318');g.branch('74',True,1);g.take('837f1800');g.branch('7e',empty,1)
 if not empty:g.take('8b4718','4533c9','488b4f10','4c8bc3','48c744242800000000','33d2','89442420');g.call(calls['arrayCopy'])
 collector=g.relative('833d');g.take('00','48895f10');g.branch('74',True,1);g.take('8b6c2478','488b4f10','418d4501','894718','4885c9');g.branch('74',False,1);g.take('443b6918');g.branch('73',False,1);g.take('4c8b7c2430','4c8b742438','4c8ba42480000000','42896ca920','4883c440','415d','5f','5e','5d','5b','c3')
 return dict(selectedBytes=g.seen,normalReturn=True,emptyOldArray=empty,preservedElementBits=32,oldCountAlias='r13',itemAlias='saved incoming EDX reloaded EBP',publishedItemsSlot=16,publishedCountSlot=24,storeStride=4,collectorZeroCondition=collector,instrumentationZeroCondition=instrumentation,condition='Ready closed Int32 List contexts; coherent nonnegative old count/array length requiring growth, normal typed class resolution and nonthrowing allocation/copy/zero helpers, reference-free array class allocation branch, disabled instrumentation/collector, allocation class/length/size effects remain conditional.')


def initialized_class(regions,entry,*,indexed=False):
 g=BytesPath(regions,entry)
 if indexed:g.take('488bc1','4863ca','488b0cc8');g.jump('e9')
 g.take('f6813801000001');g.branch('74',False,1);g.take('488bc1');g.jump('eb',1);g.take('c3')
 return dict(selectedBytes=g.seen,normalReturn=True,result='incoming RCX context[incoming EDX]' if indexed else 'incoming RCX',condition='Incoming index nonnegative/in-range and selected class initialized flag bit one set; readable stable context/class storage.')


def capacity(regions,entry,calls,*,positive=True):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','8bda','498bf8','488bf1','85d2');g.branch('0f88',False);g.take('498b4820','488b89c0000000');g.branch('75',positive,1)
 if positive:g.take('ba01000000');g.call(calls['resolveClass']);g.take('488bd3','488bc8');g.call(calls['arrayAllocate']);g.jump('eb',1)
 else:
  g.take('33d2');g.call(calls['resolveClass']);g.take('83b8e000000000');g.branch('74',False,1);g.take('488b4f20','33d2','488b89c0000000');g.call(calls['resolveClass']);g.take('488b88b8000000','488b01')
 g.take('488d4e10','48894610','488b5c2430','488b742438','4883c420','5f')
 if g.relative('e9')!=calls['barrier']:raise ValueError('intList.capacity-barrier')
 return dict(selectedBytes=g.seen,normalReturnViaBarrier=True,positiveCapacity=positive,arrayContextSlot=1,positiveCapacityUnchanged=True,itemsSlot=16,countWrites=0,versionWrites=0,condition='Nonnegative capacity, normal initialized class resolver results and typed array allocation; zero-capacity List class ready with static empty array. Allocation effects and initial List count remain conditional.')


def copy_array(regions,entry,*,fast):
 g=BytesPath(regions,entry);g.take('48895c2410','4889742418','57','4154','4155','4156','4157','4883ec70','458bf9','498bd8','448bf2','488bf9','c744246000000000','4885c9');g.branch('0f84',False);g.take('4885db');g.branch('0f84',False);g.take('8bb424c0000000','85f6');g.branch('0f88',False);g.take('488b11','498b00','0fb68834010000','388a34010000');g.branch('0f85',False);g.take('4585f6');g.branch('0f88',False);g.take('4585c9');g.branch('0f88',False);g.take('89742420','418bd6','488bcf');g.call(fast);g.take('84c0');g.branch('74',False,1);g.take('4c8d5c2470','498b5b38','498b7340','498be3','415f','415e','415d','415c','5f','c3')
 return dict(selectedBytes=g.seen,normalReturn=True,source='incoming RCX',sourceIndex='incoming EDX',destination='incoming R8',destinationIndex='incoming R9D',count='incoming stack fifth argument',condition='Nonnull same-rank arrays and nonnegative indices/count; fast helper returns true.')


def fast_copy(regions,entry,*,move):
 g=BytesPath(regions,entry);g.take('48895c2410','44894c2420','4c89442418','48894c2408','55','56','57','4154','4155','4156','4157','4883ec30','4d8be8','4c63fa','4c8b19','498b00','440fb69034010000','45389334010000');g.branch('0f85',False);g.take('4883791000');g.branch('0f85',False);g.take('4983781000');g.branch('0f85',False);g.take('4c63a42490000000','438d0421','413b4018');g.branch('0f87',False);g.take('438d0427','3b4118');g.branch('0f87',False);g.take('498b7340','498b00','488b5840');object_class=g.relative('483b35');g.branch('0f85',True);g.take('483bf3');g.branch('0f84',True)
 g.take('498b4500','48639800010000','4c8bc3','4d0fafc4','488bc3','490fafc7','488b542470','4883c220','4803d0','488bcb','4863b42488000000','480fafce','4883c120','4903cd');g.call(move);collector=g.relative('833d');g.take('00');g.branch('74',True,1);g.take('b001');g.jump('eb',1);g.take('488b5c2478','4883c430','415f','415e','415d','415c','5f','5e','5d','c3')
 return dict(selectedBytes=g.seen,normalReturnTrue=True,elementSizeSlot=256,dataOffset=32,copyBytes='destination element size * incoming count',source='incoming source +32+elementSize*sourceIndex',destination='incoming destination +32+elementSize*destinationIndex',collectorZeroCondition=collector,excludedObjectClassCell=object_class,condition='Same ordinary SZARRAY shape and identical primitive element class, signed in-range nonnegative indices/count without addition overflow, element size four, collector disabled, move helper has normal memmove effects.')


def factory_pair(regions,entry,*,type_handle,add):
 g=BytesPath(regions,entry);key=g.relative('488b0d');g.take('33d2');g.call(type_handle);value=g.relative('488b0d');g.take('33d2','488bd8');g.call(type_handle);method=g.relative('4c8b0d');g.take('4c8bc0','488bd3','488bcf');g.call(add)
 return dict(selectedBytes=g.seen,keyTypeCell=key,valueTypeCell=value,addMethodInfoCell=method)


def backend(regions,entry,calls):
 g=BytesPath(regions,entry);g.take('4889542410','55','57','4883ec48');initialized=g.relative('803d')+1;g.take('00','488bf9');g.branch('75',True,1);provider=g.relative('488b05');g.take('48c744246800000000','83b8e000000000');g.branch('75',True,1);g.take('488b80b8000000','488b6818','4885ed');g.branch('0f84',False);g.take('48895c2470');method=g.relative('488b1d');g.take('4885ff');g.branch('0f84',False);g.take('4889742478','4c896c2440','4c89742438','4c897c2430','488b7518','4885f6');g.branch('0f84',False);g.take('488b4b20','ba0c000000','488b89c0000000');g.call(calls['resolveClass']);g.take('488bd0','b901000000','4c8bcf','4c8bc6');g.call(calls['hash']);g.take('488b4b20','448bf8','488b91c0000000','488b8ae8000000','4883792000');g.branch('75',True,1);g.take('488b4b20','488b5d10','488b91c0000000','4c8baae8000000','f0830c2400','4885db');g.branch('0f84',False);g.take('488b7310','4885f6');g.branch('0f84',False);g.take('498b4d20','ba02000000','488b89c0000000');g.call(calls['resolveClass']);g.take('83b8e000000000');g.branch('75',True,1);g.take('488b5b10','4885db');g.branch('0f84',False);g.take('418bc7','0fbaf01f','99','f77e18','3b5318');g.branch('0f83',False);g.take('4863c2','488b5cc320','f0830c2400','4885db');g.branch('74',False,1);g.take('660f1f440000','443b7b28');g.branch('75',False,1);g.take('488b7518','4c8b7310','4885f6');g.branch('0f84',False);g.take('498b4d20','ba0c000000','488b89c0000000');g.call(calls['resolveClass']);g.take('488bd0','48897c2420','33c9','4d8bce','4c8bc6');g.call(calls['equals']);g.take('84c0');g.branch('0f85',True);collector=g.relative('833d');g.take('00','488b4318','4889442468');g.branch('0f84',True);g.take('488b442468','4c8b742438','4c8b6c2440','4c8b7c2430','488b742478','488b5c2470','4883c448','5f','5d','c3')
 return dict(selectedBytes=g.seen,providerClassCell=provider,methodInfoCell=method,readyFlag=initialized,collectorZeroCondition=collector,normalReturn=True,result='unchanged successful first-bucket matching node value',key='unchanged incoming RCX Type in RDI',condition='Initialized provider/static formatter dictionary and typed ConcurrentDictionary contexts, coherent nonempty positive-sized first bucket with matching hash and equality success, normal comparer/class helper ABI, disabled collector. Runtime cache contents/default selection are not observed.')


def factory_receiver(rows):
 from scripts.game_data.il2cpp.body_claims import _writes_register
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 if not rows or rows[0]['text']!='mov rdi, rax' or rows[-1]['text']!='mov [rcx+0x8], rdi':raise ValueError('intList.factory-receiver-endpoints')
 if any(r['text'].startswith('db ') or _writes_register(r,'rdi') for r in rows[1:]):raise ValueError('intList.factory-receiver-overwritten')
 branches=[i for i,r in enumerate(rows) if control_transfer(r)['kind'] not in ('next','call')]
 if branches!=[2] or rows[1]['text']!='test rax, rax' or control_transfer(rows[2]).get('conditionCode')!=4:raise ValueError('intList.factory-nonnull-allocation-guard')
 if any(r['text'].partition(' ')[0] not in ('mov','call','test','jcc','je','cmp','lea','add','xor','nop') for r in rows[1:]):raise ValueError('intList.factory-unreviewed-receiver-operation')
 return dict(receiver='same fresh RDI dictionary through CollectionFormatters static store',condition='Nonnull fresh allocation and ordinary Win64 callees preserving RDI; runtime dictionary mutation/contents are not observed.')

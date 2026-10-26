"""Selected current pooled interactive source; children remain independently gated."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def element_program(regions,entry,s,fields,*,null=False,new=False):
 g=BytesPath(regions,entry);g.take('48895c2410','48896c2418','4889742420','57','4883ec30');g.relative('803d');g.take('00','488bf2','488bf9');g.branch('0f84',False);g.take('488b2e','4885ed');g.branch('74',new,1)
 if not new:g.relative('803d');g.take('00');g.branch('0f84',False);g.take('48837d1800');g.branch('0f84',False)
 g.take('837f3001');g.branch('0f8c',False);g.take('488b4750','0fb628','8b5f30','83eb01');g.branch('0f88',False);g.take('48ff4750','ff4740','ff4744','895f30','4080fdff');g.branch('0f84',null);usages=[];out=[]
 slot=lambda name:next(f['field'][2]for f in fields if f['name']==name)
 b=lambda v:bytes((v,)).hex()
 def base_guard(reg='c9'):
  g.take('4885db');g.branch('0f84',False);g.take('488b4b10'if reg=='c9'else'488b4310','4885'+reg);g.branch('0f84',False)
 def scalar(name,kind,*,ready=False):
  if not ready:g.take('488bcf')
  g.take('488b1e');site=g.at;g.call(s[kind]);base_guard();g.take(('8841'if kind=='bool'else'488941')+b(slot(name)))
  if kind=='pool':g.take('4883c1'+b(slot(name)));g.call(s['barrier'])
  out.append(dict(field=name,sourceCall=site,sourceKind=kind,wireBytes=1 if kind=='bool'else 4 if kind=='pool'else 8))
 def inline(name,*,vector=False,last=False):
  width=12 if vector else 4;g.take('837f30'+b(width),'488b1e');g.branch('0f8c',False);g.take('488b4750')
  if vector:g.take('f20f1030','448b7008')
  else:g.take('448b30')
  g.take('8b6f30','83c5'+b(256-width));g.branch('0f88',False);g.take('48834750'+b(width),'834740'+b(width),'834744'+b(width),'896f30');base_guard('c0')
  if vector:
   g.take('f20f1170'+b(slot(name)))
   if last:g.take('488bcf')
   g.take('448970'+b(slot(name)+8))
  else:g.take('448970'+b(slot(name)))
  out.append(dict(field=name,sourceKind='rawVector3'if vector else'rawDword',wireBytes=width))
 def own_guard(*,floating=False,final=False):
  if final:
   g.take('4885f6');g.branch('74',False,1);g.relative('803d');g.take('00');g.branch('0f84',False);g.take('48837e1800');g.branch('0f84',False);g.take('488b4610','48394618');g.branch('0f85',False);g.take('488b4e18','4885c9');g.branch('74',False,1)
  else:
   g.take('4885ed');g.branch('0f84',False);g.relative('803d');g.take('00');g.branch('0f84',False);g.take('48837d1800');g.branch('0f84',False);g.take('488b4510','48394518');g.branch('0f85',False);g.take('488b4518'if floating else'488b4d18','4885c0'if floating else'4885c9');g.branch('0f84',False)
 def reference(name,order,*,preloaded=False,final=False):
  if not preloaded and order=='reader-first':g.take('488bcf')
  usage=g.at;cell=g.relative('488b15')
  if not preloaded and order=='context-first':g.take('488bcf')
  if not preloaded:g.take('488b36'if final else'488b2e')
  site=g.at;kind='condition'if name=='progressLockCondition'else'packable';g.call(s[kind]);g.take('488bf8'if final else'4c8bf0');own_guard(final=final);offset=slot(name)
  if final:g.take('4889b9'+offset.to_bytes(4,'little').hex(),'4883e980')
  elif offset<128:g.take('4c8971'+b(offset),'4883c1'+b(offset))
  else:g.take('4c89b1'+offset.to_bytes(4,'little').hex(),'4881c1'+offset.to_bytes(4,'little').hex())
  g.call(s['barrier']);usages.append(dict(field=name,instruction=usage,cell=cell,call=site,kind=kind));out.append(dict(field=name,sourceKind=kind,wireBytes=None))
 if null:
  g.take('488bce','48c70600000000');g.call(s['barrier']);g.jump('eb',1)
 else:
  g.take('4c89742440','0f29742420','48833e00');g.branch('0f84',new)
  if new:
   allocation=g.at;g.relative('488b0d');g.call(s['allocate']);g.take('488bd8','4885c0');g.branch('0f84',False);g.take('33d2','488bc8');g.call(s['constructor']);g.take('488bce','48891e');g.call(s['barrier']);g.take('90');g.jump('e9')
  g.take('4080fd19');g.branch('0f85',False);inline('aoiRadiusType');scalar('belongLevelScriptId','qword');inline('createState');scalar('dependencyGroupId','qword');scalar('entityDataIdKey','pool');inline('entityType');scalar('forceLoad','bool');scalar('keepCrossMap','bool');scalar('levelLogicId','qword');scalar('overrideSendDieEvent','bool');inline('position',vector=True);inline('rotation',vector=True);inline('scale',vector=True,last=True);scalar('sendDieEvent','bool',ready=True)
  reference('componentProperties','reader-first');reference('globalIntKeyList','context-first');reference('globalProperties','context-first')
  for n,name in enumerate(('hideInDialog','isClientOnly','isLocked')):
   g.take(*(('488b2e','488bcf')if n==0 else('488bcf','488b2e')));site=g.at;g.call(s['bool']);g.take('440fb6f0');own_guard(floating=True);g.take('448870'+b(slot(name)));out.append(dict(field=name,sourceCall=site,sourceKind='bool',wireBytes=1))
  reference('mapIntKeyList','reader-first');reference('mapProperties','context-first');g.take('488b2e','488bcf');site=g.at;g.call(s['float']);g.take('0f28f0');own_guard(floating=True);g.take('488b2e','488bcf','f30f1170'+b(slot('modelScale')));out.append(dict(field='modelScale',sourceCall=site,sourceKind='float',wireBytes=4));reference('progressLockCondition','context-first',preloaded=True);reference('properties','context-first',final=True);g.take('4c8b742440','0f28742420')
 g.take('488b5c2448','488b6c2450','488b742458','4883c430','5f','c3')
 return dict(selectedBytes=g.seen,null=null,newWrapper=new,fields=out,typedUsages=usages,memberCount=25,wrapperBaseHolder=16,wrapperCacheHolder=24,normalReturn=True,boundary='Complete selected buffered source with initialized coherent wrapper/cache. Actual read/store widths and metadata-owned destinations; child grammar/factory/typed contexts/normal helper effects and collector barriers independent. No current admission until those joins pass.')


def parent_program(regions,entry,packable,offset):
 g=BytesPath(regions,entry);cell=g.relative('488b15');g.take('498bcd','498b1f');site=g.at;g.call(packable);g.take('4885db');g.branch('0f84',False);g.take('4c8b4310','4d85c0');g.branch('0f84',False);flag=g.relative('833d');g.take('00','498980'+offset.to_bytes(4,'little').hex());g.branch('74',True,1)
 return dict(selectedBytes=g.seen,readCall=site,typeUsageCell=cell,fieldOffset=offset,collectorZeroFlag=flag,sameRaxReferenceStored=True,readerAlias='r13',wrapperOutputAlias='r15',wrapperOriginalSlot=16,boundary='Selected single parent read?metadata-owned store through original root holder, collector disabled. Complete-root prior alias preservation/order and independently typed ReadPackable/source/factory remain owning gates.')


def dictionary_u32_program(regions,entry,s,*,count=-1,new=True):
 if type(count)is not int or count not in(-1,0,1):raise ValueError('interactive.dictionary-witness-count')
 g=BytesPath(regions,entry);g.take('488bc4','53','55','56','57','4154','4883ec50','4c8be2','33ed','488bf1','8968a8','498bcc','896810','488d50a8','488968b0','498bd9','498bf8');g.call(s['header']);g.take('84c0');g.branch('0f84',count==-1)
 if count==-1:g.take('488bcf','48892f');g.call(s['barrier']);g.take('90');g.jump('e9')
 else:
  g.take('4c89b42490000000','4c89ac2480000000','4c89bc2498000000','448b742420','48392f');g.branch('0f85',not new)
  if new:
   g.take('488b4b20','ba03000000','4c8b7e10','488b89c0000000');g.call(s['context']);g.take('488bc8');g.call(s['allocate']);g.take('488bf0','4885c0');g.branch('0f84',False);g.take('488b4b20','488b91c0000000','488b4a20','48396920');g.branch('0f84',False);g.take('488b4320','4d8bc7','418bd6','488bce','4c8b88c0000000','4d8b4920');g.call(s['constructor']);g.take('488bcf','488937');g.call(s['barrier'])
  else:
   g.take('488b4320','488b37','488b90c0000000','488b4228','48396820');g.branch('75',True,1);g.take('488b4320','488bce','488b90c0000000','488b5228');g.call(s['clear']);g.take('90');g.jump('e9')
  provider=g.relative('488b0d');g.take('39a9e0000000');g.branch('0f84',False);g.take('488b4320','488b88c0000000','488b4930');g.call(s['keyProvider']);g.take('488b4b20','488bf0','488b89c0000000','488b4938');g.call(s['valueProvider']);g.take('4c8bf8','4585f6');g.branch('7f',count>0,1)
  for i in range(count):
   g.take('488b4b20','488b91c0000000','488b4a40','4883793800');g.branch('0f84',False);g.take('0f57c0','0f11442438','33c0','89842488000000','4889442428','4885f6');g.branch('0f84',False);g.take('4c8d8c2488000000','4d8bc4','488bd6');g.call(s['keyDispatcher']);g.take('4d85ff');g.branch('74',False,1);g.take('b905000000','4c8d4c2428','4d8bc4','498bd7');g.call(s['referenceDispatcher']);g.take('8b842488000000','4c8b2f','89442420','488b442428','4889442430','4d85ed');g.branch('74',False,1);g.take('488b4320','488b88c0000000','488b4148','4883782000');g.branch('0f84',False);g.take('488b4320','498bcd','4c8b442430','8b542420','4c8b88c0000000','4d8b4948');g.call(s['add']);g.take('ffc5','413bee');g.branch('0f8c',False);g.jump('e9')
  g.take('4c8bac2480000000','4c8bbc2498000000','4c8bb42490000000')
 g.take('4883c450','415c','5f','5e','5d','5b','c3')
 return dict(selectedBytes=g.seen,count=count,newDictionary=new,wireCountBytes=4,keyWireBytes=4,valueBytes=8,keyPreservedBits=32,contextSlots=dict(dictionaryClass=3,constructor=4,clear=5,keyProvider=6,valueProvider=7,keyValuePair=8,add=9),sameIncomingReader=True,normalReturn=True,boundary='Conditional supplied owned K/V contexts and actual providers/callbacks, initialized contexts, ordinary constructor/Clear/Add/allocation/barrier effects. No live closed factory/default selection or positive child grammar follows.')


def dictionary_header_program(regions,entry,offsets):
 g=BytesPath(regions,entry);b=lambda v:bytes((v,)).hex();cur,rem,adv,used,total=(b(offsets[n])for n in('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
 g.take('48895c2408','4889742410','57','4883ec20','8379'+rem+'04','488bfa','488bd9');g.branch('0f8c',False);g.take('488b43'+cur,'8b08','890f','8b73'+rem,'83c6fc');g.branch('0f88',False);g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','8973'+rem,'486343'+used,'488b4b'+total,'448b07','482bc8','4963c0','483bc8');g.branch('0f8c',False);g.take('488b5c2430','4183f8ff','488b742438','0f95c0','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,countWireBytes=4,nullCount=-1,result='AL true iff count differs from -1; signed count checked against remaining total bytes; incoming RDX output stores same Int32',normalReturn=True)


def u32_dispatch_program(regions,entry,s,offsets):
 g=BytesPath(regions,entry);b=lambda v:bytes((v,)).hex();g.take('48895c2408','4889742410','57','4883ec20','488b0a','498bf9','498bd8','488bf2');g.call(s['prepare']);g.take('488b06','4c8b9090010000','4c8b8898010000')
 if g.relative('488d05')!=s['callback']:raise ValueError('Interactive.uint-dispatch-callback')
 g.take('4c3bd0');g.branch('0f85',False);g.take('837b'+b(offsets['bufferLength'])+'04');g.branch('0f8c',False);g.take('488b43'+b(offsets['currentPtr']),'8b00','ba04000000','488bcb','8907');g.call(s['advance']);g.take('488b5c2430','488b742438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,callback=s['callback'],interfaceSlot=5,reader='incoming R8',output='incoming R9',wireBytes=4,preservedBits=32,normalReturn=True,boundary='Ready receiver slot5 equal to independently proved current UnmanagedFormatter<uint>; ordinary preparation and full Advance helper normal effects.')


def unmanaged_u32_program(regions,entry,s,offsets):
 g=BytesPath(regions,entry);b=lambda v:bytes((v,)).hex();g.take('48895c2408','57','4883ec20','837a'+b(offsets['bufferLength'])+'04','498bf8','488bda');g.branch('0f8c',False);g.take('488b42'+b(offsets['currentPtr']),'8b00','ba04000000','488bcb','8907','488b5c2430','4883c420','5f');
 if g.relative('e9')!=s['advance']:raise ValueError('Interactive.uint-advance-tail')
 return dict(selectedBytes=g.seen,wireBytes=4,preservedBits=32,reader='incoming RDX',output='incoming R8',normalAdvanceTail=True)


def key_provider_program(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20','4883793800','488bf9');g.branch('74',False,1);typeclass=g.relative('488b0d');g.take('488b5f38','83b9e000000000','488b1b');g.branch('0f84',False);g.take('33d2','488bcb');g.call(s['typeHandle']);provider=g.relative('488b0d');g.take('488bd8','83b9e000000000');g.branch('74',False,1);g.take('488bcb');g.call(s['keyBackend']);g.take('488b4f38','ba01000000','488bd8');g.call(s['context']);g.take('488bd0','488bcb');g.call(s['cast']);g.take('4885c0');g.branch('0f84',False);g.take('488b5c2438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,methodContextSlot=0,returnFormatterSlot=1,typeClassCell=typeclass,providerClassCell=provider,normalReturn=True,boundary='Initialized GetFormatter own method context slot0 key and slot1 cast; actual backend normal return cast to owned MemoryPackFormatter<T>. Backend cache/default selection remain separately conditional.')


def dictionary_capacity_program(regions,entry,s,*,positive=True,same_comparer=False):
 g=BytesPath(regions,entry);g.take('48895c2408','48896c2410','4889742418','57','4883ec20','498be9','498bf8','8bf2','488bd9','85d2');g.branch('0f88',False);g.take('85d2');g.branch('7f',positive,1)
 if positive:g.take('498b4120','488b88c0000000','488b4108','4883782000');g.branch('0f84',False);g.take('488b4520','8bd6','488bcb','4c8b80c0000000','4d8b4008');g.call(s['initialize']);g.jump('eb',1)
 g.take('488b4520','488b88c0000000','488b4910');g.call(s['comparer']);g.take('483bf8');g.branch('74',same_comparer,1)
 if not same_comparer:g.take('488d4b30','48897b30');g.call(s['barrier'])
 g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,capacity='incoming signed nonnegative EDX forwarded unchanged to Initialize when positive',comparer='incoming R8 preserved and conditionally stored field48',normalReturn=True,boundary='Owned Dictionary context and normal Initialize/default comparer/helper effects independent; no runtime comparer identity claim.')


def dictionary_add_program(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2408','48896c2410','4889742418','57','4883ec30','498b4120','498bd9','498bf8','8bf2','488be9','4c8b88c0000000','498b81c0000000','4883782000');g.branch('0f84',False);g.take('488b4320','41b102','4c8bc7','8bd6','488b88c0000000','488b81c0000000','488bcd','4889442420');g.call(s['tryInsert']);g.take('488b5c2440','488b6c2448','488b742450','4883c430','5f','c3')
 return dict(selectedBytes=g.seen,key='incoming EDX bits preserved32',value='incoming R8 unchanged reference',receiver='incoming RCX',methodContextSlot=24,behavior=2,normalReturn=True,boundary='Exact Add->TryInsert argument transfer, normal TryInsert effects and valid owned Dictionary context remain conditional.')


def getter_coherent_program(regions,entry):
 g=BytesPath(regions,entry);g.take('4053','4883ec20');g.relative('803d');g.take('00','488bd9');g.branch('74',False,1);g.take('48837b1800');g.branch('0f84',False);g.take('488b4310','48394318');g.branch('0f85',False);g.take('488b4318','4883c420','5b','c3')
 return dict(selectedBytes=g.seen,originalHolder=16,cachedHolder=24,outputBytes=8,result='unchanged nonnull cached reference equal to inherited original holder',normalReturn=True,boundary='Explicit initialized coherent wrapper/cache fast path; constructor/CreateInstance and slow cache refresh/typed cast are independent obligations.')



def wrapper_constructor_program(regions,entry,s,*,default_comparer_null=True):
 g=BytesPath(regions,entry);g.take('4053','4883ec30');g.relative('803d');g.take('00','488bd9');g.branch('0f84',False);provider=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False);g.relative('803d');g.take('00');g.branch('0f84',False);base_alloc=g.at;base_type=g.relative('488b0d');g.take('48896c2440','4889742448','48897c2450','0f29742420');g.call(s['allocate']);g.take('4885c0');g.branch('0f84',False);default=g.relative('f30f1035');g.take('0f28c6','488d4b10','0f14c6','f20f114054','f30f11705c','48894310');g.call(s['barrier']);own_alloc=g.at;own_type=g.relative('488b0d');g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('0f84',False);g.take('c740740000803f');list_alloc=g.at;list_type=g.relative('488b0d');g.call(s['allocate']);g.take('488bf0','4885c0');g.branch('0f84',False);list_context=g.at;g.relative('488b2d');g.take('33d2','488b4d20','488b89c0000000');g.call(s['context']);g.take('83b8e000000000');g.branch('0f84',False);g.take('488b4d20','33d2','488b89c0000000');g.call(s['context']);g.take('488b88b8000000','488b01','488d4e10','48894610');g.call(s['barrier']);g.take('488d8f80000000','4889b780000000');g.call(s['barrier']);dictionary_alloc=g.at;dictionary_type=g.relative('488b0d');g.call(s['allocate']);g.take('488bf0','4885c0');g.branch('0f84',False);dictionary_context=g.at;g.relative('488b2d');g.take('488b4d20','488b91c0000000','488b0a','4883792000');g.branch('0f84',False);g.take('488b4520','488b88c0000000','488b01','488b4820','488b89c0000000','488b4910');g.call(s['dictDefaultComparer']);g.take('4533c9','4885c0');g.branch('74',default_comparer_null,1)
 if not default_comparer_null:g.take('488d4e30','4c894e30');g.call(s['barrier'])
 g.take('488d8fa8000000','4889b7a8000000');g.call(s['barrier']);g.take('0f28c6','488d4b18','0f14c6','f20f114754','f30f11775c','48897b18');g.call(s['barrier']);g.take('488d4b10','48897b10');g.call(s['barrier']);g.take('488b7b10');first_cast=g.at;first_type=g.relative('488b35');g.take('4885ff');g.branch('74',False,1);g.take('488b0f','488bd6');g.call(s['assignable']);g.take('84c0');g.branch('74',False,1);g.take('48897b18');second_cast=g.at;second_type=g.relative('488b35');g.take('488b0f','488bd6');g.call(s['assignable']);g.take('84c0');g.branch('74',False,1);g.take('488d4b18','0f28742420','488b7c2450','488b742448','488b6c2440','4883c430','5b')
 if g.relative('e9')!=s['barrier']:raise ValueError('Interactive.constructor-barrier-tail')
 if own_type!=first_type or own_type!=second_type:raise ValueError('Interactive.constructor-own-cast-type')
 return dict(selectedBytes=g.seen,allocations=[dict(role=role,instruction=site,cell=cell)for role,site,cell in(('base',base_alloc,base_type),('original',own_alloc,own_type),('defaultProperties',list_alloc,list_type),('defaultComponents',dictionary_alloc,dictionary_type))],methodContexts=[list_context,dictionary_context],sameOriginalStoredToBaseAndCache=True,originalHolder=16,cachedHolder=24,normalReturn=True,boundary='Exact initialized selected constructor, nonnull typed allocations and compatible typed-original assignability. Default nested allocations/context/comparer and normal helper/barrier effects are conditional; serialized25 fields overwrite defaults, so no default wire semantics follow.')


def wrapper_create_program(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');g.relative('803d');g.take('00','488bf9');g.branch('75',True,1);allocation=g.at;cell=g.relative('488b0d');g.call(s['allocate']);g.take('488bd8','4885c0');g.branch('75',True,1);g.take('33d2','488bcb');g.call(s['originalConstructor']);g.take('4533c0','488bd3','488bcf');g.call(s['baseSetter']);g.take('488b5f10');first=g.relative('488b15');g.take('488bcb');g.call(s['checkedCast']);g.take('48894718','488bcb');second=g.relative('488b15');g.call(s['checkedCast']);g.take('488d4f18','488b5c2430','4883c420','5f')
 if g.relative('e9')!=s['barrier']or cell!=first or cell!=second:raise ValueError('Interactive.create-owned-cast-tail')
 return dict(selectedBytes=g.seen,allocationInstruction=allocation,originalTypeCell=cell,originalHolder=16,cachedHolder=24,normalReturn=True,boundary='Exact typed-original allocation, current original constructor/base setter and two checked casts. Normal allocation/constructor/setter/cast/barrier effects and compatible selected original type are explicit; no runtime activation or factory default selection claim.')



def key_backend_forward_program(regions,entry,backend):
 g=BytesPath(regions,entry);g.take('4053','4883ec20');g.relative('803d');g.take('00','488bd9');g.branch('74',False,1);provider=g.relative('488b0d');g.take('83b9e000000000');g.branch('74',False,1);g.take('488bcb','4883c420','5b')
 if g.relative('e9')!=backend:raise ValueError('Interactive.key-backend-tail')
 return dict(selectedBytes=g.seen,providerClassCell=provider,sameIncomingTypeKey=True,tail=backend,normalReturn=True,boundary='Initialized provider forwarding wrapper; selected shared backend source and typed cache context remain independently gated.')


def collector_disabled_program(regions,entry):
 g=BytesPath(regions,entry);flag=g.relative('833d');g.take('00','4c8bc1');g.branch('74',True,1);g.take('c3')
 return dict(selectedBytes=g.seen,collectorZeroFlag=flag,preservesRegistersExcept=['r8'],unchangedReturnRegister=True,normalReturn=True,boundary='Actual collector-disabled barrier fast return only, source prefix contains complete selected return; no enabled-collector semantics or full physical-function extent claim.')


def base_setter_program(regions,entry,barrier):
 g=BytesPath(regions,entry);g.take('4883ec28','4c8bd1','48895118','4883c118','4c8bca');g.call(barrier);g.take('498d4a10','4d894a10','4883c428')
 if g.relative('e9')!=barrier:raise ValueError('Interactive.base-setter-tail')
 return dict(selectedBytes=g.seen,originalHolder=16,cachedHolder=24,sameIncomingReferenceStoredTwice=True,normalReturn=True,boundary='Current owning wrapper fields at16/24, actual collector-disabled barrier proves R9/R10 preservation; no arbitrary helper purity assumption.')



def dictionary_i32_program(regions,entry,s,offsets,*,count=2,new=True):
 if type(count)is not int or count not in(-1,0,1,2):raise ValueError('interactive.enum-dictionary-witness-count')
 g=BytesPath(regions,entry);b=lambda v:bytes((v,)).hex();cur,rem,adv,used,total=(b(offsets[n])for n in('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
 g.take('4c89442418','53','55','56','57','4154','4155','4157','4883ec60','4533ff','498bf1','837a'+rem+'04','4d8be0','488bda','4c897c2440','488be9','4489bc24a8000000','4c897c2438');g.branch('0f8c',False);g.take('488b43'+cur,'4c6328','44896c2430','8b7b'+rem,'83c7fc');g.branch('0f88',False);g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','897b'+rem,'486343'+used,'488b4b'+total,'482bc8','493bcd');g.branch('0f8c',False);g.take('4183fdff');g.branch('0f84',count==-1)
 if count==-1:
  g.take('498bcc','4d893c24');g.call(s['barrier'])
 else:
  g.take('4c89b424a0000000','4d393c24');g.branch('0f85',not new)
  if new:
   g.take('488b4e20','ba03000000','488b6d10','488b89c0000000');g.call(s['context']);g.take('488bc8');g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('0f84',False);g.take('488b4e20','488b91c0000000','488b4a20','4c397920');g.branch('0f84',False);g.take('488b4620','488b88c0000000','4c8b7120','4585ed');g.branch('0f88',False);g.branch('0f8f',count>0)
   if count:
    g.take('498b4620','488b88c0000000','488b4108','4c397820');g.branch('0f84',False);g.take('498b4620','418bd5','488bcf','4c8b80c0000000','4d8b4008');g.call(s['initialize']);g.jump('e9')
   g.take('498b4620','488b88c0000000','488b4910');g.call(s['enumDefaultComparer']);g.take('483be8');g.branch('74',False,1);g.take('488d4f30','48896f30');g.call(s['barrier']);g.take('498bcc','49893c24');g.call(s['barrier'])
  else:
   g.take('488b4620','498b3c24','488b90c0000000','488b4228','4c397820');g.branch('75',True,1);g.take('488b4620','488bcf','488b90c0000000','488b5228');g.call(s['clear']);g.take('90');g.jump('e9')
  provider=g.relative('488b0d');g.take('4439b9e0000000');g.branch('0f84',False);g.take('488b4620','488b88c0000000','488b4930');g.call(s['enumKeyProvider']);g.take('488b4e20','4c8bf0','488b89c0000000','488b4938');g.call(s['valueProvider']);g.take('4c8be8','44397c2430');g.branch('0f8e',count==0)
  if count:
   if g.relative('488d3d')!=s['intCallback']:raise ValueError('Interactive.enum-key-callback')
   secondary=g.relative('488d2d');g.take('660f1f840000000000')
  for i in range(max(count,0)):
   g.take('488b4620','488b88c0000000','488b4940','4883793800');g.branch('0f84',False);g.take('0f57c0','0f11442448','33c0','898424a8000000','4889442438','4d85f6');g.branch('0f84',False);g.take('498b0e');g.call(s['prepare']);g.take('498b06','4c8b9090010000','4c8b8898010000','4c3bd7');g.branch('0f85',False);g.take('837b'+rem+'04');g.branch('0f8c',False);g.take('488b43'+cur,'8b00','898424a8000000','8b7b'+rem,'83c7fc');g.branch('0f88',False);g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','897b'+rem,'4d85ed');g.branch('0f84',False);g.take('b905000000','4c8d4c2438','4c8bc3','498bd5');g.call(s['referenceDispatcher']);g.take('498b2c24','448bbc24a8000000','4c8b642438','4885ed');g.branch('0f84',False);g.take('488b4620','488b88c0000000','488b4148','4883782000');g.branch('0f84',False);g.take('488b4620','488b88c0000000','488b7948','488b4720','488b88c0000000','488b81c0000000','4883782000');g.branch('0f84',False);g.take('488b4720','4d8bc4','418bd7','488bcd','4c8b88c0000000','498b81c0000000','41b102','4889442420');g.call(s['enumTryInsert']);g.take('4c8b7c2440')
   if g.relative('488d3d')!=s['intCallback']:raise ValueError('Interactive.enum-key-repeat-callback')
   g.take('4c8ba424b0000000')
   if g.relative('488d2d')!=secondary:raise ValueError('Interactive.enum-key-repeat-secondary')
   g.take('41ffc7','4c897c2440','443b7c2430');g.branch('0f8c',i+1<count)
  g.take('4c8bb424a0000000')
 g.take('4883c460','415f','415d','415c','5f','5e','5d','5b','c3')
 return dict(selectedBytes=g.seen,count=count,newDictionary=new,keyWireBytes=4,valueBytes=8,inlineAddBehavior=2,keyCallback=None if count<1 else s['intCallback'],normalReturn=True,boundary='Exact current canonical Int32/reference Dictionary source with selected initialized matched32-bit key callback and actual owned typed K/V contexts; independently typed enum32 caller and normal provider/comparer/Initialize/Clear/TryInsert effects required. Positive values use independently gated KV-list grammar. No actual closed runtime inflater/default-selection identity is asserted.')



def dictionary_context(image,context):
 import struct
 from scripts.game_data.il2cpp.context import type_parameter_owner
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols,validate_claims
 md=image.metadata;owner=md.types[context['definition']]
 def need(check,expected,actual):
  if expected!=actual:raise ValueError(f'interactive.dictionary-context.{check}:expected={str(expected)[:250]}:actual={str(actual)[:250]}')
 need('owner',(False,'MemoryPack.Formatters.DictionaryFormatter`2'),(context['isMethod'],context['typeName']));validate_claims(context,ContextSymbols(image).context(owner.index),label='interactive.dictionary-context');section=md.sections['genericContainers'];at=section.offset+owner.generic_container_index*16
 if owner.generic_container_index<0 or not section.offset<=at<=section.offset+section.size-16:raise ValueError('interactive.dictionary-context.container-bounds')
 definition,arity,method,start=struct.unpack_from('<iiii',md.buf,at);need('container',(owner.index,2,0),(definition,arity,method));containers=[t.generic_container_index for t in md.types]
 for ordinal in(0,1):
  identity=type_parameter_owner(md.buf,start+ordinal,containers,source='interactive.dictionary-context');need('reciprocal',(owner.index,ordinal),(identity['typeIndex'],identity['ordinal']))
 rows=context['entries'];need('complete-slots',list(range(10)),[r['relativeSlot']for r in rows])
 def parameter(argument,ordinal):
  raw=bytes.fromhex(argument['rawHex']);need('ordinary-var',(16,b'\x13\x00',start+ordinal),(len(raw),raw[10:12],int.from_bytes(raw[:8],'little')));identity=argument['parameterOwner'];need('owned-var',(owner.index,ordinal),(identity['typeIndex'],identity['ordinal']))
 def pair(arguments):
  need('two-arguments',2,len(arguments))
  for ordinal,arg in enumerate(arguments):parameter(arg,ordinal)
 def method_slot(n,name,method_name,ordinals,*,generic_method=False,static=False,arity=0):
  row=rows[n];need('method-slot',(3,name,method_name),(row['kind'],row['typeName'],row['methodName']));args=row['methodArguments'if generic_method else'classArguments'];need('method-argument-arity',len(ordinals),len(args))
  for arg,ordinal in zip(args,ordinals):parameter(arg,ordinal)
  need('other-instantiation',[],row['classArguments'if generic_method else'methodArguments']);m=md.methods[row['methodSpec'][0]];need('declaration-abi',(static,arity),(bool(m.flags&16),m.parameter_count));return m
 method_slot(0,context['typeName'],'.ctor',[0,1],arity=1);row=rows[1];need('base-ctor',(3,'MemoryPack.MemoryPackFormatter`1','.ctor'),(row['kind'],row['typeName'],row['methodName']));arg,=row['classArguments'];need('base-dictionary',rows[3]['type']['name'],arg['name']);pair(arg['classArguments'])
 need('parent-type',2,rows[2]['kind']);parent,=rows[2]['type']['classArguments'];need('base-parent-definition','MemoryPack.MemoryPackFormatter`1',rows[2]['type']['definition']['name']);pair(parent['classArguments']);need('dictionary-type',(2,'System.Collections.Generic.Dictionary`2'),(rows[3]['kind'],rows[3]['type']['definition']['name']));pair(rows[3]['type']['classArguments'])
 method_slot(4,'System.Collections.Generic.Dictionary`2','.ctor',[0,1],arity=2);method_slot(5,'System.Collections.Generic.Dictionary`2','Clear',[0,1]);method_slot(6,'MemoryPack.MemoryPackFormatterProvider','GetFormatter',[0],generic_method=True,static=True);method_slot(7,'MemoryPack.MemoryPackFormatterProvider','GetFormatter',[1],generic_method=True,static=True);method_slot(8,'MemoryPack.Formatters.KeyValuePairFormatter','Deserialize',[0,1],generic_method=True,static=True,arity=5);method_slot(9,'System.Collections.Generic.Dictionary`2','Add',[0,1],arity=2)
 return dict(ownedClassParameters=2,authenticatedSlots=list(range(10)),keyOrdinal=0,valueOrdinal=1,runtimeInflationObserved=False,boundary='Exact reciprocal DictionaryFormatter K/V identity across Dictionary class, constructor/Clear/providers/KV Deserialize/Add; actual selected source/helper ABI and concrete typed closure are separate.')



def enum_key_provider_program(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20','4883793800','488bf9');g.branch('0f84',False);typeclass=g.relative('488b0d');g.take('488b5f38','83b9e000000000','488b1b');g.branch('0f84',False);g.take('33d2','488bcb');g.call(s['typeHandle']);provider=g.relative('488b0d');g.take('488bd8','83b9e000000000');g.branch('0f84',False);g.take('488bcb');g.call(s['keyBackend']);g.take('488b4f38','ba01000000','488bd8');g.call(s['context']);g.take('4885db');g.branch('74',False,1);g.take('488b0b','488bd0');g.call(s['assignable']);g.take('84c0');g.branch('74',False,1);g.take('488bc3','488b5c2438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,typeClassCell=typeclass,providerClassCell=provider,contextSlots=[0,1],backendResultUnchanged=True,normalReturn=True,boundary='Actual initialized owned GetFormatter<MVAR> current enum-key call profile and nonnull expected formatter assignability; successful Type-key backend/normal helpers and concrete callback correspondence independent, no runtime default selection claim.')


def read_value_reference_program(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48894c2408','53','55','56','57','4154','4155','4156','4157','4883ec68','488bda','488bf9','48837a3800');g.branch('0f84',False);g.take('48c78424c000000000000000');provider=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False);g.take('488b4338','488b28','48837d3800');g.branch('0f84',False);g.take('488b5d38','488b1b');typeclass=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False);g.take('4885db');g.branch('0f84',False);g.take('83b9e000000000');g.branch('0f84',False);g.take('b201','488bcb');g.call(s['classFromType']);g.take('4c8d6020');cache=g.relative('488b1d');g.take('488b8b80000000');enter=g.relative('ff15');g.take('90','488b4340','483b4338');g.branch('0f84',False);g.take('4533ed','4c8b7348','49ffce','498bcc');g.call(s['classHash']);g.take('488bf8','488b7368','448b7b50','4923fe','488d0c7f','443b3cce');g.branch('75',True,1);g.take('48837b3800');g.branch('0f87',False);g.take('488d047f','833cc600');g.branch('0f85',False);g.take('488b54c608','498bcc');g.call(s['classEquals']);g.take('85c0');g.branch('0f85',False);g.take('4883ffff');g.branch('0f84',False);g.take('488d0c7f','488d14ce','488b4348','488d0c40','488b4368','488d0cc8','483bd1');g.branch('0f84',False);g.take('488b4a10','488b4370','4c8b34c8','488b8b80000000');leave=g.relative('ff15');g.take('90','488bbc24b0000000')
 if g.relative('488b0d')!=provider:raise ValueError('Interactive.ReadValue-provider-class')
 g.take('83b9e000000000');g.branch('0f84',False);flag=g.relative('803d');g.take('00');g.branch('0f84',False)
 if g.relative('488b0d')!=provider:raise ValueError('Interactive.ReadValue-provider-class')
 g.take('83b9e000000000');g.branch('0f84',False);g.take('498bce');g.call(s['backend']);g.take('488bd8','ba01000000','488b4d38');g.call(s['context']);g.take('4885db');g.branch('74',False,1);g.take('488bd0','488b0b');g.call(s['assignable']);g.take('84c0');g.branch('74',False,1);g.take('b905000000','4c8d8c24c0000000','4c8bc7','488bd3');g.call(s['referenceDispatcher']);g.take('488b8424c0000000','4883c468','415f','415e','415d','415c','5f','5e','5d','5b','c3')
 return dict(selectedBytes=g.seen,typeClassCell=typeclass,providerClassCell=provider,readyFlag=flag,classKeyCacheCell=cache,enterCell=enter,leaveCell=leave,reader='incoming RCX home slot at entry RSP+8 -> restored RDI before call',output='zeroed local reference at frame RSP+192 then unchanged RAX return',contextSlots=dict(provider=0,expectedFormatter=1),normalReturn=True,boundary='Ready Reader own MVAR and provider context, coherent successful selected first-probe class-key/type-key provider mapping and assignability. Exact unchanged reader/output ABI to ordinary dispatcher; actual callback, wire grammar and all helper/runtime default selection effects remain independently conditional.')



def parent_aliases(image,regions,call):
 from scripts.game_data.il2cpp.integer_effects import decode_locked_memory_exchange
 from scripts.game_data.il2cpp.string_source_instructions import decode_register_immediate_test
 from scripts.game_data.il2cpp.field_setup_instructions import decode_register_bit_test,decode_single_bit_register_shift,decode_register_or,decode_byte_memory_or,decode_locked_memory_add
 from scripts.game_data.il2cpp.sse_lanes import decode_sse_lanes
 from scripts.game_data.il2cpp.generic_creation_instructions import decode_memory_source_xor,decode_implicit_memory_exchange
 from scripts.game_data.il2cpp.integer_addressing import decode_lea_address
 from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
 from scripts.game_data.il2cpp.reference_field_programs import preserved_argument
 class Mapper:
  def decode_one_x64(self,data,offset,start_va):
   for decoder in(decode_locked_memory_exchange,decode_register_immediate_test,decode_register_bit_test,decode_single_bit_register_shift,decode_register_or,decode_byte_memory_or,decode_locked_memory_add,decode_sse_lanes,decode_memory_source_xor,decode_implicit_memory_exchange,decode_lea_address):
    row=decoder(data,offset,start_va)
    if row is not None:return row
   return image.mapper.decode_one_x64(data,offset,start_va)
 rows=decode_type_data_initialization_instructions(Mapper(),regions[0][1],regions[0][0]);at=next(i for i,r in enumerate(rows)if int(r['va'],16)==call);aliases=tuple(preserved_argument(rows[:at],reg)for reg in('rcx','rdx'))
 if aliases!=('r13','r15'):raise ValueError('interactive.parent-preserved-aliases:'+str(aliases))
 return rows[:at]

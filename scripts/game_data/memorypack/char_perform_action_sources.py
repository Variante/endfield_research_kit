"""Current selected AddMultiTags18 and managed32 source transfers; runtime selection stays conditional."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def child_new(regions,entry,fields,s):
 if len(fields)!=18 or fields[0]['name']!='bodyType':raise ValueError('charLoop.field-plan')
 g=BytesPath(regions,entry);g.take('48895c2418','57','4883ec40');g.relative('803d');g.take('00','488bda','488bf9');g.branch('75',True,1);g.take('488b0b','c644245800','4885c9');g.branch('0f85',False);g.take('488d542458','488bcf');g.call(s['header']);g.take('84c0');g.branch('0f84',False);g.take('4889742450','48833b00');g.branch('75',False,1);allocation=g.at;allocationCell=g.relative('488b0d');g.call(s['allocate']);g.take('488bf0','4885c0');g.branch('75',True,1);g.take('33d2','488bce');g.call(s['ctor']);g.take('488bcb','488933');g.call(s['barrier']);g.take('0fb6742458','4080fe12');g.branch('0f85',False)
 result=[]
 # Actual hidden32 result, same Reader and typed R8 context, then complete runtime value copy.
 site=g.at;context=g.relative('4c8b05');g.take('488d4c2420','488b33','488bd7');call=g.at;target=g.relative('e8');g.take('4885f6');g.branch('74',False,1);g.take('488b4e10','4885c9');g.branch('74',False,1);g.take('0f10442420','0f104c2430','0f114150','0f114960','4883c158');g.call(s['barrier']);result.append(dict(name='bodyType',contextSite=site,contextCell=context,sourceCall=call,sourceTarget=target,output='hidden32 stack+32/+48 complete copy to same base original+80, nested reference barrier at+88'))
 for i,f in enumerate(fields[1:],1):
  contexts=[];kind=f['kind'];last=i==17
  if kind in('list','object'):
   site=g.at;cell=g.relative('488b15');contexts.append(dict(site=site,cell=cell));g.take('488bcf','488b33')
  elif last:g.take('488b1b','488bcf')
  else:g.take('488b33','488bcf')
  call=g.at;target=g.relative('e8');g.take('4885db'if last else'4885f6');g.branch('0f84'if last or i>=2 else'74',False,4 if last or i>=2 else 1);g.take('4533c0')
  if kind=='float32':g.take('0f28c8')
  elif kind=='bool':g.take('0fb6d0')
  elif kind in('scalar32','enum'):g.take('8bd0')
  elif kind in('string','list','object'):g.take('488bd0')
  else:raise ValueError('charLoop.unproved-kind:'+kind)
  g.take('488bcb'if last else'488bce');setterCall=g.at;setter=g.relative('e8');result.append(dict(name=f['name'],sourceCall=call,sourceTarget=target,setterCall=setterCall,setter=setter,contexts=contexts,transfer='same Reader; complete scalar/reference result reaches same wrapper named setter with R8D0'))
 g.take('488b742450','488b5c2460','4883c440','5f','c3')
 return dict(selectedBytes=g.seen,fields=result,allocationUsageSite=allocation,allocationClassCell=allocationCell,memberCount=18,sameReader=True,sameOutput=True,normalReturn=True,condition='Initialized generated reader, initially null output, normal typed wrapper allocation+constructor and barriers preserving Win64 ABI, nonnull wrapper/original, buffered header MC18 and compatible normal children/setters. Runtime constructor/storage/provider effects and child wire grammar remain separate; all18 explicit assignments overwrite constructor defaults.')


def body_reader(regions,entry,s,*,new=False):
 g=BytesPath(regions,entry);g.take('48895c2418','57','4883ec20');g.relative('803d');g.take('00','488bda','488bf9');g.branch('0f84',False);g.take('488d542430','c644243000','488bcf');g.call(s['header']);g.take('84c0');g.branch('0f84',False);g.take('4889742438','48833b00');g.branch('0f84',new);allocation=None
 if new:
  site=g.at;cell=g.relative('488b0d');allocation=dict(site=site,cell=cell);g.call(s['allocate']);g.take('4885c0');g.branch('0f84',False);g.take('0f57c0','488bcb','0f114010','0f114020','488903');g.call(s['barrier']);g.take('90');g.jump('e9')
 g.take('0fb6742430','4080fe03');g.branch('0f85',False);site=g.at;cell=g.relative('488b15');g.take('488bcf','488b33');bytecall=g.at;g.call(s['byte']);g.take('4885f6');g.branch('74',False,1);g.take('884610','488bcf','488b33');intcall=g.at;g.call(s['integer']);g.take('4885f6');g.branch('74',False,1);g.take('894620','488bcf','488b1b');stringcall=g.at;g.call(s['string']);g.take('4885db');g.branch('74',False,1);g.take('488d4b18','48894318');g.call(s['barrier']);g.take('488b742438','488b5c2440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,newWrapper=new,allocation=allocation,byteContextSite=site,byteContextCell=cell,sourceCalls=dict(bodyType=bytecall,CustomId=intcall,CustomName=stringcall),serializedFields=['bodyType','CustomId','CustomName'],runtimeValueBytes=32,wireMemberCount=3,explicitlyWrittenRuntimeOffsets=[0,16,8],mDisplayNameOffset=24,mDisplayNameWire=False,normalReturn=True,condition='Initialized metadata, MC3, normal actual header/byte/Int32/pooled-string helpers and barrier, same disjoint valid Reader/ref-holder/stack; existing holder contains coherent BodyTypeDef32 or successful typed allocation zeroes its32bytes as proved. Runtime lookup/allocation effects conditional; live selection and enclosing managed32 return route remain separate.')

def read_value32(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','4983783800','498bf8','488bf2','488bd9');g.branch('74',False,1);g.take('0f57c0','0f1103','0f114310');cell=g.relative('488b0d');g.take('83b9e000000000');g.branch('74',False,1);g.take('488b4f38','488b09');g.call(s['provider']);g.take('4885c0');g.branch('74',False,1);g.take('4c8bcb','4c8bc6','488bd0');g.call(s['dispatch']);g.take('488bc3','488b5c2430','488b742438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,providerClassCell=cell,zeroedRuntimeOutputBytes=32,reader='same incoming RDX preserved RSI and forwarded R8',output='same incoming RCX preserved RBX then forwarded R9, returned unchanged RAX',methodContext='same incoming R8 preserved RDI; exact rgctx+56 slot0 provider MethodInfo passed RCX',normalReturn=True,condition='Initialized closed ReadValue context, ready provider class and nonnull matching formatter result, ordinary compatible helper/callback returns preserving frame/nonvolatile registers with disjoint stable storage. No live/default selection or helper/storage side-effect claim; child grammar/callback separately proved.')


def flag(g):g.relative('803d');g.take('00')

def adapter(regions,entry,s,*,dispatch=False):
 g=BytesPath(regions,entry)
 if dispatch:
  g.take('48895c2408','48896c2410','4889742418','57','4883ec20','488b0a','498be9','498bf0','488bda');g.call(s['prepare']);g.take('488b3b')
  if g.relative('488d0d')!=s['main']:raise ValueError('body32.matched-main')
  g.take('488b8790010000','488bbf98010000','483bc1');g.branch('0f85',False);flag(g);g.branch('0f84',False)
 else:
  g.take('48896c2410','4889742418','57','4883ec20');flag(g);g.take('498bf9','498be8','488bf2');g.branch('0f84',False)
 g.take('488b4720','488bce','488b90c0000000','488b12');g.call(s['readNull']);g.take('84c0');g.branch('0f85',False)
 if not dispatch:g.take('48895c2430')
 g.take('488b4720');g.relative('488b0d');g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('74',False,1);g.take('33d2','488bcb');g.call(s['typeHandle'])
 if not dispatch:g.take('488b5c2430')
 g.take('4885c0');g.branch('74',False,1);g.take('33d2','488bc8');g.call(s['isValue']);g.take('84c0');g.branch('75',False,1);g.take('488b4720','488b88c0000000','488b4958');g.call(s['factory']);g.take('488b4f20','4c8bc0','488bd5','4c8b89c0000000','488bce','4d8b4918');g.call(s['notNull'])
 if dispatch:g.take('488b5c2430')
 g.take('488b6c2438','488b742440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,matchedCanonicalPointer=dispatch,reader='incoming Reader preserved RSI',output='same32-byte output preserved RBP; no guessed wire width',wrapper='Activator owned VAR1 result RAX passed R8 unchanged',notNullContextSlot=3,normalReturn=True,condition='Initialized metadata/readyType class, positive independently proved ReadIsNull, coherent concrete reference wrapper Type and ordinary TypeHandle/IsValueType=false/Activator results; disjoint storage and ABI-preserving normal calls. Live type/provider selection and helper/runtime effects remain conditional.')

def not_null(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','4c89442418','57','4883ec40');flag(g);g.take('498bf9','488bf2','488bd9');g.branch('0f84',False);provider=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False);g.take('488b4f20');g.call(s['context']);g.take('488b88c0000000','488b4920');g.call(s['hotProvider']);g.take('4885c0');g.branch('0f84',False);g.take('b905000000','4c8d4c2460','4c8bc3','488bd0');g.call(s['wrapperDispatch']);g.take('488b5c2460','4885db');g.branch('0f84',False);g.take('488b4f20');g.call(s['context']);g.take('ba08000000','488b88c0000000');g.call(s['indexed']);g.take('4c8bc0','488d4c2420','33d2','4c8bcb');g.call(s['conversion']);g.take('488d4e08','0f1000','0f104810','0f1106','0f114e10');g.call(s['barrier']);g.take('488b5c2450','488b742458','4883c440','5f','c3')
 return dict(selectedBytes=g.seen,providerClassCell=provider,reader='incoming RCX preserved RBX to wrapper slot5 R8',output='incoming RDX preserved RSI; complete two16-byte copies from conversion returned RAX',wrapper='incoming R8 saved entry RSP+24; same pointer slot/new callback result through frame RSP+96',conversion='hidden32 output RCX frame+32, selector RDX0, interface R8, wrapper R9',normalReturn=True,condition='Initialized coherent inflated context, matching compatible nonnull wrapper formatter and selected slot5 normal callback returning nonnull wrapper; conversion normal returns its complete32-byte hidden output; disjoint stable storage/normal barrier. Live/default provider selection and helper/storage effects conditional.')

def conversion(regions,entry,prepare,*,ordinal):
 if type(ordinal)is not int or not 0<=ordinal<=12:raise ValueError('body32.interface-ordinal')
 g=BytesPath(regions,entry);g.take('48895c2408','48896c2410','4889742418','48897c2420','4156','4883ec40','498b39','488bf1','488bcf','0fb7ea','4d8bf1','498bd8');g.call(prepare);g.take('440fb78730010000','33c0','66413bc0');g.branch('73',False,1);g.take('488b97b0000000')
 for i in range(ordinal+1):
  g.take('0fb7c8','4803c9','48391cca');g.branch('74',i==ordinal,1)
  if i<ordinal:g.take('66ffc0','66413bc0');g.branch('72',True,1)
 g.take('0fb7d0','488b87b0000000','4803d2','8b44d008','03c5','4898','4883c014','48c1e004','4803c7','4c8b08','488d4c2420','4c8b4008','498bd6','41ffd1','488b5c2450','488b6c2458','488b7c2468','0f1000','0f104810','488bc6','0f1106','0f114e10','488b742460','4883c440','415e','c3')
 return dict(selectedBytes=g.seen,interfaceOrdinal=ordinal,selector='incoming DX (selected0)',getterArguments=dict(rcx='hidden32 stack+32',rdx='same wrapper incoming R9 preserved R14',r8='selected interface slot MethodInfo'),output='same incoming RCX preserved RSI;32bytes copied from getter returned RAX; returned unchanged RAX',normalReturn=True,condition='Valid ready current wrapper class/interface offset and matching complete typed getter at selected slot, selector0, coherent inflated interface, disjoint frame/output and normal ABI helpers. Actual class/interface/vtable binding separate; no live runtime selection.')

def value_leaf(regions,entry,*,getter=False):
 g=BytesPath(regions,entry)
 if getter:g.take('0f104210','488bc1','0f104a20','0f1101','0f114910','c3')
 else:g.take('0f57c0','0f114110','0f114120','c3')
 return dict(selectedBytes=g.seen,bytes=32,normalReturn=True,output='same hidden RCX returned RAX after full value load from receiver RDX+16/+32'if getter else'zero32 at same receiver RCX+16/+32',condition='Declared reference wrapper and managed32 field, valid disjoint receiver/output storage and ordinary Win64 hidden-result ABI; source identity/context joins separate.')


def typed_provider(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20','4883793800','488bf9');g.branch('74',False,1);typeClass=g.relative('488b0d');g.take('488b5f38','83b9e000000000','488b1b');g.branch('0f84',False);g.take('33d2','488bcb');g.call(s['typeHandle']);providerClass=g.relative('488b0d');g.take('488bd8','83b9e000000000');g.branch('74',False,1);g.take('488bcb');g.call(s['backend']);g.take('488b4f38','ba01000000','488bd8');g.call(s['indexed']);g.take('488bd0','488bcb');g.call(s['cast']);g.take('4885c0');g.branch('0f84',False);g.take('488b5c2438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,typeClassCell=typeClass,providerClassCell=providerClass,methodContext='incoming RCX preserved RDI; same instantiated method context slot0(T) to TypeFromHandle and slot1(MemoryPackFormatter<T>) to cast',backendArgument='unchanged RuntimeType from selected T passed RCX',output='normal compatible cast RAX of unchanged backend returned formatter; complete reference return',normalReturn=True,condition='Initialized own method context and ready selected Type/provider classes; TypeFromHandle and indexed context resolve coherent T/formatter<T>; matching compatible nonnull backend result and successful cast, normal helpers with disjoint stable storage. Backend/runtime lookup/default/provider selection and helper side effects remain conditional; no wire/data consumption is inferred from this alone.')


def wrapper_ctor(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');g.relative('803d');g.take('00','488bf9');g.branch('75',True,1);baseCell=g.relative('488b0d');g.take('83b9e000000000');g.branch('75',True,1);allocation=g.at;cell=g.relative('488b0d');g.call(s['allocate']);g.take('488bd8','4885c0');g.branch('75',True,1);g.take('33d2','488bcb');g.call(s['originalConstructor']);g.take('4533c0','488bd3','488bcf');g.call(s['baseSetter']);g.take('488b5f10');first=g.relative('488b15');g.take('488bcb');g.call(s['checkedCast']);g.take('48894718','488bcb');second=g.relative('488b15');g.call(s['checkedCast']);g.take('488d4f18','488b5c2430','4883c420','5f')
 if g.relative('e9')!=s['barrier'] or cell!=first or cell!=second:raise ValueError('action.ctor-owned-cast-tail')
 return dict(selectedBytes=g.seen,baseReadyClassCell=baseCell,allocationInstruction=allocation,originalTypeCell=cell,originalHolder=16,cachedHolder=24,normalReturn=True,boundary='Initialized wrapper/base class, nonnull typed original allocation and current original constructor; exact dual-holder store and compatible casts, disabled collector. Allocator/constructor/runtime effects and default selection remain conditional.')


def reference_setter(regions,entry,getter,barrier,slot):
 if type(slot)is not int or not 0<slot<2**31:raise ValueError('action.setter-slot')
 g=BytesPath(regions,entry);g.take('4053','4883ec20','488bda','33d2');g.call(getter);g.take('4885c0');g.branch('75',True,1)
 if slot<128:g.take('488d48'+bytes((slot,)).hex(),'488958'+bytes((slot,)).hex())
 else:g.take('488d88'+slot.to_bytes(4,'little').hex(),'488998'+slot.to_bytes(4,'little').hex())
 g.take('4883c420','5b')
 if g.relative('e9')!=barrier:raise ValueError('action.setter-barrier-tail')
 return dict(selectedBytes=g.seen,slot=slot,storedBytes=8,unchangedIncomingReference=True,normalReturn=True,boundary='Owning typed accessor returns compatible nonnull original, fresh source proves initialized coherent cache; disabled barrier preserves normal return.')


def inherited_setter(regions,entry,slot,kind,barrier):
 if type(slot)is not int or not 0<slot<124 or kind not in('bool','float32','scalar32','string','object'):raise ValueError('action.base-setter-scope')
 h=bytes((slot,)).hex();g=BytesPath(regions,entry);g.take('4883ec28','488b4910'if kind=='string'else'488b4110')
 if kind=='object':g.take('4889542430')
 g.take('4885c9'if kind=='string'else'4885c0');g.branch('74',False,1)
 if kind=='string':
  g.take('488951'+h,'4883c1'+h,'4883c428')
  if g.relative('e9')!=barrier:raise ValueError('action.base-reference-barrier')
 elif kind=='object':g.take('f30f10442430','f30f104c2434','f30f1140'+h,'f30f1148'+bytes((slot+4,)).hex(),'4883c428','c3')
 else:g.take(('8850'if kind=='bool'else'f30f1148'if kind=='float32'else'8950')+h,'4883c428','c3')
 return dict(selectedBytes=g.seen,holder=16,slot=slot,kind=kind,storedBytes=8 if kind in('string','object')else 1 if kind=='bool'else 4,normalReturn=True,boundary='Exact incoming typed value bits into owning inherited original field; nonnull holder coherent with newly constructed derived original, disabled collector for reference tail. Object mode is independently typed Vector2 two-Single transfer.')


def union_new(regions,entry,s,*,tag,count,table,selected,existing=False):
 if type(tag)is not int or not 0<=tag<count<=128:raise ValueError('action.union-scope')
 g=BytesPath(regions,entry);g.take('48895c2408','4889742418','57','4883ec20');g.relative('803d');g.take('00','498bd8','488bfa');g.branch('0f84',False);g.take('33f6','488d542438','488bcf','6689742438');g.call(s['header']);g.take('84c0');g.branch('0f84',False);g.take('0fb7742438','83fe'+bytes((count-1,)).hex());g.branch('0f87',False);imageBase=g.relative('488d15');g.take('8b8cb2'+(table-imageBase).to_bytes(4,'little').hex(),'4803ca','ffe1')
 # Caller joins the authenticated current UInt32 table entry for this exact bounded tag.
 g.at=selected;g.take('488b0b','4885c9');g.branch('0f84',not existing)
 classUsage=None
 if existing:
  at=g.at;classCell=g.relative('488b15');classUsage=dict(instruction=at,cell=classCell);g.take('488b09');g.call(s['assignable']);g.take('84c0');g.branch('0f84',True)
 site=g.at;cell=g.relative('488b15');g.take('488bcf');g.call(s['packable']);g.take('488903','488bcb');g.call(s['barrier']);g.take('488b5c2430','488b742440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,tag=tag,existingBaseWrapper=existing,comparisonTypeUsage=classUsage,entryCount=count,table=table,imageBase=imageBase,childContext=dict(instruction=site,cell=cell),sameReader='incoming RDX savedRDI passed unchanged RCX to short-header and child ReadPackable',sameOutput='incoming R8 savedRBX, initial null or incompatible freshly allocated BaseW branches to fresh concrete wrapper read; returnedRAX stored full8 to same output',normalReturn=True,condition='Initialized union, short header returns selected tag, output initially null or coherent initialized BaseW incompatible with derived ChildW; current authenticated table entry, normal typed concrete-wrapper callback and disabled barrier; all other positive tags refused by consumer profile.')

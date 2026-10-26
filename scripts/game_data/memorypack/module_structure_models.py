"""Selected current module wire source models; runtime/context conditions stay explicit."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def flag(g, prefix='803d'):
    raw = g.read(7)
    if raw[:2] != bytes.fromhex(prefix) or raw[-1] != 0:
        raise ValueError('moduleReferenceList.flag-width-or-value')
    return g.at + int.from_bytes(raw[2:6], 'little', signed=True)

def rolling_holder(regions,entry,*,cast,barrier,cached=False,same=False):
 if same and not cached:raise ValueError('moduleGetter.same-requires-cache')
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');raw=g.read(7)
 if raw[:2]!=b'\x80\x3d' or raw[-1]!=0:raise ValueError('moduleGetter.flag')
 g.take('488bf9');g.branch('75',True,1);g.take('48837f1800');g.branch('74',not cached,1);usage=[]
 if cached:
  g.take('488b4710','48394718');g.branch('74',same,1)
 if not same:
  g.take('488b5f10');site=g.at;cell=g.relative('488b15');usage.append(dict(site=site,cell=cell));g.take('488bcb');g.call(cast);g.take('48894718','488bcb');site=g.at;second=g.relative('488b15');usage.append(dict(site=site,cell=second))
  if cell!=second:raise ValueError('moduleGetter.same-cast-class-cell')
  g.call(cast);g.take('488d4f18');g.call(barrier)
 g.take('488b4718','488b5c2430','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,cached=cached,same=same,classUsages=usage,baseHolderOffset=16,typedHolderOffset=24,returnedReference='typed holder after either equality or compatible cast/cache refresh',condition='Initialized metadata; valid disjoint wrapper/base/typed-reference storage; a compatible current derived original reference, successful normal class predicates/casts and ABI-preserving barrier. Cached-equal path returns the same base reference; refresh stores that compatible reference and returns it. Effective provider selection and puzzle execution remain separate.')


def rolling_owned_prehook(regions,entry,s,*,cached=False,base_null=False):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','33db','488bf9');g.relative('381d');g.branch('75',True,1);g.take('48395f18');g.branch('75',cached,1);usages=[]
 if not cached:
  g.take('48395f10');g.branch('74',base_null,1)
  if not base_null:
   g.take('488b5f10');site=g.at;cell=g.relative('488b15');usages.append(dict(site=site,cell=cell));g.take('488bcb');g.call(s['cast']);g.take('48894718','488bcb');site=g.at;second=g.relative('488b15');usages.append(dict(site=site,cell=second))
   if cell!=second:raise ValueError('moduleHook.same-cast-class')
   g.call(s['cast']);g.take('488d4f18');g.call(s['barrier'])
 g.take('488b5c2430','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,cached=cached,baseNull=base_null,classUsages=usages,serializedFieldWrites=0,condition='Initialized current metadata, coherent readable wrapper/base/cache references, compatible current original when refreshed and normal cast/barrier ABI. This hook only fills an empty typed cache; subsequent owned accessors independently enforce base/cache equality.')

def rolling_owned_factory(regions,entry,s,*,ctor=False):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');flag=g.read(7)
 if flag[:2]!=b'\x80\x3d' or flag[-1]!=0:raise ValueError('moduleFactory.flag')
 g.take('488bf9');g.branch('75',True,1);base_usage=None
 if ctor:site=g.at;cell=g.relative('488b0d');base_usage=dict(site=site,cell=cell);g.call(s['baseReady'])
 site=g.at;cell=g.relative('488b0d');allocation=dict(site=site,cell=cell);g.call(s['allocate']);g.take('488bd8','4885c0');g.branch('75',True,1);g.take('33d2','488bcb');g.call(s['originalCtor']);g.take('4533c0','488bd3','488bcf');g.call(s['instanceSet']);g.take('488b5f10');usages=[]
 site=g.at;cell=g.relative('488b15');usages.append(dict(site=site,cell=cell));g.take('488bcb');g.call(s['strictCast']);g.take('48894718','488bcb');site=g.at;second=g.relative('488b15');usages.append(dict(site=site,cell=second))
 if cell!=second:raise ValueError('moduleFactory.same-cast-class')
 g.call(s['strictCast']);g.take('488d4f18','488b5c2430','4883c420','5f')
 if g.relative('e9')!=s['barrier']:raise ValueError('moduleFactory.barrier')
 return dict(selectedBytes=g.seen,baseClassUsage=base_usage,allocationUsage=allocation,classUsages=usages,baseHolderOffset=16,typedHolderOffset=24,condition='Initialized matching current classes/contexts, successful typed original allocation and normal original constructor return; derived dual-holder setter, compatible casts and normal tail barrier. Original constructor defaults are overwritten by the complete stored-field reader; runtime invocation/default provider is separate.')

def rolling_owned_reference_setter(regions,entry,*,slot,getter,barrier):
 if not 0<=slot<128:raise ValueError('moduleSetter.slot')
 g=BytesPath(regions,entry);g.take('4053','4883ec20','488bda','33d2');g.call(getter);g.take('4885c0');g.branch('75',True,1);g.take('488d48'+bytes((slot,)).hex(),'488958'+bytes((slot,)).hex(),'4883c420','5b')
 if g.relative('e9')!=barrier:raise ValueError('moduleSetter.barrier')
 return dict(selectedBytes=g.seen,storedBytes=8,slot=slot,sameIncomingValueStored=True,condition='Current owned typed accessor returns nonnull compatible original; normal getter/barrier ABI and valid disjoint storage.')

def rolling_owned_strict_cast(regions,entry,assignable):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','488bfa','488bd9','4885c9');g.branch('74',False,1);g.take('488b09');g.call(assignable);g.take('84c0');g.branch('74',False,1);g.take('488bc3','488b5c2430','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,returnedReference='same nonnull incoming object',condition='Incoming object class is compatible with the exact expected current class passed in RDX; normal successful assignability predicate and stable object/class storage. Null/incompatible/error effects separate.')


def module_caller(regions,entry,s,plan,*,rune=False,existing=False,null=False):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742418','57','4883ec20');flag=g.read(7)
 if flag[:2]!=b'\x80\x3d' or flag[-1]!=0:raise ValueError('moduleCaller.flag')
 g.take('488bda','488bf9' if rune else '488bf1');g.branch('75',True,1);g.take('488b0b','c644243800','4885c9');g.branch('74',not existing,1)
 if existing:g.take('33d2');g.call(s['prehook'])
 g.take('488d542438','488bcf' if rune else '488bce');g.call(s['header']);g.take('84c0');g.branch('0f84',null);allocation=None;usages=[]
 if null:g.take('488bcb','48c70300000000');g.call(s['barrier'])
 else:
  g.take('48833b00');g.branch('75',existing,1)
  if not existing:
   site=g.at;cell=g.relative('488b0d');allocation=dict(site=site,cell=cell);g.call(s['allocate']);g.take('488bf0' if rune else '488bf8','4885c0');g.branch('0f84' if rune else '74',False,4 if rune else 1);g.take('33d2','488bc8');g.call(s['ctor']);g.take('488bcb','488933' if rune else '48893b');g.call(s['barrier'])
  g.take('807c2438'+bytes((len(plan),)).hex());g.branch('0f85' if rune else '75',False,4 if rune else 1)
  for i,kind in enumerate(plan):
   last=i==len(plan)-1;load='488b1b' if last else '488b33' if rune else '488b3b';reader='488bcf' if rune else '488bce'
   if kind in ('array','reference'):
    site=g.at;cell=g.relative('488b15');usages.append(dict(member=i,site=site,cell=cell));g.take(reader,load)
   else:g.take(load,reader)
   g.call(s['reads'][i]);g.take('4885db' if last else '4885f6' if rune else '4885ff');near=rune and i<13;g.branch('0f84' if near else '74',False,4 if near else 1);g.take('4533c0',{'byte':'8ad0','float':'0f28c8','qword':'488bd0','array':'488bd0','reference':'488bd0'}[kind],'488bcb' if last else '488bce' if rune else '488bcf');g.call(s['setters'][i])
  g.jump('eb',1)
 g.take('488b5c2430','488b742440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,memberCount=len(plan),existing=existing,null=null,wrapperAllocation=allocation,childUsages=usages,condition='Initialized matching generated route and coherent reader/wrapper; valid typed original references; normal allocation/constructor/prehook/child/setter/barrier Win64 effects and disjoint stable storage; actual runtime route/default-provider selection remains separate.')


def launcher_caller(regions,entry,s,*,new=False,null=False):
 g=BytesPath(regions,entry);g.take('48895c2410','4889742418','57','4881ec80000000');flag=g.read(7)
 if flag[:2]!=b'\x80\x3d' or flag[-1]!=0:raise ValueError('launcher.flag')
 g.take('488bda','488bf9');g.branch('75',True,1);g.take('488d942490000000','c684249000000000','488bcf');g.call(s['header']);g.take('84c0');g.branch('0f84',null);allocation=None;usage=None
 if null:
  g.take('488bcb','48c70300000000');g.call(s['barrier'])
 else:
  g.take('48833b00');g.branch('75',not new,1)
  if new:
   site=g.at;cell=g.relative('488b0d');allocation=dict(site=site,cell=cell);g.call(s['allocate']);g.take('488bf0','4885c0');g.branch('0f84',False);g.take('33d2','488bc8');g.call(s['ctor']);g.take('488bcb','488933');g.call(s['barrier'])
  g.take('80bc249000000007');g.branch('0f85',False)
  for i,kind in enumerate(('byte','float','list','qword','dword','dword')):
   if kind=='list':
    site=g.at;cell=g.relative('488b15');usage=dict(site=site,cell=cell);g.take('488bcf','488b33')
   else:g.take('488b33','488bcf')
   g.call(s['reads'][i]);g.take('4885f6');g.branch('0f84' if i<4 else '74',False,4 if i<4 else 1);g.take('4533c0');g.take({'byte':'8ad0','float':'0f28c8','list':'488bd0','qword':'488bd0','dword':'8bd0'}[kind]);g.take('488bce');g.call(s['setters'][i])
  g.take('488b1b','488d4c2450','488bd7');g.call(s['hidden']);g.take('4885db');g.branch('74',False,1);g.take('0f1000','4533c0','488d542420','0f104810','488bcb','0f29442420','f20f104020','f20f11442440','0f294c2430');g.call(s['setters'][6]);g.jump('eb',1)
 g.take('4c8d9c2480000000','498b5b18','498b7320','498be3','5f','c3')
 return dict(selectedBytes=g.seen,newWrapper=new,nullWrapper=null,wrapperAllocation=allocation,listUsage=usage,memberCount=7,hiddenOutputBytes=40,hiddenReaderRegister='rdx',hiddenOutputStackOffset=80,setterCopyStackOffset=32,condition='Initialized metadata, sufficient buffered input, valid coherent matching generated routes, disjoint readable caller/output storage, normal helpers/allocation/constructor/barriers and Win64 ABI preservation; no provider/default selection or nested value semantics inferred.')


def launcher_setter(regions,entry,*,kind,slot,barrier=None):
 g=BytesPath(regions,entry);g.take('4883ec28')
 if kind in ('reference','entity40'):g.take('488b4910','4885c9')
 else:g.take('488b4110','4885c0')
 g.branch('75',True,1)
 if kind=='reference':g.take('488951'+bytes((slot,)).hex(),'4883c1'+bytes((slot,)).hex())
 elif kind=='entity40':g.take('0f1002','0f104a10','0f1141'+bytes((slot,)).hex(),'f20f104220','0f1149'+bytes((slot+16,)).hex(),'f20f1141'+bytes((slot+32,)).hex(),'4883c1'+bytes((slot+24,)).hex())
 else:g.take({'byte':'8850','float':'f30f1148','qword':'488950','dword':'8950'}[kind]+bytes((slot,)).hex())
 g.take('4883c428')
 if kind in ('reference','entity40'):
  if g.relative('e9')!=barrier:raise ValueError('launcher.setter.barrier')
 else:g.take('c3')
 return dict(selectedBytes=g.seen,kind=kind,slot=slot,storedBytes={'byte':1,'float':4,'qword':8,'dword':4,'reference':8,'entity40':40}[kind],condition='Nonnull valid wrapper/original and readable disjoint caller value storage; initialized normal barrier effects; original field declarations checked separately.')

def launcher_factory(regions,entry,*,allocate,constructor,barrier):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');flag=g.read(7)
 if flag[:2]!=b'\x80\x3d' or flag[-1]!=0:raise ValueError('launcher.factory.flag')
 g.take('488bf9');g.branch('75',True,1);site=g.at;cell=g.relative('488b0d');g.call(allocate);g.take('488bd8','4885c0');g.branch('75',True,1);g.take('33d2','488bcb');g.call(constructor);g.take('488d4f10','48895f10','488b5c2430','4883c420','5f')
 if g.relative('e9')!=barrier:raise ValueError('launcher.factory.barrier')
 return dict(selectedBytes=g.seen,allocationUsageSite=site,allocationCell=cell,instanceOffset=16,sameAllocationStored=True,condition='Initialized metadata; successful typed allocation and original constructor; compatible new original receiver; normal tail barrier with caller frame restored; no runtime invocation claim.')


def float_list(regions,entry,s,o,*,count):
 if count not in (-1,0,1,2):raise ValueError('floatList.count-witness')
 cur,rem,adv,used,total=(bytes((o[n],)).hex() for n in ('currentPtr','bufferLength','advancedCount','consumed','totalLength'));g=BytesPath(regions,entry);g.take('4053','55','57','4154','4157','4883ec30','837a'+rem+'04','4d8bf9','4d8be0','c744246800000000','488bda');g.branch('0f8c',False);g.take('488b43'+cur,'8b28','8b7b'+rem,'83c7fc');g.branch('0f88',False);g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','897b'+rem,'486343'+used,'488b4b'+total,'482bc8','4863c5','483bc8');g.branch('0f8c',False);g.take('4889742460','33f6','83fdff');g.branch('0f84',count==-1)
 if count==-1:g.take('498bcc','49893424');g.call(s['barrier']);g.take('488b742460','4883c430','415f','415c','5f','5d','5b','c3')
 else:
  g.take('4c896c2470','4c89742478','0f29742420','49393424');g.branch('0f85',False);g.take('498b4f20','33d2','488b89c0000000');g.call(s['classResolve']);g.take('488bc8');g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('0f84',False);g.take('498b4f20','488b91c0000000','488b4a08','48397120');g.branch('0f84',False);g.take('85ed');g.branch('0f88',False);g.take('498b4720','488b88c0000000','4c8b7108','498b4620','488b88c0000000');g.branch('0f84',count==0)
  if count:
   g.take('ba01000000');g.call(s['classResolve']);g.take('488bd5','488bc8');g.call(s['arrayAllocate'])
  else:
   g.take('33d2');g.call(s['classResolve']);g.take('39b0e0000000');g.branch('74',False,1);g.take('498b4e20','33d2','488b89c0000000');g.call(s['classResolve']);g.take('488b88b8000000','488b01');g.jump('e9')
  g.take('488d4f10','48894710');g.call(s['barrier']);g.take('498bcc','49893c24');g.call(s['barrier']);providerCell=g.relative('488b0d');g.take('39b1e0000000');g.branch('0f84',False);g.take('498b4720','488b88c0000000','488b4918');g.call(s['provider']);g.take('4c8bf0','85ed');g.branch('0f8e',count==0);callback=None
  if count:
   callback=g.relative('488d3d')
   if callback!=s['callback']:raise ValueError('floatList.named-inline-callback')
   g.take('660f1f840000000000');loop=g.at
   for i in range(count):
    if g.at!=loop:raise ValueError('floatList.loop-backedge')
    g.take('c744246800000000','4d85f6');g.branch('0f84',False);g.take('498b0e');g.call(s['prepare']);g.take('498b06','4c8b9090010000','4c8b8898010000','4c3bd7');g.branch('0f85',False);g.take('837b'+rem+'04');g.branch('0f8c',False);g.take('488b43'+cur,'f30f1000','f30f11442468','8b7b'+rem,'83c7fc');g.branch('0f88',False);g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','897b'+rem,'498b3c24','f30f10742468','4885ff');g.branch('0f84',False);g.take('498b4720','488b88c0000000','488b4130','4883782000');g.branch('0f84',False);g.take('498b4720','488b5710','488b88c0000000','4c8b6930','ff471c','4885d2');g.branch('0f84',False);g.take('48634f18','3b4a18');g.branch('0f83',False);g.take('8d4101','894718','3b4a18');g.branch('0f83',False);g.take('f30f11748a20','ffc6')
    if g.relative('488d3d')!=callback:raise ValueError('floatList.same-callback-after-append')
    g.take('3bf5');g.branch('0f8c',i+1<count)
  g.take('4c8b742478','4c8b6c2470','0f28742420','488b742460','4883c430','415f','415c','5f','5d','5b','c3')
 return dict(selectedBytes=g.seen,countWitness=count,freshOutputReference=True,requestedCapacity='count',headerBytes=4,wireElementBytes=4,managedElementStride=4,inlineCallback=callback if count!=-1 else None,normalReturn=True,loopInvariant='After i iterations, size=i and exactly 4*i payload bytes consumed; fresh array capacity is count, so 0<=i<count takes only inline Add and size becomes i+1. Counter cannot overflow for signed nonnegative Int32 count.',condition='Buffered coherent reader with nonwrapping pointer/counter updates; matching initialized closed List<float>/constructor/Add/provider contexts and ready classes; initially null output; successful zeroed object allocation and requested-capacity typed array allocation, normal preparation/barriers; exact Single formatter selected. Actual runtime provider/default selection and growth/refill paths remain separate.')


def float_constructor(regions,entry,s,*,empty=False):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','8bda','498bf8','488bf1','85d2');g.branch('0f88',False);g.take('498b4820','488b89c0000000');g.branch('74',empty,1)
 if empty:
  g.take('33d2');g.call(s['classResolve']);g.take('83b8e000000000');g.branch('74',False,1);g.take('488b4f20','33d2','488b89c0000000');g.call(s['classResolve']);g.take('488b88b8000000','488b01');g.jump('eb',1)
 else:g.take('ba01000000');g.call(s['classResolve']);g.take('8bd3','488bc8');g.call(s['arrayAllocate'])
 g.take('488d4e10','48894610','488b5c2430','488b742438','4883c420','5f')
 if g.relative('e9')!=s['barrier']:raise ValueError('floatListCtor.barrier')
 return dict(selectedBytes=g.seen,empty=empty,capacityArgument='incoming EDX int',storedArrayOffset=16,unchangedRequestedCapacity=True,condition='Nonnegative requested capacity, initialized matching List<float> constructor context and ready shared empty class; successful array allocation of exactly requested element count, zeroed fresh original List fields and normal barrier.')

def float_add(regions,entry):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec30','ff411c','498bf8','4c8b4910','488bd9','48635118','0f29742420','0f28f1','4d85c9');g.branch('75',True,1);g.take('413b5118');g.branch('72',True,1);g.take('8d4201','894118','413b5118');g.branch('72',True,1);g.take('f3410f11749120','488b5c2440','0f28742420','4883c430','5f','c3')
 return dict(selectedBytes=g.seen,itemsOffset=16,sizeOffset=24,versionOffset=28,arrayLengthOffset=24,arrayDataOffset=32,elementStride=4,storedValue='incoming XMM1 Single unchanged',condition='Valid initialized typed List<float> with 0<=size<array length and disjoint storage; selected original no-growth Add path. It increments version modulo32, stores size+1 and writes exactly four bytes at original array[size].')


def float_provider(regions,entry,s,hot):
 g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20','4883793800','488bf9');g.branch('74',False,1);tc=g.relative('488b0d');g.take('488b5f38','83b9e000000000','488b1b');g.branch('0f84',False);g.take('33d2','488bcb');g.call(s['typeFromHandle']);pc=g.relative('488b0d');g.take('488bd8','83b9e000000000');g.branch('74',False,1);g.take('488bcb');g.call(s['providerByType']);g.take('488b4f38','ba01000000','488bd8');g.call(s['indexed']);g.take('4885db');g.branch('0f84',False);g.take('488b0b','488bd0');g.call(s['assignable']);g.take('84c0');g.branch('0f84',False);g.take('488bc3','488b5c2438','4883c420','5f','c3')
 if tc!=hot['typeClassCell'] or pc!=hot['providerClassCell']:raise ValueError('floatProvider.same-class-cells')
 return dict(selectedBytes=g.seen,typeClassCell=tc,providerClassCell=pc,typeTransfer='same owned context[0] and identical named GetTypeFromHandle; fresh shared initialized cache-hit proof',providerTransfer='identical GetFormatter(Type) call with identical Type reference',resultTransfer='same expected formatter-class context[1] through identical indexed resolver; same assignability predicate and unchanged nonnull formatter result',condition='Initialized coherent matching closed generic contexts and ready classes, successful first-probe RuntimeType cache hit and compatible nonnull backend formatter; normal helper ABI. Live provider/default/override selection, cold and failure paths remain separate.')


def dictionary(regions,entry,s,o,*,count,comparer_diff=False):
 if count not in (-1,0,1,2):raise ValueError('moduleDictionary.count-witness')
 p,b,a,c,t=(bytes((o[k],)).hex() for k in ('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
 g=BytesPath(regions,entry);g.take('4c89442418','53','55','56','57','4154','4155','4157','4883ec60','4533e4','498bf1','837a'+b+'04','4d8bf8','488bda','4c89642438','488be9','4c89a424a8000000','4c89642430');g.branch('0f8c',False);g.take('488b43'+p,'4c6328','8b7b'+b,'83c7fc');g.branch('0f88',False);g.take('488343'+p+'04','8343'+a+'04','8343'+c+'04','897b'+b,'486343'+c,'488b4b'+t,'482bc8','493bcd');g.branch('0f8c',False);g.take('4183fdff');g.branch('0f84',count==-1)
 if count==-1:
  g.take('498bcf','4d8927');g.call(s['barrier'])
 else:
  g.take('4c89b424a0000000','4d3927');g.branch('0f85',False);g.take('488b4e20','ba03000000','488b6d10','488b89c0000000');g.call(s['classResolve']);g.take('488bc8');g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('0f84',False);g.take('488b4e20','488b91c0000000','488b4a20','4c396120');g.branch('0f84',False);g.take('488b4620','488b88c0000000','4c8b7120','4585ed');g.branch('0f88',False);g.branch('0f8f',count>0)
  if count:
   g.take('498b4620','488b88c0000000','488b4108','4c396020');g.branch('0f84',False);g.take('498b4620','418bd5','488bcf','4c8b80c0000000','4d8b4008');g.call(s['initialize']);g.jump('e9')
  g.take('498b4620','488b88c0000000','488b4910');g.call(s['defaultComparer']);g.take('483be8');g.branch('74',not comparer_diff,1)
  if comparer_diff:g.take('488d4f30','48896f30');g.call(s['barrier'])
  g.take('498bcf','49893f');g.call(s['barrier']);provider=g.relative('488b0d');g.take('4439a1e0000000');g.branch('0f84',False);g.take('488b4620','488b88c0000000','488b4930');g.call(s['keyProvider']);g.take('488b4e20','4c8bf0','488b89c0000000','488b4938');g.call(s['valueProvider']);g.take('4889442440','488be8','4585ed');g.branch('7f',count>0,1)
  if count:
   if g.relative('488d3d')!=s['keyCallback']:raise ValueError('moduleDictionary.key-callback')
   g.take('90');loop=g.at
   for i in range(count):
    if g.at!=loop:raise ValueError('moduleDictionary.loop-entry')
    g.take('488b4620','488b88c0000000','488b4940','4883793800');g.branch('0f84',False);g.take('0f57c0','0f11442448','33c0','48898424a8000000','4889442430','4d85f6');g.branch('0f84',False);g.take('498b0e');g.call(s['prepare']);g.take('498b06','4c8b9090010000','4c8b8898010000','4c3bd7');g.branch('0f85',False);g.take('837b'+b+'08');g.branch('0f8c',False);g.take('488b43'+p,'488b00','48898424a8000000','8b7b'+b,'83c7f8');g.branch('0f88',False);g.take('488343'+p+'08','8343'+a+'08','8343'+c+'08','897b'+b,'4885ed');g.branch('0f84',False);g.take('b905000000','4c8d4c2430','4c8bc3','488bd5');g.call(s['dispatch']);g.take('498b2f','4c8bbc24a8000000','4c8b642430','4885ed');g.branch('0f84',False);g.take('488b4620','488b88c0000000','488b4148','4883782000');g.branch('0f84',False);g.take('488b4620','488b88c0000000','488b7948','488b4720','488b88c0000000','488b81c0000000','4883782000');g.branch('0f84',False);g.take('488b4720','4d8bc4','498bd7','488bcd','4c8b88c0000000','498b81c0000000','41b102','4889442420');g.call(s['tryInsert']);g.take('4c8b642438')
    if g.relative('488d3d')!=s['keyCallback']:raise ValueError('moduleDictionary.same-key-callback')
    g.take('4c8bbc24b0000000','41ffc4','488b6c2440','4c89642438','453be5');g.branch('0f8c',i+1<count)
   g.jump('e9')
  g.take('4c8bb424a0000000')
 g.take('4883c460','415f','415d','415c','5f','5e','5d','5b','c3')
 return dict(selectedBytes=g.seen,countWitness=count,freshOutput=True,comparerDiff=comparer_diff,headerBytes=4,keyWireBytes=8,keyOrder='little-endian',valueWidth='delegated selected slot5 child',insertArguments=dict(rcx='same fresh dictionary output',rdx='unchanged decoded UInt64 key',r8='unchanged decoded child reference',r9b=2),counterInvariant='After i normal child and TryInsert returns, i keys and i value callbacks consumed; counter i increments once, compares signed against count and returns after count.',condition='Buffered nonwrapping Reader/counters; initialized coherently inflated ulong/reference contexts; initially null output; normal successful zeroed allocation and exact Initialize(count), incoming comparer either equals selected default or is stored unchanged with a normal barrier; selected UnmanagedFormatter<ulong> key and compatible value slot5 callback; normal ready preparation/insert/barriers; disjoint stable storage. Dictionary insert/table effects, actual context inflation/provider/default choice and child framing remain separately proved.')


def enclosing_union(regions,entry,s,*,tag,count,table,null=False,existing=False):
 if not 0<=tag<count<=128:raise ValueError('moduleUnion.tag-scope')
 g=BytesPath(regions,entry);g.take('48895c2408','4889742418','57','4883ec20');ready=g.relative('803d')+1;g.take('00','498bf8','488bda');g.branch('0f84',False);g.take('33f6','488d542438','488bcb','6689742438');g.call(s['header']);g.take('84c0');g.branch('0f84',null)
 usage=None
 if null:g.take('488937');g.jump('e9')
 else:
  g.take('0fb7742438','83fe'+bytes((count-1,)).hex());g.branch('0f87',False)
  if g.relative('488d15')!=s['imageBase']:raise ValueError('moduleUnion.image-base')
  g.take('8b84b2'+(table-s['imageBase']).to_bytes(4,'little').hex(),'4803c2','ffe0');g.at=s['route'];g.take('488b0f','4885c9');g.branch('74',not existing,1)
  if existing:
   expected=g.relative('488b15');g.take('488b09');g.call(s['assignable']);g.take('84c0');g.branch('74',True,1)
  site=g.at;usage=g.relative('488b15');g.take('488bcb');g.call(s['packable']);g.take('488907');g.jump('e9')
 g.take('488bcf');g.call(s['barrier']);g.jump('e9');g.take('488b5c2430','488b742440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,readyFlag=ready,childContextSite=site if not null else None,childUsageCell=usage,existingComparisonTypeCell=expected if existing and not null else None,selectedTag=None if null else tag,childInitiallyNull=not existing,existingWrongType=existing,sameReader=True,sameOutput=True,completeSelectedReturn=True,condition='Initialized generated union, matching table target, buffered true tag helper with selected UInt16 tag or false marker, null or type-incompatible existing wrapper output; normal selected typed ReadPackable child/collector-disabled barrier ABI. Runtime provider selection and source owner/EOF separate.')

def enclosing_root_field(regions,entry,source,offset):
 g=BytesPath(regions,entry);g.take('498bcd');site=g.at;context=g.relative('488b15');g.take('498b1f');g.call(source);g.take('4885db');g.branch('0f84',False);g.take('4c8b4310','4d85c0');g.branch('0f84',False);collector=g.relative('833d')+1;g.take('00','498980'+offset.to_bytes(4,'little').hex());g.branch('74',True,1)
 return dict(selectedBytes=g.seen,contextSite=site,usageCell=context,collectorFlag=collector,resultTransfer='unchanged RAX stored into same wrapper.__instance.modules offset',fieldOffset=offset,readerRegister='r13',wrapperHolderRegister='r15',completeParentReader=False,condition='Reached this generated source with live preserved root aliases, nonnull wrapper and original, normal matching ReadPackable return and collector disabled; earlier fields and continuation remain separate.')

def enclosing_header(regions,entry,o,*,marker):
 if marker not in ('short','extended','false'):raise ValueError('moduleUnion.marker-profile')
 p,b,a,c=(bytes((o[k],)).hex() for k in ('currentPtr','bufferLength','advancedCount','consumed'));g=BytesPath(regions,entry);g.take('48895c2408','4889742410','48897c2418','4156','4883ec20');ready=g.relative('803d')+1;g.take('00','4c8bf2','488bd9');g.branch('0f84',False);g.take('837b'+b+'01');g.branch('0f8c',False);g.take('488b43'+p,'0fb638','8b73'+b,'83ee01');g.branch('0f88',False);g.take('48ff43'+p,'ff43'+a,'ff43'+c,'8973'+b,'4080fffa');g.branch('73',marker!='short',1)
 if marker=='short':g.take('6641893e','b001')
 else:
  g.branch('75',marker=='false',1)
  if marker=='false':g.take('33c0','66418906');g.jump('eb',1)
  else:
   g.take('837b'+b+'02');g.branch('0f8c',False);g.take('488b43'+p,'0fb700','66418906','8b7b'+b,'83c7fe');g.branch('0f88',False);g.take('488343'+p+'02','8343'+a+'02','8343'+c+'02','897b'+b);g.jump('eb',1);g.take('b001')
 g.take('488b5c2430','488b742438','488b7c2440','4883c420','415e','c3')
 return dict(selectedBytes=g.seen,readyFlag=ready,marker=marker,wireBytes=3 if marker=='extended' else 1,outputBits=16,tagOutput='short byte or extended little-endian UInt16' if marker!='false' else 'zero',predicate='AL true' if marker!='false' else 'EAX zero',condition='Initialized helper, valid buffered/counter bounds, disjoint stable Reader/buffer/UInt16 output/frame; high markers251..255 return false without canonical admission of reserved markers.')


def bridge_packable_return(regions,entry,dispatch):
 g=BytesPath(regions,entry);g.take('b905000000','4c8d8c2428010000','4c8bc7','488bd3');g.call(dispatch);g.take('488b842428010000','4881c4c8000000','415f','415e','415d','415c','5f','5e','5d','5b','c3')
 return dict(selectedBytes=g.seen,slot=5,reader='same saved RDI from reviewed full clone',output='same zeroed eight-byte local RSP+296',returnValue='same complete local loaded into RAX',normalReturn=True)

def bridge_list_callback(regions,entry,prepare):
 g=BytesPath(regions,entry);g.take('498b0c24');g.call(prepare);g.take('4d8b0c24','4c8d442420','498bd5','498bcc','498b8190010000','4d8b8998010000','ffd0','498b1e','488b6c2420')
 return dict(selectedBytes=g.seen,receiver='same R12 element formatter',reader='same preserved R13 Reader',output='zeroed eight-byte local RSP+32',callbackSlot=400,methodInfoSlot=408,returnedChild='unchanged local loaded into RBP before independently proved append',callbackABI='RCX formatter/RDX Reader/R8 output/R9 selected MethodInfo')


def reference_list(regions,entry,offsets,symbols,*,count=1,new=True,grow=False):
 if type(count) is not int or count not in (-1,0,1,2,3):raise ValueError('paramGraphList.witness-count')
 g=BytesPath(regions,entry);cur,rem,adv,used,total=(bytes((offsets[n],)).hex() for n in ('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
 g.take('4053','55','4155','4156','4157','4883ec30','837a'+rem+'04','4d8bf9','4d8bf0','48c744242000000000','4c8bea');g.branch('7d',True,1)
 g.take('498b45'+cur,'8b28','896c2468','418b5d'+rem,'83c3fc');g.branch('79',True,1)
 g.take('498345'+cur+'04','418345'+adv+'04','418345'+used+'04','41895d'+rem,'496345'+used,'498b4d'+total,'482bc8','4863c5','483bc8');g.branch('0f8c',False);g.take('83fdff','0f95c0','84c0');g.branch('0f84',count==-1)
 collectors=[];calls=[]
 if count==-1:
  collectors.append(flag(g,'833d'));g.take('49c70600000000');g.branch('74',True,1)
 else:
  g.take('4889742460','48897c2470','4c89642478','49833e00');g.relative('488d35');g.take('498b4720');g.branch('74',new,1)
  if new:
   g.take('488b88c0000000','488b01','f6803801000001');g.branch('75',True,1);g.take('488bc8');g.call(symbols['allocate']);g.take('488bd8','4885c0');g.branch('0f84',False)
   g.take('498b4f20','488b91c0000000','488b4a08','4883792000');g.branch('75',True,1);g.take('498b4720','488b88c0000000','488b7908','85ed');g.branch('0f88',False);g.take('488b4720','488b80c0000000');g.branch('0f84',count==0)
   if count:
    g.take('488b4008','f6803801000001');g.branch('75',True,1);g.take('488bd5','488bc8');g.call(symbols['arrayAllocate']);collectors.append(flag(g,'833d'));g.take('48894310');g.branch('0f84',True)
   else:
    g.take('488b00','f6803801000001');g.branch('75',True,1);g.take('83b8e000000000');g.branch('75',True,1);g.take('488b4720','488b88c0000000','488b01','f6803801000001');g.branch('75',True,1);collectors.append(flag(g,'833d'));g.take('488b80b8000000','488b08','48894b10');g.branch('74',True,1)
   collectors.append(flag(g,'833d'));g.take('49891e');g.branch('74',True,1)
  else:
   g.take('488b90c0000000','498b1e','488b4210','4883782000');g.branch('75',True,1);g.take('498b4720','488bcb','488b90c0000000','488b5210');g.call(symbols['clear']);g.jump('e9')
  provider=g.relative('488b0d');g.take('83b9e000000000');g.branch('75',True,1);g.take('498b4720','488b88c0000000','488b4918');g.call(symbols['provider']);g.take('33f6','4c8be0','85ed');g.branch('0f8e',count==0)
  if count:
   g.take('90');loop=g.at
   for i in range(count):
    if g.at!=loop:raise ValueError('paramGraphList.same-loop-entry')
    g.take('48c744242000000000','4d85e4');g.branch('0f84',False);g.take('498b0c24');g.call(symbols['prepare']);g.take('4d8b0c24','4c8d442420','498bd5','498bcc','498b8190010000','4d8b8998010000');calls.append(g.at);g.take('ffd0','498b1e','488b6c2420','4885db');g.branch('0f84',False)
    g.take('498b4720','488b88c0000000','488b4130','4883782000');g.branch('75',True,1);g.take('498b4720','488b5310','488b88c0000000','488b7930','ff431c','48634b18','4885d2');g.branch('0f84',False);g.take('3b4a18');g.branch('72',not grow,1)
    if grow:
     g.take('488b4720','4c8b80c0000000','498b4058','4883782000');g.branch('75',True,1);g.take('488b4720','488bd5','488bcb','4c8b80c0000000','4d8b4058');g.call(symbols['grow']);g.jump('eb',1)
    else:
     g.take('8d4101','894318','3b4a18');g.branch('0f83',False);collectors.append(flag(g,'833d'));g.take('48896cca20');g.branch('74',True,1)
    g.take('ffc6','3b742468');g.branch('0f8c',i+1<count)
  g.take('488b7c2470','4c8b642478','488b742460')
 g.take('4883c430','415f','415e','415d','5d','5b','c3')
 if len(set(collectors))>1:raise ValueError('paramGraphList.shared-disabled-collector')
 return dict(selectedBytes=g.seen,countWitness=count,newList=new,elementCallbackSites=calls,headerBytes=4,callbackAbi=dict(reader='r13',output='rsp+32',receiver='r12',methodInfoSlot=408,callbackSlot=400),growthDelegate=grow,arrayReferenceStride=8,initialElementOutput=0,normalReturn=True,disabledCollectorCells=collectors,wholeOwnerAdmitted=False)


def provider_cache_cache_hit(g,symbols,*,inline):
 # Both paths start with RBX equal to the same nonnull Il2CppType pointer.
 g.take('b201','488bcb');g.call(symbols['classFromType'])
 g.take('4c8d6020' if inline else '4c8d7820');cache=g.relative('488b1d');g.take('488b8b80000000');enter=g.relative('ff15');g.take('90','488b4340','483b4338');g.branch('0f84',False)
 g.take(*(['4533ed','4c8b7348','49ffce','498bcc'] if inline else ['4533e4','488b6b48','48ffcd','498bcf']));g.call(symbols['hash'])
 g.take('488bf8','488b7368','448b7b50' if inline else '448b7350','4923fe' if inline else '4823fd','488d0c7f','443b3cce' if inline else '443b34ce');g.branch('75',True,1)
 g.take('48837b3800');g.branch('0f87',False);g.take('488d047f','833cc600');g.branch('0f85' if inline else '75',False,4 if inline else 1)
 g.take('488b54c608','498bcc' if inline else '498bcf');g.call(symbols['compare']);g.take('85c0');g.branch('0f85' if inline else '75',False,4 if inline else 1)
 g.take('4883ffff');g.branch('0f84' if inline else '74',False,4 if inline else 1)
 g.take('488d0c7f','488d14ce','488b4348','488d0c40','488b4368','488d0cc8','483bd1');g.branch('0f84' if inline else '74',False,4 if inline else 1)
 g.take('488b4a10','488b4370','4c8b34c8' if inline else '488b2cc8','488b8b80000000');leave=g.relative('ff15');g.take('90')
 return dict(cacheGlobalCell=cache,lockImportCell=enter,unlockImportCell=leave,keyFromResolvedClassOffset=32,entryStride=24,entryKeyOffset=8,entryValueIndexOffset=16,valueTableOffset=112,lookup='same first hash/mask probe, non-sentinel entry, no special-key branch, key comparison zero and valid value index',returnedObjectRegister='r14' if inline else 'rbp')

def provider_cache_type_from_handle(regions,entry,symbols):
 g=BytesPath(regions,entry);g.take('48895c2410','55','56','57','4154','4155','4156','4157','4883ec60','488bd9','4885c9');g.branch('0f84',False);type_class=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
 proof=provider_cache_cache_hit(g,symbols,inline=False);g.take('488bc5','488b9c24a8000000','4883c460','415f','415e','415d','415c','5f','5e','5d','c3')
 return dict(selectedBytes=g.seen,typeClassCell=type_class,cache=proof,inputType='incoming RCX',result='same cached object in RAX',normalReturn=True)

def provider_cache_provider(regions,entry,symbols):
 g=BytesPath(regions,entry);g.take('48895c2418','55','56','57','4154','4155','4156','4157','4883ec60','488be9','4883793800');g.branch('0f84',False);g.take('488b5d38','488b1b');type_class=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False);g.take('4885db');g.branch('0f84',False);g.take('83b9e000000000');g.branch('0f84',False)
 proof=provider_cache_cache_hit(g,symbols,inline=True);provider_class=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False);g.take('803d');flag=g.at+5+int.from_bytes(g.read(4),'little',signed=True);g.take('00');g.branch('0f84',False)
 if g.relative('488b0d')!=provider_class:raise ValueError('providerBridge.same-provider-class')
 g.take('83b9e000000000');g.branch('0f84',False);g.take('498bce');g.call(symbols['backend']);g.take('488bd8','ba01000000','488b4d38');g.call(symbols['indexedType']);g.take('4885db');g.branch('74',False,1);g.take('488bd0','488b0b');g.call(symbols['assignable']);g.take('84c0');g.branch('74',False,1)
 g.take('488bc3','488b9c24b0000000','4883c460','415f','415e','415d','415c','5f','5e','5d','c3')
 return dict(selectedBytes=g.seen,typeClassCell=type_class,providerClassCell=provider_class,providerInitFlag=flag,cache=proof,typeInput='incoming GetFormatter MethodInfo context slot zero',expectedResultType='same method context slot one',result='unchanged nonnull backend result after compatible-class check',normalReturn=True)


def provider_success(regions,entries,symbols,hot):
 proofs={}
 g=BytesPath(regions['ready'],entries['ready']);g.take('4883ec28','83b9e000000000');g.branch('74',False,1);g.take('4883c428','c3');proofs['ready']=g.seen
 g=BytesPath(regions['indexed'],entries['indexed']);g.take('488bc1','4863ca','488b0cc8')
 if g.relative('e9')!=entries['entry']:raise ValueError('provider.indexed-context-tail')
 proofs['indexed']=g.seen
 g=BytesPath(regions['providerByType'],entries['providerByType']);g.take('4053','4883ec20','803d');flag=g.at+5+int.from_bytes(g.read(4),'little',signed=True);g.take('00','488bd9');g.branch('74',False,1);cell=g.relative('488b0d');g.take('83b9e000000000');g.branch('74',False,1);g.take('488bcb','4883c420','5b')
 if g.relative('e9')!=symbols['backend'] or flag!=hot['providerInitFlag'] or cell!=hot['providerClassCell']:raise ValueError('provider.shared-backend')
 proofs['providerByType']=g.seen
 g=BytesPath(regions['castObject'],entries['castObject']);g.take('4053','4883ec20','488bd9','4885c9');g.branch('74',False,1);g.take('488b09');g.call(symbols['assignable']);g.take('33c9','84c0','480f44d9','488bc3','4883c420','5b','c3');proofs['castObject']=g.seen
 g=BytesPath(regions['canonical'],entries['canonical']);g.take('48895c2408','4889742410','57','4883ec20','4883793800','488bf9');g.branch('75',True,1);g.take('488b5f38');typecell=g.relative('488b0d');g.take('488b1b');g.call(entries['ready']);g.take('33d2','488bcb');g.call(entries['typeFromHandle']);providercell=g.relative('488b0d');g.take('488bd8');g.call(entries['ready']);g.take('488bcb');g.call(entries['providerByType']);g.take('488b4f38','488bd8','488b4908');g.call(entries['entry']);g.take('488bd0','488bcb');g.call(entries['castObject']);g.take('4885c0');g.branch('0f85',True);g.take('488b5c2430','488b742438','4883c420','5f','c3')
 if typecell!=hot['typeClassCell'] or providercell!=hot['providerClassCell'] or symbols['indexedType']!=entries['indexed']:raise ValueError('provider.same-context-and-classes')
 proofs['canonical']=g.seen
 return dict(selectedBytes=proofs,contextTransfer='actual context[index=1] tail-calls the identical entry resolver called by canonical with context[1]',typeTransfer='identical type-context slot zero; proved equal successful initialized cache lookup',providerTransfer='identical provider class, initialization flag, backend and Type argument',resultTransfer='identical expected-class resolver and assignability check; unchanged compatible nonnull backend result',condition='Initialized coherent matching method contexts, first-probe RuntimeType cache hit, normal helper ABI and nonnull compatible formatter; initialization, cache misses/collisions, exceptions and runtime provider selection are not admitted.')


"""Current reference/reference dictionary loop induction; native bindings remain separate."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def dictionary(regions,entry,s,o,*,count):
 if type(count)is not int or count not in(-1,0,1):raise ValueError('npc.dictionary-scope')
 p,b,a,c,t=(bytes((o[k],)).hex()for k in('currentPtr','bufferLength','advancedCount','consumed','totalLength'));g=BytesPath(regions,entry);g.take('4c89442418','53','55','56','57','4155','4156','4157','4883ec60','4533ff','498bf9','837a'+b+'04','4d8be8','488bda','4c897c2430','4c8bf1','4c897c2438');g.branch('0f8c',False);g.take('488b43'+p,'486328','89ac24a8000000','8b73'+b,'83c6fc');g.branch('0f88',False);g.take('488343'+p+'04','8343'+a+'04','8343'+c+'04','8973'+b,'486343'+c,'488b4b'+t,'482bc8','483bcd');g.branch('0f8c',False);g.take('83fdff');g.branch('0f84',count==-1)
 if count==-1:g.take('498bcd','4d897d00');g.call(s['barrier'])
 else:
  g.take('4c89a424a0000000','4d397d00');g.branch('0f85',False);g.take('488b4f20','ba03000000','4d8b7610','488b89c0000000');g.call(s['classResolve']);g.take('488bc8');g.call(s['allocate']);g.take('488bf0','4885c0');g.branch('0f84',False);g.take('488b4f20','488b91c0000000','488b4a20','4c397920');g.branch('0f84',False);g.take('488b4720','4d8bc6','8bd5','488bce','4c8b88c0000000','4d8b4920');g.call(s['constructor']);g.take('498bcd','49897500');g.call(s['barrier']);provider=g.relative('488b0d');g.take('4439b9e0000000');g.branch('0f84',False);g.take('488b4720','488b88c0000000','488b4930');g.call(s['provider']);g.take('488b4f20','4c8bf0','488b89c0000000','488b4938');g.call(s['provider']);g.take('4c8be0','85ed');g.branch('0f8e',count==0)
  if count:
   g.take('660f1f840000000000');loop=g.at
   g.take('488b4f20','488b91c0000000','488b4a40','4883793800');g.branch('0f84',False);g.take('0f57c0','0f11442448','33c0','4889442430','4889442438','4d85f6');g.branch('0f84',False);g.take('b905000000','4c8d4c2430','4c8bc3','498bd6');g.call(s['dispatch']);g.take('4d85e4');g.branch('0f84',False);g.take('b905000000','4c8d4c2438','4c8bc3','498bd4');g.call(s['dispatch']);g.take('498b6d00','488b442438','4c8b6c2430','4889442440','4885ed');g.branch('0f84',False);g.take('488b4720','488b88c0000000','488b4148','4883782000');g.branch('0f84',False);g.take('488b4720','488b88c0000000','488b7148','488b4620','488b88c0000000','488b81c0000000','4883782000');g.branch('0f84',False);g.take('488b4620','498bd5','4c8b442440','488bcd','4c8b88c0000000','498b81c0000000','41b102','4889442420');g.call(s['insert']);g.take('4c8bac24b0000000','41ffc7','443bbc24a8000000');backedge=g.relative('0f8c')
   if backedge!=loop:raise ValueError('npc.dictionary-exact-loop-backedge')
  g.take('4c8ba424a0000000');g.jump('eb',1)
 g.take('4883c460','415f','415e','415d','5f','5e','5d','5b','c3');return dict(selectedBytes=g.seen,countProfile='null'if count==-1 else'zero'if count==0 else'all-positive-Int32',headerBytes=4,keyOutput='zeroed same RSP+48 -> R13 -> TryInsert.RDX',valueOutput='zeroed same RSP+56 -> RSP+64 -> TryInsert.R8',sameReader='saved RBX passed to both slot5 callbacks',sameDictionary='fresh typed constructor result stored into original output and passed to TryInsert.RCX',insertMode=2,countInvariant='R15D starts0; exact one loop body has no R15 write except INC; normal Win64 callees preserve R15; INC is followed by signed CMP to unchanged saved count and exact JL backedge to the same loop head. Thus induction consumes exactly count pairs and exits for every positive signed count without counter overflow.',normalReturn=True,condition='Fresh output, sufficient buffered nonwrapping bounds, initialized coherently inflated string/reference contexts, compatible selected key/value providers and slot5 callbacks; normal successful disjoint allocation, constructor(count,comparer), class/context, insertion and barrier helpers. Runtime constructor/table/storage effects and live provider/default selection excluded.')


def flag(g,prefix='803d'):
 cell=g.relative(prefix);g.take('00');return cell


def reference_list(regions,entry,offsets,symbols,*,count=1):
 if type(count)is not int or count not in(-1,0,1):raise ValueError('npcList.profile')
 new=True;grow=False
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
  provider=g.relative('488b0d');g.take('83b9e000000000');g.branch('75',True,1);g.take('498b4720','488b88c0000000','488b4918');g.call(symbols['provider']);g.take('33f6','4c8be0','85ed');g.branch('0f8e',count==0)
  if count:
   g.take('90');loop=g.at
   for i in range(count):
    if g.at!=loop:raise ValueError('referenceList.same-loop-entry')
    g.take('48c744242000000000','4d85e4');g.branch('0f84',False);g.take('498b0c24');g.call(symbols['prepare']);g.take('4d8b0c24','4c8d442420','498bd5','498bcc','498b8190010000','4d8b8998010000');calls.append(g.at);g.take('ffd0','498b1e','488b6c2420','4885db');g.branch('0f84',False)
    g.take('498b4720','488b88c0000000','488b4130','4883782000');g.branch('75',True,1);g.take('498b4720','488b5310','488b88c0000000','488b7930','ff431c','48634b18','4885d2');g.branch('0f84',False);g.take('3b4a18');g.branch('72',not grow,1)
    g.take('8d4101','894318','3b4a18');g.branch('0f83',False);collectors.append(flag(g,'833d'));g.take('48896cca20');g.branch('74',True,1)
    g.take('ffc6','3b742468');back=g.relative('0f8c')
    if back!=loop:raise ValueError('npcList.exact-backedge')
  g.take('488b7c2470','4c8b642478','488b742460')
 g.take('4883c430','415f','415e','415d','5d','5b','c3')
 if len(set(collectors))>1:raise ValueError('referenceList.shared-disabled-collector')
 return dict(selectedBytes=g.seen,countProfile='null'if count==-1 else'zero'if count==0 else'all-positive-Int32',newList=new,elementCallbackSites=calls,headerBytes=4,callbackAbi=dict(reader='r13',output='rsp+32',receiver='r12',methodInfoSlot=408,callbackSlot=400),growthDelegate=grow,arrayReferenceStride=8,initialElementOutput=0,normalReturn=True,disabledCollectorCells=collectors,wholeOwnerAdmitted=False,condition='Fresh output and typed normally allocated List with initial size/version zero and exact count capacity; initialized coherent contexts and matching provider/slot5 callback; normal disjoint helpers and disabled collector. One full source iteration starts ESI0, has only INC ESI, compares unchanged saved signed count at stack104 and exact JL backedge; induction stores count references without growth for all positive signed counts. Runtime allocation/helper effects, cold inflation and live provider/default selection excluded.')

"""Exact selected unsigned-key/reference dictionary; caller supplies typed facts."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def uint_dictionary(regions,entry,s,*,count):
 if type(count)is not int or count not in(-1,0,1):raise ValueError('npcUintDictionary.profile')
 g=BytesPath(regions,entry);g.take('488bc4','53','55','56','57','4154','4883ec50','4c8be2','33ed','488bf1','8968a8','498bcc','896810','488d50a8','488968b0','498bd9','498bf8');g.call(s['header']);g.take('84c0');g.branch('0f84',count==-1)
 if count==-1:
  g.take('488bcf','48892f');g.call(s['barrier']);g.take('90');g.jump('e9')
 else:
  g.take('4c89b42490000000','4c89ac2480000000','4c89bc2498000000','448b742420','48392f');g.branch('0f85',False);g.take('488b4b20','ba03000000','4c8b7e10','488b89c0000000');g.call(s['indexed']);g.take('488bc8');g.call(s['allocate']);g.take('488bf0','4885c0');g.branch('0f84',False);g.take('488b4b20','488b91c0000000','488b4a20','48396920');g.branch('0f84',False);g.take('488b4320','4d8bc7','418bd6','488bce','4c8b88c0000000','4d8b4920');g.call(s['constructor']);g.take('488bcf','488937');g.call(s['barrier']);provider=g.relative('488b0d');g.take('39a9e0000000');g.branch('0f84',False);g.take('488b4320','488b88c0000000','488b4930');g.call(s['keyProvider']);g.take('488b4b20','488bf0','488b89c0000000','488b4938');g.call(s['valueProvider']);g.take('4c8bf8','4585f6');g.branch('7f',count==1,1)
  if count:
   loop=g.at;g.take('488b4b20','488b91c0000000','488b4a40','4883793800');g.branch('0f84',False);g.take('0f57c0','0f11442438','33c0','89842488000000','4889442428','4885f6');g.branch('0f84',False);g.take('4c8d8c2488000000','4d8bc4','488bd6');g.call(s['keyDispatch']);g.take('4d85ff');g.branch('74',False,1);g.take('b905000000','4c8d4c2428','4d8bc4','498bd7');g.call(s['valueDispatch']);g.take('8b842488000000','4c8b2f','89442420','488b442428','4889442430','4d85ed');g.branch('74',False,1);g.take('488b4320','488b88c0000000','488b4148','4883782000');g.branch('0f84',False);g.take('488b4320','498bcd','4c8b442430','8b542420','4c8b88c0000000','4d8b4948');g.call(s['add']);g.take('ffc5','413bee');back=g.relative('0f8c')
   if back!=loop:raise ValueError('npcUintDictionary.exact-backedge')
   g.jump('e9')
  g.take('4c8bac2480000000','4c8bbc2498000000','4c8bb42490000000')
 g.take('4883c450','415c','5f','5e','5d','5b','c3')
 return dict(selectedBytes=g.seen,countProfile='null'if count==-1 else'zero'if count==0 else'all-positive-Int32',sameReader='saved R12 to both key and value dispatch',keyOutput='zeroed DWORD stack136 -> DWORD stack32 -> EDX',valueOutput='zeroed QWORD stack40 -> stack48 -> R8',sameDictionary='fresh constructor result -> original output -> R13 -> Add.RCX',normalReturn=True,condition='Fresh output, buffered valid header, ready coherent uint/reference contexts and matching selected providers/callbacks; normal typed allocation, constructor(count,comparer), Add and disabled barrier. EBP starts0 and only INC, compares immutable signed count R14D and exact JL backedge; normal Win64 callees preserve both, giving count pairs for every positive signed count without overflow. Runtime construction/storage/helper effects and live inflation/default selection excluded.')
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def uint_formatter(regions,entry,o,advance):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','837a'+bytes((o['bufferLength'],4)).hex(),'498bf8','488bda');g.branch('0f8c',False);g.take('488b42'+bytes((o['currentPtr'],)).hex(),'8b00','ba04000000','488bcb','8907','488b5c2430','4883c420','5f')
 if g.relative('e9')!=advance:raise ValueError('npcUint.formatter-advance')
 return dict(selectedBytes=g.seen,wireBytes=4,outputBytes=4,condition='Matched current UnmanagedFormatter<uint> callback, buffered valid disjoint Reader/output, normal shared Advance(4) tail. Live provider selection excluded.')

def uint_dispatch(regions,entry,o,prepare,callback,advance):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','488b0a','498bf9','498bd8','488bf2');g.call(prepare);g.take('488b06','4c8b9090010000','4c8b8898010000')
 if g.relative('488d05')!=callback:raise ValueError('npcUint.actual-inline-callback')
 g.take('4c3bd0');g.branch('0f85',False);g.take('837b'+bytes((o['bufferLength'],4)).hex());g.branch('0f8c',False);g.take('488b43'+bytes((o['currentPtr'],)).hex(),'8b00','ba04000000','488bcb','8907');g.call(advance);g.take('488b5c2430','488b742438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,wireBytes=4,callbackSlot=5,keyBits=32,condition='Current typed uint slot-five callback equality, ready coherent receiver/context and normal preparation/Advance(4) helpers; no alternate callbacks or live default selection.')

def uint_add(regions,entry,insert):
 g=BytesPath(regions,entry);g.take('48895c2408','48896c2410','4889742418','57','4883ec30','498b4120','498bd9','498bf8','8bf2','488be9','4c8b88c0000000','498b81c0000000','4883782000');g.branch('0f84',False);g.take('488b4320','41b102','4c8bc7','8bd6','488b88c0000000','488b81c0000000','488bcd','4889442420');g.call(insert);g.take('488b5c2440','488b6c2448','488b742450','4883c430','5f','c3')
 return dict(selectedBytes=g.seen,keyBits=32,valueBits=64,insertMode=2,dictionaryContextSlot=24,condition='Ready coherent Dictionary<uint,reference> class context and normal TryInsert behavior2; unchanged receiver/key/value reach actual typed storage helper. Hash/comparer/table effects and runtime contents excluded.')
"""Current selected one-field Atmospheric wrapper source and construction."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def atmospheric(regions,entry,s,*,null=False,new=False):
 g=BytesPath(regions,entry);g.take('48895c2418','57','4883ec20');flag=g.relative('803d');g.take('00','488bda','488bf9');g.branch('75',True,1);g.take('488d542430','c644243000','488bcf');g.call(s['header']);g.take('84c0');g.branch('0f84',null)
 allocation=None;context=None
 if null:
  g.take('488bcb','48c70300000000');g.call(s['barrier']);g.take('90');g.jump('e9')
 else:
  g.take('4889742438','48833b00');g.branch('0f84',new)
  if new:
   at=g.at;cell=g.relative('488b0d');allocation=dict(site=at,cell=cell);g.call(s['allocate']);g.take('488bf0','4885c0');g.branch('0f84',False);g.take('33d2','488bc8');g.call(s['wrapperCtor']);g.take('488bcb','488933');g.call(s['barrier']);g.take('90');g.jump('e9')
  g.take('0fb6742430','4080fe01');g.branch('0f85',False);at=g.at;cell=g.relative('488b15');context=dict(site=at,cell=cell);g.take('488bcf','488b1b');read=g.at;g.call(s['packable']);g.take('4885db');g.branch('75',True,1);g.take('4533c0','488bd0','488bcb');g.call(s['setter']);g.take('488b742438')
 g.take('488b5c2440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,null=null,newWrapper=new,typedContext=context,allocation=allocation,objectMembers=1,readCall=None if null else read,condition='Initialized actual generated metadata, normal current object header FF or exact MC1, disjoint Reader/wrapper, normal exact typed allocation/constructor, independently admitted dictionary child and disabled barrier. No live provider/default/inflation choice or whole owner admission.')

def construct(regions,entry,s,*,original=False):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');flag=g.relative('803d');g.take('00','488bf9');g.branch('75',True,1);site=g.at;cell=g.relative('488b0d');g.call(s['allocate']);g.take('488bd8','4885c0');g.branch('75',True,1)
 if original:
  methodSite=g.at;methodCell=g.relative('488b15');g.take('488bcb');g.call(s['dictionaryCtor'])
 else:methodSite=methodCell=None;g.take('33d2','488bcb');g.call(s['originalCtor'])
 g.take('488d4f10','48895f10','488b5c2430','4883c420','5f')
 if g.relative('e9')!=s['barrier']:raise ValueError('npcAtmospheric.constructor-barrier')
 return dict(selectedBytes=g.seen,allocation=dict(site=site,cell=cell),methodContext=None if not original else dict(site=methodSite,cell=methodCell),ownedFieldOffset=16,condition='Initialized selected metadata, normal exact typed allocation and constructor, stable compatible receiver and disabled collector; no execution or provider choice claim.')

def setter(regions,entry,s):
 g=BytesPath(regions,entry);g.take('4883ec28','488b4910','4885c9');g.branch('75',True,1);g.take('48895110','4883c110','4883c428')
 if g.relative('e9')!=s['barrier']:raise ValueError('npcAtmospheric.setter-barrier')
 return dict(selectedBytes=g.seen,holderSlot=16,originalFieldSlot=16,unchangedReference=True,condition='Nonnull current wrapper original, ordinary disabled barrier.')

def dictionary_formatter_default(regions,entry,target):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','488b4220','488bda','488bf9','488b90c0000000','488b02','4883782000');g.branch('0f84',False);g.take('488b4320','33d2','488bcf','4c8b80c0000000','4d8b00','488b5c2430','4883c420','5f')
 if g.relative('e9')!=target:raise ValueError('npcDictionary.default-ctor-tail')
 return dict(selectedBytes=g.seen,comparerArgument=None,constructorContextSlot=0,normalReturnViaTail=True)

def dictionary_formatter_comparer(regions,entry,barrier):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','498b4020','488bd9','488bfa','488b88c0000000','488b4108','4883782000');g.branch('0f84',False);g.take('488d4b10','48897b10','488b5c2430','4883c420','5f')
 if g.relative('e9')!=barrier:raise ValueError('npcDictionary.comparer-ctor-barrier')
 return dict(selectedBytes=g.seen,storedUnchangedComparerOffset=16,inheritedConstructorContextSlot=1,normalReturnViaBarrier=True)

def list_formatter_constructor(regions,entry):
 g=BytesPath(regions,entry);g.take('4883ec28','488b4220','488b88c0000000','488b4138','4883782000');g.branch('0f84',False);g.take('4883c428','c3');return dict(selectedBytes=g.seen,inheritedConstructorContextSlot=7,explicitStores=0,normalReturn=True)

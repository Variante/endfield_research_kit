"""Current selected sparse CharInteract source-transfer programs."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
def tag_list(regions,entry,o,s,*,null=False,new=True):
 p,b,a,c,t=(bytes((o[k],)).hex()for k in('currentPtr','bufferLength','advancedCount','consumed','totalLength'));g=BytesPath(regions,entry);g.take('48895c2420','55','56','57','4155','4156','4883ec20','4533ed','498be9','837a'+b+'04','4d8bf0','488bfa','44896c2458');g.branch('0f8c',False);g.take('488b47'+p,'8b30','8b5f'+b,'83c3fc');g.branch('0f88',False);g.take('488347'+p+'04','8347'+a+'04','8347'+c+'04','895f'+b,'486347'+c,'488b4f'+t,'482bc8','4863c6','483bc8');g.branch('0f8c',False);g.take('83feff');g.branch('0f84',null);class_cell=None
 if null:g.take('498bce','4d892e');g.call(s['barrier'])
 else:
  g.take('4c89642450','4c897c2460','4d392e');g.branch('0f85',not new)
  if new:
   g.take('488b4d20','33d2','488b89c0000000');g.call(s['indexed']);g.take('488bc8');g.call(s['allocate']);g.take('488bd8','4885c0');g.branch('0f84',False);g.take('488b4d20','488b91c0000000','488b4a08','4c396920');g.branch('0f84',False);g.take('85f6');g.branch('0f88',False);g.take('488b4520','488b88c0000000','4c8b7908','498b4720','488b88c0000000');g.branch('0f85',False);g.take('33d2');g.call(s['indexed']);g.take('4439a8e0000000');g.branch('0f84',False);g.take('498b4f20','33d2','488b89c0000000');g.call(s['indexed']);g.take('488b88b8000000','488b01','488d4b10','48894310');g.call(s['barrier']);g.take('498bce','49891e');g.call(s['barrier'])
  else:
   g.take('488b4520','498b1e','488b88c0000000','488b4110','4c396820');g.branch('75',True,1);g.take('ff431c','44896b18');g.jump('e9')
  class_cell=g.relative('488b0d');g.take('4439a9e0000000');g.branch('0f84',False);g.take('488b4520','488b88c0000000','488b4918');g.call(s['provider']);g.take('4c8bf8','458be5','85f6');g.branch('7f',False,1);g.take('4c8b642450','4c8b7c2460')
 g.take('488b5c2468','4883c420','415e','415d','5f','5e','5d','c3')
 return dict(selectedBytes=g.seen,count=-1 if null else 0,new=new,wireBytes=4,elementCallbacks=0,reader='same incoming RDX saved RDI',output='same incoming R8 saved R14',providerClassCell=class_cell,normalReturn=True,condition='Sufficient buffered nonwrapping Reader bounds, initialized coherent current GameplayTag class contexts, normal disjoint typed allocation and context/provider/barrier helpers preserving Win64 nonvolatile registers. Zero-path typed empty-array context and constructor ABI only; runtime contents/effects and positive lists excluded.')

def entry_setter(regions,entry,barrier):
 g=BytesPath(regions,entry);g.take('4883ec28','488b4910','4885c9');g.branch('74',False,1);g.take('48895110','4883c110','4883c428')
 if g.relative('e9')!=barrier:raise ValueError('charEntry.setter-barrier')
 return dict(selectedBytes=g.seen,holder=16,field=16,unchangedReference=True,normalReturn=True)

def entry_caller(regions,entry,s,*,new=True,null=False):
 g=BytesPath(regions,entry);g.take('48895c2418','56','4883ec20');g.relative('803d');g.take('00','488bda','488bf1');g.branch('74',False,1);g.take('488d542430','c644243000','488bce');g.call(s['header']);g.take('84c0');g.branch('0f84',null);allocation=None;usage=None
 if null:g.take('488bcb','48c70300000000');g.call(s['barrier']);g.take('90');g.jump('e9')
 else:
  g.take('48897c2438','48833b00');g.branch('0f84',new)
  if new:
   site=g.at;cell=g.relative('488b0d');allocation=dict(site=site,cell=cell);g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('0f84',False);g.take('33d2','488bc8');g.call(s['ctor']);g.take('488bcb','48893b');g.call(s['barrier']);g.take('90');g.jump('e9')
  g.take('0fb67c2430','4080ff01');g.branch('0f85',False);site=g.at;cell=g.relative('488b15');usage=dict(site=site,cell=cell);g.take('488bce','488b1b');g.call(s['packable']);g.take('4885db');g.branch('74',False,1);g.take('4533c0','488bd0','488bcb');g.call(s['setter']);g.take('488b7c2438')
 g.take('488b5c2440','4883c420','5e','c3');return dict(selectedBytes=g.seen,new=new,null=null,memberCount=1,allocation=allocation,typedDictionaryUsage=usage,sameReaderAndOutput=True,normalReturn=True)


def read_value_transfer(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48894c2408','53','55','56','57','4154','4155','4156','4157','4883ec68','488bda','488bf9','48837a3800');g.branch('0f84',False);g.take('48c78424c000000000000000');provider_cell=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False);g.take('488b4338','488b28','48837d3800');g.branch('0f84',False);g.take('488b5d38','488b1b');type_cell=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False);g.take('4885db');g.branch('0f84',False);g.take('83b9e000000000');g.branch('0f84',False);g.take('b201','488bcb');g.call(s['classFromType']);g.take('4c8d6020');cache=g.relative('488b1d');g.take('488b8b80000000');enter=g.relative('ff15');g.take('90','488b4340','483b4338');g.branch('0f84',False);g.take('4533ed','4c8b7348','49ffce','498bcc');g.call(s['hash']);g.take('488bf8','488b7368','448b7b50','4923fe','488d0c7f','443b3cce');g.branch('75',True,1);g.take('48837b3800');g.branch('0f87',False);g.take('488d047f','833cc600');g.branch('0f85',False);g.take('488b54c608','498bcc');g.call(s['compare']);g.take('85c0');g.branch('0f85',False);g.take('4883ffff');g.branch('0f84',False);g.take('488d0c7f','488d14ce','488b4348','488d0c40','488b4368','488d0cc8','483bd1');g.branch('0f84',False);g.take('488b4a10','488b4370','4c8b34c8','488b8b80000000');leave=g.relative('ff15');g.take('90','488bbc24b0000000')
 if g.relative('488b0d')!=provider_cell:raise ValueError('charReadValue.same-provider-class')
 g.take('83b9e000000000');g.branch('0f84',False);ready=g.relative('803d');g.take('00');g.branch('0f84',False)
 if g.relative('488b0d')!=provider_cell:raise ValueError('charReadValue.same-provider-class')
 g.take('83b9e000000000');g.branch('0f84',False);g.take('498bce');g.call(s['formatterResult']);g.take('488bd8','ba01000000','488b4d38');g.call(s['indexed']);g.take('4885db');g.branch('74',False,1);g.take('488bd0','488b0b');g.call(s['assignable']);g.take('84c0');g.branch('74',False,1);g.take('b905000000','4c8d8c24c0000000','4c8bc7','488bd3');g.call(s['dispatch']);g.take('488b8424c0000000','4883c468','415f','415e','415d','415c','5f','5e','5d','5b','c3')
 return dict(selectedBytes=g.seen,providerClassCell=provider_cell,typeClassCell=type_cell,cacheCell=cache,monitorEnter=enter,monitorLeave=leave,readyFlag=ready,reader='entry RCX saved unchanged at entry RSP+8, restored via frame RSP+176 into RDI, forwarded to slot5 R8',output='zeroed full eight-byte frame local RSP+192 passed as slot5 R9, unchanged complete local returned in RAX',directCursorStores=0,normalReturn=True,condition='Exact selected initialized context/cache branch states and compatible nonnull formatter result with declared coherent type/context/pointer selection; normal disjoint noninterfering helpers preserving Win64 nonvolatile/frame ABI. Cache/provider/runtime effects and live selection, other branch states, anonymous-clone equivalence and child wire grammar excluded.')


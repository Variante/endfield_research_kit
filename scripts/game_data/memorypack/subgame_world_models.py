"""Selected current WorldChallenge wire and typed holder source transfers."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def world(regions,entry,s,plan,*,existing=False,null=False):
 if len(plan)!=36:raise ValueError('subgame.world-member-domain')
 g=BytesPath(regions,entry);g.take('48895c2408','55','56','57','488bec','4883ec30');g.relative('803d');g.take('00','488bda','488bf9');g.branch('0f85',True);g.take('488b0b','c6452800','4885c9');g.branch('74',not existing,1)
 if existing:g.take('33d2');g.call(s['prehook'])
 g.take('488d5528','488bcf');g.call(s['header']);g.take('84c0');g.branch('0f84',null);usages=[];allocation=None;collector=None
 if null:
  collector=g.relative('833d');g.take('00','48c70300000000');g.branch('74',True,1)
 else:
  g.take('48833b00');g.branch('75',existing,1)
  if not existing:
   site=g.at;cell=g.relative('488b0d');allocation=dict(site=site,cell=cell);g.call(s['allocate']);g.take('488bf0','4885c0');g.branch('0f84',False);g.take('33d2','488bc8');g.call(s['ctor']);collector=g.relative('833d');g.take('00','488933');g.branch('74',True,1)
  g.take('807d2824');g.branch('0f85',False)
  for i,kind in enumerate(plan):
   last=i==35
   if kind=='lang':
    site=g.at;cell=g.relative('4c8b05');usages.append(dict(member=i,site=site,cell=cell,readerRegister='rdx',output='rbp-16',outputBytes=16));g.take('488d4df0','488b33','488bd7')
   elif kind in('enum','list','area'):
    site=g.at;cell=g.relative('488b15');usages.append(dict(member=i,site=site,cell=cell,readerRegister='rcx'));g.take('488bcf','488b1b'if last else'488b33')
   else:g.take('488b33','488bcf')
   g.call(s['reads'][i]);g.take('4885db'if last else'4885f6');g.branch('74'if last else'0f84',False,1 if last else 4)
   if kind=='lang':g.take('0f2845f0','488d55f0','4533c0','660f7f45f0','488bce')
   else:g.take('4533c0','8ad0'if kind=='bool'else'8bd0'if kind in('int','enum')else'488bd0','488bcb'if last else'488bce')
   g.call(s['setters'][i])
  g.jump('eb',1)
 g.take('488b5c2450','4883c430','5f','5e','5d','c3')
 return dict(selectedBytes=g.seen,existing=existing,null=null,typedUsages=usages,allocation=allocation,collectorDisabledCell=collector,memberCount=36,hiddenResultStack='same disjoint RBP-16 sixteen-byte slot forwarded unchanged to three LangKey setters',sameReader=True,entryRspRestored=True,condition='Initialized metadata, matching generated route/closed typed contexts, normal source/callback/helper ABI, disjoint stable storage, sufficient buffer and collector disabled; runtime provider/default and gameplay behavior separate.')

def owned_scalar(regions,entry,getter,*,slot,width):
 if width not in(1,8)or not 0<=slot<2**31:raise ValueError('subgame.owned-scalar-domain')
 g=BytesPath(regions,entry);g.take('4053','4883ec20','0fb6da'if width==1 else'488bda','33d2');g.call(getter);g.take('4885c0');g.branch('75'if width==1 else'74',width==1,1);g.take(('8898'if width==1 else'488998')+slot.to_bytes(4,'little').hex(),'4883c420','5b','c3')
 return dict(selectedBytes=g.seen,slot=slot,width=width,unchangedIncomingValue=True)

def factory(regions,entry,s,*,ctor=False):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');g.relative('803d');g.take('00','488bf9');g.branch('75',True,1);base_usage=None
 if ctor:site=g.at;cell=g.relative('488b0d');base_usage=dict(site=site,cell=cell);g.call(s['baseReady'])
 site=g.at;cell=g.relative('488b0d');allocation=dict(site=site,cell=cell);g.call(s['allocate']);g.take('4885c0');g.branch('75',True,1);g.take('4533c0','488bd0','488bcf');g.call(s['instanceSetter']);g.take('488b5f10');usages=[]
 for i in range(2):
  site=g.at;cell=g.relative('488b15');usages.append(dict(site=site,cell=cell));g.take('488bcb')if i==0 else None;g.call(s['cast']);g.take('48894718','488bcb')if i==0 else None
 if usages[0]['cell']!=usages[1]['cell']or allocation['cell']!=usages[0]['cell']:raise ValueError('subgame.factory-same-class')
 g.take('488d4f18','488b5c2430','4883c420','5f')
 if g.relative('e9')!=s['barrier']:raise ValueError('subgame.factory-barrier')
 return dict(selectedBytes=g.seen,baseClassUsage=base_usage,allocation=allocation,classUsages=usages,originalConstructorCalled=False,condition='Initialized ready class, successful zeroed exact original allocation, ordinary inherited instance setter and compatible same-reference casts; no constructor/default/runtime execution claim.')

def dual_holder(regions,entry,barrier):
 g=BytesPath(regions,entry);g.take('4883ec28','4c8bd1','48895118','4883c118','4c8bca');g.call(barrier);g.take('498d4a10','4d894a10','4883c428')
 if g.relative('e9')!=barrier:raise ValueError('subgame.holder-barrier')
 return dict(selectedBytes=g.seen,holderOffsets=[16,24],sameIncomingReference=True,condition='Valid disjoint coherent references; selected collector-disabled barrier preserves R9/R10.')

def base_scalar(rows,*,field,mode):
 from scripts.game_data.il2cpp.owned_partition import BranchGrammar
 value={'byte':'dl','dword':'edx','qword':'rdx'}.get(mode)
 if value is None or type(field)is not int or field<16:raise ValueError('subgame.base-scalar-domain')
 g=BranchGrammar(rows,label='subgame.baseScalar');g.take('sub rsp, 0x28','mov rax, [rcx+0x10]','test rax, rax');g.branch('jne','store');r=g.row();raw=bytes.fromhex(r['bytes']);at=int(r['va'],16)
 if len(raw)!=5 or raw[0]!=0xe8 or r['text']!=f'call {at+5+int.from_bytes(raw[1:],"little",signed=True):#x}':raise ValueError('subgame.scalar-null-call')
 g.take('int3');g.mark('store');g.take(f'mov [rax+{field:#x}], {value}','add rsp, 0x28','ret');g.finish();return dict(fieldOffset=field,storedBytes={'byte':1,'dword':4,'qword':8}[mode])

def base_reference(rows,*,field,barrier,wide=False):
 from scripts.game_data.il2cpp.owned_partition import BranchGrammar
 g=BranchGrammar(rows,label='subgame.baseReference');g.take('sub rsp, 0x28','mov rcx, [rcx+0x10]','test rcx, rcx');g.branch('jne','store');r=g.row();raw=bytes.fromhex(r['bytes']);at=int(r['va'],16)
 if len(raw)!=5 or raw[0]!=0xe8 or r['text']!=f'call {at+5+int.from_bytes(raw[1:],"little",signed=True):#x}':raise ValueError('subgame.reference-null-call')
 g.take('int3');g.mark('store')
 if wide:g.take('movups xmm0, [rdx]',f'movups [rcx+{field:#x}], xmm0')
 else:g.take(f'mov [rcx+{field:#x}], rdx')
 g.take(f'add rcx, {field:#x}','add rsp, 0x28');r=g.row();raw=bytes.fromhex(r['bytes']);at=int(r['va'],16)
 if len(raw)!=5 or raw[0]!=0xe9 or at+5+int.from_bytes(raw[1:],'little',signed=True)!=barrier:raise ValueError('subgame.reference-tail-barrier')
 g.finish();return dict(fieldOffset=field,storedBytes=16 if wide else 8,sameIncomingValue=True,nonserializedSecondReferencePreserved=wide)

def owned_reference(regions,entry,getter,barrier,*,slot):
 g=BytesPath(regions,entry);g.take('4053','4883ec20','488bda','33d2');g.call(getter);g.take('4885c0');g.branch('75',True,1);g.take('488d88'+slot.to_bytes(4,'little').hex(),'488998'+slot.to_bytes(4,'little').hex(),'4883c420','5b')
 if g.relative('e9')!=barrier:raise ValueError('subgame.owned-reference-barrier')
 return dict(selectedBytes=g.seen,fieldOffset=slot,storedBytes=8,sameIncomingValue=True)

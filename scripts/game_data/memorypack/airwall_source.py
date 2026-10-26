"""Selected current raw24 AirWall Param and MC10 action source paths."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def param(regions,entry,s,o,*,new=False,null=False):
 g=BytesPath(regions,entry);g.take('48895c2418','57','4883ec30');g.relative('803d');g.take('00','488bfa','488bd9');g.branch('0f84',False);g.take('488d542440','c644244000','488bcb');g.call(s['header']);g.take('84c0');g.branch('0f84',null);allocation=None
 if null:
  g.take('488bcf','48c70700000000');g.call(s['barrier']);g.take('90');g.jump('e9')
 else:
  g.take('4889742448','48833f00');g.branch('0f84',new)
  if new:
   site=g.at;cell=g.relative('488b0d');allocation=dict(site=site,cell=cell);g.call(s['allocate']);g.take('488bf0','4885c0');g.branch('0f84',False);g.take('33d2','488bc8');g.call(s['ctor']);g.take('488bcf','488937');g.call(s['barrier']);g.take('90');g.jump('e9')
  g.take('0fb6742440','4080fe04');g.branch('0f85',False)
  g.take('837b'+bytes((o['bufferLength'],24)).hex(),'488b37');g.branch('0f8c',False);g.take('488b43'+bytes((o['currentPtr'],)).hex(),'ba18000000','488bcb','0f1000','0f11442420','f20f104010','f20f11442440');g.call(s['advance']);g.take('4885f6');g.branch('0f84',False);g.take('488b4610','4885c0');g.branch('74',False,1);g.take('0f10442420','488bcb','0f114020','f20f10442440','f20f114030','488b37');g.call(s['integer']);g.take('4885f6');g.branch('74',False,1);g.take('4533c0','8bd0','488bce');g.call(s['idRef']);g.take('488b37','488bcb');g.call(s['integer']);g.take('4885f6');g.branch('74',False,1);g.take('4533c0','8bd0','488bce');g.call(s['paramSource']);g.take('488b3f','488bcb');g.call(s['path']);g.take('4885ff');g.branch('74',False,1);g.take('4533c0','488bd0','488bcf');g.call(s['pathSetter']);g.take('488b742448')
 g.take('488b5c2450','4883c430','5f','c3')
 return dict(selectedBytes=g.seen,new=new,null=null,wrapperAllocation=allocation,rawConstantBytes=0 if null else 24,constantTransfer='unchanged same24 bytes via disjoint stack16+8 into same original offsets32..55',sameReader=True,tail='two signed Int32 values and same pooled string result',normalReturn=True,condition='Initialized matching typed wrapper and coherent references; normal disjoint allocator/constructor/setter/pooled helper effects, sufficient buffer, disabled collector and ordinary Win64 preserved nonvolatile aliases; refill/error paths excluded.')


def constant_setter(regions,entry):
 g=BytesPath(regions,entry);g.take('4883ec28','488b4110','4885c0');g.branch('75',True,1);g.take('0f1002','f20f104a10','0f114020','f20f114830','4883c428','c3')
 return dict(selectedBytes=g.seen,sourceBytes=24,destinationOffset=32,returnVoid=True,transfer='same16+8 bytes from incoming RDX argument buffer into current wrapper.__instance.constValue; padding preserved')


def action(regions,entry,s,*,new=False,null=False):
 g=BytesPath(regions,entry);g.take('48895c2418','57','4883ec20');g.relative('803d');g.take('00','488bda','488bf9');g.branch('0f84',False);g.take('488b0b','c644243800','4885c9');g.branch('0f85',not new)
 if not new:g.take('33d2');g.call(s['prehook']);g.take('90');g.jump('e9')
 g.take('488d542438','488bcf');g.call(s['header']);g.take('84c0');g.branch('0f84',null);allocation=None;usages=[]
 if null:g.take('488bcb','48c70300000000');g.call(s['barrier']);g.take('90');g.jump('e9')
 else:
  g.take('4889742430','48833b00');g.branch('75',not new,1)
  if new:
   site=g.at;cell=g.relative('488b0d');allocation=dict(site=site,cell=cell);g.call(s['allocate']);g.take('488bf0','4885c0');g.branch('0f84',False);g.take('33d2','488bc8');g.call(s['ctor']);g.take('488bcb','488933');g.call(s['barrier'])
  g.take('0fb6742438','4080fe0a');g.branch('0f85',False)
  for i,kind in enumerate(('bool','int','bool','string','int','bool','bool','int','reference','reference')):
   last=i==9
   if kind=='reference' or i==4:site=g.at;cell=g.relative('488b15');usages.append(dict(member=i,site=site,cell=cell));g.take('488bcf','488b1b'if last else'488b33')
   else:g.take('488b33','488bcf')
   g.call(s['reads'][i]);g.take('4885db'if last else'4885f6');g.branch('0f84'if i<7 else'74',False,4 if i<7 else 1);g.take('4533c0','0fb6d0'if kind=='bool'else'8bd0'if kind=='int'else'488bd0','488bcb'if last else'488bce');g.call(s['setters'][i])
  g.take('488b742430')
 g.take('488b5c2440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,new=new,null=null,wrapperAllocation=allocation,typedUsages=usages,memberCount=10,normalReturn=True,condition='Initialized matching generated ActionBase route; coherent same Reader/output wrapper/original; normal current child/prehook/constructor/setter/barrier ABI and disjoint stable storage. Live provider/default choice and action execution remain separate.')


def action_getter(regions,entry,s,*,cached=False,same=False):
 if same and not cached:raise ValueError('airWall.getter-same-requires-cache')
 g=BytesPath(regions,entry);g.take('4053','4883ec20');g.relative('803d');g.take('00','488bd9');g.branch('74',False,1);g.take('48837b2000');g.branch('0f84',not cached)
 if cached:g.take('488b4310','48394320');g.branch('0f85',not same)
 usages=[]
 if not same:
  site=g.at;cell=g.relative('488b15');usages.append(dict(site=site,cell=cell));g.take('48897c2430','488b7b10','488bcf');g.call(s['cast']);g.take('48894320','488bcf');site=g.at;second=g.relative('488b15');usages.append(dict(site=site,cell=second))
  if cell!=second:raise ValueError('airWall.getter-class-cell')
  g.call(s['cast']);g.take('488d4b20');g.call(s['barrier']);g.take('488b7c2430');g.jump('e9')
 g.take('488b4320','4883c420','5b','c3');return dict(selectedBytes=g.seen,classUsages=usages,baseHolder=16,typedHolder=32,condition='Initialized exact typed class, matching compatible original reference, normal successful casts and barrier; equality returns unchanged base reference, refresh casts that same base reference.')


def action_setter(regions,entry,s,*,slot):
 if slot not in (208,216):raise ValueError('airWall.owned-reference-slot')
 g=BytesPath(regions,entry);g.take('4053','4883ec20','488bda','33d2');g.call(s['getter']);g.take('4885c0');g.branch('74',False,1);displacement=slot.to_bytes(4,'little').hex();g.take('488d88'+displacement,'488998'+displacement,'4883c420','5b')
 if g.relative('e9')!=s['barrier']:raise ValueError('airWall.owned-reference-barrier')
 return dict(selectedBytes=g.seen,slot=slot,sameIncomingReferenceStored=True)


def dual_holder(regions,entry,barrier):
 g=BytesPath(regions,entry);g.take('4883ec28','4c8bd1','48895120','4883c120','4c8bca');g.call(barrier);g.take('498d4a10','4d894a10','4883c428')
 if g.relative('e9')!=barrier:raise ValueError('airWall.holder-barrier')
 return dict(selectedBytes=g.seen,holders=[16,32],sameIncomingReference=True,condition='Disabled collector current barrier preserves R9/R10, normal disjoint references.')


def prehook(regions,entry,s,*,cached=False,base_null=False):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','33db','488bf9');g.relative('381d');g.branch('75',True,1);g.take('48395f20');g.branch('75',cached,1);usages=[]
 if not cached:
  g.take('48395f10');g.branch('74',base_null,1)
  if not base_null:
   g.take('488b5f10');site=g.at;cell=g.relative('488b15');usages.append(dict(site=site,cell=cell));g.take('488bcb');g.call(s['cast']);g.take('48894720','488bcb');site=g.at;second=g.relative('488b15');usages.append(dict(site=site,cell=second))
   if cell!=second:raise ValueError('airWall.prehook-class-cell')
   g.call(s['cast']);g.take('488d4f20');g.call(s['barrier'])
 g.take('488b5c2430','4883c420','5f','c3');return dict(selectedBytes=g.seen,classUsages=usages,serializedWrites=0,condition='Initialized current metadata, coherent readable references; successful compatible casts and ordinary barrier.')


def factory(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');g.relative('803d');g.take('00','488bd9');g.branch('0f84',False);site=g.at;base_cell=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False);g.take('33d2','488bcb');g.call(s['baseCtor']);site=g.at;allocation=g.relative('488b0d');g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('74',False,1);g.take('33d2','488bc8');g.call(s['originalCtor']);g.take('4533c0','488bd7','488bcb');g.call(s['instanceSetter']);g.take('488b7b10');usages=[]
 for i in range(2):
  site=g.at;cell=g.relative('488b15');usages.append(dict(site=site,cell=cell));g.take('488bcf') if i==0 else None;g.call(s['factoryCast']);g.take('48894320','488bcf') if i==0 else None
 if usages[0]['cell']!=usages[1]['cell'] or allocation!=usages[0]['cell']:raise ValueError('airWall.factory-same-class-cell')
 g.take('488d4b20','488b5c2430','4883c420','5f')
 if g.relative('e9')!=s['barrier']:raise ValueError('airWall.factory-barrier')
 return dict(selectedBytes=g.seen,baseClassCell=base_cell,allocationCell=allocation,classUsages=usages,condition='Initialized ready exact base class, successful exact original allocation, normal base/original constructor effects and same-reference casts. Original defaults/runtime effects remain conditional; stored fields overwrite their serialized slots.')


def cast(regions,entry,predicate,*,strict=False):
 g=BytesPath(regions,entry)
 if strict:g.take('48895c2408','57','4883ec20','488bfa','488bd9','4885c9');g.branch('74',False,1);g.take('488b09');g.call(predicate);g.take('84c0');g.branch('74',False,1);g.take('488bc3','488b5c2430','4883c420','5f','c3')
 else:g.take('4053','4883ec20','488bd9','4885c9');g.branch('74',False,1);g.take('488b09');g.call(predicate);g.take('33c9','84c0','480f44d9','488bc3','4883c420','5b','c3')
 return dict(selectedBytes=g.seen,returnedReference='same nonnull incoming RCX object when current expected-class predicate succeeds',condition='Current compatible original reference; normal successful class predicate returns AL nonzero; other paths separate.')


def barrier(regions,entry):
 g=BytesPath(regions,entry);g.relative('833d');g.take('00','4c8bc1');g.branch('74',True,1);g.take('c3');return dict(selectedBytes=g.seen,preserves=['r9','r10','rbx','rsi','rdi'],condition='Collector-disabled flag is zero; no calls on this selected path.')

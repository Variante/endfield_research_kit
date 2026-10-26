"""Selected compiled pointer getter transfers; runtime selection is conditional."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def _flag(g):
 g.take('803d');cell=g.at+5+int.from_bytes(g.read(4),'little',signed=True);g.take('00');return cell

def getter(regions,entry,kind,*,field,source,context):
 if kind not in ('entity40','spawner8')or type(field)is not int or not 0<=field<128:raise ValueError('pointerGetter.scope')
 variants=[]
 for table_absent in (True,False):
  g=BytesPath(regions,entry);g.take('48895c2408')
  if kind=='entity40':g.take('4889742410','57','4881ec90000000');flag=_flag(g);g.take('498bf0','488bfa','488bd9')
  else:g.take('57','4883ec20');flag=_flag(g);g.take('488bfa','488bd9')
  g.branch('75',True,1);dispatch=g.relative('488b05')
  if kind=='entity40':
   g.take('488b5028','4885d2');g.branch('74',table_absent,1)
   if not table_absent:g.take('488b82');slot=int.from_bytes(g.read(4),'little',signed=True);g.take('4885c0');g.branch('74',True,1)
   g.take('488b57'+bytes((field,)).hex(),'4c8d442430','0f57c0','488d4c2460','33c0','0f29442430','4889842480000000')
   if g.relative('488b05')!=context:raise ValueError('pointerGetter.entity-context')
   g.take('0f29442440','f20f10842480000000','f20f11442450','4889442420');g.call(source)
   g.take('0f1000','4c8d9c2490000000','0f104810','498b7318','0f1103','f20f104020','488bc3','0f114b10','f20f114320','498b5b10','498be3','5f','c3')
  else:
   g.take('488b4828','4885c9');g.branch('74',table_absent,1)
   if not table_absent:g.take('488b81');slot=int.from_bytes(g.read(4),'little',signed=True);g.take('4885c0');g.branch('74',True,1)
   if g.relative('4c8b0d')!=context:raise ValueError('pointerGetter.spawner-context')
   g.take('41b001','488b4b'+bytes((field,)).hex(),'33d2');g.call(source);g.take('488b5c2430','4883c420','5f','c3')
  variants.append(dict(selectedBytes=g.seen,initializedFlag=flag,optionalDispatchCell=dispatch,dispatchTableAbsent=table_absent,callbackSlot=None if table_absent else slot))
 return dict(paths=variants,fieldOffset=field,outputBytes=40 if kind=='entity40'else 8,output='complete child hidden40 copied to original RCX and returned same RCX'if kind=='entity40'else'unchanged full child RAX',condition='Initialized metadata; original typed receiver; optional dispatch table or its callback entry absent; coherent current typed MethodInfo; compatible normal child return and disjoint stable storage. Live optional dispatch/patch selection remains unobserved.')

def entity_thunk(regions,entry,target):
 g=BytesPath(regions,entry);g.take('4053','4883ec60','410f1000','488b842490000000','41b101','410f104810','488bd9','4889442420','0f29442430','f2410f104020','4c8d442430','f20f11442450','0f294c2440');g.call(target);g.take('488bc3','4883c460','5b','c3')
 return dict(selectedBytes=g.seen,defaultBytes=40,forcedFlag=True,sameOutput=True,sameParameter=True,sameFifthMethodInfo=True,normalReturn='original output pointer',condition='Same coherent fifth MethodInfo at entry RSP+40, valid disjoint output/default storage and ordinary child ABI.')

def use_getter(regions,entry,source_offset):
 if type(source_offset)is not int or not 0<=source_offset<128:raise ValueError('pointerGetter.source-offset')
 g=BytesPath(regions,entry);b=bytes((source_offset,)).hex();g.take('8379'+b+'ff');g.branch('74',False,1);g.take('8379'+b+'fe');g.branch('74',False,1);g.take('32c0','c3')
 return dict(selectedBytes=g.seen,sourceOffset=source_offset,result=False,condition='Source word is zero, so neither -1 nor -2; initialized valid typed Param receiver.')

def get_value(regions,entry,kind,*,use,target):
 if kind not in('entity40','spawner8'):raise ValueError('pointerGetter.get-value-scope')
 g=BytesPath(regions,entry)
 if kind=='entity40':
  g.take('48895c2408','48896c2410','4889742418','48897c2420','4156','4883ec50','488bbc2480000000','410fb6e9','4d8bf0','488bf2','488bd9','48837f3800');g.branch('0f84',False)
  g.take('33c0','0f57c0','4889442440','0f11442420','0f11442430','4885f6');g.branch('0f84',False)
  g.take('488b4738','488b4808','4883792000');g.branch('0f84',False)
  g.take('488b5738','488bce','488b5208');g.call(use);g.take('84c0');g.branch('75',False,1)
  g.take('4c8b4f38','488d542420','440fb6c5','488bce','4d8b4910');g.call(target);g.take('84c0');g.branch('0f84',False)
  g.take('0f10442420','0f104c2430','0f1103','f20f10442440','488b6c2468','488bc3','488b742470','488b7c2478','0f114b10','f20f114320','488b5c2460','4883c450','415e','c3')
 else:
  g.take('48895c2410','48896c2418','4889742420','57','4883ec20','4983793800','498bf9','410fb6e8','488bda','488bf1');g.branch('75',True,1)
  g.take('48c744243000000000','4885f6');g.branch('74',False,1);g.take('488b4738','488b5008','48837a2000');g.branch('74',False,1)
  g.take('488b5738','488bce','488b5208');g.call(use);g.take('84c0');g.branch('0f85',False)
  g.take('4c8b4f38','488d542430','440fb6c5','488bce','4d8b4910');g.call(target);g.take('84c0');g.branch('74',False,1)
  g.take('488b442430','488b5c2438','488b6c2440','488b742448','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,outputBytes=40 if kind=='entity40'else 8,sameParameter=True,sameTypedChildContext=True,condition='Nonnull same Param, initialized coherent MethodInfo/RGCTX and ready Param class; separately proved useGetter returns false for source zero, selected TryGetValue returns true and writes complete value; valid stable disjoint output and normal ABI. Other sources, inflation and context selection remain separate.')

def try_constant(regions,entry,kind,*,barrier=None,is_const=None):
 if kind not in('entity40','spawner8'):raise ValueError('pointerGetter.try-constant-scope')
 g=BytesPath(regions,entry);g.take('48895c2418','4889542410','56','57','4154','4156','4157','4881ecd0000000','498bf9','450fb6f8','4c8bf2','488bd9'if kind=='entity40'else'488bf1','4983793800');g.branch('0f84'if kind=='entity40'else'0f85',kind=='spawner8')
 if kind=='entity40':
  g.take('33c0','4889842418010000','4889842400010000','0f57c0','0f118424a0000000','0f118424b0000000','48898424c0000000','4885db');g.branch('0f84',False)
  g.take('488b4738','488b4808','4883792000');g.branch('0f84',False);g.take('837b1000');g.branch('0f84',True)
  g.take('0f104b20','0f105330','f20f104340','410f110e','410f115610','f2410f114620','498d4e18');g.call(barrier);g.take('b001');g.jump('eb',1)
 else:
  g.take('33db','48899c2418010000','48899c2400010000','0f57c0','33c0','0f118424a0000000','0f118424b0000000','48898424c0000000','4885f6');g.branch('0f84',False)
  g.take('488b4738','488b4808','48395920');g.branch('0f84',False);g.take('488b5738','488b5208','488bce');g.call(is_const);g.take('84c0');g.branch('0f85',True)
  g.take('488b4620','498906');g.jump('e9');g.take('b001');g.jump('eb',1)
 g.take('488b9c2410010000','4881c4d0000000','415f','415e','415c','5f','5e','c3')
 return dict(selectedBytes=g.seen,sourceOffset=16,constantOffset=32,outputBytes=40 if kind=='entity40'else 8,returnsTrue=True,condition='Nonnull same typed Param with source zero; initialized coherent MethodInfo/RGCTX, ready selected class and stable disjoint output. Entity reference barrier uses separately proved disabled collector return; other source branches and live context selection remain separate.')

def is_const(regions,entry):
 g=BytesPath(regions,entry);g.take('83791000');g.branch('74',True,1);g.take('b001','c3')
 return dict(selectedBytes=g.seen,sourceOffset=16,result=True,condition='Valid same typed Param with source word zero.')

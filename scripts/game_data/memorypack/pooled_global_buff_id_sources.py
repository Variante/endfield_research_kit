"""Selected nominal managed8 programs; types and live selection stay independent."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def flag(g):g.relative('803d');g.take('00')

def parent_program(regions,entry,s,*,null=False,allocated=False):
 g=BytesPath(regions,entry);g.take('48895c2410','4889742418','57','4883ec20');flag(g);g.take('488bda','488bf1');g.branch('75',True,1);g.take('488d542430','c644243000','488bce');g.call(s['header']);g.take('84c0');g.branch('0f84',null);allocation=None;usage=None
 if null:g.take('488bcb','48c70300000000');g.call(s['barrier'])
 else:
  g.take('48833b00');g.branch('75',not allocated,1)
  if allocated:
   allocation=g.at;g.relative('488b0d');g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('0f84',False);g.take('33d2','488bc8');g.call(s['constructor']);g.take('488bcb','48893b');g.call(s['barrier'])
  g.take('807c243004');g.branch('0f85',False);usage=g.at;g.relative('488b15');g.take('488bce','488b3b');g.call(s['value']);g.take('4885ff');g.branch('74',False,1);g.take('4533c0','488bd0','488bcf');g.call(s['constValue'])
  for setter in('idRef','paramSource'):
   g.take('488b3b','488bce');g.call(s['integer']);g.take('4885ff');g.branch('74',False,1);g.take('4533c0','8bd0','488bcf');g.call(s[setter])
  g.take('488b1b','488bce');g.call(s['pool']);g.take('4885db');g.branch('74',False,1);g.take('4533c0','488bd0','488bcb');g.call(s['path']);g.jump('eb',1)
 g.take('488b5c2438','488b742440','4883c420','5f','c3');return dict(selectedBytes=g.seen,null=null,allocated=allocated,allocationUsageSite=allocation,valueUsageSite=usage,valueArgumentBytes=8,valueArgumentRegister='rdx',normalReturn=True)

def child_program(regions,entry,s,*,null=False,allocated=False):
 g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20');flag(g);g.take('488bda','488bf9');g.branch('74',False,1);g.take('488d542430','c644243000','488bcf');g.call(s['header']);g.take('84c0');g.branch('0f84',null);allocation=None
 if null:g.take('48c70300000000','488bcb');g.jump('e9')
 else:
  g.take('48833b00');g.branch('0f84',allocated)
  if allocated:
   allocation=g.at;g.relative('488b0d');g.call(s['allocate']);g.take('4885c0');g.branch('0f84',False);g.take('33c9','48894810','488bcb','488903');g.call(s['barrier']);g.take('90');g.jump('e9')
  g.take('807c243001');g.branch('0f85',False);g.take('488b1b','488bcf');g.call(s['pool']);g.take('4885db');g.branch('74',False,1);g.take('488d4b10','488901')
 g.take('488b5c2438','4883c420','5f')
 if g.relative('e9')!=s['barrier']:raise ValueError('globalKey.child-barrier')
 return dict(selectedBytes=g.seen,null=null,allocated=allocated,allocationUsageSite=allocation,keyFieldOffset=16,managedValueBytes=8,positivePoolIndexBytes=4,normalReturn=True)

def adapter_program(regions,entry,s,*,dispatch=False,null=False,create=True):
 g=BytesPath(regions,entry)
 if dispatch:
  g.take('48895c2408','4889742410','48897c2418','4156','4883ec20','488b0a','4d8bf1','498bf0','488bda');g.call(s['prepare']);g.take('488b3b')
  if g.relative('488d0d')!=s['adapter']:raise ValueError('globalKey.dispatch-canonical-target')
  g.take('488b8790010000','488bbf98010000','483bc1');g.branch('0f85',False);flag(g);g.branch('0f84',False)
 else:
  g.take('4889742410','48897c2418','4156','4883ec20');flag(g);g.take('498bf9','4d8bf0','488bf2');g.branch('0f84',False)
 g.take('488b4720','488bce','488b90c0000000','488b12');g.call(s['readNull']);g.take('84c0');g.branch('0f85',null)
 if null:g.take('33c0','498906');g.jump('e9')
 else:
  if not dispatch:g.take('48895c2430')
  g.take('488b4720');g.relative('488b0d');g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('74',False,1);g.take('33d2','488bcb');g.call(s['typeHandle'])
  if not dispatch:g.take('488b5c2430')
  g.take('4885c0');g.branch('74',False,1);g.take('33d2','488bc8');g.call(s['isAbstract']);g.take('84c0');g.branch('75',not create,1)
  if create:g.take('488b4720','488b88c0000000','488b4958');g.call(s['activate'])
  else:g.take('33c0');g.jump('eb',1)
  g.take('488b4f20','4c8bc0','498bd6','4c8b89c0000000','488bce','4d8b4918');g.call(s['nonnull'])
 if dispatch:g.take('488b5c2430')
 g.take('488b742438','488b7c2440','4883c420','415e','c3');return dict(selectedBytes=g.seen,dispatch=dispatch,null=null,create=create,outputBytes=8,sameIncomingReaderAndOutput=True,normalReturn=True)

def nonnull_program(regions,entry,s,*,null=False):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','4c89442418','57','4883ec20');flag(g);g.take('498bf9','488bf2','488bd9');g.branch('0f84',False);g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
 g.take('488b4f20');g.call(s['resolve']);g.take('488b88c0000000','488b4920');g.call(s['wrapperProvider']);g.take('4885c0');g.branch('0f84',False);g.take('b905000000','4c8d4c2440','4c8bc3','488bd0');g.call(s['wrapperInvoke']);g.take('488b5c2440','4885db');g.branch('74',null,1)
 if null:g.take('33c0','488906');g.jump('eb',1)
 else:g.take('488b4f20');g.call(s['resolve']);g.take('ba08000000','488b88c0000000');g.call(s['indexed']);g.take('488bd0','4c8bc3');g.call(s['conversion']);g.take('488bce','488906');g.call(s['barrier'])
 g.take('488b5c2430','488b742438','4883c420','5f','c3');return dict(selectedBytes=g.seen,null=null,outputBytes=8,output='unchanged RAX bits',normalReturn=True)

def conversion_program(regions,entry,s,*,ordinal):
 if type(ordinal)is not int or not 0<=ordinal<=4:raise ValueError('globalKey.interface-ordinal')
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','498b38','498bf0','488bcf','488bda');g.call(s['prepare']);g.take('440fb78730010000','33c0','66413bc0');g.branch('73',False,1);g.take('488b97b0000000')
 for i in range(ordinal+1):
  g.take('0fb7c8','4803c9','48391cca');g.branch('74',i==ordinal,1)
  if i<ordinal:g.take('66ffc0','66413bc0');g.branch('72',True,1)
 g.take('0fb7c8','4803c9','486344ca08','4883c014','48c1e004','4803c7','4c8b00','488bce','488b5008','488b5c2430','488b742438','4883c420','5f','49ffe0');return dict(selectedBytes=g.seen,interfaceOrdinal=ordinal,methodSlot=0,receiver='incoming R8',companion='matching GetValue MethodInfo',unchangedGetterRax=True)

def read_null_program(regions,entry,s,*,null=False):
 g=BytesPath(regions,entry);g.take('4053','4883ec20','488bd9','c644243000');g.call(s['peek']);g.take('84c0');g.branch('0f85',null)
 if null:g.take('488d542430','488bcb');g.call(s['header']);g.take('b001');g.jump('e9')
 g.take('4883c420','5b','c3');return dict(selectedBytes=g.seen,null=null,consumedBytes=int(null))

def provider_program(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20','4883793800','488bf9');g.branch('74',False,1);g.relative('488b0d');g.take('488b5f38','83b9e000000000','488b1b');g.branch('0f84',False);g.take('33d2','488bcb');g.call(s['typeHandle']);g.relative('488b0d');g.take('488bd8','83b9e000000000');g.branch('74',False,1);g.take('488bcb');g.call(s['backend']);g.take('488b4f38','ba01000000','488bd8');g.call(s['indexed']);g.take('488bd0','488bcb');g.call(s['cast']);g.take('4885c0');g.branch('0f84',False);g.take('488b5c2438','4883c420','5f','c3');return dict(selectedBytes=g.seen,keyContextSlot=0,resultTypeContextSlot=1,backendReceivesSameTypeObject=True,returnsCompatibleFullReference=True)

"""Initialized managed8 reader/provider equivalence, never pointer identity."""
def value8_program(regions,entry,s,*,canonical=False):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','48837a3800','488bda','488bf9');g.branch('75'if canonical else'74',canonical,1)
 cell=g.relative('488b0d');g.take('48c744243800000000')
 if canonical:g.call(s['classInit'])
 else:g.take('83b9e000000000');g.branch('74',False,1)
 g.take('488b4b38','488b09');g.call(s['provider']);g.take('4885c0');g.branch('74',False,1);g.take('4c8d4c2438','4c8bc7','488bd0');g.call(s['dispatch']);g.take('488b442438','488b5c2430','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,classCell=cell,providerContextSlot=0,outputBytes=8,output='same QWORD temporary returned unchanged in RAX',canonical=canonical)

def compared_provider(regions,entry,s,*,canonical=False):
 if not canonical:
  g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20','4883793800','488bf9');g.branch('74',False,1);type_cell=g.relative('488b0d');g.take('488b5f38','83b9e000000000','488b1b');g.branch('0f84',False);g.take('33d2','488bcb');g.call(s['typeHandle']);cell=g.relative('488b0d');g.take('488bd8','83b9e000000000');g.branch('74',False,1);g.take('488bcb');g.call(s['backend']);g.take('488b4f38','ba01000000','488bd8');g.call(s['indexed'])
 else:
  g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','4883793800','488bf9');g.branch('75',True,1);g.take('488b5f38');type_cell=g.relative('488b0d');g.take('488b1b');g.call(s['classInit']);g.take('33d2','488bcb');g.call(s['typeHandle']);cell=g.relative('488b0d');g.take('488bd8');g.call(s['classInit']);g.take('488bcb');g.call(s['backend']);g.take('488b4f38','488bd8','488b4908');g.call(s['context'])
 g.take('488bd0','488bcb');g.call(s['cast']);g.take('4885c0');g.branch('0f85'if canonical else'0f84',canonical)
 g.take('488b5c2430','488b742438')if canonical else g.take('488b5c2438')
 g.take('4883c420','5f','c3');return dict(selectedBytes=g.seen,typeClassCell=type_cell,providerClassCell=cell,typeContextSlot=0,resultTypeContextSlot=1,output='same compatible backend reference',canonical=canonical)

def backend_bridge(regions,entry,target):
 g=BytesPath(regions,entry);g.take('4053','4883ec20');flag(g);g.take('488bd9');g.branch('74',False,1);cell=g.relative('488b0d');g.take('83b9e000000000');g.branch('74',False,1);g.take('488bcb','4883c420','5b')
 if g.relative('e9')!=target:raise ValueError('globalBuffId.backend-tail-target')
 return dict(selectedBytes=g.seen,classCell=cell,sameTypeArgument=True,sameBackendReturn=True)

def successful_cast(regions,entry,assignable,*,null=False):
 g=BytesPath(regions,entry);g.take('4053','4883ec20','488bd9','4885c9');g.branch('74',null,1)
 if null:g.take('33c0')
 else:g.take('488b09');g.call(assignable);g.take('33c9','84c0','480f44d9','488bc3')
 g.take('4883c420','5b','c3');return dict(selectedBytes=g.seen,null=null,result='null if input null or predicate false, otherwise unchanged incoming full reference',predicateOutcomeProved=False)

def ready_class_init(regions,entry):
 g=BytesPath(regions,entry);g.take('4883ec28','83b9e000000000');g.branch('74',False,1);g.take('4883c428','c3');return dict(selectedBytes=g.seen,condition='incoming class initialized (+224 nonzero)',calleeCalls=0,argumentRegistersUnchanged=True)

"""Authenticate the distinct managed8 GlobalBuffId nominal source."""
import json,struct
from types import SimpleNamespace
from scripts.game_data.il2cpp.closed_leaf_entry import decode_closed_leaf_entry
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.formatter_composition import validate_registered_formatter_composition,validate_generic_contexts,validate_typed_usage_context
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param as primitive,pooled_source_helper,wrapper_members,reference_adapter_sources as reference,event_args_paths
from scripts.game_data.memorypack.reference_conversion_sources import validate_conversion_context
from scripts.game_data.memorypack.vector_layout import vector_recorder
VALUE='Beyond.Gameplay.Core.GlobalBuffId'
PARENT='Beyond.Gameplay.Actions.Param`1<'+VALUE+'>'

def validate_components(image,fact):
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);entries=GenericEntries(image);s={k:base+v for k,v in fact['symbols'].items()};methods=fact['methods'];regions={};programs={}
 def fail(k,e,a):raise ValueError(f'globalBuffId.{k}:expected={str(e)[:160]}:actual={str(a)[:160]}')
 for r in fact['programs']:
  pointer=base+r['entryRva'];windows=r['windows'];wanted=sorted((p['startRva'],p['endRva'])for p in windows)
  if r['leaf']:
   leaf=decode_closed_leaf_entry(image.mapper,image.pe.bytes_at_va(pointer,512),pointer);actual=[(pointer-base,max(int(z['va'],16)+len(bytes.fromhex(z['bytes']))for z in leaf['rows'])-base)]
  else:actual=sorted(tuple(p['runtimeTriple'][:2])for p in image.unwind_index.family(pointer-base)['ranges'])
  if actual!=wanted:fail('complete-owned-source',wanted,actual)
  image.check_windows(windows,label='globalBuffId');programs[r['entryRva']]=r;regions[pointer]=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in windows]
 for row in methods.values():image.validate_method_row(row,label='globalBuffId')
 for symbol,role in(('constructor','paramConstructor'),('constValue','paramConstSetter'),('idRef','paramIdSetter'),('paramSource','paramSourceSetter'),('path','paramPathSetter')):
  if fact['symbols'][symbol]!=methods[role][3]:fail('actual-named-parent-call',role,fact['symbols'][symbol])
 def args(role):
  pointer=base+methods[role][3];return regions[pointer],pointer
 wrappers={w.name:w for w in wrapper_members.derive_from_image(image).values()}
 for d in fact['declarations']:
  w=wrappers[d['wrapperName']]
  if w.wrapped_type!=d['typeName']or[(m.name,m.declared_type)for m in w.members]!=[(m['name'],m['typeName'])for m in d['members']]or ctx.field(w.name+'::__instance')!=(w.name,w.wrapped_type,16):fail('typed-wrapper',d,w.wrapped_type)
 if not ctx.is_value_type(VALUE)or ctx.is_value_type(PARENT):fail('value-reference-ABIs','value8 and reference Param','different')
 td=ctx.index.types[VALUE];fields=[list(ctx.field(VALUE+'::'+md.string(f.name_index)))for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16];sizes=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
 if fields!=[[VALUE,'string',16]]or[md.string(f.name_index)for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]!=['id']or(image.pe.u32_at_va(sizes),image.pe.u32_at_va(sizes+4))!=(24,8):fail('owned-managed8-id','one id:string,8 managed bytes',fields)
 offsets=scalar.reader_offsets(image,'globalBuffId')
 if offsets!=dict(currentPtr=80,bufferLength=48,advancedCount=64,consumed=68):fail('owned-reader-offsets','reviewed current fields',offsets)
 for role in('keyRead','paramRead'):
  m=md.methods[methods[role][0]];primitive.reader_abi(image,ctx,m,SimpleNamespace(name=methods[role][1]))
 getter=md.methods[methods['keyGetValue'][0]];scalar.owned_method_abi(image,ctx,getter.index,getter.declaring_type,(VALUE,17,False),[],'globalBuffId.getter')
 if image.pe.bytes_at_va(base+methods['keyGetValue'][3],5)!=bytes.fromhex('488b4110c3'):fail('RAX-managed8-getter','complete +16 QWORD load/RET',methods['keyGetValue'])
 for role in('keyConstructor','keyCreateInstance'):
  m=md.methods[methods[role][0]];scalar.owned_method_abi(image,ctx,m.index,m.declaring_type,('void',1,False),[],'globalBuffId.default')
  if image.pe.bytes_at_va(base+methods[role][3],7)!=bytes.fromhex('33c048894110c3'):fail('zero-managed8-default','QWORD zero +16/RET',methods[role])
 allocated={}
 for role,fn in(('keyRead',child_program),('paramRead',parent_program)):
  for new in(False,True):
   result=fn(*args(role),s,allocated=new)
   if new:allocated[role]=result['allocationUsageSite']-base
   if role=='paramRead'and result['valueUsageSite']-base!=fact['typedValueUsage']['instructionRva']:fail('actual-typed-read-context',fact['typedValueUsage']['instructionRva'],result)
  fn(*args(role),s,null=True)
 for role,usage in fact['holderAllocations'].items():
  validate_typed_usage_context(image,usage,label='globalBuffId')
  if usage['instructionRva']!=allocated[role]or usage['typeName']!=methods[role][1]or usage['tag']!=1:fail('typed-holder-allocation',role,usage)
 if set(allocated)!=set(fact['holderAllocations']):fail('all-holder-allocation-sites',set(allocated),set(fact['holderAllocations']))
 usage=fact['typedValueUsage'];validate_typed_usage_context(image,usage,label='globalBuffId')
 if(usage['typeName'],usage['methodName'],usage['classArguments'],usage['methodArguments'])!=('MemoryPack.MemoryPackReader','ReadValue',[],[VALUE]):fail('typed-value8-read','ReadValue<GlobalBuffId>',usage)
 closed=image.instantiations.resolve(usage['methodSpec'][2]).arguments
 if len(closed)!=1:fail('closed-value-arity',1,len(closed))
 scalar.ordinary(image,closed[0].type_pointer_va,17,'globalBuffId.actualClosedValue')
 read_method=md.methods[usage['methodSpec'][0]];section=md.sections['genericContainers'];at=section.offset+read_method.generic_container_index*16
 if read_method.generic_container_index<0 or not section.offset<=at<=section.offset+section.size-16:fail('reader-container','owned MVAR0',at)
 owner,count,is_method,parameter=struct.unpack_from('<iiii',md.buf,at);returned=image.pe.bytes_at_va(ctx.type_pointer(read_method.return_type),16)
 if(owner,count,is_method)!=(read_method.index,1,1)or returned[10:12]!=bytes((30,0))or int.from_bytes(returned[:8],'little')!=parameter or read_method.flags&16 or read_method.parameter_count:fail('ReadValue-return-owned-MVAR','instance noargs returns own MVAR0',read_method.index)
 for index,row in enumerate(fact['entries']):
  if index>=2:
   m=md.methods[row['definition']];expected=('Deserialize','DeserializeNotNull','ReadIsNull')[index-2]
   if(image.type_name(m.declaring_type),md.string(m.name_index),row['classArguments'],row['methodArguments'])!=('Beyond.MemoryPack.GenericMemoryPackFormatter`2',expected,[VALUE,'object'],[]):fail('value8-adapter-registration',expected,row)
  actual=entries.resolve(row['definition'],row['classArguments'],row['methodArguments'])
  if json.loads(json.dumps(actual))!=row['registration']:fail('current-generic-registration',row,actual)
 if[(r['classArguments'],r['methodArguments'])for r in fact['entries'][:2]]!=[([],[VALUE])]*2:fail('nominal-registrations','GlobalBuffId arguments',fact['entries'][:2])
 for r,owner,name in zip(fact['entries'][:2],('MemoryPack.MemoryPackReader','MemoryPack.MemoryPackFormatterProvider'),('ReadValue','GetFormatter'),strict=True):
  m=md.methods[r['definition']]
  if(image.type_name(m.declaring_type),md.string(m.name_index))!=(owner,name):fail('typed-method-definitions',(owner,name),r['definition'])
 if(s['registeredValue'],s['registeredProvider'])!=tuple(r['registration']['pointer']for r in fact['entries'][:2]):fail('registered-entries','current nominal targets',s)
 actual=value8_program(regions[s['value']],s['value'],s);canonical=value8_program(regions[s['registeredValue']],s['registeredValue'],s,canonical=True)
 if actual['classCell']!=canonical['classCell']:fail('same-reader-class-cell',canonical['classCell'],actual['classCell'])
 actual=compared_provider(regions[s['provider']],s['provider'],s);canonical=compared_provider(regions[s['registeredProvider']],s['registeredProvider'],s,canonical=True)
 if any(actual[k]!=canonical[k]for k in('typeClassCell','providerClassCell')):fail('same-provider-class-cells',canonical,actual)
 ready_class_init(regions[s['classInit']],s['classInit']);backend_bridge(regions[s['backend']],s['backend'],s['backendTail'])
 for null in(False,True):successful_cast(regions[s['cast']],s['cast'],s['assignable'],null=null)
 event_args_paths.peek(regions[s['peek']],s['peek'],offsets)
 contexts=fact['contexts']
 for context in contexts:
  slots={e['relativeSlot']:e for e in context['entries']};definition=context['definition']
  def mvar(arg):return arg.get('parameterOwner',{}).get('methodIndex')==definition and arg['parameterOwner'].get('ordinal')==0
  if context['methodName']=='ReadValue':
   if set(slots)!={0,1,2}or(slots[0]['typeName'],slots[0]['methodName'],slots[2]['typeName'],slots[2]['methodName'])!=('MemoryPack.MemoryPackFormatterProvider','GetFormatter','MemoryPack.MemoryPackFormatter`1','Deserialize')or not mvar(slots[0]['methodArguments'][0])or not mvar(slots[1]['type']['classArguments'][0])or not mvar(slots[2]['classArguments'][0]):fail('ReadValue-owned-MVAR-context','provider/formatter/Deserialize for own MVAR0',context)
  elif context['methodName']=='GetFormatter':
   if set(slots)!={0,1}or not mvar(slots[0]['type'])or slots[1]['type']['definition']['name']!='MemoryPack.MemoryPackFormatter`1'or not mvar(slots[1]['type']['classArguments'][0]):fail('provider-owned-MVAR-context','type and formatter for own MVAR0',context)
  else:fail('unexpected-method-context','ReadValue/GetFormatter',context['methodName'])
 rec=vector_recorder(image);primitive.object_header_source(image,rec(s['header']-base),offsets);scalar.integer_source(image,rec(s['integer']-base),offsets,'globalBuffId.integer');pooled_source_helper.validate_on_image(image,s['pool'],fact['nativeInputs'])
 own={}
 for name,role in(('.ctor','paramConstructor'),('CreateInstance','paramCreateInstance'),('set___constValue__','paramConstSetter'),('set___idRef__','paramIdSetter'),('set___paramSource__','paramSourceSetter'),('set___path__','paramPathSetter')):
  r=programs[methods[role][3]];own[name]=dict(instructions=[[int(z['va'],16)-base,bytes.fromhex(z['bytes']).hex()]for p in r['windows']for z in image.body_index._decode(base+p['startRva'],p['endRva']-p['startRva'])]);m=md.methods[methods[role][0]]
  if name in('.ctor','CreateInstance'):scalar.owned_method_abi(image,ctx,m.index,m.declaring_type,('void',1,False),[],'globalBuffId.paramDefault')
  else:
   field=name.removeprefix('set___').removesuffix('__');kind,decl=(17,VALUE)if field=='constValue'else(14,'string')if field=='path'else(8,'int');scalar.owned_method_abi(image,ctx,m.index,m.declaring_type,('void',1,False),[(decl,kind,field=='path')],'globalBuffId.setter');scalar.parameter_setter(image,own[name]['instructions'],name='path'if field=='constValue'else field,slot=fact['slots'][field],width=8 if field in('path','constValue')else 4,label='globalBuffId')
 occupied=[p for n,size in(('constValue',8),('idRef',4),('paramSource',4),('path',8))for p in range(fact['slots'][n],fact['slots'][n]+size)]
 if len(set(occupied))!=24 or any(not 16<=p<128 for p in occupied):fail('disjoint-owned-parent-fields','24 distinct bytes',fact['slots'])
 allocation=fact['parameterAllocation'];validate_typed_usage_context(image,allocation,label='globalBuffId')
 if allocation['typeName']!=PARENT:fail('original-allocation',PARENT,allocation)
 scalar.allocation_bridge(image,ctx,dict(methods=own,ownedFieldSlots=fact['slots'],allocationContext=allocation),'globalBuffId.factory')
 formatter=md.methods[methods['keyFormatter'][0]]
 if formatter.flags&16 or formatter.slot!=5 or formatter.parameter_count!=2:fail('formatter-instance-slot5',5,formatter.slot)
 scalar.ordinary(image,ctx.type_pointer(formatter.return_type),1,'globalBuffId.formatterVoid')
 for parameter,name,kind in zip(md.parameters_for(formatter),('MemoryPack.MemoryPackReader',methods['keyRead'][1]),(17,18),strict=True):
  raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
  if(ctx.type_name(parameter.type_index),raw[10],raw[11])!=(name,kind,32):fail('formatter-byref-ABI',(name,kind,32),raw.hex())
 for flow in fact['registrations']:validate_eager_wrap_registration(image,flow,label='globalBuffId')
 for composition in fact['compositions']:validate_registered_formatter_composition(image,composition,label='globalBuffId')
 if{c['registrations'][0]['originalType']for c in fact['compositions']}!={VALUE,PARENT}:fail('compositions','value and Param',fact['compositions'])
 child,=[c for c in fact['compositions']if c['registrations'][0]['originalType']==VALUE];interface,=child['interfaces'];owner=md.types[interface['wrapperDefinition']];section=md.sections['interfaceOffsets'];a=section.offset+owner.interface_offsets_start*8;pairs=list(struct.iter_unpack('<ii',md.buf[a:a+owner.interface_offsets_count*8]));ordinal=pairs.index((interface['interfaceTypeIndex'],interface['interfaceOffset']))
 if ordinal!=fact['interfaceOrdinal']or(interface['getValueMethodIndex'],interface['formatterDeserializeMethodIndex'])!=(methods['keyGetValue'][0],methods['keyFormatter'][0]):fail('actual-conversion-getter-formatter',fact['interfaceOrdinal'],interface)
 for dispatch in(False,True):
  entry=s['dispatch']if dispatch else s['adapter']
  for create in(False,True):adapter_program(regions[entry],entry,s,dispatch=dispatch,create=create)
  adapter_program(regions[entry],entry,s,dispatch=dispatch,null=True)
 for null in(False,True):nonnull_program(regions[s['nonnull']],s['nonnull'],s,null=null);read_null_program(regions[s['readNull']],s['readNull'],s,null=null)
 conversion_program(regions[s['conversion']],s['conversion'],s,ordinal=ordinal);validate_generic_contexts(image,fact['contexts'],label='globalBuffId');validate_conversion_context(image,fact['adapterContext'],entries,fail=fail)
 context=fact['adapterContext'];validate_generic_contexts(image,[context],label='globalBuffId');slots={e['relativeSlot']:e for e in context['entries']}
 if slots[7]['index']!=slots[10]['index']or(slots[7]['kind'],slots[10]['kind'])!=(2,1):fail('factory-wrapper-type','same owned VAR1',slots[10])
 for slot,owner,name,ordinals in((0,context['typeName'],'ReadIsNull',[0,1]),(3,context['typeName'],'DeserializeNotNull',[0,1]),(11,'System.Activator','CreateInstance',[1])):
  e=slots[slot];arguments=e['methodArguments']if slot==11 else e['classArguments']
  if e['kind']!=3 or(e['typeName'],e['methodName'])!=(owner,name)or[a['parameterOwner']['ordinal']for a in arguments]!=ordinals or any(a['parameterOwner']['typeIndex']!=context['definition']for a in arguments):fail('adapter-factory-context',slot,e)

 r=programs[methods['keyFormatter'][3]];rows=[z for p in r['windows']for z in image.body_index._decode(base+p['startRva'],p['endRva']-p['startRva'])];prove_zero_wrapper_forwarder(rows,{k:base+v for k,v in fact['forwarderSymbols'].items()},base+methods['keyRead'][3])
 parent,=[c for c in fact['compositions']if c['registrations'][0]['originalType']==PARENT];reference.validate_reference_routes(image,fact['referenceRoutes'],[parent]);ref={k:base+v for k,v in fact['referenceRoutes']['symbolRvas'].items()}
 if(s['wrapperProvider'],s['wrapperInvoke'],s['resolve'],s['indexed'],s['context'],s['backendTail'],s['assignable'])!=(ref['hotProvider'],ref['dispatch'],ref['context'],ref['indexed'],ref['context'],ref['backend'],ref['assignable']):fail('actual-shared-context-provider-source','same helper programs',s)
 from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
 deserialize_slot(regions[s['wrapperInvoke']],s['wrapperInvoke'],prepare=ref['prepare'],callback=base+methods['keyFormatter'][3])

 return dict(status='proved-current-selected-managed8',readerRegistrationPointerEqual=s['value']==s['registeredValue'],providerRegistrationPointerEqual=s['provider']==s['registeredProvider'],runtimeSelectionProved=False,wholeOwnerAdmitted=False)

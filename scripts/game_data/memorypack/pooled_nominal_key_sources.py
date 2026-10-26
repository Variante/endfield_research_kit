"""Selected nominal managed16 key programs; buffered input and normal helpers."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def flag(g,prefix='803d'):g.relative(prefix);g.take('00')

def lang_key(regions,entry,s,*,allocated=False,null=False,formatter=False):
 g=BytesPath(regions,entry)
 if formatter:
  g.take('48895c2408','48896c2418','4889742420','57','4883ec20');flag(g);g.take('498bf8','488bda');g.branch('75',True,1)
  g.relative('488b0d');g.take('83b9e000000000');g.branch('75',True,1);flag(g);g.branch('75',True,1)
 else:
  g.take('48895c2410','48896c2418','4889742420','57','4883ec20');flag(g);g.take('488bfa','488bd9');g.branch('75',True,1)
 g.take('837b3001');g.branch('7d',True,1);g.take('488b4350','0fb630' if formatter else '0fb628','8b6b30' if formatter else '8b7330','83ed01' if formatter else '83ee01');g.branch('79',True,1)
 g.take('48ff4350','ff4340','ff4344','896b30' if formatter else '897330','4080feff' if formatter else '4080fdff');g.branch('75',not null,1);allocation=None
 if null:g.take('488bcf','48c70700000000');g.call(s['barrier'])
 else:
  g.take('48833f00');g.branch('75',not allocated,1)
  if allocated:
   allocation=g.at;g.relative('488b0d');g.call(s['allocate']);g.take('4885c0');g.branch('0f84',False);g.take('0f57c0','488bcf','0f114010','488907');g.call(s['barrier'])
  g.take('4080fe01' if formatter else '4080fd01');g.branch('75',False,1);g.take('488b3f','488bcb');g.call(s['pool']);g.take('4885ff');g.branch('0f84',False);flag(g,'833d');g.take('488d5710','488902');g.branch('74',True,1)
 g.take('488b5c2430' if formatter else '488b5c2438','488b6c2440','488b742448','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,formatter=formatter,null=null,allocated=allocated,allocationUsageSite=allocation,memberCount=None if null else 1,serializedKeyBytes=0 if null else 4,managedValueBytes=16,keyOffset=16,newWrapperValueAllZero=allocated,unserializedRawTextOffset=24,normalReturn=True,sameReaderAndWrapperOutput=True)

def lang_param(regions,entry,s,*,allocated=False,null=False):
 g=BytesPath(regions,entry);g.take('48895c2418','57','4883ec30');flag(g);g.take('488bda','488bf9');g.branch('0f84',False)
 g.take('488d542440','c644244000','488bcf');g.call(s['header']);g.take('84c0');g.branch('0f84',null);allocation=None;usage=None
 if null:
  g.take('488bcb','48c70300000000');g.call(s['barrier']);g.take('90');g.jump('e9')
 else:
  g.take('4889742448','48833b00');g.branch('0f84',allocated)
  if allocated:
   allocation=g.at;g.relative('488b0d');g.call(s['allocate']);g.take('488bf0','4885c0');g.branch('0f84',False);g.take('33d2','488bc8');g.call(s['constructor']);g.take('488bcb','488933');g.call(s['barrier']);g.take('90');g.jump('e9')
  g.take('0fb6742440','4080fe04');g.branch('0f85',False);usage=g.at;g.relative('4c8b05');g.take('488d4c2420','488b33','488bd7');g.call(s['value16']);g.take('4885f6');g.branch('0f84',False)
  g.take('488b4e10','4885c9');g.branch('74',False,1);g.take('0f10442420','0f114120','4883c120');g.call(s['barrier'])
  for setter in ('idRef','paramSource'):
   g.take('488b33','488bcf');g.call(s['integer']);g.take('4885f6');g.branch('74',False,1);g.take('4533c0','8bd0','488bce');g.call(s[setter])
  g.take('488b1b','488bcf');g.call(s['pool']);g.take('4885db');g.branch('74',False,1);g.take('4533c0','488bd0','488bcb');g.call(s['path']);g.take('488b742448')
 g.take('488b5c2450','4883c430','5f','c3')
 return dict(selectedBytes=g.seen,null=null,allocated=allocated,allocationUsageSite=allocation,valueUsageSite=usage,memberCount=None if null else 4,constValueCopyBytes=16,ownedConstValueOffset=32,sameIncomingReader=True,normalReturn=True)

def lang_const_setter(regions,entry,barrier):
 g=BytesPath(regions,entry);g.take('4883ec28','488b4910','4885c9');g.branch('74',False,1);g.take('0f1002','0f114120','4883c120','4883c428')
 if g.relative('e9')!=barrier:raise ValueError('nominalKey.const-setter-barrier')
 return dict(selectedBytes=g.seen,managedValueBytes=16,wrapperHolderOffset=16,ownedConstValueOffset=32,unchangedSourceBits=True)

def lang_default(regions,entry):
 g=BytesPath(regions,entry);g.take('0f57c0','0f114110','c3');return dict(selectedBytes=g.seen,holderOffset=16,zeroedBytes=16)

def lang_getter(regions,entry):
 g=BytesPath(regions,entry);g.take('0f104210','488bc1','0f1101','c3');return dict(selectedBytes=g.seen,holderOffset=16,outputBytes=16,hiddenOutputRegister='rcx',receiverRegister='rdx',returnedOutputRegister='rax',sourceBitsUnchanged=True)

"""Complete selected managed16/reference-wrapper adapters; typed owners are separate."""


def finish(g,main):
 if main:g.take('488b5c2450','488b7c2460','4883c430','415e','5e','5d','c3')
 else:g.take('488b5c2458','4883c430','5f','5e','5d','c3')

def convert(g,s,*,main,ordinal):
 if type(ordinal)is not int or not 0<=ordinal<=4:raise ValueError('value16Adapter.interface-ordinal')
 if main:
  g.take('498b2e','488bd8','488bcd');g.call(s['prepare']);g.take('0fb79530010000','663bfa');g.branch('73',False,1);g.take('488b8db0000000','0f1f4000','66660f1f840000000000')
 else:
  g.take('488b2e','488bf8','488bcd');g.call(s['prepare']);g.take('440fb78530010000','33c9','66413bc8');g.branch('73',False,1);g.take('488b95b0000000','6690')
 for i in range(ordinal+1):
  g.take('0fb7c7' if main else '0fb7c1','4803c0','48391cc1' if main else '48393cc2');g.branch('0f84',i==ordinal)
  if i<ordinal:g.take('66ffc7' if main else '66ffc1','663bfa' if main else '66413bc8');g.branch('72',True,1)
 if main:g.take('488b85b0000000','0fb7cf','4803c9','486344c808','4883c014','48c1e004','4803c5')
 else:g.take('0fb7c9','4803c9','486344ca08','4883c014','48c1e004','4803c5')
 g.jump('eb',1);g.take('4c8b08','488d4c2420','4c8b4008','498bd6' if main else '488bd6','41ffd1');flag(g,'833d');g.take('0f1000','0f1106' if main else '0f1103');g.branch('0f84' if main else '74',True,4 if main else 1)
 return dict(interfaceOrdinal=ordinal,hiddenOutputRegister='rcx',receiverRegister='rdx',methodInfoRegister='r8',copiedOutputBytes=16,collectorDisabled=True)

def main_program(regions,entry,s,*,null=False,create=True,wrapper_null=False,ordinal=1):
 g=BytesPath(regions,entry);g.take('4055','56','4156','4883ec30');flag(g);g.take('4d8bf1','498bf0','488bea');g.branch('75',True,1);g.take('837d3001','c644245800');g.branch('7d',True,1);g.take('488b4550','8038ff');g.branch('75',not null,1)
 if null:
  g.take('488d542458','488bcd');g.call(s['header']);g.take('0f57c0','0f1106','4883c430','415e','5e','5d','c3')
 else:
  g.take('48895c2450','48897c2460','498b4620');g.relative('488b0d');g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('75',True,1);g.take('33ff','4885db');g.branch('0f84',False);g.take('39b9e0000000');g.branch('75',True,1)
  g.take('488bcb');g.call(s['typeHandle']);g.take('4885c0');g.branch('0f84',False);g.take('b944000000','488bd0');g.call(s['typeFlags']);g.take('a980000000');g.branch('76',create,1)
  if create:g.take('498b4620','488b88c0000000','488b4958');g.call(s['activate'])
  else:g.take('488bc7');g.jump('eb',1)
  g.relative('40383d');g.take('498b4e20','4889442458','488b91c0000000','488b5a18');g.branch('75',True,1);g.relative('488b0d');g.take('39b9e0000000');g.branch('75',True,1)
  g.take('488b4b20');g.call(s['resolve']);g.take('488b88c0000000','488b4920');g.call(s['provider']);g.take('4885c0');g.branch('0f84',False);g.take('b905000000','4c8d4c2458','4c8bc5','488bd0');g.call(s['dispatch']);g.take('4c8b742458','4d85f6');g.branch('75',not wrapper_null,1)
  if wrapper_null:g.take('0f57c0','0f1106')
  else:
   g.take('488b4b20');g.call(s['resolve']);g.take('ba08000000','488b88c0000000');g.call(s['indexed']);convert(g,s,main=True,ordinal=ordinal)
  finish(g,True)
 return dict(selectedBytes=g.seen,null=null,create=create,wrapperNull=wrapper_null,outputBytes=16,normalReturn=True,sameIncomingReaderAndOutput=True)

def nonnull_program(regions,entry,s,*,wrapper_null=False,ordinal=1):
 g=BytesPath(regions,entry);g.take('48895c2410','4c89442418','55','56','57','4883ec30');flag(g);g.take('498be9','488bda','488bf1');g.branch('75',True,1);g.relative('488b0d');g.take('83b9e000000000');g.branch('75',True,1)
 g.take('488b4d20');g.call(s['resolve']);g.take('488b88c0000000','488b4920');g.call(s['provider']);g.take('4885c0');g.branch('0f84',False);g.take('b905000000','4c8d4c2460','4c8bc6','488bd0');g.call(s['dispatch']);g.take('488b742460','4885f6');g.branch('75',not wrapper_null,1)
 if wrapper_null:g.take('0f57c0','0f1103')
 else:
  g.take('488b4d20');g.call(s['resolve']);g.take('ba08000000','488b88c0000000');g.call(s['indexed']);convert(g,s,main=False,ordinal=ordinal)
 finish(g,False);return dict(selectedBytes=g.seen,wrapperNull=wrapper_null,outputBytes=16,sameIncomingReaderAndOutput=True,normalReturn=True)

def read_null_program(regions,entry,s,*,null=False):
 g=BytesPath(regions,entry);g.take('4053','4883ec20','83793001','488bd9','c644243000');g.branch('0f8c',False);g.take('488b4350','8038ff');g.branch('0f84',null)
 if null:g.take('488d542430','488bcb');g.call(s['header']);g.take('b001');g.jump('e9')
 else:g.take('32c0')
 g.take('4883c420','5b','c3');return dict(selectedBytes=g.seen,null=null,consumedBytes=int(null),normalReturn=True)

"""Authenticate the declared nominal-key source, never infer live selection."""
import json,struct
from types import SimpleNamespace
from scripts.game_data.il2cpp.closed_leaf_entry import decode_closed_leaf_entry
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import validate_registered_formatter_composition,validate_generic_contexts,validate_typed_usage_context
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param as primitive,pooled_source_helper,reference_adapter_sources as reference,wrapper_members
from scripts.game_data.memorypack.reference_conversion_sources import validate_conversion_context
from scripts.game_data.memorypack.vector_layout import vector_recorder
from scripts.game_data.levelscript_family_regenerate import Build

def validate_components(image,fact):
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);entries=GenericEntries(image);s={k:base+v for k,v in fact['symbols'].items()};w={k:base+v for k,v in fact['wideSymbols'].items()};programs={};regions={};methods=fact['methods']
 def fail(k,e,a):raise ValueError(f'nominalKey.{k}:expected={str(e)[:160]}:actual={str(a)[:160]}')
 for r in fact['programs']:
  pointer=base+r['entryRva'];windows=r['windows'];wanted=sorted((p['startRva'],p['endRva'])for p in windows)
  if r['leaf']:
   leaf=decode_closed_leaf_entry(image.mapper,image.pe.bytes_at_va(pointer,512),pointer);actual=[(pointer-base,max(int(z['va'],16)+len(bytes.fromhex(z['bytes']))for z in leaf['rows'])-base)]
  else:actual=sorted(tuple(p['runtimeTriple'][:2])for p in image.unwind_index.family(pointer-base)['ranges'])
  if actual!=wanted:fail('complete-owned-source',wanted,actual)
  image.check_windows(windows,label='nominalKey');programs[r['entryRva']]=r;regions[pointer]=[(base+p['startRva'],image.pe.bytes_at_va(base+p['startRva'],p['endRva']-p['startRva']))for p in windows]
 for row in methods.values():image.validate_method_row(row,label='nominalKey')
 for symbol,role in(('constructor','paramConstructor'),('idRef','paramIdSetter'),('paramSource','paramSourceSetter'),('path','paramPathSetter')):
  if fact['symbols'][symbol]!=methods[role][3]:fail('actual-named-parent-call',role,fact['symbols'][symbol])
 def args(role):
  pointer=base+methods[role][3];return regions[pointer],pointer
 wrappers={r.name:r for r in wrapper_members.derive_from_image(image).values()}
 if not ctx.is_value_type('Beyond.LangKey') or ctx.is_value_type('Beyond.Gameplay.Actions.Param`1<Beyond.LangKey>'):fail('value-reference-ABIs','value16 key and reference Param','different')
 allocations={}
 for d in fact['declarations']:
  actual=wrappers[d['wrapperName']]
  if actual.wrapped_type!=d['typeName'] or [(m.name,m.declared_type)for m in actual.members]!=[(m['name'],m['typeName'])for m in d['members']] or ctx.is_value_type(d['typeName'])!=d['valueType'] or ctx.field(d['wrapperName']+'::__instance')!=(d['wrapperName'],d['typeName'],16):fail('typed-wrapper',d['typeName'],actual.wrapped_type)
 fields=[list(ctx.field('Beyond.LangKey::'+md.string(f.name_index)))for f in md.fields_for(ctx.index.types['Beyond.LangKey'])if not ctx.field_attributes(f.type_index)&16]
 if fields!=[['Beyond.LangKey','string',16],['Beyond.LangKey','string',24]]:fail('managed16-reference-fields','key and nonserialized rawText',fields)
 if [md.string(f.name_index)for f in md.fields_for(ctx.index.types['Beyond.LangKey'])if not ctx.field_attributes(f.type_index)&16]!=['key','<rawText>k__BackingField']:fail('field-identities','key,rawText',fields)
 td=ctx.index.types['Beyond.LangKey'];sizes=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
 if(image.pe.u32_at_va(sizes),image.pe.u32_at_va(sizes+4))!=(32,16):fail('managed16-size',(32,16),sizes)
 offsets=scalar.reader_offsets(image,'nominalKey')
 if offsets!=dict(currentPtr=80,bufferLength=48,advancedCount=64,consumed=68):fail('reader-owned-offsets','source profile fields',offsets)
 for role in ('keyRead','paramRead'):
  m=md.methods[methods[role][0]];primitive.reader_abi(image,ctx,m,SimpleNamespace(name=methods[role][1]))
 getter=md.methods[methods['keyGetValue'][0]];scalar.owned_method_abi(image,ctx,getter.index,getter.declaring_type,('Beyond.LangKey',17,False),[],'nominalKey.getter')
 for role in ('keyConstructor','keyCreateInstance'):
  m=md.methods[methods[role][0]];scalar.owned_method_abi(image,ctx,m.index,m.declaring_type,('void',1,False),[],'nominalKey.default');lang_default(*args(role))
 lang_getter(*args('keyGetValue'));m=md.methods[methods['paramConstSetter'][0]];scalar.owned_method_abi(image,ctx,m.index,m.declaring_type,('void',1,False),[('Beyond.LangKey',17,False)],'nominalKey.constSetter');lang_const_setter(*args('paramConstSetter'),s['barrier'])
 formatter=md.methods[methods['keyFormatter'][0]];parameters=list(md.parameters_for(formatter))
 if formatter.flags&16 or formatter.slot!=5 or len(parameters)!=2:fail('formatter-instance-slot5',5,formatter.slot)
 scalar.ordinary(image,ctx.type_pointer(formatter.return_type),1,'nominalKey.formatterVoid')
 for p,name,kind in zip(parameters,('MemoryPack.MemoryPackReader',methods['keyRead'][1]),(17,18),strict=True):
  raw=image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16)
  if(ctx.type_name(p.type_index),raw[10],raw[11])!=(name,kind,32):fail('formatter-byref-ABI',(name,kind,32),raw.hex())
 for formatter in (False,True):
  role='keyFormatter'if formatter else'keyRead'
  for allocated in (False,True):
   result=lang_key(*args(role),s,allocated=allocated,formatter=formatter)
   if allocated:allocations[role]=result['allocationUsageSite']-base
  lang_key(*args(role),s,null=True,formatter=formatter)
 parent_paths=[]
 for allocated in (False,True):
  result=lang_param(*args('paramRead'),s,allocated=allocated);parent_paths.append(result)
  if allocated:allocations['paramRead']=result['allocationUsageSite']-base
 lang_param(*args('paramRead'),s,null=True)
 for role,usage in fact['holderAllocations'].items():
  validate_typed_usage_context(image,usage,label='nominalKey.holder')
  if usage['instructionRva']!=allocations[role] or usage['typeName']!=methods['keyRead'if role=='keyFormatter'else role][1] or usage['tag']!=1:fail('typed-holder-allocation',role,usage)
 if set(allocations)!=set(fact['holderAllocations']):fail('complete-holder-allocation-sites',set(allocations),set(fact['holderAllocations']))
 usage=fact['typedValueUsage'];validate_typed_usage_context(image,usage,label='nominalKey')
 if any(r['valueUsageSite']-base!=usage['instructionRva'] for r in parent_paths):fail('actual-value-reader-context',usage['instructionRva'],parent_paths)
 if(usage['typeName'],usage['methodName'],usage['classArguments'],usage['methodArguments'])!=('MemoryPack.MemoryPackReader','ReadValue',[],['Beyond.LangKey']):fail('typed-hidden-output-16-read','ReadValue<LangKey>',usage)
 Build(image,fact['nativeInputs']).prove_named_target(s['value16'],'MemoryPack.MemoryPackReader','ReadValue',result_abi='hidden-output-16')
 rec=vector_recorder(image);primitive.object_header_source(image,rec(s['header']-base),offsets);scalar.integer_source(image,rec(s['integer']-base),offsets,'nominalKey.integer');pooled_source_helper.validate_on_image(image,s['pool'],fact['nativeInputs'])
 own={}
 for name,role in (('.ctor','paramConstructor'),('CreateInstance','paramCreateInstance'),('set___idRef__','paramIdSetter'),('set___paramSource__','paramSourceSetter'),('set___path__','paramPathSetter')):
  if name in ('.ctor','CreateInstance'):
   m=md.methods[methods[role][0]];scalar.owned_method_abi(image,ctx,m.index,m.declaring_type,('void',1,False),[],'nominalKey.paramFactory')
  r=programs[methods[role][3]];own[name]=dict(instructions=[[int(z['va'],16)-base,bytes.fromhex(z['bytes']).hex()]for p in r['windows']for z in image.body_index._decode(base+p['startRva'],p['endRva']-p['startRva'])])
 for name,role,kind,decl in (('idRef','paramIdSetter',8,'int'),('paramSource','paramSourceSetter',8,'int'),('path','paramPathSetter',14,'string')):
  scalar.parameter_setter(image,own['set___'+name+'__']['instructions'],name=name,slot=fact['slots'][name],width=8 if name=='path'else 4,label='nominalKey');m=md.methods[methods[role][0]];scalar.owned_method_abi(image,ctx,m.index,m.declaring_type,('void',1,False),[(decl,kind,name=='path')],'nominalKey.setter')
 occupied=[p for n,size in (('constValue',16),('idRef',4),('paramSource',4),('path',8))for p in range(fact['slots'][n],fact['slots'][n]+size)]
 if fact['slots']['constValue']!=32 or len(set(occupied))!=32 or any(not 16<=p<128 for p in occupied):fail('disjoint-parent-slots','32 distinct owned bytes',fact['slots'])
 allocation=fact['parameterAllocation'];validate_typed_usage_context(image,allocation,label='nominalKey')
 if allocation['typeName']!='Beyond.Gameplay.Actions.Param`1<Beyond.LangKey>':fail('allocated-original','Param<LangKey>',allocation)
 scalar.allocation_bridge(image,ctx,dict(methods=own,ownedFieldSlots=fact['slots'],allocationContext=allocation),'nominalKey.factory')
 for flow in fact['registrations']:validate_eager_wrap_registration(image,flow,label='nominalKey')
 for composition in fact['compositions']:validate_registered_formatter_composition(image,composition,label='nominalKey')
 if{c['registrations'][0]['originalType']for c in fact['compositions']}!={'Beyond.LangKey','Beyond.Gameplay.Actions.Param`1<Beyond.LangKey>'}:fail('complete-compositions','key and Param',fact['compositions'])
 generic={}
 for name,r in fact['wideEntries'].items():
  m=md.methods[r['definition']]
  if image.type_name(m.declaring_type)!='Beyond.MemoryPack.GenericMemoryPackFormatter`2'or md.string(m.name_index)!=name:fail('wide-adapter-definition',name,r['definition'])
  actual=entries.resolve(r['definition'],['Beyond.LangKey','object'],[])
  if json.loads(json.dumps(actual))!=r['registration']:fail('wide-adapter-registration',r['registration'],actual)
  generic[name]=actual['pointer']
 child,=[c for c in fact['compositions']if c['registrations'][0]['originalType']=='Beyond.LangKey'];interface,=child['interfaces']
 if(interface['getValueMethodIndex'],interface['formatterDeserializeMethodIndex'],interface['wrapperType'])!=(methods['keyGetValue'][0],methods['keyFormatter'][0],methods['keyRead'][1]):fail('selected-concrete-getter-formatter',interface,methods['keyFormatter'])
 owner=md.types[interface['wrapperDefinition']];section=md.sections['interfaceOffsets'];a=section.offset+owner.interface_offsets_start*8;pairs=list(struct.iter_unpack('<ii',md.buf[a:a+owner.interface_offsets_count*8]));ordinal=pairs.index((interface['interfaceTypeIndex'],interface['interfaceOffset']))
 if ordinal!=fact['interfaceOrdinal']:fail('wide-conversion-interface-ordinal',fact['interfaceOrdinal'],ordinal)
 for create in(False,True):
  for null in(False,True):main_program(regions[generic['Deserialize']],generic['Deserialize'],w,create=create,wrapper_null=null,ordinal=ordinal)
 main_program(regions[generic['Deserialize']],generic['Deserialize'],w,null=True,ordinal=ordinal)
 for null in(False,True):nonnull_program(regions[generic['DeserializeNotNull']],generic['DeserializeNotNull'],w,wrapper_null=null,ordinal=ordinal);read_null_program(regions[generic['ReadIsNull']],generic['ReadIsNull'],w,null=null)
 context=fact['adapterContext'];validate_generic_contexts(image,[context],label='nominalKey');validate_conversion_context(image,context,entries,fail=fail)
 parent,=[c for c in fact['compositions']if c['registrations'][0]['originalType']=='Beyond.Gameplay.Actions.Param`1<Beyond.LangKey>'];reference.validate_reference_routes(image,fact['referenceRoutes'],[parent])
 ref={k:base+v for k,v in fact['referenceRoutes']['symbolRvas'].items()}
 if(w['provider'],w['dispatch'],w['resolve'],w['indexed'],w['header'])!=(ref['hotProvider'],ref['dispatch'],ref['context'],ref['indexed'],s['header']):fail('shared-typed-helper-composition','same actual provider/context/dispatcher/header',w)
 from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
 deserialize_slot(regions[w['dispatch']],w['dispatch'],prepare=ref['prepare'],callback=base+methods['keyFormatter'][3])

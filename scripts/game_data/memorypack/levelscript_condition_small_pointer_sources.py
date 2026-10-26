"""Own LsmPtr and ScriptTaskPtr MC1 values and canonical eight-byte results.

The two explicit nominal layouts select different wire fields: UInt64 id and
pooled string key. Complete getters/defaults and canonical value conversions
are proved independently. Their equal managed widths imply no wire, callback
or pointer equivalence, and this component admits no list or Param parent.
"""
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.levelscript_condition_param_sources import need

LSM='Beyond.Gameplay.Core.LsmPtr'
TASK='Beyond.Gameplay.Core.ScriptTaskPtr'
SPECS={LSM:('id','ulong',11,8),TASK:('key','string',14,4)}
SCHEMA='endfield.story-condition-small-pointer-value-sources.v1'


def _call(source,offset):
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 rows=[r for r in source['rows']if int(r['va'],16)==source['pointer']+offset]
 if len(rows)!=1:
  actual=[int(r['va'],16)-source['pointer']for r in source['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8']
  raise ValueError('smallPointer.one-owned-call:expectedOffset='+str(offset)+':actualCallOffsets='+str(actual[:16]))
 raw=bytes.fromhex(rows[0]['bytes']);need('exact-owned-small-pointer-call',len(raw)==5 and raw[0]==232)
 return control_transfer(rows[0])['target']


def wrapper_program(regions,entry,s,*,type_name,new=False,null=False):
 need('small-pointer-literal-wrapper-path',type_name in SPECS and type(new)is bool and type(null)is bool and not(new and null))
 reference=type_name==TASK;g=BytesPath(regions,entry)
 g.take('48895c2410','57','4883ec20');flag=g.relative('803d');g.take('00','488bda','488bf9');g.branch('75',True,1)
 g.take('488d542430','c644243000','488bcf');g.call(s['header']);g.take('84c0');g.branch('0f84'if reference else'74',null,4 if reference else 1)
 allocation=None
 if null:g.take('488bcb','48c70300000000');g.call(s['barrier'])
 else:
  g.take('48833b00');g.branch('75',not new,1)
  if new:
   site=g.at;cell=g.relative('488b0d');g.call(s['allocate']);g.take('4885c0');g.branch('74',False,1)
   g.take('33c9','48894810','488bcb','488903');g.call(s['barrier']);allocation=dict(instruction=site,cell=cell)
  g.take('807c243001');g.branch('75',False,1);g.take('488b1b','488bcf');g.call(s['value']);g.take('4885db');g.branch('75',True,1)
  if reference:g.take('4533c0','488bd0','488bcb');g.call(s['setter'])
  else:g.take('48894310')
  g.jump('eb',1)
 g.take('488b5c2438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,typeName=type_name,newWrapper=new,wrapperNull=null,metadataReadyFlag=flag,
  allocation=allocation,managedBytes=8,wireBytes=1 if null else 1+SPECS[type_name][3],
  serializedField=None if null else SPECS[type_name][0],defaultOriginalAdmitted=False,
  entryRspRestored=True,allIntegerNonvolatilesRestored=True,normalReturn=True)


def adapter_program(regions,entry,s,*,null=False,create=True):
 need('small-pointer-literal-canonical-path',type(null)is bool and type(create)is bool)
 g=BytesPath(regions,entry)
 g.take('488bc4','48895808','48896810','48897018','48897820','4156','4883ec20','33ff','498bf1')
 ready=g.relative('40383d');g.take('4d8bf0','488bea');g.branch('75',True,1)
 g.take('488b4620','488bcd','488b90c0000000','488b12');g.call(s['readNull']);g.take('84c0');g.branch('75',null,1)
 cell=None
 if null:g.take('33c0','498906')
 else:
  g.take('488b4620');cell=g.relative('488b0d');g.take('488b98c0000000','488b5b50');g.call(s['classInit'])
  g.take('33d2','488bcb');g.call(s['typeHandle']);g.take('4885c0');g.branch('75',True,1)
  g.take('33d2','488bc8');g.call(s['creationTest']);g.take('84c0');g.branch('75',not create,1)
  if create:
   g.take('488b4620','488b88c0000000','488b4958');g.call(s['activate']);g.take('488bf8')
  g.take('488b4e20','4c8bc7','498bd6','4c8b89c0000000','488bcd','4d8b4918');g.call(s['nonnull']);g.jump('eb',1)
 g.take('488b5c2430','488b6c2438','488b742440','488b7c2448','4883c420','415e','c3')
 return dict(selectedBytes=g.seen,metadataReadyFlag=ready,typeClassCell=cell,null=null,create=None if null else create,
  outputBytes=8,defaultZeroBytes=8 if null else 0,sameIncomingReaderAndOutput=True,
  entryRspRestored=True,allIntegerNonvolatilesRestored=True,normalReturn=True)


def nonnull_program(regions,entry,s,*,type_name,wrapper_null=False):
 need('small-pointer-literal-nonnull-path',type_name in SPECS and type(wrapper_null)is bool)
 reference=type_name==TASK;g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','4c89442418','57','4883ec20');ready=g.relative('803d')
 g.take('00','498bf1','488bda','488bf9');g.branch('75',True,1)
 provider=g.relative('488b0d');g.call(s['classInit']);g.take('488b4e20');g.call(s['resolve'])
 g.take('488b88c0000000','488b4920');g.call(s['wrapperProvider']);g.take('4885c0');g.branch('75',True,1)
 g.take('b905000000','4c8d4c2440','4c8bc7','488bd0');g.call(s['wrapperInvoke'])
 g.take('488b7c2440','4885ff');g.branch('75',not wrapper_null,1)
 if wrapper_null:
  g.take('33c0')
  if reference:g.take('488903')
  g.jump('eb',1)
 else:
  g.take('488b4e20');g.call(s['resolve']);g.take('488b88c0000000','488b4940');g.call(s['resolve'])
  g.take('33c9','4c8bc7','488bd0');g.call(s['conversion'])
  if reference:g.take('488bcb','488903');g.call(s['barrier'])
 if not reference:g.take('488b742438','488903','488b5c2430')
 else:g.take('488b5c2430','488b742438')
 g.take('4883c420','5f','c3')
 return dict(selectedBytes=g.seen,typeName=type_name,metadataReadyFlag=ready,providerClassCell=provider,
  wrapperNull=wrapper_null,outputBytes=8,defaultZeroBytes=8 if wrapper_null else 0,
  wholeGetterRaxStored=True,referenceBarrierSelected=reference and not wrapper_null,
  entryRspRestored=True,allIntegerNonvolatilesRestored=True,normalReturn=True)


def conversion_program(regions,entry,*,prepare,ordinal):
 """Actual matched interface path with the caller's explicit zero selector."""
 need('small-pointer-own-interface-ordinal',type(ordinal)is int and 0<=ordinal<=8)
 g=BytesPath(regions,entry)
 g.take('48895c2408','48896c2410','4889742418','57','4883ec20','498b38','498bd8','0fb7e9','488bf2','488bcf')
 g.call(prepare);g.take('0fb79730010000','4533c9','66443bca');g.branch('73',False,1)
 g.take('488b8fb0000000')
 for index in range(ordinal+1):
  g.take('410fb7c1','4803c0','483934c1');g.branch('74',index==ordinal,1)
  if index<ordinal:g.take('6641ffc1','66443bca');g.branch('72',True,1)
 g.take('410fb7d1','4803d2','8b44d108','03c5','4898','4883c014','48c1e004','4803c7');g.jump('eb',1)
 g.take('4c8b00','488bcb','488b5008','488b5c2430','488b6c2438','488b742440','4883c420','5f','49ffe0')
 return dict(selectedBytes=g.seen,interfaceOrdinal=ordinal,selector='low UInt16 CX; actual caller supplies zero',
  wrapper='incoming R8, unchanged complete object reference',interface='incoming RDX',
  completeGetterRaxPreserved=True,entryRspRestored=True,allIntegerNonvolatilesRestored=True,
  normalReturnViaOwnedGetter=True,unmatchedInterfaceFallbackAdmitted=False)


def read_null_program(regions,entry,s,*,null=False):
 need('small-pointer-literal-null-test',type(null)is bool)
 g=BytesPath(regions,entry);g.take('4053','4883ec20','488bd9','c644243000');g.call(s['peek'])
 g.take('84c0');g.branch('75',null,1)
 if null:g.take('488d542430','488bcb');g.call(s['header']);g.take('b001')
 else:g.jump('eb',1)
 g.take('4883c420','5b','c3')
 return dict(selectedBytes=g.seen,null=null,consumedBytes=1 if null else 0,sameIncomingReader=True,
  entryRspRestored=True,allIntegerNonvolatilesRestored=True,normalReturn=True)


def derive(image,pins,*,type_name):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
 from scripts.game_data.memorypack import pointer_param as pointer,primitive_param,scalar_param_native as scalar
 from scripts.game_data.memorypack import pooled_source_helper,pooled_global_buff_id_sources as common,buff_ptr_sources,event_args_paths
 from scripts.game_data.memorypack.skill_root_value_sources import value_layout
 from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.vector_layout import vector_recorder
 need('exact-small-pointer-domain',type_name in SPECS)
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image)
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==type_name]
 field,decl,kind,width=SPECS[type_name]
 need('own-small-pointer-member',[(m.name,m.declared_type)for m in wrapper.members]==[(field,decl)])
 layout=value_layout(image,ctx,type_name,wrapper,managed_bytes=8,fields={field:(decl,kind,8)})
 mm=pointer.methods(image,wrapper);primitive_param.reader_abi(image,ctx,mm['Deserialize'],wrapper)
 scalar.owned_method_abi(image,ctx,mm['GetValue'].index,wrapper.type_definition,(type_name,17,False),[],'smallPointer.getter')
 getter=pointer.leaf(image,image.method_pointer_va(mm['GetValue']),['488B4110','C3']);defaults={}
 for name in('.ctor','CreateInstance'):
  scalar.owned_method_abi(image,ctx,mm[name].index,wrapper.type_definition,('void',1,False),[],'smallPointer.default')
  defaults[name]=pointer.leaf(image,image.method_pointer_va(mm[name]),['33C0','48894110','C3'])
 pair=derive_pair(image,type_name,wrapper.name);forward=pointer.registered_pair(image,pair,wrapper,label='smallPointer.registration')
 body=pointer.owned(image,image.method_pointer_va(mm['Deserialize']));sources={'wrapper':body};s={}
 call=_call
 def add(role,pointer_):sources[role]=pointer.owned(image,pointer_);return sources[role]
 def selected_call(previous,following=None):
  rows=body['rows'];selected=[control_transfer(row)['target']for i,row in enumerate(rows)
   if i and i+1<len(rows)and len(bytes.fromhex(row['bytes']))==5 and bytes.fromhex(row['bytes'])[0]==232
   and rows[i-1]['text']==previous and(following is None or rows[i+1]['text']==following)]
  need('one-owned-small-pointer-helper:'+previous,len(set(selected))==1);return selected[0]
 allocation_load=next(r['text']for r in body['rows']if r['text'].startswith('mov rcx, [rip'))
 s.update(header=selected_call('mov rcx, rdi','test al, al'),
  allocate=selected_call(allocation_load,'test rax, rax'),
  barrier=selected_call('mov [rbx], rax'),value=selected_call('mov rcx, rdi','test rbx, rbx'))
 if type_name==TASK:s['setter']=image.method_pointer_va(mm['set___key__'])
 wrapper_paths=[wrapper_program(body['regions'],body['pointer'],s,type_name=type_name,**p)for p in({},{'new':True},{'null':True})]
 allocation=derive_typed_usage_context(image,wrapper_paths[1]['allocation']['instruction']-base,label='smallPointer.allocation')
 need('own-small-pointer-wrapper-allocation',(allocation['tag'],allocation['typeName'])==(1,wrapper.name))
 offsets=scalar.reader_offsets(image,'smallPointer');header=vector_recorder(image)(s['header']-base)
 primitive_param.object_header_source(image,header,offsets)
 if type_name==TASK:
  value=pooled_source_helper.validate_on_image(image,s['value'],pins)
  setter=image.method_pointer_va(mm['set___key__']);need('own-key-setter-target',setter==s['setter'])
  scalar.owned_method_abi(image,ctx,mm['set___key__'].index,wrapper.type_definition,('void',1,False),[('string',14,True)],'smallPointer.key')
  raw=image.pe.bytes_at_va(setter,12);g=BytesPath([(setter,raw)],setter);g.take('4883c110','488911')
  need('own-key-setter-barrier',g.relative('e9')==s['barrier']);setter_proof=dict(entryRva=setter-base,selectedBytes=g.seen)
 else:
  value=vector_recorder(image)(s['value']-base)
  scalar.integer_source(image,value,offsets,'smallPointer.id',width=8)
  setter_proof=pointer.leaf(image,image.method_pointer_va(mm['set___id__']),['48895110','C3'])
 barrier,barrier_proof,_=_fast_barrier(image,s['barrier'])
 face,=pair['composition']['interfaces'];owner=md.types[wrapper.type_definition];section=md.sections['interfaceOffsets']
 at=section.offset+owner.interface_offsets_start*8
 ordinal=list(struct.iter_unpack('<ii',md.buf[at:at+owner.interface_offsets_count*8])).index((face['interfaceTypeIndex'],face['interfaceOffset']))
 context,context_proof=buff_ptr_sources._adapter_context(image,ge);registrations={}
 for role,name in(('adapter','Deserialize'),('nonnull','DeserializeNotNull'),('readNull','ReadIsNull')):
  method=buff_ptr_sources._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2',name)
  row=ge.resolve(method.index,[type_name,'object'],[]);registrations[role]=row;s[role]=row['pointer'];add(role,row['pointer'])
 for role,offset in dict(readNull=81,classInit=112,typeHandle=122,creationTest=143,activate=167,nonnull=199).items():
  actual=call(sources['adapter'],offset)
  if role in s:need('same-canonical-small-pointer-helper:'+role,s[role]==actual)
  s[role]=actual
 need('own-named-TypeFromHandle',s['typeHandle']==base+pair['registration']['helperMethods']['typeFromHandle'][3])
 type_usage=derive_typed_usage_context(image,s['adapter']-base+94,label='smallPointer.adapterTypeClass')
 need('own-adapter-System-Type-class',(type_usage['tag'],type_usage['typeName'])==(1,'System.Type'))
 abstract=buff_ptr_sources._definition(image,'System.Type','get_IsAbstract')
 need('own-creation-predicate-helper',s['creationTest']==image.method_pointer_va(abstract))
 activator=context['entries'][11]
 need('owned-Activator-context-slot',activator['relativeSlot']==11 and activator['methodName']=='CreateInstance')
 selected_activation=ge.resolve(activator['methodSpec'][0],[],['object'])
 need('actual-selected-reference-Activator-source',s['activate']==selected_activation['pointer'])
 for role,offset in dict(resolve=73,wrapperProvider=89,wrapperInvoke=121,conversion=176 if type_name==TASK else 173).items():
  s[role]=call(sources['nonnull'],offset)
 need('same-closed-nonnull-context-resolver',s['resolve']==call(sources['nonnull'],147 if type_name==TASK else 144))
 need('same-own-wrapper-barrier',type_name!=TASK or s['barrier']==call(sources['nonnull'],187))
 for role in('classInit','conversion','wrapperInvoke'):add(role,s[role])
 s['prepare']=call(sources['conversion'],35)
 s['peek']=call(sources['readNull'],14);add('peek',s['peek'])
 ff=BytesPath(sources['readNull']['regions'],s['readNull']+21).relative('75',1)
 need('same-wrapper-null-header',BytesPath(sources['readNull']['regions'],ff+8).relative('e8')==s['header'])
 paths=dict(adapter=[adapter_program(sources['adapter']['regions'],s['adapter'],s,**p)for p in({},{'create':False},{'null':True})],
  nonnull=[nonnull_program(sources['nonnull']['regions'],s['nonnull'],s,type_name=type_name,wrapper_null=n)for n in(False,True)],
  conversion=conversion_program(sources['conversion']['regions'],s['conversion'],prepare=s['prepare'],ordinal=ordinal),
  readNull=[read_null_program(sources['readNull']['regions'],s['readNull'],s,null=n)for n in(False,True)],
  peek=event_args_paths.peek(sources['peek']['regions'],s['peek'],offsets),
  classInit=common.ready_class_init(sources['classInit']['regions'],s['classInit']),
  wrapperInvocation=deserialize_slot(sources['wrapperInvoke']['regions'],s['wrapperInvoke'],prepare=s['prepare'],
   callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']])))
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-small-pointer-value',nativeInputs=pins,
  typeName=type_name,wrapperName=wrapper.name,managedBytes=8,positiveWireBytes=1+width,nullWireBytes=1,defaultZeroBytes=8,
  fieldName=field,fieldType=decl,layout=layout,getter=getter,defaults=defaults,registeredPair=pair,forwarder=forward,
  wrapperPaths=wrapper_paths,allocation=allocation,valueSource=value,setter=setter_proof,header=header,barrier=barrier,
  barrierProof=barrier_proof,registrations=registrations,adapterContext=context,adapterContextProof=context_proof,
  typeClassUsage=type_usage,selectedActivationSource=selected_activation,
  interfaceOrdinal=ordinal,paths=paths,symbolRvas={k:v-base for k,v in s.items()},
  sourceWindows={k:v['windows']for k,v in sources.items()},sourceRegions={k:[[a,b.hex().upper()]for a,b in v['regions']]for k,v in sources.items()},
  actualCallbackEqualsCanonicalRequired=True,closedPointerEquivalenceProved=False,runtimeSelectionObserved=False,
  actualWrapperCallbackEqualsProvedWrapperRequired=True,coherentTypedContextsRequired=True,
  normalMatchingProviderAndAllocationEffectsRequired=True,
  parentFieldAdmitted=False,positiveCollectionAdmitted=False,wholeOwnerAdmitted=False)))

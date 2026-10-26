"""Current canonical managed16 adapter and nominal wrapper conversion.

This component owns a selected canonical callback, not a live provider choice.
Its input MethodInfo must be the coherent closed adapter for the independently
registered Original/wrapper pair. The wrapper wire grammar and enclosing caller
remain separate obligations. Managed size supplies no serialized width.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath,deserialize_slot
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.skill_root_tag_query_transfer import adapter16_program

LABEL='managedValue16'

def need(key,condition,detail=None):
 if not condition:raise ValueError(LABEL+'.'+key+':'+str(detail)[:700])

def nonnull_program(regions,entry,s,*,ordinal,reference_lane,wrapper_null=False):
 """Full inline interface conversion with an explicit native reference lane."""
 need('literal-null',type(wrapper_null)is bool)
 need('interface-bound',type(ordinal)is int and 0<=ordinal<=16)
 need('reference-lane',type(reference_lane)is int and reference_lane in(0,8))
 g=BytesPath(regions,entry)
 g.take('48895c2410','48896c2420','4c89442418','57','4883ec30');ready=flag(g)
 g.take('498bd9','488bea','488bf9');g.branch('0f84',False)
 provider=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
 g.take('488b4b20');g.call(s['resolve']);g.take('488b88c0000000','488b4920');g.call(s['wrapperProvider'])
 g.take('4885c0');g.branch('0f84',False)
 g.take('b905000000','4889742440','4c8d4c2450','4c8bc7','488bd0');g.call(s['wrapperInvoke'])
 g.take('488b742450','4885f6');g.branch('0f84',wrapper_null);getter=None
 if wrapper_null:
  g.take('0f57c0','0f114500')
  if g.bytes.get(g.at)==235:g.jump('eb',1)
  else:g.jump('e9')
 else:
  g.take('488b4b20');g.call(s['resolve']);g.take('ba08000000','488b88c0000000');g.call(s['indexed'])
  g.take('488b3e','488bd8','488bcf');g.call(s['prepare'])
  g.take('440fb78730010000','33c9','66413bc8');g.branch('73',False,1)
  g.take('488b97b0000000')
  for i in range(ordinal+1):
   g.take('0fb7c1','4803c0','48391cc2');g.branch('74',i==ordinal,1)
   if i<ordinal:g.take('66ffc1','66413bc8');g.branch('72',True,1)
  g.take('488b87b0000000','0fb7d1','4803d2','486344d008','4883c014','48c1e004','4803c7',
   '4c8b08','488d4c2420','4c8b4008','488bd6');getter=g.at;g.take('41ffd1')
  g.take('488bcd'if reference_lane==0 else'488d4d08','0f1000','0f114500');g.call(s['barrier'])
 g.take('488b742440','488b5c2448','488b6c2458','4883c430','5f','c3')
 return dict(selectedBytes=g.seen,metadataReadyFlag=ready,providerClassCell=provider,wrapperNull=wrapper_null,
  wrapperProviderContextSlot=4,conversionInterfaceContextSlot=8,interfaceOrdinal=ordinal,getValueMethodSlot=0,
  hiddenGetterCall=getter,managedOutputBytes=16,completeCopiedBytes=0 if wrapper_null else 16,
  defaultZeroBytes=16 if wrapper_null else 0,referenceLaneOffset=reference_lane,
  sameReaderAndOutput=True,entryRspRestored=True,normalReturn=True)

def derive_adapter(image,pins,*,type_name,wrapper_name=None,reference_lane):
 """Derive fresh nominal registration, canonical callback and GetValue16.

 Only direct one-reference managed16 records are supported by this profile.
 This is a source capability under a stated callback selection; it does not
 admit the wrapper's byte grammar or infer a concrete inflated function body.
 """
 import json,struct
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import pointer_param as pointer,buff_ptr_sources,primitive_param,event_args_paths
 from scripts.game_data.memorypack import scalar_param_native as scalar,generated_lifecycle_sources as lifecycle
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.vector_layout import vector_recorder
 from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
 from scripts.game_data.memorypack.pooled_nominal_key_sources import lang_getter
 _publication_gate(image,pins);need('type-name',isinstance(type_name,str)and bool(type_name))
 need('reference-lane',type(reference_lane)is int and reference_lane in(0,8))
 ctx=NativeReferenceContext(image);md=image.metadata;base=image.pe.image_base;ge=GenericEntries(image)
 wrappers=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==type_name and(wrapper_name is None or w.name==wrapper_name)]
 need('one-current-wrapper',len(wrappers)==1);wrapper=wrappers[0];td=ctx.index.types[type_name]
 need('nongeneric-value-original',ctx.is_value_type(type_name)and td.generic_container_index<0)
 scalar.ordinary(image,ctx.type_pointer(td.byval_type_index),17,LABEL+'.original')
 size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
 need('managed16-layout',(image.pe.u32_at_va(size),image.pe.u32_at_va(size+4))==(32,16))
 layout=[];references=[];occupied=[]
 for field in md.fields_for(td):
  if ctx.field_attributes(field.type_index)&16:continue
  name=md.string(field.name_index);owner,declared,offset=ctx.field(type_name+'::'+name)
  raw=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16);kind=raw[10]
  if kind in(14,18,29):width=8;references.append(offset-16);scalar.ordinary(image,ctx.type_pointer(field.type_index),kind,LABEL+'.referenceField',reference=True)
  else:
   need('direct-int32-or-enum-field',kind in(8,17))
   if kind==17:
    need('enum-field',ctx.is_enum(declared));enum=ctx.index.types[declared]
    backing,=[f for f in md.fields_for(enum)if not ctx.field_attributes(f.type_index)&16]
    need('int32-enum-backing',md.string(backing.name_index)=='value__'and ctx.type_name(backing.type_index)=='int')
    scalar.ordinary(image,ctx.type_pointer(backing.type_index),8,LABEL+'.enumBacking')
   scalar.ordinary(image,ctx.type_pointer(field.type_index),kind,LABEL+'.valueField');width=4
  occupied.extend(range(offset-16,offset-16+width));layout.append(dict(name=name,typeName=declared,offset=offset,managedBytes=width))
 need('exact-one-native-reference-lane',references==[reference_lane],references)
 need('complete-disjoint-managed16-fields',sorted(occupied)==list(range(16)),occupied)
 need('exact-wrapper-holder',ctx.field(wrapper.name+'::__instance')==(wrapper.name,type_name,16))
 pair=derive_pair(image,type_name,wrapper.name);registration=pointer.registered_pair(image,pair,wrapper,label=LABEL+'.pair')
 face,=pair['composition']['interfaces'];getter=md.methods[face['getValueMethodIndex']]
 scalar.owned_method_abi(image,ctx,getter.index,wrapper.type_definition,(type_name,17,False),[],LABEL+'.getter')
 getter_entry=image.method_pointer_va(getter);getter_path=lang_getter([(getter_entry,image.pe.bytes_at_va(getter_entry,16))],getter_entry)
 section=md.sections['interfaceOffsets'];at=section.offset+md.types[wrapper.type_definition].interface_offsets_start*8
 table=list(struct.iter_unpack('<ii',md.buf[at:at+md.types[wrapper.type_definition].interface_offsets_count*8]))
 ordinal=table.index((face['interfaceTypeIndex'],face['interfaceOffset']))
 context,context_proof=buff_ptr_sources._adapter_context(image,ge);sources={};s={};registrations={}
 for role,name in(('adapter','Deserialize'),('nonnull','DeserializeNotNull')):
  method=buff_ptr_sources._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2',name)
  registrations[role]=ge.resolve(method.index,[type_name,'object'],[]);s[role]=registrations[role]['pointer'];sources[role]=pointer.owned(image,s[role])
 def call(role,offset):return buff_ptr_sources._call(sources[role],offset)
 for name,offset in dict(peek=45,typeHandle=103,creationTest=126,activate=153,nonnull=182).items():
  actual=call('adapter',offset)
  if name in s:need('exact-registered-nonnull-target',s[name]==actual)
  s[name]=actual
 ff=BytesPath(sources['adapter']['regions'],s['adapter']+52).relative('0f85')
 s['header']=BytesPath(sources['adapter']['regions'],ff+8).relative('e8')
 for name,offset in dict(resolve=66,wrapperProvider=82,wrapperInvoke=117,indexed=157,prepare=171,barrier=293 if reference_lane==0 else 294).items():s[name]=call('nonnull',offset)
 need('same-context-resolver',s['resolve']==call('nonnull',140))
 need('named-type-handle-target',s['typeHandle']==base+pair['registration']['helperMethods']['typeFromHandle'][3])
 programs=dict(adapter=[adapter16_program(sources['adapter']['regions'],s['adapter'],s,**p)for p in({},{'create':False},{'null':True})],
  nonnull=[nonnull_program(sources['nonnull']['regions'],s['nonnull'],s,ordinal=ordinal,reference_lane=reference_lane,wrapper_null=n)for n in(False,True)])
 for role in('wrapperInvoke','peek','header'):sources[role]=pointer.owned(image,s[role])
 invocation=deserialize_slot(sources['wrapperInvoke']['regions'],s['wrapperInvoke'],prepare=s['prepare'],callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]))
 offsets=scalar.reader_offsets(image,LABEL);peek=event_args_paths.peek(sources['peek']['regions'],s['peek'],offsets)
 header=vector_recorder(image)(s['header']-base);primitive_param.object_header_source(image,header,offsets)
 collector=_barrier(image,s['barrier'])
 definition=buff_ptr_sources._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2','Deserialize')
 observed=ge.observe(definition.index,[type_name,wrapper.name],[])
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.managed-value16-adapter-source.v1',status='proved-conditional-managed16-adapter',nativeInputs=pins,
  typeName=type_name,wrapperName=wrapper.name,managedBytes=16,referenceLaneOffset=reference_lane,layout=layout,
  canonicalCallbackAdmitted=True,wrapperGrammarAdmitted=False,providerSelectionObserved=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  proof=dict(registeredPair=pair,registration=registration,registrations=registrations,closedWrapperDeserializeObserved=observed,
   closedWrapperCallbackPointerEqualityInferred=False,adapterContext=context,adapterContextProof=context_proof,interfaceOrdinal=ordinal,
   programs=programs,ownGetValue=getter_path,wrapperInvocation=invocation,peek=peek,header=header,collector=collector,
   symbolRvas={k:v-base for k,v in s.items()},sourceWindows={k:v['windows']for k,v in sources.items()}),
  evidenceBoundary=dict(exact='Fresh nominal managed16/one-reference layout, eager wrapper pair, canonical adapter FF/create paths, complete own wrapper slot5 invocation, interface/GetValue16 transfer and reference-lane barrier.',
   conditional='The compatible initialized selected formatter callback equals the canonical entry; its coherent closed MethodInfo represents the exact registered Original/wrapper pair. Disjoint buffered input/output, bounded owned interface ordinal and ordinary compatible allocation/helper effects. No actual runtime provider choice is observed.',
   unresolved=['independent wrapper wire grammar','actual typed enclosing caller/source join','runtime formatter selection','positive domain beyond independent child bound','whole owner and physical EOF']))))

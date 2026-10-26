"""Closed managed8 CameraShakeConfigPtr and its own one-key pooled formatter.

The original is a value type containing one managed string reference; the
generated wrapper is a reference. Neither nominal identity comes from another
string-valued wrapper. Only initialized coherent selected formatter paths are
proved. Pool absence, cold refill, live provider selection and camera execution
remain unresolved.
"""
import json,struct
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.reference_conversion_sources import validate_conversion_context
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar,primitive_param as primitive
from scripts.game_data.memorypack import pooled_global_buff_id_sources as qword_programs
from scripts.game_data.memorypack.wrapper_members import derive_from_image

LABEL='cameraShakeParam'
VALUE='Beyond.Gameplay.CameraShakeConfigPtr'


def nonnull_value8_program(regions,entry,s,*,null=False):
 """Current managed8 conversion explicitly supplies selector zero in ECX."""
 g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','4c89442418','57','4883ec20')
 qword_programs.flag(g);g.take('498bf9','488bf2','488bd9');g.branch('0f84',False)
 g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
 g.take('488b4f20');g.call(s['resolve']);g.take('488b88c0000000','488b4920');g.call(s['wrapperProvider'])
 g.take('4885c0');g.branch('0f84',False)
 g.take('b905000000','4c8d4c2440','4c8bc3','488bd0');g.call(s['wrapperInvoke'])
 g.take('488b5c2440','4885db');g.branch('74',null,1)
 if null:g.take('33c0','488906');g.jump('eb',1)
 else:
  g.take('488b4f20');g.call(s['resolve']);g.take('ba08000000','488b88c0000000');g.call(s['indexed'])
  g.take('488bd0','33c9','4c8bc3');g.call(s['conversion'])
  g.take('488bce','488906');g.call(s['barrier'])
 g.take('488b5c2430','488b742438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,wrapperNull=null,outputBytes=8,output='unchanged RAX bits',getterSelector=0,normalReturn=True)


def conversion_value8_program(regions,entry,s,*,ordinal):
 scalar.need(LABEL,'boundedInterfaceOrdinal',True,type(ordinal) is int and 0<=ordinal<=8)
 g=BytesPath(regions,entry)
 g.take('48895c2408','48896c2410','4889742418','57','4883ec20','498b38','498bf0','0fb7e9','488bda','488bcf')
 g.call(s['prepare']);g.take('440fb78730010000','33c0','66413bc0');g.branch('73',False,1)
 g.take('488b97b0000000')
 for i in range(ordinal+1):
  g.take('0fb7c8','4803c9','48391cca');g.branch('74',i==ordinal,1)
  if i<ordinal:g.take('66ffc0','66413bc0');g.branch('72',True,1)
 g.take('0fb7d0','488b87b0000000','4803d2','8b44d008','03c5','4898','4883c014','48c1e004','4803c7',
        '4c8b00','488bce','488b5008','488b5c2430','488b6c2438','488b742440','4883c420','5f','49ffe0')
 return dict(selectedBytes=g.seen,interfaceOrdinal=ordinal,selector='incoming UInt16 CX (caller explicitly zero)',receiver='same incoming R8 wrapper forwarded in RCX',companion='selected getter MethodInfo in RDX',returnValue='unchanged managed8 getter RAX',normalTailReturn=True)


def derive(image,pins,profile):
 scalar.need(LABEL,'profileShape',{'registration','composition','integerSlots','initializedHeader','child'},set(profile))
 scalar.need(LABEL,'childProfileShape',{'registration','composition'},set(profile['child']))
 parent,ctx=pointer.derive_parent(image,pins,profile,VALUE)
 base=image.pe.image_base;md=image.metadata
 w,=[w for w in derive_from_image(image).values() if w.wrapped_type==VALUE]
 scalar.need(LABEL,'oneStoredKey',[('key','string')],[(m.name,m.declared_type) for m in w.members])
 scalar.need(LABEL,'valueType',True,ctx.is_value_type(VALUE))
 scalar.need(LABEL,'wrapperHolder',(w.name,VALUE,16),ctx.field(w.name+'::__instance'))
 td=ctx.index.types[VALUE];fields=[f for f in md.fields_for(td) if not ctx.field_attributes(f.type_index)&16]
 scalar.need(LABEL,'exactOwnedKey',['key'],[md.string(f.name_index) for f in fields])
 scalar.need(LABEL,'keyField',(VALUE,'string',16),ctx.field(VALUE+'::key'))
 scalar.ordinary(image,ctx.type_pointer(fields[0].type_index),14,LABEL+'.key',reference=True)
 size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
 scalar.need(LABEL,'boxedAndNativeSizes',(24,8),(image.pe.u32_at_va(size),image.pe.u32_at_va(size+4)))
 mm=pointer.methods(image,w);getter=mm['GetValue']
 scalar.owned_method_abi(image,ctx,getter.index,w.type_definition,(VALUE,17,False),[],LABEL+'.getter')
 getter_proof=pointer.leaf(image,image.method_pointer_va(getter),['488B4110','C3'])
 defaults={}
 for name in ('.ctor','CreateInstance'):
  scalar.owned_method_abi(image,ctx,mm[name].index,w.type_definition,('void',1,False),[],LABEL+'.default')
  defaults[name]=pointer.leaf(image,image.method_pointer_va(mm[name]),['33C0','48894110','C3'])
 reader=mm['Deserialize'];primitive.reader_abi(image,ctx,reader,w);source=pointer.owned(image,image.method_pointer_va(reader))
 header=base+parent['parentHeader']['pointerRva'];barrier=base+parent['barrierRva']
 # The allocation target is selected from the exact owning cold path, then
 # independently tied to the concrete wrapper's typed metadata usage.
 rows=source['rows'];allocation_loads=[]
 for row in rows:
  if bytes.fromhex(row['bytes'])[:3]!=bytes.fromhex('488B0D'):continue
  usage=derive_typed_usage_context(image,int(row['va'],16)-base,label=LABEL+'.allocation')
  if usage.get('typeName')==w.name:allocation_loads.append((row,usage))
 scalar.need(LABEL,'oneWrapperAllocation',1,len(allocation_loads))
 load,allocation=allocation_loads[0];index=rows.index(load);allocate=control_transfer(rows[index+1])['target']
 s=dict(header=header,pool=base+parent['pooledPath']['sourceHelpers'][0],barrier=barrier,allocate=allocate)
 paths=[qword_programs.child_program(source['regions'],source['pointer'],s,**options) for options in ({},{'allocated':True},{'null':True})]
 scalar.need(LABEL,'actualWrapperAllocation',allocation['instructionRva'],paths[1]['allocationUsageSite']-base)
 scalar.need(LABEL,'wrapperAllocationType',w.name,allocation['typeName'])
 scalar.ordinary(image,ctx.type_pointer(allocation['typeIndex']),18,LABEL+'.wrapperAllocation',reference=True)
 key_setter=mm['set___key__'];scalar.owned_method_abi(image,ctx,key_setter.index,w.type_definition,('void',1,False),[('string',14,True)],LABEL+'.keySetter')
 at=image.method_pointer_va(key_setter);raw=image.pe.bytes_at_va(at,12)
 scalar.need(LABEL,'keySetterEntry',bytes.fromhex('4883C110488911E9'),raw[:8])
 scalar.need(LABEL,'keySetterBarrier',barrier,at+12+int.from_bytes(raw[8:],'little',signed=True))
 child_pair=pointer.registered_pair(image,profile['child'],w,label=LABEL+'.childRegistration')
 value_source=derive_value_source(image,parent,profile['child'],VALUE)
 return json.loads(json.dumps(dict(parent=parent,childMethod=child_pair['readerMethod'],childWindows=source['windows'],childPair=child_pair,childPaths=paths,typedAllocation=allocation,childDefaults=defaults,childGetter=getter_proof,keySetter=dict(entryRva=at-base,bytes=raw.hex().upper(),physicalExtentProved=False),valueSource=value_source,evidenceBoundary=dict(direct='Exact closed four-member Param transfers the complete managed8 CameraShakeConfigPtr, two Int32 bindings and pooled path. Its value wrapper owns exactly one pooled string key; default/null and allocation routes preserve that value without borrowing another nominal type.',conditional='Initialized matching generated wrapper, registered adapter and typed conversion route, original pooled StringPool, sufficient contiguous input, disjoint coherent storage and normal Win64 helpers/allocation/barriers; live formatter/provider selection remains conditional.',unresolved=['pool-absent inline encoding','cold refill and malformed paths','live provider/default/cache/override selection','camera execution']))))


def derive_value_source(image,parent,child_pair,value_type):
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
 entries=GenericEntries(image);symbols=ContextSymbols(image);usage=parent['typedRead'];definition=md.methods[usage['methodSpec'][0]]
 scalar.need(LABEL,'readValueInstanceNoArgs',(0,0),(definition.flags&16,definition.parameter_count))
 section=md.sections['genericContainers'];at=section.offset+definition.generic_container_index*16
 scalar.need(LABEL,'readValueGenericContainer',True,definition.generic_container_index>=0 and section.offset<=at<=section.offset+section.size-16)
 container=struct.unpack_from('<iiii',md.buf,at);returned=image.pe.bytes_at_va(ctx.type_pointer(definition.return_type),16)
 scalar.need(LABEL,'readValueOwnMVAR',(definition.index,1,1,30,0,container[3]),(*container[:3],returned[10],returned[11],int.from_bytes(returned[:8],'little')))
 closed=image.instantiations.resolve(usage['methodSpec'][2]).arguments
 scalar.need(LABEL,'oneClosedValue',1,len(closed));scalar.ordinary(image,closed[0].type_pointer_va,17,LABEL+'.closedValue')
 scalar.need(LABEL,'closedValueIdentity',ctx.index.types[value_type].index,int.from_bytes(image.pe.bytes_at_va(closed[0].type_pointer_va,8),'little'))
 selected={};sources={};s={}
 def generic(role,owner,name,classes,methods_):
  candidates=[m for td in image.named_type_definitions[owner] for m in md.methods_for(td) if md.string(m.name_index)==name and (name!='GetFormatter' or m.parameter_count==0)]
  scalar.need(LABEL,'oneGenericDefinition:'+role,1,len(candidates));m=candidates[0]
  e=entries.resolve(m.index,classes,methods_);selected[role]=dict(definition=m.index,classArguments=classes,methodArguments=methods_,registration=e);s[role]=e['pointer'];return m
 selected['registeredValue']=dict(definition=definition.index,classArguments=[],methodArguments=[value_type],registration=entries.resolve(definition.index,[],[value_type]));s['registeredValue']=selected['registeredValue']['registration']['pointer']
 provider_method=generic('registeredProvider','MemoryPack.MemoryPackFormatterProvider','GetFormatter',[],[value_type])
 adapter_method=generic('adapter','Beyond.MemoryPack.GenericMemoryPackFormatter`2','Deserialize',[value_type,'object'],[])
 generic('nonnull','Beyond.MemoryPack.GenericMemoryPackFormatter`2','DeserializeNotNull',[value_type,'object'],[])
 generic('readNull','Beyond.MemoryPack.GenericMemoryPackFormatter`2','ReadIsNull',[value_type,'object'],[])
 def source(role,p):
  sources[role]=pointer.owned(image,p);s[role]=p;return sources[role]
 def call(role,offset):
  r=next(r for r in sources[role]['rows'] if int(r['va'],16)==sources[role]['pointer']+offset);raw=bytes.fromhex(r['bytes'])
  scalar.need(LABEL,'directSourceCall:'+role,(5,232),(len(raw),raw[0]));return control_transfer(r)['target']
 source('value',base+parent['valueReadTargetRva']);source('registeredValue',s['registeredValue'])
 source('provider',call('value',55));source('dispatch',call('value',76));source('registeredProvider',s['registeredProvider'])
 s['prepare']=call('dispatch',33)
 s['classInit']=call('registeredValue',66)
 for offset,role in ((78,'provider'),(99,'dispatch')):scalar.need(LABEL,'canonicalValueSameCall:'+role,s[role],call('registeredValue',offset))
 for offset,role in ((52,'typeHandle'),(79,'backend'),(96,'indexed'),(107,'cast')):s[role]=call('provider',offset)
 s['context']=call('registeredProvider',127)
 for role in ('adapter','nonnull','readNull'):source(role,s[role])
 for offset,role in ((109,'typeHandle'),(129,'isAbstract'),(153,'activate'),(182,'nonnull')):
  target=call('adapter',offset)
  if role in s:scalar.need(LABEL,'adapterSameCall:'+role,s[role],target)
  s[role]=target
 for offset,role in ((66,'resolve'),(82,'wrapperProvider'),(112,'wrapperInvoke'),(148,'indexed'),(161,'conversion'),(172,'barrier')):
  target=call('nonnull',offset)
  if role in s:scalar.need(LABEL,'nonnullSameCall:'+role,s[role],target)
  s[role]=target
 scalar.need(LABEL,'sameOwnedReferenceBarrier',base+parent['barrierRva'],s['barrier'])
 s['peek']=call('readNull',14);s['header']=base+parent['parentHeader']['pointerRva']
 source('backend',s['backend']);source('cast',s['cast']);source('classInit',s['classInit']);source('conversion',s['conversion']);source('peek',s['peek']);source('wrapperInvoke',s['wrapperInvoke'])
 # The backend's complete selected tail has exactly one unconditional jump.
 jumps=[control_transfer(r)['target'] for r in sources['backend']['rows'] if len(bytes.fromhex(r['bytes']))==5 and bytes.fromhex(r['bytes'])[0]==233]
 scalar.need(LABEL,'oneBackendTail',1,len(jumps));s['backendTail']=jumps[0]
 s['assignable']=pointer.calls(sources['cast'])[0]
 run=lambda fn,role,*args,**kwargs:fn(sources[role]['regions'],sources[role]['pointer'],*args,**kwargs)
 actual=run(qword_programs.value8_program,'value',s);canonical=run(qword_programs.value8_program,'registeredValue',s,canonical=True)
 scalar.need(LABEL,'sameValueReaderClass',canonical['classCell'],actual['classCell'])
 actual_provider=run(qword_programs.compared_provider,'provider',s);canonical_provider=run(qword_programs.compared_provider,'registeredProvider',s,canonical=True)
 for key in ('typeClassCell','providerClassCell'):scalar.need(LABEL,'sameProvider:'+key,canonical_provider[key],actual_provider[key])
 run(qword_programs.ready_class_init,'classInit');run(qword_programs.backend_bridge,'backend',s['backendTail'])
 for null in (False,True):run(qword_programs.successful_cast,'cast',s['assignable'],null=null)
 contexts=[]
 for m in (definition,provider_method):
  context=symbols.context(m.index,is_method=True);contexts.append(context);slots={e['relativeSlot']:e for e in context['entries']}
  def own(arg):return arg.get('parameterOwner',{}).get('methodIndex')==m.index and arg['parameterOwner'].get('ordinal')==0
  if m.index==definition.index:
   scalar.need(LABEL,'readerContextSlots',{0,1,2},set(slots));scalar.need(LABEL,'readerContextMethods',[('MemoryPack.MemoryPackFormatterProvider','GetFormatter'),('MemoryPack.MemoryPackFormatter`1','Deserialize')],[(slots[i]['typeName'],slots[i]['methodName'])for i in(0,2)])
   scalar.need(LABEL,'readerContextOwnMVAR',True,own(slots[0]['methodArguments'][0]) and own(slots[1]['type']['classArguments'][0]) and own(slots[2]['classArguments'][0]))
  else:
   scalar.need(LABEL,'providerContextSlots',{0,1},set(slots));scalar.need(LABEL,'providerContextOwnMVAR',True,own(slots[0]['type']) and own(slots[1]['type']['classArguments'][0]))
   scalar.need(LABEL,'providerTypedFormatter','MemoryPack.MemoryPackFormatter`1',slots[1]['type']['definition']['name'])
 adapter_context=symbols.context(adapter_method.declaring_type);validate_conversion_context(image,adapter_context,entries,fail=lambda k,e,a:scalar.need(LABEL,k,e,a))
 face,=child_pair['composition']['interfaces'];td=md.types[face['wrapperDefinition']];section=md.sections['interfaceOffsets'];start=section.offset+td.interface_offsets_start*8;pairs=list(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8]));ordinal=pairs.index((face['interfaceTypeIndex'],face['interfaceOffset']))
 from scripts.game_data.memorypack import event_args_paths
 event_args_paths.peek(sources['peek']['regions'],s['peek'],scalar.reader_offsets(image,LABEL))
 paths={}
 for dispatch in (False,True):
  role='dispatch' if dispatch else 'adapter'
  paths[role]=[run(qword_programs.adapter_program,role,s,dispatch=dispatch,create=create)for create in(False,True)]+[run(qword_programs.adapter_program,role,s,dispatch=dispatch,null=True)]
 paths['nonnull']=[run(nonnull_value8_program,'nonnull',s,null=null)for null in(False,True)]
 paths['readNull']=[run(qword_programs.read_null_program,'readNull',s,null=null)for null in(False,True)]
 paths['conversion']=run(conversion_value8_program,'conversion',s,ordinal=ordinal)
 prepare=next(control_transfer(r)['target']for r in sources['wrapperInvoke']['rows']if len(bytes.fromhex(r['bytes']))==5 and bytes.fromhex(r['bytes'])[0]==232)
 paths['wrapperInvoke']=deserialize_slot(sources['wrapperInvoke']['regions'],s['wrapperInvoke'],prepare=prepare,callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]))
 return dict(entries=selected,contexts=contexts,adapterContext=adapter_context,symbolRvas={k:v-base for k,v in s.items()},windows={k:r['windows'] for k,r in sources.items()},sourceRead=actual,canonicalRead=canonical,providerRead=actual_provider,canonicalProvider=canonical_provider,interfaceOrdinal=ordinal,paths=paths,liveProviderSelectionProved=False,condition='Selected initialized coherent typed provider and GenericMemoryPackFormatter<CameraShakeConfigPtr,its own wrapper> receiver/slot, own getter, valid disjoint reader/output and normal helpers. Default/cache/override selection and execution are not inferred.')

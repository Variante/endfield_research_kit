"""AI48 and its bounded dictionary component under the caller's selected image."""
import struct
from scripts.game_data.levelscript_family_regenerate import Build
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.closed_leaf_entry import decode_closed_leaf_entry
from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_registered_formatter_composition
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.memorypack import npc_ai_sources as source,scalar_param_native as scalar,primitive_param
from scripts.game_data.memorypack.vector_layout import vector_recorder



def _dictionary_abi(image,ctx,method,instance):
 def need(name,expected,actual):scalar.need('npcAI48.dictionaryABI',name,expected,actual)
 need('static-signature',(True,'void',2),(bool(method.flags&16),ctx.type_name(method.return_type),method.parameter_count))
 parameters=list(image.metadata.parameters_for(method));need('parameter-rows',2,len(parameters))
 for parameter,name,kind in zip(parameters,('MemoryPack.MemoryPackReader',instance['name']),(17,21),strict=True):
  raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16);need('exact-parameter',(name,kind,32),(ctx.type_name(parameter.type_index),raw[10],raw[11]))
  if kind==17:need('exact-reader-definition',ctx.index.types[name].index,int.from_bytes(raw[:8],'little'))
  else:need('exact-dictionary-carrier-and-owned-arguments',bytes.fromhex(instance['rawHex'])[:11],raw[:11])


def validate_components(image,pins,fact,string_fact):
 """No opener or success cache; the owning operation bookends all inputs."""
 def need(name,expected,actual):scalar.need('npcAI48',name,expected,actual)
 need('selected-pins',pins,fact['nativeInputs'])
 need('schema','endfield.npc-ai48-source-component.v1',fact.get('schema'))
 validate_eager_wrap_registration(image,fact['eager'],label='npcAI48')
 validate_registered_formatter_composition(image,fact['composition'],label='npcAI48')
 base=image.pe.image_base;ctx=NativeReferenceContext(image);build=Build(image,pins);md=image.metadata;w,=[w for w in build.wrappers.values()if w.wrapped_type=='Beyond.Gameplay.Core.NpcAiInstanceData'];methods={md.string(m.name_index):m for m in md.methods_for(ctx.index.types[w.name])};o=scalar.reader_offsets(image,'NpcAI48');rec=vector_recorder(image)
 def owned(pointer):
  try:ranges=[r['runtimeTriple'][:2]for r in image.unwind_index.family(pointer-base)['ranges']]
  except ValueError as error:
   if not str(error).startswith('unwind-chain.entry-missing:'):raise
   leaf=decode_closed_leaf_entry(image.mapper,image.pe.bytes_at_va(pointer,512),pointer);ranges=[(pointer-base,max(int(r['va'],16)+len(bytes.fromhex(r['bytes']))for r in leaf['rows'])-base)]
  regions=[];rows=[]
  for a,z in ranges:
   raw=image.pe.bytes_at_va(base+a,z-a);regions.append((base+a,raw));rows+=decode_type_data_initialization_instructions(image.mapper,raw,base+a)
  return dict(pointer=pointer,regions=regions,rows=rows)
 def target(row):
  raw=bytes.fromhex(row['bytes']);return int(row['va'],16)+len(raw)+int.from_bytes(raw[-4:],'little',signed=True)
 def after(body,text):
  values={target(r)for i,r in enumerate(body['rows'])if i and bytes.fromhex(r['bytes'])[:1]==b'\xe8'and body['rows'][i-1]['text']==text};need('unique-current-call-'+text,1,len(values));return values.pop()
 proofs={}
 def prove(model,body,*args,**kwargs):return getattr(source,model)(body['regions'],body['pointer'],*args,**kwargs)
 for name,model in(('GetValue','getter'),('.ctor','constructor'),('CreateInstance','constructor')):proofs[name]=prove(model,owned(image.method_pointer_va(methods[name])))
 body=owned(image.method_pointer_va(methods['Deserialize']));calls=[r for r in body['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8'];s=dict(header=target(calls[0]),barrier=after(body,'mov [rbx], rax'),allocate=next(target(r)for i,r in enumerate(body['rows'])if bytes.fromhex(r['bytes'])[:1]==b'\xe8'and i and body['rows'][i-1]['text'].startswith('mov rcx, [rip')))
 reads=[target(calls[i])for i in(1,2,4,5,7,8)]
 for role,pointer in zip(('single','pool','long','poolAgain','enum','vector'),reads,strict=True):s[role]=pointer
 need('same-pool-source',s['pool'],s.pop('poolAgain'))
 proofs['reader']=[prove('reader',body,s,null=True),prove('reader',body,s),prove('reader',body,s,allocated=True)]
 owner=ctx.index.types['Beyond.SerializeFieldDictionary`2'];method,=[m for m in md.methods_for(owner)if md.string(m.name_index)=='DeserializeV2'];entry=GenericEntries(image).resolve(method.index,['object',w.wrapped_type],[]);dictionary=owned(entry['pointer']);ds={role:after(dictionary,previous)for role,previous in(('context','mov rcx, [rbp+0x20]'),('type','mov rcx, [rax+0xc0]'),('allocate','mov rcx, rax'),('constructor','mov rdx, [rdx+0xb0]'),('barrier','mov [r14], rdi'),('keyProvider','mov rcx, [rcx+0xb8]'),('valueProvider','mov rcx, [rcx+0xc0]'),('keyDispatch','mov rdx, r15'),('valueDispatch','mov rdx, r12'),('setItem','mov r9, [r9+0x28]'))}
 proofs['dictionary']=[prove('dictionary',dictionary,o,ds,null=True),prove('dictionary',dictionary,o,ds,count=0),prove('dictionary',dictionary,o,ds,count=1)]
 proofs['single']=primitive_param.single_source(image,rec(s['single']-base,fragments=True),o);proofs['long']=scalar.integer_source(image,rec(s['long']-base,fragments=True),o,'NpcAI.long',width=8);proofs['enum']=scalar.integer_source(image,rec(s['enum']-base,fragments=True),o,'NpcAI.enum',width=4);proofs['header']=primitive_param.object_header_source(image,rec(s['header']-base,fragments=True),o);proofs['pool']=build.prove_pooled_string_target(s['pool'])

 from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 adapter_type=ctx.index.types['Beyond.MemoryPack.GenericMemoryPackFormatter`2'];am={md.string(m.name_index):m for m in md.methods_for(adapter_type)};ge=GenericEntries(image);ab={name:owned(ge.resolve(am[name].index,[w.wrapped_type,'object'],[])['pointer'])for name in('Deserialize','DeserializeNotNull','ReadIsNull')};main=ab['Deserialize'];nonnull=ab['DeserializeNotNull'];a=dict(main=main['pointer'],readNull=after(main,'mov rdx, [rdx]'),typeFromHandle=after(main,'mov rcx, rbx'),isValueType=after(main,'mov rcx, rax'),factory=after(main,'mov rcx, [rcx+0x58]'),nonnull=after(main,'mov r9, [r9+0x18]'));need('closed-ReadIsNull',ab['ReadIsNull']['pointer'],a['readNull']);need('closed-NotNull',nonnull['pointer'],a['nonnull']);dispatch=owned(ds['valueDispatch']);a['prepare']=after(dispatch,'mov rbx, rdx');proofs['adapter']=[prove('adapter',main,a),prove('adapter',dispatch,a,dispatch=True)]
 n=dict(context=after(nonnull,'mov rcx, [rdi+0x20]'),wrapperProvider=after(nonnull,'mov rcx, [rcx+0x20]'),wrapperDispatch=after(nonnull,'mov rdx, rax'),type=after(nonnull,'mov rcx, [rax+0xc0]'),conversion=after(nonnull,'mov r9, rbx'),barrier=after(nonnull,'movups [rsi+0x20], xmm2'));proofs['nonnull']=[prove('nonnull',nonnull,n),prove('nonnull',nonnull,n,wrapper_null=True)]
 td=ctx.index.types[w.name];section=md.sections['interfaceOffsets'];pairs=list(struct.iter_unpack('<ii',md.buf[section.offset+td.interface_offsets_start*8:section.offset+(td.interface_offsets_start+td.interface_offsets_count)*8]));ordinal,= [i for i,(index,_)in enumerate(pairs)if ctx.type_name(index)=='Beyond.MemoryPack.IMemoryPackDeSerializeWrapper`1<'+w.wrapped_type+'>'];conversion=owned(n['conversion']);prepare=after(conversion,'mov rbx, r8');proofs['conversion']=prove('conversion',conversion,prepare=prepare,ordinal=ordinal)
 fmt=w.name+'+'+w.name.rsplit('.',1)[-1]+'Formatter';fm,=[m for m in md.methods_for(ctx.index.types[fmt])if md.string(m.name_index)=='Deserialize'];wrapper_pointer=image.method_pointer_va(fm);wrapper_dispatch=owned(n['wrapperDispatch']);prep=after(wrapper_dispatch,'mov rcx, [rdx]');proofs['wrapperSlot5']=deserialize_slot(wrapper_dispatch['regions'],wrapper_dispatch['pointer'],prepare=prep,callback=wrapper_pointer);sm,=[m for m in md.methods_for(ctx.index.types['MemoryPack.BeyondStringFormatter'])if md.string(m.name_index)=='Deserialize'];key_dispatch=owned(ds['keyDispatch']);proofs['keySlot5']=deserialize_slot(key_dispatch['regions'],key_dispatch['pointer'],prepare=prep,callback=image.method_pointer_va(sm));null=ab['ReadIsNull'];peek=after(null,'mov byte [rsp+0x30], 0x0');peekbody=owned(peek)
 proofs['peek']=prove('peek',peekbody,o);proofs['readNull']=[prove('read_null',null,peek=peek,header=s['header'],null=value)for value in(False,True)];proofs['forwarder']=prove('forwarder',owned(wrapper_pointer),body['pointer']);setitem=owned(ds['setItem']);insert=after(setitem,'movaps [rsp+0x50], xmm0');proofs['setItem']=prove('set_item',setitem,insert)
 from scripts.game_data.memorypack.int_list_sources import initialized_class
 proofs['contextWarm']=initialized_class([(ds['context'],image.pe.bytes_at_va(ds['context'],64))],ds['context']);proofs['typeWarm']=initialized_class([(ds['type'],image.pe.bytes_at_va(ds['type'],64)),(ds['context'],image.pe.bytes_at_va(ds['context'],64))],ds['type'],indexed=True)

 need('value-type',True,ctx.is_value_type(w.wrapped_type));need('wrapper-reference',False,ctx.is_value_type(w.name));need('instance-field',(w.name,w.wrapped_type,16),ctx.field(w.name+'::__instance'))
 expected=[('key','string',16),('stringValue','string',24),('longValue','long',32),('floatValue','float',40),('vector3Value','UnityEngine.Vector3',44),('valueType',w.wrapped_type+'+ValueType',56)]
 actual=[(md.string(f.name_index),ctx.type_name(f.type_index),ctx.field(w.wrapped_type+'::'+md.string(f.name_index))[2])for f in md.fields_for(ctx.index.types[w.wrapped_type])if not ctx.field_attributes(f.type_index)&16];need('owned-fields',expected,actual)
 for name,size in((w.wrapped_type,(64,48,0,0)),(w.name,(64,-1,0,0))):
  address=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+ctx.index.types[name].index*8);need('managed-size-'+name,size,struct.unpack('<iiii',image.pe.bytes_at_va(address,16)))
 primitive_param.reader_abi(image,ctx,methods['Deserialize'],w)
 need('wrapper-formatter-ABI',(False,5,'void',2),(bool(fm.flags&16),fm.slot,ctx.type_name(fm.return_type),fm.parameter_count))
 for parameter,name,kind in zip(md.parameters_for(fm),('MemoryPack.MemoryPackReader',w.name),(17,18),strict=True):
  raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16);need('wrapper-formatter-byref',(name,kind,32),(ctx.type_name(parameter.type_index),raw[10],raw[11]))
 scalar.owned_method_abi(image,ctx,methods['GetValue'].index,td.index,(w.wrapped_type,17,False),[],'npcAI48.GetValue')
 need('declared-order',['floatValue','key','longValue','stringValue','valueType','vector3Value'],[m.name for m in w.members])
 registration,=fact['composition']['registrations'];need('registered-original',w.wrapped_type,registration['originalType']);need('registered-wrapper',w.name,registration['wrapperType'])
 allocated=proofs['reader'][2]['allocation'];usage=derive_typed_usage_context(image,allocated['site']-base,label='npcAI48.allocate');need('allocated-wrapper',(1,w.name),(usage['tag'],usage['typeName']))
 for key,expected_type in(('enumContext',w.wrapped_type+'+ValueType'),('vectorContext','UnityEngine.Vector3')):
  usage=derive_typed_usage_context(image,proofs['reader'][1][key]['site']-base,label='npcAI48.'+key);need(key,('MemoryPack.MemoryPackReader','ReadUnmanaged',[],[expected_type]),(usage['typeName'],usage['methodName'],usage['classArguments'],usage['methodArguments']))
 from scripts.game_data.memorypack.vector3_source import validate_vector3_source
 proofs['vector3']=validate_vector3_source(image,usage,s['vector']-base)
 enum=ctx.index.types[w.wrapped_type+'+ValueType'];underlying,=[f for f in md.fields_for(enum)if md.string(f.name_index)=='value__'];need('enum-underlying','int',ctx.type_name(underlying.type_index))
 dc=ContextSymbols(image).context(owner.index,slots=[5,21,22,23,24]);slots={r['relativeSlot']:r for r in dc['entries']}
 _dictionary_abi(image,ctx,method,slots[21]['type'])
 for index,owner_name,name in((5,'System.Collections.Generic.Dictionary`2','set_Item'),(22,'Beyond.SerializeFieldDictionary`2','.ctor'),(23,'MemoryPack.MemoryPackFormatterProvider','GetFormatter'),(24,'MemoryPack.MemoryPackFormatterProvider','GetFormatter')):need('dictionary-slot-'+str(index),(owner_name,name),(slots[index]['typeName'],slots[index]['methodName']))
 need('dictionary-allocation-type','Beyond.SerializeFieldDictionary`2',slots[21]['type']['definition']['name'])
 for index,arguments in((5,slots[5]['classArguments']),(21,slots[21]['type']['classArguments']),(22,slots[22]['classArguments']),(23,slots[23]['methodArguments']),(24,slots[24]['methodArguments'])):
  expected_ordinals=[0]if index==23 else[1]if index==24 else[0,1];need('dictionary-owned-vars-'+str(index),[(owner.index,n)for n in expected_ordinals],[(v['parameterOwner']['typeIndex'],v['parameterOwner']['ordinal'])for v in arguments])
 need('dictionary-constructor',ds['constructor'],ge.resolve(slots[22]['methodSpec'][0],['object',w.wrapped_type],[])['pointer']);need('dictionary-setter',ds['setItem'],ge.resolve(slots[5]['methodSpec'][0],['object',w.wrapped_type],[])['pointer'])
 value_provider=owned(ds['valueProvider'])
 provider_calls=[target(r)for r in value_provider['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8'];vs=dict(zip(('typeFromHandle','backend','type','cast'),provider_calls[:4],strict=True));proofs['valueProviderClone']=prove('value_provider',value_provider,vs)
 need('provider-indexed-type',ds['type'],vs['type'])
 from scripts.game_data.memorypack.pooled_string_list_sources import validate_string_components
 proofs['stringCallback']=validate_string_components(image,string_fact)
 need('string-selected-pins',pins,string_fact['nativeInputs'])
 ac={r['relativeSlot']:r for r in ContextSymbols(image).context(adapter_type.index)['entries']}
 def vars(name,arguments,ordinals,owner_index=adapter_type.index,owner_key='typeIndex'):
  need(name,[(owner_index,n)for n in ordinals],[(v['parameterOwner'][owner_key],v['parameterOwner']['ordinal'])for v in arguments])
 for slot,name in((0,'ReadIsNull'),(3,'DeserializeNotNull')):
  need('adapter-method-'+str(slot),('Beyond.MemoryPack.GenericMemoryPackFormatter`2',name),(ac[slot]['typeName'],ac[slot]['methodName']));vars('adapter-class-vars-'+str(slot),ac[slot]['classArguments'],[0,1])
 need('adapter-wrapper-provider',('MemoryPack.MemoryPackFormatterProvider','GetFormatter'),(ac[4]['typeName'],ac[4]['methodName']));vars('adapter-provider-wrapper',ac[4]['methodArguments'],[1])
 need('adapter-conversion-interface','Beyond.MemoryPack.IMemoryPackDeSerializeWrapper`1',ac[8]['type']['definition']['name']);vars('adapter-conversion-original',ac[8]['type']['classArguments'],[0])
 vars('adapter-wrapper-type',[ac[10]['type']],[1]);need('adapter-wrapper-factory',('System.Activator','CreateInstance'),(ac[11]['typeName'],ac[11]['methodName']));vars('adapter-factory-wrapper',ac[11]['methodArguments'],[1])
 need('adapter-conversion-getter',('Beyond.MemoryPack.IMemoryPackDeSerializeWrapper`1','GetValue'),(ac[9]['typeName'],ac[9]['methodName']));vars('adapter-getter-original',ac[9]['classArguments'],[0])
 pc=ContextSymbols(image).context(slots[24]['methodSpec'][0],is_method=True);ps={r['relativeSlot']:r for r in pc['entries']};need('provider-context-slots',[0,1],sorted(ps));vars('provider-type',[ps[0]['type']],[0],pc['definition'],'methodIndex');need('provider-formatter-type','MemoryPack.MemoryPackFormatter`1',ps[1]['type']['definition']['name']);vars('provider-formatter-argument',ps[1]['type']['classArguments'],[0],pc['definition'],'methodIndex')
 need('wrapper-dispatch',ds['keyDispatch'],n['wrapperDispatch']);need('shared-ready-context',ds['context'],n['context']);need('shared-ready-type',ds['type'],n['type']);need('shared-barrier',ds['barrier'],n['barrier'])
 return dict(selectedPrograms=sum(len(v)if isinstance(v,list)else 1 for v in proofs.values()),wireMemberCount=6,managedValueBytes=48,dictionaryCounts=[0,1],dictionaryNullAllowed=True,valueNullAllowed=False,fieldOrder=[m.name for m in w.members],referenceSharingConditional=True,matchingProviderResultConditional=True,liveProviderSelectionProved=False,wholeOwnerAdmitted=False)

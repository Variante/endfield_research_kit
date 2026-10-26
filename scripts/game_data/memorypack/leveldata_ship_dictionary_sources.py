"""Finite string-key spaceship dictionaries under explicit erased-source joins.

An object-key registration is only a source witness. The actual string-key
carrier, helper contexts/targets, pooled-string callback and value callback
must be proved separately; no closed pointer equivalence is inferred.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
import copy
import json

CABIN='Beyond.Gameplay.CabinSlotInfo'
LIMIT=4096


def dictionary_helper_context(symbols,definition):
 """Only actual constructor/default comparer/Add insertion slots are used.

 Unrelated Dictionary slots may use unsupported RGCTX kinds. They acquire no
 declaration, callable or body admission from this selected source path.
 """
 return symbols.context(definition,slots=[1,2,24])


def _constructor_facts(rows):
 """Keep full authenticated windows/decoded rows, not owned raw byte buffers."""
 return [dict(registration=row['registration'],sourceWindows=row['body']['windows'],sourceRows=row['body']['rows'])for row in rows]


def _owned_call_after(rows,text):
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 targets=[control_transfer(rows[i+1])['target']for i,row in enumerate(rows[:-1])
  if row['text']==text and bytes.fromhex(rows[i+1]['bytes'])[:1]==b'\xe8']
 if len(set(targets))!=1:raise ValueError('storyShipDictionary.one-owned-source-call:'+text+':'+str(targets))
 return targets[0]


def dictionary48_program(regions,entry,s,*,count):
 if type(count)is not int or not -1<=count<=3:raise ValueError('storyShipDictionary.finite-count-witness')
 g=BytesPath(regions,entry)
 g.take('4053','55','56','57','4154','4881ecd0000000');ready=flag(g)
 g.take('498bd9','498bf0','4c8be2','488be9');g.branch('75',True,1)
 g.take('0f57c0','488d942408010000','33ff','498bcc','89bc2408010000','48897c2430','0f11442438','0f11442448','0f11442458')
 g.call(s['header']);g.take('84c0');g.branch('0f84',count==-1)
 provider=None;callbacks=[];adds=[]
 if count==-1:
  g.take('488bce','48893e');g.call(s['barrier']);g.take('90');g.jump('e9')
 else:
  g.take('4c89b42410010000','4c89ac2400010000','4c89bc2418010000','448bb42408010000','48393e');g.branch('0f85',False)
  g.take('488b4b20','ba03000000','4c8b7d10','488b89c0000000');g.call(s['context']);g.take('488bc8');g.call(s['allocate'])
  g.take('488be8','4885c0');g.branch('0f84',False)
  g.take('488b4b20','488b91c0000000','488b4a20','48397920');g.branch('0f84',False)
  g.take('488b4320','4d8bc7','418bd6','488bcd','4c8b88c0000000','4d8b4920');g.call(s['constructor'])
  g.take('488bce','48892e');g.call(s['barrier']);provider=g.relative('488b0d')
  g.take('39b9e0000000');g.branch('0f84',False)
  g.take('488b4320','488b88c0000000','488b4930');g.call(s['keyProvider'])
  g.take('488b4b20','4c8be8','488b89c0000000','488b4938');g.call(s['valueProvider'])
  g.take('4889842408010000','4585f6');g.branch('0f8e',count==0)
  for index in range(count):
   g.take('488b4b20','4c8d4c2430','4d8bc4','488b91c0000000','488b4a40','488bd0','48894c2428','488d4c2438','48894c2420','498bcd')
   callbacks.append(g.at);g.call(s['keyValue'])
   g.take('0f10442438','488b2e','4c8b7c2430','0f104c2448','0f10542458','0f11442468','0f114c2478','0f11942488000000','4885ed');g.branch('0f84',False)
   g.take('488b4320','488b88c0000000','488b4148','4883782000');g.branch('0f84',False)
   g.take('488b4320','4c8d8424a0000000','498bd7','0f298424a0000000','488bcd','0f298c24b0000000','0f299424c0000000',
    '4c8b88c0000000','4d8b4948');adds.append(g.at);g.call(s['Add'])
   g.take('488b842408010000','ffc7','413bfe');g.branch('0f8c',index+1<count)
  g.take('4c8bac2400010000','4c8bbc2418010000','4c8bb42410010000')
 g.take('4881c4d0000000','415c','5f','5e','5d','5b','c3')
 return dict(selectedBytes=g.seen,metadataReadyFlag=ready,countWitness=count,headerBytes=4,newDictionary=True,
  initiallyNullOutputRequired=True,providerClassCell=provider,keyValueCallbackSites=callbacks,elementCallbackSites=callbacks,AddCallSites=adds,
  keyManagedBytes=8,valueManagedBytes=48,valueWireBytes=None,paddingByteRanges=[[44,48]],
  rawValueSlices=[[0,16],[16,16],[32,16]],counter='EDI starts0/increments1',savedCount='R14D unchanged',
  constructorCapacityEqualsSavedCount=count!=-1,constructorComparerFromFormatterOffset=16,
  helperContextSlots=dict(dictionary=3,constructor=4,keyProvider=6,valueProvider=7,keyValue=8,Add=9),
  normalReturn=True,entryRspRestored=True,closedPointerEquivalenceProved=False,keyWireGrammarAdmitted=False,valueWireGrammarAdmitted=False,
  frame=dict(entryRspDelta=-248,callShadow=[0,32],stackCallArguments=[[32,40],[40,48]],keyLocal=[48,56],
   valueLocal=[56,104],valueBackup=[104,152],alignedAddLocal=[160,208],
   savedEntryHomes=dict(r13=[8,16],countThenValueProvider=[16,24],r14=[24,32],r15=[32,40]),
   pushedNonvolatiles=['rbx','rbp','rsi','rdi','r12']))


def key_value48_program(regions,entry,s):
 g=BytesPath(regions,entry)
 g.take('48895c2408','48896c2410','4889742418','48897c2420','4156','4883ec60','488bf1','498bf9',
  '488b8c2498000000','498be8','4c8bf2','4883793800');g.branch('74',False,1)
 g.take('0f57c0','33c0','0f11442420','4889442450','0f11442430','0f11442440','488b9c2490000000',
  '488907','0f1103','0f114310','0f114320','4885f6');g.branch('74',False,1)
 g.take('b905000000','4c8bcf','4c8bc5','488bd6');g.call(s['keyDispatch']);g.take('4d85f6');g.branch('74',False,1)
 g.take('4c8bcb','4c8bc5','498bd6');g.call(s['valueDispatch'])
 g.take('4c8d5c2460','498b5b10','498b6b18','498b7320','498b7b28','498be3','415e','c3')
 return dict(selectedBytes=g.seen,keyOutputBytesZeroed=8,valueOutputBytesZeroed=48,
  sameIncomingReader=True,keyDispatchSelector=5,keyOutputRegister='r9',valueOutputRegister='r9',
  valueDispatcherRcxSelectorRequired=False,valueDispatcherMustProveUnusedRcx=True,
  keyFormatter='incoming RCX',valueFormatter='incoming RDX',reader='incoming R8',
  normalReturn=True,entryRspRestored=True,keyWireGrammarAdmitted=False,valueWireGrammarAdmitted=False,
  frame=dict(entryRspDelta=-104,callShadow=[0,32],unusedZeroLocal=[32,88],
   incomingArgumentHomes=dict(valueOutput=40,methodInfo=48),
   savedEntryHomes=dict(rbx=[8,16],rbp=[16,24],rsi=[24,32],rdi=[32,40]),pushedNonvolatiles=['r14']))


def add48_program(regions,entry,insert):
 g=BytesPath(regions,entry)
 g.take('48895c2408','48896c2410','4889742418','57','4883ec60','498b4120','498bd9','498bf8','488bf2','488be9',
  '4c8b88c0000000','498b81c0000000','4883782000');g.branch('0f84',False)
 g.take('488b4320','4c8d442430','0f1007','41b102','488bd6','0f104f10','488b88c0000000','0f29442430','0f104720',
  '488b81c0000000','488bcd','4889442420','0f294c2440','0f29442450');g.call(insert)
 g.take('488b5c2470','488b6c2478','488bb42480000000','4883c460','5f','c3')
 return dict(selectedBytes=g.seen,valueManagedBytes=48,rawCopySlices=[[0,16],[16,16],[32,16]],
  insertionBehaviorLiteral=2,insertionMethodContextSlot=24,keyReferenceUnchanged=True,
  normalReturn=True,entryRspRestored=True,storedMapSemanticsAdmitted=False,
  actualInsertNormalCompatibilityRequired=True,frame=dict(entryRspDelta=-104,callShadow=[0,32],methodInfoArgument=[32,40],
   alignedValueLocal=[48,96],savedEntryHomes=dict(rbx=[8,16],rbp=[16,24],rsi=[24,32]),pushedNonvolatiles=['rdi']))


def constructor48_program(regions,entry,s,*,positive,same_comparer):
 if type(positive)is not bool or type(same_comparer)is not bool:raise ValueError('storyShipDictionary.literal-constructor-path')
 g=BytesPath(regions,entry)
 g.take('48895c2408','48896c2410','4889742418','57','4883ec20','498be9','498bf0','8bfa','488bd9','85d2');g.branch('0f88',False)
 g.take('85d2');g.branch('7e',not positive,1)
 if positive:
  g.take('498b4120','488b88c0000000','488b4108','4883782000');g.branch('0f84',False)
  g.take('488b4520','8bd7','488bcb','4c8b80c0000000','4d8b4008');g.call(s['initialize'])
 g.take('488b4520','488b88c0000000','488b4910');g.call(s['defaultComparer'])
 g.take('483bf0');g.branch('74',same_comparer,1)
 if not same_comparer:g.take('488d4b30','48897330');g.call(s['barrier'])
 g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,positiveCapacity=positive,sameComparer=same_comparer,capacityUnchanged=True,
  comparerReferenceUnchanged=True,comparerFieldOffset=48,initializeContextSlot=1,defaultComparerContextSlot=2,
  normalReturn=True,entryRspRestored=True,closedPointerEquivalenceProved=False,
  actualInitializeAndComparerNormalCompatibilityRequired=True,storageAndHashSemanticsAdmitted=False)


def value_provider48_program(regions,entry,s):
 """Actual warm MVAR provider source; closed value/key semantics stay separate."""
 g=BytesPath(regions,entry)
 g.take('48895c2410','57','4883ec20','4883793800','488bf9');g.branch('75',True,1)
 type_cell=g.relative('488b0d');g.take('488b5f38','83b9e000000000','488b1b');g.branch('75',True,1)
 g.take('33d2','488bcb');g.call(s['typeHandle']);provider=g.relative('488b0d')
 g.take('488bd8','83b9e000000000');g.branch('75',True,1)
 g.take('488bcb');g.call(s['backend']);g.take('488b4f38','ba01000000','488bd8');g.call(s['indexed'])
 g.take('488bd0','488bcb');g.call(s['cast']);g.take('4885c0');g.branch('0f84',False)
 g.take('488b5c2438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,typeClassCell=type_cell,providerClassCell=provider,contextSlots=[0,1],
  successfulCastReturnsBackendUnchangedRequired=True,normalReturn=True,entryRspRestored=True,
  actualRuntimeProviderChoiceObserved=False,closedPointerEquivalenceProved=False)


def _derive_dictionary(image,pins,*,typed_request,call_target,value_profile):
 """Two finite profiles with independent value/copy/loop source algorithms."""
 if value_profile not in('cabin','uint64'):raise ValueError('storyShipDictionary.closed-value-profile')
 if value_profile=='cabin':
  value_name=CABIN;value_bytes=48;dictionary_program=dictionary48_program;pair_source=key_value48_program
  constructor_source=constructor48_program;add_source=add48_program
 else:
  from scripts.game_data.memorypack import leveldata_ship_u64_dictionary_sources as uint64
  value_name='ulong';value_bytes=8;dictionary_program=uint64.dictionary_program;pair_source=uint64.pair_program
  constructor_source=uint64.constructor_program;add_source=uint64.add_program
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.contracts import CONTRACTS_DIR
 from scripts.game_data.il2cpp.context import method_parameter_owner,type_parameter_owner
 from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context,validate_generic_contexts,_vtable,derive_typed_usage_context
 from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,closed_generic_reference_pointer_extent
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.memorypack import scalar_param_native as scalar,modelview_packable_sources,lang_key_list_sources,numeric_list_sources
 from scripts.game_data.memorypack import npc_collection_sources,npc_collection_programs,pooled_global_buff_id_sources
 from scripts.game_data.memorypack.leveldata_cabin_transfer_sources import derive_dispatch
 from scripts.game_data.memorypack.levelscript_interactive_sources import dictionary_context,dictionary_header_program
 from scripts.game_data.memorypack.pointer_param import owned
 from scripts.game_data.memorypack.pooled_string_list_sources import validate_string_components
 from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
 from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
 from scripts.game_data.memorypack.counted_loop_sources import prove_induction
 need=lambda k,e,a:scalar.need('storyShipDictionary',k,e,a)
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image);cs=ContextSymbols(image)
 deps={name:(CONTRACTS_DIR/name).read_bytes()for name in('npc_runtime_native.json','leveldata_npc_patrol_native.json',
  'levelscript_pooled_string_list_native.json','levelscript_int_list_native.json')}
 facts={name:json.loads(raw)for name,raw in deps.items()}
 for name,fact in facts.items():need('dependency-selected-inputs:'+name,pins,fact['nativeInputs'])
 typename='System.Collections.Generic.Dictionary`2<string,'+value_name+'>'
 validate_typed_usage_context(image,typed_request,label='storyShipDictionary.parent')
 bind_typed_read(image,typed_request,method_name='ReadPackable',argument=typename,kind=21,reference=True)
 argument,=image.instantiations.resolve(typed_request['methodSpec'][2]).arguments
 carrier=cs.type(argument.type_pointer_va);extent=closed_generic_reference_pointer_extent(ctx,argument.type_pointer_va)
 need('actual-closed-dictionary',typename,carrier['name']);key,value=carrier['classArguments']
 need('actual-string-key',('string',b'\x0e\x00'),(key['name'],bytes.fromhex(key['rawHex'])[10:12]))
 if value_profile=='cabin':
  need('actual-Cabin-value',(CABIN,b'\x11\x80',ctx.index.types[CABIN].index),
   (value['name'],bytes.fromhex(value['rawHex'])[10:12],int.from_bytes(bytes.fromhex(value['rawHex'])[:8],'little')))
 else:need('actual-UInt64-value',('ulong',b'\x0b\x80'),(value['name'],bytes.fromhex(value['rawHex'])[10:12]))
 core=facts['npc_runtime_native.json'];generic=facts['leveldata_npc_patrol_native.json']['declarations']
 routes=copy.deepcopy(generic['adapters']['referenceRoutes']);routes['wrappers']=[]
 need('actual-reference-frontdoor',base+core['readPackable']['entryRva'],call_target)
 reference=modelview_packable_sources.validate_components(image,pins,core['readPackable'],routes)
 td=ctx.index.types['MemoryPack.Formatters.DictionaryFormatter`2'];method,=[m for m in md.methods_for(td)if md.string(m.name_index)=='Deserialize']
 context=cs.context(td.index);validate_generic_contexts(image,[context],label='storyShipDictionary.context');context_proof=dictionary_context(image,context)
 slots={r['relativeSlot']:r for r in context['entries']}
 _vtable(image,td.index,5,method.index,'storyShipDictionary')
 need('source-declaration-ABI',(False,5,2,'void'),(bool(method.flags&16),method.slot,method.parameter_count,ctx.type_name(method.return_type)))
 reader,output=md.parameters_for(method);rr=image.pe.bytes_at_va(ctx.type_pointer(reader.type_index),16);out=image.pe.bytes_at_va(ctx.type_pointer(output.type_index),16)
 declared=image.pe.bytes_at_va(ctx.type_pointer(slots[3]['index']),16)
 need('source-reader-byref',(b'\x11\x20',ctx.index.types['MemoryPack.MemoryPackReader'].index),(rr[10:12],int.from_bytes(rr[:8],'little')))
 need('same-owned-dictionary-output',(b'\x15\x20',declared[:8]),(out[10:12],out[:8]))
 witness=ge.resolve(method.index,['object',value_name],[]);source=owned(image,witness['pointer'])
 def calls(body):
  result=[]
  for row in body['rows']:
   if bytes.fromhex(row['bytes'])==b'\xc3':break
   if bytes.fromhex(row['bytes'])[:1]==b'\xe8':result.append(control_transfer(row)['target'])
  return result
 hot=calls(source)
 if value_profile=='cabin':
  need('exact-normal-helper-sequence',10,len(hot))
  s=dict(zip(('metadata','header','context','allocate','constructor','barrier','keyProvider','valueProvider','keyValue','Add'),hot,strict=True))
 else:
  # This physical primary returns before its separately owned positive-loop
  # fragment. Select each exact source call in the full authenticated family;
  # dictionary_program independently authenticates all complete paths/targets.
  s={}
  for role,text in dict(header='mov [rsp+0x38], rdi',context='mov rcx, [rcx+0xc0]',allocate='mov rcx, rax',
   constructor='mov r9, [r9+0x20]',barrier='mov [rsi], rbp',keyProvider='mov rcx, [rcx+0x30]',
   valueProvider='mov rcx, [rcx+0x38]',keyValue='mov [rsp+0x20], rax',Add='mov r9, [r9+0x48]').items():
   s[role]=_owned_call_after(source['rows'],text)
 paths=[dictionary_program(source['regions'],source['pointer'],s,count=count)for count in(-1,0,1,2,3)]
 induction=prove_induction(paths[1:],initial='33ff',increment='ffc7',comparison='413bfe',counter='edi',saved_count='R14D',max_count=LIMIT,mode_key='newDictionary')
 bodies={name:owned(image,s[name])for name in('header','constructor','keyProvider','valueProvider','keyValue','Add')}
 kv=calls(bodies['keyValue']);need('exact-pair-callbacks',2 if value_profile=='cabin'else 3,len(kv))
 s.update(keyDispatch=kv[-2],valueDispatch=kv[-1])
 pair_program=pair_source(bodies['keyValue']['regions'],s['keyValue'],s)
 value_component=(derive_dispatch if value_profile=='cabin'else uint64.derive_dispatch)(image,pins,call_target=s['valueDispatch'])
 need('matched-value-dispatch-ABI',('r8','r9','rdx',False),
  (value_component['readerRegister'],value_component['outputRegister'],value_component['formatterRegister'],value_component['entryRcxSelectorUsed']))
 string_fact=facts['levelscript_pooled_string_list_native.json'];string_proof=validate_string_components(image,string_fact)
 string_target=base+next(p['entryRva']for p in string_fact['programs']if p['role']=='string')
 key_dispatch=owned(image,s['keyDispatch'])
 prepare=base+(value_component['value']['proof']['symbolRvas']['prepare']if value_profile=='cabin'else value_component['prepareTargetRva'])
 need('same-independently-proved-reference-preparation',base+routes['symbolRvas']['prepare'],prepare)
 dispatch_proof=deserialize_slot(key_dispatch['regions'],key_dispatch['pointer'],prepare=prepare,callback=string_target)
 # Pair helper declarations are owned MVARs, not value-width aliases.
 pair_method=md.methods[slots[8]['methodSpec'][0]];params=list(md.parameters_for(pair_method));method_containers=[m.generic_container_index for m in md.methods]
 need('pair-static-void-five',('MemoryPack.Formatters.KeyValuePairFormatter','Deserialize',True,'void',5),
  (image.type_name(pair_method.declaring_type),md.string(pair_method.name_index),bool(pair_method.flags&16),ctx.type_name(pair_method.return_type),len(params)))
 for index,formal in enumerate(params):
  pointer=ctx.type_pointer(formal.type_index);raw=image.pe.bytes_at_va(pointer,16)
  if index in(0,1):
   typ=cs.type(pointer);need('pair-provider-carrier:'+str(index),('MemoryPack.MemoryPackFormatter`1',b'\x15\x00'),(typ['definition']['name'],raw[10:12]))
   item,=typ['classArguments'];need('pair-provider-owned-MVAR:'+str(index),(pair_method.index,index),(item['parameterOwner']['methodIndex'],item['parameterOwner']['ordinal']))
  elif index==2:need('pair-same-reader',(b'\x11\x20',ctx.index.types['MemoryPack.MemoryPackReader'].index),(raw[10:12],int.from_bytes(raw[:8],'little')))
  else:
   need('pair-output-MVAR-byref:'+str(index),b'\x1e\x20',raw[10:12])
   owner=method_parameter_owner(md.buf,int.from_bytes(raw[:8],'little'),method_containers,source='storyShipDictionary.pair')
   need('pair-output-owner:'+str(index),(pair_method.index,index-3),(owner['methodIndex'],owner['ordinal']))
 # Fresh open constructor/Add declarations plus actual complete argument copies.
 ctor=md.methods[slots[4]['methodSpec'][0]];add=md.methods[slots[9]['methodSpec'][0]]
 for role,m in(('constructor',ctor),('Add',add)):
  need('Dictionary-method:'+role,('System.Collections.Generic.Dictionary`2',False,2,'void'),
   (image.type_name(m.declaring_type),bool(m.flags&16),m.parameter_count,ctx.type_name(m.return_type)))
 capacity,comparer=md.parameters_for(ctor);scalar.ordinary(image,ctx.type_pointer(capacity.type_index),8,'storyShipDictionary.capacity')
 comparison=cs.type(ctx.type_pointer(comparer.type_index));need('comparer-definition','System.Collections.Generic.IEqualityComparer`1',comparison['definition']['name'])
 item,=comparison['classArguments'];need('constructor-own-key',(ctor.declaring_type,0),(item['parameterOwner']['typeIndex'],item['parameterOwner']['ordinal']))
 containers=[t.generic_container_index for t in md.types]
 for ordinal,p in enumerate(md.parameters_for(add)):
  raw=image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16);need('Add-byvalue-VAR:'+str(ordinal),b'\x13\x00',raw[10:12])
  owner=type_parameter_owner(md.buf,int.from_bytes(raw[:8],'little'),containers,source='storyShipDictionary.Add')
  need('Add-owned-argument:'+str(ordinal),(add.declaring_type,ordinal),(owner['typeIndex'],owner['ordinal']))
 if value_profile=='cabin':
  constructor_calls=calls(bodies['constructor']);need('three-capacity-constructor-calls',3,len(constructor_calls))
  constructor_symbols=dict(zip(('initialize','defaultComparer','barrier'),constructor_calls,strict=True))
 else:
  constructor_symbols={role:_owned_call_after(bodies['constructor']['rows'],text)for role,text in
   dict(initialize='mov r8, [r8+0x8]',defaultComparer='mov rcx, [rcx+0x10]',barrier='mov [rbx+0x30], rdi').items()}
 need('same-ref-barrier',s['barrier'],constructor_symbols['barrier'])
 constructors=[constructor_source(bodies['constructor']['regions'],s['constructor'],constructor_symbols,positive=p,same_comparer=same)for p in(False,True)for same in(False,True)]
 insert,=calls(bodies['Add']);add_program=add_source(bodies['Add']['regions'],s['Add'],insert)
 dictionary_context_row=dictionary_helper_context(cs,ctor.declaring_type)
 dslots={r['relativeSlot']:r for r in dictionary_context_row['entries']}
 for slot,name in((1,'Initialize'),(24,'TryInsert')):
  declaration=dslots[slot];need('actual-Dictionary-helper:'+name,('System.Collections.Generic.Dictionary`2',name),(declaration['typeName'],declaration['methodName']))
  need('same-helper-owned-pair:'+name,[(ctor.declaring_type,0),(ctor.declaring_type,1)],
   [(a['parameterOwner']['typeIndex'],a['parameterOwner']['ordinal'])for a in declaration['classArguments']])
 default=dslots[2];need('same-key-default-comparer',('System.Collections.Generic.EqualityComparer`1','get_Default'),(default['typeName'],default['methodName']))
 item,=default['classArguments'];need('default-comparer-owned-key',(ctor.declaring_type,0),(item['parameterOwner']['typeIndex'],item['parameterOwner']['ordinal']))
 formatter_fields=list(md.fields_for(td));field,=formatter_fields;need('owned-comparer-field-name','equalityComparer',md.string(field.name_index))
 # Never read an open generic field offset. The registered witness's actual
 # comparer constructor supplies the complete unchanged reference store at16;
 # metadata independently owns the sole instance field and its TK carrier.
 overloads=[m for m in md.methods_for(td)if md.string(m.name_index)=='.ctor']
 default,=[m for m in overloads if m.parameter_count==0];compared,=[m for m in overloads if m.parameter_count==1]
 formatter_constructors=[]
 for declaration in(default,compared):
  observation,=ge.observe(declaration.index,['object',value_name],[])
  need('formatter-constructor-MethodSpec',declaration.index,ge.specs[observation['methodSpecIndex']][0])
  need('formatter-constructor-explicit-fold',True,declaration.index in observation['methodDefinitionIndices'])
  formatter_constructors.append(dict(registration=observation,body=owned(image,observation['pointer'])))
 default_body,compared_body=[item['body']for item in formatter_constructors]
 formatter_constructor_programs=[npc_collection_programs.dictionary_formatter_default(default_body['regions'],default_body['pointer'],compared_body['pointer']),
  npc_collection_programs.dictionary_formatter_comparer(compared_body['regions'],compared_body['pointer'],s['barrier'])]
 need('actual-formatter-field-store',16,formatter_constructor_programs[1]['storedUnchangedComparerOffset'])
 need('owned-comparer-instance-field',0,ctx.field_attributes(field.type_index)&16)
 field_type=cs.type(ctx.type_pointer(field.type_index));need('owned-comparer-field-type','System.Collections.Generic.IEqualityComparer`1',field_type['definition']['name'])
 item,=field_type['classArguments'];need('formatter-own-key',(td.index,0),(item['parameterOwner']['typeIndex'],item['parameterOwner']['ordinal']))
 pcontext=cs.context(slots[6]['methodSpec'][0],is_method=True);need('same-provider-method',slots[6]['methodSpec'][0],slots[7]['methodSpec'][0])
 validate_generic_contexts(image,[pcontext],label='storyShipDictionary.provider');pslots={r['relativeSlot']:r for r in pcontext['entries']}
 need('provider-open-slots',[0,1],sorted(pslots))
 for item in(pslots[0]['type'],pslots[1]['type']['classArguments'][0]):need('provider-own-MVAR',(pcontext['definition'],0),(item['parameterOwner']['methodIndex'],item['parameterOwner']['ordinal']))
 key_symbols={k:base+v for k,v in generic['referenceProviderSymbols'].items()}
 key_provider=lang_key_list_sources.wrapper_provider_program(bodies['keyProvider']['regions'],s['keyProvider'],key_symbols)
 value_calls=calls(bodies['valueProvider']);need('value-provider-hot-scope',True,len(value_calls)>=4)
 # The last three calls on the physical warm family are backend/indexed/cast;
 # the full program below independently enforces their exact data flow.
 value_symbols=dict(zip(('backend','indexed','cast')if value_profile=='cabin'else('backend','indexed','assignable'),value_calls[-3:],strict=True))
 type_handle,=[m for m in md.methods_for(ctx.index.types['System.Type'])if md.string(m.name_index)=='GetTypeFromHandle']
 need('Type-handle-static-one-Type',(True,1,'System.Type'),(bool(type_handle.flags&16),type_handle.parameter_count,ctx.type_name(type_handle.return_type)))
 value_symbols['typeHandle']=image.method_pointer_va(type_handle)
 value_provider=(value_provider48_program if value_profile=='cabin'else uint64.provider_program)(bodies['valueProvider']['regions'],s['valueProvider'],value_symbols)
 need('same-indexed-context',s['context'],value_symbols['indexed'])
 if value_profile=='cabin':
  cast=owned(image,value_symbols['cast']);predicate=next(control_transfer(r)['target']for r in cast['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8')
  cast_program=pooled_global_buff_id_sources.successful_cast(cast['regions'],cast['pointer'],predicate)
 else:
  need('same-inline-current-class-predicate',base+generic['referenceProviderSymbols']['assignable'],value_symbols['assignable'])
  cast_program=dict(inlineProviderPredicate=True,predicateTargetRva=value_symbols['assignable']-base,
   actualSelectedPredicateTrueRequired=True,returnedFullBackendReferenceUnchanged=True)
 backend=owned(image,value_symbols['backend']);backend_target=base+facts['levelscript_int_list_native.json']['bodies']['providerBackend']['entryRva']
 backend_program=numeric_list_sources.uint_backend_forward_program(backend['regions'],backend['pointer'],backend_target)
 factory=lang_key_list_sources.generic_provider_factory(image,pins,dict(backend=backend_target,context=s['context']),need)
 dictionary_factory=npc_collection_sources._factory(image,ctx,ge,core['collections'],need)
 need('same-provider-class',[factory['providerClassCell']]*3,[paths[1]['providerClassCell'],key_provider['providerClassCell'],value_provider['providerClassCell']])
 offsets=scalar.reader_offsets(image,'storyShipDictionary');offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
 header=dictionary_header_program(bodies['header']['regions'],s['header'],offsets)
 barrier,barrier_program,_=_fast_barrier(image,s['barrier'])
 for name,raw in deps.items():need('dependency-bookend:'+name,raw,(CONTRACTS_DIR/name).read_bytes())
 _publication_gate(image,pins)
 cap=dict(typeName=typename,keyType='string',valueType=value_name,countLimit=LIMIT,countRange=[-1,LIMIT],headerBytes=4,
  positiveCountsAdmitted=True,nullable=True,initiallyNullOutputRequired=True,valueManagedBytes=value_bytes,valueCapability=value_component['capability'],
  keyCallbackEqualsPooledStringRequired=True,valueCallbackEqualsCanonicalRequired=True,actualCallbackEqualsSourceWitnessRequired=True,
  sourceWitnessClassArguments=['object',value_name],actualClosedContextAndSourceBodyCompatibilityRequired=True,
  typedConstructorAndHelperCompatibilityRequired=True,normalNonthrowingInsertRequired=True,closedPointerEquivalenceProved=False,
  storedMapSemanticsAdmitted=False,runtimeProviderSelectionObserved=False,profileAdmitted=True,wholeGrammarAdmitted=False,
  packableReaderMethodDefinition=typed_request['methodSpec'][0],packableReaderTargetRva=call_target-base,parentFieldAdmitted=False,wholeOwnerAdmitted=False)
 return json.loads(json.dumps(dict(schema='endfield.story-ship-dictionary-source.v1'if value_profile=='cabin'else'endfield.story-ship-u64-dictionary-source.v1',
  status='validated-conditional-string-cabin-dictionary-profile'if value_profile=='cabin'else'validated-conditional-string-uint64-dictionary-profile',nativeInputs=pins,
  capability=cap,typedRequest=typed_request,closedCarrier=carrier,carrierExtent=extent,referenceParentSource=reference,
  sourceWitness=witness,sourceWitnessClassArguments=['object',value_name],closedPointerEquivalenceProved=False,
  proof=dict(context=context,contextProof=context_proof,sourceWindows=source['windows'],programs=paths,induction=induction,
   pair=pair_program,pairMethodDefinition=pair_method.index,value=value_component,keyString=string_proof,keyDispatch=dispatch_proof,
   constructors=constructors,formatterConstructors=_constructor_facts(formatter_constructors),formatterConstructorPrograms=formatter_constructor_programs,
   openGenericFieldOffsetsUsed=False,Add=add_program,DictionaryContext=dictionary_context_row,
   unselectedDictionaryContextSlotsAdmitted=False,keyProvider=key_provider,valueProvider=value_provider,
   cast=cast_program,backend=backend_program,providerContext=pcontext,factory=factory,dictionaryFactory=dictionary_factory,
   header=header,barrier=dict(source=barrier,proof=barrier_program),symbolRvas={key:target-base for key,target in s.items()},
   helperWindows={key:body['windows']for key,body in bodies.items()}),parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  evidenceBoundary=dict(exact='Actual closed string/Cabin reference parent; independently registered object/Cabin source witness, complete signed count/new/loop/key-value/Add48/local/frame source with induction, owned TK/TV constructor/Add/pair declarations, independent pooled string callback and actual matched canonical Cabin48 dispatcher.'if value_profile=='cabin'else
   'Actual closed string/UInt64 reference parent; independently registered object/UInt64 source witness and separate complete signed count/new/key-value/Add8/local/frame byte programs with EDI4096 induction. Exact owned TK/TV pair/constructor/Add contexts, independently proved pooled-string key callback and current UInt64 canonical raw8 callback/specialized dispatcher.',
   conditional='Actual selected dictionary callback equals the proved erased source witness and its closed MethodInfo/receiver/helper bodies are compatible with the independently authenticated string/Cabin context. Exact pooled-string and Cabin callbacks, coherent constructor/comparer/Initialize/TryInsert/context/provider/factory effects and normal nonthrowing Add remain required. Initially-null output, disjoint buffered/frame storage, finite floats/counts; positive padding unobserved.'if value_profile=='cabin'else
   'Actual selected dictionary callback equals the proved erased source witness and its closed MethodInfo/receiver/helper bodies are compatible with the independently authenticated string/UInt64 context. Exact pooled-string and UInt64 callbacks, coherent constructor/comparer/Initialize/TryInsert/context/provider/factory effects and normal nonthrowing Add remain required. Initially-null output, disjoint buffered/frame storage and bounded counts; live callback/context/provider selection unobserved.',
   unresolved=['closed dictionary pointer equivalence and runtime selected callbacks/helper contexts','hash/comparer/storage behavior and live provider/factory choice','actual enclosing field/store/owner/physical EOF']))))


def derive_cabin(image,pins,*,typed_request,call_target):
 return _derive_dictionary(image,pins,typed_request=typed_request,call_target=call_target,value_profile='cabin')

"""Own Rune UInt64/Int32 dictionary source, including its raw16 KV fast path.

The exact closed formatter reads a signed four-byte header. Each positive
iteration reads one constructed KeyValuePair<ulong,int> as sixteen raw bytes,
copies its key QWORD and value DWORD to Add and transports four padding bytes.
Individual key/value formatter arguments are unused by this selected KV body.
Actual typed formatter/internal MethodInfo contexts, initialized helpers,
fresh output, successful constructor/Add, enough stable buffered bytes and
disabled collector are conditions. No reused map, duplicate-map semantics,
parent setter/frame, whole Module or live selection is admitted.
"""
import copy
import json

from scripts.game_data.memorypack import levelscript_rune_dictionary_programs as paths

SCHEMA='endfield.story-rune-dictionary-sources.v1'
CAPABILITY='story-rune-u64-i32-dictionary'
DICTIONARY='System.Collections.Generic.Dictionary`2'
FORMATTER='MemoryPack.Formatters.DictionaryFormatter`2'
PAIR='System.Collections.Generic.KeyValuePair`2'
TYPE=DICTIONARY+'<ulong,int>'
PAIR_TYPE=PAIR+'<ulong,int>'
PARENT='Beyond.Gameplay.RunePuzzleData'
FIELD='anchorPointToIndexMap'


def need(check,condition):
 if not condition:raise ValueError('runeDictionarySource.'+check)


def require_carrier(carrier):
 need('exact-own-closed-dictionary',isinstance(carrier,dict)and carrier.get('name')==TYPE
  and carrier.get('definition',{}).get('name')==DICTIONARY and len(carrier.get('classArguments',[]))==2)
 for row,name,kind in zip(carrier['classArguments'],('ulong','int'),(11,8),strict=True):
  raw=bytes.fromhex(row.get('rawHex',''));need('exact-own-primitive-argument:'+name,row.get('name')==name
   and len(raw)==16 and raw[10:12]==bytes((kind,128)))
 return dict(typeName=TYPE,keyType='ulong',valueType='int',keyRawKind=11,valueRawKind=8,
  keyValueType=True,valueValueType=True)


def require_pair_parameters(parameters,*,method_definition,reader_definition):
 need('exact-five-KV-formal-parameters',len(parameters)==5)
 for i in(0,1):
  p=parameters[i];need('own-formatter-formal:'+str(i),p.get('definition',{}).get('name')=='MemoryPack.MemoryPackFormatter`1'
   and bytes.fromhex(p['rawHex'])[10:12]==bytes((21,0))and len(p.get('classArguments',[]))==1)
  arg,=p['classArguments'];need('own-reciprocal-KV-formatter-parameter',bytes.fromhex(arg['rawHex'])[10:12]==bytes((30,0))
   and(arg['parameterOwner'].get('methodIndex'),arg['parameterOwner'].get('ordinal'))==(method_definition,i))
 raw=bytes.fromhex(parameters[2]['rawHex']);need('own-Reader-byref-KV-formal',raw[10:12]==bytes((17,32))and int.from_bytes(raw[:8],'little')==reader_definition)
 for i in(0,1):
  p=parameters[i+3];need('own-reciprocal-KV-out-parameter',bytes.fromhex(p['rawHex'])[10:12]==bytes((30,32))
   and(p['parameterOwner'].get('methodIndex'),p['parameterOwner'].get('ordinal'))==(method_definition,i))


def validate_component(component,pins):
 need('own-component-schema-and-pins',isinstance(component,dict)and component.get('schema')==SCHEMA
  and component.get('status')=='validated-conditional-raw16-pair-dictionary-source'and component.get('nativeInputs')==pins)
 cap=component.get('capability');need('exact-finite-source-capability',isinstance(cap,dict)and cap.get('name')==CAPABILITY
  and cap.get('typeName')==TYPE and type(cap.get('countLimit'))is int and 3<=cap['countLimit']<=4096
  and cap.get('countRange')==[-1,cap['countLimit']]and cap.get('nullable')is True
  and(cap.get('keyType'),cap.get('valueType'),cap.get('keyRawKind'),cap.get('valueRawKind'))==('ulong','int',11,8)
  and cap.get('headerBytes')==4 and cap.get('pairWireBytes')==16 and cap.get('keyByteRange')==[0,8]
  and cap.get('valueByteRange')==[8,12]and cap.get('transportedPaddingByteRange')==[12,16]
  and cap.get('individualKeyValueCallbacksUsed')is False and cap.get('positiveSourceInductionProved')is True
  and cap.get('initiallyNullOutputRequired')is True and cap.get('actualTypedFormatterSelectionRequired')is True
  and cap.get('sourceOnly')is True and cap.get('parentFieldAdmitted')is False)
 need('exact-source-context-identities',isinstance(component.get('proof',{}).get('typedRequest'),dict)
  and component['proof']['typedRequest'].get('methodSpec',[None])[0]==cap.get('packableReaderMethodDefinition')
  and type(cap.get('packableReaderTargetRva'))is int and cap['packableReaderTargetRva']>0)
 return copy.deepcopy(cap)


def bind_request(pins,typed_request,source_target_rva,component):
 cap=validate_component(component,pins)
 need('same-actual-closed-parent-request',typed_request==component['proof']['typedRequest'])
 need('same-actual-parent-E8-target',type(source_target_rva)is int and source_target_rva==cap['packableReaderTargetRva'])
 return dict(capability=CAPABILITY,typeName=TYPE,typedRequest=copy.deepcopy(typed_request),sourceTargetRva=source_target_rva,
  packableReaderMethodDefinition=cap['packableReaderMethodDefinition'],pairWireBytes=16,
  parentFieldAdmitted=False,parentLocalStoreAndFrameRequired=True)


def derive_member(image,pins,source,member_index=2,*,count_limit=4096):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
 from scripts.game_data.memorypack import pointer_param as pointer
 _publication_gate(image,pins)
 need('exact-current-Rune-parent-source',source.get('nativeInputs')==pins and source.get('wrappedType')==PARENT
  and source.get('completeSelectedCallerAdmitted')is True and member_index==2)
 read,=[r for r in source['orderedSourceReads']if r['memberIndex']==member_index]
 need('exact-Rune-parent-member',(read.get('fieldName'),read.get('declaredType'))==(FIELD,TYPE))
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==PARENT]
 need('fresh-own-wrapper-member',source.get('wrapperName')==wrapper.name and len(wrapper.members)>member_index
  and(wrapper.members[member_index].name,wrapper.members[member_index].declared_type)==(FIELD,TYPE))
 method=pointer.methods(image,wrapper)['Deserialize'];body=pointer.owned(image,image.method_pointer_va(method))
 usage=derive_typed_usage_context(image,read['context']['instructionRva'],label=SCHEMA+'.actualParent')
 instruction=read['instruction'];image.check_instruction_windows([instruction],label=SCHEMA+'.actualParentE8')
 raw=bytes.fromhex(instruction[1]);need('exact-owned-parent-call',len(raw)==5 and raw[0]==0xe8
  and instruction[0]+5+int.from_bytes(raw[1:],'little',signed=True)==read['sourceTargetRva'])
 g=BytesPath(body['regions'],image.pe.image_base+instruction[0]);g.call(image.pe.image_base+read['sourceTargetRva'])
 g=BytesPath(body['regions'],image.pe.image_base+usage['instructionRva']);g.take(usage['instructionHex'])
 out=derive(image,pins,typed_request=usage,call_target=image.pe.image_base+read['sourceTargetRva'],count_limit=count_limit)
 out['actualParentBinding']=dict(bind_request(pins,usage,read['sourceTargetRva'],out),parentType=PARENT,fieldName=FIELD,
  memberIndex=member_index,instruction=list(instruction));_publication_gate(image,pins);return out


def derive(image,pins,*,typed_request,call_target,count_limit=4096):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.contracts import CONTRACTS_DIR
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.formatter_composition import _vtable
 from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar,modelview_packable_sources
 from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
 from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
 from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
 from scripts.game_data.memorypack.levelscript_interactive_sources import dictionary_context
 from scripts.game_data.memorypack.generated_called_advance_sources import derive as advance_source
 from scripts.game_data.memorypack.counted_loop_sources import prove_induction
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;cs=ContextSymbols(image);ge=GenericEntries(image)
 declaration_bytes={p:p.read_bytes()for p in(CONTRACTS_DIR/'npc_runtime_native.json',CONTRACTS_DIR/'leveldata_npc_patrol_native.json')}
 need('finite-positive-count-domain',type(count_limit)is int and 3<=count_limit<=4096)
 bind_typed_read(image,typed_request,method_name='ReadPackable',argument=TYPE,kind=21,reference=True)
 actual_arg,=image.instantiations.resolve(typed_request['methodSpec'][2]).arguments;carrier=cs.type(actual_arg.type_pointer_va);identity=require_carrier(carrier)
 core=_load('npc_runtime_native.json',pins)['readPackable'];routes=copy.deepcopy(_load('leveldata_npc_patrol_native.json',pins)['declarations']['adapters']['referenceRoutes']);routes['wrappers']=[]
 reference=modelview_packable_sources.validate_components(image,pins,core,routes)
 need('actual-reference-ReadPackable-target',type(call_target)is int and call_target==base+core['entryRva'])
 td=ctx.index.types[FORMATTER];method,=[m for m in md.methods_for(td)if md.string(m.name_index)=='Deserialize']
 need('own-slot5-formatter-ABI',not method.flags&16 and method.parameter_count==2 and method.slot==5 and ctx.type_name(method.return_type)=='void')
 _vtable(image,td.index,5,method.index,SCHEMA+'.slot5');context=cs.context(td.index);context_proof=dictionary_context(image,context)
 slots={r['relativeSlot']:r for r in context['entries']};reader,out=md.parameters_for(method)
 rr=image.pe.bytes_at_va(ctx.type_pointer(reader.type_index),16);vr=image.pe.bytes_at_va(ctx.type_pointer(out.type_index),16)
 declared=slots[3]['type']['rawHex']
 need('exact-own-Reader-and-Dictionary-byref',rr[10:12]==bytes((17,32))and int.from_bytes(rr[:8],'little')==ctx.index.types['MemoryPack.MemoryPackReader'].index
  and vr[10:12]==bytes((21,32))and vr[:8]==bytes.fromhex(declared)[:8])
 registration=ge.resolve(method.index,['ulong','int'],[]);body=pointer.owned(image,registration['pointer'])
 programs=[paths.dictionary(body['regions'],body['pointer'],count=n)for n in(-1,0,1,2,3)]
 induction=prove_induction(programs,initial='33f6',increment='ffc6',comparison='3b742478',counter='esi',saved_count='immutable signed DWORD RSP+120',
  max_count=count_limit,mode_key='newDictionary',backedge_sites=programs[2]['backedgeSites'])
 symbols={}
 for p in programs:
  for row in p['calls']:
   need('same-actual-helper-target:'+row['role'],row['role']not in symbols or symbols[row['role']]==row['targetVa']);symbols[row['role']]=row['targetVa']
 offsets=scalar.reader_offsets(image,SCHEMA);offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
 helper_registrations={}
 for role,slot,args in(('dictionary-constructor',4,['ulong','int']),('key-provider',6,[]),('value-provider',7,[])):
  selected=slots[slot];entry=ge.resolve(selected['methodSpec'][0],args,['ulong'if slot==6 else'int']if slot in(6,7)else[])
  if role=='dictionary-constructor':
   need('same-own-closed-helper-target:'+role,entry['pointer']==symbols[role]);helper_registrations[role]=entry
  else:
   actual_body=pointer.owned(image,symbols[role]);helper_registrations[role]=dict(registration=entry,actualDirectTargetRva=symbols[role]-base,
    actualCanonicalPointersEqual=entry['pointer']==symbols[role],canonicalPointerAliasClaimed=False,
    actualSourceWindows=actual_body['windows'],actualSourceRegions=[[a,h.hex().upper()]for a,h in actual_body['regions']],
    providerResultUnusedBySelectedKVSource=True,providerSelectionOrEffectsProved=False,normalNoninterferingProviderCallRequired=True)
 reader_td=ctx.index.types['MemoryPack.MemoryPackReader']
 header=pointer.owned(image,symbols['header']);header_program=paths.header(header['regions'],header['pointer'],offsets)
 pair=pointer.owned(image,symbols['key-value-pair']);pair_program=paths.pair(pair['regions'],pair['pointer'])
 pair_slot=slots[8];pair_method=md.methods[pair_slot['methodSpec'][0]]
 need('own-static-KV-specialization-request',(pair_slot['typeName'],pair_slot['methodName'])==('MemoryPack.Formatters.KeyValuePairFormatter','Deserialize')
  and bool(pair_method.flags&16)and pair_method.parameter_count==5 and ctx.type_name(pair_method.return_type)=='void')
 pair_parameters=[cs.type(ctx.type_pointer(p.type_index))for p in md.parameters_for(pair_method)]
 require_pair_parameters(pair_parameters,method_definition=pair_method.index,reader_definition=reader_td.index)
 pair_registered=ge.resolve(pair_method.index,[],['ulong','int'])
 need('same-actual-closed-KV-source',pair_registered['pointer']==pair['pointer'])
 pair_context=cs.context(pair_method.index,is_method=True);pair_slots={r['relativeSlot']:r for r in pair_context['entries']};raw_slot=pair_slots[0]
 need('actual-KV-reader-internal-method-context',raw_slot['kind']==3 and(raw_slot['typeName'],raw_slot['methodName'])==('MemoryPack.MemoryPackReader','DangerousReadUnmanaged')
  and raw_slot['classArguments']==[]and len(raw_slot['methodArguments'])==1)
 formal_pair,=raw_slot['methodArguments'];need('own-constructed-value-KV-formal',formal_pair['definition']['name']==PAIR
  and bytes.fromhex(formal_pair['rawHex'])[10:12]==bytes((21,128))and len(formal_pair['classArguments'])==2)
 for i,arg in enumerate(formal_pair['classArguments']):
  need('exact-reciprocal-KV-method-MVAR',bytes.fromhex(arg['rawHex'])[10:12]==bytes((30,0))
   and(arg['parameterOwner'].get('methodIndex'),arg['parameterOwner'].get('ordinal'))==(pair_method.index,i))
 pair_td=ctx.index.types[PAIR];fields=[f for f in md.fields_for(pair_td)if not ctx.field_attributes(f.type_index)&16];pair_fields=[]
 need('two-own-KV-fields',len(fields)==2)
 for i,(name,f)in enumerate(zip(('key','value'),fields,strict=True)):
  typ=cs.type(ctx.type_pointer(f.type_index));need('own-reciprocal-KV-field',md.string(f.name_index)==name
   and bytes.fromhex(typ['rawHex'])[10:12]==bytes((19,0))and(typ['parameterOwner'].get('typeIndex'),typ['parameterOwner'].get('ordinal'))==(pair_td.index,i))
  pair_fields.append(dict(name=name,fieldIndex=f.index,type=typ))
 raw_method=md.methods[raw_slot['methodSpec'][0]];parameters=list(md.parameters_for(raw_method))
 need('own-instance-out-aggregate-reader',not raw_method.flags&16 and raw_method.parameter_count==1 and ctx.type_name(raw_method.return_type)=='void')
 formal=cs.type(ctx.type_pointer(parameters[0].type_index));need('own-reciprocal-out-MVAR',bytes.fromhex(formal['rawHex'])[10:12]==bytes((30,32))
  and(formal['parameterOwner'].get('methodIndex'),formal['parameterOwner'].get('ordinal'))==(raw_method.index,0))
 raw_registered=ge.resolve(raw_method.index,[],[PAIR_TYPE]);need('same-actual-raw-KV-reader-entry',raw_registered['pointer']==pair_program['rawReaderTargetVa'])
 selected_pair,=image.instantiations.resolve(ge.specs[raw_registered['methodSpecIndex']][2]).arguments;pair_carrier=cs.type(selected_pair.type_pointer_va)
 need('same-exact-constructed-value-KV-argument',pair_carrier['definition']['name']==PAIR and bytes.fromhex(pair_carrier['rawHex'])[10:12]==bytes((21,128))
  and len(pair_carrier['classArguments'])==2)
 for a,b in zip(carrier['classArguments'],pair_carrier['classArguments'],strict=True):
  need('same-exact-dictionary-and-KV-primitive-argument',a['typePointerVa']==b['typePointerVa']and a['rawHex']==b['rawHex'])
 raw=pointer.owned(image,pair_program['rawReaderTargetVa']);raw_program=paths.raw_pair(raw['regions'],raw['pointer'],offsets)
 advanced=advance_source(image,pins,target=raw_program['advanceTargetVa'],offsets=offsets)
 add=pointer.owned(image,symbols['add']);added=paths.add(add['regions'],add['pointer']);add_method=md.methods[slots[9]['methodSpec'][0]]
 need('own-closed-Add-entry',ge.resolve(add_method.index,['ulong','int'],[])['pointer']==add['pointer'])
 dictionary_context_used=cs.context(ctx.index.types[DICTIONARY].index,slots=[24]);insert,=dictionary_context_used['entries']
 need('own-named-TryInsert-context-slot24',insert['relativeSlot']==24 and(insert['typeName'],insert['methodName'])==(DICTIONARY,'TryInsert'))
 need('same-actual-closed-TryInsert-target',ge.resolve(insert['methodSpec'][0],['ulong','int'],[])['pointer']==added['insertTargetVa'])
 def capture(b):return dict(windows=b['windows'],regions=[[a,h.hex().upper()]for a,h in b['regions']])
 cap=dict(name=CAPABILITY,typeName=TYPE,**{k:v for k,v in identity.items()if k!='typeName'},headerBytes=4,
  pairWireBytes=16,keyByteRange=[0,8],valueByteRange=[8,12],transportedPaddingByteRange=[12,16],
  countLimit=count_limit,countRange=[-1,count_limit],nullable=True,initiallyNullOutputRequired=True,individualKeyValueCallbacksUsed=False,
  positiveSourceInductionProved=True,actualTypedFormatterSelectionRequired=True,internalKVMethodInfoCompatibilityRequired=True,
  packableReaderMethodDefinition=typed_request['methodSpec'][0],packableReaderTargetRva=call_target-base,
  sourceMethodDefinition=method.index,sourceTargetRva=body['pointer']-base,sourceOnly=True,parentFieldAdmitted=False,
  referenceOrInt32DictionarySourceBorrowed=False,actualRuntimeSelectionObserved=False)
 result=dict(schema=SCHEMA,status='validated-conditional-raw16-pair-dictionary-source',nativeInputs=copy.deepcopy(pins),capability=cap,
  proof=dict(typedRequest=copy.deepcopy(typed_request),carrier=carrier,referenceParent=reference,formatterRegistration=registration,
   formatterContext=context,contextProof=context_proof,source=capture(body),programs=programs,induction=induction,
   readerOffsets=offsets,symbolRvas={k:v-base for k,v in symbols.items()},header=capture(header),headerProgram=header_program,
   headerMethodIdentityClaimed=False,headerSourceIdentity='actual owned caller E8 and complete Reader/out-count byte program',helperRegistrations=helper_registrations,
   pair=capture(pair),pairProgram=pair_program,pairRegistration=pair_registered,pairMethodContext=pair_context,pairFields=pair_fields,
   pairFormalParameters=pair_parameters,
   rawReader=capture(raw),rawReaderProgram=raw_program,rawReaderRegistration=raw_registered,rawReaderFormal=formal,closedPairCarrier=pair_carrier,
   advanceSource=advanced,add=capture(add),addProgram=added,DictionaryContextSlotsUsed=dictionary_context_used,disabledBarrier=_barrier(image,symbols['barrier'])),
  wholeOwnerAdmitted=False,parentFieldAdmitted=False,liveFormatterSelectionObserved=False,
  evidenceBoundary=dict(exact='Exact own ulong/int carrier and registered callback, complete header/new/null/count loop, internal constructed KV raw16 source/Advance and key8/value4 Add/TryInsert argument flow. No UInt64/reference specialization is substituted.',
   conditional=__doc__,structuralOnly='Ordered entry key/value bits and transported padding; mutable dictionary/hash/duplicate contents are not reconstructed.',
   unresolved=['normal constructor/provider/Add/TryInsert effects and actual coherent closed MethodInfo selection','refill/reused output/nonselected paths','parent field/local/full-frame and whole Module/host']))
 for path,raw in declaration_bytes.items():need('reference-source-declaration-bookend:'+path.name,path.read_bytes()==raw)
 validate_component(result,pins);_publication_gate(image,pins);return json.loads(json.dumps(result))

"""Exact canonical CabinSlotInfo value48 transfer; containers stay separate."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
import json
import struct
from scripts.game_data.memorypack.leveldata_cabin_value_sources import TYPE,derive_record


def adapter_program(regions,entry,s,*,null=False,create=True,dispatch=False):
 if any(type(value)is not bool for value in(null,create,dispatch)):raise ValueError('storyCabinTransfer.literal-adapter-path')
 g=BytesPath(regions,entry)
 if dispatch:
  g.take('48895c2408','48896c2410','4889742418','57','4883ec20','488b0a','498be9','498bf0','488bda');g.call(s['prepare'])
  g.take('488b3b')
  if g.relative('488d0d')!=s['adapter']:raise ValueError('storyCabinTransfer.exact-compared-canonical-adapter')
  g.take('488b8790010000','488bbf98010000','483bc1');g.branch('0f85',False);ready=flag(g);g.branch('0f84',False)
 else:
  g.take('48896c2410','4889742418','57','4883ec20');ready=flag(g)
  g.take('498bf9','498be8','488bf2');g.branch('0f84',False)
 g.take('488b4720','488bce','488b90c0000000','488b12');g.call(s['readNull']);g.take('84c0');g.branch('0f85',null)
 type_cell=None
 if null:g.take('0f57c0','0f114500','0f114510','0f114520');g.jump('e9')
 else:
  if not dispatch:g.take('48895c2430')
  g.take('488b4720');type_cell=g.relative('488b0d')
  g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('74',False,1)
  g.take('33d2','488bcb');g.call(s['typeHandle'])
  if not dispatch:g.take('488b5c2430')
  g.take('4885c0');g.branch('74',False,1)
  g.take('33d2','488bc8');g.call(s['creationTest']);g.take('84c0');g.branch('75',not create,1)
  if create:g.take('488b4720','488b88c0000000','488b4958');g.call(s['activate'])
  else:g.take('33c0');g.jump('eb',1)
  g.take('488b4f20','4c8bc0','488bd5','4c8b89c0000000','488bce','4d8b4918');g.call(s['nonnull'])
 if dispatch:g.take('488b5c2430')
 g.take('488b6c2438','488b742440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,metadataReadyFlag=ready,ff=null,createWrapperBeforeRead=None if null else create,
  defaultOutputBytes=48 if null else 0,outputBytes=48,typeClassCell=type_cell,sameIncomingReaderAndOutput=True,
  entryRspRestored=True,normalReturn=True,wireBytes=1 if null else None,childWireGrammarAdmitted=False,
  rcxSelectorUsed=False if dispatch else None)


def nonnull_program(regions,entry,s,*,wrapper_null=False):
 if type(wrapper_null)is not bool:raise ValueError('storyCabinTransfer.literal-wrapper-result')
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','4c89442418','57','4883ec50');ready=flag(g)
 g.take('498bf9','488bf2','488bd9');g.branch('0f84',False)
 provider=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
 g.take('488b4f20');g.call(s['resolve']);g.take('488b88c0000000','488b4920');g.call(s['wrapperProvider'])
 g.take('4885c0');g.branch('0f84',False)
 g.take('b905000000','4c8d4c2470','4c8bc3','488bd0');g.call(s['wrapperInvoke'])
 g.take('488b5c2470','4885db');g.branch('0f84',wrapper_null)
 if wrapper_null:g.take('0f57c0','0f1106','0f114610','0f114620');g.jump('e9')
 else:
  g.take('488b4f20');g.call(s['resolve']);g.take('ba08000000','488b88c0000000');g.call(s['indexed'])
  g.take('4c8bc0','488d4c2420','4c8bcb');g.call(s['conversion'])
  g.take('0f1000','0f104810','0f105020','0f1106','0f114e10','0f115620')
 g.take('488b5c2460','488b742468','4883c450','5f','c3')
 return dict(selectedBytes=g.seen,metadataReadyFlag=ready,returnedWrapperNull=wrapper_null,providerClassCell=provider,
  outputBytes=48,defaultOutputBytes=48 if wrapper_null else 0,copiedCompleteGetterBytes=0 if wrapper_null else 48,
  conversionInterfaceContextSlot=8,hiddenGetterOutputLocal=[32,80],wrapperOutputEntryHome=[24,32],
  sameIncomingReaderAndOutput=True,entryRspRestored=True,normalReturn=True,childWireGrammarAdmitted=False,
  frame=dict(entryRspDelta=-88,callShadow=[0,32],getterLocal=[32,80],savedRbxEntryHome=[8,16],savedRsiEntryHome=[16,24],
   wrapperEntryHome=[24,32],pushedNonvolatiles=['rdi']))


def conversion_program(regions,entry,prepare,*,ordinal):
 if type(ordinal)is not int or not 0<=ordinal<=16:raise ValueError('storyCabinTransfer.literal-owned-interface-ordinal')
 g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','48897c2418','4156','4883ec50','498b39','488bf1','488bcf','4d8bf1','498bd8');g.call(prepare)
 g.take('440fb78730010000','33c0','66413bc0');g.branch('73',False,1);g.take('488b97b0000000')
 for index in range(ordinal+1):
  g.take('0fb7c8','4803c9','48391cca');g.branch('74',index==ordinal,1)
  if index<ordinal:g.take('66ffc0','66413bc0');g.branch('72',True,1)
 g.take('0fb7c8','4803c9','486344ca08','4883c014','48c1e004','4803c7','4c8b08','488d4c2420','4c8b4008','498bd6')
 getter=g.at;g.take('41ffd1','488b5c2460','488b7c2470','0f1000','0f104810','0f1106','0f104020','488bc6','0f114e10','0f114620',
  '488b742468','4883c450','415e','c3')
 return dict(selectedBytes=g.seen,interfaceOrdinal=ordinal,interfaceMethodSlot=0,getterCall=getter,managedOutputBytes=48,
  hiddenGetterArguments=dict(rcx='owned local48',rdx='incoming R9 wrapper',r8='same selected GetValue MethodInfo'),
  rawCopySlices=[[0,16],[16,16],[32,16]],sameOutputReturnedInRax=True,normalReturn=True,entryRspRestored=True,
  frame=dict(entryRspDelta=-88,callShadow=[0,32],getterLocal=[32,80],savedEntryHomes=dict(rbx=[8,16],rsi=[16,24],rdi=[24,32]),pushedNonvolatiles=['r14']))


def derive(image,pins):
 """Fresh nominal source/canonical adapter/conversion; no parent proof input."""
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import pointer_param as pointer,buff_ptr_sources,event_args_paths,primitive_param
 from scripts.game_data.memorypack import scalar_param_native as scalar,pooled_global_buff_id_sources as provider_programs
 from scripts.game_data.memorypack.vector_layout import vector_recorder
 need=lambda k,e,a:scalar.need('storyCabinTransfer',k,e,a)
 _publication_gate(image,pins);record=derive_record(image,pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);ge=GenericEntries(image)
 need('same-current-record',pins,record['nativeInputs']);need('exact-owned-layout',(TYPE,48,[],[[44,48]]),
  (record['typeName'],record['managedBytes'],record['referenceLaneOffsets'],record['paddingByteRanges']))
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
 pair=record['pair'];face,=pair['composition']['interfaces'];td=md.types[wrapper.type_definition]
 section=md.sections['interfaceOffsets'];at=section.offset+td.interface_offsets_start*8
 ordinal=list(struct.iter_unpack('<ii',md.buf[at:at+td.interface_offsets_count*8])).index((face['interfaceTypeIndex'],face['interfaceOffset']))
 adapter_context,context_proof=buff_ptr_sources._adapter_context(image,ge);sources={};registrations={};symbols={}
 for role,name in(('adapter','Deserialize'),('nonnull','DeserializeNotNull')):
  method=buff_ptr_sources._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2',name)
  registration=ge.resolve(method.index,[TYPE,'object'],[]);registrations[role]=registration
  symbols[role]=registration['pointer'];sources[role]=pointer.owned(image,registration['pointer'])
 def calls(body):return[control_transfer(r)['target']for r in body['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8']
 adapter_calls=calls(sources['adapter']);need('complete-adapter-hot-calls',True,len(adapter_calls)>=5)
 for key,target in zip(('readNull','typeHandle','creationTest','activate','nonnull'),adapter_calls[:5],strict=True):
  if key in symbols:need('same-canonical-source:'+key,symbols[key],target)
  symbols[key]=target
 nonnull_calls=calls(sources['nonnull']);need('complete-nonnull-hot-calls',True,len(nonnull_calls)>=6)
 need('same-context-resolver',nonnull_calls[0],nonnull_calls[3])
 symbols.update(dict(zip(('resolve','wrapperProvider','wrapperInvoke','indexed','conversion'),
  [nonnull_calls[n]for n in(0,1,2,4,5)],strict=True)))
 for key in('readNull','wrapperInvoke','conversion'):sources[key]=pointer.owned(image,symbols[key])
 null_calls=calls(sources['readNull']);need('complete-read-null-hot-calls',True,len(null_calls)>=2)
 symbols.update(peek=null_calls[0],header=null_calls[1]);sources['peek']=pointer.owned(image,symbols['peek'])
 symbols['prepare']=calls(sources['conversion'])[0]
 need('named-TypeFromHandle',base+pair['registration']['helperMethods']['typeFromHandle'][3],symbols['typeHandle'])
 programs=dict(adapter=[adapter_program(sources['adapter']['regions'],symbols['adapter'],symbols,**mode)for mode in({},dict(create=False),dict(null=True))],
  nonnull=[nonnull_program(sources['nonnull']['regions'],symbols['nonnull'],symbols,wrapper_null=value)for value in(False,True)],
  conversion=conversion_program(sources['conversion']['regions'],symbols['conversion'],symbols['prepare'],ordinal=ordinal),
  readNull=[provider_programs.read_null_program(sources['readNull']['regions'],symbols['readNull'],symbols,null=value)for value in(False,True)])
 invocation=deserialize_slot(sources['wrapperInvoke']['regions'],symbols['wrapperInvoke'],prepare=symbols['prepare'],
  callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]))
 offsets=scalar.reader_offsets(image,'storyCabinTransfer');peek=event_args_paths.peek(sources['peek']['regions'],symbols['peek'],offsets)
 header=vector_recorder(image)(symbols['header']-base);primitive_param.object_header_source(image,header,offsets)
 _publication_gate(image,pins)
 cap=dict(typeName=TYPE,memberCount=4,managedBytes=48,referenceLaneOffsets=[],paddingByteRanges=[[44,48]],
  positiveWireBytes=45,canonicalFFWireBytes=1,canonicalFFDefaultManagedBytes=48,positivePaddingSerialized=False,
  canonicalAdapterAdmitted=True,finiteFloatProfile=True,actualCallbackEqualsCanonicalRequired=True,
  profileAdmitted=True,wholeGrammarAdmitted=False,liveFormatterSelectionObserved=False)
 return json.loads(json.dumps(dict(schema='endfield.story-cabin-value-transfer.v1',status='validated-conditional-cabin-value48-profile',nativeInputs=pins,
  capability=cap,record=record,proof=dict(registrations=registrations,adapterContext=adapter_context,adapterContextProof=context_proof,
   interfaceOrdinal=ordinal,programs=programs,wrapperInvocation=invocation,peek=peek,header=header,
   symbolRvas={key:target-base for key,target in symbols.items()},sourceWindows={key:value['windows']for key,value in sources.items()}),
  containerAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
   exact='Fresh CabinSlotInfo nominal48 source/getter/zeroing/fields; registered canonical adapter FF/new/reuse and independent wrapper-null/nonnull source, exact owned interface getter conversion/local/frame and all48 bits copied unchanged.',
   conditional='Actual callback equals the freshly proved canonical adapter; closed MethodInfo/provider contexts, returned wrapper class and its current interface table select the proved Cabin wrapper/getter. Ready coherent helpers and disjoint buffered/frame/output storage; finite floating values only. Positive padding is not serialized or fabricated.',
   unresolved=['dictionary/list framing/callback and actual enclosing parent','runtime provider/formatter/class selection','whole owner/physical EOF']))))


def derive_dispatch(image,pins,*,call_target):
 """Own an actual matched value48 dispatcher; caller argument flow is separate."""
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.memorypack.pointer_param import owned
 from scripts.game_data.memorypack import scalar_param_native as scalar
 _publication_gate(image,pins);value=derive(image,pins);base=image.pe.image_base
 symbols={key:base+rva for key,rva in value['proof']['symbolRvas'].items()}
 source=owned(image,call_target)
 programs=[adapter_program(source['regions'],call_target,symbols,dispatch=True,**mode)for mode in({},dict(create=False),dict(null=True))]
 scalar.need('storyCabinTransfer','unused-entry-selector',[False]*3,[p['rcxSelectorUsed']for p in programs])
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-cabin-value-dispatch.v1',status='validated-conditional-cabin-value48-dispatch',nativeInputs=pins,
  value=value,capability=value['capability'],sourceTargetRva=call_target-base,readerRegister='r8',outputRegister='r9',
  formatterRegister='rdx',entryRcxSelectorUsed=False,actualCallerArgumentFlowRequired=True,
  programs=programs,sourceWindows=source['windows'],containerAdmitted=False,wholeOwnerAdmitted=False,
  evidenceBoundary=dict(exact='Actual complete value48 dispatcher compares its selected callback to the independently proved current canonical Cabin adapter, owns FF/new/reuse and forwards the same Reader/output/context. Entry RCX is overwritten before use.',
   conditional=value['evidenceBoundary']['conditional'],unresolved=['actual enclosing caller argument/context joins','runtime callback/provider selection','container/whole owner/EOF']))))

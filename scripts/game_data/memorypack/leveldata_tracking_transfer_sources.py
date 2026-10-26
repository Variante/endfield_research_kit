"""Tracking value canonical callbacks and hidden getters, separate from raw reads.

The two nominal wrappers have no reference lanes. Their canonical adapters
consume FF as one byte and zero the complete Original output, or invoke the
independently proved wrapper and copy its complete hidden getter result.
Runtime provider/callback and closed-context selection remain explicit
conditions; a matching managed width never selects a callback or wire grammar.
"""
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.leveldata_tracking_value_sources import BOUNDS,POINT,SPECS,derive_record

LABEL='storyTrackingTransfer'
SCHEMA='endfield.story-tracking-value-transfer.v1'


def need(check,condition):
 if not condition:raise ValueError(LABEL+'.'+check)


def adapter_program(regions,entry,s,*,type_name,null=False,create=True):
 """Complete ready-metadata canonical callback, including owned default output."""
 need('finite-type-and-path',type_name in SPECS and type(null)is bool and type(create)is bool)
 bounds=type_name==BOUNDS;g=BytesPath(regions,entry)
 g.take('488bc4','48895808','48896810','48897018','48897820','4156','4883ec20','33ff')
 g.take('498be9'if bounds else'498bf1');ready=g.relative('40383d')
 g.take('498bf0'if bounds else'498be8','4c8bf2');g.branch('75',True,1)
 g.take('488b4520'if bounds else'488b4620','498bce','488b90c0000000','488b12')
 g.call(s['readNull']);g.take('84c0');g.branch('75',null,1)
 type_cell=None;type_site=None
 if null:
  g.take('0f57c0')
  if bounds:g.take('33c0','0f1106','0f114610','894620')
  else:g.take('0f114500')
 else:
  g.take('488b4520'if bounds else'488b4620');type_site=g.at;type_cell=g.relative('488b0d')
  g.take('488b98c0000000','488b5b50');g.call(s['classInit'])
  g.take('33d2','488bcb');g.call(s['typeHandle']);g.take('4885c0');g.branch('75',True,1)
  g.take('33d2','488bc8');g.call(s['creationTest']);g.take('84c0');g.branch('75',not create,1)
  if create:
   g.take('488b4520'if bounds else'488b4620','488b88c0000000','488b4958')
   g.call(s['activate']);g.take('488bf8')
  g.take('488b4d20'if bounds else'488b4e20','4c8bc7','488bd6'if bounds else'488bd5',
   '4c8b89c0000000','498bce','4d8b4918');g.call(s['nonnull']);g.jump('eb',1)
 g.take('488b5c2430','488b6c2438','488b742440','488b7c2448','4883c420','415e','c3')
 return dict(selectedBytes=g.seen,typeName=type_name,metadataReadyFlag=ready,typeClassCell=type_cell,typeClassInstruction=type_site,
  null=null,createWrapper=None if null else create,defaultOutputBytes=SPECS[type_name]['managedBytes']if null else 0,
  managedOutputBytes=SPECS[type_name]['managedBytes'],sameIncomingReaderAndOutput=True,
  actualNullWireBytes=1 if null else None,frame=dict(entryRspDelta=-40,shadowBytes=32,
   savedEntryHomes=dict(rbx=[8,16],rbp=[16,24],rsi=[24,32],rdi=[32,40]),pushed=['r14']),
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,
  actualCallbackSelectionObserved=False,wrapperWireGrammarAdmitted=False)


def nonnull_program(regions,entry,s,*,type_name,wrapper_null=False):
 """Slot5 wrapper invocation, then default or complete hidden getter output."""
 need('finite-type-and-wrapper-result',type_name in SPECS and type(wrapper_null)is bool)
 bounds=type_name==BOUNDS;size=80 if bounds else 48;g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','4c89442418','57','4883ec'+bytes((size,)).hex());ready=flag(g)
 g.take('498bf1','488bda','488bf9');g.branch('75',True,1)
 provider_site=g.at;provider=g.relative('488b0d');g.call(s['classInit'])
 g.take('488b4e20');g.call(s['resolve']);g.take('488b88c0000000','488b4920');g.call(s['wrapperProvider'])
 g.take('4885c0');g.branch('75',True,1)
 home='70'if bounds else'50'
 g.take('b905000000','4c8d4c24'+home,'4c8bc7','488bd0');invoke=g.at;g.call(s['wrapperInvoke'])
 g.take('488b7c24'+home,'4885ff');g.branch('75',not wrapper_null,1)
 conversion=None
 if wrapper_null:
  g.take('0f57c0')
  if bounds:g.take('33c0','0f1103','0f114310','894320')
  else:g.take('0f1103')
  g.jump('eb',1)
 else:
  g.take('488b4e20');g.call(s['resolve']);g.take('488b88c0000000','488b4940');g.call(s['resolve'])
  if bounds:g.take('4c8bcf','488d4c2420','4c8bc0')
  else:g.take('33d2','488d4c2420','4c8bcf','4c8bc0')
  conversion=g.at;g.call(s['conversion'])
  if bounds:g.take('0f1000','8b4820','0f104810','0f1103','0f114b10','894b20')
  else:g.take('0f1000','f30f7f03')
 g.take('488b5c24'+('60'if bounds else'40'),'488b7424'+('68'if bounds else'48'),
  '4883c4'+bytes((size,)).hex(),'5f','c3')
 return dict(selectedBytes=g.seen,typeName=type_name,metadataReadyFlag=ready,providerClassCell=provider,providerClassInstruction=provider_site,
  wrapperNull=wrapper_null,managedOutputBytes=SPECS[type_name]['managedBytes'],
  defaultZeroBytes=SPECS[type_name]['managedBytes']if wrapper_null else 0,
  copiedCompleteGetterBytes=0 if wrapper_null else SPECS[type_name]['managedBytes'],
  wrapperInvokeInstructionVa=invoke,conversionInstructionVa=conversion,wrapperSlot=5,conversionMethodSlot=0,
  sameIncomingReaderAndOutput=True,referenceLaneOffsets=[],frame=dict(entryRspDelta=-(size+8),
   shadow=[0,32],hiddenGetterLocal=[32,32+SPECS[type_name]['managedBytes']],
   wrapperEntryHome=[24,32],savedEntryHomes=dict(rbx=[8,16],rsi=[16,24]),pushed=['rdi']),
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True)


def conversion_program(regions,entry,prepare,*,type_name,ordinal):
 """Exact selected interface-table hit; unresolved/fallback paths stay closed."""
 need('finite-conversion',type_name in SPECS and type(ordinal)is int and 0<=ordinal<=32)
 bounds=type_name==BOUNDS;g=BytesPath(regions,entry)
 g.take('48895c2408','48896c2410','4889742418')
 if bounds:g.take('57','4883ec50','498b19','488be9','488bcb','498bf9','498bf0')
 else:g.take('48897c2420','4156','4883ec30','498b19','4c8bf1','488bcb','0fb7ea','498bf9','498bf0')
 g.call(prepare)
 if bounds:g.take('440fb78330010000','33d2','66413bd0')
 else:g.take('0fb79330010000','4533d2','66443bd2')
 g.branch('73',False,1);g.take('488b8bb0000000')
 for i in range(ordinal+1):
  g.take('0fb7c2'if bounds else'410fb7c2','4803c0','483934c1');g.branch('74',i==ordinal,1)
  if i<ordinal:g.take('66ffc2'if bounds else'6641ffc2','66413bd0'if bounds else'66443bd2');g.branch('72',True,1)
 if bounds:g.take('488b83b0000000','0fb7ca','4803c9','486344c808')
 else:g.take('410fb7d2','4803d2','8b44d108','03c5','4898')
 g.take('4883c014','48c1e004','4803c3');g.jump('eb',1)
 g.take('4c8b08','488d4c2420','4c8b4008','488bd7');getter=g.at;g.take('41ffd1')
 if bounds:g.take('488b5c2460','488b742470','0f1000','0f104810','8b4020','0f114500','0f114d10','894520',
  '488bc5','488b6c2468','4883c450','5f','c3')
 else:g.take('488b5c2440','488b6c2448','488b742450','0f1000','488b7c2458','498bc6','410f1106','4883c430','415e','c3')
 width=SPECS[type_name]['managedBytes']
 return dict(selectedBytes=g.seen,typeName=type_name,interfaceOrdinal=ordinal,getValueMethodSlot=0,
  incomingSelectorRequired=0 if not bounds else None,managedOutputBytes=width,
  getterCallInstructionVa=getter,hiddenGetterArguments=dict(rcx='owned local',rdx='same wrapper R9',r8='selected getter MethodInfo'),
  copiedSlices=[[0,16],[16,16],[32,4]]if bounds else[[0,16]],sameOutputReturnedInRax=True,
  referenceLaneOffsets=[],frame=dict(entryRspDelta=-88 if bounds else-56,shadow=[0,32],getterLocal=[32,32+width]),
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,interfaceFallbackAdmitted=False)


def null_program(regions,entry,s,*,null=False):
 need('literal-null',type(null)is bool);g=BytesPath(regions,entry)
 g.take('4053','4883ec20','488bd9','c644243000');g.call(s['peek']);g.take('84c0');g.branch('75',null,1)
 if null:g.take('488d542430','488bcb');g.call(s['header']);g.take('b001')
 else:g.jump('eb',1)
 g.take('4883c420','5b','c3')
 return dict(selectedBytes=g.seen,null=null,consumedBytes=int(null),entryRspRestored=True,normalReturn=True)


def derive(image,pins,type_name):
 """Fresh own wrapper/canonical/default/getter composition; no parent/list."""
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import pointer_param as pointer,buff_ptr_sources,event_args_paths,primitive_param
 from scripts.game_data.memorypack import scalar_param_native as scalar,pooled_global_buff_id_sources as provider
 from scripts.game_data.memorypack.vector_layout import vector_recorder
 _publication_gate(image,pins);need('finite-owned-type',type_name in SPECS)
 record=derive_record(image,pins,type_name);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);ge=GenericEntries(image)
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==type_name]
 pair=record['pair'];face,=pair['composition']['interfaces'];td=md.types[wrapper.type_definition]
 section=md.sections['interfaceOffsets'];at=section.offset+td.interface_offsets_start*8
 ordinal=list(struct.iter_unpack('<ii',md.buf[at:at+td.interface_offsets_count*8])).index((face['interfaceTypeIndex'],face['interfaceOffset']))
 adapter_context,context_proof=buff_ptr_sources._adapter_context(image,ge);sources={};registrations={};s={}
 for role,name in(('adapter','Deserialize'),('nonnull','DeserializeNotNull')):
  method=buff_ptr_sources._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2',name)
  registration=ge.resolve(method.index,[type_name,'object'],[]);registrations[role]=registration
  s[role]=registration['pointer'];sources[role]=pointer.owned(image,s[role])
 def calls(source):return[control_transfer(r)['target']for r in source['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8']
 ac=calls(sources['adapter']);nc=calls(sources['nonnull'])
 need('complete-canonical-calls',len(ac)==8 and len(nc)==9)
 for role,index in dict(readNull=1,classInit=2,typeHandle=3,creationTest=5,activate=6,nonnull=7).items():
  need('same-owned-nonnull',role not in s or s[role]==ac[index]);s[role]=ac[index]
 need('same-nonnull-initializer',nc[1]==s['classInit'])
 need('same-reciprocal-context-resolver',nc[2]==nc[6]==nc[7])
 s.update(resolve=nc[2],wrapperProvider=nc[3],wrapperInvoke=nc[5],conversion=nc[8])
 for role in('readNull','conversion','wrapperInvoke','classInit'):sources[role]=pointer.owned(image,s[role])
 convert_calls=calls(sources['conversion']);need('owned-preparation-entry',len(convert_calls)>=2);s['prepare']=convert_calls[0]
 null_calls=calls(sources['readNull']);need('exact-null-helper-calls',len(null_calls)==2);s.update(peek=null_calls[0],header=null_calls[1])
 need('named-TypeFromHandle',s['typeHandle']==base+pair['registration']['helperMethods']['typeFromHandle'][3])
 programs=dict(adapter=[adapter_program(sources['adapter']['regions'],s['adapter'],s,type_name=type_name,**p)
  for p in({},dict(create=False),dict(null=True))],nonnull=[nonnull_program(sources['nonnull']['regions'],s['nonnull'],s,type_name=type_name,wrapper_null=v)for v in(False,True)],
  conversion=conversion_program(sources['conversion']['regions'],s['conversion'],s['prepare'],type_name=type_name,ordinal=ordinal),
  readNull=[null_program(sources['readNull']['regions'],s['readNull'],s,null=v)for v in(False,True)])
 invocation=deserialize_slot(sources['wrapperInvoke']['regions'],s['wrapperInvoke'],prepare=s['prepare'],
  callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]))
 initialized=provider.ready_class_init(sources['classInit']['regions'],s['classInit'])
 offsets=scalar.reader_offsets(image,LABEL);sources['peek']=pointer.owned(image,s['peek'])
 peek=event_args_paths.peek(sources['peek']['regions'],s['peek'],offsets)
 header=vector_recorder(image)(s['header']-base);primitive_param.object_header_source(image,header,offsets)
 classes=[]
 for role,items,instruction_key,cell_key,expected in(
  ('Type',programs['adapter'],'typeClassInstruction','typeClassCell','System.Type'),
  ('provider',programs['nonnull'],'providerClassInstruction','providerClassCell','MemoryPack.MemoryPackFormatterProvider')):
  site=next(p[instruction_key]for p in items if p[instruction_key]is not None)
  usage=derive_typed_usage_context(image,site-base,label=LABEL+'.'+role)
  need('actual-owned-class:'+role,(usage['tag'],usage['typeName'])==(1,expected)
   and all(p[cell_key]in(None,base+usage['usageCellRva'])for p in items))
  classes.append(usage)
 _publication_gate(image,pins)
 width=SPECS[type_name]['managedBytes'];count=len(SPECS[type_name]['order'])
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-tracking-value-transfer',nativeInputs=pins,
  typeName=type_name,wrapperName=wrapper.name,managedBytes=width,referenceLaneOffsets=[],paddingByteRanges=[],
  canonicalFFWireBytes=1,canonicalFFDefaultManagedBytes=width,positiveMemberCount=count,positiveWireBytes=1+12*(3 if type_name==BOUNDS else 1)+(0 if type_name==BOUNDS else 4),
  canonicalCallbackTargetRva=s['adapter']-base,canonicalCallbackAdmitted=True,wrapperGrammarAdmitted=True,
  actualCallbackEqualsCanonicalRequired=True,liveFormatterSelectionObserved=False,parentFieldAdmitted=False,containerAdmitted=False,wholeOwnerAdmitted=False,
  record=record,proof=dict(registrations=registrations,adapterContext=adapter_context,adapterContextProof=context_proof,
   interfaceOrdinal=ordinal,programs=programs,wrapperInvocation=invocation,initializedClassHelper=initialized,actualClasses=classes,peek=peek,header=header,
   symbolRvas={k:v-base for k,v in s.items()},sourceWindows={k:v['windows']for k,v in sources.items()},
   sourceRegions={key:[(at,data.hex().upper())for at,data in value['regions']]for key,value in sources.items()}),
  evidenceBoundary=dict(exact='Own nominal wrapper MC/FF/new/reused sources, zero constructors, canonical adapter/default output, slot5 wrapper invocation and hidden GetValue interface transfer of all managed16/36 bits.',
   conditional='Actual compatible formatter slot5 equals this exact canonical callback; its coherent initialized closed MethodInfo represents the independently proved nominal Original/wrapper pair and selects that wrapper/getter. Ready metadata/provider/classes, normal Win64 helpers, disjoint buffered input/Reader/output/frame. Runtime callback/provider replacement and selection are not observed.',
   structuralOnly='Raw coordinates/bounds/match-mode bits retained without runtime tracking semantics.',
   unresolved=['actual enclosing field/local/frame transfer','container count/callback/Add','runtime callback/provider selection','whole owner/physical EOF']))))

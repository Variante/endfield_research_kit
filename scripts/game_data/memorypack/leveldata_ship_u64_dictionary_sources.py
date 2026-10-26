"""Finite string/UInt64 dictionary source, independent of the Cabin48 shape.

The object-key specialization is a source witness only. No pooled-string key,
UInt64 callback or concrete closed pointer identity follows from that witness.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag

TYPE='System.Collections.Generic.Dictionary`2<string,ulong>'
LIMIT=4096


def dictionary_program(regions,entry,s,*,count):
 if type(count)is not int or not -1<=count<=3:raise ValueError('storyShipU64Dictionary.finite-count-witness')
 g=BytesPath(regions,entry)
 g.take('4053','55','56','57','4157','4883ec50');ready=flag(g)
 g.take('498bd9','498bf0','4c8bfa','488be9');g.branch('75',True,1)
 g.take('33ff','488d942488000000','498bcf','89bc2488000000','48897c2430','48897c2438')
 g.call(s['header']);g.take('84c0');g.branch('0f84',count==-1)
 provider=None;callbacks=[];adds=[]
 if count==-1:
  g.take('488bce','48893e');g.call(s['barrier']);g.take('90');g.jump('e9')
 else:
  g.take('4c89b42498000000','4c89a42480000000','4c89ac2490000000','448bb42488000000','48393e');g.branch('0f85',False)
  g.take('488b4b20','ba03000000','4c8b6510','488b89c0000000');g.call(s['context']);g.take('488bc8');g.call(s['allocate'])
  g.take('488be8','4885c0');g.branch('0f84',False)
  g.take('488b4b20','488b91c0000000','488b4a20','48397920');g.branch('0f84',False)
  g.take('488b4320','4d8bc4','418bd6','488bcd','4c8b88c0000000','4d8b4920');g.call(s['constructor'])
  g.take('488bce','48892e');g.call(s['barrier']);provider=g.relative('488b0d')
  g.take('39b9e0000000');g.branch('75',True,1)
  g.take('488b4320','488b88c0000000','488b4930');g.call(s['keyProvider'])
  g.take('488b4b20','488be8','488b89c0000000','488b4938');g.call(s['valueProvider'])
  g.take('4c8be0','4585f6');g.branch('0f8f',count>0)
  for index in range(count):
   g.take('488b4b20','488d442438','4c8d4c2430','4d8bc7','488b91c0000000','488b4a40','498bd4','48894c2428','488bcd','4889442420')
   callbacks.append(g.at);g.call(s['keyValue'])
   g.take('488b442430','4c8b2e','4889442440','488b442438','4889842488000000','4d85ed');g.branch('0f84',False)
   g.take('488b4320','488b88c0000000','488b4148','4883782000');g.branch('75',True,1)
   g.take('488b4320','498bcd','4c8b842488000000','488b542440','4c8b88c0000000','4d8b4948')
   adds.append(g.at);g.call(s['Add']);g.take('ffc7','413bfe');g.branch('0f8c',index+1<count)
  if count:g.jump('e9')
  g.take('4c8bac2490000000','4c8ba42480000000','4c8bb42498000000')
 g.take('4883c450','415f','5f','5e','5d','5b','c3')
 return dict(selectedBytes=g.seen,metadataReadyFlag=ready,countWitness=count,newDictionary=True,headerBytes=4,
  elementCallbackSites=callbacks,keyValueCallbackSites=callbacks,AddCallSites=adds,providerClassCell=provider,
  keyManagedBytes=8,valueManagedBytes=8,keyWireGrammarAdmitted=False,valueWireGrammarAdmitted=False,
  constructorCapacityEqualsSavedCount=count!=-1,constructorComparerFromFormatterOffset=16,
  initiallyNullOutputRequired=True,closedPointerEquivalenceProved=False,normalReturn=True,entryRspRestored=True,
  counter='EDI starts0/increments1',savedCount='R14D unchanged',frame=dict(entryRspDelta=-120,callShadow=[0,32],
   stackCallArguments=[[32,40],[40,48]],keyOutputLocal=[48,56],valueOutputLocal=[56,64],savedKeyLocal=[64,72],
   headerThenValueEntryHome=[16,24],savedEntryHomes=dict(r12=[8,16],r13=[24,32],r14=[32,40]),
   pushedNonvolatiles=['rbx','rbp','rsi','rdi','r15']))


def constructor_program(regions,entry,s,*,positive,same_comparer):
 if type(positive)is not bool or type(same_comparer)is not bool:raise ValueError('storyShipU64Dictionary.literal-constructor-path')
 g=BytesPath(regions,entry)
 g.take('48895c2408','48896c2410','4889742418','57','4883ec20','498be9','498bf8','8bf2','488bd9','85d2');g.branch('0f88',False)
 g.take('85d2');g.branch('7f',positive,1)
 if positive:
  g.take('498b4120','488b88c0000000','488b4108','4883782000');g.branch('0f84',False)
  g.take('488b4520','8bd6','488bcb','4c8b80c0000000','4d8b4008');g.call(s['initialize']);g.jump('eb',1)
 g.take('488b4520','488b88c0000000','488b4910');g.call(s['defaultComparer'])
 g.take('483bf8');g.branch('74',same_comparer,1)
 if not same_comparer:g.take('488d4b30','48897b30');g.call(s['barrier'])
 g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,positiveCapacity=positive,sameComparer=same_comparer,capacityUnchanged=True,
  comparerReferenceUnchanged=True,comparerFieldOffset=48,initializeContextSlot=1,defaultComparerContextSlot=2,
  normalReturn=True,entryRspRestored=True,closedPointerEquivalenceProved=False,
  actualInitializeAndComparerNormalCompatibilityRequired=True,storageAndHashSemanticsAdmitted=False)


def pair_program(regions,entry,s):
 g=BytesPath(regions,entry)
 g.take('488bc4','48895808','48896810','48897018','48897820','4156','4883ec30',
  '488be9','4d8bf1','488b4c2468','498bd8','488bfa','4883793800');g.branch('75',True,1)
 g.take('0f57c0','0f11442420','488b742460','33c0','498906','488906','4885ed');g.branch('74',False,1)
 g.take('8d4805','4d8bce','4c8bc3','488bd5');g.call(s['keyDispatch']);g.take('4885ff');g.branch('74',False,1)
 g.take('4c8bce','4c8bc3','488bd7');g.call(s['valueDispatch'])
 g.take('488b5c2440','488b6c2448','488b742450','488b7c2458','4883c430','415e','c3')
 return dict(selectedBytes=g.seen,keyOutputBytesZeroed=8,valueOutputBytesZeroed=8,
  sameIncomingReader=True,keyDispatchSelector=5,keyOutputRegister='r9',valueOutputRegister='r9',
  valueDispatcherRcxSelectorRequired=False,valueDispatcherMustProveUnusedRcx=True,
  keyFormatter='incoming RCX',valueFormatter='incoming RDX',reader='incoming R8',
  normalReturn=True,entryRspRestored=True,keyWireGrammarAdmitted=False,valueWireGrammarAdmitted=False,
  frame=dict(entryRspDelta=-56,callShadow=[0,32],unusedZeroLocal=[32,48],
   incomingArgumentHomes=dict(valueOutput=40,methodInfo=48),
   savedEntryHomes=dict(rbx=[8,16],rbp=[16,24],rsi=[24,32],rdi=[32,40]),pushedNonvolatiles=['r14']))


def add_program(regions,entry,insert):
 g=BytesPath(regions,entry)
 g.take('48895c2408','48896c2410','4889742418','57','4883ec30','498b4120','498bd9','498bf8','488bf2','488be9',
  '4c8b88c0000000','498b81c0000000','4883782000');g.branch('0f84',False)
 g.take('488b4320','41b102','4c8bc7','488bd6','488b88c0000000','488b81c0000000','488bcd','4889442420');g.call(insert)
 g.take('488b5c2440','488b6c2448','488b742450','4883c430','5f','c3')
 return dict(selectedBytes=g.seen,valueManagedBytes=8,valueBits=64,valueRegisterUnchanged='incoming R8→RDI→R8',
  insertionBehaviorLiteral=2,insertionMethodContextSlot=24,keyReferenceUnchanged=True,
  normalReturn=True,entryRspRestored=True,storedMapSemanticsAdmitted=False,actualInsertNormalCompatibilityRequired=True,
  frame=dict(entryRspDelta=-56,callShadow=[0,32],methodInfoArgument=[32,40],
   savedEntryHomes=dict(rbx=[8,16],rbp=[16,24],rsi=[24,32]),pushedNonvolatiles=['rdi']))


def dispatch_program(regions,entry,o,s):
 cur,rem,adv,used=(bytes((o[k],)).hex()for k in('currentPtr','bufferLength','advancedCount','consumed'))
 g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','57','4883ec20','488b0a','498bf9','498bd8','488bf2');g.call(s['prepare'])
 g.take('488b06','4c8b9090010000','4c8b8898010000')
 if g.relative('488d05')!=s['callback']:raise ValueError('storyShipU64Dictionary.exact-UInt64-callback')
 g.take('4c3bd0');g.branch('0f85',False)
 g.take('837b'+rem+'08');g.branch('0f8c',False)
 g.take('488b43'+cur,'488b00','488907','8b7b'+rem,'83c7f8');g.branch('0f88',False)
 g.take('488343'+cur+'08','8343'+adv+'08','8343'+used+'08','897b'+rem,
  '488b5c2430','488b742438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,wireBytes=8,resultBytes=8,rawBits=64,formatterRegister='rdx',
  readerRegister='r8',outputRegister='r9',entryRcxSelectorUsed=False,normalReturn=True,entryRspRestored=True,
  actualCallbackEqualsCanonicalRequired=True,headerBytes=0,nullMarkerAdmitted=False,
  frame=dict(entryRspDelta=-40,callShadow=[0,32],savedEntryHomes=dict(rbx=[8,16],rsi=[16,24]),pushedNonvolatiles=['rdi']))


def provider_program(regions,entry,s):
 """Actual UInt64 provider has an inline class predicate, not Cabin's cast."""
 g=BytesPath(regions,entry)
 g.take('48895c2410','57','4883ec20','4883793800','488bf9');g.branch('74',False,1)
 type_cell=g.relative('488b0d');g.take('488b5f38','83b9e000000000','488b1b');g.branch('0f84',False)
 g.take('33d2','488bcb');g.call(s['typeHandle']);provider=g.relative('488b0d')
 g.take('488bd8','83b9e000000000');g.branch('74',False,1)
 g.take('488bcb');g.call(s['backend']);g.take('488b4f38','ba01000000','488bd8');g.call(s['indexed'])
 g.take('4885db');g.branch('0f84',False)
 g.take('488b0b','488bd0');g.call(s['assignable']);g.take('84c0');g.branch('0f84',False)
 g.take('488bc3','488b5c2438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,typeClassCell=type_cell,providerClassCell=provider,contextSlots=[0,1],
  inlinePredicate=True,predicateMustBeTrue=True,returnedBackendFullReferenceUnchanged=True,
  normalReturn=True,entryRspRestored=True,actualRuntimeProviderChoiceObserved=False,closedPointerEquivalenceProved=False)


def derive_dispatch(image,pins,*,call_target):
 import json
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.context import type_parameter_owner
 from scripts.game_data.il2cpp.formatter_composition import _vtable
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.memorypack import scalar_param_native as scalar
 from scripts.game_data.memorypack.levelscript_collection_sources import ulong_formatter_program
 from scripts.game_data.memorypack.pointer_param import owned
 need=lambda k,e,a:scalar.need('storyShipU64Dictionary.value',k,e,a)
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image)
 td=ctx.index.types['MemoryPack.Formatters.UnmanagedFormatter`1']
 method,=[m for m in md.methods_for(td)if md.string(m.name_index)=='Deserialize']
 registration=ge.resolve(method.index,['ulong'],[]);argument,=registration['classInstantiation']['arguments']
 raw=image.pe.bytes_at_va(argument['type_pointer_va'],16)
 need('exact-ordinary-UInt64',('ulong',b'\x0b\x80'),(ContextSymbols(image).type(argument['type_pointer_va'])['name'],raw[10:12]))
 need('instance-void-slot5-two',(0,5,2,'void'),(method.flags&16,method.slot,method.parameter_count,ctx.type_name(method.return_type)))
 _vtable(image,td.index,5,method.index,'storyShipU64Dictionary.value')
 reader,out=md.parameters_for(method);rr=image.pe.bytes_at_va(ctx.type_pointer(reader.type_index),16);vr=image.pe.bytes_at_va(ctx.type_pointer(out.type_index),16)
 need('formatter-exact-Reader-byref',(b'\x11\x20',ctx.index.types['MemoryPack.MemoryPackReader'].index),(rr[10:12],int.from_bytes(rr[:8],'little')))
 need('formatter-output-owned-VAR-byref',b'\x13\x20',vr[10:12])
 owner=type_parameter_owner(md.buf,int.from_bytes(vr[:8],'little'),[t.generic_container_index for t in md.types],source='storyShipU64Dictionary.value')
 need('formatter-output-owner',(td.index,0),(owner['typeIndex'],owner['ordinal']))
 source=owned(image,registration['pointer']);offsets=scalar.reader_offsets(image,'storyShipU64Dictionary.value')
 canonical=ulong_formatter_program(source['regions'],source['pointer'],offsets)
 actual=owned(image,call_target);prepare=next(control_transfer(r)['target']for r in actual['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8')
 program=dispatch_program(actual['regions'],call_target,offsets,dict(prepare=prepare,callback=registration['pointer']))
 _publication_gate(image,pins)
 cap=dict(typeName='ulong',managedBytes=8,wireBytes=8,rawBits=64,headerBytes=0,nullMarkerAdmitted=False,
  actualCallbackEqualsCanonicalRequired=True,profileAdmitted=True,wholeGrammarAdmitted=True,liveFormatterSelectionObserved=False)
 return json.loads(json.dumps(dict(schema='endfield.story-ship-uint64-dispatch-source.v1',status='validated-conditional-uint64-dispatch',nativeInputs=pins,
  capability=cap,sourceTargetRva=call_target-base,prepareTargetRva=prepare-base,readerRegister='r8',outputRegister='r9',formatterRegister='rdx',entryRcxSelectorUsed=False,
  proof=dict(registration=registration,canonicalWindows=source['windows'],canonicalProgram=canonical,
   actualWindows=actual['windows'],actualProgram=program),containerAdmitted=False,wholeOwnerAdmitted=False,
  evidenceBoundary=dict(exact='Fresh exact UInt6411/128 canonical slot5/byref VAR ABI and raw64 callback; actual specialized dispatcher compares that pointer and preserves all8 bits with exact Reader updates and Win64 frame. Entry RCX selector is overwritten before use.',
   conditional='Actual coherent formatter/context, successful type preparation and sufficiently buffered stable disjoint nonwrapping input/output. Matching compared callback is required; fallback/refill effects and live selection are unobserved.'))))


def derive(image,pins,*,typed_request,call_target):
 from scripts.game_data.memorypack.leveldata_ship_dictionary_sources import _derive_dictionary
 return _derive_dictionary(image,pins,typed_request=typed_request,call_target=call_target,value_profile='uint64')

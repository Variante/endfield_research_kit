"""Selected canonical reference adapters and their actually inlined dispatch."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def flag(g):g.relative('803d');g.take('00')

def cache(g,s,kind):
 """Same initialized first class-key probe, with all live-register variants."""
 d=kind=='dispatch';n=kind=='nonnull';w=kind=='wrapper'
 g.take('b201','488bcb');g.call(s['classFromType'])
 if d:g.take('488d5820','48899c24b8000000')
 elif n:g.take('488d5820','48895c2420')
 else:g.take('4c8d6820','4c896c2420' if w else '4c89ac24e8000000')
 cell=g.relative('488b3d');g.take('488b8f80000000');enter=g.relative('ff15');g.take('90','488b4740')
 if d:g.take('4533f6')
 g.take('483b4738');g.branch('75',True,1)
 if d:g.take('498bf6','4c8b4748','49ffc8','4c898424c8000000','488bcb')
 else:g.take('33f6','4c8b7f48','49ffcf','488bcb' if n else '498bcd')
 g.call(s['hash']);g.take('488bd8')
 if d:g.take('4923d8','4c8b6768','8b6f50','488d0c5b','413b2ccc')
 else:g.take('4c8b7768','8b6f50','4c8b6f38' if n else '4c8b6738','4923df','488d0c5b','413b2cce')
 g.branch('75',True,1)
 if d:g.take('4c397738');g.branch('76',True,1)
 else:g.take('4d85ed' if n else '4d85e4');g.branch('74',True,1)
 g.take('488d045b','453934c4' if d else '41833cc600');g.branch('75',False,1)
 g.take('498b54c408' if d else '498b54c608','488b8c24b8000000' if d else '488b4c2420' if n else '498bcd');g.call(s['compare']);g.take('85c0');g.branch('74',True,1)
 g.take('4883fbff');g.branch('74',False,1);g.take('488d0c5b','498d14cc' if d else '498d14ce','488b4748','488d0c40','488b4768','488d0cc8','483bd1');g.branch('74',False,1)
 g.take('488b4a10','488b4770','4c8b2cc8' if w else '488b34c8','488b8f80000000');leave=g.relative('ff15');g.take('90')
 if kind=='provider':g.take('488b6c2450','488b7c2430')
 elif n:g.take('488b6c2430','4c8bb424d8000000','4c8bbc24c0000000')
 g.jump('e9')
 return dict(cacheCell=cell,enterCell=enter,leaveCell=leave,key='same class byval type at +32',entryStride=24,keyOffset=8,valueIndexOffset=16,valueArrayOffset=112,resultRegister='r13' if w else 'rsi',firstProbeMatch=True)

def provider_tail(g,s,kind):
 n=kind=='nonnull'
 g.relative('488b0d');g.take('83b9e000000000');g.branch('75',True,1);flag(g);g.branch('75',True,1);g.relative('488b0d');g.take('83b9e000000000');g.branch('75',True,1)
 g.take('488bce');g.call(s['backend']);g.take('488bd8','ba01000000','488b4d38');g.call(s['indexed']);g.take('4885db');g.branch('74' if n else '0f84',False,1 if n else 4)
 g.take('488bd0','488b0b');g.call(s['assignable']);g.take('84c0');g.branch('0f85' if n else '0f84',n)

def notnull_end(g,s,kind,wrapper_null):
 n=kind=='nonnull';d=kind=='dispatch'
 if d:
  g.take('488b4f20');g.call(s['context']);g.take('488b88c0000000','488b4920');g.call(s['hotProvider']);g.take('4885c0');g.branch('0f84',False)
  g.take('b905000000','4c8d8c24b8000000','4d8bc7','488bd0');g.call(s['dispatch']);g.take('488b9c24b8000000','4885db');g.branch('0f84',wrapper_null)
 elif n:
  g.take('b905000000','4c8d8c24d0000000','4d8bc7','488bd3');g.call(s['dispatch']);g.take('488b9c24d0000000','4885db');g.branch('75',not wrapper_null,1)
 else:
  g.take('b905000000','4c8d4c2428','4c8b8424d8000000','488bd3');g.call(s['dispatch']);g.take('488b5c2428','4885db');g.branch('75',not wrapper_null,1)
 if wrapper_null:
  if d:g.take('33c0','49894500');g.jump('e9')
  elif n:g.take('33c0','49890424');g.jump('eb',1)
  else:g.take('33c9','488b8424e0000000','488908');g.jump('e9')
 else:
  g.take('498b4e20' if n else '488b4f20');g.call(s['context']);g.take('ba08000000','488b88c0000000');g.call(s['indexed']);g.take('488bd0','33c9','4c8bc3');g.call(s['conversion'])
  if d:g.take('49894500');flag_prefix='833d';g.relative(flag_prefix);g.take('00');g.branch('0f84',True)
  elif n:g.take('49890424');g.relative('833d');g.take('00');g.branch('74',True,1)
  else:g.take('4c8b8424e0000000','498900');g.relative('833d');g.take('00');g.branch('0f84',True)

def finish(g,kind):
 g.take('488b9c24'+('c8000000' if kind=='nonnull' else 'b0000000' if kind=='dispatch' else 'd0000000'),'4881c480000000' if kind=='nonnull' else '4883c470' if kind=='dispatch' else '4881c490000000','415f','415e','415d','415c','5f','5e','5d','c3')

def nonnull(regions,entry,s,*,wrapper_null=False):
 g=BytesPath(regions,entry);g.take('48895c2410','4c894c2420','4c89442418','48894c2408','55','56','57','4154','4155','4156','4157','4881ec80000000','4d8bf1','4c8be2','4c8bf9');flag(g);g.branch('75',True,1)
 g.relative('488b0d');g.take('83b9e000000000');g.branch('75',True,1);g.take('498b4e20');g.call(s['context']);g.take('488b88c0000000','488b6920','48896c2430','48837d3800');g.branch('75',True,1)
 g.take('488b5d38','488b1b');g.relative('488b0d');g.take('83b9e000000000');g.branch('75',True,1);g.take('4885db');g.branch('0f84',False);g.take('83b9e000000000');g.branch('75',True,1)
 cp=cache(g,s,'nonnull');provider_tail(g,s,'nonnull');notnull_end(g,s,'nonnull',wrapper_null);finish(g,'nonnull')
 return dict(selectedBytes=g.seen,cache=cp,outputBytes=8,wrapperNull=wrapper_null,reader='incoming RCX preserved in R15',originalOutput='incoming RDX preserved in R12',wrapperTemporary='incoming R8 saved to entry RSP+24',typedContextSlots=dict(wrapperProvider=4,conversionInterface=8),normalReturn=True)

def main(regions,entry,s,*,null=False,create=True,wrapper_null=False):
 g=BytesPath(regions,entry);g.take('48895c2408','4c894c2420','4c89442418','4889542410','55','56','57','4154','4155','4156','4157','4881ec90000000','498bd9','498bf0','488bfa');flag(g);g.branch('75',True,1)
 g.take('837f3001');g.branch('7d',True,1);g.take('488b4750','8038ff');g.branch('75',not null,1)
 if null:
  g.take('837f3001');g.branch('7d',True,1);g.take('8b5f30','83eb01');g.branch('79',True,1);g.take('895f30','48ff4750','ff4740','ff4744','33c0','488906');proofs=[]
 else:
  g.take('488b4320','488b98c0000000','488b5b50');g.relative('488b0d');g.take('83b9e000000000');g.branch('75',True,1);g.take('4885db');g.branch('0f84',False);g.take('83b9e000000000');g.branch('75',True,1);wrapper_cache=cache(g,s,'wrapper')
  g.take('4d85ed');g.branch('0f84',False);g.take('b944000000','498bd5');g.call(s['typeFlags']);g.take('488b9c24e8000000','a980000000');g.branch('76',create,1)
  if create:g.take('488b4320','488b88c0000000','488b4958');g.call(s['factory'])
  else:g.take('33c0');g.jump('eb',1)
  g.take('488b4b20','488b91c0000000','488b7a18','48897c2430','4889442428');flag(g);g.branch('75',True,1);g.relative('488b0d');g.take('83b9e000000000');g.branch('75',True,1);g.take('488b4f20');g.call(s['context']);g.take('488b88c0000000','488b6920','48896c2450','48837d3800');g.branch('75',True,1)
  g.take('488b5d38','488b1b');g.relative('488b0d');g.take('83b9e000000000');g.branch('75',True,1);g.take('4885db');g.branch('0f84',False);g.take('83b9e000000000');g.branch('75',True,1);provider_cache=cache(g,s,'provider');provider_tail(g,s,'main');notnull_end(g,s,'main',wrapper_null);proofs=[wrapper_cache,provider_cache]
 finish(g,'main');return dict(selectedBytes=g.seen,caches=proofs,null=null,create=create,wrapperNull=wrapper_null,outputBytes=8,normalReturn=True,sameIncomingReaderAndOutput=True)

def dispatch(regions,entry,s,*,null=False,create=True,wrapper_null=False):
 g=BytesPath(regions,entry);g.take('48895c2408','55','56','57','4154','4155','4156','4157','4883ec70','4d8be9','4d8bf8','488bfa','0fb7d9','488b0a');g.call(s['prepare']);g.take('488d4b14','4803c9','488b07','4c8b14c8','488b5cc808','48899c24c0000000')
 if g.relative('488d05')!=s['main']:raise ValueError('bbReferenceDispatch.canonical-target')
 g.take('4c3bd0');g.branch('0f85',False);flag(g);g.branch('75',True,1);g.take('41837f3001');g.branch('7d',True,1);g.take('498b4750','8038ff');g.branch('75',not null,1)
 if null:
  g.take('41837f3001');g.branch('7d',True,1);g.take('418b5f30','83eb01');g.branch('79',True,1);g.take('41895f30','49ff4750','41ff4740','41ff4744','33c0','49894500');g.jump('e9');cp=None
 else:
  g.take('488b4320','488b98c0000000','488b5b50');g.relative('488b0d');g.take('83b9e000000000');g.branch('75',True,1);g.take('4885db');g.branch('0f84',False);g.take('83b9e000000000');g.branch('75',True,1);cp=cache(g,s,'dispatch')
  g.take('4885f6');g.branch('0f84',False);g.take('b944000000','488bd6');g.call(s['typeFlags']);g.take('488b9c24c0000000','a980000000');g.branch('77',not create,1)
  if create:g.take('488b4320','488b88c0000000','488b4958');g.call(s['factory']);g.take('4c8bf0')
  g.take('488b4320','488b88c0000000','488b7918','4c89b424b8000000');flag(g);g.branch('75',True,1);g.relative('488b0d');g.take('83b9e000000000');g.branch('75',True,1);notnull_end(g,s,'dispatch',wrapper_null)
 finish(g,'dispatch');return dict(selectedBytes=g.seen,cache=cp,null=null,create=create,wrapperNull=wrapper_null,slot=5,outputBytes=8,normalReturn=True,sameIncomingReaderAndOutput=True,canonicalPointerMatched=True)

def conversion(regions,entry,prepare,getter,*,ordinal):
 if type(ordinal)is not int or not 0<=ordinal<=8:raise ValueError('bbReferenceConversion.ordinal')
 g=BytesPath(regions,entry);g.take('4053','55','56','57','4155','4883ec40','498b30','498bf8','0fb7e9','488bda','488bce');g.call(prepare);g.take('440fb78630010000','4533ed','410fb7c5','66453be8');g.branch('73',False,1);g.take('488b96b0000000')
 for i in range(ordinal+1):
  g.take('0fb7c8','4803c9','48391cca');g.branch('74',i==ordinal,1)
  if i<ordinal:g.take('66ffc0','66413bc0');g.branch('72',True,1)
 g.take('0fb7d0','488b86b0000000','4803d2','8b44d008','03c5','4898','4883c014','48c1e004','4803c6','4c8b00','488b5808');excluded=[]
 for i in range(3):
  target=g.relative('488d05')
  if target==getter:raise ValueError('bbReferenceConversion.unproved-inline-getter')
  excluded.append(target)
  if i==0:g.take('4c89742478','4c89bc2488000000')
  g.take('4c3bc0');g.branch('0f84' if i==2 else '74',False,4 if i==2 else 1)
 g.take('488bd3','488bcf','41ffd0','4c8bbc2488000000','4c8b742478','4883c440','415d','5f','5e','5d','5b','c3')
 return dict(selectedBytes=g.seen,interfaceOrdinal=ordinal,selector=0,getterReceiver='incoming R8 wrapper preserved in RDI',getterMethodInfo='selected interface slot MethodInfo',sameFullReferenceReturned=True,excludedInlineGetters=excluded,normalReturn=True)

def class_hash(regions,entry):
 g=BytesPath(regions,entry);g.take('4053','4883ec20','480fbe410a','8b5908','4869d0dba2fa1c','0fb6410a','48c1eb1d','83e301','4803da','3c12');g.branch('75',False,1);g.take('4869c3dba2fa1c','480301','4883c420','5b','c3')
 return dict(selectedBytes=g.seen,typeKind=18,preservesR8=True,calleeCalls=0,condition='Matching coherent non-generic reference wrapper class byval type (kind CLASS).')

def read_null(regions,entry,*,null=False):
 g=BytesPath(regions,entry);g.take('4053','4883ec20','83793001','488bd9');g.branch('0f8c',False);g.take('488b4350','8038ff');g.branch('74',null,1)
 if null:g.take('837b3001','48897c2430');g.branch('0f8c',False);g.take('8b7b30','83ef01');g.branch('0f88',False);g.take('48ff4350','ff4340','ff4344','897b30','488b7c2430','b001');g.jump('eb',1)
 else:g.take('32c0')
 g.take('4883c420','5b','c3');return dict(selectedBytes=g.seen,null=null,consumedBytes=1 if null else 0,returnsComparisonTo255=True)

import json,struct
from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts,validate_registered_formatter_composition
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
from scripts.game_data.memorypack.reference_conversion_sources import validate_conversion_context
from scripts.game_data.memorypack.scalar_param_native import owned_method_abi,ordinary,reader_offsets

def validate_reference_routes(image,fact,compositions):
 """Recheck typed identities, owned windows and each selected program every time."""
 offsets=reader_offsets(image,'referenceAdapter')
 if offsets!={'currentPtr':80,'bufferLength':48,'advancedCount':64,'consumed':68}:raise ValueError('referenceAdapter.reader-field-layout:'+str(offsets))
 base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;entries=GenericEntries(image);regions={};programs={}
 def fail(key,expected,actual):raise ValueError(f'referenceAdapter.{key}:expected={str(expected)[:160]}:actual={str(actual)[:160]}')
 for program in fact['ownedPrograms']:
  entry=program['entryRva'];windows=program['windows'];wanted=sorted((p['startRva'],p['endRva']) for p in windows)
  if program['leaf']:
   if wanted!=[(entry,entry+5)] or image.pe.bytes_at_va(base+entry,5)!=bytes.fromhex('488b4110c3'):fail('getter-complete-leaf','ref8 +16 then RET',entry)
  elif sorted(tuple(p['runtimeTriple'][:2]) for p in image.unwind_index.family(entry)['ranges'])!=wanted:fail('complete-owned-method',wanted,entry)
  image.check_windows(windows,label='referenceAdapter');programs[entry]=program;regions[base+entry]=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva'])) for w in windows]
 image.check_windows(fact['leafWindows'],label='referenceAdapter')
 for w in fact['leafWindows']:regions[base+w['startRva']]=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))]
 s={k:base+v for k,v in fact['symbolRvas'].items()};canonical={}
 for name,row in fact['canonicalEntries'].items():
  method=md.methods[row['definition']]
  if image.type_name(method.declaring_type)!='Beyond.MemoryPack.GenericMemoryPackFormatter`2' or md.string(method.name_index)!=name:fail('canonical-method',name,row['definition'])
  actual=entries.resolve(row['definition'],['object','object'],[])
  if json.loads(json.dumps(actual))!=row['registration']:fail('canonical-registration',row['registration'],actual)
  canonical[name]=actual['pointer']
 if s['main']!=canonical['Deserialize']:fail('matched-main-entry',canonical['Deserialize'],s['main'])
 context=fact['context'];validate_generic_contexts(image,[context],label='referenceAdapter');typed=validate_conversion_context(image,context,entries,fail=fail);slots={e['relativeSlot']:e for e in context['entries']}
 if slots[7]['index']!=slots[10]['index'] or (slots[7]['kind'],slots[10]['kind'])!=(2,1):fail('factory-wrapper-type','same VAR1',slots[10])
 for slot,owner,name,ordinals in ((0,context['typeName'],'ReadIsNull',[0,1]),(3,context['typeName'],'DeserializeNotNull',[0,1]),(11,'System.Activator','CreateInstance',[1])):
  e=slots[slot];args=e['classArguments'] if slot!=11 else e['methodArguments']
  if e['kind']!=3 or (e['typeName'],e['methodName'])!=(owner,name) or [a['parameterOwner']['ordinal'] for a in args]!=ordinals or any(a['parameterOwner']['typeIndex']!=context['definition'] for a in args):fail('adapter-factory-context',slot,e)
 proofs=[]
 for create in (True,False):
  for null in (False,True):
   proofs.extend((main(regions[s['main']],s['main'],s,create=create,wrapper_null=null),dispatch(regions[s['dispatch']],s['dispatch'],s,create=create,wrapper_null=null)))
 for null in (False,True):proofs.append(nonnull(regions[canonical['DeserializeNotNull']],canonical['DeserializeNotNull'],s,wrapper_null=null))
 for fn,entry in ((main,s['main']),(dispatch,s['dispatch'])):proofs.append(fn(regions[entry],entry,s,null=True))
 for null in (False,True):proofs.append(read_null(regions[canonical['ReadIsNull']],canonical['ReadIsNull'],null=null))
 proofs.append(class_hash(regions[s['hash']],s['hash']))
 g=BytesPath(regions[s['context']],s['context']);g.take('f6813801000001');g.branch('74',False,1);g.take('488bc1');g.jump('eb',1);g.take('c3')
 g=BytesPath(regions[s['indexed']],s['indexed']);g.take('488bc1','4863ca','488b0cc8')
 if g.relative('e9')!=s['context']:fail('indexed-context-tail',s['context'],g.at)
 selected=[]
 for row,composition in zip(fact['wrappers'],compositions,strict=True):
  original,name=row['original'],row['wrapper'];td=image.body_index.types[name]
  if ctx.is_value_type(original) or ctx.is_value_type(name) or ctx.field(name+'::__instance')!=(name,original,16):fail('reference-holder',(original,name),ctx.field(name+'::__instance'))
  validate_registered_formatter_composition(image,composition,label='referenceAdapter')
  registration,=composition['registrations'];interface,=composition['interfaces']
  wrapper_pointer=image.instantiations.resolve(registration['classInstantiation']).arguments[1].type_pointer_va
  if image.pe.bytes_at_va(wrapper_pointer,16)[10:12]!=bytes((18,0)):fail('class-key-hash-selection','ordinary concrete CLASS wrapper',name)
  if (registration['originalType'],registration['wrapperType'],interface['originalType'],interface['wrapperType'])!=(original,name,original,name):fail('concrete-composition',row,registration)
  methods={md.string(m.name_index):m for m in md.methods_for(td)};getter=methods['GetValue'];return_raw=image.pe.bytes_at_va(ctx.type_pointer(getter.return_type),16)
  if return_raw[10] not in (18,21):fail('reference-return-kind','CLASS or generic reference',return_raw.hex())
  owned_method_abi(image,ctx,getter.index,td.index,(original,return_raw[10],True),[],'referenceAdapter.getter')
  for method_row in (row['getter'],row['forwarder'],row['reader']):image.validate_method_row(method_row,label='referenceAdapter')
  pointer=image.method_pointer_va(getter)
  if pointer!=base+row['getter'][3] or image.pe.bytes_at_va(pointer,5)!=bytes.fromhex('488b4110c3'):fail('getter-source','full ref8 holder load',pointer)
  section=md.sections['interfaceOffsets'];a=section.offset+td.interface_offsets_start*8;pairs=list(struct.iter_unpack('<ii',md.buf[a:a+td.interface_offsets_count*8]));ordinal=pairs.index((interface['interfaceTypeIndex'],interface['interfaceOffset']))
  if ordinal!=row['interfaceOrdinal']:fail('interface-ordinal',row['interfaceOrdinal'],ordinal)
  forwarder=md.methods[row['forwarder'][0]];parameters=list(md.parameters_for(forwarder));static=methods['Deserialize'];reader_parameters=list(md.parameters_for(static))
  if forwarder.flags&16 or not static.flags&16 or len(parameters)!=2 or len(reader_parameters)!=2:fail('forwarder-static-arity','instance2/static2',[forwarder.parameter_count,static.parameter_count])
  if md.string(forwarder.name_index)!='Deserialize' or forwarder.declaring_type!=interface['formatterDefinition'] or forwarder.index!=interface['formatterDeserializeMethodIndex']:fail('selected-slot-five-method',interface,forwarder.index)
  for method in (forwarder,static):
   raw=image.pe.bytes_at_va(ctx.type_pointer(method.return_type),16)
   ordinary(image,ctx.type_pointer(method.return_type),1,'referenceAdapter.void')
   if ctx.type_name(method.return_type)!='void':fail('void-return','void',ctx.type_name(method.return_type))
   for p,expected,kind in zip(md.parameters_for(method),('MemoryPack.MemoryPackReader',name),(17,18),strict=True):
    raw=image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16)
    if (ctx.type_name(p.type_index),raw[10],raw[11])!=(expected,kind,32):fail('reader-output-byref',(expected,kind,32),raw.hex())
  program=programs[row['forwarder'][3]];forward_rows=[r for w in program['windows'] for r in image.body_index._decode(base+w['startRva'],w['endRva']-w['startRva'])]
  prove_zero_wrapper_forwarder(forward_rows,{k:base+v for k,v in row['forwarderSymbolRvas'].items()},base+row['reader'][3])
  selected.extend((conversion(regions[s['conversion']],s['conversion'],base+fact['conversionPrepareRva'],pointer,ordinal=ordinal),deserialize_slot(regions[s['dispatch']],s['dispatch'],prepare=s['prepare'],callback=base+row['forwarder'][3])))
 return dict(typedContext=typed,selectedPrograms=len(proofs)+len(selected),runtimeInflationObserved=False,liveProviderSelectionProved=False)

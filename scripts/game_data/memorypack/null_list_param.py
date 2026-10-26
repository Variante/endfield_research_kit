"""Selected null List constants; the parent keeps its independent typed proof."""
import hashlib,json
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.il2cpp.formatter_composition import _vtable,derive_typed_usage_context
from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import scalar_param_native as scalar,utf8_source_helper
from scripts.game_data.memorypack.reference_param import derive_reference_parameter
LABEL='nullListParam'
BOUNDARY=dict(direct='Typed four-member Param, owned parent fields/factory/null, reference ReadPackable, two Int32 bindings and pooled path; each selected collection source consumes the signed header and proves its declared null/zero subset.',conditional='Initialized coherent closed generated Param/List contexts; sufficient contiguous disjoint input/reader/output/frame; normal compatible metadata/allocation/barrier and constructor helpers. Admitted zero paths invoke an optimized provider whose result is unused. EntityPtr optimized Clear effects correspond to its actual closed Clear program under normal identical array-clear effects; UInt64 separately proves inline count/cursor, typed zero-constructor and Clear effects. String separately joins the identical closed ReadPackable MethodSpec/native target to current reference-shared ListFormatter source, typed factory/provider contexts and null/new-zero/existing-zero paths; shared/inflated runtime selection remains conditional.',unresolved=['all positive list counts/elements','zero-count Vector3 lists','live provider default/cache/override selection','cold refill or malformed helper paths','enclosing owner execution'])


def derive(image,pins,profile,value_type,*,collection_counts):
 if not value_type.startswith('System.Collections.Generic.List`1<') or not value_type.endswith('>'):raise ValueError(LABEL+'.listType')
 expected=[-1,0] if value_type in ('System.Collections.Generic.List`1<Beyond.Gameplay.Core.EntityPtr>','System.Collections.Generic.List`1<ulong>','System.Collections.Generic.List`1<string>') else [-1]
 scalar.need(LABEL,'collection-capability',expected,collection_counts)
 if any(type(n)is not int for n in collection_counts):raise ValueError(LABEL+'.collection-capability:integer-required')
 element=value_type[len('System.Collections.Generic.List`1<'):-1];base=image.pe.image_base;md=image.metadata
 parent,ctx,owned,calls=derive_reference_parameter(image,pins,profile,value_type,reader_method='ReadPackable');at,raw=parent['ownedMethods']['set___path__']['instructions'][7];barrier=at+5+int.from_bytes(bytes.fromhex(raw)[1:],'little',signed=True)
 if value_type=='System.Collections.Generic.List`1<string>':
  from .string_list_param_sources import derive as derive_string
  return json.loads(json.dumps(dict(**parent,collectionCounts=collection_counts,listSource=derive_string(image,pins,parent),evidenceBoundary=BOUNDARY)))
 td=ctx.index.types['MemoryPack.Formatters.ListFormatter`1'];method,=[m for m in md.methods_for(td) if md.string(m.name_index)=='Deserialize'];entry=GenericEntries(image).resolve(method.index,[element],[]);source=owned(entry['pointer'])
 if value_type=='System.Collections.Generic.List`1<ulong>':
  from .ulong_list_sources import derive as derive_ulong
  return json.loads(json.dumps(dict(**parent,listRegistration=entry,listCodeWindows=source['windows'],collectionCounts=collection_counts,listSource=derive_ulong(image,pins,ctx,entry,source,constructor_program=empty_list_constructor),evidenceBoundary=BOUNDARY)))
 header_target=calls(source)[0];headers=utf8_source_helper._contract();scalar.need(LABEL,'headerNativeInputs',pins,headers['nativeInputs']);scalar.need(LABEL,'selectedCollectionHeader',headers['bodies']['header']['entryRva'],header_target-base);header_proof=utf8_source_helper._validate_native(image,headers)
 null_program=null_list_program(source['regions'],source['pointer'],header_target,base+barrier)
 return json.loads(json.dumps(dict(**parent,listRegistration=entry,listCodeWindows=source['windows'],collectionHeader=header_proof,nullListProgram=null_program,collectionCounts=collection_counts,emptyList=derive_empty_entity(image,ctx,source,entry) if 0 in collection_counts else None,evidenceBoundary=BOUNDARY)))


def null_list_program(regions,entry,header,barrier):
 g=BytesPath(regions,entry)
 if bytes(g.bytes.get(entry+i,0) for i in range(3))==bytes.fromhex('4c8bdc'):
  g.take('4c8bdc','53','55','56','57','4881eca8000000','488bf2','0f57c0','33c0','498d5310','0f11442440','33db','488bce','0f11442450','49894398','498be9','498bf8','41895b10');g.call(header);g.take('84c0');g.branch('75',False,1)
  g.take('488bcf','48891f');g.call(barrier);g.take('4881c4a8000000','5f','5e','5d','5b','c3')
 else:
  g=BytesPath(regions,entry);g.take('4053','55','4154','4157','4883ec48','488bda','33c0','4533e4','4889442420','488bcb','4489642478','488d542478','89442428','498be9','4d8bf8');g.call(header);g.take('84c0');g.branch('0f84',True)
  g.take('498bcf','4d8927');g.call(barrier);g.take('4883c448','415f','415c','5d','5b','c3')
 return dict(selectedBytes=g.seen,wireBytes=4,collectionCount=-1,returnedReference=0)


def empty_entity_program(regions,entry,symbols,*,new):
 g=BytesPath(regions,entry)
 g.take('4c8bdc','53','55','56','57','4881eca8000000','488bf2','0f57c0','33c0','498d5310','0f11442440','33db','488bce','0f11442450','49894398','498be9','498bf8','41895b10');g.call(symbols['header']);g.take('84c0');g.branch('75',True,1)
 g.take('4c89a424d0000000','4c89b424e0000000','4c89bc24a0000000','448ba424d8000000','48391f');g.branch('0f85',not new)
 if new:
  g.take('488b4d20','33d2','488b89c0000000');g.call(symbols['context']);g.take('488bc8');g.call(symbols['allocate']);g.take('4c8bf0','4885c0');g.branch('0f84',False)
  g.take('488b4d20','488b91c0000000','488b4a08','48395920');g.branch('0f84',False);g.take('488b4520','418bd4','498bce','4c8b80c0000000','4d8b4008');g.call(symbols['constructor']);g.take('488bcf','4c8937');g.call(symbols['barrier'])
 else:
  g.take('488b4520','4c8b37','488b90c0000000','488b4210','48395820');g.branch('75',True,1);g.take('488b4520','498bce','488b90c0000000','488b5210');g.call(symbols['clear']);g.take('90');g.jump('e9')
 provider_owner=g.relative('488b0d');g.take('3999e0000000');g.branch('0f84',False);g.take('488b4520','488b88c0000000','488b4918');g.call(symbols['provider']);g.take('4c8bf0','4585e4');g.branch('0f8e',True)
 g.take('4c8bb424e0000000','4c8bbc24a0000000','4c8ba424d0000000');g.jump('e9');g.take('4881c4a8000000','5f','5e','5d','5b','c3')
 return dict(selectedBytes=g.seen,wireBytes=4,collectionCount=0,newList=new,providerStaticOwnerCell=provider_owner,elementCallbacks=0,providerResultUsed=False,headerOutputStackOffset=216,entryRspRestored=True,nonvolatileRestored=['rbx','rbp','rsi','rdi','r12','r14','r15'],condition='Selected coherent initialized closed ListFormatter<EntityPtr> context; normal compatible context/allocation/constructor/Clear/provider/barrier helpers; sufficient disjoint reader/source/output/frame storage. New calls constructor(capacity=0), existing calls Clear; provider returns normally without modifying those disjoint inputs and its formatter result is unused. No positive element or live provider selection follows.')


def derive_empty_entity(image,ctx,source,entry):
 base=image.pe.image_base;md=image.metadata;entries=GenericEntries(image);td=ctx.index.types['MemoryPack.Formatters.ListFormatter`1'];method,=[m for m in md.methods_for(td) if md.string(m.name_index)=='Deserialize'];_vtable(image,td.index,5,method.index,LABEL)
 context=ContextSymbols(image).context(td.index)
 def fail(*args):raise ValueError(LABEL+'.empty-context:'+str(args)[:1200])
 typed=validate_list_formatter_base_context(image,context,entries,fail=fail);slots={r['relativeSlot']:r for r in context['entries']};parameters=list(md.parameters_for(method))
 scalar.need(LABEL,'list-abi',(False,2,'void'),(bool(method.flags&16),len(parameters),ctx.type_name(method.return_type)))
 reader=ctx.index.types['MemoryPack.MemoryPackReader'];formal=image.pe.bytes_at_va(ctx.type_pointer(parameters[0].type_index),16);byval=image.pe.bytes_at_va(ctx.type_pointer(reader.byval_type_index),16)
 scalar.need(LABEL,'reader-byval-kind',b'\x11\x80',byval[10:12]);scalar.need(LABEL,'reader-byref-kind',b'\x11\x20',formal[10:12]);scalar.need(LABEL,'reader-type',('MemoryPack.MemoryPackReader','System.ValueType',byval[:8]),(ctx.type_name(parameters[0].type_index),ctx.parent('MemoryPack.MemoryPackReader'),formal[:8]))
 formal=image.pe.bytes_at_va(ctx.type_pointer(parameters[1].type_index),16);byval=image.pe.bytes_at_va(ctx.type_pointer(slots[0]['index']),16);scalar.need(LABEL,'list-byref-kind',b'\x15\x20',formal[10:12]);scalar.need(LABEL,'list-owned-type',(b'\x15\x00',formal[:8]),(byval[10:12],byval[:8]))
 rows=source['rows'];symbols={}
 for role,previous in [('header','mov [r11+0x10], ebx'),('context','mov rcx, [rcx+0xc0]'),('allocate','mov rcx, rax'),('constructor','mov r8, [r8+0x8]'),('clear','mov rdx, [rdx+0x10]'),('provider','mov rcx, [rcx+0x18]')]:
  found=[r for i,r in enumerate(rows) if i and bytes.fromhex(r['bytes'])[:1]==b'\xe8' and rows[i-1]['text']==previous]
  scalar.need(LABEL,'empty-helper-unique.'+role,1,len(found));r=found[0];raw=bytes.fromhex(r['bytes']);symbols[role]=int(r['va'],16)+5+int.from_bytes(raw[1:],'little',signed=True)
 barriers={int(r['va'],16)+5+int.from_bytes(bytes.fromhex(r['bytes'])[1:],'little',signed=True) for i,r in enumerate(rows) if i and bytes.fromhex(r['bytes'])[:1]==b'\xe8' and rows[i-1]['text'] in ('mov [rdi], rbx','mov [rdi], r14')};scalar.need(LABEL,'empty-barrier-unique',1,len(barriers));symbols['barrier']=next(iter(barriers));element='Beyond.Gameplay.Core.EntityPtr'
 scalar.need(LABEL,'element-value-type',True,ctx.is_value_type(element));scalar.need(LABEL,'list-constructor-declaration',('System.Collections.Generic.List`1','.ctor'),(slots[1]['typeName'],slots[1]['methodName']))
 constructor_spec=slots[1]['methodSpec'];clear_spec=slots[2]['methodSpec'];scalar.need(LABEL,'constructor-no-method-arguments',-1,constructor_spec[2]);scalar.need(LABEL,'constructor-owned-var',[a.type_pointer_va for a in image.instantiations.resolve(clear_spec[1]).arguments],[a.type_pointer_va for a in image.instantiations.resolve(constructor_spec[1]).arguments])
 constructor=md.methods[constructor_spec[0]];scalar.need(LABEL,'constructor-abi',(False,'void',['int']),(bool(constructor.flags&16),ctx.type_name(constructor.return_type),[ctx.type_name(p.type_index) for p in md.parameters_for(constructor)]))
 for slot,role in ((1,'constructor'),):
  spec=slots[slot]['methodSpec'];selected=entries.resolve(spec[0],[element],[]);scalar.need(LABEL,'closed-'+role,selected['pointer'],symbols[role]);scalar.need(LABEL,'same-closed-element.'+role,[a['raw_type_record_hex'] for a in entry['classInstantiation']['arguments']],[a['raw_type_record_hex'] for a in selected['classInstantiation']['arguments']])
 programs=[empty_entity_program(source['regions'],source['pointer'],symbols,new=new) for new in (False,True)]
 owner,=[r for r in rows if bytes.fromhex(r['bytes'])[:3]==b'\x48\x8b\x0d' and any(int(r['va'],16)+7+int.from_bytes(bytes.fromhex(r['bytes'])[3:],'little',signed=True)==p['providerStaticOwnerCell'] for p in programs)];owner_usage=derive_typed_usage_context(image,int(owner['va'],16)-base,label=LABEL+'.provider-owner');scalar.need(LABEL,'provider-static-owner',(1,'MemoryPack.MemoryPackFormatterProvider'),(owner_usage['tag'],owner_usage['typeName']))
 helpers={}
 for role in ('constructor','clear'):
  windows=[];regions=[];decoded=[]
  for part in image.unwind_index.family(symbols[role]-base)['ranges']:
   a,b=part['runtimeTriple'][:2];raw=image.pe.bytes_at_va(base+a,b-a);windows.append(dict(startRva=a,endRva=b,sha256=hashlib.sha256(raw).hexdigest().upper()));regions.append((base+a,raw));decoded+=image.body_index._decode(base+a,b-a)
  helpers[role]=dict(windows=windows,regions=regions,rows=decoded)
 list_owner=ctx.index.types['System.Collections.Generic.List`1'];list_context=ContextSymbols(image).context(list_owner.index);list_slot,=[r for r in list_context['entries'] if r['relativeSlot']==0];scalar.need(LABEL,'constructor-owned-list',(2,'System.Collections.Generic.List`1'),(list_slot['kind'],list_slot['type']['definition']['name']));argument,=list_slot['type']['classArguments'];scalar.need(LABEL,'constructor-list-var',(list_owner.index,0),(argument['parameterOwner']['typeIndex'],argument['parameterOwner']['ordinal']))
 static=[f for f in md.fields_for(list_owner) if ctx.field_attributes(f.type_index)&16 and not ctx.field_attributes(f.type_index)&64];scalar.need(LABEL,'sole-stored-static-array',1,len(static));empty_field=static[0];empty_raw=image.pe.bytes_at_va(ctx.type_pointer(empty_field.type_index),16);scalar.need(LABEL,'empty-array-reference-kind',(29,0),(empty_raw[10],empty_raw[11]));scalar.need(LABEL,'empty-array-element-owner',argument['typePointerVa'],int.from_bytes(empty_raw[:8],'little'))
 ctor_program=empty_list_constructor(helpers['constructor']['regions'],symbols['constructor'],context=symbols['context'],barrier=symbols['barrier'])
 clear_calls=[r for r in helpers['clear']['rows'] if bytes.fromhex(r['bytes'])[:1]==b'\xe8'];scalar.need(LABEL,'clear-call-count',1,len(clear_calls));r=clear_calls[0];array_clear=int(r['va'],16)+5+int.from_bytes(bytes.fromhex(r['bytes'])[1:],'little',signed=True);clear_programs=[empty_list_clear(helpers['clear']['regions'],symbols['clear'],array_clear=array_clear,nonempty=nonempty) for nonempty in (False,True)]
 registered_clear=entries.resolve(slots[2]['methodSpec'][0],[element],[]);leaf=image.pe.bytes_at_va(registered_clear['pointer'],34);leaf_programs=[registered_list_clear([(registered_clear['pointer'],leaf)],registered_clear['pointer'],array_clear=array_clear,nonempty=n) for n in (False,True)]
 clear_method=md.methods[slots[2]['methodSpec'][0]];scalar.need(LABEL,'clear-method-abi',(False,'void',0),(bool(clear_method.flags&16),ctx.type_name(clear_method.return_type),clear_method.parameter_count));scalar.need(LABEL,'clear-same-element',[a['raw_type_record_hex'] for a in entry['classInstantiation']['arguments']],[a['raw_type_record_hex'] for a in registered_clear['classInstantiation']['arguments']])
 for actual,registered in zip(clear_programs,leaf_programs):scalar.need(LABEL,'clear-program-effects',{k:registered[k] for k in ('previousSizePositive','sizeOffset','versionOffset','itemsOffset','returnedSize')},{k:actual[k] for k in ('previousSizePositive','sizeOffset','versionOffset','itemsOffset','returnedSize')})
 helper_proofs=dict(constructorWindows=helpers['constructor']['windows'],clearWindows=helpers['clear']['windows'],constructorContext=list_context,constructorProgram=ctor_program,clearPrograms=clear_programs,arrayClearCallRva=array_clear-base,registeredClearEntry=registered_clear,registeredClearProgramBytes=leaf.hex().upper(),registeredClearPrograms=leaf_programs,clearSelectedEffectsEquivalent=True,staticArrayField=dict(name=md.string(empty_field.name_index),type=ctx.type_name(empty_field.type_index),rawTypeHex=empty_raw.hex().upper(),physicalOffsetInferredFromSoleStoredReference=True))
 return dict(helperProofs=helper_proofs,context=context,typedBase=typed,constructorMethodIndex=constructor.index,providerStaticOwner=owner_usage,helperRvas={k:v-base for k,v in symbols.items()},programs=programs,providerBoundary=dict(actualCallRva=symbols['provider']-base,registeredClosedEntry=entries.resolve(slots[3]['methodSpec'][0],[],[element]),bodyEquivalenceProved=False,formatterResultUsed=False,condition='Only normal noninterfering Win64 return is required for count0. No identity/equivalence between the optimized helper and the registered provider is inferred.'))


def empty_list_constructor(regions,entry,*,context,barrier):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','8bda','498bf8','488bf1','85d2');g.branch('0f88',False);g.take('498b4820','488b89c0000000');g.branch('74',True,1)
 g.take('33d2');g.call(context);g.take('83b8e000000000');g.branch('74',False,1);g.take('488b4f20','33d2','488b89c0000000');g.call(context);g.take('488b88b8000000','488b01');g.jump('eb',1)
 g.take('488d4e10','48894610','488b5c2430','488b742438','4883c420','5f')
 if g.relative('e9')!=barrier:raise ValueError(LABEL+'.constructor-barrier')
 return dict(selectedBytes=g.seen,capacity=0,storedItemsOffset=16,sizeWritten=False,condition='Coherent initialized List constructor context with slot0 selecting actual closed List class, correctly initialized static empty array, zeroed fresh managed allocation and normal noninterfering context/barrier helpers. Original size remains zero; no positive capacity path is admitted.')


def empty_list_clear(regions,entry,*,array_clear,nonempty):
 g=BytesPath(regions,entry);g.take('4883ec28','448b4118','ff411c','c7411800000000','4585c0');g.branch('7f',nonempty,1)
 if nonempty:g.take('488b4910','4533c9','33d2');g.call(array_clear);g.jump('eb',1)
 g.take('4883c428','c3')
 return dict(selectedBytes=g.seen,previousSizePositive=nonempty,sizeOffset=24,versionOffset=28,itemsOffset=16,returnedSize=0,condition='Valid typed List instance and version increment semantics; if old size is positive, normal array-clear ABI writes only the selected items range and preserves disjoint list/source/reader/output/frame. No physical identity with registered generic Clear is assumed.')


def registered_list_clear(regions,entry,*,array_clear,nonempty):
 g=BytesPath(regions,entry);g.take('448b4118','ff411c','c7411800000000','4585c0');g.branch('7e',not nonempty,1)
 if nonempty:
  g.take('488b4910','4533c9','33d2')
  if g.relative('e9')!=array_clear:raise ValueError(LABEL+'.registered-clear-array-target')
 else:g.take('c3')
 return dict(selectedBytes=g.seen,previousSizePositive=nonempty,sizeOffset=24,versionOffset=28,itemsOffset=16,returnedSize=0,condition='Actual registered closed List<EntityPtr>.Clear entry; complete selected leaf normal control through RET or identical Array.Clear tail. Same stable disjoint memory and normal helper return assumptions as the optimized framed source; no full unwind ownership is claimed for this leaf.')

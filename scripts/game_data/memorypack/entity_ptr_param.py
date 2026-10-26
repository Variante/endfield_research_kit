"""Authenticate current stored EntityPtr fields and their typed Param composition."""
import hashlib,json
from scripts.game_data import levelscript_family_regenerate as r
from scripts.game_data.levelscript_family_regenerate import Build
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.closed_leaf_entry import decode_closed_leaf_entry
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_registered_formatter_composition
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
from scripts.game_data.il2cpp.string_source_instructions import decode_string_source_instructions
from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param as primitive,pooled_source_helper
from scripts.game_data.memorypack.entity_ptr_leaf import path as leaf_path
from scripts.game_data.memorypack.entity_ptr_outer import path as outer_path
from scripts.game_data.memorypack.entity_ptr_adapter import adapter
from scripts.game_data.memorypack.entity_ptr_conversion import check as conversion_program

def _leaf(image,pins,profile):
 base=image.pe.image_base;build=r.Build(image,pins);ctx=NativeReferenceContext(image);wrapper,=[w for w in build.wrappers.values() if w.wrapped_type=='Beyond.Gameplay.Core.EntityPtr'];md=image.metadata;methods={md.string(m.name_index):m for m in md.methods_for(md.types[wrapper.type_definition])}
 scalar.need('entityLeaf','typedFields',[('logicId','ulong'),('slotId','uint'),('useSlotId','bool')],[(m.name,m.declared_type) for m in wrapper.members]);scalar.need('entityLeaf','holder',(wrapper.name,wrapper.wrapped_type,16),ctx.field(wrapper.name+'::__instance'));scalar.need('entityLeaf','wrapperAndValueKinds',(False,True),(ctx.is_value_type(wrapper.name),ctx.is_value_type(wrapper.wrapped_type)))
 primitive.reader_abi(image,ctx,methods['Deserialize'],wrapper);pointer=image.method_pointer_va(methods['Deserialize']);parts=sorted(tuple(p['runtimeTriple'][:2]) for p in image.unwind_index.family(pointer-base)['ranges']);rows=[];windows=[]
 for a,b in parts:
  raw=image.pe.bytes_at_va(base+a,b-a);rows+=image.body_index._decode(base+a,b-a);windows.append(dict(startRva=a,endRva=b,sha256=hashlib.sha256(raw).hexdigest().upper()))
 first=[control_transfer(row)['target'] for row in rows if control_transfer(row)['kind']=='call'];symbols=dict(uint64=first[0],uint32=first[1],boolean=first[2],barrier=first[3]);symbols['allocation']=next(control_transfer(row)['target'] for i,row in enumerate(rows[:-1]) if row['text'].startswith('call 0x') and rows[i+1]['text']=='test rax, rax');offsets=scalar.reader_offsets(image,'entityLeaf');paths=[leaf_path(rows,pointer,offsets,symbols,allocated=allocated) for allocated in (False,True)]
 allocation=derive_typed_usage_context(image,int(paths[1]['allocation']['classLoad']['va'],16)-base,label='entityLeafAllocation');scalar.need('entityLeaf','typedAllocation',(1,wrapper.name),(allocation['tag'],allocation['typeName']))
 def record(pointer):
  end=image.body_index.extents[pointer];raw=image.pe.bytes_at_va(pointer,end-pointer);decoded=image.body_index._decode(pointer,end-pointer);return dict(pointerRva=pointer-base,window=dict(startRva=pointer-base,endRva=end-base,sha256=hashlib.sha256(raw).hexdigest().upper()),instructions=[[int(row['va'],16)-base,bytes.fromhex(row['bytes']).hex().upper()] for row in decoded])
 sources={name:record(symbols[name]) for name in ('uint64','uint32','boolean')}
 if len(sources['uint64']['instructions'])==16:
  source=sources['uint64'];call=image.body_index._decode(base+source['instructions'][10][0],5)[0];source['advance']=record(control_transfer(call)['target']);scalar.uint64_source(image,source,offsets)
 else:scalar.integer_source(image,sources['uint64'],offsets,'entityLeaf.uint64',width=8)
 scalar.integer_source(image,sources['uint32'],offsets,'entityLeaf.uint32',width=4);scalar.boolean_source(image,sources['boolean'],offsets,'entityLeaf.boolean')
 get=image.method_pointer_va(methods['GetValue']);leaf=decode_closed_leaf_entry(image.mapper,image.pe.bytes_at_va(get,256),get);expected=['0f104210','488bc1','0f104a20','0f1101','f20f104230','0f114910','f20f114120','c3'];scalar.need('entityLeaf','hidden40Getter',expected,[bytes.fromhex(row['bytes']).hex() for row in leaf['rows']]);scalar.owned_method_abi(image,ctx,methods['GetValue'].index,wrapper.type_definition,(wrapper.wrapped_type,17,False),[],'entityLeaf')
 setters=[]
 for name,width,slot,prefix in [('logicId',8,24,'488951'),('slotId',4,32,'8951'),('useSlotId',1,16,'8851')]:
  method=methods['set___'+name+'__'];at=image.method_pointer_va(method);program=decode_closed_leaf_entry(image.mapper,image.pe.bytes_at_va(at,128),at);scalar.need('entityLeaf','namedSetter:'+name,[prefix+bytes((slot,)).hex(),'c3'],[bytes.fromhex(row['bytes']).hex() for row in program['rows']]);setters.append(dict(member=name,methodIndex=method.index,program=program['rows'],storedOffset=slot,storedBytes=width))
 return dict(status='current-entity-mc3-wrapper-source-and-hidden40-getter-pass-not-admitted',nativeInputs=pins,wrapperName=wrapper.name,sourceWindows=windows,sourcePaths=paths,allocation=allocation,sources=sources,getter=leaf['rows'],setters=setters,boundary='Current initialized buffered existing/allocating wrapper MC3 read/store and exact40-byte getter only. Generic concrete adapter/context/provider, outer Param path and whole owner admission remain separate.')

def _outer(image,pins,profile):
 base=image.pe.image_base;build=Build(image,pins);ctx=NativeReferenceContext(image);md=image.metadata;wrapped='Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Core.EntityPtr>';w,=[w for w in build.wrappers.values() if w.wrapped_type==wrapped];methods={md.string(m.name_index):m for m in md.methods_for(md.types[w.type_definition])};slots=profile['ownedFieldSlots']
 scalar.need('entityParam','members',[('constValue','Beyond.Gameplay.Core.EntityPtr'),('idRef','int'),('paramSource','int'),('path','string')],[(m.name,m.declared_type) for m in w.members]);scalar.need('entityParam','holder',(w.name,wrapped,16),ctx.field(w.name+'::__instance'));primitive.reader_abi(image,ctx,methods['Deserialize'],w)
 def record(m):
  pointer=image.method_pointer_va(m) if not isinstance(m,int) else m;ranges=sorted(tuple(p['runtimeTriple'][:2]) for p in image.unwind_index.family(pointer-base)['ranges']);rows=[];windows=[]
  for a,b in ranges:
   raw=image.pe.bytes_at_va(base+a,b-a);rows+=image.body_index._decode(base+a,b-a);windows.append(dict(startRva=a,endRva=b,sha256=hashlib.sha256(raw).hexdigest().upper()))
  return dict(pointerRva=pointer-base,windows=windows,rows=rows,instructions=[[int(r['va'],16)-base,bytes.fromhex(r['bytes']).hex().upper()] for r in rows])
 caller=record(methods['Deserialize']);rows=caller['rows'];calls=[control_transfer(r)['target'] for r in rows if control_transfer(r)['kind']=='call'];symbols=dict(value=calls[0],barrier=calls[1],idRef=calls[2],paramSource=calls[3],path=calls[4],allocateWrapper=control_transfer(next(r for i,r in enumerate(rows[:-1]) if r['text'].startswith('call 0x') and rows[i+1]['text']=='mov rbp, rax'))['target'],constructor=image.method_pointer_va(methods['.ctor']));_require(symbols['idRef']==symbols['paramSource'],"symbols['idRef']==symbols['paramSource']");paths=[outer_path(rows,base+caller['pointerRva'],slots,symbols,allocated=a,null=n) for a,n in ((False,False),(True,False),(False,True))]
 positive=paths[0];value_context=derive_typed_usage_context(image,int(positive['valueContext']['va'],16)-base,label='entityParamValue');scalar.need('entityParam','closed-value-reader',('MemoryPack.MemoryPackReader','ReadValue',[],['Beyond.Gameplay.Core.EntityPtr']),(value_context['typeName'],value_context['methodName'],value_context['classArguments'],value_context['methodArguments']));build.prove_named_target(symbols['value'],'MemoryPack.MemoryPackReader','ReadValue',result_abi='hidden-output-40')
 allocation=derive_typed_usage_context(image,int(paths[1]['allocation']['va'],16)-base,label='entityParamWrapper');scalar.need('entityParam','allocated-wrapper',w.name,allocation['typeName']);scalar.need('entityParam','owned-constructor',image.method_pointer_va(methods['.ctor']),symbols['constructor'])
 offsets=scalar.reader_offsets(image,'entityParam');integer=record(symbols['idRef']);integer['window']=integer['windows'][0];integer['instructions']=[r for r in integer['instructions'] if integer['window']['startRva']<=r[0]<integer['window']['endRva']];scalar.integer_source(image,integer,offsets,'entityParamBindings');strings=pooled_source_helper.validate_on_image(image,symbols['path'],pins);scalar.need('entityParam','pooled-path','int32-pool-index',strings['wireEncoding'])
 owned={name:record(methods[name]) for name in ('.ctor','CreateInstance','set___constValue__','set___idRef__','set___paramSource__','set___path__')}
 for field in ('idRef','paramSource','path'):
  scalar.owned_method_abi(image,ctx,methods['set___'+field+'__'].index,w.type_definition,('void',1,False),[('string',14,True) if field=='path' else ('int',8,False)],'entityParamSetter')
  scalar.parameter_setter(image,owned['set___'+field+'__']['instructions'],name=field,slot=slots[field],width=4,label='entityParamSetter')
 scalar.owned_method_abi(image,ctx,methods['set___constValue__'].index,w.type_definition,('void',1,False),[('Beyond.Gameplay.Core.EntityPtr',17,False)],'entityParamSetter40')
 expected=['4883ec28','488b4910','4885c9','7426','0f1002','0f104a10','0f114120','f20f104220','0f114930','f20f114140','4883c138','4883c428',None,None,'cc'];scalar.program(image,owned['set___constValue__']['instructions'],[bytes.fromhex(x) if x else None for x in expected],'entityParamSetter40');setter=owned['set___constValue__']['rows'];_require(control_transfer(setter[3])['target']==int(setter[13]['va'],16) and control_transfer(setter[12])==dict(kind='jump',target=symbols['barrier']),"control_transfer(setter[3])['target']==int(setter[13]['va'],16) and control_transfer(setter[12])==dict(kind='jump',target=symbols['barrier'])")
 constructor=owned['.ctor'];load,=[r for r in constructor['rows'] if bytes.fromhex(r['bytes'])[:3]==b'\x48\x8b\x0d'];allocation_context=derive_typed_usage_context(image,int(load['va'],16)-base,label='entityParamAllocation');scalar.need('entityParam','allocated-Param',wrapped,allocation_context['typeName']);scalar.allocation_bridge(image,ctx,dict(allocationContext=allocation_context,ownedFieldSlots=slots,methods=owned),'entityParamFactory')
 return dict(status='current-entity-outer-param-source-store-component-pass-not-admitted',nativeInputs=pins,caller=caller,paths=paths,slots=slots,valueContext=value_context,wrapperAllocation=allocation,parameterAllocation=allocation_context,ownedMethods=owned,integerSource=integer,pooledPath=strings,boundary='Initialized buffered outer null/existing/allocating paths, typed hidden40 value context/caller equivalence, named owned setters, both reference factories and Int32/pool tails. Nested EntityPtr formatter/default/context and whole-owner/runtime admission remain separate.')

def _adapter(image,pins,profile):
 base=image.pe.image_base;source=profile['actualAdapter'];helpers=profile['wrapperRegistration'];_require(source['nativeInputs']==helpers['nativeInputs']==pins,"source['nativeInputs']==helpers['nativeInputs']==pins");shared=next(r for r in source['records'] if r['role']=='compared-adapter');dispatch=next(r for r in source['records'] if r['role']=='actual-dispatch');rows=[r for p in shared['parts'] for r in p['rows']];calls=[r for r in rows if control_transfer(r)['kind']=='call'];by_name=lambda name:control_transfer(next(r for r in calls if name in r.get('namedTargets',[])))['target'];symbols=dict(adapter=base+shared['entryRva'],classPrepare=control_transfer(next(r for p in dispatch['parts'] for r in p['rows'] if r['text'].startswith('call 0x')))['target'],peek=base+next(r for r in helpers['records'] if r['role']=='peekIsNull')['entryRva'],readNull=base+next(r for r in helpers['records'] if r['role']=='readNullByte')['entryRva'],typeFromHandle=by_name('System.Type.GetTypeFromHandle'),factory=by_name('System.Activator.CreateInstance'),notNull=by_name('Beyond.MemoryPack.GenericMemoryPackFormatter`2.DeserializeNotNull'))
 flags=next(r for i,r in enumerate(rows[:-1]) if r['text'].startswith('call 0x') and rows[i+1]['text']=='test eax, 0x80');symbols['typeFlags']=control_transfer(flags)['target'];paths=[]
 for record,kind in ((shared,False),(dispatch,True)):
  fresh=[]
  for p in record['parts']:
   raw=b''.join(bytes.fromhex(r['bytes']) for r in p['rows']);_require(raw==image.pe.bytes_at_va(base+p['startRva'],p['endRva']-p['startRva']),"raw==image.pe.bytes_at_va(base+p['startRva'],p['endRva']-p['startRva'])");fresh+=p['rows']
  for null,skip in ((True,False),(False,False),(False,True)):paths.append(adapter(fresh,base+record['entryRva'],symbols,dispatch=kind,null=null,skip_factory=skip))
 def primary(record):
  p=next(p for p in record['parts'] if p['startRva']==record['entryRva']);raw=image.pe.bytes_at_va(base+p['startRva'],p['endRva']-p['startRva']);return dict(window=dict(startRva=p['startRva'],endRva=p['endRva'],sha256=hashlib.sha256(raw).hexdigest().upper()),instructions=[[int(r['va'],16)-base,bytes.fromhex(r['bytes']).hex().upper()] for r in p['rows']])
 offsets=scalar.reader_offsets(image,'entityAdapter');peek=primary(next(r for r in helpers['records'] if r['role']=='peekIsNull'));remaining,current=offsets['bufferLength'],offsets['currentPtr'];expected=[b'\x40\x53',b'\x48\x83\xec\x20',b'\x83\x79'+bytes((remaining,1)),b'\x48\x8b\xd9',None,b'\x48\x8b\x43'+bytes((current,)),b'\x80\x38\xff',b'\x0f\x94\xc0',b'\x48\x83\xc4\x20',b'\x5b',b'\xc3'];scalar.program_extent(peek['instructions'],peek['window'],'entityPeek');scalar.program(image,peek['instructions'],expected,'entityPeek');row=peek['instructions'][4];code=bytes.fromhex(row[1]);scalar.need('entityPeek','short-buffer-guard',(6,b'\x0f\x8c'),(len(code),code[:2]));target=row[0]+6+int.from_bytes(code[2:],'little',signed=True);scalar.need('entityPeek','cold-target-outside-primary',False,peek['window']['startRva']<=target<peek['window']['endRva']);consume=primary(next(r for r in helpers['records'] if r['role']=='readNullByte'));primitive.object_header_source(image,consume,offsets)
 return dict(status='current-entity-shared-and-invoker-selected-transfers-pass-not-admitted',nativeInputs=pins,symbols=symbols,paths=paths,peekSource=peek,nullConsumeSource=consume,boundary='Exact current selected initialized null/positive paths, both factory-bit arms, same reader/output/slot3 context forwarding and unchanged normal returns. Peek consumes zero, null header consumes one and clears40 output bytes. DeserializeNotNull, concrete context/inflater/provider and outer Param remain separate.')

def _conversion(image,pins,profile):
 base=image.pe.image_base;source=profile['actualAdapter'];_require(source['nativeInputs']==pins,"source['nativeInputs']==pins");record=next(r for r in source['records'] if sum(len(p['rows']) for p in r['parts'])==95)
 actual=sorted(tuple(p['runtimeTriple'][:2]) for p in image.unwind_index.family(record['entryRva'])['ranges']);_require(actual==sorted((p['startRva'],p['endRva']) for p in record['parts']),"actual==sorted((p['startRva'],p['endRva']) for p in record['parts'])");rows=[];windows=[]
 for a,b in actual:
  raw=image.pe.bytes_at_va(base+a,b-a);rows+=decode_string_source_instructions(image.mapper,raw,base+a);windows.append(dict(startRva=a,endRva=b,sha256=hashlib.sha256(raw).hexdigest().upper()))
 calls=[control_transfer(r)['target'] for r in rows if control_transfer(r)['kind']=='call'];keys=['classContext','formatter','slotDispatch','classContext','interfaceContext','classPrepare','interfaceFallback','barrier','metadataInit','classInit','throwMissing'];symbols={}
 for key,value in zip(keys,calls,strict=True):
  if key in symbols:_require(symbols[key]==value,'symbols[key]==value')
  symbols[key]=value
 proof=conversion_program(rows,symbols);
 return dict(status='complete-current-not-null-transfer-program-pass-not-admitted',nativeInputs=pins,windows=windows,instructions=rows,symbols=symbols,proof=proof,boundary='Complete current transfer program and all local edges, including cold initialization, interface scan/fallback,40-byte result copy and null-wrapper output. Class-context inflation, helper effects, actual typed callee/provider and outer Param remain separate.')


def derive(image,pins,profile):
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
 scalar.need('entityParam','registeredPairs',{'Beyond.Gameplay.Core.EntityPtr','Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Core.EntityPtr>'},{row['originalType'] for row in profile['registrations']})
 for row in profile['registrations']:validate_eager_wrap_registration(image,row,label='entityParam.registration')
 for row in profile['compositions']:validate_registered_formatter_composition(image,row,label='entityParam.composition')
 leaf=_leaf(image,pins,profile);outer=_outer(image,pins,profile);adapter_proof=_adapter(image,pins,profile);conversion=_conversion(image,pins,profile)
 forwarders=[]
 for fact in profile['compositions']:
  original=fact['registrations'][0]['originalType'];getter,formatter=fact['methods'];wrapper=ctx.index.types[getter[1]]
  scalar.need('entityParam','nonabstractWrapper',0,wrapper.flags&0x80)
  target,=[m for m in md.methods_for(wrapper) if md.string(m.name_index)=='Deserialize'];pointer=base+formatter[3];rows=[];regions=[]
  for item in image.unwind_index.family(pointer-base)['ranges']:
   a,b=item['runtimeTriple'][:2];raw=image.pe.bytes_at_va(base+a,b-a);regions.append((base+a,raw));rows+=image.body_index._decode(base+a,b-a)
  calls=[control_transfer(row)['target'] for row in rows if control_transfer(row)['kind']=='call']
  proof=prove_zero_wrapper_forwarder(rows,dict(metadataInit=calls[0],classInit=calls[1]),image.method_pointer_va(target),label='entityParam.forward')
  forwarders.append(dict(originalType=original,proof=proof))
  if original=='Beyond.Gameplay.Core.EntityPtr':selected_formatter=pointer
 scalar.need('entityParam','compositionPairSet',{'Beyond.Gameplay.Core.EntityPtr','Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Core.EntityPtr>'},{r['originalType'] for r in forwarders})
 symbols=conversion['symbols'];invoke=symbols['slotDispatch'];regions=[]
 for item in image.unwind_index.family(invoke-base)['ranges']:
  a,b=item['runtimeTriple'][:2];regions.append((base+a,image.pe.bytes_at_va(base+a,b-a)))
 transfer=deserialize_slot(regions,invoke,prepare=symbols['classPrepare'],callback=selected_formatter)
 td=ctx.index.types['Beyond.MemoryPack.GenericMemoryPackFormatter`2'];method,=[m for m in md.methods_for(td) if md.string(m.name_index)=='Deserialize']
 observed=GenericEntries(image).observe(method.index,['Beyond.Gameplay.Core.EntityPtr','object'],[])
 scalar.need('entityParam','canonicalSharedEntry',True,any(r['pointer']==adapter_proof['symbols']['adapter'] for r in observed))
 return json.loads(json.dumps(dict(leaf=leaf,outer=outer,adapter=adapter_proof,conversion=conversion,forwarders=forwarders,slotTransfer=transfer,adapterRegistration=observed,evidenceBoundary=dict(direct='Current three-field EntityPtr wire source, exact hidden40 getter, typed null/existing/allocating four-member Param and both bindings, clone equivalence, actual selected dispatch/conversion/forwarders and static concrete registration.',conditional='Coherent initialized closed contexts and ready classes, sufficient contiguous input, disjoint storage and normal helper/allocation/barrier ABI; matching generated adapter/wrapper/conversion route selected.',unresolved=['live provider default/cache/override selection','runtime entity resolution','unserialized EntityPtr state','cold refill and malformed paths','enclosing owner execution']))))

def _require(condition,check):
 if not condition:raise ValueError("entityParam."+check)

"""Current EventArgsPtr wire composition under the declared generated formatter route."""
import hashlib,json
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_registered_formatter_composition
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.memorypack.wrapper_members import derive_from_image
from scripts.game_data.memorypack.vector_layout import vector_recorder
from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param as primitive,pooled_source_helper,event_args_paths,event_args_key
VALUE='Beyond.Gameplay.Core.EventArgsPtr'
LABEL='eventArgsParam'

def derive(image,pins,profile):
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);wrappers=derive_from_image(image)
 parent,=[w for w in wrappers.values() if w.wrapped_type=='Beyond.Gameplay.Actions.Param`1<'+VALUE+'>']
 child,=[w for w in wrappers.values() if w.wrapped_type==VALUE]
 scalar.need(LABEL,'parentMembers',[('constValue',VALUE),('idRef','int'),('paramSource','int'),('path','string')],[(m.name,m.declared_type) for m in parent.members])
 scalar.need(LABEL,'childMembers',[('key','string')],[(m.name,m.declared_type) for m in child.members])
 scalar.need(LABEL,'valueType',True,ctx.is_value_type(VALUE));scalar.need(LABEL,'valueField',(VALUE,'string',16),ctx.field(VALUE+'::key'))
 td=ctx.index.types[VALUE];sizes=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
 scalar.need(LABEL,'valueSize',(24,8),(image.pe.u32_at_va(sizes),image.pe.u32_at_va(sizes+4)))
 for w in (parent,child):scalar.need(LABEL,'wrapperHolder',(w.name,w.wrapped_type,16),ctx.field(w.name+'::__instance'))
 def methods(w):return {md.string(m.name_index):m for m in md.methods_for(md.types[w.type_definition])}
 pm,cm=methods(parent),methods(child);record=vector_recorder(image)
 def owned(pointer):
  windows=[];regions=[];rows=[]
  for part in image.unwind_index.family(pointer-base)['ranges']:
   a,b=part['runtimeTriple'][:2];raw=image.pe.bytes_at_va(base+a,b-a);regions.append((base+a,raw));rows+=image.body_index._decode(base+a,b-a);windows.append(dict(startRva=a,endRva=b,sha256=hashlib.sha256(raw).hexdigest().upper()))
  return dict(pointer=pointer,regions=regions,rows=rows,windows=windows)
 def calls(r):return [control_transfer(x)['target'] for x in r['rows'] if control_transfer(x)['kind']=='call']
 def named(m,size=None):
  at=image.method_pointer_va(m);end=at+size if size else image.body_index.extents[at];raw=image.pe.bytes_at_va(at,end-at);rows=image.body_index._decode(at,end-at)
  return dict(pointerRva=at-base,window=dict(startRva=at-base,endRva=end-base,sha256=hashlib.sha256(raw).hexdigest().upper()),instructions=[[int(r['va'],16)-base,bytes.fromhex(r['bytes']).hex().upper()] for r in rows])
 parent_entry=image.method_pointer_va(pm['Deserialize']);caller=record(parent_entry-base,fragments=True);primitive.reader_abi(image,ctx,pm['Deserialize'],parent)
 setters={n:image.method_pointer_va(pm['set___'+n+'__'])-base for n in ('constValue','idRef','paramSource','path')}
 targets=primitive.setter_call_program(image,caller,setters,width=8,vector2=True)
 usage=derive_typed_usage_context(image,caller['instructions'][19][0],label=LABEL)
 scalar.need(LABEL,'typedValueRead',('MemoryPack.MemoryPackReader','ReadValue',[],[VALUE]),tuple(usage[k] for k in ('typeName','methodName','classArguments','methodArguments')))
 offsets=scalar.reader_offsets(image,LABEL);header=record(targets['header']);primitive.object_header_source(image,header,offsets)
 integer=record(targets['idRef']);scalar.integer_source(image,integer,offsets,LABEL+'.integer');scalar.need(LABEL,'sameInteger',targets['idRef'],targets['paramSource'])
 pool=pooled_source_helper.validate_on_image(image,base+targets['path'],pins)
 own={n:named(pm[n],5 if n=='GetValue' else None) for n in ('.ctor','CreateInstance','GetValue',*('set___'+n+'__' for n in setters))}
 slots={}
 for n in setters:
  instructions=own['set___'+n+'__']['instructions'];slots[n]=bytes.fromhex(instructions[4 if n in ('constValue','path') and bytes.fromhex(instructions[3][1])[:1]==b'\x74' else 6][1])[-1]
  scalar.owned_method_abi(image,ctx,pm['set___'+n+'__'].index,parent.type_definition,('void',1,False),[(VALUE,17,False) if n=='constValue' else ('string',14,True) if n=='path' else ('int',8,False)],LABEL+'.setter')
  scalar.parameter_setter(image,instructions,name='path' if n=='constValue' else n,slot=slots[n],width=8 if n=='constValue' else 4,label=LABEL+'.setter')
 occupied=[p for n,size in (('constValue',8),('idRef',4),('paramSource',4),('path',8)) for p in range(slots[n],slots[n]+size)]
 scalar.need(LABEL,'disjointParamSlots',(24,True),(len(set(occupied)),all(16<=p<128 for p in occupied)))
 scalar.program(image,own['GetValue']['instructions'],[bytes.fromhex('488b4110'),b'\xc3'],LABEL+'.parentGetValue')
 load,=[r for r in own['.ctor']['instructions'] if bytes.fromhex(r[1])[:3]==bytes.fromhex('488b0d')]
 allocation=derive_typed_usage_context(image,load[0],label=LABEL+'.parameter')
 scalar.need(LABEL,'allocatedParam',parent.wrapped_type,allocation['typeName']);scalar.allocation_bridge(image,ctx,dict(methods=own,ownedFieldSlots=slots,allocationContext=allocation),LABEL+'.allocation')
 pointer=base+targets['null'];fragment,=[p['runtimeTriple'][:2] for p in image.unwind_index.family(parent_entry-base)['ranges'] if p['runtimeTriple'][0]<=pointer-base<p['runtimeTriple'][1]]
 a,b=fragment;rows=image.body_index._decode(pointer,base+b-pointer);null=dict(window=dict(startRva=pointer-base,endRva=b,sha256=hashlib.sha256(image.pe.bytes_at_va(pointer,base+b-pointer)).hexdigest().upper()),instructions=[[int(r['va'],16)-base,bytes.fromhex(r['bytes']).hex().upper()] for r in rows],fragmentStartRva=a,fragmentEndRva=b)
 barrier=primitive.null_output_program(image,null,caller['instructions'][57][0])
 def tail(r):
  (at,raw),=[row for row in r['instructions'] if bytes.fromhex(row[1])[:1]==b'\xe9'];raw=bytes.fromhex(raw);return at+5+int.from_bytes(raw[1:],'little',signed=True)
 scalar.need(LABEL,'parentReferenceBarriers',[barrier,barrier],[tail(own['set___constValue__']),tail(own['set___path__'])])
 key=owned(image.method_pointer_va(cm['Deserialize']));primitive.reader_abi(image,ctx,cm['Deserialize'],child)
 s={k:base+v for k,v in profile['symbols'].items()}
 for helper_name,owner,method in (('typeHandle','System.Type','GetTypeFromHandle'),('isAbstract','System.Type','get_IsAbstract'),('activate','System.Activator','CreateInstance')):
  scalar.need(LABEL,'namedHelper:'+helper_name,True,any(r.get('type')==owner and r.get('method')==method for r in image.body_index.names_by_pointer.get(s[helper_name],[])))
 key_symbols={k:base+v for k,v in profile['keySymbols'].items()}
 key_paths=[event_args_key.child(key['regions'],key['pointer'],key_symbols,allocated=a) for a in (False,True)]
 key_allocation=derive_typed_usage_context(image,key_paths[1]['allocationUsageSite']-base,label=LABEL+'.keyAllocation')
 scalar.need(LABEL,'keyAllocation',child.name,key_allocation['typeName'])
 scalar.need(LABEL,'sameKeyAndTailSource',s['barrier']-base,barrier)
 scalar.need(LABEL,'sameKeyPool',targets['path'],key_symbols['pool']-base)
 primitive.object_header_source(image,record(key_symbols['header']-base),offsets)
 scalar.need(LABEL,'keyBarrier',barrier,key_symbols['barrier']-base)
 value=owned(base+targets['constValue']);dispatch=owned(s['dispatch']);readnull=owned(s['readNull']);peek=owned(s['peek']);positive=owned(s['deserializeNotNull']);invoke=owned(s['wrapperInvoke']);conversion=owned(s['getValueInvoke'])
 paths=dict(value=event_args_paths.read_value(value['regions'],value['pointer'],s),dispatch=event_args_paths.original_dispatch(dispatch['regions'],dispatch['pointer'],s),peek=event_args_paths.peek(peek['regions'],peek['pointer'],offsets),readNull=event_args_paths.read_is_null(readnull['regions'],readnull['pointer'],s),positive=event_args_paths.deserialize_not_null(positive['regions'],positive['pointer'],s),conversion=event_args_paths.get_value_interface(conversion['regions'],conversion['pointer'],prepare=s['prepare']))
 scalar.need(LABEL,'registrationPairSet',{parent.wrapped_type,VALUE},{r['originalType'] for r in profile['registrations']})
 for r in profile['registrations']:validate_eager_wrap_registration(image,r,label=LABEL+'.registration')
 scalar.need(LABEL,'compositionPairSet',{parent.wrapped_type,VALUE},{r['registrations'][0]['originalType'] for r in profile['compositions']})
 for r in profile['compositions']:validate_registered_formatter_composition(image,r,label=LABEL+'.composition')
 fact,=[r for r in profile['compositions'] if r['registrations'][0]['originalType']==VALUE];getter,formatter=fact['methods']
 adapter=ctx.index.types['Beyond.MemoryPack.GenericMemoryPackFormatter`2'];method,=[m for m in md.methods_for(adapter) if md.string(m.name_index)=='Deserialize']
 observed=GenericEntries(image).observe(method.index,[VALUE,'object'],[])
 scalar.need(LABEL,'canonicalAdapterEntry',True,any(r['pointer']==s['adapter'] for r in observed))
 scalar.need(LABEL,'concreteWrapperNonabstract',0,md.types[child.type_definition].flags&0x80)
 scalar.need(LABEL,'getterProgram',bytes.fromhex('488b4110c3'),image.pe.bytes_at_va(base+getter[3],5))
 scalar.owned_method_abi(image,ctx,getter[0],child.type_definition,(VALUE,17,False),[],LABEL+'.keyGetValue')
 forward=owned(base+formatter[3]);forward_calls=calls(forward)
 paths['forward']=prove_zero_wrapper_forwarder(forward['rows'],dict(metadataInit=forward_calls[0],classInit=forward_calls[1]),key['pointer'],label=LABEL+'.forward')
 paths['invoke']=deserialize_slot(invoke['regions'],invoke['pointer'],prepare=s['prepare'],callback=forward['pointer'])
 return json.loads(json.dumps(dict(caller=caller,typedValueRead=usage,ownedMethods=own,slots=slots,parameterAllocation=allocation,nullSource=null,headerSource=header,integerSource=integer,pooledPath=pool,keyPaths=key_paths,keyAllocation=key_allocation,paths=paths,codeWindows=[w for r in (key,value,dispatch,readnull,peek,positive,invoke,conversion,forward) for w in r['windows']],canonicalAdapter=observed,evidenceBoundary=dict(direct='Typed four-member Param, one-member EventArgsPtr pooled key, exact selected caller/dispatch/forwarder/GetValue transfers, null parent output, current static registration and wrapper ownership.',conditional='Initialized coherent closed contexts and ready classes; selected compatible generated adapter, wrapper formatter and conversion slots; normal nonabstract typed wrapper activation, allocation/barrier/helper ABI and sufficient contiguous input.',unresolved=['live provider default/cache/override selection','cold or malformed branches','null nested EventArgsPtr value','enclosing owner execution']))))

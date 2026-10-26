"""Authenticate one selected generated reference-valued Param and pooled bindings."""
import hashlib
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_registered_formatter_composition
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
from scripts.game_data.levelscript_family_regenerate import Build
from scripts.game_data.memorypack.wrapper_members import derive_from_image
from scripts.game_data.memorypack.vector_layout import vector_recorder
from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param as primitive,pooled_source_helper
LABEL='referenceParam'

def derive_reference_parameter(image,pins,profile,value_type,*,reader_method):
 VALUE=value_type
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);wrappers=derive_from_image(image)
 parent,=[w for w in wrappers.values() if w.wrapped_type=='Beyond.Gameplay.Actions.Param`1<'+VALUE+'>']
 scalar.need(LABEL,'parentMembers',[('constValue',VALUE),('idRef','int'),('paramSource','int'),('path','string')],[(m.name,m.declared_type) for m in parent.members])
 for w in (parent,):scalar.need(LABEL,'wrapperHolder',(w.name,w.wrapped_type,16),ctx.field(w.name+'::__instance'))
 def methods(w):return {md.string(m.name_index):m for m in md.methods_for(md.types[w.type_definition])}
 pm=methods(parent);record=vector_recorder(image)
 def owned(pointer):
  windows=[];regions=[];rows=[]
  for part in image.unwind_index.family(pointer-base)['ranges']:
   a,b=part['runtimeTriple'][:2];raw=image.pe.bytes_at_va(base+a,b-a);regions.append((base+a,raw));rows+=image.body_index._decode(base+a,b-a);windows.append(dict(startRva=a,endRva=b,sha256=hashlib.sha256(raw).hexdigest().upper()))
  return dict(pointer=pointer,regions=regions,rows=rows,windows=windows)
 def calls(r):return [control_transfer(x)['target'] for x in r['rows'] if len(bytes.fromhex(x['bytes']))==5 and bytes.fromhex(x['bytes'])[0]==0xe8]
 def named(m,size=None):
  at=image.method_pointer_va(m);end=at+size if size else image.body_index.extents[at];raw=image.pe.bytes_at_va(at,end-at);rows=image.body_index._decode(at,end-at)
  return dict(pointerRva=at-base,window=dict(startRva=at-base,endRva=end-base,sha256=hashlib.sha256(raw).hexdigest().upper()),instructions=[[int(r['va'],16)-base,bytes.fromhex(r['bytes']).hex().upper()] for r in rows])
 parent_entry=image.method_pointer_va(pm['Deserialize']);caller=record(parent_entry-base,fragments=True);primitive.reader_abi(image,ctx,pm['Deserialize'],parent)
 setters={n:image.method_pointer_va(pm['set___'+n+'__'])-base for n in ('constValue','idRef','paramSource','path')}
 initialized=profile.get('initializedHeader',False);scalar.need(LABEL,'initializedHeaderProfile',True,type(initialized) is bool and (not initialized or profile['integerSlots'] is None))
 targets=primitive.initialized_enum_program(image,caller,setters,width=8) if initialized else primitive.setter_call_program(image,caller,setters,width=8,typed_qword=True,integer_slots=profile['integerSlots'])
 usage=derive_typed_usage_context(image,caller['instructions'][28 if initialized else 19][0],label=LABEL)
 scalar.need(LABEL,'typedValueRead',('MemoryPack.MemoryPackReader',reader_method,[],[VALUE]),tuple(usage[k] for k in ('typeName','methodName','classArguments','methodArguments')))
 offsets=scalar.reader_offsets(image,LABEL);header=record(targets['header']);primitive.object_header_source(image,header,offsets)
 integer=record(targets['idRef']);scalar.integer_source(image,integer,offsets,LABEL+'.integer');scalar.need(LABEL,'sameInteger',targets['idRef'],targets['paramSource'])
 pool=pooled_source_helper.validate_on_image(image,base+targets['path'],pins)
 own={n:named(pm[n],5 if n=='GetValue' else None) for n in ('.ctor','CreateInstance','GetValue',*('set___'+n+'__' for n in setters))}
 slots={}
 for n in setters:
  instructions=own['set___'+n+'__']['instructions'];slots[n]=bytes.fromhex(instructions[4 if n in ('constValue','path') and bytes.fromhex(instructions[3][1])[:1]==b'\x74' else 6][1])[-1]
  scalar.owned_method_abi(image,ctx,pm['set___'+n+'__'].index,parent.type_definition,('void',1,False),[(VALUE,21 if '<' in VALUE else 18,True) if n=='constValue' else ('string',14,True) if n=='path' else ('int',8,False)],LABEL+'.setter')
  scalar.parameter_setter(image,instructions,name='path' if n=='constValue' else n,slot=slots[n],width=8 if n=='constValue' else 4,label=LABEL+'.setter')
 occupied=[p for n,size in (('constValue',8),('idRef',4),('paramSource',4),('path',8)) for p in range(slots[n],slots[n]+size)]
 scalar.need(LABEL,'disjointParamSlots',(24,True),(len(set(occupied)),all(16<=p<128 for p in occupied)))
 scalar.program(image,own['GetValue']['instructions'],[bytes.fromhex('488b4110'),b'\xc3'],LABEL+'.parentGetValue')
 load,=[r for r in own['.ctor']['instructions'] if bytes.fromhex(r[1])[:3]==bytes.fromhex('488b0d')]
 allocation=derive_typed_usage_context(image,load[0],label=LABEL+'.parameter')
 scalar.need(LABEL,'allocatedParam',parent.wrapped_type,allocation['typeName']);scalar.allocation_bridge(image,ctx,dict(methods=own,ownedFieldSlots=slots,allocationContext=allocation),LABEL+'.allocation')
 pointer=base+targets['null'];fragment,=[p['runtimeTriple'][:2] for p in image.unwind_index.family(parent_entry-base)['ranges'] if p['runtimeTriple'][0]<=pointer-base<p['runtimeTriple'][1]]
 a,b=fragment;rows=image.body_index._decode(pointer,base+b-pointer);null=dict(window=dict(startRva=pointer-base,endRva=b,sha256=hashlib.sha256(image.pe.bytes_at_va(pointer,base+b-pointer)).hexdigest().upper()),instructions=[[int(r['va'],16)-base,bytes.fromhex(r['bytes']).hex().upper()] for r in rows],fragmentStartRva=a,fragmentEndRva=b)
 barrier=primitive.null_output_program(image,null,caller['instructions'][68 if initialized else 57][0])
 def tail(r):
  (at,raw),=[row for row in r['instructions'] if bytes.fromhex(row[1])[:1]==b'\xe9'];raw=bytes.fromhex(raw);return at+5+int.from_bytes(raw[1:],'little',signed=True)
 scalar.need(LABEL,'parentReferenceBarriers',[barrier,barrier],[tail(own['set___constValue__']),tail(own['set___path__'])])

 Build(image,pins).prove_named_target(base+targets['constValue'],'MemoryPack.MemoryPackReader',reader_method,result_abi='reference')
 registration=profile['registration'];composition=profile['composition'];validate_eager_wrap_registration(image,registration,label=LABEL+'.registration');validate_registered_formatter_composition(image,composition,label=LABEL+'.composition')
 scalar.need(LABEL,'registeredParent',parent.wrapped_type,registration['originalType']);scalar.need(LABEL,'compositionParent',[parent.wrapped_type],[r['originalType'] for r in composition['registrations']])
 getter,formatter=composition['methods'];forward=owned(base+formatter[3]);forward_calls=calls(forward)
 forwarding=prove_zero_wrapper_forwarder(forward['rows'],dict(metadataInit=forward_calls[0],classInit=forward_calls[1]),parent_entry,label=LABEL+'.forward')
 return dict(parent=caller,typedRead=usage,ownedMethods=own,parameterAllocation=allocation,slots=slots,parentNull=null,integerSource=integer,pooledPath=pool,parentHeader=header,forwarding=forwarding),ctx,owned,calls

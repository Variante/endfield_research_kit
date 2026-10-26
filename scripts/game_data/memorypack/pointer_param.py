"""Selected value8/value16 pointer Params; nominal identity remains explicit.

Only the two named closed selections are accepted. Shared instruction programs
prove transfers, never a borrowed nominal layout or an enclosing owner.
"""
import hashlib
from scripts.game_data.il2cpp.closed_leaf_entry import decode_closed_leaf_entry
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_registered_formatter_composition
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param as primitive,pooled_source_helper
from scripts.game_data.memorypack.wrapper_members import derive_from_image
from scripts.game_data.memorypack.vector_layout import vector_recorder

LABEL='pointerParam'
VALUES={'Beyond.Gameplay.CameraShakeConfigPtr':8,'Beyond.Gameplay.Core.BuffPtr':16}


def owned(image,pointer):
 base=image.pe.image_base;windows=[];regions=[];rows=[]
 for part in image.unwind_index.family(pointer-base)['ranges']:
  a,b=part['runtimeTriple'][:2];raw=image.pe.bytes_at_va(base+a,b-a)
  regions.append((base+a,raw));rows+=image.body_index._decode(base+a,b-a)
  windows.append(dict(startRva=a,endRva=b,sha256=hashlib.sha256(raw).hexdigest().upper()))
 return dict(pointer=pointer,regions=regions,rows=rows,windows=windows)


def leaf(image,pointer,expected):
 size=sum(len(bytes.fromhex(x)) for x in expected)
 result=decode_closed_leaf_entry(image.mapper,image.pe.bytes_at_va(pointer,size),pointer)
 scalar.need(LABEL,'closedLeaf',expected,[bytes.fromhex(r['bytes']).hex().upper() for r in result['rows']])
 return dict(entryRva=pointer-image.pe.image_base,instructions=[[int(r['va'],16)-image.pe.image_base,bytes.fromhex(r['bytes']).hex().upper()] for r in result['rows']],physicalExtentProved=False)


def methods(image,wrapper):
 return {image.metadata.string(m.name_index):m for m in image.metadata.methods_for(image.metadata.types[wrapper.type_definition])}


def calls(source):
 return [control_transfer(r)['target'] for r in source['rows'] if len(bytes.fromhex(r['bytes']))==5 and bytes.fromhex(r['bytes'])[0]==0xe8]


def registered_pair(image,pair,wrapper,*,label):
 registration=pair['registration'];composition=pair['composition']
 validate_eager_wrap_registration(image,registration,label=label)
 validate_registered_formatter_composition(image,composition,label=label)
 scalar.need(label,'registeredPair',(wrapper.wrapped_type,wrapper.name),(registration['originalType'],registration['wrapperType']))
 scalar.need(label,'compositionPair',[(wrapper.wrapped_type,wrapper.name)],[(r['originalType'],r['wrapperType']) for r in composition['registrations']])
 getter,formatter=composition['methods'];source=owned(image,image.pe.image_base+formatter[3]);fcalls=calls(source)
 reader=methods(image,wrapper)['Deserialize'];entry=image.method_pointer_va(reader)
 forwarding=prove_zero_wrapper_forwarder(source['rows'],dict(metadataInit=fcalls[0],classInit=fcalls[1]),entry,label=label+'.forward')
 return dict(forwarding=forwarding,readerMethod=[reader.index,wrapper.name,'Deserialize',entry-image.pe.image_base])


def derive_parent(image,pins,profile,value_type):
 scalar.need(LABEL,'closedValueSelection',True,value_type in VALUES)
 scalar.need(LABEL,'profileOptions',(None,False),(profile.get('integerSlots'),profile.get('initializedHeader')))
 scalar.need(LABEL,'valueABI',True,NativeReferenceContext(image).is_value_type(value_type))
 width=VALUES[value_type];base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
 wrapped='Beyond.Gameplay.Actions.Param`1<'+value_type+'>'
 wrapper,=[w for w in derive_from_image(image).values() if w.wrapped_type==wrapped]
 scalar.need(LABEL,'parentMembers',[('constValue',value_type),('idRef','int'),('paramSource','int'),('path','string')],[(m.name,m.declared_type) for m in wrapper.members])
 scalar.need(LABEL,'parentHolder',(wrapper.name,wrapped,16),ctx.field(wrapper.name+'::__instance'))
 mm=methods(image,wrapper);record=vector_recorder(image);entry=image.method_pointer_va(mm['Deserialize'])
 primitive.reader_abi(image,ctx,mm['Deserialize'],wrapper)
 def named(name):
  m=mm[name];at=image.method_pointer_va(m);end=at+5 if name=='GetValue' else image.body_index.extents[at]
  raw=image.pe.bytes_at_va(at,end-at)
  return dict(methodIndex=m.index,pointerRva=at-base,window=dict(startRva=at-base,endRva=end-base,sha256=hashlib.sha256(raw).hexdigest().upper()),instructions=[[int(r['va'],16)-base,bytes.fromhex(r['bytes']).hex().upper()] for r in image.body_index._decode(at,end-at)])
 own={n:named(n) for n in ('.ctor','CreateInstance','GetValue','set___constValue__','set___idRef__','set___paramSource__','set___path__')}
 slots={}
 for name in ('constValue','idRef','paramSource','path'):
  r=own['set___'+name+'__'];instructions=r['instructions'];kind,decl=(17,value_type) if name=='constValue' else (14,'string') if name=='path' else (8,'int')
  scalar.owned_method_abi(image,ctx,r['methodIndex'],wrapper.type_definition,('void',1,False),[(decl,kind,name=='path')],LABEL+'.setter')
  if name=='constValue' and width==16:
   from scripts.game_data.memorypack.pooled_nominal_key_sources import lang_const_setter
   raw=bytes.fromhex(instructions[5][1]);slots[name]=raw[-1]
   tail=bytes.fromhex(instructions[-3][1]);barrier=base+instructions[-3][0]+5+int.from_bytes(tail[1:],'little',signed=True)
   source=owned(image,base+r['pointerRva']);lang_const_setter(source['regions'],source['pointer'],barrier)
  else:
   at=4 if name in ('constValue','path') and bytes.fromhex(instructions[3][1])[:1]==b'\x74' else 6
   slots[name]=bytes.fromhex(instructions[at][1])[-1]
   scalar.parameter_setter(image,instructions,name='path' if name=='constValue' else name,slot=slots[name],width=8 if name=='constValue' else 4,label=LABEL)
 occupied=[p for name,size in (('constValue',width),('idRef',4),('paramSource',4),('path',8)) for p in range(slots[name],slots[name]+size)]
 scalar.need(LABEL,'disjointParentFields',(width+16,True),(len(set(occupied)),all(16<=p<128 for p in occupied)))
 scalar.program(image,own['GetValue']['instructions'],[bytes.fromhex('488B4110'),b'\xc3'],LABEL+'.parentGetter')
 for name in ('.ctor','CreateInstance','GetValue'):
  scalar.owned_method_abi(image,ctx,mm[name].index,wrapper.type_definition,(wrapped,21,True) if name=='GetValue' else ('void',1,False),[],LABEL+'.'+name)
 load,=[r for r in own['.ctor']['instructions'] if bytes.fromhex(r[1])[:3]==bytes.fromhex('488B0D')]
 allocation=derive_typed_usage_context(image,load[0],label=LABEL+'.allocation')
 scalar.need(LABEL,'allocatedParam',wrapped,allocation['typeName'])
 scalar.allocation_bridge(image,ctx,dict(methods=own,ownedFieldSlots=slots,allocationContext=allocation),LABEL+'.allocation')
 caller=record(entry-base,fragments=True);setters={n:own['set___'+n+'__']['pointerRva'] for n in slots}
 if width==8:
  targets=primitive.setter_call_program(image,caller,setters,width=8,typed_qword=True,integer_slots=None)
  usage=derive_typed_usage_context(image,caller['instructions'][19][0],label=LABEL+'.readValue')
  null_at=targets['null'];restore=caller['instructions'][57][0]
 else:
  from scripts.game_data.memorypack.pooled_nominal_key_sources import lang_param
  source=owned(image,entry)
  def target(at,opcode=b'\xe8'):
   row,=[r for r in source['rows'] if int(r['va'],16)==entry+at];raw=bytes.fromhex(row['bytes'])
   scalar.need(LABEL,'hidden16ControlShape',(len(opcode)+4,opcode),(len(raw),raw[:len(opcode)]))
   return entry+at+len(raw)+int.from_bytes(raw[len(opcode):],'little',signed=True)
  allocation_entry=target(64,b'\x0f\x84');allocation_load=derive_typed_usage_context(image,allocation_entry-base,label=LABEL+'.wrapperAllocation')
  scalar.need(LABEL,'allocatedWrapper',wrapper.name,allocation_load['typeName'])
  scalar.ordinary(image,ctx.type_pointer(allocation_load['typeIndex']),18,LABEL+'.wrapperAllocation',reference=True)
  cold={int(r['va'],16):r for r in source['rows']}
  def cold_call(offset):
   row=cold[allocation_entry+offset];raw=bytes.fromhex(row['bytes']);scalar.need(LABEL,'hidden16AllocationCall',(5,232),(len(raw),raw[0]));return control_transfer(row)['target']
  symbols=dict(header=target(42),value16=target(103),integer=target(150),pool=target(208),barrier=target(139),idRef=target(168),paramSource=target(197),path=target(227),allocate=cold_call(7),constructor=cold_call(29))
  scalar.need(LABEL,'sameHidden16Int32Helper',symbols['integer'],target(179))
  for name in('idRef','paramSource','path'):scalar.need(LABEL,'hidden16NamedSetter:'+name,base+setters[name],symbols[name])
  scalar.need(LABEL,'hidden16NamedConstructor',base+own['.ctor']['pointerRva'],symbols['constructor'])
  scalar.need(LABEL,'hidden16ConstSlot',32,slots['constValue'])
  paths=[lang_param(source['regions'],entry,symbols,**option)for option in({},{'allocated':True},{'null':True})]
  scalar.need(LABEL,'hidden16AllocationUsage',allocation_entry,paths[1]['allocationUsageSite'])
  scalar.need(LABEL,'hidden16TypedUsage',entry+85,paths[0]['valueUsageSite'])
  usage=derive_typed_usage_context(image,85+entry-base,label=LABEL+'.readValue')
  targets=dict(header=symbols['header']-base,constValue=symbols['value16']-base,idRef=symbols['integer']-base,paramSource=symbols['integer']-base,path=symbols['pool']-base,null=target(49,b'\x0f\x84')-base)
  null_at=targets['null'];restore=entry+237-base
  caller['hidden16Paths']=paths;caller['ownedSourceWindows']=source['windows'];caller['wrapperAllocation']=allocation_load
 scalar.need(LABEL,'closedValueRequest',('MemoryPack.MemoryPackReader','ReadValue',[],[value_type]),tuple(usage[k] for k in ('typeName','methodName','classArguments','methodArguments')))
 offsets=scalar.reader_offsets(image,LABEL);header=record(targets['header']);primitive.object_header_source(image,header,offsets)
 integer=record(targets['idRef']);scalar.integer_source(image,integer,offsets,LABEL+'.integer')
 scalar.need(LABEL,'sameInt32Helper',targets['idRef'],targets['paramSource'])
 pool=pooled_source_helper.validate_on_image(image,base+targets['path'],pins)
 a,b=next(p['runtimeTriple'][:2] for p in image.unwind_index.family(entry-base)['ranges'] if p['runtimeTriple'][0]<=null_at<p['runtimeTriple'][1])
 raw=image.pe.bytes_at_va(base+null_at,b-null_at);null=dict(window=dict(startRva=null_at,endRva=b,sha256=hashlib.sha256(raw).hexdigest().upper()),instructions=[[int(r['va'],16)-base,bytes.fromhex(r['bytes']).hex().upper()] for r in image.body_index._decode(base+null_at,b-null_at)],fragmentStartRva=a,fragmentEndRva=b)
 barrier=primitive.null_output_program(image,null,restore)
 for name in ('constValue','path'):
  tail=next(r for r in own['set___'+name+'__']['instructions'] if bytes.fromhex(r[1])[:1]==b'\xe9')
  scalar.need(LABEL,'sameContainedReferenceBarrier',barrier,tail[0]+5+int.from_bytes(bytes.fromhex(tail[1])[1:],'little',signed=True))
 pair=registered_pair(image,profile,wrapper,label=LABEL+'.parentRegistration')
 return dict(parent=caller,typedRead=usage,ownedMethods=own,parameterAllocation=allocation,slots=slots,parentNull=null,integerSource=integer,pooledPath=pool,parentHeader=header,parentPair=pair,valueReadTargetRva=targets['constValue'],barrierRva=barrier),ctx

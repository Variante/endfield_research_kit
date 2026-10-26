"""Complete current initialized reference-Param transfer with explicit nominal joins.

The shared instruction program owns no constant wire grammar. Each caller must
independently bind its actual typed child source and canonical outer adapter.
"""
from scripts.game_data.memorypack.levelscript_condition_param_sources import need

def _derive_parent(image,pins,*,value_type,reader_method,constant_kind,constant_width):
 """Own the exact 98-row reference Param; nominal and constant grammar stay explicit."""
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import pointer_param as pointer,primitive_param as primitive,scalar_param_native as scalar,pooled_source_helper
 from scripts.game_data.memorypack.levelscript_script_task_param_sources import _record
 from scripts.game_data.memorypack.param_setter_call_programs import reader_program
 from scripts.game_data.memorypack.wrapper_members import derive_from_image
 need('explicit-reference-value-selection',type(value_type)is str and bool(value_type)and reader_method in('ReadValue','ReadPackable','ReadUnmanaged')
  and type(constant_kind)is int and type(constant_width)is int
  and((constant_kind in(18,21)and constant_width==8 and reader_method!='ReadUnmanaged')
   or(constant_kind==17 and constant_width==4 and reader_method=='ReadUnmanaged')))
 LIST=value_type
 base=image.pe.image_base;ctx=NativeReferenceContext(image);typename='Beyond.Gameplay.Actions.Param`1<'+LIST+'>'
 wrapper,=[w for w in derive_from_image(image).values()if w.wrapped_type==typename]
 need('own-reference-Param-four-members',[(m.name,m.declared_type)for m in wrapper.members]==
  [('constValue',LIST),('idRef','int'),('paramSource','int'),('path','string')])
 need('own-reference-Param-holder',ctx.field(wrapper.name+'::__instance')==(wrapper.name,typename,16))
 mm=pointer.methods(image,wrapper);records={};slots={};bodies={}
 for name in('.ctor','CreateInstance','GetValue','Deserialize',*('set___'+m.name+'__'for m in wrapper.members)):
  method=mm[name];target=image.method_pointer_va(method)
  if name=='GetValue':
   pointer.leaf(image,target,['488B4110','C3']);records[name]=dict(methodIndex=method.index,pointerRva=target-base,
    instructions=[[target-base,'488B4110'],[target-base+4,'C3']])
  else:bodies[name]=pointer.owned(image,target);records[name]=_record(image,target,method.index)
  if name=='Deserialize':primitive.reader_abi(image,ctx,method,wrapper);continue
  declaration={'constValue':(LIST,constant_kind,constant_kind in(18,21)),'idRef':('int',8,False),'paramSource':('int',8,False),'path':('string',14,True)}
  scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,(typename,21,True)if name=='GetValue'else('void',1,False),
   [declaration[name[6:-2]]]if name.startswith('set___')else[],'currentReferenceParam')
  if name.startswith('set___'):
   field=name[6:-2];rows=records[name]['instructions'];reference=field=='path'or field=='constValue'and constant_kind in(18,21)
   at=(4 if bytes.fromhex(rows[3][1])[:1]==b'\x74'else 6)if reference else 6;slots[field]=bytes.fromhex(rows[at][1])[-1]
   scalar.parameter_setter(image,rows,name='path'if reference else field,slot=slots[field],width=constant_width,label='currentReferenceParam')
 occupied=[i for field,size in(('constValue',constant_width),('idRef',4),('paramSource',4),('path',8))for i in range(slots[field],slots[field]+size)]
 need('own-reference-Param-disjoint-fields',len(set(occupied))==constant_width+16 and all(16<=i<128 for i in occupied))
 loads=[r for r in records['.ctor']['instructions']if bytes.fromhex(r[1]).startswith(bytes.fromhex('488B0D'))]
 need('one-reference-Original-allocation',len(loads)==1)
 allocation=derive_typed_usage_context(image,loads[0][0],label='currentReferenceParam.Original')
 need('own-reference-Original-allocation',allocation['typeName']==typename)
 parameter=dict(methods=records,ownedFieldSlots=slots,allocationContext=allocation);scalar.allocation_bridge(image,ctx,parameter,'currentReferenceParam')
 body=bodies['Deserialize'];programs=[reader_program(body['regions'],body['pointer'],existing=e,ff=f,constant_width=constant_width)for e,f in((False,False),(True,False),(False,True),(True,True))]
 positive=programs[0];calls=positive['sourceCalls'];need('same-reference-positive-program-callees',calls==programs[1]['sourceCalls'])
 need('own-reference-named-setter-targets',all(calls['set'+field[0].upper()+field[1:]]==base+records['set___'+field+'__']['pointerRva']for field in slots))
 new=positive['allocation'];wrapper_usage=derive_typed_usage_context(image,new['instructionVa']-base,label='currentReferenceParam.wrapper')
 need('own-reference-wrapper-allocation-and-constructor',(wrapper_usage['tag'],wrapper_usage['typeName'])==(1,wrapper.name)
  and new['constructorVa']==base+records['.ctor']['pointerRva'])
 usage=derive_typed_usage_context(image,positive['constantContext']['instructionVa']-base,label='currentReferenceParam.constant')
 need('own-actual-reference-packable-reference-read',(usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))==
  ('MemoryPack.MemoryPackReader',reader_method,[],[LIST]))
 offsets=scalar.reader_offsets(image,'currentReferenceParam');header=_record(image,positive['headerTargetVa']);primitive.object_header_source(image,header,offsets)
 need('same-reference-two-Int32-sources',calls['idRef']==calls['paramSource'])
 integer=_record(image,calls['idRef']);scalar.integer_source(image,integer,offsets,'currentReferenceParam.integer')
 path=pooled_source_helper.validate_on_image(image,calls['path'],pins)
 def tail(record):
  at,raw=record['instructions'][-1];raw=bytes.fromhex(raw);need('owned-reference-reference-tail',raw[:1]==b'\xe9')
  return base+at+5+int.from_bytes(raw[1:],'little',signed=True)
 barrier=tail(records['set___path__'])
 need('same-reference-output-and-reference-field-barriers',all(p['barrierTargetVa']==barrier for p in(programs[0],programs[2],programs[3]))
  and all(tail(records[n])==barrier for n in(('.ctor','CreateInstance','set___constValue__')if constant_kind in(18,21)else('.ctor','CreateInstance'))))
 return dict(parent=records['Deserialize'],typedRead=usage,ownedMethods=records,parameter=parameter,programs=programs,
  wrapperAllocation=wrapper_usage,integerSource=integer,pooledPath=path,parentHeader=header,barrierTargetRva=barrier-base,
  sourceWindows=body['windows'],sourceRegions=[[a,raw.hex().upper()]for a,raw in body['regions']])



def derive_reference_parent(image,pins,*,value_type,reader_method,constant_kind=21):
 """Own the exact reference caller; kind18 and21 remain distinct declarations."""
 need('explicit-reference-constant-kind',type(constant_kind)is int and constant_kind in(18,21))
 return _derive_parent(image,pins,value_type=value_type,reader_method=reader_method,constant_kind=constant_kind,constant_width=8)


def derive_value4_parent(image,pins,*,value_type):
 """Own only the actual value17/EAX-to-EDX caller; the raw source stays separate."""
 return _derive_parent(image,pins,value_type=value_type,reader_method='ReadUnmanaged',constant_kind=17,constant_width=4)

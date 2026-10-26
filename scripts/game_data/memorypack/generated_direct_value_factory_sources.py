"""Direct-holder constructors with exact shared scalar or named Vector3 defaults."""
import hashlib
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def need(key,condition,detail=None):
 if not condition:raise ValueError('generatedDirectValueFactory.'+key+':'+str(detail)[:700])

def shared_constant_program(regions,entry,s):
 from scripts.game_data.memorypack import generated_lifecycle_sources as life
 g=BytesPath(regions,entry);g.take('4053','4883ec20');flag=life._direct_flag(g,'803d');g.take('488bd9');life._initialized(g)
 site=g.at;cell=g.relative('488b0d');g.call(s['allocate']);g.take('4885c0');life._nonnull(g)
 g.take('b9');constant=g.read(4).hex().upper();g.take('48894310');stores=[]
 for _ in range(2):
  at=g.at;g.take('8948');offset=g.read(1)[0];need('scalar-offset-positive-disp8',16<=offset<128);stores.append(dict(instructionVa=at,offset=offset,bytes=4,constantHex=constant))
 need('distinct-scalar-fields',stores[0]['offset']!=stores[1]['offset'])
 g.take('488d4b10','4883c420','5b');need('actual-final-barrier',g.relative('e9')==s['barrier'])
 return dict(selectedBytes=g.seen,metadata=flag,allocation=dict(site=site,cell=cell),allocationTarget=s['allocate'],constantFields=stores,
  baseHolderOffset=16,typedCacheOffset=None,inlineHolderWrites=[dict(offset=16,bytes=8,sameAllocatedReference=True)],
  sameAllocatedOriginalStored=True,normalReturnViaBarrier=True,completeSharedConstantBitsStored=True)

def vector3_one_program(regions,entry,s):
 from scripts.game_data.memorypack import generated_lifecycle_sources as life
 g=BytesPath(regions,entry);g.take('4053','4883ec30');flag=life._direct_flag(g,'803d');g.take('488bd9');life._initialized(g)
 site=g.at;cell=g.relative('488b0d');g.call(s['allocate']);g.take('488bd0','4885c0');life._nonnull(g)
 g.take('488d4c2420');at=g.at;g.take('c740');offset=g.read(1)[0];constant=g.read(4).hex().upper();stores=[dict(instructionVa=at,offset=offset,bytes=4,constantHex=constant)]
 need('positive-initial-scalar-disp8',16<=offset<128)
 helper_site=g.at;helper=g.relative('e8');g.take('8b4808','f20f1000','f20f1142');value_field=g.read(1)[0];g.take('894a');need('same-vector-tail-field',g.read(1)[0]==value_field+8)
 need('positive-complete-vector-disp8-fields',16<=value_field and value_field+8<128)
 g.take('488d4b10')
 for _ in range(3):
  at=g.at;g.take('c742');offset=g.read(1)[0];constant=g.read(4).hex().upper();stores.append(dict(instructionVa=at,offset=offset,bytes=4,constantHex=constant))
  need('positive-scalar-disp8',16<=offset<128)
 g.take('48895310','4883c430','5b');need('same-actual-final-barrier',g.relative('e9')==s['barrier'])
 return dict(selectedBytes=g.seen,metadata=flag,allocation=dict(site=site,cell=cell),allocationTarget=s['allocate'],constantFields=stores,
  baseHolderOffset=16,typedCacheOffset=None,inlineHolderWrites=[dict(offset=16,bytes=8,sameAllocatedReference=True)],sameAllocatedOriginalStored=True,
  valueInitialization=dict(helperTarget=helper,helperCallVa=helper_site,fieldOffset=value_field,bytes=12,outputLocal=32,originalRegister='rdx'),normalReturnViaBarrier=True)

def value_leaf(data,entry):
 g=BytesPath([(entry,data)],entry);constant=g.relative('f30f1015');g.take('0f28c2','0f14c2','f20f1101','f30f115108','488bc1','c3')
 return dict(selectedBytes=g.seen,constantAddress=constant,constantBytes=4,outputBytes=12,outputSlices=[[0,8],[8,4]],
  outputRegister='rcx',sameOutputReturnedInRax=True,preservedOriginalRegister='rdx',unchangedIntegerRegisters=True,normalReturn=True)

def bind(image,ctx,original,program,barrier):
 from scripts.game_data.memorypack import generated_vector_member_sources as values,generated_lifecycle_sources as life,scalar_param_native as scalar
 from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
 base=image.pe.image_base;md=image.metadata;record=program['valueInitialization'];td=ctx.index.types['UnityEngine.Vector3']
 selected=[m for m in md.methods_for(td)if md.string(m.name_index)=='get_one'and image.method_pointer_va(m)==record['helperTarget']]
 need('unique-current-named-value-helper',len(selected)==1);method=selected[0]
 need('actual-static-nongeneric-value-ABI',method.flags&16 and method.parameter_count==0 and method.generic_container_index<0 and ctx.type_name(method.return_type)=='UnityEngine.Vector3')
 scalar.ordinary(image,ctx.type_pointer(method.return_type),17,'generatedDirectValueFactory.return');layout=values.layout(image,ctx,'UnityEngine.Vector3')
 entry=record['helperTarget'];data=image.pe.bytes_at_va(entry,128);source=value_leaf(data,entry);constant=image.pe.bytes_at_va(source['constantAddress'],4)
 fields=[]
 for owner in life._class_ancestry(ctx,original):
  for field in md.fields_for(ctx.index.types[owner]):
   if ctx.field_attributes(field.type_index)&16:continue
   fact=ctx.field(owner+'::'+md.string(field.name_index))
   if fact[2]==record['fieldOffset']:
    need('actual-current-vector3-field',fact[1]=='UnityEngine.Vector3');scalar.ordinary(image,ctx.type_pointer(field.type_index),17,'generatedDirectValueFactory.field');fields.append(fact)
 need('one-current-value-field',len(fields)==1)
 size=max(at+len(bytes.fromhex(h))for at,h in source['selectedBytes'])-entry
 return dict(method=life._method_row(image,method),sourceProgram=source,layout=layout,field=fields[0],collector=_barrier(image,barrier),
  reachableEntryWindow=dict(startRva=entry-base,endRva=entry-base+size,sha256=hashlib.sha256(data[:size]).hexdigest().upper()),
  constantData=dict(startRva=source['constantAddress']-base,endRva=source['constantAddress']-base+4,hex=constant.hex().upper()),
  actualOriginalRdxPreserved=True,physicalFunctionExtentProved=False)

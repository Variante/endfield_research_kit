"""Exact named value-helper initialization in current wrapper constructors.

The helper's own reachable leaf proves output16 and RDX/R9 preservation. The
caller owns both holder writes, complete frame and actual typed class/cast
joins; no method name or managed width substitutes for these programs.
"""
import hashlib
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import generated_lifecycle_sources as lifecycle,generated_vector_member_sources as values

def need(k,condition,detail=None):
 if not condition:raise ValueError('generatedVectorFactorySource.'+k+':'+str(detail)[:700])

def value_entry_program(data,entry):
 g=BytesPath([(entry,data)],entry);constant=g.relative('660f6f05');g.take('0f1101','488bc1','c3')
 return dict(selectedBytes=g.seen,constantAddress=constant,outputBytes=16,outputRegister='rcx',sameOutputPointerReturnedInRax=True,
  integerRegistersPreserved=['rdx','r9','rbx','rbp','rsi','rdi','r12','r13','r14','r15'],volatileVectorWrites=['xmm0'],normalReturn=True)

def constructor_program(regions,entry,barrier,*,base_slot,cache_slot):
 need('finite-holder-displacements',16<=base_slot<cache_slot<128)
 g=BytesPath(regions,entry);g.take('4057'if lifecycle._peek(g,2)==bytes.fromhex('4057')else'57','4883ec30');flag=lifecycle._direct_flag(g,'803d');g.take('488bf9');lifecycle._initialized(g)
 site=g.at;cell=g.relative('488b0d');ancestor=dict(site=site,cell=cell);g.take('83b9e000000000');lifecycle._initialized(g)
 site=g.at;cell=g.relative('488b0d');allocation=dict(site=site,cell=cell);allocate=g.relative('e8');g.take('4c8bc8','4885c0');lifecycle._nonnull(g)
 g.take('488d4c2420','48895c2440');helper_site=g.at;helper=g.relative('e8');c=bytes((cache_slot,)).hex();b=bytes((base_slot,)).hex()
 g.take('488d4f'+c,'0f1008');store=g.at;g.take('410f1149');field=g.read(1)[0];g.take('4c894f'+c);g.call(barrier)
 g.take('488d4f'+b,'4c894f'+b);g.call(barrier);g.take('488b5f'+b);usages=[];casts=[]
 for i in range(2):
  at=g.at;cell=g.relative('488b15');usages.append(dict(site=at,cell=cell))
  if i==0:g.take('488bcb')
  casts.append(g.relative('e8'))
  if i==0:g.take('488947'+c,'488bcb')
 need('same-current-class-and-cast',len(set(casts))==1 and all(u['cell']==allocation['cell']for u in usages))
 g.take('488d4f'+c,'488b5c2440','4883c430','5f');need('same-tail-barrier',g.relative('e9')==barrier)
 return dict(selectedBytes=g.seen,initializedFlag=flag,constructor=True,allocation=allocation,allocationTarget=allocate,baseClassUsage=ancestor,baseReady=None,
  instanceSetter=None,inlineHolderWrites=[dict(offset=o,bytes=8,sameAllocatedReference=True)for o in(cache_slot,base_slot)],strictCast=casts[0],classUsages=usages,
  baseHolderOffset=base_slot,typedCacheOffset=cache_slot,originalConstructorCalled=False,originalConstructorTarget=None,originalConstructorEffectsProved=False,
  valueInitialization=dict(helperTarget=helper,helperCallVa=helper_site,fieldOffset=field,bytes=16,storeInstructionVa=store,originalRegister='r9',outputLocal=32),
  normalReturnViaBarrier=True)

def bind(image,ctx,original,program,barrier):
 from scripts.game_data.memorypack import scalar_param_native as scalar
 from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
 md=image.metadata;base=image.pe.image_base;record=program['valueInitialization'];owner=ctx.index.types['UnityEngine.Quaternion']
 methods=[m for m in md.methods_for(owner)if md.string(m.name_index)=='get_identity'and image.method_pointer_va(m)==record['helperTarget']]
 need('one-actual-owned-value-helper',len(methods)==1);method=methods[0]
 need('static-nongeneric-noarg-value-helper',bool(method.flags&16)and method.parameter_count==0 and method.generic_container_index<0 and ctx.type_name(method.return_type)=='UnityEngine.Quaternion')
 scalar.ordinary(image,ctx.type_pointer(method.return_type),17,'generatedVectorFactorySource.valueReturn')
 type_layout=values.layout(image,ctx,'UnityEngine.Quaternion');entry=record['helperTarget'];data=image.pe.bytes_at_va(entry,128);source=value_entry_program(data,entry)
 need('aligned-current-constant16',source['constantAddress']%16==0);constant=image.pe.bytes_at_va(source['constantAddress'],16)
 field=[]
 for typename in lifecycle._class_ancestry(ctx,original):
  for f in md.fields_for(ctx.index.types[typename]):
   if ctx.field_attributes(f.type_index)&16:continue
   name=md.string(f.name_index);fact=ctx.field(typename+'::'+name)
   if fact[2]!=record['fieldOffset']:continue
   need('actual-current-value-field',fact[1]=='UnityEngine.Quaternion');scalar.ordinary(image,ctx.type_pointer(f.type_index),17,'generatedVectorFactorySource.field');field.append(fact)
 need('one-owned-value-field',len(field)==1)
 collector=_barrier(image,barrier);reachable=max(at+len(bytes.fromhex(h))for at,h in source['selectedBytes'])-entry
 return dict(method=lifecycle._method_row(image,method),sourceProgram=source,layout=type_layout,field=field[0],collector=collector,
  reachableEntryWindow=dict(startRva=entry-base,endRva=entry-base+reachable,sha256=hashlib.sha256(data[:reachable]).hexdigest().upper()),
  constantData=dict(startRva=source['constantAddress']-base,endRva=source['constantAddress']-base+16,hex=constant.hex().upper()),
  helperPreservesAllocatedR9=True,disabledCollectorPreservesAllocatedR9=True,physicalFunctionExtentProved=False,
  condition='Exact current static value helper with readable aligned constant16 and disjoint local/heap storage. Normal allocation and initialized class/cast metadata, disabled collector; runtime invocation/rotation meaning is not observed.')

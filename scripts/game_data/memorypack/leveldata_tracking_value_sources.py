"""Owned Tracking value wrappers, distinct from their enclosing reference hosts.

TrackingBounds has three Vector3 wire members in center/euler/extents order;
their physical order is center/extents/euler. TrackingPoint reads its enum
before its Vector3 despite the opposite physical order. Exact wrapper sources,
hidden getters and default constructors are separate from canonical Original
adapter/default output, enclosing parent transfer and collection admission.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag

LABEL='storyTrackingValues'
VECTOR='UnityEngine.Vector3'
ENUM='Beyond.Gameplay.TrackingPointMatchMode'
BOUNDS='Beyond.Gameplay.TrackingBounds'
POINT='Beyond.Gameplay.TrackingPoint'
SPECS={
 BOUNDS:dict(managedBytes=36,order=(('centerWorldPos',VECTOR),('eulerAngles',VECTOR),('extents',VECTOR)),
  fields=(('centerWorldPos',VECTOR,16),('extents',VECTOR,28),('eulerAngles',VECTOR,40)),
  constructor=('0F57C0','33C0','0F114110','0F114120','894130','C3'),
  getter=('8B4230','0F104210','0F104A20','0F1101','0F114910','894120','488BC1','C3')),
 POINT:dict(managedBytes=16,order=(('matchMode',ENUM),('worldPos',VECTOR)),
  fields=(('worldPos',VECTOR,16),('matchMode',ENUM,28)),
  constructor=('0F57C0','0F114110','C3'),getter=('0F104210','488BC1','0F1101','C3')),
}


def need(check,condition):
 if not condition:raise ValueError(LABEL+'.'+check)


def value_leaf_program(data,entry,*,type_name,role):
 need('finite-value-leaf',type_name in SPECS and role in('GetValue','.ctor','CreateInstance'))
 spec=SPECS[type_name];getter=role=='GetValue';g=BytesPath([(entry,data)],entry)
 g.take(*(spec['getter']if getter else spec['constructor']))
 slices=[[0,16],[16,16],[32,4]]if type_name==BOUNDS else[[0,16]]
 return dict(selectedBytes=g.seen,typeName=type_name,role=role,managedBytes=spec['managedBytes'],
  copiedSlices=slices if getter else[],zeroedBytes=0 if getter else spec['managedBytes'],
  hiddenOutputRegister='rcx'if getter else None,wrapperInputRegister='rdx'if getter else'rcx',
  wrapperPayloadOffset=16,sameOutputReturnedInRax=getter,referenceLaneOffsets=[],
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,physicalExtentProved=False,
  wireGrammarAdmitted=False,wrapperFFDefaultOriginalAdmitted=False)


def record_program(regions,entry,*,type_name,symbols=None,new=False,null=False):
 """Four exact initialized paths; a wrapper FF clears only its reference."""
 need('finite-nominal-wrapper',type_name in SPECS)
 need('literal-path-options',type(new)is bool and type(null)is bool)
 need('explicit-role-targets',symbols is None or isinstance(symbols,dict))
 spec=SPECS[type_name];bounds=type_name==BOUNDS;roles={};calls={};allocation=None;enum=None
 g=BytesPath(regions,entry)
 def call(role):
  site=g.at;target=g.relative('e8')
  need('same-role-call-target:'+role,role not in roles or roles[role]==target)
  if symbols is not None:need('independent-role-target:'+role,symbols.get(role)==target)
  roles[role]=target;return site
 def guard():g.branch('74',False,1)
 g.take('48895c2410','4889742418','57','4883ec30');ready=flag(g)
 g.take('488bda','488bf9');g.branch('75',True,1)
 g.take('488d542440','c644244000','488bcf');header=call('header')
 g.take('84c0');g.branch('0f84',null)
 if null:
  g.take('488bcb','48c70300000000');call('barrier')
 else:
  g.take('48833b00');g.branch('75',not new,1)
  if new:
   allocation=dict(instruction=g.at,cell=g.relative('488b0d'));call('allocate')
   g.take('4885c0')
   if bounds:g.branch('0f84',False)
   else:guard()
   if bounds:g.take('33c9','0f57c0','0f114010','0f114020','894830','488bcb','488903')
   else:g.take('0f57c0','488bcb','0f114010','488903')
   call('barrier')
  g.take('807c2440'+('03'if bounds else'02'));g.branch('75',False,1)
  if bounds:
   g.take('488b33','488d4c2420','488bd7');calls['centerWorldPos']=call('vector3')
   g.take('488bc8','4885f6');guard()
   g.take('f20f1001','488bd7','8b4008','488d4c2420','f20f114610','894618','488b33')
   calls['eulerAngles']=call('vector3');g.take('488bc8','4885f6');guard()
   g.take('f20f1001','488bd7','8b4008','488d4c2420','f20f114628','894630','488b1b')
   calls['extents']=call('vector3');g.take('488bc8','4885db');guard()
   g.take('f20f1001','8b4008','f20f11431c','894324')
  else:
   enum=dict(instruction=g.at,cell=g.relative('488b15'))
   g.take('488bcf','488b33');calls['matchMode']=call('enum32')
   g.take('4885f6');guard();g.take('89461c','488d4c2420','488b1b','488bd7')
   calls['worldPos']=call('vector3');g.take('488bc8','4885db');guard()
   g.take('f20f1001','8b4008','f20f114310','894318')
  g.jump('eb',1)
 g.take('488b5c2448','488b742450','4883c430','5f','c3')
 physical={name:(offset,12 if typename==VECTOR else 4)for name,typename,offset in spec['fields']}
 copies=[]if null else[[name,*physical[name]]for name,typename in spec['order']]
 return dict(selectedBytes=g.seen,metadataReadyFlag=ready,typeName=type_name,existing=not new,wrapperNull=null,
  symbolTargets=roles,headerCall=header,typedAllocation=allocation,enumContext=enum,memberCalls=calls,
  memberCount=None if null else len(spec['order']),wireBytes=1 if null else 1+sum(n for name,offset,n in copies),
  managedBytes=spec['managedBytes'],newWrapperZeroedBytes=spec['managedBytes']if new and not null else 0,
  clearedWrapperReferenceBytes=8 if null else 0,completeFieldCopies=copies,
  referenceLaneOffsets=[],paddingByteRanges=[],valueSourceOutputLocal=None if null else[32,44],
  sourceLocalReusedOnlyAfterPreviousFieldStored=True,
  frame=dict(entryRspDelta=-56,callShadow=[0,32],headerOutputEntryHome=[8,9],sourceOutputLocal=[32,44],
   savedEntryHomes=dict(rbx=[16,24],rsi=[24,32]),pushedNonvolatiles=['rdi']),
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,
  canonicalOriginalAdapterAdmitted=False,parentFieldAdmitted=False,containerAdmitted=False,wholeOwnerAdmitted=False,
  condition='Initialized coherent selected metadata, stable sufficiently buffered disjoint input/Reader/output/frame, '
   'nonnull compatible new or reused wrapper, independently proved normal header/child/allocation/barrier effects and disabled collector. '
   'Wrapper FF clears8 only; default Original output and canonical adapter selection remain separate.')


def layout(image,ctx,wrapper):
 """Fresh exact value fields/holder/sizes; none select a wire width."""
 from scripts.game_data.memorypack import scalar_param_native as scalar
 name=wrapper.wrapped_type;need('finite-selected-type',name in SPECS);spec=SPECS[name]
 md=image.metadata;td=ctx.index.types[name]
 need('plain-owned-value',ctx.is_value_type(name)and not ctx.is_enum(name)
  and ctx.parent(name)=='System.ValueType'and td.generic_container_index<0)
 scalar.ordinary(image,ctx.type_pointer(td.byval_type_index),17,LABEL+'.Original')
 need('serialized-member-order',[(m.name,m.declared_type)for m in wrapper.members]==list(spec['order']))
 fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
 actual=sorted([(md.string(f.name_index),*ctx.field(name+'::'+md.string(f.name_index))[1:])for f in fields],key=lambda f:f[2])
 need('complete-physical-named-layout',actual==list(spec['fields']))
 for field in fields:scalar.ordinary(image,ctx.type_pointer(field.type_index),17,LABEL+'.field')
 holder=ctx.field(wrapper.name+'::__instance');need('direct-inline-holder',holder==(wrapper.name,name,16))
 sizes={}
 for definition in(td,md.types[wrapper.type_definition]):
  need('bounded-size-row',0<=definition.index<image.registration['typeDefinitionsSizesCount'])
  at=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*definition.index)
  need('present-size-row',type(at)is int and at>0)
  sizes[image.type_name(definition.index)]=dict(instanceBytes=image.pe.u32_at_va(at),nativeBytes=image.pe.u32_at_va(at+4))
 need('own-boxed-physical-size',sizes[name]['instanceBytes']==16+spec['managedBytes'])
 need('complete-wrapper-storage',sizes[wrapper.name]['instanceBytes']>=16+spec['managedBytes'])
 return dict(typeName=name,typeDefinition=td.index,managedBytes=spec['managedBytes'],fields=actual,holder=holder,
  sizeRows=sizes,referenceLaneOffsets=[],paddingByteRanges=[],wireWidthFromLayoutClaimed=False)


def derive_record(image,pins,type_name):
 """Source-only exact nominal wrapper; canonical/default/list joins stay open."""
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import pointer_param as pointer,primitive_param,scalar_param_native as scalar
 from scripts.game_data.memorypack import generated_vector3_source,unmanaged_enum_member_sources
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
 from scripts.game_data.memorypack.vector_layout import vector_recorder
 _publication_gate(image,pins);need('selected-finite-type',type_name in SPECS)
 base=image.pe.image_base;ctx=NativeReferenceContext(image)
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==type_name]
 nominal=layout(image,ctx,wrapper);spec=SPECS[type_name];methods=pointer.methods(image,wrapper)
 reader=methods['Deserialize'];primitive_param.reader_abi(image,ctx,reader,wrapper)
 body=pointer.owned(image,image.method_pointer_va(reader))
 first=record_program(body['regions'],body['pointer'],type_name=type_name,new=True)
 symbols=first['symbolTargets'];programs=[first]
 for new,null in((False,False),(True,True),(False,True)):
  programs.append(record_program(body['regions'],body['pointer'],type_name=type_name,symbols=symbols,new=new,null=null))
 allocation=derive_typed_usage_context(image,first['typedAllocation']['instruction']-base,label=LABEL+'.allocation')
 need('actual-owned-wrapper-allocation',(allocation['tag'],allocation['typeName'])==(1,wrapper.name))
 need('same-actual-wrapper-allocation-cell',base+allocation['usageCellRva']==first['typedAllocation']['cell'])
 scalar.ordinary(image,ctx.type_pointer(allocation['typeIndex']),18,LABEL+'.wrapperAllocation',reference=True)
 pair=derive_pair(image,type_name,wrapper.name);registration=pointer.registered_pair(image,pair,wrapper,label=LABEL+'.pair')
 getter=methods['GetValue'];scalar.owned_method_abi(image,ctx,getter.index,wrapper.type_definition,(type_name,17,False),[],LABEL+'.GetValue')
 getter_target=image.method_pointer_va(getter);getter_source=pointer.leaf(image,getter_target,list(spec['getter']))
 getter_program=value_leaf_program(image.pe.bytes_at_va(getter_target,sum(len(bytes.fromhex(h))for h in spec['getter'])),
  getter_target,type_name=type_name,role='GetValue')
 constructors={}
 for name in('.ctor','CreateInstance'):
  method=methods[name];scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),[],LABEL+'.'+name)
  target=image.method_pointer_va(method);leaf=pointer.leaf(image,target,list(spec['constructor']))
  program=value_leaf_program(image.pe.bytes_at_va(target,sum(len(bytes.fromhex(h))for h in spec['constructor'])),
   target,type_name=type_name,role=name)
  constructors[name]=dict(source=leaf,program=program)
 offsets=scalar.reader_offsets(image,LABEL);header=vector_recorder(image)(symbols['header']-base)
 primitive_param.object_header_source(image,header,offsets)
 vector=generated_vector3_source.derive_forwarder(image,pins,source_target=symbols['vector3'])
 enum=None
 if type_name==POINT:
  request=derive_typed_usage_context(image,first['enumContext']['instruction']-base,label=LABEL+'.pointEnum')
  call=first['memberCalls']['matchMode']
  enum=unmanaged_enum_member_sources.derive(image,pins,typed_request=request,source_target=symbols['enum32'],enum_type=ENUM,
   source_instruction=[call-base,image.pe.bytes_at_va(call,5).hex().upper()])
 barrier,barrier_program,_=_fast_barrier(image,symbols['barrier']);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-tracking-value-wrapper.v1',status='validated-conditional-tracking-value-wrapper',
  nativeInputs=pins,typeName=type_name,wrapperName=wrapper.name,layout=nominal,managedBytes=spec['managedBytes'],
  referenceLaneOffsets=[],paddingByteRanges=[],orderedMembers=spec['order'],
  readerMethod=[reader.index,wrapper.name,'Deserialize',body['pointer']-base],sourceWindows=body['windows'],
  sourceRegions=[(at,data.hex().upper())for at,data in body['regions']],programs=programs,
  getter=dict(source=getter_source,program=getter_program),constructors=constructors,pair=pair,registration=registration,allocation=allocation,
  headerSource=header,vectorSource=vector,enumSource=enum,barrier=dict(source=barrier,program=barrier_program),
  symbolRvas={role:target-base for role,target in symbols.items()},
  canonicalOriginalAdapterAdmitted=False,parentFieldAdmitted=False,containerAdmitted=False,wholeOwnerAdmitted=False,
  evidenceBoundary=dict(exact='Own named value layout/direct wrapper payload, complete initialized MC/FF/new/reused wrapper sources, exact zeroing constructors/hidden getter, actual header, Vector3 and nominal enum direct Reader sources.',
   conditional=first['condition'],structuralOnly='Stored world coordinates/bounds and raw match-mode bits; runtime tracking meaning unproved.',
   unresolved=['canonical Original provider/adapter/default and conversion','actual host value/local/setter/frame transfer','collection callbacks/counts','whole owner/physical EOF/publication']))))

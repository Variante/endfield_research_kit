"""Finite Patrol helper source paths, without runtime dispatch or event claims.

The virtual-slot thunk preserves a selected result but cannot establish which
runtime callback ran. The base filter returns true only on the independently
selected absent-replacement path. Neither fact supplies blackboard effects.
"""
import hashlib
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

CONTROLLER='Beyond.Gameplay.AI.NewNpcAIPatrolController'
CORE='Beyond.Gameplay.Core.PatrolData'


def getter_program(regions,entry,*,field_offset):
 if type(field_offset)is not int or not 128<=field_offset<2**31:
  raise ValueError('patrolHelper.owned-controller-reference-field')
 g=BytesPath(regions,entry);g.take('488b81'+field_offset.to_bytes(4,'little').hex(),'c3')
 return dict(selectedBytes=g.seen,receiverRegister='rcx',resultRegister='rax',fieldOffset=field_offset,
  returnedReferenceBitsUnchanged=True,sourceWrite=False,stackAndNonvolatilesUntouched=True,normalReturn=True,
  completeNormalLeafProved=True,physicalFunctionExtentProved=False,runtimeInvocationObserved=False)


def lookup_program(regions,entry,*,prepare,selector):
 if type(selector)is not int or not 0<=selector<2**16 or type(prepare)is not int or prepare<=0:
  raise ValueError('patrolHelper.literal-slot-selector-and-prepare')
 g=BytesPath(regions,entry)
 g.take('48895c2408','57','4883ec20','0fb7d9','488bfa','488b0a');g.call(prepare)
 g.take('488b07','488d5314','4803d2','488bcf','4c8b04d0','488b54d008',
  '488b5c2430','4883c420','5f','49ffe0')
 return dict(selectedBytes=g.seen,incomingSelectorBits=16,selector=selector,vtableBaseBytes=320,slotStrideBytes=16,
  callbackByteOffset=320+selector*16,methodInfoByteOffset=328+selector*16,
  callbackRegister='r8',callbackArguments=dict(rcx='unchanged incoming rdx receiver',rdx='selected slot MethodInfo'),
  tailJumpsSelectedCallback=True,preservesSelectedReturnBits=True,entryRspRestored=True,
  restoredNonvolatiles=['rbx','rdi'],runtimeCallbackSelectionObserved=False,lookupResultProved=False,
  condition='Compatible nonnull receiver/class and normal preparation preserving Win64 nonvolatiles; '
   'the actual selected class slot and MethodInfo must match the independently authenticated getter. '
   'The tail jump proves no live receiver type, getter invocation or returned object.')


def base_process_program(regions,entry,*,replacement_root_present=False):
 if type(replacement_root_present)is not bool:raise ValueError('patrolHelper.literal-replacement-root-mode')
 g=BytesPath(regions,entry);g.take('4883ec28','488bc1');root=g.relative('488b0d')
 g.take('488b4928','4885c9');g.branch('0f85',replacement_root_present)
 callback_offset=None
 if replacement_root_present:
  g.take('4c8b91e0c60000','4d85d2');g.branch('0f84',True)
  callback_offset=0xc6e0
 g.take('b001','4883c428','c3')
 return dict(selectedBytes=g.seen,optionalCallbackRootCell=root,optionalRootFieldOffset=40,
  replacementRootPresent=replacement_root_present,selectedCallbackOffset=callback_offset,
  absentSelectedReplacementRequired=True,returnsLiteralTrue=True,entryRspRestored=True,
  blackboardRead=False,blackboardWrite=False,normalReturn=True,runtimeInvocationObserved=False,
  condition='Stable initialized optional-callback root; either its selected receiver is null, or the selected callback is null. '
   'Only these normal source paths are admitted. Replacement callbacks, event dispatch and live invocation remain unproved.')


def _selector(program,target):
 selected=program['selectedBytes'];found=[]
 for index,(at,encoded)in enumerate(selected):
  raw=bytes.fromhex(encoded)
  if raw!=b'\xe8':continue
  if index+1>=len(selected):raise ValueError('patrolHelper.complete-owned-call-displacement')
  displacement_at,displacement_hex=selected[index+1];displacement=bytes.fromhex(displacement_hex)
  if displacement_at!=at+1 or len(displacement)!=4:raise ValueError('patrolHelper.complete-owned-call-displacement')
  if at+5+int.from_bytes(displacement,'little',signed=True)!=target:continue
  if index<2 or selected[index-1][1]!='488bd3':raise ValueError('patrolHelper.actual-getter-receiver')
  immediate=bytes.fromhex(selected[index-2][1])
  if len(immediate)!=5 or immediate[0]!=0xb9:raise ValueError('patrolHelper.actual-literal-getter-slot')
  found.append(int.from_bytes(immediate[1:],'little'))
 if len(found)!=1:raise ValueError('patrolHelper.one-actual-getter-call:expected=1:actual='+str(len(found)))
 return found[0]


def derive(image,pins):
 """Fresh caller/helper, exact named getter leaf and nominal slot joins."""
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import _vtable
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
 from scripts.game_data.memorypack.leveldata_patrol_checkpoint_sources import derive as producer_source
 from scripts.game_data.memorypack.leveldata_patrol_checkpoint_filter_sources import derive as filter_source
 _publication_gate(image,pins);ctx=NativeReferenceContext(image);md=image.metadata;base=image.pe.image_base
 need=lambda key,expected,actual:scalar.need('patrolHelper',key,expected,actual)
 producer=producer_source(image,pins);filtered=filter_source(image,pins)
 target=base+producer['symbolRvas']['patrolLookup'];body=pointer.owned(image,target)
 calls=[control_transfer(row)['target']for row in body['rows']if bytes.fromhex(row['bytes'])[:1]==b'\xe8'
  and len(bytes.fromhex(row['bytes']))==5]
 need('one-actual-class-prepare',1,len(calls));selector=_selector(producer['program'],target)
 thunk=lookup_program(body['regions'],target,prepare=calls[0],selector=selector)
 getter,=[m for m in md.methods_for(ctx.index.types[CONTROLLER])if md.string(m.name_index)=='get_patrolData'and m.parameter_count==0]
 scalar.owned_method_abi(image,ctx,getter.index,getter.declaring_type,(CORE,18,False),[],'patrolHelper.patrolGetter')
 need('actual-selected-nominal-getter-slot',getter.slot,selector);_vtable(image,getter.declaring_type,selector,getter.index,'patrolHelper.getter')
 field=ctx.field(CONTROLLER+'::<patrolData>k__BackingField');need('own-Core-reference',(CONTROLLER,CORE),field[:2])
 declared,=[f for f in md.fields_for(ctx.index.types[CONTROLLER])if md.string(f.name_index)=='<patrolData>k__BackingField']
 scalar.ordinary(image,ctx.type_pointer(declared.type_index),18,'patrolHelper.Core-reference-field',reference=True)
 need('reference-Core-domain',False,ctx.is_value_type(CORE))
 getter_at=image.method_pointer_va(getter);raw=image.pe.bytes_at_va(getter_at,8)
 pointer.leaf(image,getter_at,['488B81'+field[2].to_bytes(4,'little').hex().upper(),'C3'])
 getter_source=dict(sourceWindow=dict(startRva=getter_at-base,endRva=getter_at-base+8,
  sha256=hashlib.sha256(raw).hexdigest().upper()),sourceRegions=[[getter_at,raw.hex().upper()]],
  program=getter_program([(getter_at,raw)],getter_at,field_offset=field[2]),physicalFunctionExtentProved=False)
 base_target=base+filtered['symbolRvas']['baseProcess'];processes=[]
 for owner in filtered['actualAncestorChain'][1:]:
  for method in md.methods_for(ctx.index.types[owner]):
   if md.string(method.name_index)!='Process'or method.parameter_count!=1:continue
   try:at=image.method_pointer_va(method)
   except ValueError:continue
   if at==base_target:processes.append((owner,method))
 need('one-exact-owned-base-Process',1,len(processes));owner,method=processes[0]
 scalar.owned_method_abi(image,ctx,method.index,method.declaring_type,('bool',2,False),
  [('Beyond.Gameplay.ParamBlackboard',18,True)],'patrolHelper.baseProcess')
 process_body=pointer.owned(image,base_target)
 programs=[base_process_program(process_body['regions'],base_target,replacement_root_present=present)for present in(False,True)]
 need('same-optional-root-cell',programs[0]['optionalCallbackRootCell'],programs[1]['optionalCallbackRootCell'])
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-patrol-helper-paths.v1',
  status='validated-conditional-selected-helper-paths',nativeInputs=pins,
  lookupThunk=dict(actualProducer=producer,sourceWindows=body['windows'],sourceRegions=[[a-base,b.hex().upper()]for a,b in body['regions']],
   program=thunk,selectedGetterMethod=[getter.index,CONTROLLER,'get_patrolData',getter_at-base],
   selectedMetadataSlot=selector,nominalField=list(field),getterSource=getter_source,
   selectedControllerPatrolFieldReadProved=True,liveSelectedSlotMatchesCanonicalGetterRequired=True,
   liveReceiverClassObserved=False),
  baseProcess=dict(actualFilter=filtered,method=[method.index,owner,'Process',base_target-base],
   sourceWindows=process_body['windows'],sourceRegions=[[a-base,b.hex().upper()]for a,b in process_body['regions']],programs=programs,
   selectedAbsentReplacementReturnProved=True,liveReplacementAbsenceObserved=False),
  controllerLookupProved=False,blackboardEffectsProved=False,checkpointProducerProved=False,checkpointFilterProved=False,
  runtimeInvocationObserved=False,playbackProved=False,wholeOwnerAdmitted=False)))

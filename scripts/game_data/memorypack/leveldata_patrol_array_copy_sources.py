"""Patrol array-copy selected fast-helper control and argument preservation.

A normal true result from the actual fast helper is an explicit condition;
this caller alone does not establish a copy or a callback identity.  Both
arrays, nonnegative indices/count, equal ranks and valid disjoint frame storage
must remain stable.  Element compatibility, bounds and the fast helper's own
copy effects require their independent source before a preserving growth join.
"""
import json

# Instruction algorithms only. Their Int32 owner declarations, conditions,
# registrations and wire grammar are not consumed by this reference-array lane.
from scripts.game_data.memorypack.int_list_sources import copy_array as _copy_array,fast_copy as _fast_copy

SCHEMA='endfield.story-patrol-reference-array-copy-source.v1'


def _actual_call(regions,pattern):
 found=[];prefix=bytes.fromhex(pattern)
 for a,raw in regions:
  offset=raw.find(prefix)
  while offset>=0:
   site=a+offset+len(prefix)-1
   if offset+len(prefix)+4<=len(raw):found.append((site,site+5+int.from_bytes(raw[offset+len(prefix):offset+len(prefix)+4],'little',signed=True)))
   offset=raw.find(prefix,offset+1)
 if len(found)!=1:raise ValueError('storyPatrolArrayCopy.one-actual-owned-call:'+str(len(found)))
 return found[0]


def program(regions,entry):
 site,helper=_actual_call(regions,'89742420418bd6488bcfe8');checked=_copy_array(regions,entry,fast=helper)
 return dict(selectedBytes=checked['selectedBytes'],entry=entry,actualFastHelperTarget=helper,actualFastHelperCall=site,
  incomingArguments=dict(rcx='source array',edx='source index',r8='destination array',r9d='destination index',entryStack40='element count'),
  fastHelperArguments=dict(rcx='unchanged source array',edx='unchanged source index',r8='unchanged destination array',r9d='unchanged destination index',stack32='unchanged element count'),
  sourceAndDestinationNonnullRequired=True,sourceAndDestinationRanksEqualRequired=True,
  indicesAndCountNonnegativeRequired=True,rankByteOffset=308,fastHelperBoolTrueRequired=True,
  entryRspDeltaAtCall=-152,normalCallHomeSpaceAndAlignment=True,entryRspRestored=True,normalReturn=True,
  nonvolatilesRestored=['rbx','rsi','rdi','r12','r13','r14','r15'],
  fastHelperEffectsProved=False,arrayCopySemanticsProved=False,wholeGrowthOrConversionProved=False)


def fast_program(regions,entry):
 site,move=_actual_call(regions,'4883c1204903cde8');checked=_fast_copy(regions,entry,move=move)
 return dict(selectedBytes=checked['selectedBytes'],entry=entry,actualMoveTarget=move,actualMoveCall=site,
  incomingSourceAndDestinationNonnullRequired=True,ordinarySzArrayBoundsPointersNullRequired=True,
  sameElementClassRequired=True,elementClassDifferentFromObjectCellRequired=checked['excludedObjectClassCell'],
  elementBytesRequired=8,sourceAndDestinationIndicesNonnegativeRequired=True,
  sourceAndDestinationBoundsAndNonwrappingIndexSumsRequired=True,
  source='same source array +32+8*sourceIndex',destination='same destination array +32+8*destinationIndex',
  moveBytes='unchanged count *8',actualCollectorCell=checked['collectorZeroCondition']+1,
  disabledCollectorRequired=True,returnsBoolTrue=True,entryRspRestored=True,
  nonvolatilesRestored=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],normalReturn=True,
  moveEffectsProved=False,actualArrayRuntimeClassObserved=False,wholeGrowthOrConversionProved=False)


def derive(image,pins,*,count_limit=4096):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.forward_copy_sources import derive as derive_copy
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
 from scripts.game_data.il2cpp import enum_nominal_callback_sources as profile_owner
 from scripts.game_data.memorypack import pointer_param as pointer,leveldata_patrol_list_growth_sources as growth_owner
 from scripts.game_data.memorypack.leveldata_patrol_count_selection_sources import reference_program
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
 if type(count_limit)is not int or not 1<=count_limit<=4096:raise ValueError('storyPatrolArrayCopy.finite-count-domain')
 growth=growth_owner.derive(image,pins);proof=growth['proof'];body=proof['growth']
 regions=[(at,bytes.fromhex(raw))for at,raw in body['sourceRegions']]
 copy_site,copy_target=_actual_call(regions,'89442420e8')
 copied=pointer.owned(image,copy_target);caller=program(copied['regions'],copied['pointer'])
 fast=pointer.owned(image,caller['actualFastHelperTarget']);selected=fast_program(fast['regions'],fast['pointer'])
 disabled=proof['selectedFirstGrowth']['disabledCollectorCell']
 if selected['actualCollectorCell']!=disabled:raise ValueError('storyPatrolArrayCopy.same-actual-disabled-collector')
 profile=json.loads(profile_owner.CONTRACT_PATH.read_bytes());profile_owner.validate_profile(profile,pins)
 normal=pointer.owned(image,base+profile['sourceEntries']['primitiveEntryRva'])
 ref=reference_program(normal['regions'],normal['pointer'],image_base=base)
 if selected['elementClassDifferentFromObjectCellRequired']!=ref['objectClassCell']:raise ValueError('storyPatrolArrayCopy.same-actual-excluded-Object-cell')
 declaration,=[m for m in md.methods_for(ctx.index.types['System.Array'])if md.string(m.name_index)=='Copy'
  and image.method_pointer_va(m)==copy_target]
 if not declaration.flags&16 or ctx.type_name(declaration.return_type)!='void' or [ctx.type_name(p.type_index)for p in md.parameters_for(declaration)]!=['System.Array','int','System.Array','int','int']:
  raise ValueError('storyPatrolArrayCopy.actual-Array-Copy-signature')
 move=derive_copy(image,pins,entry=selected['actualMoveTarget'],max_bytes=max(64,count_limit*8))
 def capture(b):return dict(sourceWindows=b['windows'],sourceRegions=[[a,h.hex().upper()]for a,h in b['regions']])
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-reference-array-copy-source',nativeInputs=pins,
  proof=dict(firstGrowthSource=growth,actualGrowthCopyCallRva=copy_site-base,ownArrayCopyMethodDefinition=declaration.index,
   arrayCopy=capture(copied),selectedArrayCopy=caller,fastCopy=capture(fast),selectedSameReferenceClassFastCopy=selected,
   actualObjectReferenceNormalizer=ref,actualForwardCopySource=move),
  countLimit=count_limit,elementBytes=8,maxCopyBytes=count_limit*8,
  exactSameReferenceBytesPreservedConditional=True,copyWholeSourceAndFrameProved=True,
  laterGrowthAllocationAndWholeConversionProved=False,runtimeInvocationObserved=False,playbackProved=False,
  evidenceBoundary=dict(exact='Actual growth Array.Copy E8/signature, complete five-argument caller and same-element-class FastCopy path, disabled collector and exact actual forward byte-copy source across the finite reference-byte domain.',
   conditional='Valid initialized identical ordinary reference-element classes distinct from System.Object with element-size8, bounds/nonwrapping index/count arithmetic, disjoint arrays/frame, disabled collector and actual forward-copy mode/CPU conditions. All opaque metadata/helper state remains coherent; no Int32 nominal or wire proof is borrowed.',
   unresolved=['later growth allocation/cache branches','actual inflated array/runtime class selection','full conversion/initializer/checkpoint/playback']))))

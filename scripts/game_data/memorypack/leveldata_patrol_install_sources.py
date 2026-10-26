"""Exact conditional New Patrol installation and caller argument transfer.

The helper's canonical slot branch stores the unchanged supplied Core reference.
Its dynamic callback alternative and all effects of the preceding conversion are
outside this proof. No live controller, initializer or playback is observed.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.leveldata_patrol_config_prefix_sources import CONTROLLER,CORE


def need(key,condition):
 if not condition:raise ValueError('storyPatrolInstall.'+key)


def install_program(regions,entry,*,prepare,setter,barrier,field_offset,slot):
 """Own all bytes through normal RET on the exact canonical setter branch."""
 need('literal-reference-field-and-slot',type(field_offset)is int and 128<=field_offset<2**31
  and type(slot)is int and 0<=slot<2**16
  and all(type(n)is int and n>0 for n in(prepare,setter,barrier)))
 offset=320+slot*16
 g=BytesPath(regions,entry)
 g.take('48895c2408','57','4883ec20','488b0a','498bf8','488bda');g.call(prepare)
 g.take('488b03','4c8b88'+offset.to_bytes(4,'little').hex(),
  '4c8b80'+(offset+8).to_bytes(4,'little').hex())
 need('own-named-setter-marker',g.relative('488d05')==setter)
 g.take('4c3bc8');g.branch('0f85',False)
 g.take('488d8b'+field_offset.to_bytes(4,'little').hex(),
  '4889bb'+field_offset.to_bytes(4,'little').hex());g.call(barrier)
 g.take('488b5c2430','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,normalReturn=True,entryRspRestored=True,
  restoredNonvolatiles=['rbx','rdi'],receiverArgument='incoming RDX preserved in RBX',
  storedReferenceArgument='incoming R8 preserved unchanged in RDI',storedBytes=8,
  fieldOffset=field_offset,selectedSlot=slot,callbackByteOffset=offset,methodInfoByteOffset=offset+8,
  selectedCallbackEqualsOwnNamedSetterRequired=True,selectedCanonicalBranchOnly=True,
  wholeReferenceStoredUnchanged=True,barrierArgument='address of the same owned reference field',
  barrierTargetVa=barrier,normalPreparationPreservingNonvolatilesRequired=True,
  independentDisabledBarrierSourceRequired=True,nonnullCompatibleReceiverRequired=True,
  dynamicCallbackAlternativeAdmitted=False,liveReceiverClassObserved=False,
  runtimeInvocationObserved=False,wholeInitializerProved=False,playbackProved=False)


def converted_argument_program(regions,entry,*,convert,install):
 """Selected successful lookup result to conversion and installation calls.

The Config local's lookup provenance, the conversion's full effects and output,
and the earlier initializer path are separate. These bytes only preserve the
actual byref output/local/reference argument flow between the two calls.
"""
 need('literal-convert-and-install-targets',all(type(n)is int and n>0 for n in(convert,install)))
 g=BytesPath(regions,entry);g.take('84c0');g.branch('74',False,1)
 g.take('488b542430','4c8d442438','4533c9','488bcf');convert_site=g.at;g.call(convert)
 g.take('4c8b442438','488bd7');install_site=g.at;g.call(install)
 return dict(selectedBytes=g.seen,continuationInstructionVa=g.at,selectedLookupResultTrue=True,
  controllerReceiver='RDI to conversion RCX and installation RDX',
  configReferenceLocalOffset=48,coreOutputReferenceLocalOffset=56,localReferenceBytes=8,
  configArgumentRegister='RDX',conversionOutputByrefRegister='R8',
  conversionMethodInfoZero=True,conversionInstructionVa=convert_site,installationInstructionVa=install_site,
  outputLocalAddressPassedToConversion=True,sameOutputLocalReferencePassedToInstall=True,
  disjointConfigAndCoreLocals=True,conversionNormalReturnRequired=True,
  conversionOutputSemanticsProved=False,lookupEffectsProved=False,wholeInitializerProved=False,
  runtimeInvocationObserved=False,playbackProved=False)


def derive(image,pins):
 """Fresh actual caller/nominal setter slot/full helper/disabled barrier joins."""
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import _vtable
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
 from scripts.game_data.memorypack.leveldata_patrol_config_prefix_sources import derive as derive_prefix
 from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
 _publication_gate(image,pins);ctx=NativeReferenceContext(image);md=image.metadata;base=image.pe.image_base
 prefix=derive_prefix(image,pins);convert=base+prefix['proof']['metadataJoin']['method']['targetRva']
 owner=ctx.index.types[CONTROLLER]
 setter,=[m for m in md.methods_for(owner)if md.string(m.name_index)=='set_patrolData'and m.parameter_count==1]
 scalar.owned_method_abi(image,ctx,setter.index,owner.index,('void',1,False),[(CORE,18,True)],'storyPatrolInstall.setter')
 _vtable(image,owner.index,setter.slot,setter.index,'storyPatrolInstall.exactSetterSlot')
 field=ctx.field(CONTROLLER+'::<patrolData>k__BackingField')
 need('same-own-Core-reference-field',tuple(field[:2])==(CONTROLLER,CORE)and not ctx.is_value_type(CORE))
 declared,=[f for f in md.fields_for(owner)if md.string(f.name_index)=='<patrolData>k__BackingField']
 scalar.ordinary(image,ctx.type_pointer(declared.type_index),18,'storyPatrolInstall.field',reference=True)
 init,=[m for m in md.methods_for(owner)if md.string(m.name_index)=='_InitLevelData']
 need('own-instance-initializer',init.declaring_type==owner.index and not init.flags&16)
 caller=pointer.owned(image,image.method_pointer_va(init));rows=caller['rows'];conversions=[]
 for i,row in enumerate(rows):
  raw=bytes.fromhex(row['bytes'])
  if len(raw)==5 and raw[0]==0xe8 and control_transfer(row)['target']==convert:conversions.append(i)
 need('one-actual-own-conversion-call',len(conversions)==1);index=conversions[0]
 need('complete-owned-argument-fragment',index>=6 and index+3<len(rows))
 first=rows[index-6];last=rows[index+3]
 need('actual-postconversion-install-E8',len(bytes.fromhex(last['bytes']))==5 and bytes.fromhex(last['bytes'])[0]==0xe8)
 install=control_transfer(last)['target'];body=pointer.owned(image,install)
 direct=[control_transfer(r)['target']for r in body['rows']if len(bytes.fromhex(r['bytes']))==5 and bytes.fromhex(r['bytes'])[0]==0xe8]
 need('exact-prepare-and-disabled-barrier-calls',len(direct)==2)
 program=install_program(body['regions'],install,prepare=direct[0],setter=image.method_pointer_va(setter),
  barrier=direct[1],field_offset=field[2],slot=setter.slot)
 fragment=converted_argument_program(caller['regions'],int(first['va'],16),convert=convert,install=install)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-patrol-install-source.v1',
  status='validated-conditional-canonical-install-source',nativeInputs=pins,
  proof=dict(prefix=prefix,setterMethod=[setter.index,CONTROLLER,'set_patrolData',image.method_pointer_va(setter)-base],
   setterSlot=setter.slot,nominalField=list(field),initializerMethod=[init.index,CONTROLLER,'_InitLevelData',caller['pointer']-base],
   callerWindows=caller['windows'],callerRegions=[(a,b.hex().upper())for a,b in caller['regions']],
   callerArgumentProgram=fragment,helperTargetRva=install-base,helperWindows=body['windows'],
   helperRegions=[(a,b.hex().upper())for a,b in body['regions']],helperProgram=program,
   disabledBarrier=_barrier(image,direct[1])),
  canonicalFieldInstallationSourceProved=True,conversionOutputSemanticsProved=False,
  wholeConversionProved=False,wholeInitializerProved=False,controllerInstallationObserved=False,
  checkpointProducerProved=False,checkpointFilterProved=False,runtimeInvocationObserved=False,playbackProved=False,
  evidenceBoundary=dict(exact='Own New controller setter metadata and slot, full helper canonical branch stores unchanged Core-reference argument into the exact own backing field; actual initializer passes the conversion output local to that helper.',
   conditional='Compatible nonnull receiver, selected slot equal to own named setter, normally returning preparation/conversion, disabled unchanged collector and stable disjoint locals. Only the successful lookup argument fragment is proved.',
   unresolved=['whole Config-to-Core conversion and lookup effects','dynamic setter callback alternative','whole initializer paths and live selection','checkpoint sender/receiver and runtime playback']))))

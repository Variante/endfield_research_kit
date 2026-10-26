"""Exact direct ReadUnmanaged<TrackingBounds> raw36, distinct from wrapper MC3.

The actual typed parent supplies a hidden output and closed R8 MethodInfo. The
selected source guards36, copies16+16+4 unchanged and calls its independently
owned Advance36 helper. The nominal layout, direct source and actual call are
proved independently; the canonical wrapper's header/default and any list
callback have no role in this raw grammar.
"""
import hashlib
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.leveldata_tracking_value_sources import BOUNDS,VECTOR,SPECS

LABEL='storyTrackingRawBounds'
SCHEMA='endfield.story-tracking-bounds-raw36.v1'
CAPABILITY='story-tracking-bounds-raw36'


def need(check,condition):
 if not condition:raise ValueError(LABEL+'.'+check)


def program(regions,entry,offsets):
 keys=('currentPtr','bufferLength','advancedCount','consumed')
 need('distinct-small-owned-Reader-slots',set(offsets)>=set(keys)and len({offsets[k]for k in keys})==4
  and all(type(offsets[k])is int and 0<=offsets[k]<128 for k in keys))
 rem=bytes((offsets['bufferLength'],)).hex();cur=bytes((offsets['currentPtr'],)).hex()
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','837a'+rem+'24','488bda','488bf9')
 g.branch('7d',True,1)
 g.take('488b43'+cur,'ba24000000','488bcb','0f1000','0f104810','8b4020','0f1107','0f114f10','894720')
 site=g.at;advance=g.relative('e8');g.take('488b5c2430','488bc7','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,wireBytes=36,managedOutputBytes=36,hiddenOutputRegister='rcx',readerRegister='rdx',
  methodInfoRegister='r8',copiedSlices=[[0,16],[16,16],[32,4]],advanceInstructionVa=site,advanceTargetVa=advance,
  actualReaderArgument='rbx',actualSignedCountArgument=36,sameOutputReturnedInRax=True,
  referenceLaneOffsets=[],paddingByteRanges=[],entryRspRestored=True,allNonvolatilesRestored=True,
  frame=dict(entryRspDelta=-40,shadow=[0,32],savedEntryHomes=dict(rbx=[8,16]),pushed=['rdi']),normalReturn=True,
  independentAdvanceSourceRequired=True,objectHeaderRead=False,canonicalWrapperUsed=False)


def require_request(usage,*,type_definition,argument_raw,method_identity,container,parameter_owner,return_raw):
 need('exact-closed-raw-request',(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),
  usage.get('classArguments'),usage.get('methodArguments'))==(6,'MemoryPack.MemoryPackReader','ReadUnmanaged',[],[BOUNDS]))
 raw=bytes.fromhex(usage.get('instructionHex',''));spec=usage.get('methodSpec')
 need('actual-R8-closed-MethodInfo',len(raw)==7 and raw[:3]==bytes.fromhex('4c8b05')
  and type(usage.get('instructionRva'))is int and usage['instructionRva']>=0)
 need('literal-owned-closed-spec',isinstance(spec,(list,tuple))and len(spec)==3 and all(type(n)is int for n in spec)
  and spec[0]>=0 and spec[1]==-1 and spec[2]>=0 and type(usage.get('methodSpecIndex'))is int and usage['methodSpecIndex']>=0)
 need('exact-nominal-value17',type(type_definition)is int and type_definition>=0 and len(argument_raw)==16
  and argument_raw[10:12]==bytes((17,128))and int.from_bytes(argument_raw[:8],'little')==type_definition)
 need('own-instance-noargument-Reader',method_identity==(spec[0],'MemoryPack.MemoryPackReader','ReadUnmanaged',0,0))
 need('reciprocal-sole-MVAR',len(container)==4 and all(type(n)is int for n in container)
  and tuple(container[:3])==(spec[0],1,1)and container[3]>=0
  and parameter_owner.get('methodIndex')==spec[0]and type(parameter_owner.get('ordinal'))is int and parameter_owner['ordinal']==0
  and len(return_raw)==16 and return_raw[10:12]==bytes((30,0))and int.from_bytes(return_raw[:8],'little')==container[3])
 return dict(typeName=BOUNDS,typeDefinition=type_definition,readerMethodDefinition=spec[0],sourceMethod='ReadUnmanaged')


def bind_call(usage,instruction,*,source_target,base):
 need('literal-actual-owned-E8',type(base)is int and type(source_target)is int and source_target>base
  and isinstance(instruction,(tuple,list))and len(instruction)==2 and type(instruction[0])is int and instruction[0]>=0)
 raw=bytes.fromhex(instruction[1]);need('exact-actual-E8-target',len(raw)==5 and raw[0]==232
  and base+instruction[0]+5+int.from_bytes(raw[1:],'little',signed=True)==source_target)
 need('actual-context-precedes-source',type(usage.get('instructionRva'))is int and usage['instructionRva']<instruction[0])
 return dict(sourceInstruction=instruction,sourceTargetRva=source_target-base,
  parentArgumentFlowRequired=True,parentFieldAdmitted=False,canonicalPointerIdentityClaimed=False)


def layout(image,ctx):
 from scripts.game_data.memorypack import scalar_param_native as scalar
 md=image.metadata;td=ctx.index.types[BOUNDS];vector=ctx.index.types[VECTOR]
 sizes={};actual=[]
 for name,definition,fields,want in((BOUNDS,td,SPECS[BOUNDS]['fields'],52),(VECTOR,vector,
  tuple((axis,'float',16+4*i)for i,axis in enumerate(('x','y','z'))),28)):
  need('plain-owned-value:'+name,ctx.is_value_type(name)and not ctx.is_enum(name)
   and ctx.parent(name)=='System.ValueType'and definition.generic_container_index<0)
  scalar.ordinary(image,ctx.type_pointer(definition.byval_type_index),17,LABEL+'.'+name)
  rows=[f for f in md.fields_for(definition)if not ctx.field_attributes(f.type_index)&16]
  resolved=sorted([(md.string(f.name_index),*ctx.field(name+'::'+md.string(f.name_index))[1:])for f in rows],key=lambda r:r[2])
  need('complete-owned-field-plan:'+name,resolved==list(fields))
  for field in rows:scalar.ordinary(image,ctx.type_pointer(field.type_index),17 if name==BOUNDS else 12,LABEL+'.field')
  need('bounded-size-row',0<=definition.index<image.registration['typeDefinitionsSizesCount'])
  pointer=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+definition.index*8)
  need('own-boxed-size:'+name,image.pe.u32_at_va(pointer)==want)
  sizes[name]=dict(boxedBytes=image.pe.u32_at_va(pointer),marshaledNativeBytes=image.pe.u32_at_va(pointer+4))
  if name==BOUNDS:actual=resolved
 return dict(typeName=BOUNDS,typeDefinition=td.index,fields=actual,managedBytes=36,referenceLaneOffsets=[],paddingByteRanges=[],
  vector3Fields=[[axis,'float',16+4*i]for i,axis in enumerate(('x','y','z'))],sizeRows=sizes,
  layoutUsedForWireWidth=False,canonicalWrapperWireUsed=False)


def _owned_regions(regions,windows,*,base,label):
 need('complete-owned-regions:'+label,type(base)is int and isinstance(regions,(list,tuple))and bool(regions)
  and isinstance(windows,(list,tuple))and len(regions)==len(windows)
  and len({w.get('startRva')for w in windows})==len(windows))
 result=[];seen=set()
 for at,h in regions:
  need('literal-region:'+label,type(at)is int and type(h)is str and at not in seen);seen.add(at);data=bytes.fromhex(h)
  own=[w for w in windows if type(w.get('startRva'))is int and type(w.get('endRva'))is int
   and base+w['startRva']==at and w['endRva']-w['startRva']==len(data)]
  need('exact-full-window-bytes:'+label,len(own)==1 and bool(data)
   and hashlib.sha256(data).hexdigest().upper()==own[0].get('sha256'))
  result.append((at,data))
 return result


def verify(component,pins):
 """Pure complete-native-window replay; fresh native admission is separate."""
 from scripts.game_data.memorypack.generated_called_advance_sources import advance_program
 need('same-selected-raw36-component',component.get('schema')==SCHEMA
  and component.get('status')=='validated-conditional-tracking-bounds-raw36'and component.get('nativeInputs')==pins
  and component.get('typeName')==BOUNDS and component.get('capability')==CAPABILITY
  and all(type(component.get(k))is int and component[k]==36 for k in('wireBytes','managedBytes'))
  and type(component.get('sourceTargetRva'))is int and component['sourceTargetRva']>0
  and all(component.get(k)is True for k in('actualSourceProved','allFourReaderUpdatesProved','entryRspRestored','allNonvolatilesRestored'))
  and all(component.get(k)is False for k in('canonicalPointerIdentityClaimed','canonicalWrapperUsed','objectHeaderRead','parentFieldAdmitted','wholeOwnerAdmitted')))
 proof=component.get('proof',{});selected=proof.get('program',{}).get('selectedBytes',[])
 need('literal-selected-source-entry',bool(selected)and type(selected[0][0])is int)
 base=selected[0][0]-component['sourceTargetRva'];offsets=proof['readerOffsets'];normalize=lambda v:json.loads(json.dumps(v))
 regions=_owned_regions(proof['sourceRegions'],proof['sourceWindows'],base=base,label='raw36')
 replay=program(regions,base+component['sourceTargetRva'],offsets)
 need('complete-actual-raw36-program',normalize(replay)==proof['program'])
 usage=proof['typedRequest'];need('same-current-closed-request',usage.get('tag')==6
  and(usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))==
   ('MemoryPack.MemoryPackReader','ReadUnmanaged',[],[BOUNDS])
  and usage.get('methodSpec',[None])[0]==component.get('readerMethodDefinition')
  and bytes.fromhex(usage.get('instructionHex',''))[:3]==bytes.fromhex('4c8b05'))
 caller=bind_call(usage,proof['actualCaller']['sourceInstruction'],source_target=base+component['sourceTargetRva'],base=base)
 need('exact-actual-caller-replay',normalize(caller)==proof['actualCaller'])
 advance=proof['advanceSource'];need('same-independent-advance',advance.get('nativeInputs')==pins
  and type(advance.get('targetRva'))is int and base+advance['targetRva']==replay['advanceTargetVa']
  and advance.get('readerOffsets')==offsets and advance.get('registeredMethodIdentityClaimed')is False
  and all(advance.get(k)is True for k in('completeAdvanceProgramProved','allFourReaderUpdatesProved','entryRspRestored',
   'allNonvolatilesRestored','zeroCountReturnsWithoutMutation')))
 ar=_owned_regions(advance['sourceRegions'],advance['codeWindows'],base=base,label='advance')
 programs=[advance_program(ar,replay['advanceTargetVa'],offsets,zero=z)for z in(False,True)]
 need('both-complete-advance-paths',normalize(programs)==advance.get('programs'))
 return base


def derive(image,pins,*,typed_request,source_target,source_instruction):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.context import method_parameter_owner
 from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
 from scripts.game_data.memorypack.generated_called_advance_sources import derive as advance_source
 _publication_gate(image,pins);validate_typed_usage_context(image,typed_request,label=LABEL)
 base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;nominal=layout(image,ctx)
 argument,=image.instantiations.resolve(typed_request['methodSpec'][2]).arguments
 scalar.ordinary(image,argument.type_pointer_va,17,LABEL+'.actualArgument');raw=image.pe.bytes_at_va(argument.type_pointer_va,16)
 method=md.methods[typed_request['methodSpec'][0]];section=md.sections['genericContainers'];at=section.offset+method.generic_container_index*16
 need('bounded-owned-generic-container',method.generic_container_index>=0 and section.offset<=at<=section.offset+section.size-16)
 container=struct.unpack_from('<iiii',md.buf,at);parameter=method_parameter_owner(md.buf,container[3],
  [m.generic_container_index for m in md.methods],source=LABEL)
 returned=image.pe.bytes_at_va(ctx.type_pointer(method.return_type),16)
 need('zero-declared-parameters',not list(md.parameters_for(method)))
 identity=require_request(typed_request,type_definition=nominal['typeDefinition'],argument_raw=raw,
  method_identity=(method.index,image.type_name(method.declaring_type),md.string(method.name_index),method.flags&16,method.parameter_count),
  container=container,parameter_owner=parameter,return_raw=returned)
 actual=bind_call(typed_request,source_instruction,source_target=source_target,base=base)
 image.check_instruction_windows([source_instruction],label=LABEL+'.actualParentE8')
 source=pointer.owned(image,source_target);offsets=scalar.reader_offsets(image,LABEL)
 proved=program(source['regions'],source_target,offsets)
 advance=advance_source(image,pins,target=proved['advanceTargetVa'],offsets=offsets)
 observed=GenericEntries(image).observe(method.index,[],[BOUNDS])
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-tracking-bounds-raw36',nativeInputs=pins,**identity,
  capability=CAPABILITY,wireBytes=36,managedBytes=36,referenceLaneOffsets=[],paddingByteRanges=[],
  sourceTargetRva=source_target-base,resultAbi='hidden-output-rcx',contextRegister='r8',
  actualSourceProved=True,allFourReaderUpdatesProved=True,entryRspRestored=True,allNonvolatilesRestored=True,
  canonicalPointerIdentityClaimed=False,canonicalWrapperUsed=False,objectHeaderRead=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  proof=dict(nominalLayout=nominal,typedRequest=typed_request,argumentRawHex=raw.hex().upper(),genericContainer=container,
   reciprocalParameter=parameter,returnRawHex=returned.hex().upper(),actualCaller=actual,program=proved,
   canonicalRegistrationObservations=observed,sourceWindows=source['windows'],
   sourceRegions=[(at,data.hex().upper())for at,data in source['regions']],advanceSource=advance,readerOffsets=offsets),
  evidenceBoundary=dict(exact='Own nominal TrackingBounds physical fields and selected direct ReadUnmanaged MethodSpec/E8, complete literal36 capture/store/hidden return and independently owned Advance36/four Reader updates.',
   conditional='At least36 coherent contiguous input bytes, exact initialized nominal MethodInfo, disjoint Reader/input/output/frame and normal compatible helper; counters do not wrap. Incoming parent argument/local/store/frame joins remain separate.',
   structuralOnly='All coordinate bits retained; runtime tracking interpretation unproved.',
   unresolved=['actual enclosing local/field/frame join','refill/errors','canonical wrapper/default/list selection','whole owner/physical EOF']))))

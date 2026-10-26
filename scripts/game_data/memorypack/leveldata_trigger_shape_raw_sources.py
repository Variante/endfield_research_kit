"""Actual direct TriggerShapeData raw44; independent of wrapper MC5/defaults."""
import json
import struct
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.leveldata_trigger_shape_value_sources import TYPE,ENUM,VECTOR,FIELDS

LABEL='storyTriggerShapeRaw44'
CAP='story-trigger-shape-raw44'


def need(check,condition):
 if not condition:raise ValueError(LABEL+'.'+check)


def program(regions,entry,offsets):
 keys=('currentPtr','bufferLength','advancedCount','consumed')
 need('four-owned-small-Reader-slots',set(offsets)>=set(keys)and len({offsets[k]for k in keys})==4
  and all(type(offsets[k])is int and 0<=offsets[k]<128 for k in keys))
 cur=bytes((offsets['currentPtr'],)).hex();rem=bytes((offsets['bufferLength'],)).hex()
 g=BytesPath(regions,entry)
 g.take('48895c2408','57','4883ec20','837a'+rem+'2c','488bda','488bf9');g.branch('7d',True,1)
 g.take('488b43'+cur,'ba2c000000','488bcb','0f1000','0f104810','0f1107','f20f104020','8b4028',
  '0f114f10','f20f114720','894728')
 site=g.at;advance=g.relative('e8');g.take('488b5c2430','488bc7','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,wireBytes=44,managedOutputBytes=44,hiddenOutputRegister='rcx',readerRegister='rdx',
  contextRegister='r8',copiedSlices=[[0,16],[16,16],[32,8],[40,4]],advanceInstructionVa=site,advanceTargetVa=advance,
  actualReaderArgument='rbx',actualSignedCountArgument=44,sameOutputReturnedInRax=True,
  referenceLaneOffsets=[],paddingByteRanges=[],entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,
  frame=dict(entryRspDelta=-40,shadow=[0,32],savedEntryHomes=dict(rbx=[8,16]),pushed=['rdi']),
  objectHeaderRead=False,canonicalWrapperUsed=False,independentAdvanceSourceRequired=True)


def layout(image,ctx):
 """Exact current nominal physical fields, without Reader/wire admission."""
 from scripts.game_data.memorypack import scalar_param_native as scalar
 md=image.metadata;td=ctx.index.types[TYPE]
 fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
 actual=sorted([(md.string(f.name_index),*ctx.field(TYPE+'::'+md.string(f.name_index))[1:])for f in fields],key=lambda r:r[2])
 need('own-nominal44-layout',actual==list(FIELDS)and ctx.is_value_type(TYPE)and not ctx.is_enum(TYPE)
  and ctx.parent(TYPE)=='System.ValueType'and td.generic_container_index<0)
 scalar.ordinary(image,ctx.type_pointer(td.byval_type_index),17,LABEL+'.nominal')
 need('bounded-own-size-index',0<=td.index<image.registration['typeDefinitionsSizesCount'])
 size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*td.index)
 need('own-boxed-and-managed44-sizes',(image.pe.u32_at_va(size),image.pe.u32_at_va(size+4))==(60,44))
 for field in fields:scalar.ordinary(image,ctx.type_pointer(field.type_index),12 if ctx.type_name(field.type_index)=='float'else 17,LABEL+'.field')
 vector=ctx.index.types[VECTOR];vf=[f for f in md.fields_for(vector)if not ctx.field_attributes(f.type_index)&16]
 need('own-Vector3-float-fields',[(md.string(f.name_index),*ctx.field(VECTOR+'::'+md.string(f.name_index))[1:])for f in vf]
  ==[(axis,'float',16+4*j)for j,axis in enumerate('xyz')])
 for f in vf:scalar.ordinary(image,ctx.type_pointer(f.type_index),12,LABEL+'.vectorField')
 backing=ctx.field(ENUM+'::value__');need('own-exact-enum32',ctx.parent(ENUM)=='System.Enum'and backing[0]==ENUM
  and backing[1]in('int','uint')and backing[2]==16)
 return dict(typeName=TYPE,typeDefinition=td.index,managedBytes=44,fields=actual,
  vectorFields=[list(ctx.field(VECTOR+'::'+a))for a in'xyz'],enumBacking=list(backing),
  boxedBytes=60,referenceLaneOffsets=[],paddingByteRanges=[],wireGrammarAdmitted=False,
  readerSourceAdmitted=False,parentFieldAdmitted=False)


def derive(image,pins,*,typed_request,source_target,source_instruction):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.context import method_parameter_owner
 from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
 from scripts.game_data.memorypack.generated_called_advance_sources import derive as advance_source
 from scripts.game_data.memorypack.leveldata_tracking_raw_sources import bind_call
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
 validate_typed_usage_context(image,typed_request,label=LABEL)
 td=ctx.index.types[TYPE];physical=layout(image,ctx);actual=physical['fields'];backing=physical['enumBacking']
 need('actual-closed-ReadUnmanaged-request',(typed_request.get('tag'),typed_request.get('typeName'),typed_request.get('methodName'),
  typed_request.get('classArguments'),typed_request.get('methodArguments'))==(6,'MemoryPack.MemoryPackReader','ReadUnmanaged',[],[TYPE]))
 spec=typed_request['methodSpec'];need('closed-no-class-spec',isinstance(spec,(tuple,list))and len(spec)==3
  and all(type(n)is int for n in spec)and spec[0]>=0 and spec[1]==-1 and spec[2]>=0)
 ins=bytes.fromhex(typed_request['instructionHex']);need('actual-R8-MethodInfo',len(ins)==7 and ins[:3]==bytes.fromhex('4c8b05'))
 argument,=image.instantiations.resolve(spec[2]).arguments;raw=image.pe.bytes_at_va(argument.type_pointer_va,16)
 scalar.ordinary(image,argument.type_pointer_va,17,LABEL+'.argument')
 need('own-ordinary-value17-128',raw[10:12]==bytes((17,128))and int.from_bytes(raw[:8],'little')==td.index)
 method=md.methods[spec[0]];need('own-instance-no-parameter-reader',image.type_name(method.declaring_type)=='MemoryPack.MemoryPackReader'
  and md.string(method.name_index)=='ReadUnmanaged'and not(method.flags&16)and method.parameter_count==0 and not list(md.parameters_for(method)))
 section=md.sections['genericContainers'];at=section.offset+method.generic_container_index*16
 need('bounded-owned-container',method.generic_container_index>=0 and section.offset<=at<=section.offset+section.size-16)
 container=struct.unpack_from('<iiii',md.buf,at);need('sole-owned-method-generic-parameter',container[:3]==(method.index,1,1)and container[3]>=0)
 parameter=method_parameter_owner(md.buf,container[3],[m.generic_container_index for m in md.methods],source=LABEL)
 returned=image.pe.bytes_at_va(ctx.type_pointer(method.return_type),16)
 need('exact-reciprocal-MVAR-return',parameter['methodIndex']==method.index and type(parameter['ordinal'])is int and parameter['ordinal']==0
  and returned[10:12]==bytes((30,0))and int.from_bytes(returned[:8],'little')==container[3])
 caller=bind_call(typed_request,source_instruction,source_target=source_target,base=base)
 image.check_instruction_windows([source_instruction],label=LABEL+'.actualE8')
 body=pointer.owned(image,source_target);offsets=scalar.reader_offsets(image,LABEL);proved=program(body['regions'],source_target,offsets)
 advance=advance_source(image,pins,target=proved['advanceTargetVa'],offsets=offsets)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-trigger-shape-raw44.v1',status='validated-conditional-trigger-shape-raw44',
  nativeInputs=pins,typeName=TYPE,capability=CAP,wireBytes=44,managedBytes=44,resultAbi='hidden-local',contextRegister='r8',
  readerMethodDefinition=method.index,sourceTargetRva=source_target-base,actualSourceProved=True,
  referenceLaneOffsets=[],paddingByteRanges=[],objectHeaderRead=False,canonicalWrapperUsed=False,
  enumType=ENUM,enumBacking=backing[1],actualCallbackSelectionRequired=False,
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,proof=dict(fields=actual,vectorFields=physical['vectorFields'],
   enumBacking=list(backing),typedRequest=typed_request,argumentRawHex=raw.hex().upper(),genericContainer=container,
   reciprocalParameter=parameter,returnRawHex=returned.hex().upper(),actualCaller=caller,actualProgram=proved,readerOffsets=offsets,
   actualWindows=body['windows'],actualSourceRegions=[[a,b.hex().upper()]for a,b in body['regions']],advanceSource=advance),
  evidenceBoundary=dict(exact='Actual nominal direct ReadUnmanaged<TriggerShapeData> MethodSpec/E8 and complete literal44 raw16+16+8+4 buffered transfer, independently owned Advance/four Reader updates. Physical field order differs from wrapper MC5 order.',
   conditional='Enough stable contiguous input, disjoint input/output/Reader/frame, initialized exact MethodInfo, normal compatible Advance helper and nonwrapping counters. No refill or malformed input path is admitted.',
   structuralOnly='All enum/coordinate/radius bits are retained; source proves storage rather than gameplay interpretation.',
   unresolved=['actual enclosing local/field/setter/full-frame','canonical wrapper/default44/list callbacks','runtime behavior or whole owner/physical EOF']))))

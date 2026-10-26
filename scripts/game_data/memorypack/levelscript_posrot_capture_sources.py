"""Exact inline PosRot24 captures, separate from its MC2 value formatter.

The selected Encounter source captures16+8 raw bytes before Advance24 and
stores them unchanged into a named field afterwards. Parent lifetime, full
frames, factories and field grammar are deliberately separate obligations.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.PosRot'
PARENT='Beyond.Gameplay.EncounterData+IntroPart'
FIELDS=('teleportSlot0','teleportSlot1','teleportSlot2','teleportSlot3')
SCHEMA='endfield.story-posrot-inline-capture.v1'


def need(key,condition):
 if not condition:raise ValueError('storyPosRotCapture.'+key)


def capture_program(regions,entry,offsets):
 keys=('currentPtr','bufferLength','advancedCount','consumed')
 need('four-distinct-owned-Reader-slots',set(offsets)>=set(keys)and len({offsets[k]for k in keys})==4
  and all(type(offsets[k])is int and 0<=offsets[k]<128 for k in keys))
 cur,rem=(bytes((offsets[k],)).hex()for k in('currentPtr','bufferLength'))
 g=BytesPath(regions,entry)
 g.take('837b'+rem+'18');wrapper=g.at;g.take('488b37');g.branch('0f8c',False)
 pointer=g.at;g.take('488b43'+cur,'ba18000000','488bcb')
 low=g.at;g.take('0f1030');high=g.at;g.take('f20f107810');site=g.at;advance=g.relative('e8')
 return dict(selectedBytes=g.seen,guardInstructionVa=entry,sourcePointerInstructionVa=pointer,
  sourcePointerRegister='rax',wireBytes=24,
  capturedSourceSlices=[dict(register='xmm6',sourceOffset=0,bytes=16,loadInstructionVa=low,kind='sse'),
   dict(register='xmm7',sourceOffset=16,bytes=8,loadInstructionVa=high,kind='sse')],
  sourceLocalValues=[],wrapperLoad=dict(instructionVa=wrapper,register='rsi',outputRegister='rdi'),remainingRegister=None,
  readerOffsets={k:offsets[k]for k in keys},advanceCallInstructionVa=site,advanceTargetVa=advance,
  actualReaderArgument='rbx',actualSignedCountArgument=24,independentAdvanceSourceRequired=True,
  completeSourceBitsCaptured=True,preservedCaptureRegistersRequired=['xmm6','xmm7'],
  managedLayoutUsedForWidth=False,typedReadUnmanagedClaimed=False,fieldTransferProved=False,callerFrameProved=False,
  nextInstructionVa=g.at,boolBytesNormalized=False,paddingBytesCopied=True)


def program(regions,entry,*,field_offset):
 need('literal-owned-field-offset',type(field_offset)is int and 16<=field_offset<4096)
 capture=capture_program(regions,entry,dict(currentPtr=80,bufferLength=48,advancedCount=64,consumed=68))
 g=BytesPath(regions,capture['nextInstructionVa']);g.seen.extend(capture['selectedBytes'])
 site=capture['advanceCallInstructionVa'];advance=capture['advanceTargetVa']
 g.take('4885f6');g.branch('0f84',False)
 g.take('488b4610','4885c0');g.branch('0f84',False)
 g.take('0f1170'+field_offset.to_bytes(1,'little').hex()if field_offset<128 else'0f11b0'+field_offset.to_bytes(4,'little').hex())
 prepared=None
 if field_offset==120:prepared=g.at;g.take('488bcb')
 tail=field_offset+16
 g.take('f20f1178'+tail.to_bytes(1,'little').hex()if tail<128 else'f20f11b8'+tail.to_bytes(4,'little').hex())
 return dict(selectedBytes=g.seen,startVa=entry,endVa=g.at,wireBytes=24,
  readerRegister='rbx',wrapperOutputRegister='rdi',wrapperRegister='rsi',originalHolderOffset=16,
  capturedSlices=[dict(offset=0,bytes=16,register='xmm6'),dict(offset=16,bytes=8,register='xmm7')],
  storedSlices=[dict(sourceOffset=0,fieldOffset=field_offset,bytes=16),dict(sourceOffset=16,fieldOffset=field_offset+16,bytes=8)],
  sourceCaptureBeforeAdvance=True,whole24BitsStoredUnchanged=True,advanceInstructionVa=site,advanceTargetVa=advance,
  advanceReaderRegister='rcx',advanceCountRegister='edx',advanceCount=24,
  nextReaderPreparationVa=prepared,nextReaderRegisterValue='rbx'if prepared is not None else None,
  sufficientBufferedBoundsRequired=True,normalAdvancePreservesXmm6Xmm7Required=True,
  parentFramesAdmitted=False,parentFieldAdmitted=False,canonicalWrapperUsed=False,nominalTypeAdmitted=False)


def layout(image,ctx):
 from scripts.game_data.memorypack import scalar_param_native as scalar
 md=image.metadata;sizes={};fields=None
 for name,plan,want in((TYPE,[('position','UnityEngine.Vector3',16),('eulerAngles','UnityEngine.Vector3',28)],40),
  ('UnityEngine.Vector3',[(axis,'float',16+4*i)for i,axis in enumerate(('x','y','z'))],28)):
  td=ctx.index.types[name]
  need('own-plain-nonenum-value:'+name,ctx.is_value_type(name)and not ctx.is_enum(name)
   and ctx.parent(name)=='System.ValueType'and td.generic_container_index<0)
  scalar.ordinary(image,ctx.type_pointer(td.byval_type_index),17,'storyPosRot.layout')
  rows=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
  actual=sorted([(md.string(f.name_index),*ctx.field(name+'::'+md.string(f.name_index))[1:])for f in rows],key=lambda r:r[2])
  need('complete-nominal-instance-fields:'+name,actual==plan)
  for field in rows:scalar.ordinary(image,ctx.type_pointer(field.type_index),17 if name==TYPE else 12,'storyPosRot.field')
  need('owned-size-row:'+name,0<=td.index<image.registration['typeDefinitionsSizesCount'])
  pointer=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
  need('exact-boxed-size:'+name,image.pe.u32_at_va(pointer)==want)
  sizes[name]=dict(boxedBytes=image.pe.u32_at_va(pointer),marshaledNativeBytes=image.pe.u32_at_va(pointer+4))
  if name==TYPE:fields=actual
 return dict(typeName=TYPE,typeDefinition=ctx.index.types[TYPE].index,managedBytes=24,fields=fields,sizeRows=sizes,
  referenceLaneOffsets=[],paddingByteRanges=[],rawFieldOrder=['position','eulerAngles'],
  canonicalWrapperWireUsed=False,canonicalMemberOrderNotSubstituted=True)


def derive(image,pins,*,field_name):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack.wrapper_members import derive_from_image
 from scripts.game_data.memorypack.pointer_param import owned,methods
 from scripts.game_data.memorypack import scalar_param_native as scalar
 from scripts.game_data.memorypack.generated_called_advance_sources import derive as derive_advance
 need('finite-exact-parent-field',field_name in FIELDS)
 _publication_gate(image,pins);ctx=NativeReferenceContext(image);nominal=layout(image,ctx);base=image.pe.image_base
 wrapper,=[w for w in derive_from_image(image).values()if w.wrapped_type==PARENT]
 member,=[m for m in wrapper.members if m.name==field_name]
 need('exact-nominal-parent-member',member.declared_type==TYPE and ctx.field(PARENT+'::'+field_name)[1]==TYPE)
 offset=ctx.field(PARENT+'::'+field_name)[2];need('exact-ordinary-parent',not ctx.is_value_type(PARENT)
  and ctx.field(wrapper.name+'::__instance')==(wrapper.name,PARENT,16))
 method=methods(image,wrapper)['Deserialize'];body=owned(image,image.method_pointer_va(method));selected=[]
 for row in body['rows']:
  if bytes.fromhex(row['bytes'])!=bytes.fromhex('837b3018'):continue
  try:selected.append(program(body['regions'],int(row['va'],16),field_offset=offset))
  except ValueError:continue
 need('one-exact-named-inline-capture',len(selected)==1);capture,=selected
 offsets=scalar.reader_offsets(image,'storyPosRotCapture')
 advance=derive_advance(image,pins,target=capture['advanceTargetVa'],offsets=offsets)
 declared,=[f for f in image.metadata.fields_for(ctx.index.types[PARENT])if image.metadata.string(f.name_index)==field_name]
 field=dict(name=field_name,declaringType=PARENT,typeName=TYPE,offset=offset,
  rawTypeHex=image.pe.bytes_at_va(ctx.type_pointer(declared.type_index),16).hex().upper())
 _publication_gate(image,pins)
 result=json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-posrot-inline-capture',nativeInputs=pins,
  typeName=TYPE,parentType=PARENT,fieldName=field_name,fieldOffset=offset,layout=nominal,
  parentFieldMetadata=field,
  sourceMethod=[method.index,wrapper.name,'Deserialize',body['pointer']-base],sourceWindows=body['windows'],
  sourceRegions=[[a,raw.hex().upper()]for a,raw in body['regions']],sourceProgram=capture,
  advanceSource=advance,readerOffsets=offsets,parentFramesAdmitted=False,parentFieldAdmitted=False,
  canonicalAdapterAdmitted=False,wholeOwnerAdmitted=False)))
 verify(result,pins);return result


def verify(component,pins):
 """Pure full-window, selected macro and independent Advance byte replay."""
 from scripts.game_data.memorypack.leveldata_tracking_raw_sources import _owned_regions
 from scripts.game_data.memorypack.generated_called_advance_sources import advance_program
 need('same-explicit-capture-component',component.get('schema')==SCHEMA
  and component.get('status')=='validated-conditional-posrot-inline-capture'and component.get('nativeInputs')==pins
  and(component.get('typeName'),component.get('parentType'))==(TYPE,PARENT)and component.get('fieldName')in FIELDS
  and all(component.get(k)is False for k in('parentFramesAdmitted','parentFieldAdmitted','canonicalAdapterAdmitted','wholeOwnerAdmitted')))
 nominal=component['layout'];need('independent-exact-nominal-layout',nominal.get('typeName')==TYPE
  and nominal.get('managedBytes')==24 and nominal.get('fields')==[['position','UnityEngine.Vector3',16],['eulerAngles','UnityEngine.Vector3',28]]
  and nominal.get('referenceLaneOffsets')==[]and nominal.get('paddingByteRanges')==[]
  and nominal.get('rawFieldOrder')==['position','eulerAngles']and nominal.get('canonicalWrapperWireUsed')is False)
 field=component.get('parentFieldMetadata',{});raw=bytes.fromhex(field.get('rawTypeHex',''))
 need('same-independently-selected-named-field',(field.get('name'),field.get('declaringType'),field.get('typeName'),field.get('offset'))==
  (component['fieldName'],PARENT,TYPE,component['fieldOffset'])and len(raw)==16 and raw[10:12]==bytes((17,128))
  and int.from_bytes(raw[:8],'little')==nominal['typeDefinition'])
 first=component['sourceRegions'][0][0];base=first-component['sourceWindows'][0]['startRva']
 regions=_owned_regions(component['sourceRegions'],component['sourceWindows'],base=base,label='posrot-parent')
 replay=program(regions,component['sourceProgram']['startVa'],field_offset=component['fieldOffset'])
 normalize=lambda v:json.loads(json.dumps(v))
 need('same-complete-inline-capture-program',normalize(replay)==component['sourceProgram'])
 advance=component['advanceSource'];offsets=component['readerOffsets']
 need('same-independent-owned-Advance24',advance.get('nativeInputs')==pins
  and base+advance['targetRva']==replay['advanceTargetVa']and advance.get('readerOffsets')==offsets
  and advance.get('registeredMethodIdentityClaimed')is False
  and all(advance.get(k)is True for k in('completeAdvanceProgramProved','allFourReaderUpdatesProved',
   'entryRspRestored','allNonvolatilesRestored','zeroCountReturnsWithoutMutation')))
 owned=_owned_regions(advance['sourceRegions'],advance['codeWindows'],base=base,label='posrot-advance')
 checked=[advance_program(owned,replay['advanceTargetVa'],offsets,zero=zero)for zero in(False,True)]
 need('both-complete-Advance-paths',normalize(checked)==advance['programs'])
 return base

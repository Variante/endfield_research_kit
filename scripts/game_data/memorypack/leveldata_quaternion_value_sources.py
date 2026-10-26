"""Exact Quaternion ReadUnmanaged hidden16 source; no reference adapter.

The actual method reads a complete raw16 payload directly. Its nominal closed
MVAR request, layout and full normal source are independent gates; no provider,
formatter selection, object header or null/default wrapper is inferred.
"""
import json
import struct
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='UnityEngine.Quaternion'
LABEL='storyQuaternionValue'


def need(k,c):
 if not c:raise ValueError(LABEL+'.'+k)


def program(regions,entry,offsets,*,path_factory=None):
 need('callable-only-path-factory',path_factory is None or callable(path_factory))
 cur,rem,adv,used=(bytes((offsets[k],)).hex()for k in('currentPtr','bufferLength','advancedCount','consumed'))
 g=(BytesPath if path_factory is None else path_factory)(regions,entry)
 g.take('48895c2408','4889742410','57','4883ec20','837a'+rem+'10','488bda','488bf9');g.branch('0f8c',False)
 g.take('488b43'+cur,'0f1000','0f1107','8b73'+rem,'83c6f0');g.branch('0f88',False)
 g.take('488343'+cur+'10','8343'+adv+'10','8343'+used+'10','8973'+rem,
  '488b5c2430','488bc7','488b742438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,wireBytes=16,managedOutputBytes=16,capturedSourceSlices=[[0,16]],storedOutputSlices=[[0,16]],
  hiddenOutputRegister='rcx',readerRegister='rdx',methodInfoRegister='r8',sameOutputReturnedInRax=True,
  allFourReaderUpdatesProved=True,fullFrameAndNonvolatilesRestored=True,normalReturn=True)


def bind(context,source_target,proof,*,base):
 need('literal-current-identity',type(source_target)is int and type(base)is int and source_target>base
  and type(context.get('typeDefinition'))is int and type(context.get('typeKind'))is int
  and type(proof.get('typeDefinition'))is int and type(proof.get('readerMethodDefinition'))is int
  and type(proof.get('targetRva'))is int and isinstance(context.get('methodSpec'),(tuple,list))and len(context['methodSpec'])==3
  and type(context['methodSpec'][0])is int)
 need('actual-closed-Quaternion-request',context.get('methodOwner')=='MemoryPack.MemoryPackReader'
  and context.get('methodName')=='ReadUnmanaged'and context.get('register')=='r8'
  and context.get('fullTypeName')==TYPE and context.get('typeKind')==17
  and proof.get('schema')=='endfield.story-quaternion-value-source.v1'and proof.get('status')=='validated'
  and proof.get('typeName')==TYPE and proof.get('typeDefinition')==context['typeDefinition']
  and proof.get('readMethod')=='ReadUnmanaged'and proof.get('readerMethodDefinition')==context['methodSpec'][0]
  and proof.get('targetRva')==source_target-base and proof.get('wireBytes')==proof.get('managedBytes')==16
  and type(proof.get('wireBytes'))is int and type(proof.get('managedBytes'))is int
  and proof.get('referenceLaneOffsets')==[]and proof.get('paddingByteRanges')==[]
  and proof.get('resultAbi')=='hidden-local'and proof.get('contextRegister')=='r8'
  and all(proof.get(k)is True for k in('actualSourceProved','allFourReaderUpdatesProved','fullFrameAndNonvolatilesRestored'))
  and proof.get('pointerAliasClaimed')is False)
 return dict(typeName=TYPE,typeDefinition=proof['typeDefinition'],readerMethodDefinition=proof['readerMethodDefinition'],
  targetRva=proof['targetRva'],wireBytes=16,managedBytes=16,resultAbi='hidden-local')


def derive(image,pins,*,context,source_target):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import scalar_param_native as scalar
 from scripts.game_data.memorypack.pointer_param import owned
 _publication_gate(image,pins);base=image.pe.image_base
 need('exact-actual-context',context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('methodName')=='ReadUnmanaged'
  and context.get('fullTypeName')==TYPE and context.get('typeKind')==17 and context.get('register')=='r8')
 usage=derive_typed_usage_context(image,context['instructionRva'],label=LABEL)
 need('fresh-same-request',usage.get('tag')==6 and usage.get('typeName')=='MemoryPack.MemoryPackReader'
  and usage.get('methodName')=='ReadUnmanaged'and usage.get('classArguments')==[]and usage.get('methodArguments')==[TYPE]
  and usage['methodSpec']==context['methodSpec']and usage['instructionHex']==context['instructionHex'])
 ctx=NativeReferenceContext(image);md=image.metadata;td=ctx.index.types[TYPE]
 need('closed-nominal-nonenumeration-value',(ctx.is_value_type(TYPE),ctx.is_enum(TYPE),ctx.parent(TYPE),td.generic_container_index,td.index)==
  (True,False,'System.ValueType',-1,context['typeDefinition']))
 fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
 layout=[(md.string(f.name_index),*ctx.field(TYPE+'::'+md.string(f.name_index))[1:])for f in fields]
 need('complete-four-owned-Single-fields',layout==[(axis,'float',16+4*index)for index,axis in enumerate('xyzw')])
 for field in fields:scalar.ordinary(image,ctx.type_pointer(field.type_index),12,LABEL+'.Single')
 need('bounded-nominal-size-index',0<=td.index<image.registration['typeDefinitionsSizesCount'])
 sizes=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*td.index)
 need('independent-boxed-native-sizes',(image.pe.u32_at_va(sizes),image.pe.u32_at_va(sizes+4))==(32,16))
 argument,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
 raw=image.pe.bytes_at_va(argument.type_pointer_va,16);scalar.ordinary(image,argument.type_pointer_va,17,LABEL+'.closedQuaternion')
 need('same-actual-closed-carrier',raw.hex().upper()==context['argumentRawHex'].upper()and int.from_bytes(raw[:8],'little')==td.index)
 method=md.methods[usage['methodSpec'][0]]
 need('owned-noarg-instance-method',(image.type_name(method.declaring_type),md.string(method.name_index),method.flags&16,method.parameter_count,
  list(md.parameters_for(method)))==('MemoryPack.MemoryPackReader','ReadUnmanaged',0,0,[]))
 section=md.sections['genericContainers'];at=section.offset+16*method.generic_container_index
 need('bounded-method-container',method.generic_container_index>=0 and section.offset<=at<=section.offset+section.size-16)
 container=struct.unpack_from('<iiii',md.buf,at);need('own-single-method-MVAR',container[:3]==(method.index,1,1))
 returned=image.pe.bytes_at_va(ctx.type_pointer(method.return_type),16)
 need('same-owned-return-MVAR',returned[10:12]==b'\x1e\x00'and int.from_bytes(returned[:8],'little')==container[3])
 entry=GenericEntries(image).resolve(method.index,[],[TYPE]);need('same-registered-MethodSpec',entry['methodSpecIndex']==usage['methodSpecIndex'])
 actual=owned(image,source_target);offsets=scalar.reader_offsets(image,LABEL);actual_program=program(actual['regions'],source_target,offsets)
 result=dict(schema='endfield.story-quaternion-value-source.v1',status='validated',nativeInputs=dict(pins),typeName=TYPE,
  typeDefinition=td.index,readMethod='ReadUnmanaged',readerMethodDefinition=method.index,targetRva=source_target-base,
  wireBytes=16,managedBytes=16,resultAbi='hidden-local',hiddenOutputRegister='rcx',readerRegister='rdx',contextRegister='r8',
  referenceLaneOffsets=[],paddingByteRanges=[],actualSourceProved=True,actualEqualsRegisteredPointer=source_target==entry['pointer'],
  pointerAliasClaimed=False,allFourReaderUpdatesProved=True,fullFrameAndNonvolatilesRestored=True,wholeOwnerAdmitted=False,
  proof=dict(typedRequest=usage,registration=entry,nominalLayout=layout,boxedBytes=32,nativeBytes=16,
   methodContainer=container,returnRawHex=returned.hex(),actualWindows=actual['windows'],actualFamily=image.unwind_index.family(source_target-base),actualProgram=actual_program,readerOffsets=offsets),
  evidenceBoundary=dict(exact='Fresh exact ReadUnmanaged<Quaternion> request/formal return MVAR and nominal four-Single layout, complete actual hidden16 MOVUPS source/return/frame and all four Reader updates.',
   conditional='Sufficient contiguous coherent input, disjoint hidden output, nonwrapping counters and normal direct source call. No type-size inference, provider/formatter selection or registered-body alias is used.',
   unresolved=['refill/error paths','enclosing local/setter/full caller frame','runtime meaning','whole owner/physical EOF']))
 bind(context,source_target,result,base=base)
 _publication_gate(image,pins)
 return json.loads(json.dumps(result))

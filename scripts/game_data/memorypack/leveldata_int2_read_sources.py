"""Actual closed ReadUnmanaged<Int2> qword source; inline parents stay separate."""
import json
import struct
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='UnityEngine.Vector2Int'
LABEL='storyInt2Read'


def need(key,value):
 if not value:raise ValueError(LABEL+'.'+key)


def program(regions,entry,offsets):
 need('literal-reader-offsets',set(offsets)=={'currentPtr','bufferLength','advancedCount','consumed'}
  and all(type(v)is int and 0<=v<128 for v in offsets.values())and len(set(offsets.values()))==4)
 cur,rem,adv,used=(bytes([offsets[k]]).hex()for k in('currentPtr','bufferLength','advancedCount','consumed'))
 g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','57','4883ec20','8379'+rem+'08','488bf9');g.branch('0f8c',False)
 g.take('488b5f'+cur,'488b1b','8b77'+rem,'83c6f8');g.branch('0f88',False)
 g.take('488347'+cur+'08','8347'+adv+'08','8347'+used+'08','8977'+rem,
  '488b742438','488bc3','488b5c2430','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,wireBytes=8,managedOutputBytes=8,capturedSourceSlices=[[0,8]],
  resultAbi='register-value',resultRegister='rax',readerRegister='rcx',contextRegister='rdx',contextUnusedOnSelectedPath=True,
  rawInt32Axes=['x','y'],allFourReaderUpdatesProved=True,fullFrameAndNonvolatilesRestored=True,normalReturn=True,
  frame=dict(entryRspDelta=-40,callShadow=[0,32],savedEntryHomes=dict(rbx=[8,16],rsi=[16,24]),pushedNonvolatiles=['rdi']))


def bind(context,source_target,proof,*,base):
 need('literal-current-source',type(source_target)is int and type(base)is int and source_target>base
  and type(context.get('typeDefinition'))is int and isinstance(context.get('methodSpec'),(list,tuple))
  and len(context['methodSpec'])==3 and type(context['methodSpec'][0])is int
  and all(type(proof.get(k))is int for k in('typeDefinition','readerMethodDefinition','targetRva','wireBytes','managedBytes')))
 need('closed-actual-Int2-source',context.get('methodOwner')=='MemoryPack.MemoryPackReader'
  and context.get('methodName')=='ReadUnmanaged'and context.get('register')=='rdx'
  and context.get('fullTypeName')==TYPE and type(context.get('typeKind'))is int and context['typeKind']==17
  and proof.get('schema')=='endfield.story-int2-read-source.v1'and proof.get('status')=='validated'
  and proof.get('typeName')==TYPE and proof.get('typeDefinition')==context['typeDefinition']
  and proof.get('readerMethodDefinition')==context['methodSpec'][0]and proof.get('targetRva')==source_target-base
  and proof.get('readMethod')=='ReadUnmanaged'and proof.get('wireBytes')==proof.get('managedBytes')==8
  and proof.get('resultAbi')=='register-value'and proof.get('resultRegister')=='rax'
  and proof.get('readerRegister')=='rcx'and proof.get('contextRegister')=='rdx'
  and proof.get('rawInt32Axes')==['x','y']and proof.get('referenceLaneOffsets')==[]and proof.get('paddingByteRanges')==[]
  and all(proof.get(k)is True for k in('actualSourceProved','allFourReaderUpdatesProved','fullFrameAndNonvolatilesRestored'))
  and proof.get('pointerAliasClaimed')is False)
 return dict(typeName=TYPE,typeDefinition=proof['typeDefinition'],readerMethodDefinition=proof['readerMethodDefinition'],
  targetRva=proof['targetRva'],wireBytes=8,managedBytes=8,resultAbi='register-value',resultRegister='rax',rawInt32Axes=['x','y'])


def derive(image,pins,*,context,source_target):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import scalar_param_native as scalar
 from scripts.game_data.memorypack.leveldata_integer_vector_layout import derive_layout
 from scripts.game_data.memorypack.pointer_param import owned
 _publication_gate(image,pins);base=image.pe.image_base
 need('actual-rdx-Int2-context',context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('methodName')=='ReadUnmanaged'
  and context.get('fullTypeName')==TYPE and context.get('typeKind')==17 and context.get('register')=='rdx')
 need('actual-literal-target',type(source_target)is int and source_target>base)
 usage=derive_typed_usage_context(image,context['instructionRva'],label=LABEL)
 need('fresh-same-request',usage.get('tag')==6 and usage.get('typeName')=='MemoryPack.MemoryPackReader'
  and usage.get('methodName')=='ReadUnmanaged'and usage.get('classArguments')==[]and usage.get('methodArguments')==[TYPE]
  and list(usage['methodSpec'])==list(context['methodSpec'])and usage['instructionHex']==context['instructionHex']
  and usage['instructionHex'].startswith('488B15'))
 ctx=NativeReferenceContext(image);md=image.metadata;td=ctx.index.types[TYPE]
 argument,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
 raw=image.pe.bytes_at_va(argument.type_pointer_va,16);scalar.ordinary(image,argument.type_pointer_va,17,LABEL+'.argument')
 need('same-owned-ordinary-carrier',int.from_bytes(raw[:8],'little')==td.index and td.index==context['typeDefinition']
  and raw.hex().upper()==context['argumentRawHex'].upper())
 layout=derive_layout(image,type_pointer=argument.type_pointer_va)
 need('independent-Int2-layout',layout['typeName']==TYPE and layout['managedBytes']==8
  and layout['referenceLaneOffsets']==[]and layout['paddingByteRanges']==[])
 method=md.methods[usage['methodSpec'][0]]
 need('owned-noarg-instance-method',(image.type_name(method.declaring_type),md.string(method.name_index),method.flags&16,
  method.parameter_count,list(md.parameters_for(method)))==('MemoryPack.MemoryPackReader','ReadUnmanaged',0,0,[]))
 section=md.sections['genericContainers'];at=section.offset+16*method.generic_container_index
 need('bounded-method-container',method.generic_container_index>=0 and section.offset<=at<=section.offset+section.size-16)
 container=struct.unpack_from('<iiii',md.buf,at);need('own-single-method-MVAR',container[:3]==(method.index,1,1))
 returned=image.pe.bytes_at_va(ctx.type_pointer(method.return_type),16)
 need('owned-return-MVAR',returned[10:12]==b'\x1e\x00'and int.from_bytes(returned[:8],'little')==container[3])
 registration=GenericEntries(image).resolve(method.index,[],[TYPE])
 need('same-registered-closed-MethodSpec',registration['methodSpecIndex']==usage['methodSpecIndex'])
 actual=owned(image,source_target);offsets=scalar.reader_offsets(image,LABEL);checked=program(actual['regions'],source_target,offsets)
 result=dict(schema='endfield.story-int2-read-source.v1',status='validated',nativeInputs=dict(pins),typeName=TYPE,typeDefinition=td.index,
  readMethod='ReadUnmanaged',readerMethodDefinition=method.index,targetRva=source_target-base,wireBytes=8,managedBytes=8,
  resultAbi='register-value',resultRegister='rax',readerRegister='rcx',contextRegister='rdx',rawInt32Axes=['x','y'],
  referenceLaneOffsets=[],paddingByteRanges=[],actualSourceProved=True,allFourReaderUpdatesProved=True,
  fullFrameAndNonvolatilesRestored=True,actualEqualsRegisteredPointer=source_target==registration['pointer'],
  pointerAliasClaimed=False,wholeOwnerAdmitted=False,proof=dict(typedRequest=usage,registration=registration,nominalLayout=layout,
   methodContainer=container,returnRawHex=returned.hex(),actualWindows=actual['windows'],
   actualSourceRegions=[[start-base,raw.hex()]for start,raw in actual['regions']],actualProgram=checked,readerOffsets=offsets),
  evidenceBoundary=dict(exact='Fresh closed ordinary Int2 ReadUnmanaged RDX MethodSpec, owned formal MVAR and independent two-Int32 layout, complete actual qword source, unchanged RAX return/full frame and all four Reader updates.',
   conditional='Sufficient stable contiguous buffered input, nonwrapping counters and disjoint Reader/frame storage. Exact incoming context is independently bound by each enclosing actual call. No registered source pointer alias is used.',
   unresolved=['inline Int2 variants, refill/error paths','parent source/local/named setter/full frame','runtime meaning','collection or whole owner physical EOF/publication']))
 bind(context,source_target,result,base=base);_publication_gate(image,pins)
 return json.loads(json.dumps(result))

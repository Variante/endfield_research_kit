"""Exact typed ReadUnmanaged<Vector3> hidden12 source, independent of layout."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='generatedVector3Source'
TYPE='UnityEngine.Vector3'

def need(key,condition,detail=None):
 if not condition:raise ValueError(LABEL+'.'+key+':'+str(detail)[:700])

def program(regions,entry,offsets):
 g=BytesPath(regions,entry);cur,rem,adv,used=(bytes((offsets[k],)).hex()for k in('currentPtr','bufferLength','advancedCount','consumed'))
 g.take('48895c2408','4889742410','57','4883ec20','837a'+rem+'0c','488bda','488bf9');g.branch('0f8c',False)
 g.take('488b43'+cur,'f20f1000','8b4008','f20f1107','894708','8b73'+rem,'83c6f4');g.branch('0f88',False)
 g.take('488343'+cur+'0c','8343'+adv+'0c','8343'+used+'0c','8973'+rem,
  '488b5c2430','488bc7','488b742438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,wireBytes=12,managedOutputBytes=12,hiddenOutputRegister='rcx',readerRegister='rdx',methodInfoRegister='r8',
  capturedSourceSlices=[[0,8],[8,4]],storedOutputSlices=[[0,8],[8,4]],sameOutputReturnedInRax=True,
  allFourReaderUpdatesProved=True,fullFrameAndNonvolatilesRestored=True,normalReturn=True)

def derive(image,pins,*,context,source_target):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
 from scripts.game_data.memorypack.vector_layout import vector_context
 _publication_gate(image,pins);base=image.pe.image_base
 need('exact-actual-nominal-context',context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('methodName')=='ReadUnmanaged'and context.get('fullTypeName')==TYPE and context.get('typeKind')==17 and context.get('register')=='r8')
 usage=derive_typed_usage_context(image,context['instructionRva'],label=LABEL)
 need('actual-context-spec-and-instruction',usage['methodSpec']==context['methodSpec']and usage['instructionHex']==context['instructionHex'])
 selected=NativeReferenceContext(image);need('current-nominal-definition',selected.index.types[TYPE].index==context['typeDefinition'])
 argument,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
 need('exact-closed-argument-bytes',argument.raw_type_record_hex.upper()==context['argumentRawHex'].upper())
 entry=vector_context(image,usage,3,label=LABEL);actual=pointer.owned(image,source_target)
 offsets=scalar.reader_offsets(image,LABEL);actual_program=program(actual['regions'],source_target,offsets)
 _publication_gate(image,pins)
 return dict(status='validated',nativeInputs=dict(pins),typeName=TYPE,readMethod='ReadUnmanaged',readerMethodDefinition=usage['methodSpec'][0],
  targetRva=source_target-base,wireBytes=12,managedBytes=12,resultAbi='hidden-local',hiddenOutputRegister='rcx',readerRegister='rdx',contextRegister='r8',
  actualSourceProved=True,actualEqualsRegisteredPointer=source_target==entry['pointer'],pointerAliasClaimed=False,
  proof=dict(typedRequest=usage,registration=entry,actualFamily=image.unwind_index.family(source_target-base),actualWindows=actual['windows'],actualProgram=actual_program,readerOffsets=offsets),
  evidenceBoundary=dict(exact='Fresh actual typed ReadUnmanaged<Vector3> request/formal MVAR/value ABI and independent x/y/z Single layout plus complete actual hidden12 split8+4 source, all four Reader updates and full normal frame.',
   conditional='Sufficient coherent contiguous input, disjoint output and input, normal selected direct source invocation. Registered entry provenance is recorded; a distinct canonical body is not substituted for the actual call.',
   unresolved=['enclosing local/setter/full caller frame','refill and malformed paths','runtime meaning','whole owner/EOF']))

def forwarder_program(regions,entry):
 g=BytesPath(regions,entry);g.take('4053','4883ec20');site=g.at;cell=g.relative('4c8b05')
 g.take('488bd9');call=g.at;target=g.relative('e8');g.take('488bc3','4883c420','5b','c3')
 return dict(selectedBytes=g.seen,contextInstructionVa=site,contextCellVa=cell,sourceCallVa=call,nestedTargetVa=target,
  sameIncomingReaderRdx=True,sameIncomingOutputRcx=True,sameOutputReturnedInRax=True,fullFrameAndNonvolatilesRestored=True)

def derive_forwarder(image,pins,*,source_target):
 """Own a real closed helper that supplies its internal Vector3 MethodInfo."""
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.memorypack import pointer_param as pointer,generated_action_sources as actions
 _publication_gate(image,pins);base=image.pe.image_base;body=pointer.owned(image,source_target)
 program=forwarder_program(body['regions'],source_target);site=program['contextInstructionVa'];target=program['nestedTargetVa']
 contexts,skipped=actions._contexts(image,body['rows']);context,=[c for c in contexts if c['instructionRva']==site-base]
 need('sole-closed-source-context',len(contexts)==1)
 nested=derive(image,pins,context=context,source_target=target)
 _publication_gate(image,pins)
 return dict(status='validated',nativeInputs=dict(pins),typeName=TYPE,readMethod='ReadUnmanaged',readerMethodDefinition=nested['readerMethodDefinition'],
  targetRva=source_target-base,wireBytes=12,managedBytes=12,resultAbi='hidden-local',hiddenOutputRegister='rcx',readerRegister='rdx',contextRegister=None,
  actualSourceProved=True,contextMode='owned-closed-forwarder',pointerAliasClaimed=False,
  proof=dict(forwarderProgram=program,
   typedRequest=nested['proof']['typedRequest'],actualFamily=image.unwind_index.family(source_target-base),actualWindows=body['windows'],
   actualProgram=nested['proof']['actualProgram'],nestedSource=nested,skippedRuntimeCells=skipped),
  evidenceBoundary=dict(exact='Fresh owned closed helper supplies its exact internal ReadUnmanaged<Vector3> MethodInfo and forwards unchanged Reader/output to the independently proved hidden12 source, then returns the same output with full frame restored.',
   conditional='Coherent initialized internal MethodInfo and the nested sufficient-buffer/disjoint-storage source conditions.',unresolved=['enclosing local/setter/full caller frame','refill','runtime meaning','whole owner/EOF']))

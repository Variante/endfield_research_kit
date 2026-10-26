"""Own Single and enum dispatch paths for the gait dictionary's actual calls.

Raw DWORD movement proves bits only. Single gets its own closed formatter
registration and formal VAR/Reader ABI; nominal enum callback selection is a
separate input and cannot be supplied by an Int32 name or equal width.
"""
import hashlib,json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='skillGaitDictionaryCallbacks'


def need(key,condition):
 if not condition:raise ValueError(LABEL+'.'+key)


def replay_single(proof,pins):
 """Pure replay of both independent current Single byte programs/windows."""
 need('current-own-Single-capability',proof.get('nativeInputs')==pins and proof.get('schema')=='endfield.skill-gait-Single-callback.v1'
  and proof.get('status')=='validated-conditional'and proof.get('typeName')=='float'and proof.get('wireBytes')==4
  and proof.get('numericConversion')is False and proof.get('referenceLaneOffsets')==proof.get('paddingByteRanges')==[]
  and proof.get('actualCallbackSelectionObserved')is False)
 p=proof['proof'];reg=p['registration'];callback=reg['pointer'];base=callback-proof['callbackTargetRva']
 need('same-own-Single-registration',type(base)is int and base>=0 and reg['methodDefinitionIndices']==[proof['callbackMethodDefinition']]
  and len(reg['classInstantiation']['arguments'])==1
  and bytes.fromhex(reg['classInstantiation']['arguments'][0]['raw_type_record_hex'])[10:12]==bytes((12,128))
  and bytes.fromhex(p['readerParameterRawHex'])[10:12]==bytes((17,32))
  and bytes.fromhex(p['outputParameterRawHex'])[10:12]==bytes((19,32))
  and int.from_bytes(bytes.fromhex(p['outputParameterRawHex'])[:8],'little')==p['ownedOutputParameter']['parameterIndex']
  and p['ownedOutputParameter']['ordinal']==0)
 regions={}
 for name in('callback','dispatch'):
  windows=p[name+'Windows'];raw_regions=p[name+'Regions']
  need('complete-'+name+'-regions',bool(windows)and len(windows)==len(raw_regions)
   and len({at for at,h in raw_regions})==len(raw_regions))
  for at,h in raw_regions:
   raw=bytes.fromhex(h);matches=[w for w in windows if w.get('startRva')==at and w.get('endRva',0)-at==len(raw)]
   need('exact-'+name+'-owned-window',len(matches)==1 and hashlib.sha256(raw).hexdigest().upper()==matches[0].get('sha256'))
  regions[name]=[(base+at,bytes.fromhex(h))for at,h in raw_regions]
 from scripts.game_data.memorypack.float_list_sources import callback_program
 actual=callback_program(regions['callback'],callback,p['readerOffsets'])
 need('exact-whole-Single-callback-byte-replay',json.loads(json.dumps(actual))==p['callbackProgram'])
 chunks=p['dispatchProgram']['selectedBytes'];calls=[at for at,h in chunks if h=='e8']
 need('one-actual-selected-preparation-call',len(calls)==1);at=calls[0];delta=bytes.fromhex(dict(chunks).get(at+1,''))
 need('actual-direct-preparation-target',len(delta)==4);prepare=at+5+int.from_bytes(delta,'little',signed=True)
 dispatch=dispatch_program(regions['dispatch'],base+proof['sourceTargetRva'],p['readerOffsets'],prepare=prepare,callback=callback,kind='single')
 need('exact-whole-actual-Single-dispatch-replay',json.loads(json.dumps(dispatch))==p['dispatchProgram']
  and dispatch['selectedPath']=='matched-inline-raw4')
 return dict(typeName='float',wireBytes=4,sourceTargetRva=proof['sourceTargetRva'],callbackTargetRva=proof['callbackTargetRva'],
  nominalCallbackSelectionRequired=True,rawBitsPreserved=True)


def dispatch_program(regions,entry,offsets,*,prepare,callback,kind):
 need('finite-dispatch-domain',kind in('enum','single')and type(callback)is int and callback>0)
 o={k:bytes((offsets[k],)).hex()for k in('currentPtr','bufferLength','advancedCount','consumed')}
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','488b0a',
  '498bf1'if kind=='enum'else'498bf9','498bd8','488bfa'if kind=='enum'else'488bf2');g.call(prepare)
 g.take('488b07'if kind=='enum'else'488b06','4c8b9090010000','4c8b8898010000');first=g.relative('488d05')
 g.take('4c3bd0');same_first=callback==first
 g.branch('75'if kind=='enum'else'0f85',not same_first,1 if kind=='enum'else 4)
 second=None;indirect=False
 if not same_first:
  if kind=='enum':
   second=g.relative('488d05');g.take('4c3bd0');same_second=callback==second;g.branch('74',same_second,1)
   if not same_second:g.jump('e9');indirect=True
  else:indirect=True
 if indirect:
  g.take('4c8bc6'if kind=='enum'else'4c8bc7','488bd3','488bcf'if kind=='enum'else'488bce','41ffd2','90');g.jump('e9')
 else:
  g.take('837b'+o['bufferLength']+'04');g.branch('0f8c',False)
  g.take('488b43'+o['currentPtr'],'8b00','8906'if kind=='enum'else'8907','8b7b'+o['bufferLength'],'83c7fc');g.branch('0f88',False)
  for code,key in(('488343','currentPtr'),('8343','advancedCount'),('8343','consumed')):g.take(code+o[key]+'04')
  g.take('897b'+o['bufferLength'])
 g.take('488b5c2430','488b742438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,dispatchKind=kind,selectedCallback=callback,firstComparedCallback=first,secondComparedCallback=second,
  selectedPath='indirect-slot-five'if indirect else'matched-inline-raw4',slot=5,callbackOffset=400,methodInfoOffset=408,
  incomingRcxUnused=True,readerRegister='incoming R8',outputRegister='incoming R9',rawBytes=None if indirect else 4,
  nominalCallbackGrammarRequired=True,sameReaderAndOutput=True,entryRspRestored=True,allNonvolatilesRestored=True,
  condition='Ready receiver with the independently selected nominal slot-five callback and MethodInfo; normal preparation/callback ABI, disjoint buffered input/Reader/output and nonwrapping counters. Indirect source framing comes only from its separately proved exact callback.')


def derive_single(image,pins,*,call_target):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.context import type_parameter_owner
 from scripts.game_data.il2cpp.formatter_composition import _vtable
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar,float_list_sources
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
 td=ctx.index.types['MemoryPack.Formatters.UnmanagedFormatter`1'];methods=[m for m in md.methods_for(td)if md.string(m.name_index)=='Deserialize']
 need('own-unmanaged-formatter-Deserialize',len(methods)==1);method=methods[0];parameters=list(md.parameters_for(method))
 need('owned-slot-five-instance-void-ABI',not method.flags&16 and ctx.type_name(method.return_type)=='void'and method.parameter_count==len(parameters)==2)
 _vtable(image,td.index,5,method.index,LABEL)
 reader=image.pe.bytes_at_va(ctx.type_pointer(parameters[0].type_index),16);out=image.pe.bytes_at_va(ctx.type_pointer(parameters[1].type_index),16)
 need('own-reader-and-byref-VAR-output',ctx.type_name(parameters[0].type_index)=='MemoryPack.MemoryPackReader'
  and reader[10:12]==bytes((17,32))and out[10:12]==bytes((19,32)))
 owner=type_parameter_owner(md.buf,int.from_bytes(out[:8],'little'),[t.generic_container_index for t in md.types],source=LABEL)
 need('own-class-VAR-zero',(owner['typeIndex'],owner['ordinal'])==(td.index,0))
 registration=GenericEntries(image).resolve(method.index,['float'],[]);argument,=registration['classInstantiation']['arguments']
 raw=bytes.fromhex(argument['raw_type_record_hex']);need('exact-closed-Single-carrier',raw[10:12]==bytes((12,128)))
 source=pointer.owned(image,registration['pointer']);offsets=scalar.reader_offsets(image,LABEL)
 program=float_list_sources.callback_program(source['regions'],source['pointer'],offsets)
 actual=pointer.owned(image,call_target);calls=[control_transfer(r)['target']for r in actual['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8']
 need('actual-prepare-call',bool(calls));dispatch=dispatch_program(actual['regions'],call_target,offsets,prepare=calls[0],callback=source['pointer'],kind='single')
 need('actual-Single-inline-callback-equality',dispatch['selectedPath']=='matched-inline-raw4')
 result=dict(schema='endfield.skill-gait-Single-callback.v1',status='validated-conditional',nativeInputs=dict(pins),typeName='float',wireBytes=4,
  sourceTargetRva=call_target-base,callbackTargetRva=source['pointer']-base,callbackMethodDefinition=method.index,
  actualCallbackSelectionObserved=False,referenceLaneOffsets=[],paddingByteRanges=[],numericConversion=False,
  proof=dict(registration=registration,readerParameterRawHex=reader.hex().upper(),outputParameterRawHex=out.hex().upper(),
   ownedOutputParameter=owner,callbackWindows=source['windows'],callbackRegions=[[a-base,h.hex()]for a,h in source['regions']],
   callbackProgram=program,dispatchWindows=actual['windows'],dispatchRegions=[[a-base,h.hex()]for a,h in actual['regions']],
   dispatchProgram=dispatch,readerOffsets=offsets),
  evidenceBoundary=dict(exact='Own closed Single generic registration, formal class VAR/Reader byref and slot-five identity; complete actual raw4 callback and actual compared dispatcher, unchanged output bits and all Reader/frame effects.',
   conditional='Actual provider receiver/MethodInfo selects this exact nominal callback, normal preparation ABI and disjoint sufficient buffered input. Runtime provider state remains unobserved.'))
 _publication_gate(image,pins);return json.loads(json.dumps(result))

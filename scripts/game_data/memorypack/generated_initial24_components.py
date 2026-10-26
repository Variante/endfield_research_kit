"""Exact inline CameraInitial24 source/Advance/closed-property compiler join."""
import json
from scripts.game_data.memorypack import generated_initial24_capture_sources as capture
from scripts.game_data.memorypack.generated_called_advance_components import verify_advance
from scripts.game_data.memorypack.generated_inline_record_components import _owned_setter_trace

LABEL='generatedInitial24Components'


def need(key,condition):
 if not condition:raise ValueError(LABEL+'.'+key)


def norm(value):return json.loads(json.dumps(value))


def _compile_member(owner,scope,read,pins):
 index=read['memberIndex'];need('same-complete-current-event',type(index)is int and 0<=index<len(scope.get('events',[]))
  and owner.get('nativeInputs')==scope.get('nativeInputs')==pins and owner.get('sourceScope')==scope
  and owner.get('orderedSourceReads',[])[index]==scope['events'][index]==read
  and read.get('mode')=='buffered-called-advance-initial24'and read.get('context')is None
  and'resultAbi'not in read and'sourceTargetRva'not in read)
 setter=owner['setters'][index];layout=capture.validate_nominal(read,setter)
 value=scope.get('valueTypeSources',{}).get(str(index),{});macro=read.get('inlineSourceProgram',{});advance=read.get('inlineAdvanceSource',{})
 need('own-independent-layout-and-capture',value.get('typeName')==capture.TYPE and value.get('layout')==layout
  and value.get('actualSourceProved')is True and value.get('wireBytes')==24 and value.get('resultAbi')=='inline-bits-to-owned-field'
  and value.get('advanceSource')==advance and macro.get('typedReadUnmanagedClaimed')is False
  and macro.get('managedLayoutUsedForWidth')is False and macro.get('boolBytesNormalized')is False and macro.get('paddingBytesCopied')is True)
 base=macro['guardInstructionVa']-read['instruction'][0];selected=scope.get('selectedProgram',[])
 need('literal-current-guard-and-registers',type(base)is int and base>=0 and bool(selected)
  and(scope['headerProof']['readerRegister'],scope['headerProof']['outputRegister'])==('rdi','rbx')
  and bytes.fromhex(read['instruction'][1])==bytes((131,127,macro['readerOffsets']['bufferLength'],24)))
 regions=[(base+a,bytes.fromhex(h))for a,h in selected]
 replay=capture.program(regions,macro['guardInstructionVa'],macro['readerOffsets'],reader='rdi',output='rbx',
  path_factory=lambda regions,entry:_owned_setter_trace(regions,entry,scope['codeWindows'],base))
 need('complete-literal-XMM6-XMM7-capture-replay',norm(replay)==macro and macro.get('preservedCaptureRegistersRequired')==['xmm6','xmm7'])
 verify_advance(advance,macro,pins,base)
 rich=scope.get('richProgram',{});flows=[x for x in rich.get('sources',[])if x.get('memberIndex')==index]
 stores=[x for x in rich.get('fieldStores',[])if x.get('memberIndex')==index];flow=value.get('sourceProgram',{})
 need('complete-source-to-actual-property-effects',rich.get('completeSelectedNormalProgram')is True and rich.get('selectedProgram')==selected
  and len(flows)==1 and flows[0].get('instruction')==read['instruction']and flows[0].get('mode')==read['mode']
  and flows[0].get('program')==macro and flows[0].get('actualAdvanceSource')==advance
  and[(x.get('sourceOffset'),x.get('storedBytes'))for x in stores]==[(0,16),(16,8)]
  and all(x['instruction']in selected for x in stores)and all(flow.get(k)==v for k,v in macro.items())
  and flow.get('sourceBytes')==macro['selectedBytes']and flow.get('storedBytes')==24
  and flow.get('fullValueBitsStoredUnchanged')is True and flow.get('fieldStoreProgram')==stores
  and setter==scope['richSetters'][index])
 from scripts.game_data.memorypack.generated_closed_camera_property_components import verify as verify_property
 getter=verify_property(owner,setter,read,layout,base)
 from scripts.game_data.memorypack.generated_member_sources import _displacement
 from scripts.game_data.memorypack.generated_vector_member_sources import nonnull
 g=_owned_setter_trace(regions,macro['advanceCallInstructionVa']+5,scope['codeWindows'],base)
 g.take('4885f6');nonnull(g);g.take('33d2','488bce');g.call(base+getter['method'][3]);g.take('4885c0');nonnull(g)
 g.take(_displacement('0f11b0',setter['fieldOffset']),'488bcf',_displacement('f20f11b8',setter['fieldOffset']+16))
 need('actual-XMM6-XMM7-property-store-bytes',[stores[0]['instruction'],stores[1]['instruction']]==
  [[a-base,h.upper()]for a,h in(g.seen[-3],g.seen[-1])])
 paths=owner.get('programs',[])
 need('all-four-complete-parent-frames',len(paths)==4 and{(p.get('existing'),p.get('wrapperNull'))for p in paths}==
  {(False,False),(True,False),(False,True),(True,True)}and all(p.get('frame',{}).get('entryRspRestored')is True
   and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths))
 for p in paths:
  if not p['wrapperNull']:need('both-whole-preserved-XMM-homes',all(name in p['frame'].get('restoredVectorHomes',{})for name in('xmm6','xmm7')))
 return 'camera-initial-raw24'


def compile_member(owner,scope,read,pins):
 try:return _compile_member(owner,scope,read,pins)
 except(ValueError,KeyError,IndexError,TypeError)as error:
  from scripts.game_data.memorypack.corpus_gate import CensusGateError
  failure=CensusGateError(LABEL+'.field',source=owner.get('wrapperName','unknown')+'::Deserialize',
   expected='Exact inline24 XMM6/XMM7 source, actual Advance, own padded nominal/closed property and full getter/setter/caller frames.',
   actual=dict(fieldName=read.get('fieldName'),memberIndex=read.get('memberIndex'),failedGate=str(error)[:800]))
  failure.diagnostic.update(validator=LABEL,nativeInputs=pins,sourceInstruction=read.get('instruction'))
  failure.args=(json.dumps(failure.diagnostic,ensure_ascii=False),);raise failure from error

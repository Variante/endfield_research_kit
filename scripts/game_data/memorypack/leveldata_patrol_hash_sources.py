"""Actual warm managed UTF16 path-hash fallback with pair-loop induction.

The accelerated implementation is not selected. Runtime readiness and the
actual acceleration-selector Bool remain explicit conditions. A finite stable
UTF16 prefix through its first zero is required; embedded zeros are respected,
and no character normalization beyond the literal ASCII A..Z fold is inferred.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.story-patrol-path-hash-source.v1'
MASK=(1<<60)-1


def need(check,condition):
 if not condition:raise ValueError('storyPatrolHash.'+check)


def program(regions,entry,*,first_zero=False,second_zero=False):
 need('literal-loop-exit-selection',type(first_zero)is bool and type(second_zero)is bool and not(first_zero and second_zero))
 g=BytesPath(regions,entry);g.take('4056','4883ec60');ready=g.relative('803d')+1;g.take('00','488bf1');g.branch('0f85',True)
 usage=g.at;class_cell=g.relative('488b0d');g.take('83b9e000000000');g.branch('75',True,1);g.take('33c9')
 selection_site=g.at;selection=g.relative('e8');g.take('84c0');g.branch('74',True,1)
 fallback=g.at;g.take('0fbf0e','41b805150000','458bc8','8bd1','49baffffffffffffff0f','85c9');g.branch('74',first_zero,1)
 loop=None;back=None
 if not first_zero:
  g.take('0f1f4000','660f1f840000000000');loop=g.at
  g.take('8d41bf','83c120','83f819','0f47ca','496bc021','4863d1','4923d2','4c8bc2','0fbf5602','4c33c0','85d2')
  g.branch('74',second_zero,1)
  if not second_zero:
   g.take('8d42bf','8d4a20','83f819','0f47ca','4883c604','496bc121','4863d1','0fbf0e','4923d2',
    '4c8bca','8bd1','4c33c8','85c9');back=g.at;target=g.relative('75',1)
   need('exact-pair-loop-backedge',target==loop)
 g.take('4969c1658b585d','4903c0','4923c2','4883c460','5e','c3')
 return dict(selectedBytes=g.seen,entry=entry,metadataReadyCell=ready,classUsageInstructionVa=usage,classCell=class_cell,
  accelerationSelectorInstructionVa=selection_site,accelerationSelectorTargetVa=selection,accelerationSelectorArgumentEcx=0,
  selectedAccelerationBoolMustBeFalse=True,fallbackEntryVa=fallback,firstCodeUnitZero=first_zero,
  secondCodeUnitZero=second_zero,pairLoopEntryVa=loop,pairLoopBackedgeVa=back,
  initialAccumulatorValues=[5381,5381],accumulatorMultiply=33,finalSecondAccumulatorMultiply=1566083941,
  codeUnitLoadBytes=2,codeUnitLoadSigned=True,finalMask=MASK,normalReturn=True,entryRspRestored=True,
  nonvolatilesRestored=['rsi'],liveAccelerationOrCpuSelectionObserved=False)


def fold_proof():
 for code in range(1<<16):
  signed=code if code<32768 else code-65536
  unsigned_delta=(signed-65)&0xffffffff
  selected=(signed+32)&0xffffffff if unsigned_delta<=25 else signed&0xffffffff
  extended=selected if selected<1<<31 else selected-(1<<32)
  expected=code+32 if 65<=code<=90 else code
  expected_signed=expected if expected<32768 else expected-65536
  need('all-UTF16-signed-source-folds',extended==expected_signed)
 return dict(codeUnitPatternsChecked=1<<16,onlyAsciiUppercaseAThroughZFolded=True,
  signed16ExtendedToSigned64BeforeMask=True,mask=MASK,otherCodeUnitsUnchangedBeforeSignExtension=True)


def loop_induction():
 return dict(incomingData='nonnull stable UTF16 pointer with a finite first zero',
  h0Initial=5381,h1Initial=5381,recurrence='h := (h*33 mod2^64) XOR (signExtend64(asciiFold(codeUnit)) AND (2^60-1))',
  h0Processes='even-indexed nonzero UTF16 code units in order',h1Processes='odd-indexed nonzero UTF16 code units in order',
  sourceOffsetsPerIteration=[0,2],sourceStepBytes=4,
  earlyExits=['first/even code unit zero before first update','second/odd code unit zero after first update'],
  termination='Each backedge consumes two nonzero code units and advances4; finite first zero terminates after floor(length/2) backedges.',
  result='(h0 + h1*1566083941 mod2^64) AND (2^60-1)',
  everyPreTerminatorCodeUnitProcessedExactlyOnce=True,zeroTerminatorNotFoldedOrAccumulated=True,
  outputBitsPreserved=True,inputWrites=0,extraPayloadReadsBeyondFirstTerminator=False,
  finiteStableReadablePrefixAndNonwrappingPointerRequired=True)


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import leveldata_patrol_path_sources as path_owner,pointer_param as pointer
 _publication_gate(image,pins);base=image.pe.image_base;path=path_owner.derive(image,pins);child=path['proof']['hashSource']
 body=pointer.owned(image,base+child['entryRva']);programs=[program(body['regions'],body['pointer'],first_zero=a,second_zero=b)
  for a,b in((True,False),(False,True),(False,False))]
 need('same-actual-fallback-and-selector',len({p['fallbackEntryVa']for p in programs})==1 and
  len({p['accelerationSelectorTargetVa']for p in programs})==1)
 usage=derive_typed_usage_context(image,programs[0]['classUsageInstructionVa']-base,label='storyPatrolHash.actualClass')
 selector=pointer.owned(image,programs[0]['accelerationSelectorTargetVa']);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-managed-path-hash-source',nativeInputs=pins,
  proof=dict(pathSource=path,sourceWindows=body['windows'],sourceRegions=[[a,h.hex()]for a,h in body['regions']],programs=programs,
   actualClassUsage=usage,codeUnitFold=fold_proof(),loopInduction=loop_induction(),accelerationSelector=dict(entryRva=selector['pointer']-base,
    sourceWindows=selector['windows'],sourceRegions=[[a,h.hex()]for a,h in selector['regions']],rows=selector['rows'],effectsProved=False)),
  selectedManagedUtf16HashSourceAndLoopProved=True,selectedNormalPathCacheAndFrameSourceProved=True,
  liveAccelerationOrCpuSelectionObserved=False,runtimeInvocationObserved=False,playbackProved=False,wholeConversionProved=False,
  evidenceBoundary=dict(exact='Actual warm nonaccelerated fallback bytes, all UTF16 code-unit fold cases, paired modulo64 hash recurrence and finite first-zero loop induction/full return frame, joined to actual path/hash cache caller.',
   conditional=__doc__,unresolved=['acceleration selector actual live Bool and accelerated implementation','actual StartsWith prefix and concat/handle/loader helper effects','live path/asset/cache identity and activation']))))

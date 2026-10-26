"""Actual Patrol large-array allocation/preparation selected pointer paths.

These byte programs select a no-work preparation epoch, the large-allocation
route and a preparation result which skips collection. The backend result is
returned unchanged, including its null alternative; the successful branch
adds the requested bytes to the actual owned global counter. Result
preparation advances its actual counter and returns incoming RCX only on the
independently stated arithmetic-inequality branch. Backend allocation/zeroing,
collector paths and live epoch/flags/cache state remain independent.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.story-patrol-allocation-source.v1'


def need(check,condition):
 if not condition:raise ValueError('storyPatrolAllocation.'+check)


def preparation_program(regions,entry):
 g=BytesPath(regions,entry);g.take('4883ec28');epoch=g.relative('488b05');compared=g.relative('483905');g.branch('74',True,1)
 g.take('4883c428','c3')
 return dict(selectedBytes=g.seen,entry=entry,loadedEpochCell=epoch,comparedEpochCell=compared,
  selectedEpochQwordsMustMatch=True,receiverAndAllocationArgumentRegistersUnchanged=True,
  memoryWrites=0,opaqueCalls=0,entryRspRestored=True,normalReturn=True,nonselectedPreparationEffectsProved=False)


def allocation_program(regions,entry,*,nonnull=True):
 need('literal-backend-result-selection',type(nonnull)is bool)
 g=BytesPath(regions,entry);g.take('89542410','53','55','56','57','4154','4155','4156','4157','4881ec98000000',
  '0f29b42480000000','488bd9','4c63fa','4881f900080000');g.branch('0f87',True)
 g.take('48c7c0ffffffff','418bd7','483bd8','480f43c8','4533c0');site=g.at;backend=g.relative('e8')
 g.take('488bc8','4885c0');g.branch('74',not nonnull,1);counter=None
 if nonnull:counter=g.relative('48011d')
 g.take('488bc1','0f28b42480000000','4881c498000000','415f','415e','415d','415c','5f','5e','5d','5b','c3')
 return dict(selectedBytes=g.seen,entry=entry,nonnull=nonnull,largeRequestUnsignedGreaterThan2048Required=True,
  requestedBytesMustBeBelow2Pow64Minus1=True,backendCallVa=site,backendTargetVa=backend,
  backendArguments=dict(rcx='unchanged incoming requested byte count',edx='unchanged incoming low32 flags',r8d=0),
  backendReturnedPointerUnchanged=True,allocationBytesCounterCell=counter,
  successfulCounterOperation='actual QWORD := old QWORD + incoming requested bytes modulo 2^64'if nonnull else None,
  backendAllocationOrZeroingEffectsProved=False,entryRspRestored=True,nonvolatilesRestored=['rbx','rbp','rsi','rdi','r12','r13','r14','r15','xmm6'],normalReturn=True)


def result_program(regions,entry):
 g=BytesPath(regions,entry);g.take('4883ec28','488d442438','4889442438','b8');multiplier=int.from_bytes(g.read(4),'little')
 g.take('4c8b4c2438');counter=g.relative('448b05');g.take('41ffc0','41f7e0')
 need('same-counter-load-and-publication',g.relative('448905')==counter);g.take('c1ea02','6bc2');factor=int.from_bytes(g.read(1),'little',signed=True)
 g.take('443bc0');g.branch('75',True,1);g.take('488bc1','4883c428','c3')
 return dict(selectedBytes=g.seen,entry=entry,counterCell=counter,counterBytes=4,counterIncrementModulo2Pow32=1,
  multiplyUnsignedHigh32By=multiplier,highProductShiftRight=2,multiplyLow32By=factor,
  selectedIncrementedCounterAndDerivedDwordMustDiffer=True,incomingPointerInRcxReturnedUnchanged=True,
  collectorCalled=False,opaqueCalls=0,entryRspRestored=True,normalReturn=True,nonselectedCollectionEffectsProved=False)


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.memorypack import leveldata_patrol_positive_growth_sources as growth_owner,pointer_param as pointer
 _publication_gate(image,pins);base=image.pe.image_base;growth=growth_owner.derive(image,pins)
 large=growth['proof']['positiveGrowthPrograms'][1];targets=large['actualAllocationCalls'];sources={};programs={}
 for role,target in targets.items():
  body=pointer.owned(image,target);sources[role]=dict(sourceWindows=body['windows'],sourceRegions=[[a,h.hex().upper()]for a,h in body['regions']])
  if role=='prepare-allocation':programs[role]=preparation_program(body['regions'],body['pointer'])
  elif role=='allocate':programs[role]=[allocation_program(body['regions'],body['pointer'],nonnull=r)for r in(False,True)]
  elif role=='prepare-result':programs[role]=result_program(body['regions'],body['pointer'])
 need('exact-three-actual-large-allocation-source-calls',set(programs)=={'prepare-allocation','allocate','prepare-result'})
 backend=programs['allocate'][1]['backendTargetVa'];need('same-backend-null-and-nonnull-source',backend==programs['allocate'][0]['backendTargetVa'])
 body=pointer.owned(image,backend);sources['backend']=dict(entryRva=backend-base,sourceWindows=body['windows'],
  sourceRegions=[[a,h.hex().upper()]for a,h in body['regions']],rows=body['rows'],bodyEffectsProved=False)
 transitions=growth['proof']['capacityInduction']['growthTransitions'];large_sizes=[s['arrayBytes']for s in transitions if s['allocationPath']=='large']
 need('all-finite-large-request-sizes-fit-actual-path',large_sizes and all(2048<n<2**31 for n in large_sizes))
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-large-allocation-pointer-sources',nativeInputs=pins,
  proof=dict(positiveGrowthSource=growth,sources=sources,programs=programs,finiteLargeRequestBytes=large_sizes),
  selectedLargeAllocationArgumentPointerAndFrameSourcesProved=True,selectedNoCollectionPreparationReturnsSamePointer=True,
  backendAllocationOrZeroingEffectsProved=False,actualHeapEpochFlagsOrCounterStateObserved=False,
  wholeConversionProved=False,runtimeInvocationObserved=False,playbackProved=False,
  evidenceBoundary=dict(exact='Actual growth-selected helper calls, complete chosen no-work preparation and large allocation/return frames, successful global counter operation and same-pointer no-collection result preparation.',
   conditional=__doc__,unresolved=['backend allocation/zeroing source effects','nonselected collector/preparation paths and compatible heap state','full consumer effects and runtime activation']))))

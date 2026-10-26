"""Bounded warm first-success heap caller selected by Patrol large growth.

The selected initialized heap skips initialization/collection and its first
allocation attempt succeeds. The actual allocation primitive must provide a
valid disjoint page-rounded block. No cold, retry, collector, OS availability or
live class-selector state is inferred from this normal source program.
"""
import hashlib
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.story-patrol-warm-heap-source.v1'


def need(check,condition):
 if not condition:raise ValueError('storyPatrolHeap.'+check)


def program(regions,entry,*,classification='none',multiple_pages=True,new_high_water=False):
 need('finite-literal-source-selections',classification in('range','primary','secondary','none')and
  type(multiple_pages)is bool and type(new_high_water)is bool and(multiple_pages or not new_high_water))
 g=BytesPath(regions,entry);g.take('4055','56','57','4154','4155','4156','4883ec38','33ff','458be8','897c2470','448bf2',
  '4883f9f0');g.branch('73',False,1);g.take('488d710f','4883e6f0','4881fe00f0ffff');g.branch('73',False,1)
 g.take('488daeff0f0000');g.at=g.relative('eb',1);g.take('48c1ed0c');initialized=g.relative('393d')
 g.take('4889ac2488000000');g.branch('75',True,1);collection=g.relative('393d');g.branch('74',True,1)
 g.take('48895c2478','458be5','4c897c2430','4881fe00f0ffff');g.branch('0f83',False)
 g.take('4c8dbeff0f0000','49c1ef0c','498bc7','48c1e00c','4885c0');g.branch('0f88',False)
 g.take('418d46fd','83f802');g.branch('76',classification=='range',1);primary=None;secondary=None
 if classification!='range':
  primary=g.relative('8b05');g.take('85c0');g.branch('7e',classification!='primary',1)
  if classification=='primary':g.take('443bf0');g.branch('74',True,1)
  else:
   secondary=g.relative('8b05');g.take('85c0');g.branch('7e',classification=='none',1)
   if classification=='secondary':g.take('443bf0');g.branch('75',False,1)
 if classification!='none':g.take('4183cc40')
 g.take('bf3c000000','4983ff20');g.branch('76',True,1)
 g.take('458bcf','c744242000000000','458bc4','418bd6','488bce');call=g.at;allocate=g.relative('e8')
 g.take('4c8bd0','4885c0');g.branch('0f85',True);g.take('4d85d2');g.branch('75',True,1)
 g.take('4883fd01');g.branch('76',not multiple_pages,1);current=None;maximum=None
 if multiple_pages:
  current=g.relative('488b05');g.take('48c1e50c','4803c5');maximum=g.relative('483b05')
  need('same-current-page-counter-publication',g.relative('488905')==current);g.branch('76',not new_high_water,1)
  if new_high_water:need('same-high-water-publication',g.relative('488905')==maximum)
 g.take('498bc2','4c8b7c2430','488b5c2478','4883c438','415e','415d','415c','5f','5e','5d','c3')
 return dict(selectedBytes=g.seen,entry=entry,classification=classification,multiplePages=multiple_pages,newHighWater=new_high_water,
  heapInitializedCell=initialized,selectedInitializedDwordNonzeroRequired=True,
  collectionGateCell=collection,selectedCollectionGateDwordZeroRequired=True,
  primaryClassSelectorCell=primary,secondaryClassSelectorCell=secondary,
  flagConditions={'range':'unsigned(flags-3)<=2','primary':'unsigned(flags-3)>2; primary selector signed-positive and equals flags',
   'secondary':'unsigned(flags-3)>2; primary selector nonpositive; secondary selector signed-positive and equals flags',
   'none':'unsigned(flags-3)>2; both class selectors nonpositive'}[classification],
  incomingAllocationOptionsRequired=0,allocatorInstructionVa=call,allocatorTargetVa=allocate,
  allocatorArguments=dict(rcx='incoming request rounded up to16',edx='incoming low32 flags',
   r8d=64 if classification!='none'else 0,r9d='page count ceil(aligned request/4096)',stackArgument5=0),
  selectedFirstAllocationResultNonzeroRequired=True,returnedPointerUnchanged=True,
  currentPageBytesCounterCell=current,highWaterCounterCell=maximum,
  selectedCurrentCounterAddsPageRoundedExtent=multiple_pages,
  currentCounterOperation='old QWORD +page-rounded bytes modulo2^64'if multiple_pages else None,
  selectedHighWaterPublished=new_high_water,
  entryRspRestored=True,nonvolatilesRestored=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],normalReturn=True,
  allocationPrimitiveEffectsProved=False,coldRetryOrCollectorPathsProved=False)


def domain(requests):
 need('finite-request-set',isinstance(requests,list)and 0<len(requests)<=64)
 out=[]
 for n in requests:
  need('bounded-request',type(n)is int and 2048<n<2**31)
  aligned=(n+15)&-16;pages=(aligned+4095)>>12;extent=pages<<12
  need('literal-selected-rounding-domain',1<=pages<=32 and aligned<2**64-4096 and n<=aligned<=extent<n+4096)
  out.append(dict(requestBytes=n,alignedBytes=aligned,pageCount=pages,allocatorSizeClass=pages,
   requiredWritableBytes=extent,multiplePages=pages>1))
 return dict(requests=out,allOverflowAndSmallPageClassBranchesProved=True,
  pageRoundingMatchesBackendFill=True,successfulDisjointWritableAllocationRequired=True,allocationSuccessObserved=False)


def validate(source,pins):
 need('exact-owned-schema-and-source-status',isinstance(source,dict)and source.get('schema')==SCHEMA and
  source.get('status')=='validated-conditional-warm-first-success-heap-source'and source.get('nativeInputs')==pins)
 need('selected-source-only-boundary',source.get('selectedWarmAllocationArgumentsPointerCountersAndFrameProved')is True and
  source.get('conditionalSelectedRoundedZeroFillSourceProved')is True and
  all(source.get(k)is False for k in('actualHeapAllocationOrCapacityProved','coldRetryOrCollectorPathsProved',
   'runtimeInvocationObserved','playbackProved','wholeConversionProved')))
 proof=source['proof'];programs=proof['programs'];need('twelve-selected-programs',len(programs)==12)
 regions=[(a,bytes.fromhex(h))for a,h in proof['sourceRegions']]
 base=programs[0]['entry']-proof['entryRva']
 need('complete-own-window-regions',len(regions)==len(proof['sourceWindows'])and all(
  w['startRva']==a-base and w['endRva']==a-base+len(raw)and w['sha256']==hashlib.sha256(raw).hexdigest().upper()
  for(a,raw),w in zip(regions,proof['sourceWindows'])))
 expected=[program(regions,base+proof['entryRva'],classification=k,multiple_pages=m,new_high_water=h)
  for k in('range','primary','secondary','none')for m,h in((False,False),(True,False),(True,True))]
 need('complete-selected-program-replay',json.loads(json.dumps(expected))==programs)
 backend=proof['backendSource'];need('same-selected-backend-native-inputs-and-schema',backend.get('nativeInputs')==pins and
  backend.get('schema')=='endfield.story-patrol-allocation-backend-source.v1'and
  backend.get('conditionalSelectedRoundedZeroFillSourceProved')is True and backend.get('actualHeapAllocationOrCapacityProved')is False)
 request=backend['proof']['allocationSource']['proof']['finiteLargeRequestBytes'];bounded=domain(request)
 need('same-own-request-domain',proof['ownRequestDomain']==bounded)
 need('same-backend-child-and-actual-first-allocation-primitive',backend['proof']['allocationChild']['entryRva']==proof['entryRva']and
  all(p['allocatorTargetVa']-base==proof['allocationPrimitive']['entryRva']for p in programs))
 fill=backend['proof']['fullFillInstructionControl'];fp=fill['proof']['program']
 need('independent-complete-current-fill-source',fill.get('schema')=='endfield.byte-fill-source.v1'and fill.get('nativeInputs')==pins and
  fill.get('maxBytes')==max(r['requiredWritableBytes']for r in bounded['requests'])and
  fp.get('completeOwnedFillAndRepProgramsChecked')is True and fp.get('typedCallerDomainImported')is False and
  fp.get('allocationSuccessOrValidCapacityProved')is False)
 return dict(entryRva=proof['entryRva'],allocationPrimitiveRva=proof['allocationPrimitive']['entryRva'],
  maxRoundedBytes=fill['maxBytes'],sourceProgramsReplayed=True,actualHeapAllocationOrCapacityProved=False)


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.memorypack import leveldata_patrol_backend_sources as backend_owner,pointer_param as pointer
 _publication_gate(image,pins);base=image.pe.image_base;backend=backend_owner.derive(image,pins)
 child=backend['proof']['allocationChild'];body=pointer.owned(image,base+child['entryRva'])
 need('own-caller-allocation-options-are-zero',all(p['incomingAllocationOptionsPreservedThroughChildCall']is True
  for p in backend['proof']['programs'])and all(p['backendArguments']['r8d']==0
   for p in backend['proof']['allocationSource']['proof']['programs']['allocate']))
 cases=[program(body['regions'],body['pointer'],classification=k,multiple_pages=m,new_high_water=h)
  for k in('range','primary','secondary','none')for m,h in((False,False),(True,False),(True,True))]
 need('same-own-first-allocation-source',len({p['allocatorTargetVa']for p in cases})==1)
 bounded=domain(backend['proof']['allocationSource']['proof']['finiteLargeRequestBytes'])
 need('same-page-rounded-fill-and-allocator-extents',[r['requiredWritableBytes']for r in bounded['requests']]==
  [r['zeroedBytes']for r in backend['proof']['ownRoundedRequestDomain']['requests']])
 target=pointer.owned(image,cases[0]['allocatorTargetVa']);_publication_gate(image,pins)
 result=json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-warm-first-success-heap-source',nativeInputs=pins,
  proof=dict(backendSource=backend,entryRva=body['pointer']-base,sourceWindows=body['windows'],sourceRegions=[[a,h.hex()]for a,h in body['regions']],
   programs=cases,ownRequestDomain=bounded,allocationPrimitive=dict(entryRva=target['pointer']-base,
    sourceWindows=target['windows'],sourceRegions=[[a,h.hex()]for a,h in target['regions']],rows=target['rows'],effectsProved=False)),
  selectedWarmAllocationArgumentsPointerCountersAndFrameProved=True,conditionalSelectedRoundedZeroFillSourceProved=True,
  actualHeapAllocationOrCapacityProved=False,coldRetryOrCollectorPathsProved=False,
  runtimeInvocationObserved=False,playbackProved=False,wholeConversionProved=False,
  evidenceBoundary=dict(exact='Actual warm first-success allocator argument/frame/unchanged-pointer paths, own finite byte/page rounding, actual allocation primitive E8 and selected current/high-water counter stores, joined to independent complete current fill source.',
   conditional=__doc__,unresolved=['actual successful allocation capacity and heap state','cold/retry/collector and other class-selector paths','full consumer effects and runtime activation']))))
 validate(result,pins);return result

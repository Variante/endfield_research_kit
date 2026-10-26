"""Selected Patrol large allocation backend and page-rounded zero fill source.

The backend's actual allocation child must return a valid disjoint block with
the page-rounded writable extent. The selected force/class-zero flags remain
runtime conditions. Complete fill instruction/control/table/value/geometry
algorithms are reused independently of the earlier typed caller's byte-count
domain; this owner proves its own finite page-rounded extent from actual
Patrol growth requests. No allocation success or live heap state is observed.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.story-patrol-allocation-backend-source.v1'


def need(check,condition):
 if not condition:raise ValueError('storyPatrolBackend.'+check)


def program(regions,entry,*,nonnull,force_zero=False,class_zero=False):
 need('literal-result-and-zero-selections',all(type(v)is bool for v in(nonnull,force_zero,class_zero)))
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','4863fa','488bf1','8bd7')
 allocate_site=g.at;allocate=g.relative('e8');g.take('488bd8','4885c0');g.branch('74',not nonnull,1)
 force=None;table=None;fill=None
 if nonnull:
  force=g.relative('833d')+1;g.take('00');g.branch('75',force_zero,1)
  if not force_zero:
   g.take('488bc7');table=g.relative('488d0d');g.take('48c1e005','833c0800');g.branch('74',not class_zero,1)
  if force_zero or class_zero:
   g.take('4c8d86ff0f0000','33d2','4981e000f0ffff','488bcb');at=g.at;target=g.relative('e8')
   fill=dict(instructionVa=at,targetVa=target,destination='same allocated reference in RBX',fillByte=0,
    requestedCount='(incoming requested bytes +4095) & -4096')
  g.take('488bc3')
 g.take('488b5c2430','488b742438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,entry=entry,nonnull=nonnull,forceZero=force_zero,classZero=class_zero,
  allocatorInstructionVa=allocate_site,allocatorTargetVa=allocate,allocatorArguments=dict(rcx='unchanged incoming byte count',edx='unchanged incoming low32 flags',r8d='unchanged incoming allocation options'),
  incomingAllocationOptionsPreservedThroughChildCall=True,
  zeroForceCell=force,zeroClassTableBase=table,zeroClassTableStride=32,zeroClassIndex='sign-extended incoming flags',fill=fill,
  sameAllocationPointerReturned=nonnull,nullAllocationReturnsZero=not nonnull,normalReturn=True,entryRspRestored=True,
  nonvolatilesRestored=['rbx','rsi','rdi'],allocatorChildEffectsProved=False,zeroClassTableIndexValidityRequired=nonnull and not force_zero)


def extent_proof(requests):
 need('nonempty-finite-own-request-domain',isinstance(requests,list)and 0<len(requests)<=64
  and all(type(n)is int and 2048<n<2**31 for n in requests))
 sizes=[]
 for n in requests:
  rounded=(n+4095)&-4096
  need('own-request-rounded-without-overflow',n<=rounded<n+4096 and rounded%4096==0 and rounded<2**31)
  sizes.append(dict(requestBytes=n,zeroedBytes=rounded,requiredWritableCapacity=rounded))
 return dict(pageBytes=4096,requests=sizes,maximumFillBytes=max(x['zeroedBytes']for x in sizes),
  everyRequestedByteCoveredByRoundedZeroRange=True,actualAllocatedWritableCapacityProved=False)


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.memorypack import leveldata_patrol_allocation_sources as allocation,pointer_param as pointer
 from scripts.game_data.il2cpp import byte_fill_sources
 _publication_gate(image,pins);base=image.pe.image_base;parent=allocation.derive(image,pins)
 backend=parent['proof']['sources']['backend'];body=pointer.owned(image,base+backend['entryRva'])
 selected=[program(body['regions'],body['pointer'],nonnull=False),program(body['regions'],body['pointer'],nonnull=True),
  program(body['regions'],body['pointer'],nonnull=True,force_zero=True),program(body['regions'],body['pointer'],nonnull=True,class_zero=True)]
 need('same-source-owned-allocation-child',len({p['allocatorTargetVa']for p in selected})==1)
 filled=[p['fill']for p in selected if p['fill']is not None];need('same-source-owned-byte-fill',len(filled)==2 and filled[0]['targetVa']==filled[1]['targetVa'])
 extent=extent_proof(parent['proof']['finiteLargeRequestBytes'])
 fill_source=byte_fill_sources.derive(image,pins,entry=filled[0]['targetVa'],max_bytes=extent['maximumFillBytes'])
 checked=fill_source['proof']['program']
 need('whole-fill-program-covers-normal-store-values-and-pointer',checked['completeOwnedFillAndRepProgramsChecked']is True
  and checked['normalReturnEqualsIncomingDestinationProved']is True
  and checked['allRequestedBytesEqualLowIncomingValueByteConditionallyProved']is True)
 child=pointer.owned(image,selected[0]['allocatorTargetVa'])
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-backend-and-rounded-zero-source',nativeInputs=pins,
  proof=dict(allocationSource=parent,backendWindows=body['windows'],backendRegions=[[a,h.hex().upper()]for a,h in body['regions']],programs=selected,
   fullFillInstructionControl=fill_source,independentFillByteReplication=checked['byteReplication'],independentFillRangeGeometry=checked['vectorGeometry'],
   ownRoundedRequestDomain=extent,
   allocationChild=dict(entryRva=child['pointer']-base,windows=child['windows'],regions=[[a,h.hex().upper()]for a,h in child['regions']],rows=child['rows'],effectsProved=False)),
  selectedBackendArgumentPointerAndFrameSourcesProved=True,conditionalSelectedRoundedZeroFillSourceProved=True,
  priorTypedCallerDomainImported=False,actualHeapAllocationOrCapacityProved=False,allocationChildEffectsProved=False,
  liveZeroFlagOrCpuModeSelectionObserved=False,wholeConversionProved=False,runtimeInvocationObserved=False,playbackProved=False,
  evidenceBoundary=dict(exact='Actual allocation child arguments, both pointer-return alternatives, force/class-zero selected predicates, page-rounded zero-fill arguments, independently checked complete fill bytes/control/tables/value/geometry and exact finite Patrol request extents.',
   conditional=__doc__,unresolved=['allocation child source and actual returned writable capacity','live zero/class/CPU/heap flags and nonselected collector/preparation effects','full consumer effects/runtime activation']))))

"""Actual resource binary hash-bucket search, independent of managed dictionaries.

The selected default source uses a valid stable native index: positive bucket
count, complete bucket/record storage and at most4096 records in the selected
bucket. Actual loaded index contents/identity are not observed. Raw QWORD keys
are compared unchanged; no serialization, class-name alias or asset existence
claim follows from these source effects.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.story-patrol-resource-bucket-search-source.v1'


def need(check,condition):
 if not condition:raise ValueError('storyPatrolResourceLookup.'+check)


def quotient_proof(divisor,multiplier,shift):
 need('literal-unsigned-division-constants',all(type(v)is int for v in(divisor,multiplier,shift))and
  0<divisor<1<<28 and 0<=multiplier<1<<64 and 0<=shift<63)
 power=1<<(65+shift);reciprocal=(1<<64)+multiplier;error=divisor*reciprocal-power;maximum=(1<<64)-1
 need('reciprocal-is-ceiling-with-exact-all-u64-error-bound',0<=error<divisor and maximum*error<power)
 return dict(divisor=divisor,multiplier=multiplier,shift=shift,reciprocal=reciprocal,power=power,error=error,
  maximumDividend=maximum,errorBound=maximum*error,
  halfDifferenceThenAddCannotOverflow=True,quotientTimesDivisorDoesNotOverflow=True,
  identity='floor((high64(n*m)+(n-high64(n*m))//2)/2^s) = floor(n*(2^64+m)/2^(65+s)) = floor(n/d)',
  proof='For n=q*d+r, 0<=r<d, q is a lower bound; r*power+n*error < (d-1)*power+power = d*power prevents an extra quotient unit.',
  exactForEveryUnsigned64Dividend=True,remainderInHalfOpenDivisorRange=True)


def program(regions,entry,*,division='magic',failures=0,found=True):
 need('bounded-selected-search-witness',division in('magic','div')and type(failures)is int and 0<=failures<=3 and type(found)is bool)
 g=BytesPath(regions,entry);g.take('4053','4883ec50');root=g.relative('488b05');g.take('488bda','4c8b5078','4d85d2')
 g.branch('0f85',False);g.take('4883792800');g.branch('0f84',False)
 g.take('4889742468','48896c2460','48897c2470','4c896c2440','4c89742438','488b7128','4d85d2');g.branch('0f85',False)
 g.take('488b7610','4885f6');g.branch('0f84',False);g.take('48634e40');context_usage=g.at;context=g.relative('4c8b2d')
 g.take('4881f9');divisor=int.from_bytes(g.read(4),'little',signed=True);g.branch('0f85',division=='div')
 multiplier=None;shift=None
 if division=='magic':
  g.take('48b8');multiplier=int.from_bytes(g.read(8),'little');g.take('48f7e3','488bc3','482bc2','48d1e8','4803c2','488bd3','48c1e8')
  shift=int.from_bytes(g.read(1),'little');g.take('4869c0');need('same-magic-remainder-divisor',int.from_bytes(g.read(4),'little',signed=True)==divisor)
  g.take('482bd0')
 else:
  g.take('33d2','488bc3','48f7f1');g.at=g.relative('e9')
 g.take('8d04d500000000','4863f8','48037e50','0f1f440000','bd00000000','448bf5');g.branch('74',False,1)
 g.take('4c89642448','4c897c2430');loop=g.at;calls=[];probes=[]
 for i in range(failures+1):
  begin=len(g.seen);g.take('443b7704');miss=i==failures and not found;g.branch('7d',miss,1)
  if miss:break
  g.take('498b4d20','4c8b7e48','4c6327');site=g.at;target=g.relative('e8');calls.append(dict(instructionVa=site,targetVa=target))
  g.take('488b88c0000000','488b4930','4883793800');g.branch('74',False,1)
  g.take('498d042c','4a391c38');g.branch('75',i<failures,1)
  if i<failures:
   g.take('41ffc6','4883c518');back=g.relative('eb',1);need('same-forward-probe-loop',back==loop);g.at=back
   probes.append(g.seen[begin:])
  else:g.take('b001')
 if not found:g.take('32c0');g.at=g.relative('eb',1)
 g.take('4c8b642448','4c8b7c2430','4c8b6c2440','488b7c2470','488b6c2460','4c8b742438','488b742468','4883c450','5b','c3')
 return dict(selectedBytes=g.seen,entry=entry,division=division,failedRecords=failures,found=found,
  replacementRootCell=root,selectedReplacementReceiverAt120RequiredNull=True,indexOwnerFieldOffset=40,indexFieldOffset=16,
  bucketCountOffset=64,bucketAddressBaseOffset=80,bucketStride=8,bucketRecordStartOffset=0,bucketRecordCountOffset=4,
  recordAddressBaseOffset=72,recordStride=24,keyBytes=8,keyOffset=0,keysComparedBitwiseUnchanged=True,
  contextUsageInstructionVa=context_usage,contextCell=context,metadataCalls=calls,failedProbeBodies=probes,
  pairLoopEntryVa=loop,divisor=divisor,multiplier=multiplier,shift=shift,
  bucketCountPositiveBelow2Pow28Required=True,selectedBucketCountEqualsLiteral=division=='magic',
  resultAl=found,entryRspRestored=True,nonvolatilesRestored=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],normalReturn=True,
  actualIndexContentsOrIdentityObserved=False)


def induction(programs,count_limit=4096):
 need('finite-normal-record-domain',type(count_limit)is int and count_limit==4096)
 bodies=[body for p in programs for body in p['failedProbeBodies']]
 need('one-byte-identical-forward-failed-probe-arm',bodies and all(body==bodies[0]for body in bodies))
 return dict(countLimit=count_limit,countRegister='r14d',initialCount=0,step=1,recordOffsetRegister='rbp',
  initialRecordOffset=0,recordByteStep=24,keyBytes=8,
  invariant='At the loop entry, R14D=k and RBP=24*k, with unchanged input hash RBX and stable index/bucket. The signed count guard precedes each record read. A mismatch increments k/offset exactly once; a match returns true. Thus any valid bucket of0..4096 records returns on its first exact QWORD match or false at count, without counter overflow.',
  firstExactMatchOrBoundedMissProved=True,metadataNormalReadyNoninterferingCallsRequired=True,
  validStableBucketRecordExtentsAndNonwrappingAddressesRequired=True,loadedIndexContentsObserved=False)


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import leveldata_patrol_resource_sources as resource_owner,pointer_param as pointer
 from scripts.game_data.il2cpp import ready_context_sources
 _publication_gate(image,pins);base=image.pe.image_base;resource=resource_owner.derive(image,pins);child=resource['proof']['children']['request-backend']
 body=pointer.owned(image,base+child['entryRva']);programs=[program(body['regions'],body['pointer'],division=d,failures=n,found=f)
  for d in('magic','div')for n in range(4)for f in(False,True)]
 p=next(p for p in programs if p['division']=='magic');arithmetic=quotient_proof(p['divisor'],p['multiplier'],p['shift'])
 usage=derive_typed_usage_context(image,p['contextUsageInstructionVa']-base,label='storyPatrolResourceLookup.actualContext')
 targets={c['targetVa']for p in programs for c in p['metadataCalls']};need('same-one-actual-metadata-helper',len(targets)==1)
 target=next(iter(targets));metadata=ready_context_sources.derive(image,pins,entry=target)
 ready_context_sources.validate(metadata,pins);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-resource-bucket-search-source',nativeInputs=pins,
  proof=dict(resourceSource=resource,sourceWindows=body['windows'],sourceRegions=[[a,h.hex()]for a,h in body['regions']],programs=programs,
   actualContextUsage=usage,quotientArithmetic=arithmetic,recordInduction=induction(programs),metadataHelper=metadata),
  selectedResourceHashBucketSearchAndResultProved=True,loadedIndexContentsOrIdentityObserved=False,
  runtimeInvocationObserved=False,playbackProved=False,wholeConversionProved=False,
  evidenceBoundary=dict(exact='Actual unsigned quotient/remainder source, exact all-u64 magic proof and hardware DIV alternative, native8-byte bucket/24-byte record source, bounded forward QWORD search/all hit/miss returns/fullframe.',
   conditional=__doc__,unresolved=['metadata ready-flag predicate/actual context identity and cold effects','actual valid loaded index/backend identity and contents','other resource creation/Get/retention effects and live activation']))))

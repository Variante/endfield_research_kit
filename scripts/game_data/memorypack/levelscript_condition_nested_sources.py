"""Exact initialized nested GameCondition union programs, without children.

The ordinary static record reader is absent on these independently abstract
wrappers. Their actual instance formatters select another nominal union child.
Only null incoming wrapper output and the explicitly proved warm source paths
are available here. Concrete Param grammars and recursive framing remain owned
by their enclosing finite composition.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='storyNestedConditionSource'


def need(key,condition):
 if not condition:raise ValueError(LABEL+'.'+key)


def posthook_program(regions,entry,*,base_slot,cache_slot,cast,barrier,cached=False,base_null=False,
 predicate=None,disabled_flag=None,predicate_matches=True):
 """Own the typed-cache refresh while preserving the inherited base reference."""
 need('literal-posthook-path-and-disjoint-reference-fields',type(cached)is bool and type(base_null)is bool
  and all(type(n)is int and n>0 for n in(entry,cast,barrier))
  and type(base_slot)is int and type(cache_slot)is int and 16<=base_slot<128
  and 16<=cache_slot<128 and abs(base_slot-cache_slot)>=8)
 b=bytes((base_slot,)).hex();c=bytes((cache_slot,)).hex();g=BytesPath(regions,entry)
 if _peek(g,5)==bytes.fromhex('48895c2410'):
  return large_posthook_program(regions,entry,base_slot=base_slot,cache_slot=cache_slot,
   predicate=predicate,disabled_flag=disabled_flag,cached=cached,base_null=base_null,
   predicate_matches=predicate_matches)
 g.take('48895c2408','57','4883ec20','33db','488bf9');flag=g.relative('381d')
 _branch(g,True);g.take('48395f'+c);_branch(g,cached)
 usage=None;cell=None
 if not cached:
  g.take('48395f'+b);_branch(g,base_null)
  if not base_null:
   g.take('488b5f'+b);usage=g.at;cell=g.relative('488b15');g.take('488bcb');g.call(cast)
   g.take('488947'+c,'488bcb');second=g.relative('488b15');g.call(cast)
   need('same-owned-refresh-cast-context',cell==second)
   g.take('488d4f'+c);g.call(barrier)
 g.take('488b5c2430','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,initializedFlagCellVa=flag,baseReferenceSlot=base_slot,
  cacheReferenceSlot=cache_slot,cachedReferenceInitiallyPresent=cached,
  inheritedBaseReferenceInitiallyNull=base_null if not cached else None,
  castUsageInstructionVa=usage,castTypeCellVa=cell,castTargetVa=cast if usage is not None else None,
  cacheReferenceWriteBytes=8 if usage is not None else 0,inheritedBaseReferenceWrites=0,
  inheritedBaseReferencePreserved=True,wholeReceiverReferencePreserved=True,
  castPredicateOutcomeProved=False,cacheCoherenceObserved=False,
  normalReturn=True,entryRspRestored=True,restoredNonvolatiles=['rbx','rdi'],
  condition='Initialized metadata, stable disjoint owned base/cache reference fields, normally returning compatible casts and independently disabled unchanged collector. The typed cache may receive the unchanged base reference or null; no write targets the inherited base-reference field.')


def large_posthook_program(regions,entry,*,base_slot,cache_slot,predicate,disabled_flag,
 cached=False,base_null=False,predicate_matches=True):
 """Own the direct predicate/cache store and its exact disabled collector edge."""
 need('actual-direct-predicate-and-collector',type(predicate)is int and predicate>0
  and type(disabled_flag)is int and disabled_flag>0 and type(predicate_matches)is bool)
 b=bytes((base_slot,)).hex();c=bytes((cache_slot,)).hex();g=BytesPath(regions,entry)
 g.take('48895c2410','48896c2418','4889742420','57','4883ec40','33ff')
 image_base=g.relative('488d2d');flag=g.relative('40383d');g.take('488bf1');_branch(g,True)
 g.take('48397e'+c);_branch(g,cached);usage=None;cell=None
 if not cached:
  g.take('48397e'+b);_branch(g,base_null)
  if not base_null:
   g.take('488b5e'+b);usage=g.at;cell=g.relative('488b15');g.take('488b0b');g.call(predicate)
   g.take('84c0');_branch(g,not predicate_matches)
   if predicate_matches:g.take('488bfb')
   g.take('48897e'+c);second=g.relative('488b15');g.take('488b0b');g.call(predicate)
   need('same-owned-direct-predicate-type',cell==second)
   need('actual-disabled-hook-collector',g.relative('833d')+1==disabled_flag);g.take('00');_branch(g,True)
 g.take('488b5c2458','488b6c2460','488b742468','4883c440','5f','c3')
 return dict(selectedBytes=g.seen,profile='direct-predicate-inline-collector',imageBase=image_base,
  initializedFlagCellVa=flag,baseReferenceSlot=base_slot,cacheReferenceSlot=cache_slot,
  cachedReferenceInitiallyPresent=cached,inheritedBaseReferenceInitiallyNull=base_null if not cached else None,
  castUsageInstructionVa=usage,castTypeCellVa=cell,castTargetVa=None,
  predicateTargetVa=predicate if usage is not None else None,
  predicateMatchWitness=predicate_matches if usage is not None else None,
  cacheReferenceWriteBytes=8 if usage is not None else 0,inheritedBaseReferenceWrites=0,
  inheritedBaseReferencePreserved=True,wholeReceiverReferencePreserved=True,
  castPredicateOutcomeProved=False,cacheCoherenceObserved=False,disabledCollectorFlagVa=disabled_flag,
  normalReturn=True,entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi'],
  condition='Initialized metadata and matching disabled collector, stable disjoint owned base/cache fields, normally returning class predicates. Both possible first-predicate results are proved separately; the second result is unused. The cache receives unchanged base reference or null; the inherited base field is never written.')


def nonnull_preparation_program(regions,entry,*,null_helper):
 """Own the selected nonnull receiver check and the separate owned trap arm."""
 need('literal-owned-nonnull-preparation',all(type(n)is int and n>0 for n in(entry,null_helper)))
 g=BytesPath(regions,entry);g.take('4883ec28','4885c9');branch=g.at
 g.branch('74',False,1);g.take('4883c428','c3')
 null_entry=g.at;g.call(null_helper);g.take('cc')
 other=BytesPath(regions,branch);other.branch('74',True,1)
 need('exact-owned-null-trap-successor',other.at==null_entry)
 return dict(selectedBytes=g.seen,receiverNonNullRequired=True,incomingReceiverUnchanged=True,
  selectedNormalPathCalls=0,selectedNormalPathStores=0,normalReturn=True,entryRspRestored=True,
  nullArmHelperVa=null_helper,nullArmNormalReturnAdmitted=False,
  barrierClaimed=False,condition='The actual caller independently proves incoming RCX nonnull. The selected path only tests that receiver and restores its own stack; the owned null call/INT3 arm is excluded.')


def _peek(g,count):
 try:return bytes(g.bytes[g.at+i]for i in range(count))
 except KeyError as error:raise ValueError(LABEL+'.owned-source-bytes')from error


def _jump(g):
 if _peek(g,1)==b'\xeb':g.jump('eb',1)
 else:g.jump('e9')


def _branch(g,taken):
 raw=_peek(g,1)
 if raw in(b'\x74',b'\x75'):g.branch(raw.hex(),taken,1)
 else:
  raw=_peek(g,2);need('owned-equality-branch',raw in(b'\x0f\x84',b'\x0f\x85'))
  g.branch(raw.hex(),taken)


def discriminator(g,tag,*,initial_register=None):
 """Exact TEST/SUB/CMP unsigned partition tree over the actual header word."""
 need('literal-tag',type(tag)is int and 0<=tag<=65535)
 need('explicit-initial-discriminator-register',initial_register is None or type(initial_register)is int and initial_register==1)
 value=tag if initial_register is not None else None;register=initial_register;flags=None;seen=set();start=len(g.seen)
 for _ in range(128):
  need('finite-acyclic-discriminator',g.at not in seen);seen.add(g.at)
  raw=_peek(g,3)
  if raw in(bytes.fromhex(h)for h in('0fb74c','0fb754')):
   register=1 if raw[-1]==0x4c else 2;g.take(raw.hex(),'2438');value=tag;flags=None
  elif raw==bytes.fromhex('66396c'):
   g.take('66396c2438');value=tag;register='header16';flags=(tag==0,False)
  elif raw==bytes.fromhex('66837c'):
   g.take('66837c2438');immediate=g.read(1)[0]
   need('literal-small-header-word-comparison',immediate<128)
   value=tag;register='header16';flags=(tag==immediate,tag<immediate)
  elif raw[:2]in(bytes.fromhex('85c9'),bytes.fromhex('85d2')):
   expected=1 if raw[1]==0xc9 else 2
   need('same-test-register',register==expected and value is not None)
   g.take(raw[:2].hex());flags=(value==0,False)
  elif raw[0]==0x83 and raw[1]in(0xe9,0xea,0xf9,0xfa):
   expected=1 if raw[1]in(0xe9,0xf9)else 2
   need('same-DWORD-discriminator-register',register==expected and value is not None)
   immediate=int.from_bytes(raw[2:3],'little',signed=True)&0xffffffff
   g.take(raw.hex());old=value;result=(old-immediate)&0xffffffff
   flags=(result==0,old<immediate)
   if raw[1]in(0xe9,0xea):
    need('literal-small-positive-partition-subtraction',1<=immediate<=127);value=result
  elif raw[0]==0xb8:
   need('literal-word-sized-register-comparison',register==1 and value is not None)
   g.take('b8');immediate=int.from_bytes(g.read(4),'little')
   need('literal-ushort-partition-comparison',0<=immediate<65536)
   g.take('3bc8');flags=(value==immediate,value<immediate)
  elif raw[:2]==bytes.fromhex('81e9'):
   need('same-explicit-DWORD-partition-register',register==1 and value is not None)
   g.take('81e9');immediate=int.from_bytes(g.read(4),'little')
   need('literal-positive-ushort-partition-subtraction',1<=immediate<65536)
   old=value;value=(old-immediate)&0xffffffff;flags=(value==0,old<immediate)
  elif raw[:2]in(bytes.fromhex(h)for h in('0f84','0f85','0f87','0f86','0f82','0f83'))or raw[0]in(0x74,0x75,0x77,0x76,0x72,0x73):
   need('owned-known-comparison-flags',flags is not None)
   short=raw[0]!=0x0f;condition=raw[0]&15 if short else raw[1]&15;zero,carry=flags
   take={4:zero,5:not zero,7:not carry and not zero,6:carry or zero,2:carry,3:not carry}[condition]
   g.branch(raw[:1 if short else 2].hex(),take,1 if short else 4)
  elif raw[:2]in(bytes.fromhex('488b'),bytes.fromhex('4c8b')):
   need('comparison-selected-owned-leaf',flags is not None)
   return dict(selectedBytes=g.seen[start:],leafVa=g.at,tag=tag,headerWordUnchanged=True,
    partitionArithmetic='uint32 TEST/CMP and literal positive partition subtraction with independently replayed flags',
    normalChildOrReturnAdmitted=False)
  else:raise ValueError(LABEL+'.unsupported-discriminator:'+raw.hex())
 raise ValueError(LABEL+'.finite-discriminator-bound')


def header_prefix(g):
 """Own the initialized Reader/output/header-local argument path to its E8."""
 g.take('48895c2408');next_=_peek(g,5)
 if next_==bytes.fromhex('4889742418'):
  profile='sil-rdi';zero='rsi';reader='rdi';g.take('4889742418','57','4883ec20','33f6','498bd8')
  flag=g.relative('403835');g.take('488bfa');_branch(g,True)
  g.take('488d542438','6689742438','488bcf')
 else:
  g.take('48896c2418');saved=_peek(g,1);need('finite-BPL-helper-profile',saved in(b'\x56',b'\x57'))
  reader='rsi'if saved==b'\x56'else'rdi';profile='bpl-'+reader;zero='rbp'
  g.take(saved.hex(),'4883ec20','33ed','498bd8');flag=g.relative('40382d')
  g.take('488bf2'if reader=='rsi'else'488bfa');_branch(g,True)
  g.take('488d542438','66896c2438','488bce'if reader=='rsi'else'488bcf')
 return profile,zero,reader,flag


def large_header_prefix(g):
 """Exact R14-zero/RBP-reader/RSI-output prefix, including its owned frame."""
 g.take('488bc4','48895820','55','56','57','4156','4157')
 if _peek(g,3)==bytes.fromhex('4881ec'):
  g.take('4881ec80000000');stack=128;local=184
 else:g.take('4883ec70');stack=112;local=168
 g.take('4533f6');image_base=g.relative('4c8d3d');flag=g.relative('443835')
 g.take('498bf0','488bea');_branch(g,True)
 displacement=local.to_bytes(4,'little').hex()
 g.take('488d9424'+displacement,'664489b424'+displacement,'488bcd')
 return dict(stackBytes=stack,headerLocalOffset=local,imageBase=image_base,initializedFlagCellVa=flag)


def client_selection(regions,entry,*,tag,extended=False,ff=False):
 """Own the distinct inline header and null-output returning-reader call site.

 This partial source witness records each actual helper target. Its helper ABI,
 Reader effects and closed forwarding source must still be independently bound.
 """
 need('literal-inline-header-selection',type(tag)is int and 0<=tag<65536
  and type(extended)is bool and type(ff)is bool and not(ff and extended)
  and(extended or ff or tag<250))
 g=BytesPath(regions,entry)
 g.take('48895c2408','48896c2418','56','57','4154','4156','4157','4883ec30','4533e4','498bf8')
 flag=g.relative('443825');g.take('488bda');_branch(g,True)
 header_flag=g.relative('443825');g.take('664489642468');_branch(g,True)
 g.take('4533c0','488bcb','418d5001');before_site=g.at;before=g.relative('e8')
 g.take('488b4350','4533c0','488bcb','0fb630','418d5001');advance_site=g.at;advance=g.relative('e8')
 g.take('4080fefa');g.branch('0f82',not(ff or extended));raw_usage=None;raw_site=None;raw_target=None
 if ff:
  g.branch('0f84',False)
  return dict(selectedBytes=g.seen,initializedFlagCellVa=flag,headerFlagCellVa=header_flag,
   beforeInstructionVa=before_site,beforeTargetVa=before,advanceInstructionVa=advance_site,advanceTargetVa=advance,
   canonicalFF=True,continuationVa=g.at,wholeCallerAdmitted=False)
 if extended:
  g.branch('0f84',True);site=g.at;cell=g.relative('4c8b05');raw_usage=dict(instructionVa=site,cellVa=cell)
  g.take('488d542468','488bcb');raw_site=g.at;raw_target=g.relative('e8')
  g.take('440fb7742468');_jump(g)
 else:g.take('440fb7f6','6689742468')
 g.take('410fb7ce');collector_base=g.relative('488d35');g.take('bdffff1f00')
 selected=discriminator(g,tag,initial_register=1)
 cast_usage=None;cast_site=None;cast=None
 if _peek(g,3)==bytes.fromhex('488b0f'):
  g.take('488b0f','4885c9');_branch(g,True)
 else:
  usage_site=g.at;cast_cell=g.relative('488b15');cast_usage=dict(instructionVa=usage_site,cellVa=cast_cell)
  g.take('488b0f');cast_site=g.at;cast=g.relative('e8');g.take('4885c0');_branch(g,False)
 child_usage_site=g.at;context_mode='direct-rdx'
 if _peek(g,3)==bytes.fromhex('4c8b35'):
  cell=g.relative('4c8b35');g.take('4d396638');_branch(g,True)
  g.take('498b5638','488bcb','488b12');context_mode='ready-r14-rgctx56-slot0'
 else:cell=g.relative('488b15');g.take('488bcb')
 child_site=g.at;child=g.relative('e8')
 jumps=set()
 while _peek(g,1)in(b'\xeb',b'\xe9'):
  need('bounded-owned-result-jump-chain',g.at not in jumps and len(jumps)<4);jumps.add(g.at);_jump(g)
 need('owned-client-returned-result-store',_peek(g,3)in(bytes.fromhex('488bd0'),bytes.fromhex('443925')))
 return dict(selectedBytes=g.seen,initializedFlagCellVa=flag,headerFlagCellVa=header_flag,
  beforeInstructionVa=before_site,beforeTargetVa=before,advanceInstructionVa=advance_site,advanceTargetVa=advance,
  canonicalFF=False,tag=tag,extendedHeader=extended,rawHeaderUsage=raw_usage,
  rawHeaderInstructionVa=raw_site,rawHeaderTargetVa=raw_target,collectorBaseVa=collector_base,
  discriminator=selected,nullableCastUsage=cast_usage,
  nullableCastInstructionVa=cast_site,nullableCastTargetVa=cast,
  childUsage=dict(instructionVa=child_usage_site,cellVa=cell,contextMode=context_mode),childInstructionVa=child_site,childTargetVa=child,
  resultStoreEntryVa=g.at,outputInitiallyNullRequired=True,wholeCallerAdmitted=False,
  concreteChildGrammarAdmitted=False)


def client_program(regions,entry,*,tag,barrier,disabled_flag,cast=None,extended=False,
 ff=False,child_null=False,cached=False,base_null=False):
 """Complete distinct inline union/header/cache path, with helper joins separate."""
 need('literal-client-output-and-cache-paths',all(type(n)is bool for n in(ff,extended,child_null,cached,base_null)))
 selected=client_selection(regions,entry,tag=tag,extended=extended,ff=ff)
 g=BytesPath(regions,entry);g.seen=list(selected['selectedBytes'])
 g.at=selected['continuationVa']if ff else selected['resultStoreEntryVa'];cache_usage=None;predicate=None
 used_barrier=None
 if ff:
  need('same-disabled-client-FF-collector',g.relative('443925')==disabled_flag)
  collector=g.relative('488d35');g.take('664489642468','bdffff1f00','4c8927');_branch(g,True)
 else:
  if selected['nullableCastTargetVa']is not None:need('actual-client-nullable-cast-source',selected['nullableCastTargetVa']==cast)
  if _peek(g,3)==bytes.fromhex('488bd0'):
   g.take('488bd0','488907','488bcf');g.call(barrier);used_barrier=barrier
   _jump(g)
  else:
   need('same-disabled-client-positive-collector',g.relative('443925')==disabled_flag)
   g.take('488907');_branch(g,True)
  collector=selected['collectorBaseVa']
 g.take('488b3f','4885ff');_branch(g,ff or child_null)
 cache_flag=None
 if not(ff or child_null):
  cache_flag=g.relative('443825');_branch(g,True)
  g.take('4c396718');_branch(g,cached)
  if not cached:
   g.take('4c396710');_branch(g,base_null)
   if not base_null:
    g.take('488b5f10');usage_site=g.at;cell=g.relative('488b15');g.take('488b0b');predicate=g.relative('e8')
    g.take('f6d8','481bd2','4823d3','48895718');second=g.relative('488b15');g.take('488b0b')
    need('same-client-inline-cache-type',cell==second);g.call(predicate)
    need('same-disabled-client-cache-collector',g.relative('443925')==disabled_flag);_branch(g,True)
    cache_usage=dict(instructionVa=usage_site,cellVa=cell)
 g.take('488b5c2460','488b6c2470','4883c430','415f','415e','415c','5f','5e','c3')
 return dict(selectedBytes=g.seen,profile='r12-rbx-inline-client',inlineHeader=selected,
  initializedFlagCellVa=selected['initializedFlagCellVa'],headerInstructionVa=None,headerTargetVa=None,
  headerWordLocalOffset=104,tag=None if ff else tag,canonicalFF=ff,
  discriminator=selected.get('discriminator'),childUsage=selected.get('childUsage'),
  nullableCastUsage=selected.get('nullableCastUsage'),childInstructionVa=selected.get('childInstructionVa'),
  childTargetVa=selected.get('childTargetVa'),outputInitiallyNullRequired=not ff,
  clearedOutputBytes=8 if ff else 0,sameReader=True,sameOutput=True,wholeReferenceOutput=True,
  normalReturn=True,entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r14','r15'],
  frame=dict(entryRspDelta=-88,shadow=[0,32],headerHomeEntry=[16,18],savedEntryHomes=dict(rbx=[8,16],rbp=[24,32]),pushed=['rsi','rdi','r12','r14','r15']),
  inlineDisabledCollector=used_barrier is None,disabledBarrierTargetVa=used_barrier,
  disabledBarrierSameOutputAddress=True,disabledCollectorFlagVa=disabled_flag,
  positiveChildReturnedNull=child_null if not ff else None,posthookTargetVa=None,postPreparationTargetVa=None,
  inlineCacheUsage=cache_usage,inlinePredicateTargetVa=predicate,inlineCacheFlagVa=cache_flag,
  cacheInitiallyPresent=cached,inheritedBaseInitiallyNull=base_null,
  cacheWriteBytes=8 if cache_usage is not None else 0,inheritedBaseReferencePreserved=True,
  inlineCacheResult='unchanged base reference when predicate AL is nonzero; null otherwise',
  independentInlineHeaderHelpersRequired=True,concreteChildGrammarAdmitted=False,wholeOwnerAdmitted=False)


def large_program(regions,entry,*,tag,header,packable,barrier,cast,disabled_flag,ff=False,child_null=False):
 """Selected large-frame one/two-case program under the same disabled flag."""
 g=BytesPath(regions,entry);prefix=large_header_prefix(g);header_site=g.at;g.call(header)
 g.take('84c0');_branch(g,ff);usage=None;child_site=None
 local=prefix['headerLocalOffset'];displacement=local.to_bytes(4,'little').hex();selected=None
 if not ff:
  need('one-or-two-case-large-tag',tag in(0,1));start=len(g.seen)
  g.take('0fb7bc24'+displacement,'6685ff');_branch(g,tag!=0)
  if tag:
   g.take('6683ff01');_branch(g,False)
  if _peek(g,1)in(b'\xeb',b'\xe9'):_jump(g)
  selected=dict(selectedBytes=g.seen[start:],leafVa=g.at,tag=tag,headerWordUnchanged=True)
  g.take('488b0e','4885c9');_branch(g,True)
  site=g.at;cell=g.relative('488b15');usage=dict(instructionVa=site,cellVa=cell)
  g.take('488bcd');child_site=g.at;g.call(packable)
  need('same-disabled-large-positive-collector',g.relative('443935')==disabled_flag)
  g.take('488906');_branch(g,True)
 else:
  need('same-disabled-large-FF-collector',g.relative('443935')==disabled_flag)
  g.take('4c8936');_branch(g,True)
 g.take('488b0e','4885c9');_branch(g,ff or child_null);hook=None
 if not(ff or child_null):g.take('33d2');hook=g.relative('e8')
 saved=(prefix['stackBytes']+72).to_bytes(4,'little').hex()
 g.take('488b9c24'+saved)
 g.take('4881c480000000'if prefix['stackBytes']==128 else'4883c470','415f','415e','5f','5e','5d','c3')
 return dict(selectedBytes=g.seen,profile='r14-rbp-rsi-large',**prefix,
  headerInstructionVa=header_site,headerTargetVa=header,headerWordLocalOffset=local,
  tag=None if ff else tag,canonicalFF=ff,discriminator=selected,childUsage=usage,nullableCastUsage=None,
  childInstructionVa=child_site,childTargetVa=None if ff else packable,
  outputInitiallyNullRequired=not ff,clearedOutputBytes=8 if ff else 0,
  sameReader=True,sameOutput=True,wholeReferenceOutput=True,normalReturn=True,
  entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','r14','r15'],
  headerHomeEntryOffset=local-(prefix['stackBytes']+40),savedRbxHomeEntryOffset=32,
  disabledBarrierTargetVa=None,disabledBarrierSameOutputAddress=True,
  inlineDisabledCollector=True,disabledCollectorFlagVa=disabled_flag,
  positiveChildReturnedNull=child_null if not ff else None,posthookTargetVa=hook,
  postPreparationTargetVa=None,independentlyProvedPosthookSourceRequired=hook is not None,
  concreteChildGrammarAdmitted=False,wholeOwnerAdmitted=False,
  normalCompatibleHelpersRequired=True,liveCallbackSelectionObserved=False)


def program(regions,entry,*,tag,header,packable,barrier,cast,disabled_flag,ff=False,child_null=False):
 """Whole warm null-output caller for exact SIL/BPL helper-header profiles."""
 need('literal-program-selection',type(ff)is bool and type(child_null)is bool and type(tag)is int and 0<=tag<65536
  and(cast is None or type(cast)is int and cast>0)
  and all(type(n)is int and n>0 for n in(entry,header,packable,barrier,disabled_flag)))
 g=BytesPath(regions,entry)
 if _peek(g,18)==bytes.fromhex('48895c240848896c24185657415441564157'):
  return client_program(regions,entry,tag=tag,barrier=barrier,disabled_flag=disabled_flag,
   cast=cast,ff=ff,child_null=child_null)
 if _peek(g,3)==bytes.fromhex('488bc4'):
  return large_program(regions,entry,tag=tag,header=header,packable=packable,barrier=barrier,
   cast=cast,disabled_flag=disabled_flag,ff=ff,child_null=child_null)
 profile,zero,reader,flag=header_prefix(g)
 header_site=g.at;g.call(header);g.take('84c0');_branch(g,ff)
 selected=None;usage=None;child_site=None;cast_usage=None;barrier_done=False;inline_collector=False
 if ff:
  if _peek(g,2)==bytes.fromhex('3935'):
   need('same-disabled-inline-FF-collector',zero=='rsi'and g.relative('3935')==disabled_flag)
   g.take('488933');_branch(g,True);barrier_done=True;inline_collector=True
  else:g.take('488933'if zero=='rsi'else'48892b')
 else:
  selected=discriminator(g,tag)
  if _peek(g,3)==bytes.fromhex('488b0b'):
   g.take('488b0b','4885c9');_branch(g,True)
  usage_site=g.at;cell=g.relative('488b15')
  if _peek(g,3)==bytes.fromhex('488b0b'):
   need('independently-selected-nullable-cast-target',type(cast)is int)
   cast_usage=dict(instructionVa=usage_site,cellVa=cell);g.take('488b0b');g.call(cast)
   g.take('488bce'if reader=='rsi'else'488bcf','4885c0');_branch(g,False)
   usage_site=g.at;cell=g.relative('488b15')
   if _peek(g,1)in(b'\xeb',b'\xe9'):_jump(g)
   child_site=g.at;g.call(packable)
  else:
   if _peek(g,1)in(b'\xeb',b'\xe9'):_jump(g)
   g.take('488bce'if reader=='rsi'else'488bcf');child_site=g.at;g.call(packable)
  usage=dict(instructionVa=usage_site,cellVa=cell)
  if _peek(g,3)==bytes.fromhex('488bcb'):
   g.take('488bcb','488903');g.call(barrier);_jump(g)
   barrier_done=True
  elif _peek(g,2)==bytes.fromhex('3935'):
   need('own-current-disabled-inline-collector',g.relative('3935')==disabled_flag)
   g.take('488903');_branch(g,True);barrier_done=True;inline_collector=True
  else:g.take('488903')
  if _peek(g,1)in(b'\xeb',b'\xe9'):_jump(g)
 # The disabled helper receives the same whole output reference address.
 if not barrier_done:
  g.take('488bcb');g.call(barrier)
 hook=None;prepare=None;no_posthook=_peek(g,5)==bytes.fromhex('488b5c2430')
 if no_posthook:
  # Some one-child abstract wrappers return directly after the actual output
  # barrier. The complete epilogue below still owns every remaining byte.
  pass
 elif _peek(g,3)==bytes.fromhex('488b1b'):
  g.take('488b1b','4885db');_branch(g,ff or child_null)
  if not(ff or child_null):
   g.take('488bcb');prepare=g.relative('e8');g.take('33d2','488bcb');hook=g.relative('e8')
 else:
  g.take('488b0b','4885c9');_branch(g,ff or child_null)
  if not(ff or child_null):g.take('33d2');hook=g.relative('e8')
 g.take('488b5c2430','488b742440'if zero=='rsi'else'488b6c2440','4883c420',
  '5e'if reader=='rsi'else'5f','c3')
 result=dict(selectedBytes=g.seen,profile=profile,initializedFlagCellVa=flag,
  headerInstructionVa=header_site,headerTargetVa=header,headerWordLocalOffset=56,
  tag=None if ff else tag,canonicalFF=ff,discriminator=selected,childUsage=usage,nullableCastUsage=cast_usage,
  childInstructionVa=child_site,childTargetVa=None if ff else packable,
  outputInitiallyNullRequired=not ff,clearedOutputBytes=8 if ff else 0,
  sameReader=True,sameOutput=True,wholeReferenceOutput=True,normalReturn=True,
  entryRspRestored=True,restoredNonvolatiles=['rbx',zero,reader],
  disabledBarrierTargetVa=None if inline_collector else barrier,disabledBarrierSameOutputAddress=True,
  inlineDisabledCollector=inline_collector,disabledCollectorFlagVa=disabled_flag if inline_collector else None,
  positiveChildReturnedNull=child_null if not ff else None,posthookTargetVa=hook,
  postPreparationTargetVa=prepare,
  independentlyProvedPosthookSourceRequired=hook is not None,
  concreteChildGrammarAdmitted=False,wholeOwnerAdmitted=False,
  normalCompatibleHelpersRequired=True,liveCallbackSelectionObserved=False)
 if no_posthook:result['directReturnWithoutPosthook']=True
 return result


def derive_many(image,pins,wrapper_names):
 """Independently report every requested nested transport and precise hold.

 No source family is selected from an abstract name alone. All tag paths must
 resolve bijectively onto the fresh immediate wrapper family, with actual
 nominal returning ReadPackable contexts and independently owned helper bytes.
 """
 import copy
 import json
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.contracts import CONTRACTS_DIR
 from scripts.game_data.il2cpp.formatter_composition import _vtable,derive_typed_usage_context
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import modelview_packable_sources,pointer_param as pointer,scalar_param_native as scalar
 from scripts.game_data.memorypack import levelscript_condition_client_helpers as client_helpers
 from scripts.game_data.memorypack.module_structure_models import enclosing_header
 from scripts.game_data.memorypack.pooled_string_list_sources import compatible_list_cast
 from scripts.game_data.memorypack.skill_action_union_sources import original_lineage
 from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
 from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
 from scripts.game_data.memorypack.skill_shared_sequence_sources import _wrapper_holder
 from scripts.game_data.memorypack.union_dispatch import _family
 need('bounded-distinct-requested-wrappers',isinstance(wrapper_names,(tuple,list))
  and 1<=len(wrapper_names)<=32 and len(set(wrapper_names))==len(wrapper_names)
  and all(isinstance(n,str)for n in wrapper_names))
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
 wrappers=image.memorypack_wrappers;by_name={w.name:w for w in wrappers.values()}
 core=json.loads((CONTRACTS_DIR/'npc_runtime_native.json').read_bytes())
 generic=json.loads((CONTRACTS_DIR/'leveldata_npc_patrol_native.json').read_bytes())
 need('same-selected-reference-source-inputs',core['nativeInputs']==generic['nativeInputs']==pins)
 routes=copy.deepcopy(generic['declarations']['adapters']['referenceRoutes']);routes['wrappers']=[]
 reference=modelview_packable_sources.validate_components(image,pins,core['readPackable'],routes)
 packable=base+core['readPackable']['entryRva']
 reader=ctx.index.types['MemoryPack.MemoryPackReader']
 header_method,=[m for m in md.methods_for(reader)if md.string(m.name_index)=='TryReadUnionHeader']
 need('own-instance-header-bool-ABI',not header_method.flags&16 and header_method.parameter_count==1
  and ctx.type_name(header_method.return_type)=='bool')
 parameter,=md.parameters_for(header_method)
 need('own-header-UInt16-output-byref',ctx.type_name(parameter.type_index)=='ushort'
  and image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)[10:12]==bytes((7,32)))
 named_header=image.method_pointer_va(header_method)
 prepared=[];barriers={};nullable={};actual_headers=set()
 for name in wrapper_names:
  need('actual-selected-nested-wrapper',name in by_name);wrapper=by_name[name]
  need('actual-abstract-without-static-record-reader',wrapper.frames_as_union is True)
  formatter_name=wrapper.name+'+'+wrapper.name.rsplit('.',1)[-1]+'Formatter'
  formatter,=image.named_type_definitions[formatter_name]
  method,=[m for m in md.methods_for(formatter)if md.string(m.name_index)=='Deserialize'and m.slot==5 and not m.flags&16]
  _vtable(image,formatter.index,5,method.index,LABEL+'.own-slot5')
  need('own-void-two-byref-ABI',ctx.type_name(method.return_type)=='void'and method.parameter_count==2)
  for p,nominal,kind in zip(md.parameters_for(method),('MemoryPack.MemoryPackReader',wrapper.name),(17,18),strict=True):
   raw=image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16)
   need('actual-own-Reader-and-wrapper-byrefs',(ctx.type_name(p.type_index),raw[10:12])==(nominal,bytes((kind,32))))
  body=pointer.owned(image,image.method_pointer_va(method));prepared.append((wrapper,method,body))
  try:
   selected=BytesPath(body['regions'],body['pointer'])
   (large_header_prefix if _peek(selected,3)==bytes.fromhex('488bc4')else header_prefix)(selected)
   actual_headers.add(selected.relative('e8'))
  except ValueError:pass # Unsupported prefix remains an independent held owner below.
  for row in body['rows']:
   raw=bytes.fromhex(row['bytes'])
   if len(raw)!=5 or raw[0]!=232:continue
   target=control_transfer(row)['target']
   at=int(row['va'],16)
   previous=image.pe.bytes_at_va(at-3,3)
   if previous in(bytes.fromhex('488bcb'),bytes.fromhex('488bcf'),bytes.fromhex('488903'))and target not in barriers:
    try:barriers[target]=_barrier(image,target)
    except(ValueError,KeyError,IndexError):barriers[target]=None
   if previous==bytes.fromhex('488b0b')and image.pe.bytes_at_va(at-10,3)==bytes.fromhex('488b15')and target not in nullable:
    try:
     source=pointer.owned(image,target)
     nullable[target]=dict(windows=source['windows'],program=compatible_list_cast(source['regions'],target,0,null=True))
    except(ValueError,KeyError,IndexError):nullable[target]=None
 need('one-actual-complete-helper-header-source',len(actual_headers)==1)
 header=next(iter(actual_headers));header_body=pointer.owned(image,header)
 offsets=scalar.reader_offsets(image,LABEL)
 headers={marker:enclosing_header(header_body['regions'],header,offsets,marker=marker)for marker in('short','extended','false')}
 selected_barriers={target:proof for target,proof in barriers.items()if proof is not None}
 need('bounded-actual-disabled-barrier-family',1<=len(selected_barriers)<=8)
 # Each candidate retains its own actual entry; no pointer equivalence follows.
 disabled={base+p['result']['disabledFlagRva']for p in selected_barriers.values()}
 need('same-independent-current-disabled-collector',len(disabled)==1);disabled_flag=next(iter(disabled))
 owners=[]
 for wrapper,method,body in prepared:
  stage='complete-caller-programs'
  try:
   successes=[];failures=[]
   family=_family(wrappers,wrapper.name);need('bounded-nested-family',1<=len(family)<=512)
   for barrier,barrier_proof in selected_barriers.items():
    for cast in[None,*[t for t,p in nullable.items()if p is not None]]:
     try:
      paths=[]
      for tag in range(len(family)):
       positive=program(body['regions'],body['pointer'],tag=tag,header=header,packable=packable,
        barrier=barrier,cast=cast,disabled_flag=disabled_flag)
       null_child=program(body['regions'],body['pointer'],tag=tag,header=header,packable=packable,
        barrier=barrier,cast=cast,disabled_flag=disabled_flag,child_null=True)
       paths.append(dict(tag=tag,nonnullChild=positive,nullChild=null_child))
      ff=program(body['regions'],body['pointer'],tag=0,header=header,packable=packable,
       barrier=barrier,cast=cast,disabled_flag=disabled_flag,ff=True)
      used_cast=any(p['nonnullChild']['nullableCastUsage']is not None for p in paths)
      used_barrier=any(not p['nonnullChild']['inlineDisabledCollector']for p in paths)or not ff['inlineDisabledCollector']
      identity=(barrier if used_barrier else None,cast if used_cast else None)
      if any(row[0]==identity for row in successes):continue
      successes.append((identity,paths,ff,barrier_proof,nullable.get(cast)))
     except(ValueError,KeyError,IndexError)as error:failures.append(str(error)[:500])
   need('one-complete-exact-nested-caller',len(successes)==1)
   identity,paths,ff,barrier_proof,cast_proof=successes[0];resolved=[];hooks={};post_preparations={};inline_helpers=None;inline_programs=None;inline_cache=None
   if paths[0]['nonnullChild']['profile']=='r12-rbx-inline-client':
    stage='complete-inline-header-helper-sources'
    extended=client_program(body['regions'],body['pointer'],tag=0,barrier=identity[0],disabled_flag=disabled_flag,cast=identity[1],extended=True)
    inline_helpers=client_helpers.derive_common(image,pins,extended['inlineHeader'],core,routes)
    inline_programs=dict(extended=extended,cached=client_program(body['regions'],body['pointer'],tag=0,
     barrier=identity[0],disabled_flag=disabled_flag,cast=identity[1],cached=True),baseNull=client_program(body['regions'],body['pointer'],tag=0,
     barrier=identity[0],disabled_flag=disabled_flag,cast=identity[1],base_null=True))
    first=paths[0]['nonnullChild'];holder=_wrapper_holder(ctx,image,wrapper);cache=ctx.field(wrapper.name+'::__realInstance')
    need('exact-inline-cache-and-inherited-reference-slots',holder['offset']==16 and tuple(cache)==(wrapper.name,wrapper.wrapped_type,24))
    cache_usage=derive_typed_usage_context(image,first['inlineCacheUsage']['instructionVa']-base,label=LABEL+'.inline-cache-type')
    need('same-inline-cache-original-type',(cache_usage.get('tag'),cache_usage.get('typeName'))==(1,wrapper.wrapped_type))
    cast_body=pointer.owned(image,identity[1]);calls=pointer.calls(cast_body)
    need('same-independent-inline-cache-predicate',len(calls)==1 and first['inlinePredicateTargetVa']==calls[0])
    inline_cache=dict(holder=holder,cacheField=list(cache),typedRequest=cache_usage,predicateTargetRva=calls[0]-base,
     initializedFlagCellVa=first['inlineCacheFlagVa'],inheritedBaseReferencePreserved=True,
     predicateOutcomeProved=False,liveCacheCoherenceObserved=False)
   for row in paths:
    stage='actual-nominal-child:'+str(row['tag'])
    path=row['nonnullChild'];site=path['childUsage']['instructionVa']
    child_usage=derive_typed_usage_context(image,site-base,label=LABEL+'.actual-child')
    arguments=child_usage.get('methodArguments',[]);need('one-owned-nominal-child-argument',len(arguments)==1 and arguments[0]in by_name)
    child=by_name[arguments[0]];need('actual-child-in-own-immediate-family',child.type_definition in family)
    bound=bind_typed_read(image,child_usage,method_name='ReadPackable',argument=child.name,kind=18,reference=True)
    need('same-actual-returning-reader-definition',bound['methodDefinition']==reference['packableContext']['packableDefinition'])
    read_source=None
    if inline_helpers is not None:
     stage='actual-closed-child-returning-source:'+str(row['tag'])
     read_source=client_helpers.bind_returning(image,path,child_usage,bound,inline_helpers,canonical=packable)
    else:need('actual-canonical-returning-reader-target',path['childTargetVa']==packable)
    cast_usage=None
    if path['nullableCastUsage']is not None:
     cast_usage=derive_typed_usage_context(image,path['nullableCastUsage']['instructionVa']-base,label=LABEL+'.actual-cast')
     need('same-actual-nullable-cast-class',(cast_usage.get('tag'),cast_usage.get('typeName'))==(1,child.name))
    hook=path['posthookTargetVa']
    if hook is not None and hook not in hooks:
     stage='owned-posthook-metadata:'+str(row['tag'])
     declarations=[]
     for candidate in md.methods_for(md.types[wrapper.type_definition]):
      if md.string(candidate.name_index)=='OnDeserialized'and candidate.parameter_count==0 and not candidate.flags&16 and ctx.type_name(candidate.return_type)=='void':
       at=image.method_pointer_va(candidate)
       if at==hook:declarations.append([candidate.index,wrapper.name,'OnDeserialized',at-base])
     if len(declarations)!=1:raise ValueError(LABEL+'.one-own-declared-noargument-posthook:'+json.dumps(declarations))
     scalar.owned_method_abi(image,ctx,declarations[0][0],wrapper.type_definition,('void',1,False),[],LABEL+'.OnDeserialized')
     stage='actual-posthook-cache-source:'+str(row['tag']);owned_hook=pointer.owned(image,hook)
     holder=_wrapper_holder(ctx,image,wrapper);cache=ctx.field(wrapper.name+'::__realInstance')
     need('same-exact-own-typed-cache',tuple(cache[:2])==(wrapper.name,wrapper.wrapped_type)and cache[2]!=holder['offset'])
     field,=[f for f in md.fields_for(md.types[wrapper.type_definition])if md.string(f.name_index)=='__realInstance']
     raw=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16)
     need('owned-reference-cache-kind',len(raw)==16 and raw[10]in(18,21)and raw[11]==0)
     scalar.ordinary(image,ctx.type_pointer(field.type_index),raw[10],LABEL+'.cache',reference=True)
     extent=None
     if raw[10]==21:
      from scripts.game_data.il2cpp.reference_layouts import closed_generic_reference_extent
      extent=closed_generic_reference_extent(ctx,field.type_index)
      need('same-closed-cache-carrier',extent['type']==wrapper.wrapped_type)
     checked=[]
     for actual_cast,nullable_proof in nullable.items():
      if nullable_proof is None:continue
      cast_body=pointer.owned(image,actual_cast);calls=pointer.calls(cast_body)
      need('one-independent-cast-predicate',len(calls)==1)
      for actual_barrier in selected_barriers:
       try:
        large=_peek(BytesPath(owned_hook['regions'],hook),5)==bytes.fromhex('48895c2410')
        options=({},dict(predicate_matches=False),dict(cached=True),dict(base_null=True))if large else({},dict(cached=True),dict(base_null=True))
        programs=[posthook_program(owned_hook['regions'],hook,base_slot=holder['offset'],cache_slot=cache[2],cast=actual_cast,
         barrier=actual_barrier,predicate=calls[0],disabled_flag=disabled_flag,**option)for option in options]
        if large and any(p[0]==actual_cast for p in checked):continue
        checked.append((actual_cast,actual_barrier,programs))
       except ValueError:continue
     if not checked:
      # A typed-cache hook may call its own compatible cast clone rather than
      # the union caller's nullable-cast entry. Prove this actual callee in full;
      # neither its pointer nor its predicate is borrowed from the union.
      for actual_cast in sorted(set(pointer.calls(owned_hook))-set(nullable)):
       try:
        cast_body=pointer.owned(image,actual_cast);calls=pointer.calls(cast_body)
        if len(calls)!=1:continue
        for null in(False,True):compatible_list_cast(cast_body['regions'],actual_cast,calls[0],null=null)
       except(ValueError,KeyError,IndexError,TypeError):continue
       for actual_barrier in selected_barriers:
        try:
         programs=[posthook_program(owned_hook['regions'],hook,base_slot=holder['offset'],cache_slot=cache[2],
          cast=actual_cast,barrier=actual_barrier,**option)for option in({},dict(cached=True),dict(base_null=True))]
         checked.append((actual_cast,actual_barrier,programs))
        except ValueError:continue
     need('one-complete-exact-cache-hook',len(checked)==1);actual_cast,actual_barrier,programs=checked[0]
     cast_body=pointer.owned(image,actual_cast);calls=pointer.calls(cast_body)
     need('one-independent-cast-predicate',len(calls)==1)
     casts=[compatible_list_cast(cast_body['regions'],actual_cast,calls[0],null=n)for n in(False,True)]
     cache_usage=derive_typed_usage_context(image,programs[0]['castUsageInstructionVa']-base,label=LABEL+'.actual-cache-type')
     need('exact-actual-cache-cast-type',(cache_usage.get('tag'),cache_usage.get('typeName'))==(1,wrapper.wrapped_type))
     hooks[hook]=dict(method=declarations[0],programs=programs,holder=holder,cacheField=list(cache),cacheRawTypeHex=raw.hex().upper(),
      closedCacheReference=extent,typedCastUsage=cache_usage,castWindows=cast_body['windows'],castPrograms=casts,
      sourceWindows=owned_hook['windows'],sourceRegions=[(a,b.hex().upper())for a,b in owned_hook['regions']],
      barrier=selected_barriers[actual_barrier],inheritedBaseReferencePreserved=True,
      cacheWriteAdmitted=True,liveCacheCoherenceObserved=False)
     if actual_cast not in nullable:hooks[hook]['castSourceIndependentOfUnionNullableCast']=True
    prepare=path['postPreparationTargetVa']
    if prepare is not None and prepare not in post_preparations:
     stage='actual-nonnull-post-preparation:'+str(row['tag']);preparation=pointer.owned(image,prepare)
     preparation_calls=pointer.calls(preparation);need('one-owned-preparation-null-arm-helper',len(preparation_calls)==1)
     post_preparations[prepare]=dict(sourceWindows=preparation['windows'],
      sourceRegions=[(a,b.hex().upper())for a,b in preparation['regions']],
      program=nonnull_preparation_program(preparation['regions'],prepare,null_helper=preparation_calls[0]))
    stage='actual-owned-original-ancestry:'+str(row['tag'])
    resolved.append(dict(tag=row['tag'],wrapperName=child.name,wrappedType=child.wrapped_type,
     source=row,typedRequest=child_usage,typedArgument=bound,nullableCastUsage=cast_usage,actualReturningSource=read_source,
     originalLineage=original_lineage(image,ctx,child,wrapper.wrapped_type)))
   need('actual-bijective-entire-nested-family',len({r['wrapperName']for r in resolved})==len(family))
   owners.append(dict(status='complete-nested-union-transport-source',wrapperName=wrapper.name,wrappedType=wrapper.wrapped_type,
    slot5Method=[method.index,image.type_name(method.declaring_type),'Deserialize',body['pointer']-base],
    sourceWindows=body['windows'],sourceRegions=[(a,b.hex().upper())for a,b in body['regions']],
    cases=resolved,canonicalFF=ff,barrier=barrier_proof,nullableCast=cast_proof,
    posthooks=hooks,postPreparations=post_preparations,inlineHeaderHelpers=inline_helpers,inlinePrograms=inline_programs,inlineCache=inline_cache,
    concreteChildGrammarAdmitted=False,wholeOwnerAdmitted=False))
  except(ValueError,KeyError,IndexError,TypeError)as error:
   owners.append(dict(status='pendingReview',wrapperName=wrapper.name,wrappedType=wrapper.wrapped_type,
    reason=str(error)[:1800],programHolds=list(dict.fromkeys(failures))[:12]if'failures'in locals()else[],
    diagnostic=dict(validator=LABEL,stage=stage,errorType=type(error).__name__,
     failedGate=str(error).split(':',1)[0],sourceMethod=[method.index,body['pointer']-base],
     expected='complete own selected caller, nominal child context, exact helper/posthook and original ancestry joins',
     actual=str(error)[:1200]),
    concreteChildGrammarAdmitted=False,wholeOwnerAdmitted=False))
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-nested-condition-source.v1',nativeInputs=pins,
  reference=reference,headerWindows=header_body['windows'],headerPrograms=headers,
  actualHeaderTargetRva=header-base,namedHeaderPointerRva=named_header-base,
  headerPointerEquivalenceProved=header==named_header,headerSourceProvedIndependently=True,owners=owners,
  concreteChildGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)))

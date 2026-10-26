"""Actual Patrol actions-list constructor and first reference growth paths.

These are selected source transfers, not observed allocation or a complete
conversion.  The first growth path requires a clean, valid, sufficiently sized
reference-array cache block, compatible initialized array metadata/context,
normal class/indexed-context helper returns, disabled collector/instrumentation
and disjoint stable storage.  A noarg List constructor's initialized empty-array
result and allocation-zeroed count/version remain explicit conditions.  Later
growth requires an independently proved preserving Array.Copy source.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.story-patrol-list-growth-source.v1'


def need(check,condition):
 if not condition:raise ValueError('storyPatrolListGrowth.'+check)


def _flag(g,prefix):
 cell=g.relative(prefix);g.take('00');return cell+1


def constructor_program(regions,entry,*,disabled,ready=True):
 need('literal-class-ready-branch',type(ready)is bool)
 g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20','488bf9','488bda',
  '488b4a20','33d2','488b89c0000000');indexed=g.relative('e8')
 g.take('83b8e000000000');g.branch('75',ready,1);initializer=None
 if not ready:g.take('488bc8');initializer=g.relative('e8')
 g.take('488b4b20','33d2','488b89c0000000')
 need('same-indexed-class-context-helper',g.relative('e8')==indexed)
 need('same-disabled-collector',_flag(g,'833d')==disabled)
 g.take('488b88b8000000','488b01','48894710');g.branch('74',True,1)
 g.take('488b5c2438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,entry=entry,indexedContextTarget=indexed,contextSlot=0,methodInfoClassOffset=32,
  classContextOffset=192,classStaticFieldsOffset=184,staticReferenceSlot=0,
  incomingMethodInfoPreserved=True,unchangedStaticReferenceStoredAtReceiverOffset=16,
  classInitializerTarget=initializer,ready=ready,disabledCollectorCell=disabled,
  listCountAndVersionWritten=False,initializedTypedEmptyArrayRequired=True,zeroedCountAndVersionRequired=True,
  entryRspRestored=True,nonvolatilesRestored=['rbx','rdi'],normalReturn=True)


def array_store_program(regions,entry,*,disabled):
 g=BytesPath(regions,entry);g.take('4883ec28','3b5118');g.branch('73',False,1)
 need('same-disabled-collector',_flag(g,'833d')==disabled)
 g.take('4c8944d120');g.branch('74',True,1);g.take('4883c428','c3')
 return dict(selectedBytes=g.seen,entry=entry,receiver='incoming RCX',index='incoming EDX',value='unchanged incoming R8',
  unsignedIndexBelowArrayLengthRequired=True,arrayLengthOffset=24,elementBaseOffset=32,elementScale=8,
  storedReferenceUnchanged=True,disabledCollectorCell=disabled,opaqueCalls=0,entryRspRestored=True,normalReturn=True,
  compatibleTypedArrayAndElementRequired=True,arrayAllocationOrNominalIdentityProved=False)


def resize_dispatch_program(regions,entry):
 """Complete Add route under nonnull full array and ready slot11 context."""
 g=BytesPath(regions,entry);g.take('48895c2410','48896c2418','56','57','4156','4883ec20',
  'ff411c','498be8','488b7910','4c8bf2','48635918','488bf1','4885ff');g.branch('0f84',False)
 g.take('3b5f18');g.branch('72',False,1)
 g.take('498b4020','488b88c0000000','488b4158','4883782000');g.branch('75',True,1)
 g.take('488b4520','498bd6','488bce','4c8b80c0000000','4d8b4058');growth=g.relative('e8')
 g.jump('eb',1);g.take('488b5c2448','488b6c2450','4883c420','415e','5f','5e','c3')
 return dict(selectedBytes=g.seen,entry=entry,versionOffset=28,versionIncrement=1,receiverStorageOffsets=dict(items=16,size=24),
  slot11ReadyRequired=True,unchangedReceiverAndReferenceIntoGrowth=True,growthContextSlot=11,growthTarget=growth,
  growthRequiredBecauseCapacityNotGreaterThanSize=True,normalGrowthReturnRequired=True,
  entryRspRestored=True,nonvolatilesRestored=['rbx','rbp','rsi','rdi','r14'],normalReturn=True)


def first_growth_program(regions,entry,*,disabled,empty=True,large=False):
 """Whole selected reference-array growth path through same-value tail.

The default retains the first empty/small-cache route. Positive old arrays
select the actual preserving-copy call; large allocations select their own
actual allocation/preparation calls and require their normal valid results.
"""
 need('literal-consistent-growth-selection',type(empty)is bool and type(large)is bool and (not empty or not large))
 g=BytesPath(regions,entry)
 g.take('4889542410','53','55','56','57','4157','4883ec40','498b4020','498bd8',
  '448b7918','488bea','488bf9','44897c2470','4c8b88c0000000','498b4160','4883782000')
 g.branch('75',True,1)
 g.take('488b4320','418d5f01','4c89a42488000000','4c896c2438','4c89742430','488b88c0000000',
  '488b4710','488b7160','4885c0');g.branch('0f84',False)
 g.take('395818');g.branch('0f8d',False)
 g.take('4883781800','b904000000');g.branch('75',not empty,1)
 if empty:g.take('8bc1');g.jump('eb',1)
 else:g.take('8b4018','03c0','b9ffffef7f','3bc1','0f47c1')
 g.take('3bc3','0f4dd8','488b4620','488b88c0000000','488b81c0000000','4883782000')
 g.branch('75',True,1)
 g.take('488b4620','488b88c0000000','488bb1c0000000','3b5f18');g.branch('0f8c',False)
 g.take('488b4710','4885c0');g.branch('0f84',False)
 g.take('3b5818');g.branch('0f84',False)
 g.take('488b4e20','85db');g.branch('0f8f',True)
 g.take('488b89c0000000','41be01000000','418bd6');indexed=g.relative('e8')
 g.take('488bc8','448beb','488be8');initialize=g.relative('e8')
 g.take('81fbffffff7f');g.branch('0f87',False)
 g.take('8bb500010000');cache_table=g.relative('4c8d25')
 g.take('490faff5','4883c620','f6853801000020');g.branch('75',True,1)
 g.take('488b4540','83782800');g.branch('0f8d',False)
 g.take('0fb64808','80e103','413ace');g.branch('0f85',False)
 cache_mode=g.relative('443935');g.branch('75',False,1)
 cache_heads=g.relative('4c8b35');cache_flags=g.relative('448b3d');g.jump('eb',1)
 g.take('4881fe00080000');g.branch('0f87',large)
 instrumentation=_flag(g,'833d');g.branch('74',True,1);allocation_calls={}
 if large:
  allocation_calls['prepare-allocation']=g.relative('e8');g.take('418bd7','488bce')
  allocation_calls['allocate']=g.relative('e8');g.take('488bc8')
  allocation_calls['prepare-result']=g.relative('e8');g.take('488bd8','4885c0');g.jump('e9');g.branch('75',True,1)
  allocation_bytes=None
 else:
  g.take('498b8cf4e81a0000','498b1cce','4885db');g.branch('0f85',True)
  g.take('488b03','498904ce','48c1e104');allocation_bytes=g.relative('48010d')
 need('same-disabled-instrumentation',_flag(g,'833d')==instrumentation);g.take('48892b');g.branch('74',True,1)
 need('same-disabled-array-header-barrier',_flag(g,'833d')==disabled);g.branch('74',True,1)
 g.take('448b7c2470');g.jump('eb',1)
 allocation_hook=g.relative('f605')+1;g.take('80','4c896b18');g.branch('74',True,1)
 g.take('837f1800');g.branch('7e',empty,1);copy=None
 if not empty:
  g.take('8b4718','4533c9','488b4f10','4c8bc3','48c744242800000000','33d2','89442420');copy=g.relative('e8')
 need('same-disabled-list-publication-barrier',_flag(g,'833d')==disabled)
 g.take('48895f10');g.branch('74',True,1)
 g.take('488b6c2478','488b4f10','418d4701','894718','4885c9');g.branch('74',False,1)
 g.take('4963d7','4c8bc5','4c8b742430','4c8b6c2438','4c8ba42488000000',
  '4883c440','415f','5f','5e','5d','5b');tail=g.relative('e9')
 return dict(selectedBytes=g.seen,entry=entry,oldCount=0 if empty else 'old full-array count',oldCapacity=0 if empty else 'old full-array capacity',
  newCount=1 if empty else 'old count +1',newCapacity=4 if empty else 'max(old count +1,min(2*old capacity,0x7fefffff))',
  arrayElementBytesRequired=8,arrayAllocationBytes=64 if empty else 'new capacity *8+32',arrayReferenceFlagRequired=True,
  arrayClassSourceSlot=1,ensureCapacityContextSlot=12,setCapacityContextSlot=24,
  indexedContextTarget=indexed,arrayClassInitializerTarget=initialize,actualArrayStoreTail=tail,
  disabledCollectorCell=disabled,allocationCacheTable=cache_table,allocationCacheHeads=cache_heads,
  allocationCacheModeCell=cache_mode,allocationCacheFlagsCell=cache_flags,allocationBytesCounter=allocation_bytes,
  instrumentationCell=instrumentation,allocationHookCell=allocation_hook,
  initializedCleanNonemptyCompatibleCacheBlockRequired=not large,cacheDescriptorTagRequired=1,
  exactArrayClassStoredToNewArray=True,actualCapacityStoredToNewArray=True,
  newArrayPublishedBeforeCountAndElement=True,oldCountSavedAcrossCacheAllocation=True,
  incomingReferenceSavedAtEntryOffset=16,incomingReferenceReloadedBeforeTail=True,
  tailArguments=dict(rcx='same newly published array',edx=0 if empty else 'old count',r8='unchanged incoming element reference'),
  argumentHomeRestoresOriginalReference=True,entryRspRestored=True,
  nonvolatilesRestored=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],
  normalTail=True,laterGrowthOrArrayCopyProved=False,allocationRuntimeObserved=False,wholeConversionProved=False,
  emptyOldArray=empty,largeAllocationSelected=large,actualAllocationCalls=allocation_calls,
  actualPreservingCopyTarget=copy,preservingCopyEffectsIndependentlyRequired=not empty,
  normalValidAllocationAndPreparationResultsRequired=large)


def join_programs(constructors,dispatch,growth,store):
 need('both-complete-class-ready-constructor-paths',len(constructors)==2
  and {p.get('ready')for p in constructors}=={True,False}
  and all(p.get('entry')==constructors[0].get('entry')and p.get('normalReturn')is True for p in constructors))
 need('actual-full-array-Add-calls-owned-growth',dispatch.get('growthTarget')==growth.get('entry'))
 need('actual-growth-tails-owned-same-reference-store',growth.get('actualArrayStoreTail')==store.get('entry')
  and store.get('storedReferenceUnchanged')is True)
 need('same-owned-indexed-context-resolver',all(p.get('indexedContextTarget')==growth.get('indexedContextTarget')for p in constructors))
 need('same-disabled-collector-in-all-reference-publications',all(p.get('disabledCollectorCell')==growth.get('disabledCollectorCell')for p in constructors+[store]))
 need('exact-first-append-count-and-capacity',(growth.get('oldCount'),growth.get('oldCapacity'),growth.get('newCount'),growth.get('newCapacity'))==(0,0,1,4))
 return dict(initialAppendSourceProvedConditional=True,constructorPublishesSelectedStaticArray=True,
  growthPreservesIncomingElementThroughFinalArrayStore=True,laterGrowthOrArrayCopyProved=False,
  allocationRuntimeObserved=False,wholeConversionProved=False)


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.memorypack import leveldata_patrol_point_sources as points,pointer_param as pointer,scalar_param_native as scalar
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
 point=points.derive(image,pins);targets=point['proof']['actualTargets'];usages=point['proof']['typedUsages']
 add=pointer.owned(image,base+targets['action-add']);dispatch=resize_dispatch_program(add['regions'],add['pointer'])
 constructor=pointer.owned(image,base+targets['construct-actions-list'])
 disabled=base+point['proof']['disabledBarrier']['result']['disabledFlagRva']
 constructors=[constructor_program(constructor['regions'],constructor['pointer'],disabled=disabled,ready=ready)for ready in (True,False)]
 growth=pointer.owned(image,dispatch['growthTarget']);first=first_growth_program(growth['regions'],growth['pointer'],disabled=disabled)
 store=pointer.owned(image,first['actualArrayStoreTail']);stored=array_store_program(store['regions'],store['pointer'],disabled=disabled)
 joined=join_programs(constructors,dispatch,first,stored)
 td=ctx.index.types[points.LIST];symbols=ContextSymbols(image);context=symbols.context(td.index)
 entries=context['entries'];klass=entries[0]
 need('own-List-class-context-zero',klass['relativeSlot']==0 and klass['kind']==2
  and klass['type']['definition']['name']==points.LIST and len(klass['type']['classArguments'])==1)
 variable,=klass['type']['classArguments'];owner=variable.get('parameterOwner',{})
 need('actual-reciprocal-List-VAR',owner.get('typeIndex')==td.index and owner.get('ordinal')==0
  and bytes.fromhex(variable['rawHex'])[10:12]==bytes((19,0)))
 need('own-array-of-same-List-VAR',entries[1]['relativeSlot']==1 and entries[1]['kind']==2
  and bytes.fromhex(entries[1]['type']['rawHex'])[10:12]==bytes((29,0)))
 array_raw=bytes.fromhex(entries[1]['type']['rawHex'])
 need('same-actual-SZARRAY-element-pointer',int.from_bytes(array_raw[:8],'little')==variable['typePointerVa'])
 roles={11:'AddWithResize',12:'EnsureCapacity',24:'set_Capacity'}
 for slot,name in roles.items():
  e=entries[slot]
  need('own-named-List-context-method:'+name,e['relativeSlot']==slot and e['kind']==3
   and e['typeName']==points.LIST and e['methodName']==name
   and e['classArguments']==[variable]and e['methodArguments']==[])
 ctor=md.methods[usages['actions-list-constructor']['methodSpec'][0]]
 need('own-List-noarg-instance-constructor',ctor.declaring_type==td.index and md.string(ctor.name_index)=='.ctor'
  and not ctor.flags&16 and not ctor.parameter_count)
 scalar.owned_method_abi(image,ctx,ctor.index,td.index,('void',1,False),[],SCHEMA+'.constructor')
 # Actual instructions have independently resolved the same indexed context
 # entry. Prove its complete count-indexed leaf, never an inflated class value.
 indexed=first['indexedContextTarget'];raw=image.pe.bytes_at_va(indexed,15);g=BytesPath([(indexed,raw)],indexed)
 g.take('488bc1','4863ca','488b0cc8');resolver=g.relative('e9')
 need('exact-whole-indexed-context-leaf',g.at==indexed+15)
 def capture(body):return dict(sourceWindows=body['windows'],sourceRegions=[[at,h.hex().upper()]for at,h in body['regions']])
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-first-actions-list-growth-source',nativeInputs=pins,
  proof=dict(pointTransfer=point,constructor=capture(constructor),constructorPaths=constructors,
   add=capture(add),selectedResizeDispatch=dispatch,growth=capture(growth),selectedFirstGrowth=first,
   arrayStore=capture(store),selectedArrayStore=stored,programJoin=joined,ownListContext=context,
   indexedContextLeaf=dict(selectedBytes=g.seen,typeResolverTail=resolver,entryRspUnchanged=True)),
  **joined,evidenceBoundary=dict(exact='Actual closed Patrol List constructor/Add requests, complete selected constructor and first reference-array resize/store paths, full restored frames, same incoming element, own reciprocal List contexts and exact actual helper targets.',
   conditional=__doc__,unresolved=['actual initialized empty-array/zero-allocation state','actual clean reference allocation cache/array class and opaque initializer effects',
    'later positive growth and preserving Array.Copy','SafeCount actual Count selection','complete Convert/Init/checkpoint/playback']))))

"""Compose fresh installed Patrol consumer source evidence, without runtime use.

This API has no report-file input and grants no wire/host capability. It joins
the actual Config-to-Core source segments, constructors, finite point loop,
Count selection, preserving list growth, initializer/install and checkpoint/
radio callers. Source-dependent runtime conditions and still-unproved native
helper effects remain separate named frontiers. No source result observes
controller activation, event registration, playback or a live callback pair.
"""
import copy

SCHEMA='endfield.story-patrol-offline-consumer-sources.v1'
OWNER_NAMES={'loader','initializer','growth','allocation','count','methodSelection','helpers','consumer','radio','range'}


def need(check,condition):
 if not condition:raise ValueError('storyPatrolOffline.'+check)


def _same_pins(node,pins,path='owners'):
 if isinstance(node,dict):
  if 'nativeInputs'in node:need('same-selected-native-inputs:'+path,node['nativeInputs']==pins)
  for key,value in node.items():
   if key!='nativeInputs':_same_pins(value,pins,path+'.'+str(key))
 elif isinstance(node,list):
  for i,value in enumerate(node):_same_pins(value,pins,path+'['+str(i)+']')


def compose(owners,pins,*,count_limit=4096,heap=None):
 from scripts.game_data.memorypack import leveldata_patrol_constructor_sources as ctor
 need('exact-source-stage-set',isinstance(owners,dict)and set(owners)==OWNER_NAMES)
 need('exact-current-finite-point-domain',type(count_limit)is int and count_limit==4096)
 for name,owner in owners.items():
  need('owned-selected-source:'+name,isinstance(owner,dict)and owner.get('nativeInputs')==pins)
  need('no-live-runtime-or-playback-promotion:'+name,owner.get('runtimeInvocationObserved')is False and owner.get('playbackProved')is False)
 _same_pins(owners,pins)
 loader=owners['loader'];constructors=loader['proof']['controllerConstruction'];lead=constructors['proof']['lead']
 point=lead['proof']['pointTransfer'];prefix=point['proof']['prefix'];initial=owners['initializer'];installation=initial['proof']['installation']
 growth=owners['growth'];first=growth['proof']['referenceCopySource']['proof']['firstGrowthSource']
 count=owners['count'];methods=owners['methodSelection'];helpers=owners['helpers'];consumer=owners['consumer']
 for obj,schema,flag in((loader,'endfield.story-patrol-loader-constructor-source.v1','completeSelectedLoaderConstructorControlAndFieldSourcesProved'),
  (constructors,'endfield.story-patrol-constructor-sources.v1','CoreAndActionInitializedConstructorStoreSourcesProved'),
  (lead,'endfield.story-patrol-lead-source.v1','selectedAssetLookupArgumentFlowProved'),
  (initial,'endfield.story-patrol-initializer-control-source.v1','selectedCompleteCallerControlProved'),
  (growth,'endfield.story-patrol-positive-list-growth-source.v1','normalGrowthControlAndReferenceCopiesProved'),
  (owners['allocation'],'endfield.story-patrol-allocation-source.v1','selectedLargeAllocationArgumentPointerAndFrameSourcesProved'),
  (count,'endfield.story-patrol-Count-dispatch-source.v1','completeSlotZeroCountCallerArgumentAndReturnSourceProved'),
  (methods,'endfield.story-patrol-method-selection-source.v1','selectedMethodSpecKeyAndTripleSourceProved')):
  need('exact-independent-source-schema:'+schema,obj.get('schema')==schema)
  need('complete-selected-source-gate:'+flag,obj.get(flag)is True)
 need('same-fresh-Config-prefix-and-installation',installation['proof']['prefix']==prefix)
 need('same-fresh-point-loop-and-array-growth',first['proof']['pointTransfer']==point)
 need('same-fresh-positive-growth-and-allocation-call-sources',owners['allocation']['proof']['positiveGrowthSource']==growth)
 need('same-fresh-point-loop-and-Count-dispatch',count['proof']['pointTransfer']==point)
 need('same-independent-Object-key-source',methods['proof']['ObjectKeySource']==count['proof']['ObjectKeySource'])
 starts=[p['selectedBytes'][0][0]for p in lead['proof']['programs']]
 need('all-lead-paths-start-at-exact-Config-prefix-end',len(starts)==5 and all(s==prefix['proof']['programs'][0]['continuationInstructionVa']for s in starts))
 loop_entry=point['proof']['programs'][0]['selectedBytes'][0][0]
 need('all-five-lead-paths-rejoin-exact-point-loop',all(p['continuationInstructionVa']==loop_entry for p in lead['proof']['programs']))
 need('same-Core-and-action-constructors',constructors['proof']['programs'][ctor.CORE]['entry']==prefix['proof']['programs'][0]['constructorTargetVa']
  and constructors['proof']['constructors'][ctor.ACTION]['targetRva']==point['proof']['actualTargets']['construct-action'])
 need('same-point-Count-request',count['proof']['SafeCountSource']['proof']['typedRequest']==point['proof']['typedUsages']['points-safe-count'])
 selected=count['proof']['selectedInterfacePath'];static=methods['proof']['selectedStaticCountRow']
 need('same-selected-count-method-and-actual-fallback-pointer',static['methodDefinition']==count['proof']['countMethodDefinition']
  and static['primaryPointer']==selected['selectedCallbackRequired']and selected['callbackArguments']==
   dict(rcx='unchanged incoming collection receiver',rdx='selected same-slot MethodInfo'))
 need('same-finite-count-and-positive-growth-domains',growth['countLimit']==count_limit and point['proof']['induction']['countLimit']==count_limit)
 need('every-positive-reference-copy-and-append-state-covered',growth['proof']['capacityInduction']['allAppendStatesCoveredExactlyOnce']is True
  and growth['proof']['capacityInduction']['everyGrowthCopyPreservesExactlyPriorCount']is True)
 need('exact-initializer-to-conversion-target',initial['proof']['actualTargets']['convert-Config-to-Core']==prefix['proof']['metadataJoin']['method']['targetRva'])
 need('same-installed-reference-local-source',initial['successfulConversionLocalFlowProved']is True and installation['canonicalFieldInstallationSourceProved']is True)
 producer=helpers['lookupThunk']['actualProducer'];filtered=helpers['baseProcess']['actualFilter']
 need('same-selected-checkpoint-event-key',producer['eventKey']==consumer['eventKey'])
 need('checkpoint-producer-and-filter-caller-sources',producer['checkpointRequestSourceProved']is True and filtered['filterCallerSourceProved']is True
  and helpers['lookupThunk']['selectedControllerPatrolFieldReadProved']is True and helpers['baseProcess']['selectedAbsentReplacementReturnProved']is True)
 installed=installation['proof']['nominalField'];getter=helpers['lookupThunk']['nominalField']
 need('same-new-controller-installed-and-read-Core-field',installed==getter and installed[:2]==[ctor.CONTROLLER,ctor.CORE])
 # The delayed radio and subaction callers must target the same actual request.
 need('same-actual-radio-request',owners['radio']['delayed']['request']==consumer['radio']['requestMethod'])
 joins=dict(selectedConversionCallerByteSegmentsJoined=True,ownConstructorAndLoaderPublicationSourcesJoined=True,
  finiteOrderedPointAndPreservingReferenceGrowthSourcesJoined=True,conditionalCountKeyAndCallbackSourceJoined=True,
  selectedLargeAllocationArgumentAndPointerSourcesJoined=True,
  canonicalInitializerOutputAndInstallationSourcesJoined=True,checkpointRequestGetterAndFilterCallerSourcesJoined=True,
  actualRadioRequestSourcesJoined=True)
 static_frontiers=[
  dict(role='asset-and-loader-helpers',required='Complete own concat/path, TryLoad/Get, service/nested-constructor and Unity validity helper effects, including their selected receiver/context joins.'),
  dict(role='allocation-and-array-state',required='Backend allocation/zeroing and nonselected collector/preparation effects plus valid disjoint object/reference-array state; selected growth/copy and large-helper argument/pointer/frame programs are already joined.'),
  dict(role='method-and-interface-setup',required='Method descriptor/setup, full table reservation/collision/resize history and inflated interface MethodInfo construction; the selected static Count row/key/lookup/projection sources are already joined.'),
  dict(role='initializer-lookup-and-callbacks',required='Own eligibility/config/entity lookup helper effects and full virtual getter/setter/preparation paths; the selected output local and canonical field source are already joined.'),
  dict(role='checkpoint-and-playback-effects',required='Own blackboard/Param/output/entity/event-manager helper effects, action/state dispatch and playback consumer joins; selected producer/filter/radio callers are source-proved.'),
  dict(role='nonselected-control',required='Replacement, initialization, exceptional and other nonselected helper branches remain independent native-control obligations, never runtime observations.')]
 runtime_conditions=[
  'Actual selected controller/entity/config asset and live activation are observed only by an authorized runtime capture.',
  'Actual initialized canonical class/interner/key/interface tables and exact callback/MethodInfo pairs must satisfy the separately proved source selections; file bytes do not observe those live values.',
  'Actual allocation/cache/lock state, no intervening replacement and stable compatible disjoint storage must satisfy every selected source condition.',
  'Actual checkpoint producer/filter/event dispatch and audio/action playback invocation require live ownership evidence.']
 if heap is not None:
  from scripts.game_data.memorypack import leveldata_patrol_heap_sources as heap_owner
  heap_owner.validate(heap,pins);_same_pins(heap,pins,'heap')
  need('same-fresh-selected-allocation-and-complete-backend',heap['proof']['backendSource']['proof']['allocationSource']==owners['allocation'])
  owners={**owners,'heap':heap};joins['conditionalWarmHeapBackendAndCurrentFillSourcesJoined']=True
  static_frontiers[1]=dict(role='allocation-and-array-state',required='Nonselected preparation/collector/cold/retry and other class-selector paths remain independent; the actual warm first-success allocator arguments/frame/unchanged result/counters, complete current fill and finite requested/rounded extents are joined. The actual allocation primitive must provide compatible valid disjoint page-rounded storage; this result neither proves nor observes capacity or success.')
  runtime_conditions.append('Warm initialized heap, zero collection gate, selected allocator class/zero/CPU flags and first-success valid disjoint page-rounded allocation are explicit conditions; OS availability and live heap contents are not observed.')
 return dict(schema=SCHEMA,status='validated-conditional-composed-offline-source-chain',nativeInputs=copy.deepcopy(pins),
  finitePointCountLimit=count_limit,sourceJoins=joins,sources=copy.deepcopy(owners),
  unprovedNativeSourceFrontiers=static_frontiers,runtimeConditions=runtime_conditions,
  wholeConversionProved=False,wholeInitializerProved=False,checkpointProducerProved=False,checkpointFilterProved=False,
  playbackSourceClosureProved=False,offlineEvidenceExhausted=False,runtimeInvocationObserved=False,playbackProved=False,
  wireGrammarAdmitted=False,parentOrHostAdmitted=False,
  evidenceBoundary=dict(exact='Fresh source-only components joined by complete selected identities, byte-segment seams, own constructors, actual Count callback target/static key row, finite growth/copy domain and unchanged installation/checkpoint/radio values.',
   conditional=__doc__,unresolved='Named unproved native source frontiers and runtime conditions remain explicit; no wire, host, live selection, checkpoint or playback authority is emitted.'))


def derive(image,pins,*,stage=None,include_heap=False,include_normal_helpers=False):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.memorypack import leveldata_patrol_loader_sources as loader,leveldata_patrol_initializer_sources as initializer
 from scripts.game_data.memorypack import leveldata_patrol_positive_growth_sources as growth,leveldata_patrol_count_dispatch_sources as count
 from scripts.game_data.memorypack import leveldata_patrol_allocation_sources as allocation
 from scripts.game_data.memorypack import leveldata_patrol_method_selection_sources as method_selection,leveldata_patrol_helper_sources as helpers
 from scripts.game_data.memorypack import leveldata_patrol_consumer_sources as consumer,leveldata_patrol_radio_sources as radio,leveldata_patrol_range_sources as range_source
 _publication_gate(image,pins);owners={}
 for name,owner in(('loader',loader),('initializer',initializer),('growth',growth),('allocation',allocation),('count',count),('methodSelection',method_selection),
  ('helpers',helpers),('consumer',consumer),('radio',radio),('range',range_source)):
  if stage is not None:stage(name,'deriving')
  owners[name]=owner.derive(image,pins)
  if stage is not None:stage(name,'derived')
 need('literal-heap-source-opt-in',type(include_heap)is bool and type(include_normal_helpers)is bool)
 heap=None
 if include_heap or include_normal_helpers:
  from scripts.game_data.memorypack import leveldata_patrol_heap_sources as heap_owner
  if stage is not None:stage('heap','deriving')
  heap=heap_owner.derive(image,pins)
  if stage is not None:stage('heap','derived')
 result=compose(owners,pins,heap=heap)
 if include_normal_helpers:
  from scripts.game_data.memorypack import leveldata_patrol_normal_sources as normal
  result=normal.derive(image,pins,base_source=result,stage=stage)
 _publication_gate(image,pins);return result

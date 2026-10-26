"""Finite Patrol actions-list capacity/control and preserving-copy composition.

The native paths are independently replayed for empty, positive cached and
positive large allocations.  Typed metadata, clean disjoint valid allocation
results and normal allocation/preparation helpers remain conditions.  The
source proves the actual arguments and stores, not live heap/cache state.
It does not substitute those runtime conditions for still unproved allocator
body effects or claim the enclosing conversion has been completed.
"""
import json

from scripts.game_data.memorypack.leveldata_patrol_list_growth_sources import need

SCHEMA='endfield.story-patrol-positive-list-growth-source.v1'


def capacity_induction(count_limit=4096):
 need('explicit-finite-positive-reference-count',type(count_limit)is int and 1<=count_limit<=4096)
 capacity=0;transitions=[];spare=0;maximum_copy=0
 for count in range(count_limit):
  need('valid-initial-or-positive-list-capacity',0<=count<=capacity or count==capacity==0)
  if count==capacity:
   new=4 if capacity==0 else capacity*2
   need('literal-signed-native-growth-math-does-not-clamp-or-wrap',count+1<=new<0x7fefffff
    and new*8+32<1<<31)
   transitions.append(dict(oldCount=count,oldCapacity=capacity,newCount=count+1,newCapacity=new,
    arrayBytes=new*8+32,oldBytesCopied=count*8,allocationPath='large'if new*8+32>2048 else'small-cache'))
   maximum_copy=max(maximum_copy,count*8);capacity=new
  else:
   need('spare-path-index-in-bounds',count<capacity);spare+=1
 return dict(countMinimum=0,countMaximum=count_limit,initialCount=0,initialCapacity=0,
  firstGrowthCapacity=4,positiveCapacityMultiplier=2,growthTransitions=transitions,
  spareAppendStates=spare,allAppendStatesCoveredExactlyOnce=len(transitions)+spare==count_limit,
  finalCapacity=capacity,maximumPreservingCopyBytes=maximum_copy,
  everyGrowthCopyPreservesExactlyPriorCount=True,everyAppendStoresAtPriorCount=True,
  signedNativeCounterArithmeticExact=True,elementBytes=8,allocationStateOrHelperEffectsProved=False)


def derive(image,pins,*,count_limit=4096):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.memorypack import leveldata_patrol_array_copy_sources as copy_owner,leveldata_patrol_list_growth_sources as growth_owner
 _publication_gate(image,pins);domain=capacity_induction(count_limit)
 copy=copy_owner.derive(image,pins,count_limit=count_limit);growth=copy['proof']['firstGrowthSource'];source=growth['proof']['growth']
 regions=[(a,bytes.fromhex(h))for a,h in source['sourceRegions']];first=growth['proof']['selectedFirstGrowth'];disabled=first['disabledCollectorCell']
 selected=[growth_owner.first_growth_program(regions,first['entry'],disabled=disabled,empty=False,large=large)for large in (False,True)]
 caller=copy['proof']['selectedArrayCopy']
 need('actual-growth-copy-and-independent-source',all(p['actualPreservingCopyTarget']==caller['entry']for p in selected)
  and copy['copyWholeSourceAndFrameProved']is True and copy['maxCopyBytes']>=domain['maximumPreservingCopyBytes'])
 need('all-three-allocation-control-branches',first['emptyOldArray']is True and first['largeAllocationSelected']is False
  and [p['largeAllocationSelected']for p in selected]==[False,True]
  and all(p['emptyOldArray']is False and p['argumentHomeRestoresOriginalReference']is True and p['entryRspRestored']is True for p in selected))
 need('same-actual-large-allocation-helper-targets',set(selected[1]['actualAllocationCalls'])=={'prepare-allocation','allocate','prepare-result'})
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-finite-positive-reference-growth-control',nativeInputs=pins,
  proof=dict(referenceCopySource=copy,positiveGrowthPrograms=selected,capacityInduction=domain),
  countLimit=count_limit,normalGrowthControlAndReferenceCopiesProved=True,
  actualAllocationAndPreparationCallArgumentsProved=True,largeAllocatorBodyEffectsProved=False,
  actualAllocationOrCacheStateObserved=False,wholeConversionProved=False,wholeInitializerProved=False,
  runtimeInvocationObserved=False,playbackProved=False,evidenceBoundary=dict(exact='Actual empty/small-positive/large-positive growth control, unchanged element/local/full frame, preserving reference copy through actual Array.Copy/FastCopy/move source, exhaustive finite capacity arithmetic and disjoint spare/new-element slots.',
   conditional=__doc__,unresolved=['actual allocator/preparation child source effects and valid disjoint returned storage',
    'initialized typed List/array/cache metadata state','actual Count callback and input stability','remaining conversion/initializer/checkpoint/playback']))))

"""Finite pooled spaceship cursor; erased dictionary conditions stay visible."""
from scripts.game_data.memorypack import leveldata_specific_components as source
from scripts.game_data.codecs.leveldata import current_ship_dictionary,current_vector_tuple


def validate(cap):
 if (not isinstance(cap,dict)or cap.get('typeName')!=source.TYPE or cap.get('childTypeName')!=source.CHILD
  or not isinstance(cap.get('wrapperName'),str)or not cap['wrapperName']
  or type(cap.get('memberCount'))is not int or cap['memberCount']!=8
  or type(cap.get('countLimit'))is not int or cap['countLimit']!=source.LIMIT
  or type(cap.get('admittedRouteTags'))is not list or cap['admittedRouteTags']!=[0]or type(cap['admittedRouteTags'][0])is not int
  or type(cap.get('wrapperNullAdmitted'))is not bool
  or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','finiteFloatProfile','actualCallbackEqualsProvedChildRequired',
   'actualDictionaryCallbacksEqualSourceWitnessRequired','actualDictionaryClosedContextAndSourceBodyCompatibilityRequired',
   'typedDictionaryConstructorAndHelperCompatibilityRequired','normalNonthrowingDictionaryInsertRequired'))
  or any(cap.get(k)is not False for k in('wholeGrammarAdmitted','concreteOriginalAdapterUsed','closedPointerEquivalenceProved',
   'storedMapSemanticsAdmitted','runtimeProviderSelectionObserved','parentFieldAdmitted','wholeOwnerAdmitted'))):
  raise ValueError('currentLevelSpecific.exact-conditional-spaceship-profile')
 declared=dict(wrappedType=source.CHILD,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in source.PLAN])
 source.bind_program(declared,cap.get('program'),[])
 caps=cap.get('childCapabilities',{})
 expected={source.CABIN_CAP,source.MACHINE_CAP,source.ULONG_CAP,source.tuples.LIST_CAP,source.tuples.VALUE_CAP}
 if not isinstance(caps,dict)or set(caps)!=expected:raise ValueError('currentLevelSpecific.exact-child-capability-set')
 for key in source.OPERATIONS.values():source.validate_child(key,caps)
 witnesses={key:caps[key]['sourceWitnessClassArguments']for key in(source.CABIN_CAP,source.MACHINE_CAP)}
 if cap.get('sourceWitnessClassArguments')!=witnesses:raise ValueError('currentLevelSpecific.outer-erased-source-witnesses')
 for binding in cap['program']['childBindings']:
  key=binding['capability']
  if (type(binding.get('readerMethodDefinition'))is not int or binding['readerMethodDefinition']<0
   or type(binding.get('sourceTargetRva'))is not int or binding['sourceTargetRva']<=0):raise ValueError('currentLevelSpecific.literal-collection-source-binding')
  join=dict(fieldName=binding['fieldName'],typeName=binding['typeName'],sourceTargetRva=binding['sourceTargetRva'],
   typedRequest=dict(methodName='ReadPackable',methodArguments=[binding['typeName']],methodSpec=[binding['readerMethodDefinition']]))
  if binding!=source.bind_collection({},join,dict(nativeInputs={},capabilities=caps),key):
   raise ValueError('currentLevelSpecific.complete-conditional-collection-binding')
 binding=cap.get('parentBinding',{})
 if (any(binding.get(k)!=v for k,v in dict(ownerType='Beyond.Gameplay.LevelData',fieldName='specificData',typeName=source.TYPE,capability=source.CAP).items())
  or type(binding.get('readerMethodDefinition'))is not int or binding['readerMethodDefinition']<0
  or type(binding.get('sourceTargetRva'))is not int or binding['sourceTargetRva']<=0
  or binding.get('actualCallbackEqualsProvedChildRequired')is not True):raise ValueError('currentLevelSpecific.exact-current-host-parent-binding')


def read(reader,field,cap):
 validate(cap);start=reader.offset;tag=reader.number('<B',field+'.unionTag')
 if tag==255:return None
 if tag==250:raise ValueError(field+':extended-LevelSpecific-tag-unproved')
 if 251<=tag<=254:raise ValueError(field+':reserved-LevelSpecific-union-marker')
 if tag!=0:raise ValueError(field+':unknown-LevelSpecific-union-tag:'+str(tag))
 at=reader.offset;marker=reader.number('<B',field+'.memberCount');value=None
 if marker==255:
  if cap['wrapperNullAdmitted']is not True:raise ValueError(field+':LevelSpecific-wrapper-null-unproved')
 else:
  if marker!=8:raise ValueError(field+':SpaceShip-member-count')
  caps=cap['childCapabilities'];value=dict(startOffset=at,recordType=source.CHILD,memberCount=8);ranges={}
  for member,declared,kind in source.PLAN:
   begin=reader.offset;path=field+'.'+member
   if kind=='ship-cabin-dictionary':data=current_ship_dictionary.read_cabin(reader,path,caps[source.CABIN_CAP])
   elif kind=='ship-uint64-dictionary':data=current_ship_dictionary.read_uint64(reader,path,caps[source.MACHINE_CAP])
   elif kind=='vector3-pair-list':data=current_vector_tuple.read_list(reader,path,caps[source.tuples.LIST_CAP],caps[source.tuples.VALUE_CAP])
   elif kind=='uint64-list':
    count=reader.number('<i',path+'.count')
    if not -1<=count<=source.LIMIT:raise ValueError(path+':ship-UInt64-list-count-limit')
    reader.need(max(count,0)*8,path+'.elements');rows=[str(reader.number('<Q',path+f'[{i}]'))for i in range(max(count,0))]
    data=dict(startOffset=begin,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)
   elif kind=='unity-vector3-raw12':data={axis:reader.single(path+'.'+axis)for axis in'xyz'}
   else:raise ValueError(path+':closed-spaceship-operation')
   value[member]=data;ranges[member]=[begin,reader.offset]
  value.update(endOffset=reader.offset,fieldRanges=ranges)
 return dict(startOffset=start,endOffset=reader.offset,tag=0,recordType=source.CHILD,value=value,
  sourceWitnessClassArguments=cap['sourceWitnessClassArguments'],closedPointerEquivalenceProved=False,
  actualDictionaryCallbacksEqualSourceWitnessRequired=True,actualDictionaryClosedContextAndSourceBodyCompatibilityRequired=True,
  typedDictionaryConstructorAndHelperCompatibilityRequired=True,normalNonthrowingDictionaryInsertRequired=True,
  storedMapSemanticsAdmitted=False,runtimeProviderSelectionObserved=False,wholeOwnerAdmitted=False)


def conditional_sources(cap):
 validate(cap);children=cap['childCapabilities'];result=[]
 for key in(source.CABIN_CAP,source.MACHINE_CAP):
  child=children[key]
  result.append(dict(typeName=child['typeName'],sourceWitnessClassArguments=child['sourceWitnessClassArguments'],
   closedPointerEquivalenceProved=False,actualCallbackEqualsSourceWitnessRequired=True,
   actualClosedContextAndSourceBodyCompatibilityRequired=True,typedConstructorAndHelperCompatibilityRequired=True,
   normalNonthrowingInsertRequired=True,keyCallbackEqualsPooledStringRequired=True,valueCallbackEqualsCanonicalRequired=True,
   storedMapSemanticsAdmitted=False,runtimeProviderSelectionObserved=False,countLimit=source.LIMIT))
 result.append(dict(typeName=source.tuples.LIST,elementType=source.tuples.TYPE,managedElementBytes=24,elementWireBytes=24,
  initiallyNullListRequired=True,countLimit=source.LIMIT,actualCallbackEqualsCanonicalRequired=True,runtimeFormatterSelectionObserved=False))
 result.append(dict(typeName=source.ULONGS,initiallyNullOutputRequired=True,countLimit=source.LIMIT,
  actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False))
 return result

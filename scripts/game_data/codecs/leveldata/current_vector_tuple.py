"""Raw24 Vector3 pairs under exact constructed-value and list capabilities."""
from scripts.game_data.memorypack import leveldata_vector_tuple_sources as source
from scripts.game_data.memorypack import leveldata_vector_tuple_list_sources as lists

VALUE_CAP='story-vector3-pair-value'
LIST_CAP='story-vector3-pair-list'


def validate(cap):
 if (not isinstance(cap,dict)or cap.get('typeName')!=source.TYPE
   or cap.get('classArguments')!=[source.ELEMENT,source.ELEMENT]
   or any(type(cap.get(k))is not int or cap[k]!=v for k,v in dict(managedBytes=24,wireBytes=24,headerBytes=0).items())
   or cap.get('referenceLaneOffsets')!=[]or cap.get('paddingByteRanges')!=[]
   or any(cap.get(k)is not True for k in('constructedValueLayoutProved','actualRawSourceProved','actualAdvanceSourceProved',
    'actualCallbackEqualsCanonicalRequired','finiteFloatProfile','profileAdmitted'))
   or any(cap.get(k)is not False for k in('nullMarkerAdmitted','wholeGrammarAdmitted','liveFormatterSelectionObserved'))):
  raise ValueError('currentVectorTuple.exact-constructed-Vector3-pair-profile')


def validate_list(cap,value):
 validate(value)
 if (not isinstance(cap,dict)or cap.get('typeName')!=lists.LIST or cap.get('elementType')!=source.TYPE
   or cap.get('elementCapability')!=VALUE_CAP
   or any(type(cap.get(k))is not int or cap[k]!=v for k,v in
    dict(countLimit=lists.LIMIT,headerBytes=4,managedElementBytes=24,elementWireBytes=24).items())
   or cap.get('countRange')!=[-1,lists.LIMIT]
   or any(cap.get(k)is not True for k in('nullable','positiveCountsAdmitted','initiallyNullListRequired',
    'actualCallbackEqualsCanonicalRequired','full24BitsStored','profileAdmitted'))
   or any(cap.get(k)is not False for k in('growthAdmitted','wholeGrammarAdmitted','liveFormatterSelectionObserved'))):
  raise ValueError('currentVectorTuple.exact-constructed-pair-list-profile')
 for key in('packableReaderMethodDefinition','packableReaderTargetRva'):
  if type(cap.get(key))is not int or cap[key]<(1 if key.endswith('TargetRva')else 0):
   raise ValueError('currentVectorTuple.literal-list-source-binding')


def _read(reader,field):
 start=reader.offset;reader.need(24,field)
 first={axis:reader.single(field+'.Item1.'+axis)for axis in'xyz'}
 second={axis:reader.single(field+'.Item2.'+axis)for axis in'xyz'}
 return dict(startOffset=start,endOffset=reader.offset,recordType=source.TYPE,Item1=first,Item2=second,
  fieldRanges=dict(Item1=[start,start+12],Item2=[start+12,start+24]))


def read(reader,field,cap):
 validate(cap);return _read(reader,field)


def read_list(reader,field,cap,value):
 validate_list(cap,value);start=reader.offset;count=reader.number('<i',field+'.count')
 if not -1<=count<=lists.LIMIT:raise ValueError(field+':vector-tuple-list-count-limit')
 reader.need(max(count,0)*24,field+'.elements')
 rows=[_read(reader,field+f'[{index}]')for index in range(max(count,0))]
 return dict(startOffset=start,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)

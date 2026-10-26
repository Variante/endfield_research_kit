"""Finite WayLane value/list cursor under freshly composed source capabilities.

WayLane's FF is the canonical adapter's zero16 default value. It is distinct
from the signed -1 collection header. Positive padding bytes are not serialized
and are left unobserved; array elements retain their UInt32 values exactly.
"""
from scripts.game_data.memorypack import leveldata_waylane_list_sources as source
from scripts.game_data.memorypack import leveldata_uint_array_sources as arrays


def validate_value(cap):
 if (not isinstance(cap,dict)or cap.get('typeName')!=source.TYPE
   or any(type(cap.get(k))is not int or cap[k]!=v for k,v in
    dict(memberCount=2,managedBytes=16,canonicalFFWireBytes=1,canonicalFFDefaultManagedBytes=16).items())
   or cap.get('referenceLaneOffsets')!=[8]or cap.get('paddingByteRanges')!=[[4,8]]
   or cap.get('profileAdmitted')is not True or cap.get('actualCallbackEqualsCanonicalRequired')is not True
   or cap.get('wholeGrammarAdmitted')is not False or cap.get('liveFormatterSelectionObserved')is not False):
  raise ValueError('currentWayLane.exact-padded-value-profile')
 array=cap.get('arrayCapability')
 if (not isinstance(array,dict)or array.get('typeName')!=arrays.TYPE or array.get('elementType')!='uint'
   or any(type(array.get(k))is not int or array[k]!=v for k,v in dict(countLimit=arrays.LIMIT,headerBytes=4,elementWireBytes=4).items())
   or array.get('countRange')!=[-1,arrays.LIMIT]
   or any(array.get(k)is not True for k in('elementValueType','nullable','positiveCountsAdmitted','rawBitsPreserved',
    'nestedDangerousMethodInfoRequired','normalTypedAllocationRequired','actualOwningSourceJoinProved','wholeGrammarAdmitted'))
   or any(array.get(k)is not False for k in('elementCallbackUsed','actualRuntimeSelectionObserved','parentFieldAdmitted','wholeOwnerAdmitted'))
   or array.get('actualSourceAuthentication')!='fresh-owning-caller'):
  raise ValueError('currentWayLane.exact-uint-array-source-profile')
 for key in('arrayReaderMethodDefinition','dangerousMethodDefinition','dangerousTargetRva'):
  if type(array.get(key))is not int or array[key]<(1 if key=='dangerousTargetRva'else 0):
   raise ValueError('currentWayLane.literal-array-source-binding')
 for key in('canonicalEntryPointerMatched','closedPointerEquivalenceProved'):
  if type(array.get(key))is not bool:raise ValueError('currentWayLane.literal-canonical-source-observation')
 if array['canonicalEntryPointerMatched']!=array['closedPointerEquivalenceProved']:
  raise ValueError('currentWayLane.canonical-source-observation-mismatch')


def validate_list(cap,value_cap):
 validate_value(value_cap)
 if (not isinstance(cap,dict)or cap.get('typeName')!=source.LIST or cap.get('elementType')!=source.TYPE
   or cap.get('elementCapability')!=source.VALUE_CAP or cap.get('elementWireBytes','missing')is not None
   or any(type(cap.get(k))is not int or cap[k]!=v for k,v in dict(countLimit=source.LIMIT,headerBytes=4,managedElementBytes=16).items())
   or cap.get('countRange')!=[-1,source.LIMIT]
   or any(cap.get(k)is not True for k in('nullable','positiveCountsAdmitted','initiallyNullListRequired',
    'finiteElementProfileAdmitted','actualCallbackEqualsCanonicalRequired','profileAdmitted'))
   or any(cap.get(k)is not False for k in('wholeGrammarAdmitted','liveFormatterSelectionObserved'))):
  raise ValueError('currentWayLane.exact-finite-list-profile')
 for key in('packableReaderMethodDefinition','packableReaderTargetRva'):
  if type(cap.get(key))is not int or cap[key]<(1 if key=='packableReaderTargetRva'else 0):
   raise ValueError('currentWayLane.literal-list-source-binding')


def _read(reader,field):
 start=reader.offset;marker=reader.number('<B',field+'.memberCount')
 if marker==255:
  return dict(startOffset=start,endOffset=reader.offset,recordType=source.TYPE,memberCount=marker,
   defaultValue=True,totalLane=0,laneDir=None,managedPadding=dict(byteRanges=[[4,8]],serialized=False,bits='zero'),fieldRanges={})
 if marker!=2:raise ValueError(field+':waylane-member-count')
 at=reader.offset;count=reader.number('<i',field+'.laneDir.count')
 if not -1<=count<=arrays.LIMIT:raise ValueError(field+'.laneDir:waylane-array-count-limit')
 reader.need(max(count,0)*4,field+'.laneDir.elements')
 rows=[reader.number('<I',field+f'.laneDir[{index}]')for index in range(max(count,0))]
 lane=dict(startOffset=at,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)
 at_total=reader.offset;total=reader.number('<i',field+'.totalLane')
 return dict(startOffset=start,endOffset=reader.offset,recordType=source.TYPE,memberCount=marker,defaultValue=False,
  totalLane=total,laneDir=lane,managedPadding=dict(byteRanges=[[4,8]],serialized=False,bits='unobserved'),
  fieldRanges=dict(laneDir=[at,at_total],totalLane=[at_total,reader.offset]))


def read(reader,field,cap):
 validate_value(cap);return _read(reader,field)


def read_list(reader,field,cap,value_cap):
 validate_list(cap,value_cap);start=reader.offset;count=reader.number('<i',field+'.count')
 if not -1<=count<=source.LIMIT:raise ValueError(field+':waylane-list-count-limit')
 reader.need(max(count,0),field+'.elements')
 rows=[_read(reader,field+f'[{index}]')for index in range(max(count,0))]
 return dict(startOffset=start,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)

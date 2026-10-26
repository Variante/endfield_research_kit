"""Finite Line wire projection under own current value and list source gates."""
from scripts.game_data.memorypack import leveldata_line_list_sources as source


def validate_value(cap):
 if (not isinstance(cap,dict)or cap.get('typeName')!=source.TYPE
  or any(type(cap.get(k))is not int or cap[k]!=v for k,v in dict(memberCount=2,managedBytes=12,
   positiveWireBytes=13,canonicalFFWireBytes=1,canonicalFFDefaultManagedBytes=12).items())
  or cap.get('referenceLaneOffsets')!=[]or cap.get('paddingByteRanges')!=[]
  or cap.get('serializedOrder')!=['length:Int32','startPos:Int2-raw8']
  or any(cap.get(k)is not True for k in('canonicalOriginalAdapterAdmitted','profileAdmitted','actualCallbackEqualsCanonicalRequired'))
  or any(cap.get(k)is not False for k in('wholeGrammarAdmitted','liveFormatterSelectionObserved'))):
  raise ValueError('currentLine.exact-nominal-value-profile')


def validate_list(cap,value_cap):
 validate_value(value_cap)
 if (not isinstance(cap,dict)or cap.get('typeName')!=source.LIST or cap.get('elementType')!=source.TYPE
  or cap.get('elementCapability')!=source.VALUE_CAP or cap.get('elementWireBytes','missing')is not None
  or any(type(cap.get(k))is not int or cap[k]!=v for k,v in dict(countLimit=source.LIMIT,headerBytes=4,managedElementBytes=12).items())
  or cap.get('countRange')!=[-1,source.LIMIT]
  or any(cap.get(k)is not True for k in('nullable','positiveCountsAdmitted','initiallyNullListRequired',
   'actualCallbackEqualsCanonicalRequired','full12BitsStored','profileAdmitted'))
  or any(cap.get(k)is not False for k in('growthAdmitted','wholeGrammarAdmitted','liveFormatterSelectionObserved'))):
  raise ValueError('currentLine.exact-finite-list-profile')
 for key in('packableReaderMethodDefinition','packableReaderTargetRva'):
  if type(cap.get(key))is not int or cap[key]<(1 if key=='packableReaderTargetRva'else 0):
   raise ValueError('currentLine.literal-list-source-binding')


def _read(reader,field):
 start=reader.offset;marker=reader.number('<B',field+'.memberCount')
 if marker==255:return dict(startOffset=start,endOffset=reader.offset,recordType=source.TYPE,memberCount=marker,
  defaultValue=True,length=0,startPos=dict(x=0,y=0),fieldRanges={})
 if marker!=2:raise ValueError(field+':line-member-count')
 length_at=reader.offset;length=reader.number('<i',field+'.length');position_at=reader.offset
 point={axis:reader.number('<i',field+'.startPos.'+axis)for axis in'xy'}
 return dict(startOffset=start,endOffset=reader.offset,recordType=source.TYPE,memberCount=marker,
  defaultValue=False,length=length,startPos=point,fieldRanges=dict(length=[length_at,position_at],startPos=[position_at,reader.offset]))


def read(reader,field,cap):
 validate_value(cap);return _read(reader,field)


def read_list(reader,field,cap,value_cap):
 validate_list(cap,value_cap);start=reader.offset;count=reader.number('<i',field+'.count')
 if not -1<=count<=source.LIMIT:raise ValueError(field+':line-list-count-limit')
 reader.need(max(count,0),field+'.elements')
 rows=[_read(reader,field+'['+str(index)+']')for index in range(max(count,0))]
 return dict(startOffset=start,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)

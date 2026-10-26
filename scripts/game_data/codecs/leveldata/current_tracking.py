"""Tracking raw and canonical value cursors behind separate exact source caps.

Every IEEE lane and enum bit is retained. A canonical FF yields a zero value;
a raw Bounds36 read has no header or null/default marker. These pure children
give no parent, runtime tracking meaning or physical EOF authority.
"""
import math
import struct

from scripts.game_data.memorypack import leveldata_tracking_components as profiles
from scripts.game_data.memorypack import leveldata_tracking_raw_sources as raw_source
from scripts.game_data.memorypack.leveldata_tracking_value_sources import BOUNDS,POINT,SPECS


def need(check,condition):
 if not condition:raise ValueError('currentTracking.'+check)


def validate_value(cap,type_name):
 need('finite-nominal-value',type_name in SPECS and isinstance(cap,dict))
 width=SPECS[type_name]['managedBytes'];count=len(SPECS[type_name]['order'])
 need('exact-canonical-value-profile',cap.get('typeName')==type_name and cap.get('capability')==profiles.VALUE_CAPS[type_name]
  and all(type(cap.get(k))is int and cap[k]==v for k,v in dict(memberCount=count,managedBytes=width,
   positiveWireBytes=37 if type_name==BOUNDS else 17,canonicalFFWireBytes=1,canonicalFFDefaultManagedBytes=width).items())
  and cap.get('serializedOrder')==[list(pair)for pair in SPECS[type_name]['order']]
  and(cap.get('enumBackingType')in('int','uint')if type_name==POINT else cap.get('enumBackingType')is None)
  and cap.get('referenceLaneOffsets')==[]and cap.get('paddingByteRanges')==[]
  and type(cap.get('canonicalCallbackTargetRva'))is int and cap['canonicalCallbackTargetRva']>0
  and all(cap.get(k)is True for k in('canonicalOriginalAdapterAdmitted','actualCallbackEqualsCanonicalRequired','rawBitsPreserved','profileAdmitted'))
  and all(cap.get(k)is False for k in('wholeGrammarAdmitted','liveFormatterSelectionObserved','parentFieldAdmitted','wholeOwnerAdmitted')))


def validate_raw(cap):
 need('exact-direct-raw36-profile',isinstance(cap,dict)and cap.get('schema')==raw_source.SCHEMA
  and cap.get('status')=='validated-conditional-tracking-bounds-raw36'and cap.get('typeName')==BOUNDS
  and cap.get('capability')==raw_source.CAPABILITY and all(type(cap.get(k))is int and cap[k]==36 for k in('wireBytes','managedBytes'))
  and type(cap.get('typeDefinition'))is int and cap['typeDefinition']>=0
  and type(cap.get('readerMethodDefinition'))is int and cap['readerMethodDefinition']>=0
  and type(cap.get('sourceTargetRva'))is int and cap['sourceTargetRva']>0
  and cap.get('sourceMethod')=='ReadUnmanaged'and cap.get('resultAbi')=='hidden-output-rcx'and cap.get('contextRegister')=='r8'
  and cap.get('referenceLaneOffsets')==[]and cap.get('paddingByteRanges')==[]
  and all(cap.get(k)is True for k in('actualSourceProved','allFourReaderUpdatesProved','entryRspRestored','allNonvolatilesRestored'))
  and all(cap.get(k)is False for k in('canonicalPointerIdentityClaimed','canonicalWrapperUsed','objectHeaderRead','parentFieldAdmitted','wholeOwnerAdmitted')))


def _vector(reader,field):
 start=reader.offset;reader.need(12,field);data=bytes(reader.data[start:start+12]);reader.offset+=12
 floats=struct.unpack('<fff',data)
 return dict(values={axis:value if math.isfinite(value)else None for axis,value in zip('xyz',floats,strict=True)},
  bits={axis:data[i:i+4].hex().upper()for axis,i in zip('xyz',(0,4,8),strict=True)},
  allFinite=all(math.isfinite(value)for value in floats))


def _zero_vector():return dict(values=dict(x=0.0,y=0.0,z=0.0),bits=dict(x='00000000',y='00000000',z='00000000'),allFinite=True)


def read_value(reader,field,type_name,cap):
 validate_value(cap,type_name);start=reader.offset;count=reader.number('<B',field+'.memberCount')
 need('canonical-member-count',count in(255,len(SPECS[type_name]['order'])))
 result=dict(startOffset=start,recordType=type_name,memberCount=count,defaultValue=count==255,fieldRanges={})
 if count==255:
  for member,declared in SPECS[type_name]['order']:
   result[member]=_zero_vector()if declared=='UnityEngine.Vector3'else dict(value=0,bits='00000000')
 else:
  for member,declared in SPECS[type_name]['order']:
   at=reader.offset;path=field+'.'+member
   if declared=='UnityEngine.Vector3':value=_vector(reader,path)
   else:
    fmt='<I'if cap['enumBackingType']=='uint'else'<i';value=reader.number(fmt,path)
    value=dict(value=value,bits=struct.pack(fmt,value).hex().upper())
   result[member]=value;result['fieldRanges'][member]=[at,reader.offset]
 result.update(endOffset=reader.offset,runtimeTrackingProved=False);return result


def read_raw_bounds(reader,field,cap):
 validate_raw(cap);start=reader.offset;reader.need(36,field)
 result=dict(startOffset=start,recordType=BOUNDS,wireBytes=36,wrapperFramingUsed=False,fieldRanges={})
 for member,declared,offset in SPECS[BOUNDS]['fields']:
  at=reader.offset;result[member]=_vector(reader,field+'.'+member);result['fieldRanges'][member]=[at,reader.offset]
 result.update(endOffset=reader.offset,runtimeTrackingProved=False);return result


def validate_list(cap,value_cap,type_name):
 from scripts.game_data.memorypack.leveldata_tracking_list_sources import LIMIT
 validate_value(value_cap,type_name)
 need('exact-canonical-value-list-profile',isinstance(cap,dict)
  and cap.get('typeName')=='System.Collections.Generic.List`1<'+type_name+'>'
  and cap.get('elementType')==type_name and cap.get('elementValueType')is True
  and cap.get('elementCapability')==profiles.VALUE_CAPS[type_name]
  and cap.get('elementWireBytes','missing')is None
  and all(type(cap.get(k))is int and cap[k]==v for k,v in dict(headerBytes=4,
   managedElementBytes=SPECS[type_name]['managedBytes'],countLimit=LIMIT).items())
  and cap.get('countRange')==[-1,LIMIT]
  and type(cap.get('packableReaderMethodDefinition'))is int and cap['packableReaderMethodDefinition']>=0
  and type(cap.get('packableReaderTargetRva'))is int and cap['packableReaderTargetRva']>0
  and type(cap.get('elementCanonicalCallbackTargetRva'))is int
  and cap['elementCanonicalCallbackTargetRva']==value_cap['canonicalCallbackTargetRva']
  and all(cap.get(k)is True for k in('nullable','positiveCountsAdmitted','initiallyNullListRequired',
   'actualCallbackEqualsCanonicalRequired','completeManagedValueStored','profileAdmitted'))
  and all(cap.get(k)is False for k in('growthAdmitted','wholeGrammarAdmitted','liveFormatterSelectionObserved')))


def read_list(reader,field,type_name,cap,value_cap):
 validate_list(cap,value_cap,type_name);start=reader.offset;reader.need(4,field+'.count')
 count=struct.unpack_from('<i',reader.data,reader.offset)[0]
 need('canonical-value-list-count-domain',-1<=count<=cap['countLimit'])
 reader.offset+=4;reader.need(max(count,0),field+'.elementHeaders')
 rows=[read_value(reader,field+'['+str(index)+']',type_name,value_cap)for index in range(max(count,0))]
 return dict(startOffset=start,endOffset=reader.offset,count=count,rows=None if count==-1 else rows,
  runtimeTrackingProved=False)

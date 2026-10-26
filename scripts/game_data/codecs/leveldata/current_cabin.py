"""Finite CabinSlotInfo value48 projection; padding is not a wire field."""
from scripts.game_data.memorypack.leveldata_cabin_value_sources import TYPE


def validate(cap):
 if (not isinstance(cap,dict)or cap.get('typeName')!=TYPE
   or any(type(cap.get(k))is not int or cap[k]!=v for k,v in dict(memberCount=4,managedBytes=48,positiveWireBytes=45,
    canonicalFFWireBytes=1,canonicalFFDefaultManagedBytes=48).items())
   or cap.get('referenceLaneOffsets')!=[]or cap.get('paddingByteRanges')!=[[44,48]]
   or any(cap.get(k)is not True for k in('canonicalAdapterAdmitted','finiteFloatProfile','actualCallbackEqualsCanonicalRequired','profileAdmitted'))
   or any(cap.get(k)is not False for k in('positivePaddingSerialized','wholeGrammarAdmitted','liveFormatterSelectionObserved'))):
  raise ValueError('currentCabin.exact-padded-nominal48-profile')


def read(reader,field,cap):
 validate(cap);start=reader.offset;marker=reader.number('<B',field+'.memberCount')
 if marker==255:
  return dict(startOffset=start,endOffset=reader.offset,recordType=TYPE,memberCount=255,defaultValue=True,logicId='0',
   boundSize=dict(x=0.0,y=0.0,z=0.0),position=dict(x=0.0,y=0.0,z=0.0),rotation=dict(x=0.0,y=0.0,z=0.0),
   managedPadding=dict(byteRanges=[[44,48]],serialized=False,bits='zero'),fieldRanges={})
 if marker!=4:raise ValueError(field+':cabin-member-count')
 out=dict(startOffset=start,recordType=TYPE,memberCount=4,defaultValue=False);ranges={}
 for member in('boundSize','logicId','position','rotation'):
  at=reader.offset;path=field+'.'+member
  out[member]=str(reader.number('<Q',path))if member=='logicId'else{axis:reader.single(path+'.'+axis)for axis in'xyz'}
  ranges[member]=[at,reader.offset]
 out.update(endOffset=reader.offset,fieldRanges=ranges,managedPadding=dict(byteRanges=[[44,48]],serialized=False,bits='unobserved'))
 return out

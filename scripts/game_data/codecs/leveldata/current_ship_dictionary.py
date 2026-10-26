"""Conditional serialized spaceship pairs; no stored-map or provider claim."""
from scripts.game_data.codecs.leveldata import current_cabin
from scripts.game_data.memorypack import leveldata_ship_dictionary_sources as source

CABIN=source.CABIN
TYPE='System.Collections.Generic.Dictionary`2<string,'+CABIN+'>'
UINT64_TYPE='System.Collections.Generic.Dictionary`2<string,ulong>'


def _validate_dictionary(cap,*,type_name,value_type,value_bytes):
 if (not isinstance(cap,dict)or cap.get('typeName')!=type_name or cap.get('keyType')!='string'or cap.get('valueType')!=value_type
   or any(type(cap.get(k))is not int or cap[k]!=v for k,v in
    dict(countLimit=source.LIMIT,headerBytes=4,valueManagedBytes=value_bytes).items())
   or cap.get('countRange')!=[-1,source.LIMIT]or cap.get('sourceWitnessClassArguments')!=['object',value_type]
   or any(cap.get(k)is not True for k in('positiveCountsAdmitted','nullable','initiallyNullOutputRequired',
    'keyCallbackEqualsPooledStringRequired','valueCallbackEqualsCanonicalRequired','actualCallbackEqualsSourceWitnessRequired',
    'actualClosedContextAndSourceBodyCompatibilityRequired','typedConstructorAndHelperCompatibilityRequired',
    'normalNonthrowingInsertRequired','profileAdmitted'))
   or any(cap.get(k)is not False for k in('closedPointerEquivalenceProved','storedMapSemanticsAdmitted',
    'runtimeProviderSelectionObserved','wholeGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted'))):
  raise ValueError('currentShipDictionary.exact-erased-source-string-value-profile:'+value_type)
 for key in('packableReaderMethodDefinition','packableReaderTargetRva'):
  if type(cap.get(key))is not int or cap[key]<(1 if key.endswith('TargetRva')else 0):
   raise ValueError('currentShipDictionary.literal-actual-parent-source')


def validate_cabin(cap):
 _validate_dictionary(cap,type_name=TYPE,value_type=CABIN,value_bytes=48)
 current_cabin.validate(cap.get('valueCapability'))


def validate_uint64(cap):
 _validate_dictionary(cap,type_name=UINT64_TYPE,value_type='ulong',value_bytes=8)
 value=cap.get('valueCapability')
 if (not isinstance(value,dict)or value.get('typeName')!='ulong'
  or any(type(value.get(k))is not int or value[k]!=v for k,v in dict(managedBytes=8,wireBytes=8,rawBits=64,headerBytes=0).items())
  or any(value.get(k)is not True for k in('actualCallbackEqualsCanonicalRequired','profileAdmitted','wholeGrammarAdmitted'))
  or any(value.get(k)is not False for k in('nullMarkerAdmitted','liveFormatterSelectionObserved'))):
  raise ValueError('currentShipDictionary.exact-UInt64-raw64-child-profile')


def read_cabin(reader,field,cap):
 validate_cabin(cap)
 return _read(reader,field,cap,value_profile='cabin')


def read_uint64(reader,field,cap):
 validate_uint64(cap)
 return _read(reader,field,cap,value_profile='uint64')


def _read(reader,field,cap,*,value_profile):
 start=reader.offset;count=reader.number('<i',field+'.count')
 if not -1<=count<=source.LIMIT:raise ValueError(field+':ship-dictionary-count-limit')
 reader.need(max(count,0)*(5 if value_profile=='cabin'else 12),field+'.entries')
 entries=[]
 for index in range(max(count,0)):
  name=field+f'[{index}]';at=reader.offset;key=reader.string(name+'.key');value_at=reader.offset
  value=current_cabin.read(reader,name+'.value',cap['valueCapability'])if value_profile=='cabin'else str(reader.number('<Q',name+'.value'))
  entries.append(dict(key=key,value=value,startOffset=at,endOffset=reader.offset,
   fieldRanges=dict(key=[at,value_at],value=[value_at,reader.offset])))
 return dict(startOffset=start,endOffset=reader.offset,count=count,entries=None if count==-1 else entries,
  storedMapSemanticsAdmitted=False,sourceWitnessClassArguments=cap['sourceWitnessClassArguments'],
  closedPointerEquivalenceProved=False,actualCallbackEqualsSourceWitnessRequired=True,
  actualClosedContextAndSourceBodyCompatibilityRequired=True,typedConstructorAndHelperCompatibilityRequired=True,
  normalNonthrowingInsertRequired=True,runtimeProviderSelectionObserved=False)

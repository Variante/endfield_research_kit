"""Ordered Rune raw16 pairs; padding is retained and map contents stay opaque."""
import struct

from scripts.game_data.memorypack import levelscript_rune_dictionary_components as profiles


def need(key,condition):
 if not condition:raise ValueError('currentRuneDictionary.'+key)


def validate(cap):
 need('exact-raw16-pair-framing',isinstance(cap,dict)and cap.get('schema')==profiles.CAP_SCHEMA
  and(cap.get('name'),cap.get('typeName'),cap.get('keyType'),cap.get('valueType'))==
   (profiles.CAPABILITY,profiles.source.TYPE,'ulong','int')
  and all(type(cap.get(k))is int and cap[k]==v for k,v in dict(headerBytes=4,pairWireBytes=16,keyRawKind=11,valueRawKind=8).items())
  and cap.get('keyByteRange')==[0,8]and cap.get('valueByteRange')==[8,12]and cap.get('transportedPaddingByteRange')==[12,16]
  and type(cap.get('countLimit'))is int and 3<=cap['countLimit']<=4096 and cap.get('countRange')==[-1,cap['countLimit']]
  and all(cap.get(k)is True for k in('nullable','rawBitsPreserved','paddingBytesPreserved','storedEntryFramingAdmitted',
   'initiallyNullOutputRequired','actualTypedFormatterSelectionRequired','internalKVMethodInfoCompatibilityRequired'))
  and all(cap.get(k)is False for k in('individualKeyValueCallbacksUsed','hashMapContentsAdmitted','duplicateSemanticsAdmitted',
   'liveFormatterSelectionObserved','parentFieldAdmitted','wholeOwnerAdmitted'))
  and type(cap.get('packableReaderMethodDefinition'))is int and cap['packableReaderMethodDefinition']>=0
  and type(cap.get('packableReaderTargetRva'))is int and cap['packableReaderTargetRva']>0)


def read(reader,field,cap,*,budget=None):
 validate(cap);start=reader.offset;reader.need(4,field+'.count');count=struct.unpack_from('<i',reader.data,start)[0]
 need('bounded-signed-count',-1<=count<=cap['countLimit']);reader.need(4+16*max(0,count),field+'.rawPairs')
 if budget is None:budget=dict(nodes=16384,elements=16384)
 need('shared-budget',isinstance(budget,dict)and all(type(budget.get(k))is int and 0<=budget[k]<=16384 for k in('nodes','elements'))
  and budget['nodes']>=1 and budget['elements']>=max(0,count))
 budget['nodes']-=1;budget['elements']-=max(0,count);reader.offset+=4;entries=None
 if count>=0:
  entries=[]
  for index in range(count):
   raw=bytes(reader.data[reader.offset:reader.offset+16]);reader.offset+=16
   entries.append(dict(key=str(int.from_bytes(raw[:8],'little')),value=int.from_bytes(raw[8:12],'little',signed=True),
    rawHex=raw.hex().upper(),transportedPaddingHex=raw[12:16].hex().upper()))
 return dict(typeName=profiles.source.TYPE,startOffset=start,endOffset=reader.offset,count=count,entries=entries,
  hashMapContentsAdmitted=False,duplicateSemanticsAdmitted=False)

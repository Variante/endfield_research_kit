"""Exact Rune array64 framing; Boolean storage bytes remain unnormalized."""
import struct

from scripts.game_data.memorypack import levelscript_rune_array_components as profiles


def need(check,condition):
 if not condition:raise ValueError('currentRuneArray.'+check)


def validate(cap):
 need('explicit-primitive-array',isinstance(cap,dict)and cap.get('elementType')in('int','bool'))
 element=cap['elementType'];width=4 if element=='int'else 1
 need('exact-owned-array64-profile',cap.get('typeName')==element+'[]'
  and all(type(cap.get(k))is int and cap[k]==v for k,v in dict(headerBytes=4,elementWireBytes=width,countLimit=64).items())
  and cap.get('countRange')==[-1,64]and type(cap.get('readerMethodDefinition'))is int and cap['readerMethodDefinition']>=0
  and type(cap.get('sourceTargetRva'))is int and cap['sourceTargetRva']>0
  and all(cap.get(k)is True for k in('nullable','positiveCountsAdmitted','rawBitsPreserved','wholeGrammarAdmitted'))
  and all(cap.get(k)is False for k in('booleanNormalizationClaimed','elementCallbackUsed','parentFieldAdmitted','wholeOwnerAdmitted')))


def read(reader,field,cap,*,budget=None):
 validate(cap);start=reader.offset;reader.need(4,field+'.count');count=struct.unpack_from('<i',reader.data,start)[0]
 width=cap['elementWireBytes'];need('bounded-signed-count',-1<=count<=64)
 reader.need(4+width*max(0,count),field+'.payload')
 if budget is None:budget=dict(nodes=16384,elements=16384)
 need('shared-budget',isinstance(budget,dict)and all(type(budget.get(k))is int and 0<=budget[k]<=16384 for k in('nodes','elements'))
  and budget['nodes']>=1 and budget['elements']>=max(0,count))
 budget['nodes']-=1;budget['elements']-=max(0,count);reader.offset+=4;rows=None
 if count>=0:
  rows=[]
  for index in range(count):
   raw=bytes(reader.data[reader.offset:reader.offset+width]);reader.offset+=width
   rows.append(dict(rawHex=raw.hex().upper(),storedValue=int.from_bytes(raw,'little',signed=cap['elementType']=='int')))
 return dict(typeName=cap['typeName'],startOffset=start,endOffset=reader.offset,count=count,values=rows,
  rawBooleanBitsPreserved=cap['elementType']=='bool')

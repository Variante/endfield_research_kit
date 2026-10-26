"""Bounded authored gait/Single entries, retaining raw bits and duplicates."""
import struct
from scripts.game_data.memorypack import skill_gait_dictionary_sources as source


def need(key,condition):
 if not condition:raise ValueError('skillGaitDictionaryCodec.'+key)


def require_capability(cap):
 need('literal-wire-integers',all(type(cap.get(k))is int for k in('referenceBytes','nullMarker','positiveHeader','countLimit','minimumCount','keyWireBytes','valueWireBytes')))
 need('own-static-out-grammar',cap.get('typeName')==source.TYPE and cap.get('keyType')==source.KEY and cap.get('valueType')=='float'
  and cap.get('resultAbi')=='void-byref-reference8'and cap.get('referenceBytes')==8
  and all(cap.get(k)is True for k in('wholeGrammarAdmitted','staticOutReferenceAdmitted','nullable','orderedEntriesPreserved','duplicateKeysPreserved','initiallyNullOutputRequired'))
  and all(cap.get(k)is False for k in('ordinaryOriginalReadValueAdmitted','nativePositiveHeaderOneEnforced','numericConversion','actualRuntimeSelectionObserved'))
  and(cap.get('nullMarker'),cap.get('positiveHeader'),cap.get('countLimit'),cap.get('minimumCount'),cap.get('keyWireBytes'),cap.get('valueWireBytes'))==(255,1,4096,0,4,4)
  and cap.get('countEncoding')=='signed-int32'and type(cap.get('staticReaderMethodDefinition'))is int
  and type(cap.get('staticReaderTargetRva'))is int and cap['staticReaderTargetRva']>0
  and bool(cap.get('conditions')))
 return cap


def read(reader,depth=0):
 need('depth',type(depth)is int and 0<=depth<=64);r=reader;cap=require_capability(r.operation.child(source.CAPABILITY))
 start=r.pos;null=r.peek()==255;entries=[]
 if null:r.take(1,source.CAPABILITY+'.null')
 else:
  need('authored-header-one',r.peek()==cap['positiveHeader']);need('complete-count',r.pos+5<=r.limit)
  count=struct.unpack_from('<i',r.data,r.pos+1)[0]
  need('nonnegative-bounded-count',0<=count<=cap['countLimit'])
  need('complete-entry-bytes',r.pos+5+8*count<=r.limit)
  r.take(5,source.CAPABILITY+'.header-count')
  for _ in range(count):
   at=r.pos;key=bytes(r.data[at:at+4]).hex();value=bytes(r.data[at+4:at+8]).hex();r.take(8,source.CAPABILITY+'.entry')
   entries.append(dict(start=at,end=r.pos,keyRawHex=key,valueRawHex=value))
 row=dict(kind=source.CAPABILITY,start=start,end=r.pos,isNull=null,entries=entries)
 if not null:row['count']=count
 r.records.append(row);return row

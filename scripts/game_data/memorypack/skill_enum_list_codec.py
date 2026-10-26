"""Conditionally selected nominal enum lists, preserving every raw DWORD."""
import struct
from scripts.game_data.memorypack.enum_list_native_sources import ENUM_TYPES


def need(key,condition):
 if not condition:raise ValueError('skillEnumListCodec.'+key)


def list_capability(name):return 'skill-enum-list:'+name
def element_capability(name):return 'skill-enum-callback:'+name


def require_capability(cap,element,*,name):
 need('finite-nominal-domain',name in ENUM_TYPES)
 need('own-conditional-list',cap.get('schema')=='endfield.nominal-enum-list-sources.v1'
  and cap.get('status')=='validated-conditional-enum-list'and cap.get('closedListType')=='System.Collections.Generic.List`1<'+name+'>'
  and cap.get('elementType')==name and cap.get('elementCapability')==element_capability(name)
  and cap.get('elementValueType')is True and cap.get('nullable')is True
  and all(cap.get(k)is True for k in('positiveCountsAdmitted','elementGrammarAdmitted','rawBitsPreserved'))
  and all(type(cap.get(k))is int for k in('countLimit','headerBytes','signedCountBits','nullCount','elementWireBytes','elementTypeDefinition','packableReaderMethodDefinition','packableReaderTargetRva'))
  and(cap['countLimit'],cap['headerBytes'],cap['signedCountBits'],cap['nullCount'],cap['elementWireBytes'])==(10000,4,32,-1,4)
  and cap.get('collectionCounts')==[-1,0]and all(type(n)is int for n in cap['collectionCounts'])
  and cap['packableReaderMethodDefinition']>=0 and cap['packableReaderTargetRva']>0
  and cap.get('actualRuntimeSelectionObserved')is False and cap.get('parentFieldAdmitted')is False and cap.get('wholeOwnerAdmitted')is False
  and isinstance(cap.get('conditions'),list)and bool(cap['conditions'])and all(type(c)is str and c for c in cap['conditions']))
 need('independent-own-nominal-callback',element==cap.get('elementCallback')and element.get('nativeInputs')==cap.get('nativeInputs')
  and element.get('schema')=='endfield.enum-nominal-callback-sources.v1'and element.get('status')=='validated-conditional-callback'
  and element.get('typeName')==name and element.get('typeDefinition')==cap['elementTypeDefinition']
  and type(element.get('wireBytes'))is int and element['wireBytes']==4 and type(element.get('callbackSlot'))is int and element['callbackSlot']==5
  and element.get('readerByref')is True and element.get('outputByref')is True
  and element.get('formatterType')=='MemoryPack.Formatters.UnmanagedFormatter`1'
  and type(element.get('callbackTargetRva'))is int and element['callbackTargetRva']>0
  and element.get('actualRuntimeSelectionObserved')is False and element.get('unconditionalCallbackSelectionProved')is False
  and element.get('parentOrCollectionGrammarAdmitted')is False and isinstance(element.get('conditions'),list)
  and len(element['conditions'])==6 and all(type(c)is str and c for c in element['conditions']))
 return cap


def read(reader,capability,depth=0):
 need('depth',type(depth)is int and 0<=depth<=64)
 names=[name for name in ENUM_TYPES if capability==list_capability(name)];need('own-list-capability',len(names)==1);name,=names
 r=reader;cap=require_capability(r.operation.child(capability),r.operation.child(element_capability(name)),name=name)
 need('complete-count',r.pos+4<=r.limit);count=struct.unpack_from('<i',r.data,r.pos)[0]
 need('bounded-signed-count',-1<=count<=cap['countLimit']);need('complete-entry-bytes',r.pos+4+4*max(0,count)<=r.limit)
 start=r.pos;r.take(4,capability+'.count');entries=[]
 for _ in range(max(0,count)):
  at=r.pos;bits=bytes(r.data[at:at+4]).hex();r.take(4,capability+'.enum-bits');entries.append(dict(start=at,end=r.pos,rawHex=bits))
 row=dict(kind=capability,start=start,end=r.pos,count=count,isNull=count==-1,elementType=name,entries=entries)
 r.records.append(row);return row

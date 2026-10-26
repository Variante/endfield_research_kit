"""Finite TrackingRoute cursor with separately gated raw/value/reference children."""
import struct

from scripts.game_data.memorypack import leveldata_tracking_route_sources as source
from scripts.game_data.memorypack import leveldata_tracking_components as values,leveldata_tracking_raw_sources as raw
from scripts.game_data.memorypack.leveldata_tracking_value_sources import BOUNDS,POINT
from scripts.game_data.codecs.leveldata import current_tracking as tracking,current_leaf_record as leaf


def need(check,condition):
 if not condition:raise ValueError('currentTrackingRoute.'+check)


def validate_rectangle_list(cap,element):
 leaf.validate(source.RECTANGLE,element)
 need('exact-ordinary-Rectangle-list',isinstance(cap,dict)and cap.get('typeName')==source.LIST(source.RECTANGLE)
  and cap.get('elementType')==cap.get('elementCapability')==source.RECTANGLE and cap.get('elementValueType')is False
  and cap.get('elementWireBytes','absent')is None and cap.get('countRange')==[-1,source.LIMIT]
  and all(type(n)is int for n in cap['countRange'])
  and all(type(cap.get(k))is int and cap[k]==v for k,v in dict(countLimit=source.LIMIT,headerBytes=4).items())
  and all(type(cap.get(k))is int and cap[k]>0 for k in('readerMethodDefinition','sourceTargetRva',
   'referenceReaderMethodDefinition','referenceReaderTargetRva'))
  and all(cap.get(k)is True for k in('nullable','positiveCountsAdmitted','elementGrammarAdmitted','initiallyNullListRequired',
   'actualCallbackEqualsProvedChildRequired','profileAdmitted'))
  and all(cap.get(k)is False for k in('wholeGrammarAdmitted','liveFormatterSelectionObserved','parentFieldAdmitted','wholeOwnerAdmitted')))


def validate(cap):
 need('exact-finite-route',isinstance(cap,dict)and cap.get('typeName')==source.TYPE and cap.get('capability')==source.CAPABILITY
  and all(type(cap.get(k))is int and cap[k]==v for k,v in dict(memberCount=8,countLimit=source.LIMIT,nodeLimit=source.NODE_LIMIT).items())
  and all(cap.get(k)is True for k in('nullAdmitted','positiveAdmitted','ordinaryAdapterAdmitted','profileAdmitted',
   'actualCallbackEqualsProvedChildRequired','initiallyNullListsRequired','canonicalBooleanProfile',
   'finiteRectangleFloatProfile','trackingRawBitsPreserved'))
  and all(cap.get(k)is False for k in('wholeGrammarAdmitted','liveFormatterSelectionObserved','parentFieldAdmitted','wholeOwnerAdmitted','runtimeTrackingProved'))
  and all(type(cap.get(k))is int and cap[k]>0 for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')))
 children=cap.get('trackingChildren',{})
 need('exact-five-independent-tracking-scopes',type(children)is dict and set(children)==
  {raw.CAPABILITY,*values.VALUE_CAPS.values(),*values.LIST_CAPS.values()})
 tracking.validate_raw(children[raw.CAPABILITY])
 for name in(BOUNDS,POINT):tracking.validate_list(children[values.LIST_CAPS[name]],children[values.VALUE_CAPS[name]],name)
 validate_rectangle_list(cap.get('rectangleCollection'),cap.get('rectangle'))
 program=cap.get('program');source.bind_program(dict(wrappedType=source.TYPE,
  orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k,c in source.PLAN]),program,[])
 for row,(index,name)in zip(program['childBindings'],((2,BOUNDS),(5,POINT),(6,source.RECTANGLE)),strict=True):
  if name==source.RECTANGLE:
   collection=cap['rectangleCollection'];definition=collection['readerMethodDefinition'];target=collection['sourceTargetRva']
  else:
   collection=children[values.LIST_CAPS[name]];definition=collection['packableReaderMethodDefinition'];target=collection['packableReaderTargetRva']
  need('complete-actual-list-field-identity:'+str(index),type(row.get('readerMethodDefinition'))is int
   and row['readerMethodDefinition']==definition and type(row.get('sourceTargetRva'))is int and row['sourceTargetRva']==target
   and row.get('elementCapability')==collection['elementCapability']
   and row.get('initiallyNullListRequired')is True and row.get('actualCallbackEqualsProvedChildRequired')is True)


def _list_count(reader,field,budget):
 reader.need(4,field+'.count');count=struct.unpack_from('<i',reader.data,reader.offset)[0]
 need('list-count-domain',-1<=count<=source.LIMIT)
 need('node-resource-bound',max(count,0)<=budget[0]);budget[0]-=max(count,0)
 return count


def _rectangle_list(reader,field,cap,budget):
 start=reader.offset;count=_list_count(reader,field,budget);reader.offset+=4
 reader.need(max(count,0),field+'.elementHeaders');rows=[]
 for index in range(max(count,0)):
  record=leaf.read(reader,field+'['+str(index)+']',source.RECTANGLE,cap['rectangle'])
  if record is not None:
   bits={}
   for name,(at,end)in record['fieldRanges'].items():
    data=bytes(reader.data[at:end]);bits[name]=[data[i:i+4].hex().upper()for i in range(0,len(data),4)]
   record['rawFloatBits']=bits
  rows.append(record)
 return dict(startOffset=start,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)


def read(reader,field,cap,*,budget=None):
 """Consume one Route only; shared callers can supply one bounded node budget."""
 validate(cap)
 if budget is None:budget=[source.NODE_LIMIT]
 need('literal-shared-budget',isinstance(budget,list)and len(budget)==1 and type(budget[0])is int and 0<budget[0]<=source.NODE_LIMIT)
 budget[0]-=1;start=reader.offset;marker=reader.number('<B',field+'.memberCount')
 if marker==255:return None
 need('exact-route-member-count',marker==8)
 out=dict(startOffset=start,recordType=source.TYPE,memberCount=8);spans={};children=cap['trackingChildren']
 for name,declared,kind,key in source.PLAN:
  path=field+'.'+name;at=reader.offset
  if kind=='tracking-bounds-raw36':value=tracking.read_raw_bounds(reader,path,children[raw.CAPABILITY])
  elif kind=='bool-byte':value=reader.boolean(path)
  elif kind in('tracking-bounds-list','tracking-point-list'):
   element=BOUNDS if kind=='tracking-bounds-list'else POINT
   _list_count(reader,path,budget)
   value=tracking.read_list(reader,path,element,children[key],children[values.VALUE_CAPS[element]])
  elif kind=='tracking-rectangle-list':value=_rectangle_list(reader,path,cap,budget)
  elif kind=='scalar32':value=reader.number('<i',path)
  else:raise ValueError(path+':closed-tracking-route-operation')
  out[name]=value;spans[name]=[at,reader.offset]
 out.update(endOffset=reader.offset,fieldRanges=spans,runtimeTrackingProved=False)
 return out

"""Finite current MissionArea cursor with an explicit direct raw44 child."""
import math
import struct

from scripts.game_data.memorypack import leveldata_mission_area_sources as source
from scripts.game_data.codecs.leveldata import current_tracking_route as route


def need(check,condition):
 if not condition:raise ValueError('currentMissionArea.'+check)


def validate_raw(cap):
 need('exact-direct-raw44-child',isinstance(cap,dict)and cap.get('typeName')==source.raw.TYPE
  and cap.get('capability')==source.raw.CAP and all(type(cap.get(k))is int and cap[k]==44 for k in('managedBytes','wireBytes'))
  and cap.get('physicalFields')==[list(row)for row in source.raw.FIELDS]
  and cap.get('enumType')==source.raw.ENUM and cap.get('enumBacking')in('int','uint')
  and cap.get('resultAbi')=='hidden-local'and cap.get('contextRegister')=='r8'
  and all(type(cap.get(k))is int and cap[k]>0 for k in('readerMethodDefinition','sourceTargetRva'))
  and cap.get('referenceLaneOffsets')==cap.get('paddingByteRanges')==[]
  and all(cap.get(k)is True for k in('actualSourceProved','rawBitsPreserved','profileAdmitted'))
  and all(cap.get(k)is False for k in('objectHeaderRead','canonicalWrapperUsed','actualCallbackSelectionRequired',
   'wholeGrammarAdmitted','liveFormatterSelectionObserved')))


def validate(cap):
 need('exact-finite-MissionArea-graph',isinstance(cap,dict)and cap.get('typeName')==source.LIST
  and cap.get('recordType')==source.TYPE and cap.get('capability')==source.CAP
  and all(type(cap.get(k))is int and cap[k]==v for k,v in dict(memberCount=8,countLimit=source.LIMIT,nodeLimit=source.NODE_LIMIT,headerBytes=4).items())
  and all(cap.get(k)is True for k in('profileAdmitted','nullAdmitted','positiveAdmitted','ordinaryAdapterAdmitted',
   'initiallyNullListsRequired','actualCallbackEqualsProvedChildRequired','canonicalBooleanProfile',
   'rawTriggerBitsPreserved','finiteTrackingOffsetProfile'))
  and all(cap.get(k)is False for k in('wholeGrammarAdmitted','liveFormatterSelectionObserved','runtimeMissionAreaBehaviorProved')))
 validate_raw(cap.get('rawShape'));route.validate(cap.get('trackingRoute'))
 source.bind_program(dict(wrappedType=source.TYPE,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in source.PLAN]),cap.get('program'),[])
 binding=cap['program']['childBindings'][0];child=cap['trackingRoute']
 need('same-own-actual-Route-field',type(binding.get('readerMethodDefinition'))is int
  and binding['readerMethodDefinition']==child['referenceReaderMethodDefinition']
  and type(binding.get('sourceTargetRva'))is int and binding['sourceTargetRva']==child['referenceReaderTargetRva']
  and binding.get('actualCallbackEqualsProvedChildRequired')is True)
 parent=cap.get('parentBinding',{})
 need('exact-actual-MissionArea-host-parent',all(parent.get(k)==v for k,v in dict(ownerType=source.ROOT,
  fieldName=source.FIELD,typeName=source.LIST,elementType=source.TYPE,capability=source.CAP).items())
  and all(type(parent.get(k))is int and parent[k]>0 for k in('readerMethodDefinition','sourceTargetRva'))
  and parent.get('initiallyNullListRequired')is True and parent.get('actualCallbackEqualsProvedChildRequired')is True)


def _float_bits(reader,field):
 start=reader.offset;reader.need(4,field);raw=bytes(reader.data[start:start+4]);reader.offset+=4
 value=struct.unpack('<f',raw)[0]
 return dict(value=value if math.isfinite(value)else None,bits=raw.hex().upper(),finite=math.isfinite(value))


def read_raw(reader,field,cap):
 validate_raw(cap);start=reader.offset;reader.need(44,field)
 enum=reader.number('<i'if cap['enumBacking']=='int'else'<I',field+'.type')
 out=dict(startOffset=start,recordType=source.raw.TYPE,wireBytes=44,wrapperFramingUsed=False,
  type=dict(value=enum,bits=bytes(reader.data[start:start+4]).hex().upper()))
 for name in('position','eulerAngles','size'):out[name]={axis:_float_bits(reader,field+'.'+name+'.'+axis)for axis in'xyz'}
 out['radius']=_float_bits(reader,field+'.radius');out['endOffset']=reader.offset;return out


def _record(reader,field,cap,budget):
 need('node-limit',budget[0]>0);budget[0]-=1;start=reader.offset;marker=reader.number('<B',field+'.memberCount')
 if marker==255:return None
 need('member-count',marker==8);out=dict(startOffset=start,recordType=source.TYPE,memberCount=marker);spans={}
 for member,declared,kind in source.PLAN:
  at=reader.offset;path=field+'.'+member
  if kind=='bool-byte':value=reader.boolean(path)
  elif kind=='byte-payload':value=reader.string(path)
  elif kind=='trigger-shape-raw44':value=read_raw(reader,path,cap['rawShape'])
  elif kind=='scalar64-bits':value=str(reader.number('<Q',path))
  elif kind=='unity-vector3-raw12':value={axis:reader.single(path+'.'+axis)for axis in'xyz'}
  elif kind=='tracking-route-record':value=route.read(reader,path,cap['trackingRoute'],budget=budget)
  else:raise ValueError(path+':closed-MissionArea-operation')
  out[member]=value;spans[member]=[at,reader.offset]
 out.update(endOffset=reader.offset,fieldRanges=spans);return out


def read(reader,field,cap):
 validate(cap);state=getattr(reader,'_current_mission_area_budget',None)
 if state is None:state=(cap,[source.NODE_LIMIT]);reader._current_mission_area_budget=state
 else:need('same-graph-budget',state[0]is cap)
 start=reader.offset;reader.need(4,field+'.count');count=struct.unpack_from('<i',reader.data,reader.offset)[0]
 need('list-count',-1<=count<=source.LIMIT);need('list-node-limit',max(count,0)<=state[1][0]);reader.offset+=4
 reader.need(max(count,0),field+'.elementHeaders')
 rows=[_record(reader,field+'['+str(i)+']',cap,state[1])for i in range(max(count,0))]
 return dict(startOffset=start,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)


def conditional_sources(cap):
 validate(cap);tracking=cap['trackingRoute']
 rows=[dict(typeName=source.LIST,countLimit=source.LIMIT,initiallyNullListRequired=True,
  actualCallbackEqualsProvedChildRequired=True,runtimeMissionAreaBehaviorProved=False,runtimeFormatterSelectionObserved=False),
  dict(typeName=source.raw.TYPE,wireBytes=44,rawBitsPreserved=True,objectHeaderRead=False,
   canonicalWrapperUsed=False,actualCallbackSelectionRequired=False),
  dict(typeName=tracking['typeName'],actualCallbackEqualsProvedChildRequired=True,initiallyNullListsRequired=True,
   runtimeTrackingProved=False,runtimeFormatterSelectionObserved=False)]
 for child in tracking['trackingChildren'].values():
  row=dict(typeName=child['typeName'],rawBitsPreserved=True,runtimeFormatterSelectionObserved=False)
  for key in('managedBytes','wireBytes','positiveWireBytes','nullWireBytes','countLimit','initiallyNullListRequired',
    'actualCallbackEqualsCanonicalRequired','actualCallbackEqualsProvedChildRequired','closedPointerEquivalenceProved',
    'objectHeaderRead','canonicalWrapperUsed','actualCallbackSelectionRequired'):
   if key in child:row[key]=child[key]
  rows.append(row)
 rows.append(dict(typeName=tracking['rectangleCollection']['typeName'],countLimit=source.LIMIT,
  initiallyNullListRequired=True,actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False))
 return rows

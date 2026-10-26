"""Finite stored waypoints; authored links do not establish navigation use."""
from scripts.game_data.memorypack import leveldata_waypoint_sources as source
from scripts.game_data.codecs.leveldata import current_waylane


def validate(cap):
 if (not isinstance(cap,dict)or cap.get('typeName')!=source.TYPE
   or type(cap.get('memberCount'))is not int or cap['memberCount']!=len(source.PLAN)
   or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','finiteFloatProfile',
    'ordinaryAdapterAdmitted','actualCallbackEqualsProvedChildRequired'))
   or any(cap.get(k)is not False for k in('wholeGrammarAdmitted','liveFormatterSelectionObserved'))):
  raise ValueError('currentWayPoint.exact-finite-profile')
 declared=dict(wrappedType=source.TYPE,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in source.PLAN])
 source.bind_program(declared,cap.get('program'),[])
 children=cap.get('childCapabilities',{})
 if not isinstance(children,dict)or set(children)!={source.lanes.CAP,source.lanes.VALUE_CAP,source.ULONG_CAP}:
  raise ValueError('currentWayPoint.exact-child-set')
 current_waylane.validate_list(children[source.lanes.CAP],children[source.lanes.VALUE_CAP])
 for binding in cap['program']['childBindings']:
  key=binding['capability']
  if (type(binding.get('readerMethodDefinition'))is not int or binding['readerMethodDefinition']<0
    or type(binding.get('sourceTargetRva'))is not int or binding['sourceTargetRva']<=0
    or type(binding.get('countLimit'))is not int or binding['countLimit']!=source.LIMIT):
   raise ValueError('currentWayPoint.literal-list-binding')
  join=dict(fieldName=binding['fieldName'],typeName=binding['typeName'],sourceTargetRva=binding['sourceTargetRva'],
   typedRequest=dict(methodName='ReadPackable',methodArguments=[binding['typeName']],methodSpec=[binding['readerMethodDefinition']]))
  actual=source.bind_collection({},join,dict(nativeInputs={},capabilities=children),key)
  if binding!=actual:raise ValueError('currentWayPoint.complete-list-binding')
 parent=cap.get('parentBinding',{})
 if (any(parent.get(k)!=v for k,v in dict(ownerType='Beyond.Gameplay.LevelData',fieldName='worldWayPointData',typeName=source.LIST,
   capability=source.CAP,countLimit=source.LIMIT).items())or type(parent.get('countLimit'))is not int
   or type(parent.get('readerMethodDefinition'))is not int or parent['readerMethodDefinition']<0
   or type(parent.get('sourceTargetRva'))is not int or parent['sourceTargetRva']<=0
   or parent.get('actualCallbackEqualsProvedChildRequired')is not True):raise ValueError('currentWayPoint.exact-host-list-parent')


def read(reader,field,cap):
 validate(cap);start=reader.offset;marker=reader.number('<B',field+'.memberCount')
 if marker==255:return None
 if marker!=len(source.PLAN):raise ValueError(field+':waypoint-member-count')
 out=dict(startOffset=start,recordType=source.TYPE,memberCount=marker);ranges={};children=cap['childCapabilities']
 for member,declared,kind in source.PLAN:
  at=reader.offset;path=field+'.'+member
  if kind=='scalar32':value=reader.number('<i',path)
  elif kind=='bool-byte':value=reader.boolean(path)
  elif kind=='scalar64-bits':value=str(reader.number('<Q',path))
  elif kind=='unity-vector3-raw12':value={axis:reader.single(path+'.'+axis)for axis in'xyz'}
  elif kind=='waylane-list':value=current_waylane.read_list(reader,path,children[source.lanes.CAP],children[source.lanes.VALUE_CAP])
  elif kind=='uint64-list':
   count=reader.number('<i',path+'.count')
   if not -1<=count<=source.LIMIT:raise ValueError(path+':waypoint-count-limit')
   reader.need(max(count,0)*8,path+'.elements');rows=[str(reader.number('<Q',path+f'[{index}]'))for index in range(max(count,0))]
   value=dict(startOffset=at,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)
  else:raise ValueError(path+':closed-waypoint-operation')
  out[member]=value;ranges[member]=[at,reader.offset]
 out.update(endOffset=reader.offset,fieldRanges=ranges);return out

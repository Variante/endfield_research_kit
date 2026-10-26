"""Current pooled Core Patrol syntax; no controller/conversion/playback inference."""
from scripts.game_data.memorypack import leveldata_core_patrol_sources as source


def validate(cap):
 if(not isinstance(cap,dict)or(cap.get('typeName'),cap.get('capability'))!=(source.ROOT,source.CAP)
  or any(type(cap.get(k))is not int or cap[k]!=v for k,v in dict(countLimit=source.LIMIT,nodeLimit=source.NODE_LIMIT).items())
  or any(cap.get(k)is not True for k in('profileAdmitted','finiteFloatProfile','actualCallbackEqualsProvedChildRequired','initiallyNullListsRequired'))
  or any(cap.get(k)is not False for k in('wholeGrammarAdmitted','controllerConversionProved','actionDispatchProved','checkpointProducerProved','runtimeFormatterSelectionObserved'))):
  raise ValueError('currentCorePatrol.exact-conditional-profile')
 source.validate_subaction_layout(cap.get('subActionLayout'))
 records=cap.get('records',{});collections=cap.get('collections',{})
 if not isinstance(records,dict)or set(records)!=set(source.PLANS)or not isinstance(collections,dict)or set(collections)!={source.list_key(n)for n in source.COLLECTIONS}:
  raise ValueError('currentCorePatrol.exact-own-record-and-list-set')
 for name,plan in source.PLANS.items():
  record=records[name]
  if(not isinstance(record,dict)or record.get('typeName')!=name or type(record.get('memberCount'))is not int or record['memberCount']!=len(plan)
   or any(record.get(k)is not True for k in('nullAdmitted','positiveAdmitted','ordinaryAdapterAdmitted','profileAdmitted','actualCallbackEqualsProvedChildRequired'))
   or any(record.get(k)is not False for k in('wholeGrammarAdmitted','runtimeFormatterSelectionObserved'))):raise ValueError('currentCorePatrol.exact-record-profile')
  source.bind_program(name,dict(wrappedType=name,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in plan]),record.get('program'),[])
  enums=record.get('enumBackings',{});wanted={n:t for n,t,k in plan if k=='scalar32'and t!='int'}
  if not isinstance(enums,dict)or set(enums)!=set(wanted):raise ValueError('currentCorePatrol.exact-enum-set')
  for field,typename in wanted.items():
   enum=enums[field]
   if(enum.get('typeName')!=typename or enum.get('backing')not in('int','uint')or enum.get('field')!=[typename,enum['backing'],16]):
    raise ValueError('currentCorePatrol.exact-nominal-enum')
  for binding in record['program']['childBindings']:
   join=dict(fieldName=binding['fieldName'],typeName=binding['typeName'],sourceTargetRva=binding.get('sourceTargetRva'),
    typedRequest=dict(methodName='ReadPackable',methodArguments=[binding['typeName']],methodSpec=[binding.get('readerMethodDefinition')]))
   if binding!=source.bind_collection({},join,dict(nativeInputs={},capabilities=collections),binding['capability']):
    raise ValueError('currentCorePatrol.exact-actual-child-binding')
 parent=cap.get('parentBinding',{})
 if(any(parent.get(k)!=v for k,v in dict(ownerType='Beyond.Gameplay.LevelData',fieldName='patrols',typeName=source.LIST(source.ROOT),capability=source.CAP,
  countLimit=source.LIMIT,initiallyNullListRequired=True,actualCallbackEqualsProvedChildRequired=True).items())
  or type(parent.get('countLimit'))is not int or type(parent.get('readerMethodDefinition'))is not int or parent['readerMethodDefinition']<0
  or type(parent.get('sourceTargetRva'))is not int or parent['sourceTargetRva']<=0):raise ValueError('currentCorePatrol.exact-current-host-parent')


def _node(budget,field):
 if budget[0]<=0:raise ValueError(field+':core-patrol-node-limit')
 budget[0]-=1


def _list(reader,field,element,cap,budget):
 at=reader.offset;count=reader.number('<i',field+'.count')
 if not -1<=count<=source.LIMIT:raise ValueError(field+':core-patrol-count-limit')
 if count>budget[0]:raise ValueError(field+':core-patrol-node-limit')
 reader.need(max(count,0)*(12 if element==source.VECTOR else 1),field+'.elements');rows=[]
 for j in range(max(count,0)):
  path=field+'['+str(j)+']'
  if element==source.VECTOR:
   _node(budget,path);row={axis:reader.single(path+'.'+axis)for axis in'xyz'}
  elif element==source.SUBACTION:
   from scripts.game_data.codecs.leveldata.patrol import _decode_pooled_patrol_sub_action
   row,end=_decode_pooled_patrol_sub_action(reader.data,reader.offset,strings=reader.strings,layout=cap['subActionLayout'],node_budget=budget)
   reader.offset=end
  else:row=_record(reader,path,element,cap,budget)
  rows.append(row)
 return dict(startOffset=at,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)


def _record(reader,field,name,cap,budget):
 _node(budget,field);start=reader.offset;marker=reader.number('<B',field+'.memberCount');plan=source.PLANS[name]
 if marker==255:return None
 if marker!=len(plan):raise ValueError(field+':core-patrol-member-count')
 out=dict(startOffset=start,recordType=name,memberCount=marker);ranges={};enums=cap['records'][name]['enumBackings']
 for member,declared,kind in plan:
  at=reader.offset;path=field+'.'+member
  if kind=='scalar32':value=reader.number('<I'if enums.get(member,{}).get('backing')=='uint'else'<i',path)
  elif kind=='float32-bits':value=reader.single(path)
  elif kind=='bool-byte':value=reader.boolean(path)
  elif kind=='unity-vector3-raw12':value={axis:reader.single(path+'.'+axis)for axis in'xyz'}
  elif kind in('core-patrol-reference-list','core-patrol-vector3-list'):value=_list(reader,path,source.COLLECTIONS[declared][0],cap,budget)
  else:raise ValueError(path+':closed-core-patrol-operation')
  out[member]=value;ranges[member]=[at,reader.offset]
 out.update(endOffset=reader.offset,fieldRanges=ranges);return out


def read(reader,field,cap):
 validate(cap);budget=getattr(reader,'_current_core_patrol_budget',None)
 if budget is None:budget=[source.NODE_LIMIT];reader._current_core_patrol_budget=budget
 return _list(reader,field,source.ROOT,cap,budget)

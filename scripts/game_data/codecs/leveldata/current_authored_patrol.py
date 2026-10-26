"""Finite stored Character/Enemy patrol records; no controller or playback claim."""
from scripts.game_data.memorypack import leveldata_authored_patrol_sources as source


def validate(name,cap):
 if (name not in source.PLANS or not isinstance(cap,dict)or cap.get('typeName')!=name
  or type(cap.get('memberCount'))is not int or cap['memberCount']!=len(source.PLANS[name])
  or type(cap.get('nodeLimit'))is not int or cap['nodeLimit']!=source.NODE_LIMIT
  or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','finiteFloatProfile',
   'ordinaryAdapterAdmitted','actualCallbackEqualsProvedChildRequired'))
  or any(cap.get(k)is not False for k in('wholeGrammarAdmitted','liveFormatterSelectionObserved'))
  or cap.get('gameplayTagSourceProved')is not(name==source.CHAR_ACTION)):
  raise ValueError('currentAuthoredPatrol.exact-finite-profile:'+str(name))
 source.bind_program(name,dict(wrappedType=name,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in source.PLANS[name]]),cap.get('program'),[])
 expected={n:t for n,t,k in source.PLANS[name]if k=='scalar32'and t!='int'};enums=cap.get('enumBackings',{})
 if not isinstance(enums,dict)or set(enums)!=set(expected):raise ValueError('currentAuthoredPatrol.exact-enum-set')
 for member,typename in expected.items():
  value=enums[member]
  if (not isinstance(value,dict)or value.get('typeName')!=typename or value.get('backing')not in('int','uint')
   or value.get('field')!=[typename,value['backing'],16]):raise ValueError('currentAuthoredPatrol.nominal-enum')
 children=cap.get('childCapabilities',{});element=source.CHILDREN.get(name)
 expected=set()if element is None else{source.list_key(element),source.record_key(element)}
 if not isinstance(children,dict)or set(children)!=expected:raise ValueError('currentAuthoredPatrol.exact-child-set')
 if element is not None:validate(element,children[source.record_key(element)])
 for binding in cap['program']['childBindings']:
  if (type(binding.get('countLimit'))is not int or binding['countLimit']!=source.LIMIT
   or type(binding.get('readerMethodDefinition'))is not int or binding['readerMethodDefinition']<0
   or type(binding.get('sourceTargetRva'))is not int or binding['sourceTargetRva']<=0):
   raise ValueError('currentAuthoredPatrol.literal-list-binding')
  key=binding['capability'];join=dict(fieldName=binding['fieldName'],typeName=binding['typeName'],sourceTargetRva=binding['sourceTargetRva'],
   typedRequest=dict(methodName='ReadPackable',methodArguments=[binding['typeName']],methodSpec=[binding['readerMethodDefinition']]))
  if binding!=source.bind_collection({},join,dict(nativeInputs={},capabilities={key:children[key]}),key):
   raise ValueError('currentAuthoredPatrol.complete-list-binding')
 if name in source.FIELDS.values():
  field,=[field for field,original in source.FIELDS.items()if original==name];parent=cap.get('parentBinding',{})
  if (any(parent.get(k)!=v for k,v in dict(ownerType='Beyond.Gameplay.LevelData',fieldName=field,typeName=source.list_type(name),
   capability=source.record_key(name),countLimit=source.LIMIT).items())or type(parent.get('countLimit'))is not int
   or type(parent.get('readerMethodDefinition'))is not int or parent['readerMethodDefinition']<0
   or type(parent.get('sourceTargetRva'))is not int or parent['sourceTargetRva']<=0
   or parent.get('actualCallbackEqualsProvedChildRequired')is not True):raise ValueError('currentAuthoredPatrol.actual-host-list-parent')
 elif 'parentBinding'in cap:raise ValueError('currentAuthoredPatrol.unexpected-host-parent')


def _read(reader,field,name,cap,budget):
 if budget[0]<=0:raise ValueError(field+':authored-patrol-node-limit')
 budget[0]-=1;start=reader.offset;marker=reader.number('<B',field+'.memberCount')
 if marker==255:return None
 if marker!=len(source.PLANS[name]):raise ValueError(field+':authored-patrol-member-count')
 out=dict(startOffset=start,recordType=name,memberCount=marker);ranges={}
 for member,declared,kind in source.PLANS[name]:
  at=reader.offset;path=field+'.'+member
  if kind=='scalar32':value=reader.number('<I'if cap['enumBackings'].get(member,{}).get('backing')=='uint'else'<i',path)
  elif kind=='scalar64-bits':value=str(reader.number('<Q',path))
  elif kind=='float32-bits':value=reader.single(path)
  elif kind=='bool-byte':value=reader.boolean(path)
  elif kind=='byte-payload':value=reader.string(path)
  elif kind=='gameplay-tag32':value=reader.number('<I',path)
  elif kind=='unity-vector3-raw12':value={axis:reader.single(path+'.'+axis)for axis in'xyz'}
  elif kind=='authored-patrol-list':
   count=reader.number('<i',path+'.count')
   if not -1<=count<=source.LIMIT:raise ValueError(path+':authored-patrol-count-limit')
   if count>budget[0]:raise ValueError(path+':authored-patrol-node-limit')
   reader.need(max(count,0),path+'.elements');element=source.LISTS[declared];child=cap['childCapabilities'][source.record_key(element)]
   rows=[_read(reader,path+f'[{index}]',element,child,budget)for index in range(max(count,0))]
   value=dict(startOffset=at,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)
  else:raise ValueError(path+':closed-authored-patrol-operation')
  out[member]=value;ranges[member]=[at,reader.offset]
 out.update(endOffset=reader.offset,fieldRanges=ranges);return out


def read(reader,field,name,cap):
 validate(name,cap)
 budget=getattr(reader,'_current_authored_patrol_budget',None)
 if budget is None:budget=[source.NODE_LIMIT];reader._current_authored_patrol_budget=budget
 return _read(reader,field,name,cap,budget)

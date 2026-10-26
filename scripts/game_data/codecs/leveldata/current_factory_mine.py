"""One cursor for finite mine records and exact signed integer transforms."""
from scripts.game_data.memorypack import leveldata_factory_mine_sources as source


def validate(name,cap):
 if (name not in source.PLANS or not isinstance(cap,dict)or cap.get('typeName')!=name
  or type(cap.get('memberCount'))is not int or cap['memberCount']!=len(source.PLANS[name])
  or type(cap.get('nodeLimit'))is not int or cap['nodeLimit']!=source.NODE_LIMIT
  or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','ordinaryAdapterAdmitted',
   'integerVectorSourceProved','finiteFloatProfile','actualCallbackEqualsProvedChildRequired'))
  or any(cap.get(k)is not False for k in('wholeGrammarAdmitted','liveFormatterSelectionObserved'))):
  raise ValueError('currentFactoryMine.exact-ordinary-profile:'+str(name))
 source.bind_program(name,dict(wrappedType=name,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in source.PLANS[name]]),cap.get('program'),[])
 children=cap.get('childCapabilities',{})
 expected=set()if name==source.TRANSFORM else{source.integers.CAP,source.KEYS[source.TRANSFORM]}
 if not isinstance(children,dict)or set(children)!=expected:raise ValueError('currentFactoryMine.exact-child-set')
 if name==source.MINE:
  from scripts.game_data.memorypack.leveldata_integer_host_sources import bind_collection
  validate(source.TRANSFORM,children[source.KEYS[source.TRANSFORM]])
  for binding in cap['program']['childBindings']:
   method='ReadValue'if binding['capability']==source.KEYS[source.TRANSFORM]else'ReadPackable'
   join=dict(fieldName=binding['fieldName'],typeName=binding['typeName'],sourceTargetRva=binding.get('sourceTargetRva'),
    typedRequest=dict(methodName=method,methodArguments=[binding['typeName']],methodSpec=[binding.get('readerMethodDefinition')]))
   binder=source.bind_reference if method=='ReadValue'else bind_collection
   if binder({},join,dict(nativeInputs={},capabilities=children),binding['capability'])!=binding:
    raise ValueError('currentFactoryMine.complete-child-binding')
  parent=cap.get('parentBinding',{})
  if (any(parent.get(k)!=v for k,v in dict(ownerType='Beyond.Gameplay.LevelData',fieldName=source.FIELD,
   typeName='System.Collections.Generic.List`1<'+source.MINE+'>',capability=source.KEYS[source.MINE],countLimit=source.LIMIT).items())
   or type(parent.get('countLimit'))is not int or type(parent.get('readerMethodDefinition'))is not int or parent['readerMethodDefinition']<0
   or type(parent.get('sourceTargetRva'))is not int or parent['sourceTargetRva']<=0
   or parent.get('actualCallbackEqualsProvedChildRequired')is not True):raise ValueError('currentFactoryMine.exact-host-parent')
 elif 'parentBinding'in cap:raise ValueError('currentFactoryMine.unexpected-host-parent')


def _read(reader,field,name,cap,budget):
 if budget[0]<=0:raise ValueError(field+':factory-mine-node-limit')
 budget[0]-=1;start=reader.offset;marker=reader.number('<B',field+'.memberCount')
 if marker==255:return None
 if marker!=len(source.PLANS[name]):raise ValueError(field+':factory-mine-member-count')
 out=dict(startOffset=start,recordType=name,memberCount=marker);ranges={}
 for member,declared,kind in source.PLANS[name]:
  at=reader.offset;path=field+'.'+member
  if kind=='scalar32':value=reader.number('<i',path)
  elif kind=='scalar64-bits':value=str(reader.number('<Q',path))
  elif kind=='float32-bits':value=reader.single(path)
  elif kind=='byte-payload':value=reader.string(path)
  elif kind in('unity-vector2-int-raw8','unity-vector3-int-raw12'):
   value={axis:reader.number('<i',path+'.'+axis)for axis in('xy'if kind=='unity-vector2-int-raw8'else'xyz')}
  elif kind=='factory-grid-transform':value=_read(reader,path,source.TRANSFORM,cap['childCapabilities'][source.KEYS[source.TRANSFORM]],budget)
  elif kind=='int32-list':
   begin=reader.offset;count=reader.number('<i',path+'.count')
   if not -1<=count<=source.LIMIT:raise ValueError(path+':factory-mine-count-limit')
   reader.need(max(0,count)*4,path+'.elements');rows=[reader.number('<i',path+'['+str(j)+']')for j in range(max(0,count))]
   value=dict(startOffset=begin,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)
  else:raise ValueError(path+':closed-factory-mine-operation')
  out[member]=value;ranges[member]=[at,reader.offset]
 out.update(endOffset=reader.offset,fieldRanges=ranges);return out


def read(reader,field,name,cap):
 validate(name,cap);budget=getattr(reader,'_current_factory_mine_budget',None)
 if budget is None:budget=[source.NODE_LIMIT];reader._current_factory_mine_budget=budget
 return _read(reader,field,name,cap,budget)

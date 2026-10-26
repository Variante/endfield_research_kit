"""Finite EnemyGroup list cursor, requiring a complete selected stored profile."""
from scripts.game_data.memorypack import leveldata_enemy_group_sources as source
from scripts.game_data.codecs.leveldata import current_entity_ptr as entity


def validate(cap):
 if(not isinstance(cap,dict)or cap.get('typeName')!=source.LIST(source.GROUP)or cap.get('capability')!=source.CAP
  or any(type(cap.get(k))is not int or cap[k]!=v for k,v in dict(countLimit=source.LIMIT,nodeLimit=source.NODE_LIMIT,headerBytes=4).items())
  or any(cap.get(k)is not True for k in('profileAdmitted','initiallyNullListsRequired','coherentWrapperStorageRequired',
   'actualCallbackEqualsProvedChildRequired','finiteFloatProfile','canonicalBooleanProfile'))
  or cap.get('wholeGrammarAdmitted')is not False or cap.get('liveFormatterSelectionObserved')is not False
  or cap.get('runtimeEntityResolutionProved')is not False or cap.get('runtimeReferenceLayoutAdmitted')is not False):
  raise ValueError('currentEnemyGroup.exact-finite-profile')
 entity.validate(cap.get('entityCapability'));records=cap.get('records',{})
 if not isinstance(records,dict)or set(records)!=set(source.PLANS):raise ValueError('currentEnemyGroup.exact-record-set')
 for name,plan in source.PLANS.items():
  row=records[name]
  if(not isinstance(row,dict)or row.get('typeName')!=name
   or any(row.get(k)is not True for k in('nullAdmitted','positiveAdmitted','ordinaryAdapterAdmitted','profileAdmitted','actualCallbackEqualsProvedChildRequired'))
   or row.get('wholeGrammarAdmitted')is not False or row.get('liveFormatterSelectionObserved')is not False):
   raise ValueError('currentEnemyGroup.exact-record-profile')
  source.bind_program(name,dict(wrappedType=name,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in plan]),row.get('program'),[])
 binding,=records[source.SLOT]['program']['childBindings'];child=cap['entityCapability']
 if(any(binding.get(k)!=v for k,v in dict(fieldName='entityPtr',typeName=source.ENTITY,capability=source.ENTITY_CAP,
   readerMethodDefinition=child['readerMethodDefinition'],sourceTargetRva=child['sourceTargetRva'],managedBytes=40,
   opaqueRuntimeStorageRanges=[[24,40]],selectedBarrierValueOffsets=[24],runtimeReferenceLayoutAdmitted=False,
   actualCallbackEqualsProvedChildRequired=True).items())
  or binding.get('runtimeReferenceLayoutAdmitted')is not False
  or binding.get('actualCallbackEqualsProvedChildRequired')is not True):
  raise ValueError('currentEnemyGroup.exact-opaque-entity-binding')
 collection=cap.get('slotCollection',{});slot_binding,=records[source.GROUP]['program']['childBindings']
 wanted=source.bind_collection({},dict(fieldName='slot',typeName=source.LIST(source.SLOT),sourceTargetRva=slot_binding.get('sourceTargetRva'),
  typedRequest=dict(methodName='ReadPackable',methodArguments=[source.LIST(source.SLOT)],methodSpec=[slot_binding.get('readerMethodDefinition')])),
  dict(nativeInputs={},capabilities={source.SLOT_LIST_CAP:collection}),source.SLOT_LIST_CAP)
 if(slot_binding!=wanted or slot_binding.get('initiallyNullListRequired')is not True
  or slot_binding.get('actualCallbackEqualsProvedChildRequired')is not True):raise ValueError('currentEnemyGroup.exact-slot-list-binding')
 parent=cap.get('parentBinding',{})
 if(any(parent.get(k)!=v for k,v in dict(ownerType='Beyond.Gameplay.LevelData',fieldName='enemyGroup',
   typeName=source.LIST(source.GROUP),capability=source.CAP,elementType=source.GROUP,
   initiallyNullListRequired=True,actualCallbackEqualsProvedChildRequired=True).items())
  or type(parent.get('readerMethodDefinition'))is not int or parent['readerMethodDefinition']<0
  or type(parent.get('sourceTargetRva'))is not int or parent['sourceTargetRva']<=0
  or parent.get('initiallyNullListRequired')is not True or parent.get('actualCallbackEqualsProvedChildRequired')is not True):
  raise ValueError('currentEnemyGroup.exact-actual-host-parent')


def _record(reader,field,name,cap,budget):
 if budget[0]<=0:raise ValueError(field+':enemy-group-node-limit')
 budget[0]-=1;start=reader.offset;header=reader.number('<B',field+'.memberCount')
 if header==255:return None
 plan=source.PLANS[name]
 if header!=len(plan):raise ValueError(field+':enemy-group-member-count')
 out=dict(startOffset=start,recordType=name,memberCount=header);spans={}
 for member,declared,kind in plan:
  path=field+'.'+member;at=reader.offset
  if kind=='entity-ptr-stored-value':value=entity.read(reader,path,cap['entityCapability'])
  elif kind=='scalar32':value=reader.number('<i',path)
  elif kind=='scalar64-bits':value=str(reader.number('<Q',path))
  elif kind=='bool-byte':value=reader.boolean(path)
  elif kind=='float32-bits':value=reader.single(path)
  elif kind=='byte-payload':value=reader.string(path)
  elif kind=='vector2-raw8':value={axis:reader.single(path+'.'+axis)for axis in'xy'}
  elif kind=='enemy-group-slot-list':value=_list(reader,path,source.SLOT,cap,budget)
  else:raise ValueError(path+':closed-enemy-group-operation')
  out[member]=value;spans[member]=[at,reader.offset]
 out.update(endOffset=reader.offset,fieldRanges=spans);return out


def _list(reader,field,element,cap,budget):
 start=reader.offset;count=reader.number('<i',field+'.count')
 if not -1<=count<=source.LIMIT:raise ValueError(field+':enemy-group-count-limit')
 if count>budget[0]:raise ValueError(field+':enemy-group-node-limit')
 reader.need(max(count,0),field+'.elements')
 rows=[_record(reader,field+'['+str(i)+']',element,cap,budget)for i in range(max(count,0))]
 return dict(startOffset=start,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)


def read(reader,field,cap):
 validate(cap);state=getattr(reader,'_current_enemy_group_budget',None)
 if state is None:state=(cap,[source.NODE_LIMIT]);reader._current_enemy_group_budget=state
 elif state[0]is not cap:raise ValueError(field+':mixed-enemy-group-capability')
 return _list(reader,field,source.GROUP,cap,state[1])


def conditional_sources(cap):
 validate(cap)
 return [dict(typeName=source.LIST(source.GROUP),recordTypes=[source.GROUP,source.SLOT],countLimit=source.LIMIT,
  nodeLimit=source.NODE_LIMIT,initiallyNullListsRequired=True,coherentWrapperStorageRequired=True,
  opaqueRuntimeStorageRanges=[[24,40]],selectedBarrierValueOffsets=[24],runtimeReferenceLayoutAdmitted=False,
  actualCallbackEqualsProvedChildRequired=True,runtimeEntityResolutionProved=False,
  runtimeFormatterSelectionObserved=False,runtimeGameplayBehaviorProved=False)]

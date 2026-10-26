"""Bounded factory-region syntax under its fresh complete graph capability."""
from scripts.game_data.memorypack import leveldata_factory_region_sources as source


def _join(binding,method):
 return dict(fieldName=binding.get('fieldName'),typeName=binding.get('typeName'),sourceTargetRva=binding.get('sourceTargetRva'),
  typedRequest=dict(methodName=method,methodArguments=[binding.get('typeName')],methodSpec=[binding.get('readerMethodDefinition')]))


def validate(cap):
 if(not isinstance(cap,dict)or(cap.get('typeName'),cap.get('capability'))!=(source.REGION,source.CAP)
  or any(type(cap.get(k))is not int or cap[k]!=v for k,v in dict(countLimit=source.LIMIT,nodeLimit=source.NODE_LIMIT).items())
  or any(cap.get(k)is not True for k in('profileAdmitted','actualCallbackEqualsProvedChildRequired','initiallyNullListsRequired','coherentWrapperStorageRequired','finiteFloatProfile'))
  or cap.get('wholeGrammarAdmitted')is not False or cap.get('liveFormatterSelectionObserved')is not False):
  raise ValueError('currentFactoryRegion.exact-conditional-graph')
 records=cap.get('records',{});collections=cap.get('collections',{})
 if not isinstance(records,dict)or set(records)!=set(source.PLANS):raise ValueError('currentFactoryRegion.exact-record-set')
 if not isinstance(collections,dict)or set(collections)!={source.list_key(n)for n in source.COLLECTIONS}:
  raise ValueError('currentFactoryRegion.exact-list-set')
 components={source.record_key(n):r for n,r in records.items()}
 for name in source.ordered_types():
  row=records[name];plan=source.PLANS[name]
  if(not isinstance(row,dict)or row.get('typeName')!=name or type(row.get('memberCount'))is not int or row['memberCount']!=len(plan)
   or any(row.get(k)is not True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','ordinaryAdapterAdmitted','actualCallbackEqualsProvedChildRequired'))
   or row.get('wholeGrammarAdmitted')is not False or row.get('liveFormatterSelectionObserved')is not False
   or type(row.get('referenceReaderMethodDefinition'))is not int or row['referenceReaderMethodDefinition']<0
   or type(row.get('referenceReaderTargetRva'))is not int or row['referenceReaderTargetRva']<=0):
   raise ValueError('currentFactoryRegion.exact-record-profile:'+name)
  source.bind_program(name,dict(wrappedType=name,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in plan]),row.get('program'),[])
  enums=row.get('enumBackings',{});wanted={n:t for n,t,k in plan if k=='scalar32'and t!='int'}
  if not isinstance(enums,dict)or set(enums)!=set(wanted):raise ValueError('currentFactoryRegion.exact-enum-set:'+name)
  for member,declared in wanted.items():
   enum=enums[member]
   if(not isinstance(enum,dict)or enum.get('typeName')!=declared or enum.get('backing')not in('int','uint')
    or enum.get('field')!=[declared,enum['backing'],16]):raise ValueError('currentFactoryRegion.exact-nominal-enum')
  for binding in row['program']['childBindings']:
   declared=binding['typeName'];key=binding['capability']
   if declared in records:
    expected=source.bind_reference({},_join(binding,'ReadValue'),dict(nativeInputs={},capabilities=components),key)
   elif declared in source.COLLECTIONS:
    expected=source.bind_collection({},_join(binding,'ReadPackable'),dict(nativeInputs={},capabilities=collections),key)
   else:raise ValueError('currentFactoryRegion.unproved-child-type')
   if binding!=expected:raise ValueError('currentFactoryRegion.exact-child-source-binding')
 parent=cap.get('parentBinding',{})
 if(not isinstance(parent,dict)or any(parent.get(k)!=v for k,v in dict(ownerType='Beyond.Gameplay.LevelData',fieldName=source.FIELD,
  typeName=source.LIST(source.REGION),capability=source.CAP,countLimit=source.LIMIT,
  initiallyNullListRequired=True,actualCallbackEqualsProvedChildRequired=True).items())
  or type(parent.get('readerMethodDefinition'))is not int or parent['readerMethodDefinition']<0
  or type(parent.get('sourceTargetRva'))is not int or parent['sourceTargetRva']<=0):
  raise ValueError('currentFactoryRegion.exact-host-parent')


def _node(field,budget):
 if budget[0]<=0:raise ValueError(field+':factory-region-node-limit')
 budget[0]-=1


def _list(reader,field,element,kind,cap,budget):
 start=reader.offset;count=reader.number('<i',field+'.count')
 if not -1<=count<=source.LIMIT:raise ValueError(field+':factory-region-count-limit')
 if count>budget[0]:raise ValueError(field+':factory-region-node-limit')
 minimum=8 if kind=='vector2-int-list'else 4 if kind=='int32-list'else 1
 reader.need(max(count,0)*minimum,field+'.elements')
 if kind!='factory-region-record-list':budget[0]-=max(count,0)
 rows=[]
 for j in range(max(count,0)):
  path=field+'['+str(j)+']'
  if kind=='vector2-int-list':value={axis:reader.number('<i',path+'.'+axis)for axis in'xy'}
  elif kind=='int32-list':value=reader.number('<i',path)
  else:value=_record(reader,path,element,cap,budget)
  rows.append(value)
 return dict(startOffset=start,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)


def _record(reader,field,name,cap,budget):
 _node(field,budget);start=reader.offset;marker=reader.number('<B',field+'.memberCount');plan=source.PLANS[name]
 if marker==255:return None
 if marker!=len(plan):raise ValueError(field+':factory-region-member-count')
 out=dict(startOffset=start,recordType=name,memberCount=marker);ranges={};enums=cap['records'][name]['enumBackings']
 for member,declared,kind in plan:
  at=reader.offset;path=field+'.'+member
  if kind=='bool-byte':value=reader.boolean(path)
  elif kind=='scalar32':value=reader.number('<I'if enums.get(member,{}).get('backing')=='uint'else'<i',path)
  elif kind=='scalar64-bits':value=str(reader.number('<q'if declared=='long'else'<Q',path))
  elif kind=='float32-bits':value=reader.single(path)
  elif kind=='unity-vector3-raw12':value={axis:reader.single(path+'.'+axis)for axis in'xyz'}
  elif kind=='unity-vector2-int-raw8':value={axis:reader.number('<i',path+'.'+axis)for axis in'xy'}
  elif kind=='unity-vector3-int-raw12':value={axis:reader.number('<i',path+'.'+axis)for axis in'xyz'}
  elif kind=='byte-payload':value=reader.string(path)
  elif kind=='factory-region-record':value=_record(reader,path,declared,cap,budget)
  elif kind in('factory-region-record-list','int32-list','vector2-int-list'):
   element,_=source.COLLECTIONS[declared];value=_list(reader,path,element,kind,cap,budget)
  else:raise ValueError(path+':closed-factory-region-operation')
  out[member]=value;ranges[member]=[at,reader.offset]
 out.update(endOffset=reader.offset,fieldRanges=ranges);return out


def read(reader,field,cap):
 # This complete check precedes even a null/empty root list or FF element.
 validate(cap)
 budget=getattr(reader,'_current_factory_region_budget',None)
 if budget is None:budget=[source.NODE_LIMIT];reader._current_factory_region_budget=budget
 return _list(reader,field,source.REGION,'factory-region-record-list',cap,budget)


def conditional_sources(cap):
 validate(cap)
 return [dict(typeName=source.REGION,recordTypes=source.ordered_types(),countLimit=source.LIMIT,nodeLimit=source.NODE_LIMIT,
  initiallyNullListsRequired=True,coherentWrapperStorageRequired=True,actualCallbackEqualsProvedChildRequired=True,
  integerVectors=dict(Vector2Int=['x','y'],Vector3Int=['x','y','z']),
  runtimeFormatterSelectionObserved=False,factoryGameplayBehaviorProved=False)]+[
  dict(typeName=r['typeName'],elementType=r['elementType'],wireKind=r['wireKind'],countLimit=r['countLimit'],
   initiallyNullListRequired=True,actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False)
  for r in cap['collections'].values()]

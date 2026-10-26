"""Positive SafeZone/Predefine syntax, gated separately from old empty subsets."""
from scripts.game_data.memorypack import leveldata_auxiliary_container_sources as source


def validate(cap):
 if(not isinstance(cap,dict)or cap.get('typeName')not in source.CHILDREN
  or cap.get('capability')!=source.CAPS[cap['typeName']]
  or any(type(cap.get(k))is not int or cap[k]!=v for k,v in dict(memberCount=1,countLimit=source.LIMIT,nodeLimit=source.NODE_LIMIT).items())
  or any(cap.get(k)is not True for k in('profileAdmitted','actualCallbackEqualsProvedChildRequired','coherentWrapperStorageRequired','initiallyNullListsRequired','finiteFloatProfile'))
  or cap.get('wholeGrammarAdmitted')is not False or cap.get('liveFormatterSelectionObserved')is not False):
  raise ValueError('currentAuxiliaryContainer.exact-positive-profile')
 name=cap['typeName'];child=source.CHILDREN[name];records=cap.get('records',{});lists=cap.get('collections',{})
 if not isinstance(records,dict)or set(records)!={name,child}or not isinstance(lists,dict)or set(lists)!={source.list_key(source.LIST(child))}:
  raise ValueError('currentAuxiliaryContainer.exact-child-set')
 for typename,row in records.items():
  plan=source.PLANS[typename]
  if(not isinstance(row,dict)or row.get('typeName')!=typename or type(row.get('memberCount'))is not int or row['memberCount']!=len(plan)
   or any(row.get(k)is not True for k in('nullAdmitted','positiveAdmitted','ordinaryAdapterAdmitted','profileAdmitted','actualCallbackEqualsProvedChildRequired'))
   or row.get('wholeGrammarAdmitted')is not False or row.get('liveFormatterSelectionObserved')is not False):
   raise ValueError('currentAuxiliaryContainer.exact-record-profile')
  source.bind_program(typename,dict(wrappedType=typename,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in plan]),row.get('program'),[])
  for binding in row['program']['childBindings']:
   expected=source.bind_collection({},dict(fieldName=binding['fieldName'],typeName=binding['typeName'],sourceTargetRva=binding['sourceTargetRva'],
    typedRequest=dict(methodName='ReadPackable',methodArguments=[binding['typeName']],methodSpec=[binding['readerMethodDefinition']])),
    dict(nativeInputs={},capabilities=lists),binding['capability'])
   if binding!=expected:raise ValueError('currentAuxiliaryContainer.exact-list-binding')
 field,=[field for field,root in source.FIELDS.items()if root==name];parent=cap.get('parentBinding',{})
 if(not isinstance(parent,dict)or any(parent.get(k)!=v for k,v in dict(ownerType='Beyond.Gameplay.LevelData',fieldName=field,
  typeName=name,capability=source.CAPS[name],actualCallbackEqualsProvedChildRequired=True).items())
  or type(parent.get('readerMethodDefinition'))is not int or parent['readerMethodDefinition']<0
  or type(parent.get('sourceTargetRva'))is not int or parent['sourceTargetRva']<=0):
  raise ValueError('currentAuxiliaryContainer.exact-actual-host-parent')


def _record(reader,field,name,cap,budget):
 if budget[0]<=0:raise ValueError(field+':auxiliary-node-limit')
 budget[0]-=1;start=reader.offset;marker=reader.number('<B',field+'.memberCount');plan=source.PLANS[name]
 if marker==255:return None
 if marker!=len(plan):raise ValueError(field+':auxiliary-member-count')
 out=dict(startOffset=start,recordType=name,memberCount=marker);ranges={}
 for member,declared,kind in plan:
  at=reader.offset;path=field+'.'+member
  if kind=='unity-vector3-raw12':value={axis:reader.single(path+'.'+axis)for axis in'xyz'}
  elif kind=='byte-payload':value=reader.string(path)
  elif kind=='float32-bits':value=reader.single(path)
  elif kind=='auxiliary-record-list':
   count=reader.number('<i',path+'.count')
   if not -1<=count<=source.LIMIT:raise ValueError(path+':auxiliary-count-limit')
   if count>budget[0]:raise ValueError(path+':auxiliary-node-limit')
   reader.need(max(count,0),path+'.elements');rows=[_record(reader,path+'['+str(j)+']',source.LISTS[declared],cap,budget)for j in range(max(count,0))]
   value=dict(startOffset=at,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)
  else:raise ValueError(path+':closed-auxiliary-operation')
  out[member]=value;ranges[member]=[at,reader.offset]
 out.update(endOffset=reader.offset,fieldRanges=ranges);return out


def read(reader,field,cap):
 validate(cap);budgets=getattr(reader,'_current_auxiliary_container_budgets',None)
 if budgets is None:budgets={};reader._current_auxiliary_container_budgets=budgets
 budget=budgets.setdefault(cap['typeName'],[source.NODE_LIMIT])
 return _record(reader,field,cap['typeName'],cap,budget)


def conditional_sources(cap):
 validate(cap)
 return [dict(typeName=cap['typeName'],recordTypes=[cap['typeName'],source.CHILDREN[cap['typeName']]],countLimit=source.LIMIT,
  nodeLimit=source.NODE_LIMIT,initiallyNullListsRequired=True,coherentWrapperStorageRequired=True,
  actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False,runtimeGameplayBehaviorProved=False)]

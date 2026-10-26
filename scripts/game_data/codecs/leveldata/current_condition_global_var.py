"""Only the independently authenticated GlobalVar condition leaf cursor."""
from scripts.game_data.memorypack import leveldata_condition_global_var_sources as source


def validate(cap):
 if(not isinstance(cap,dict)or cap.get('typeName')!=source.TYPE
  or type(cap.get('memberCount'))is not int or cap['memberCount']!=3
  or type(cap.get('signedCompareTargetBits'))is not int or cap['signedCompareTargetBits']!=32
  or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','wholeGrammarAdmitted','actualCallbackEqualsProvedChildRequired'))
  or cap.get('liveFormatterSelectionObserved')is not False):raise ValueError('currentConditionGlobalVar.exact-leaf-capability')
 source.bind_program(dict(wrappedType=source.TYPE,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in source.PLAN]),cap.get('program'),[])
 enum=cap.get('enumBacking',{});name=source.PLAN[0][1]
 if(enum.get('typeName')!=name or enum.get('backing')not in('int','uint')or enum.get('field')!=[name,enum['backing'],16]):
  raise ValueError('currentConditionGlobalVar.exact-operator-enum')


def read(reader,field,cap):
 validate(cap);start=reader.offset;marker=reader.number('<B',field+'.memberCount')
 if marker==255:return None
 if marker!=3:raise ValueError(field+':global-var-member-count')
 at=reader.offset;operator=reader.number('<i'if cap['enumBacking']['backing']=='int'else'<I',field+'.compareOperator')
 target=reader.number('<i',field+'.compareTarget');pooled_at=reader.offset;name=reader.string(field+'.globalVarName')
 return dict(startOffset=start,endOffset=reader.offset,recordType=source.TYPE,memberCount=3,
  compareOperator=operator,compareTarget=target,globalVarName=name,
  fieldRanges=dict(compareOperator=[at,at+4],compareTarget=[at+4,pooled_at],globalVarName=[pooled_at,reader.offset]))


def validate_union(cap):
 from scripts.game_data.codecs.leveldata import current_condition as original
 if(not isinstance(cap,dict)or(cap.get('schema'),cap.get('capability'),cap.get('typeName'))!=(source.CAP_SCHEMA,source.CAP,source.BASE)
  or any(cap.get(k)is not True for k in('profileAdmitted','nullAdmitted','positiveAdmitted','actualCallbackEqualsProvedChildRequired'))
  or cap.get('wholeGrammarAdmitted')is not False or cap.get('liveFormatterSelectionObserved')is not False
  or cap.get('admittedRouteTags')!=[0,9,12,13,18]or any(type(t)is not int for t in cap['admittedRouteTags'])):
  raise ValueError('currentConditionGlobalVar.exact-opt-in-union-capability')
 base=cap.get('baseCapability',{})
 if not isinstance(base,dict):raise ValueError('currentConditionGlobalVar.exact-base-capability')
 original.validate(base)
 for key in('countLimit','nodeLimit','depthLimit','referenceReaderMethodDefinition','referenceReaderTargetRva'):
  if type(cap.get(key))is not int or cap[key]!=base[key]:raise ValueError('currentConditionGlobalVar.same-base-'+key)
 route=cap.get('tag9Route',{})
 if(not isinstance(route,dict)or type(route.get('tag'))is not int or route['tag']!=9 or route.get('typeName')!=source.TYPE
  or type(route.get('wrapperName'))is not str or not route['wrapperName']or type(route.get('wrapperNullAdmitted'))is not bool
  or route.get('actualWrapperCallbackEqualsProvedConcreteRequired')is not True):
  raise ValueError('currentConditionGlobalVar.exact-current-tag9-route')
 validate(route.get('capability'))


def read_union(reader,field,cap):
 """Opt in for this field only, including nested Combined conditions."""
 from scripts.game_data.codecs.leveldata import current_condition as original
 from scripts.game_data.memorypack import leveldata_condition_components as common
 validate_union(cap);base=cap['baseCapability']
 def condition(path,depth,budget):
  if depth>=cap['depthLimit']or budget[0]<=0:raise ValueError(path+':condition-resource-limit,offset='+str(reader.offset))
  budget[0]-=1;start=reader.offset;tag=reader.number('<B',path+'.unionTag')
  if tag==255:return None
  if tag==250:raise ValueError(path+':extended-condition-tag-unproved,offset='+str(start))
  if 251<=tag<=254:raise ValueError(path+':reserved-union-marker,offset='+str(start))
  if tag not in cap['admittedRouteTags']:raise ValueError(path+':current-condition-tag-unproved,offset='+str(start)+',actual='+str(tag))
  route=cap['tag9Route']if tag==9 else base['routes'][str(tag)];selected=route['capability']
  reader.need(1,path+'.memberCount')
  if reader.data[reader.offset]==255 and route['wrapperNullAdmitted']is not True:
   raise ValueError(path+':current-condition-wrapper-null-unproved,offset='+str(reader.offset))
  if tag==9:value=read(reader,path+'.value',selected)
  elif tag!=0:value=original.read_leaf(reader,path+'.value',route['typeName'],selected)
  else:
   child_start=reader.offset;marker=reader.number('<B',path+'.value.memberCount')
   if marker==255:value=None
   else:
    if marker!=3:raise ValueError(path+':combined-member-count,offset='+str(child_start))
    at=reader.offset;operator=reader.number('<i'if selected['enumBacking']['backing']=='int'else'<I',path+'.conditionOperator')
    reverse=reader.boolean(path+'.reverse');count_start=reader.offset;count=reader.number('<i',path+'.subConditions.count')
    if not -1<=count<=cap['countLimit']:raise ValueError(path+':current-condition-count-limit,offset='+str(count_start))
    if max(count,0)>budget[0]:raise ValueError(path+':condition-resource-limit,offset='+str(reader.offset))
    reader.need(max(count,0),path+'.subConditions.elements')
    rows=[condition(path+'.subConditions['+str(i)+']',depth+1,budget)for i in range(max(count,0))]
    value=dict(startOffset=child_start,endOffset=reader.offset,recordType=common.COMBINED,memberCount=3,
     conditionOperator=operator,reverse=reverse,subConditions=dict(startOffset=count_start,endOffset=reader.offset,
      count=count,rows=None if count==-1 else rows),fieldRanges=dict(conditionOperator=[at,at+4],reverse=[at+4,at+5],subConditions=[count_start,reader.offset]))
  return dict(startOffset=start,endOffset=reader.offset,tag=tag,recordType=route['typeName'],value=value)
 state=getattr(reader,'_current_global_var_condition_budget',None)
 if state is None:state=(cap,[cap['nodeLimit']]);reader._current_global_var_condition_budget=state
 elif state[0]is not cap:raise ValueError(field+':mixed-condition-capability,offset='+str(reader.offset))
 return condition(field,0,state[1])

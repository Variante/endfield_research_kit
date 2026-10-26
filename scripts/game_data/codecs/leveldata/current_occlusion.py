"""Finite stored occlusion geometry under exact independent current child gates."""
from scripts.game_data.memorypack import leveldata_occlusion_sources as source
from scripts.game_data.codecs.leveldata import current_line_value as line,current_condition as condition


def validate(name,cap,condition_cap=None):
 if (name not in source.PLANS or not isinstance(cap,dict)or cap.get('typeName')!=name
  or type(cap.get('memberCount'))is not int or cap['memberCount']!=3
  or type(cap.get('nodeLimit'))is not int or cap['nodeLimit']!=source.NODE_LIMIT
  or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','ordinaryAdapterAdmitted','actualCallbackEqualsProvedChildRequired'))
  or any(cap.get(k)is not False for k in('wholeGrammarAdmitted','liveFormatterSelectionObserved'))):
  raise ValueError('currentOcclusion.exact-ordinary-profile:'+str(name))
 source.bind_program(name,dict(wrappedType=name,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in source.PLANS[name]]),cap.get('program'),[])
 children=cap.get('childCapabilities',{})
 expected={source.lines.LIST_CAP,source.lines.VALUE_CAP}if name==source.GRID else{source.GRID_CAP,source.GRID_LIST_CAP}
 if not isinstance(children,dict)or set(children)!=expected:raise ValueError('currentOcclusion.exact-child-set')
 if name==source.GRID:line.validate_list(children[source.lines.LIST_CAP],children[source.lines.VALUE_CAP])
 else:
  if not isinstance(condition_cap,dict):raise ValueError('currentOcclusion.missing-condition-profile')
  condition.validate(condition_cap);validate(source.GRID,children[source.GRID_CAP])
 for binding in cap['program']['childBindings']:
  if (type(binding.get('readerMethodDefinition'))is not int or binding['readerMethodDefinition']<0
   or type(binding.get('sourceTargetRva'))is not int or binding['sourceTargetRva']<=0):raise ValueError('currentOcclusion.literal-child-source')
  method='ReadValue'if binding['capability']==source.conditions.CAP else'ReadPackable'
  join=dict(fieldName=binding['fieldName'],typeName=binding['typeName'],sourceTargetRva=binding['sourceTargetRva'],
   typedRequest=dict(methodName=method,methodArguments=[binding['typeName']],methodSpec=[binding['readerMethodDefinition']]))
  if method=='ReadValue':
   expected=source.conditions.bind_reference({},join,dict(nativeInputs={},capabilities={source.conditions.CAP:condition_cap}),binding['capability'])
  else:expected=source.bind_collection({},join,dict(nativeInputs={},capabilities=children),binding['capability'])
  if binding!=expected:raise ValueError('currentOcclusion.complete-actual-child-binding')
 if name==source.AREA:
  parent=cap.get('parentBinding',{})
  if (any(parent.get(k)!=v for k,v in dict(ownerType='Beyond.Gameplay.LevelData',fieldName=source.FIELD,
   typeName='System.Collections.Generic.List`1<'+source.AREA+'>',capability=source.AREA_CAP,countLimit=source.LIMIT).items())
   or type(parent.get('countLimit'))is not int or type(parent.get('readerMethodDefinition'))is not int or parent['readerMethodDefinition']<0
   or type(parent.get('sourceTargetRva'))is not int or parent['sourceTargetRva']<=0
   or parent.get('actualCallbackEqualsProvedChildRequired')is not True):raise ValueError('currentOcclusion.exact-host-parent')
 elif 'parentBinding'in cap:raise ValueError('currentOcclusion.unexpected-host-parent')


def _count(reader,field,budget):
 start=reader.offset;count=reader.number('<i',field+'.count')
 if not -1<=count<=source.LIMIT:raise ValueError(field+':occlusion-list-count-limit')
 if count>budget[0]:raise ValueError(field+':occlusion-node-limit')
 reader.need(max(count,0),field+'.elements');return start,count


def _read(reader,field,name,cap,condition_cap,budget):
 if budget[0]<=0:raise ValueError(field+':occlusion-node-limit')
 budget[0]-=1;start=reader.offset;marker=reader.number('<B',field+'.memberCount')
 if marker==255:return None
 if marker!=3:raise ValueError(field+':occlusion-member-count')
 out=dict(startOffset=start,recordType=name,memberCount=3);ranges={};children=cap['childCapabilities']
 for member,declared,kind in source.PLANS[name]:
  at=reader.offset;path=field+'.'+member
  if kind=='scalar32':value=reader.number('<i',path)
  elif kind=='condition-runtime':value=condition.read(reader,path,condition_cap)
  elif kind=='line-value-list':
   list_start,count=_count(reader,path,budget);budget[0]-=max(count,0)
   rows=[line.read(reader,path+'['+str(index)+']',children[source.lines.VALUE_CAP])for index in range(max(count,0))]
   value=dict(startOffset=list_start,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)
  elif kind=='occlusion-grid-list':
   list_start,count=_count(reader,path,budget)
   rows=[_read(reader,path+'['+str(index)+']',source.GRID,children[source.GRID_CAP],condition_cap,budget)for index in range(max(count,0))]
   value=dict(startOffset=list_start,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)
  else:raise ValueError(path+':closed-occlusion-operation')
  out[member]=value;ranges[member]=[at,reader.offset]
 out.update(endOffset=reader.offset,fieldRanges=ranges);return out


def read(reader,field,name,cap,condition_cap=None):
 validate(name,cap,condition_cap)
 budget=getattr(reader,'_current_occlusion_budget',None)
 if budget is None:budget=[source.NODE_LIMIT];reader._current_occlusion_budget=budget
 return _read(reader,field,name,cap,condition_cap,budget)

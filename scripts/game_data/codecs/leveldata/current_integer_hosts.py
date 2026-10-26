"""Exact signed integer-vector projections for finite Doodad/Guide records."""
from scripts.game_data.memorypack import leveldata_integer_host_sources as source


def validate(name,cap):
 plan=source.PLANS.get(name)
 if (plan is None or not isinstance(cap,dict)or cap.get('typeName')!=name
  or type(cap.get('memberCount'))is not int or cap['memberCount']!=len(plan)
  or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','ordinaryAdapterAdmitted',
   'integerVectorSourceProved','actualCallbackEqualsProvedChildRequired'))
  or any(cap.get(k)is not False for k in('wholeGrammarAdmitted','liveFormatterSelectionObserved'))):
  raise ValueError('currentIntegerHosts.exact-finite-profile:'+str(name))
 declared=dict(wrappedType=name,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in plan])
 source.bind_program(name,declared,cap.get('program'),[])
 wanted={n:t for n,t,k in plan if k=='scalar32'and t!='int'};enums=cap.get('enumBackings',{})
 if not isinstance(enums,dict)or set(enums)!=set(wanted):raise ValueError('currentIntegerHosts.exact-enum-set')
 for field,typename in wanted.items():
  row=enums[field]
  if row.get('typeName')!=typename or row.get('backing')not in('int','uint')or row.get('field')!=[typename,row['backing'],16]:
   raise ValueError('currentIntegerHosts.exact-nominal-enum')
 children=cap.get('childCapabilities',{});keys={source.OPERATIONS[k]for n,t,k in plan if k in('int32-list','uint64-list','vector2-int-list')}
 if not isinstance(children,dict)or set(children)!=keys:raise ValueError('currentIntegerHosts.exact-child-set')
 for key,child in children.items():source.validate_collection(key,child)
 for binding in cap['program']['childBindings']:
  if (type(binding.get('readerMethodDefinition'))is not int or binding['readerMethodDefinition']<0
   or type(binding.get('sourceTargetRva'))is not int or binding['sourceTargetRva']<=0):raise ValueError('currentIntegerHosts.literal-child-binding')
  usage=dict(methodName='ReadPackable',methodArguments=[binding['typeName']],methodSpec=[binding['readerMethodDefinition']])
  join=dict(fieldName=binding['fieldName'],typeName=binding['typeName'],sourceTargetRva=binding['sourceTargetRva'],typedRequest=usage)
  if binding!=source.bind_collection({},join,dict(nativeInputs={},capabilities=children),binding['capability']):
   raise ValueError('currentIntegerHosts.complete-child-binding')
 field,= [field for field,original in source.FIELDS.items()if original==name];parent=cap.get('parentBinding',{})
 if (any(parent.get(k)!=v for k,v in dict(ownerType='Beyond.Gameplay.LevelData',fieldName=field,typeName='System.Collections.Generic.List`1<'+name+'>',
  capability=source.CAPS[name],countLimit=source.LIMIT).items())or type(parent.get('countLimit'))is not int
  or type(parent.get('readerMethodDefinition'))is not int or parent['readerMethodDefinition']<0
  or type(parent.get('sourceTargetRva'))is not int or parent['sourceTargetRva']<=0
  or parent.get('actualCallbackEqualsProvedChildRequired')is not True):raise ValueError('currentIntegerHosts.exact-host-parent')


def read(reader,field,cap,*,name):
 validate(name,cap);start=reader.offset;marker=reader.number('<B',field+'.memberCount')
 if marker==255:return None
 if marker!=len(source.PLANS[name]):raise ValueError(field+':integer-host-member-count')
 out=dict(startOffset=start,recordType=name,memberCount=marker);ranges={}
 for member,declared,kind in source.PLANS[name]:
  at=reader.offset;path=field+'.'+member
  if kind=='byte-payload':value=reader.string(path)
  elif kind=='bool-byte':value=reader.boolean(path)
  elif kind=='scalar32':value=reader.number('<I'if cap['enumBackings'].get(member,{}).get('backing')=='uint'else'<i',path)
  elif kind=='scalar64-bits':value=str(reader.number('<Q',path))
  elif kind=='unity-vector3-int-raw12':value={axis:reader.number('<i',path+'.'+axis)for axis in'xyz'}
  elif kind in('int32-list','uint64-list','vector2-int-list'):
   count=reader.number('<i',path+'.count')
   if not -1<=count<=source.LIMIT:raise ValueError(path+':integer-host-count-limit')
   reader.need(max(count,0)*(4 if kind=='int32-list'else 8),path+'.elements');rows=[]
   for index in range(max(count,0)):
    item=path+f'[{index}]'
    if kind=='int32-list':row=reader.number('<i',item)
    elif kind=='uint64-list':row=str(reader.number('<Q',item))
    else:row={axis:reader.number('<i',item+'.'+axis)for axis in'xy'}
    rows.append(row)
   value=dict(startOffset=at,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)
  else:raise ValueError(path+':closed-integer-host-operation')
  out[member]=value;ranges[member]=[at,reader.offset]
 out.update(endOffset=reader.offset,fieldRanges=ranges);return out

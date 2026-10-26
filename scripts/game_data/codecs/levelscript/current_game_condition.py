"""Bounded current GameCondition graphs with explicit owned Param children.

This cursor consumes authenticated component projections. It does not select
native formatters or infer an absent field/union route from its type name.
Stored values are returned without evaluating a condition or resolving a
runtime pointer. Reserved union bytes have no canonical framing here.
"""
import struct

from scripts.game_data.codecs.levelscript.param_graph import ParamGraphDecodeError
from scripts.game_data.memorypack import levelscript_condition_record_components as records

SCHEMA='endfield.story-game-condition-graph-capability.v1'
UNION_SCHEMA='endfield.story-game-condition-union-capability.v1'


def need(key,condition):
 if not condition:raise ParamGraphDecodeError('currentGameCondition.'+key)


def _param_codec(schema):
 from scripts.game_data.codecs.levelscript import current_condition_param as primitive
 from scripts.game_data.codecs.levelscript import current_condition_enum_param as enum
 from scripts.game_data.codecs.levelscript import current_condition_storage_param as storage
 from scripts.game_data.codecs.levelscript import current_condition_int2_param as int2
 from scripts.game_data.codecs.levelscript import current_condition_list_param as listing
 from scripts.game_data.codecs.levelscript import current_condition_script_task_param as task
 from scripts.game_data.memorypack.levelscript_condition_param_sources import SCHEMA as PRIMITIVE
 from scripts.game_data.memorypack.levelscript_condition_enum_param_components import SCHEMA as ENUM
 from scripts.game_data.memorypack.levelscript_condition_storage_param_components import SCHEMA as STORAGE
 from scripts.game_data.memorypack.levelscript_int2_param_sources import SCHEMA as INT2
 from scripts.game_data.memorypack.levelscript_condition_list_param_components import SCHEMA as LIST
 from scripts.game_data.memorypack.levelscript_script_task_param_sources import SCHEMA as TASK
 selected={PRIMITIVE:primitive,ENUM:enum,STORAGE:storage,INT2:int2,LIST:listing,TASK:task}
 need('explicit-owned-Param-codec',schema in selected)
 return selected[schema]


def validate_record(cap,params):
 need('owned-concrete-record-shape',isinstance(cap,dict)and cap.get('schema')==records.CAP_SCHEMA
  and all(type(cap.get(k))is str and cap[k]for k in('typeName','wrapperName'))
  and type(cap.get('memberCount'))is int and 0<=cap['memberCount']<250
  and all(cap.get(k)is True for k in('nullAdmitted','positiveAdmitted','storedRecordGrammarAdmitted',
   'actualWrapperCallbackEqualsProvedConcreteRequired'))
  and all(cap.get(k)is False for k in('liveFormatterSelectionObserved','eagerOriginalAdapterRequired',
   'unionSelectionAdmitted','parentFieldAdmitted','runtimeConditionEvaluationAdmitted')))
 for role in('readerMethod','formatterMethod'):
  method=cap.get(role)
  need('owned-nominal-method-identity',isinstance(method,list)and len(method)==4
   and type(method[0])is int and method[0]>=0 and type(method[1])is str and method[2]=='Deserialize'
   and type(method[3])is int and method[3]>0
   and(method[1]==cap['wrapperName']if role=='readerMethod'else method[1]==
    cap['wrapperName']+'+'+cap['wrapperName'].rsplit('.',1)[-1]+'Formatter'))
 fields=cap.get('fields');program=cap.get('program',{});reads=program.get('reads')
 need('complete-ordered-record-fields',isinstance(fields,list)and isinstance(reads,list)
  and len(fields)==len(reads)==cap['memberCount']==program.get('memberCount')
  and[tuple(f.get(k)for k in('memberIndex','fieldName'))for f in fields]==
     [tuple(r.get(k)for k in('memberIndex','fieldName'))for r in reads]
  and[f.get('memberIndex')for f in fields]==list(range(cap['memberCount']))
  and all(type(f.get('memberIndex'))is int and type(f.get('declaredType'))is str
   and type(f.get('fieldName'))is str and f['fieldName']for f in fields)
  and len({f['fieldName']for f in fields})==len(fields))
 required=set();joined=[]
 for field,read in zip(fields,reads,strict=True):
  kind=read.get('kind');child=read.get('childCapability')
  need('finite-compiled-record-operation',kind in('scalar32','bool-byte','byte-payload','condition-param','game-condition-list'))
  if kind=='condition-param':
   need('own-record-Param-child',child==records.CAP_PREFIX+field['declaredType']and child in params)
   need('same-Param-field-nominal',params[child]['capability']['typeName']==field['declaredType'])
   required.add(child);joined.append((field,read))
  elif kind=='game-condition-list':
   need('only-actual-Combine-recursive-field',(cap['typeName'],field['fieldName'],field['declaredType'],child)==
    ('Beyond.Gameplay.CombineCondition','subConditions',records.LIST,records.LIST_CAP))
   required.add(child);joined.append((field,read))
  elif kind=='byte-payload':
   need('actual-string-pool-operation',field['declaredType']=='string'and child=='byte-payload');required.add(child)
  else:need('atomic-field-has-no-child',child is None)
 need('exact-required-record-capabilities',program.get('requiredCapabilities')==sorted(required))
 bindings=program.get('childBindings',[])
 need('one-actual-binding-per-child-field',isinstance(bindings,list)and len(bindings)==len(joined)
  and[(b.get('fieldName'),b.get('typeName'),b.get('capability'))for b in bindings]==
   [(f['fieldName'],f['declaredType'],r['childCapability'])for f,r in joined]
  and all(type(b.get('readerMethodDefinition'))is int and b['readerMethodDefinition']>=0
   and type(b.get('sourceTargetRva'))is int and b['sourceTargetRva']>0 for b in bindings))
 return cap


def validate(cap):
 need('owned-current-graph',isinstance(cap,dict)and cap.get('schema')==SCHEMA and cap.get('typeName')==records.BASE
  and all(cap.get(k)is True for k in('nullAdmitted','positiveAdmitted','storedGraphGrammarAdmitted',
   'actualWrapperCallbackEqualsProvedConcreteRequired','actualRecursiveCallbackEqualsProvedBaseRequired'))
  and all(cap.get(k)is False for k in('liveFormatterSelectionObserved','runtimeConditionEvaluationAdmitted','parentFieldAdmitted'))
  and type(cap.get('countLimit'))is int and cap['countLimit']==4096
  and type(cap.get('nodeLimit'))is int and cap['nodeLimit']==16384
  and type(cap.get('depthLimit'))is int and cap['depthLimit']==128
  and type(cap.get('paramElementLimit'))is int and cap['paramElementLimit']==10000)
 params=cap.get('params');concrete=cap.get('records');unions=cap.get('unions');root=cap.get('rootWrapper')
 need('finite-explicit-component-maps',isinstance(params,dict)and len(params)<=256 and isinstance(concrete,dict)
  and 0<len(concrete)<=512 and isinstance(unions,dict)and 0<len(unions)<=64
  and type(root)is str and root in unions and isinstance(unions[root],dict)and unions[root].get('typeName')==records.BASE
  and not set(concrete)&set(unions))
 for key,child in params.items():
  need('owned-Param-component-projection',isinstance(child,dict)and type(child.get('componentSchema'))is str
   and isinstance(child.get('capability'),dict)and key==records.CAP_PREFIX+child['capability'].get('typeName',''))
  _param_codec(child['componentSchema']).validate(child['capability'])
 for wrapper,child in concrete.items():
  validate_record(child,params);need('same-concrete-wrapper-key',wrapper==child['wrapperName'])
 targets=concrete|unions
 for wrapper,union in unions.items():
  need('exact-current-union-projection',isinstance(union,dict)and union.get('schema')==UNION_SCHEMA
   and union.get('wrapperName')==wrapper and type(union.get('typeName'))is str
   and union.get('headerModes')==['short','extended','canonical-FF']
   and all(union.get(k)is True for k in('nullAdmitted','positiveAdmitted','actualClosedReadPackableProved',
    'actualWrapperCallbackEqualsProvedChildRequired','nullIncomingWrapperRequired'))
   and union.get('liveFormatterSelectionObserved')is False)
  routes=union.get('routes');need('finite-exact-union-routes',isinstance(routes,dict)and 0<len(routes)<=512)
  for key,route in routes.items():
   need('literal-owned-route',isinstance(route,dict))
   tag=route.get('tag');child=route.get('wrapperName')
   need('literal-ushort-route-and-owned-child',type(tag)is int and 0<=tag<65536 and key==str(tag)
    and child in targets and route.get('typeName')==targets[child]['typeName']
    and route.get('actualClosedReadPackableProved')is True
    and route.get('actualWrapperCallbackEqualsProvedChildRequired')is True)
 # Every projected child must be reachable. Extra records/caps cannot silently
 # widen this graph's reviewed finite domain.
 visited=set();pending=[root];used_params=set()
 while pending:
  wrapper=pending.pop()
  if wrapper in visited:continue
  visited.add(wrapper)
  if wrapper in unions:pending.extend(r['wrapperName']for r in unions[wrapper]['routes'].values())
  else:used_params.update(r['childCapability']for r in concrete[wrapper]['program']['reads']if r['kind']=='condition-param')
 need('complete-reachable-component-domain',visited==set(concrete)|set(unions)and used_params==set(params))


def read(reader,field,cap,*,budget=None,param_budget=None):
 """Decode one root graph; callers may share both budgets across a container."""
 validate(cap)
 def state(value,limit,name):
  if value is None:return[limit]
  need('literal-shared-'+name,isinstance(value,list)and len(value)==1 and type(value[0])is int and 0<=value[0]<=limit)
  return value
 nodes=state(budget,cap['nodeLimit'],'node-budget');elements=state(param_budget,cap['paramElementLimit'],'Param-budget')
 params=cap['params'];concrete=cap['records'];unions=cap['unions']
 def union(wrapper,path,depth):
  if depth>=cap['depthLimit']or nodes[0]<=0:
   raise ParamGraphDecodeError(f'{path}:condition-resource-limit,offset={reader.offset}')
  nodes[0]-=1;start=reader.offset;tag=reader.number('<B',path+'.unionTag')
  if tag==255:return None
  if tag==250:
   tag=reader.number('<H',path+'.extendedUnionTag')
   # The independently proved enclosing_header copies the whole UInt16.
   # Its selected table, below, supplies the finite domain, including short
   # route numbers explicitly carried by the extended encoding.
  elif tag>250:raise ParamGraphDecodeError(f'{path}:reserved-union-marker,offset={start},actual={tag}')
  route=unions[wrapper]['routes'].get(str(tag))
  if route is None:raise ParamGraphDecodeError(f'{path}:unproved-condition-tag,offset={start},actual={tag},wrapper={wrapper}')
  target=route['wrapperName']
  value=union(target,path+'.value',depth+1)if target in unions else record(target,path+'.value',depth+1)
  return dict(startOffset=start,endOffset=reader.offset,tag=tag,recordType=route['typeName'],value=value)
 def record(wrapper,path,depth):
  start=reader.offset;selected=concrete[wrapper];marker=reader.number('<B',path+'.memberCount')
  if marker==255:return None
  if marker!=selected['memberCount']:
   raise ParamGraphDecodeError(f'{path}:condition-member-count,offset={start},expected={selected["memberCount"]},actual={marker}')
  result=dict(startOffset=start,recordType=selected['typeName'],memberCount=marker);spans={}
  for f,operation in zip(selected['fields'],selected['program']['reads'],strict=True):
   name=f['fieldName'];key=path+'.'+name;at=reader.offset;kind=operation['kind']
   if kind=='scalar32':
    bits=reader.number('<I',key);value=dict(unsignedBits=bits,rawHex=struct.pack('<I',bits).hex().upper())
   elif kind=='bool-byte':
    bits=reader.number('<B',key);value=dict(value=bool(bits),rawByte=bits)
   elif kind=='byte-payload':value=reader.string(key)
   elif kind=='condition-param':
    child=params[operation['childCapability']];codec=_param_codec(child['componentSchema'])
    from scripts.game_data.codecs.levelscript import current_condition_list_param as list_codec
    value=codec.read(reader,key,child['capability'],**({'budget':elements}if codec is list_codec else{}))
   else:
    reader.need(4,key+'.count');count=struct.unpack_from('<i',reader.data,at)[0]
    if not -1<=count<=cap['countLimit']:raise ParamGraphDecodeError(f'{key}:condition-count-limit,offset={at},actual={count}')
    if max(count,0)>nodes[0]:raise ParamGraphDecodeError(f'{key}:condition-node-budget,offset={at},actual={count}')
    reader.offset+=4
    value=None if count==-1 else[union(cap['rootWrapper'],key+'['+str(i)+']',depth+1)for i in range(count)]
   result[name]=value;spans[name]=[at,reader.offset]
  result.update(endOffset=reader.offset,fieldRanges=spans);return result
 return union(cap['rootWrapper'],field,0)

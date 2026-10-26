"""Bounded explicit Blackbox/Predefined syntax, under a fresh graph capability."""
from scripts.game_data.memorypack import leveldata_factory_config_sources as source
from scripts.game_data.codecs.leveldata import current_lang_key as language


def _join(binding,method):
 return dict(fieldName=binding.get('fieldName'),typeName=binding.get('typeName'),sourceTargetRva=binding.get('sourceTargetRva'),
  typedRequest=dict(methodName=method,methodArguments=[binding.get('typeName')],methodSpec=[binding.get('readerMethodDefinition')]))


def validate(cap):
 if(not isinstance(cap,dict)or(cap.get('typeName'),cap.get('capability'))!=(source.BLACKBOX,source.CAP)
  or any(type(cap.get(k))is not int or cap[k]!=v for k,v in dict(countLimit=source.LIMIT,nodeLimit=source.NODE_LIMIT).items())
  or any(cap.get(k)is not True for k in('profileAdmitted','actualCallbackEqualsProvedChildRequired','initiallyNullListsRequired','coherentWrapperStorageRequired','finiteFloatProfile'))
  or cap.get('wholeGrammarAdmitted')is not False or cap.get('liveFormatterSelectionObserved')is not False):
  raise ValueError('currentFactoryConfig.exact-conditional-graph')
 records=cap.get('records',{});collections=cap.get('collections',{})
 if not isinstance(records,dict)or set(records)!=set(source.PLANS):raise ValueError('currentFactoryConfig.exact-record-set')
 if not isinstance(collections,dict)or set(collections)!={source.list_key(n)for n in source.COLLECTIONS}:
  raise ValueError('currentFactoryConfig.exact-list-set')
 language.validate(cap.get('langKey',{}))
 components={source.record_key(n):r for n,r in records.items()}
 for name in source.ordered_types():
  row=records[name];plan=source.PLANS[name]
  if(not isinstance(row,dict)or row.get('typeName')!=name or type(row.get('memberCount'))is not int or row['memberCount']!=len(plan)
   or any(row.get(k)is not True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','ordinaryAdapterAdmitted','actualCallbackEqualsProvedChildRequired'))
   or row.get('wholeGrammarAdmitted')is not False or row.get('liveFormatterSelectionObserved')is not False
   or type(row.get('referenceReaderMethodDefinition'))is not int or row['referenceReaderMethodDefinition']<0
   or type(row.get('referenceReaderTargetRva'))is not int or row['referenceReaderTargetRva']<=0):
   raise ValueError('currentFactoryConfig.exact-record-profile:'+name)
  source.bind_program(name,dict(wrappedType=name,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in plan]),row.get('program'),[])
  enums=row.get('enumBackings',{});wanted={n:t for n,t,k in plan if k=='scalar32'and t!='int'}
  if not isinstance(enums,dict)or set(enums)!=set(wanted):raise ValueError('currentFactoryConfig.exact-enum-set:'+name)
  for member,declared in wanted.items():
   enum=enums[member]
   if(not isinstance(enum,dict)or enum.get('typeName')!=declared or enum.get('backing')not in('int','uint')
    or enum.get('field')!=[declared,enum['backing'],16]):raise ValueError('currentFactoryConfig.exact-nominal-enum')
  for binding in row['program']['childBindings']:
   declared=binding['typeName'];key=binding['capability']
   if declared in records:
    expected=source.bind_reference({},_join(binding,'ReadValue'),dict(nativeInputs={},capabilities=components),key)
   elif declared in source.COLLECTIONS:
    expected=source.bind_collection({},_join(binding,'ReadPackable'),dict(nativeInputs={},capabilities=collections),key)
   elif declared==source.LANG:
    lang=cap['langKey'];expected=dict(fieldName=binding['fieldName'],typeName=source.LANG,capability='story-lang-key',
     readerMethodDefinition=lang['readerMethodDefinition'],sourceTargetRva=lang['sourceTargetRva'],managedBytes=16,
     referenceLaneOffsets=[0,8],wireMemberCount=1,positiveWireBytes=5,nullWireBytes=1,nonserializedRawText=True,
     actualCallbackEqualsProvedChildRequired=True,completeFieldTransferAndFrameProved=True)
   else:raise ValueError('currentFactoryConfig.unproved-child-type')
   if binding!=expected:raise ValueError('currentFactoryConfig.exact-child-source-binding')
 parents=cap.get('parentBindings',{})
 if not isinstance(parents,dict)or set(parents)!={'blackbox','predefinedParams'}:raise ValueError('currentFactoryConfig.exact-host-parents')
 direct=parents['blackbox'];common=source.bind_reference({},_join(direct,'ReadValue'),dict(nativeInputs={},capabilities=components),source.record_key(source.BLACKBOX))
 if direct!=dict(common,ownerType='Beyond.Gameplay.LevelData')or direct['fieldName']!='blackbox':
  raise ValueError('currentFactoryConfig.exact-blackbox-parent')
 parent=parents['predefinedParams']
 if(any(parent.get(k)!=v for k,v in dict(ownerType='Beyond.Gameplay.LevelData',fieldName='predefinedParams',
  typeName=source.LIST(source.PREDEFINED_HOST),capability=source.CAP,countLimit=source.LIMIT,
  initiallyNullListRequired=True,actualCallbackEqualsProvedChildRequired=True).items())
  or type(parent.get('readerMethodDefinition'))is not int or parent['readerMethodDefinition']<0
  or type(parent.get('sourceTargetRva'))is not int or parent['sourceTargetRva']<=0):
  raise ValueError('currentFactoryConfig.exact-predefined-parent')


def _node(reader,field,budget):
 if budget[0]<=0:raise ValueError(field+':factory-config-node-limit')
 budget[0]-=1


def _list(reader,field,element,kind,cap,budget):
 start=reader.offset;count=reader.number('<i',field+'.count')
 if not -1<=count<=source.LIMIT:raise ValueError(field+':factory-config-count-limit')
 if count>budget[0]:raise ValueError(field+':factory-config-node-limit')
 reader.need(max(count,0)*(4 if kind in('pooled-string-list','int32-list')else 1),field+'.elements')
 if kind in('pooled-string-list','int32-list'):budget[0]-=max(count,0)
 rows=[reader.string(field+'['+str(j)+']')if kind=='pooled-string-list'else reader.number('<i',field+'['+str(j)+']')if kind=='int32-list'else
  _record(reader,field+'['+str(j)+']',element,cap,budget)for j in range(max(count,0))]
 return dict(startOffset=start,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)


def _record(reader,field,name,cap,budget):
 _node(reader,field,budget);start=reader.offset;marker=reader.number('<B',field+'.memberCount');plan=source.PLANS[name]
 if marker==255:return None
 if marker!=len(plan):raise ValueError(field+':factory-config-member-count')
 out=dict(startOffset=start,recordType=name,memberCount=marker);ranges={};enums=cap['records'][name]['enumBackings']
 for member,declared,kind in plan:
  at=reader.offset;path=field+'.'+member
  if kind=='bool-byte':value=reader.boolean(path)
  elif kind=='scalar32':value=reader.number('<I'if enums.get(member,{}).get('backing')=='uint'else'<i',path)
  elif kind=='scalar64-bits':value=str(reader.number('<q'if declared=='long'else'<Q',path))
  elif kind=='float32-bits':value=reader.single(path)
  elif kind=='unity-vector3-raw12':value={axis:reader.single(path+'.'+axis)for axis in'xyz'}
  elif kind=='byte-payload':value=reader.string(path)
  elif kind=='lang-key':value=language.read(reader,path,cap['langKey'])
  elif kind=='factory-config-record':value=_record(reader,path,declared,cap,budget)
  elif kind in('factory-config-record-list','pooled-string-list','int32-list'):
   element,_=source.COLLECTIONS[declared];value=_list(reader,path,element,kind,cap,budget)
  else:raise ValueError(path+':closed-factory-config-operation')
  out[member]=value;ranges[member]=[at,reader.offset]
 out.update(endOffset=reader.offset,fieldRanges=ranges);return out


def read(reader,field,cap,*,host_field='blackbox'):
 validate(cap)
 if host_field not in('blackbox','predefinedParams'):raise ValueError('currentFactoryConfig.exact-host-selection')
 budget=getattr(reader,'_current_factory_config_budget',None)
 if budget is None:budget=[source.NODE_LIMIT];reader._current_factory_config_budget=budget
 if host_field=='blackbox':return _record(reader,field,source.BLACKBOX,cap,budget)
 return _list(reader,field,source.PREDEFINED_HOST,'factory-config-record-list',cap,budget)


def conditional_sources(cap):
 validate(cap)
 rows=[dict(typeName=source.BLACKBOX,recordTypes=source.ordered_types(),countLimit=source.LIMIT,nodeLimit=source.NODE_LIMIT,
  initiallyNullListsRequired=True,coherentWrapperStorageRequired=True,actualCallbackEqualsProvedChildRequired=True,
  runtimeFormatterSelectionObserved=False,factoryGameplayBehaviorProved=False)]
 rows.extend(dict(typeName=row['typeName'],elementType=row['elementType'],countLimit=row['countLimit'],
  initiallyNullListRequired=True,actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False,
  **({'actualCallbackEqualsPooledStringRequired':True}if row.get('actualCallbackEqualsPooledStringRequired')is True else{}))
  for row in cap['collections'].values())
 rows.append(dict(typeName=source.LANG,managedBytes=16,referenceLaneOffsets=[0,8],rawTextSerialized=False,
  actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False))
 return rows

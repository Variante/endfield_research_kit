"""Bounded Enemy30 syntax; object dictionary interiors remain unproved."""
from scripts.game_data.memorypack import leveldata_enemy_sources as source
from scripts.game_data.codecs.leveldata import current_enemy_nested as nested,current_enemy_dictionary as dictionary
from scripts.game_data.codecs.leveldata import current_ordinary_leaf as ordinary,current_nullable_float as nullable


def _array_cap(cap):
 s=source.strings
 if (not isinstance(cap,dict)or(cap.get('typeName'),cap.get('elementType'),cap.get('capability'),cap.get('countRange'))!=(s.ARRAY,s.TYPE,s.CAP,[-1,s.LIMIT])
  or any(type(cap.get(k))is not int or cap[k]!=v for k,v in dict(elementRawKind=14,headerBytes=4,elementWireBytes=4,
   managedElementBytes=8,countLimit=s.LIMIT,nullElementIndex=-2,emptyElementIndex=-1).items())
  or cap.get('elementEncoding')!='signed-int32-pool-index'
  or any(cap.get(k)is not True for k in('nullable','positiveCountsAdmitted','elementGrammarAdmitted','initiallyNullArrayRequired',
   'actualCallbackEqualsPooledStringRequired','wholeGrammarAdmitted'))or cap.get('liveFormatterSelectionObserved')is not False
  or type(cap.get('arrayReaderMethodDefinition'))is not int or cap['arrayReaderMethodDefinition']<0
  or type(cap.get('arrayReaderTargetRva'))is not int or cap['arrayReaderTargetRva']<=0):raise ValueError('currentEnemy.exact-pooled-string-array')


def validate(cap):
 if (not isinstance(cap,dict)or cap.get('typeName')!=source.TYPE or type(cap.get('memberCount'))is not int or cap['memberCount']!=30
  or type(cap.get('nodeLimit'))is not int or cap['nodeLimit']!=source.NODE_LIMIT
  or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','ordinaryAdapterAdmitted',
   'finiteFloatProfile','actualCallbackEqualsProvedChildRequired','coherentOriginalCacheRequired','compatibleRefreshOnly'))
  or any(cap.get(k)is not False for k in('wholeGrammarAdmitted','liveFormatterSelectionObserved','positiveObjectValuesAdmitted','coldInitializationObserved'))
  or cap.get('aiBlackboardAllowedCounts')!=[-1,0]):raise ValueError('currentEnemy.exact-bounded-profile')
 source.bind_program(dict(wrappedType=source.TYPE,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in source.PLAN]),cap.get('program'),[])
 wanted={n:t for n,t,k in source.PLAN if k=='scalar32'and t!='int'};enums=cap.get('enumBackings',{})
 if not isinstance(enums,dict)or set(enums)!=set(wanted):raise ValueError('currentEnemy.exact-enum-set')
 for member,name in wanted.items():
  enum=enums[member]
  if(not isinstance(enum,dict)or enum.get('typeName')!=name or enum.get('backing')not in('int','uint')
   or enum.get('field')!=[name,enum['backing'],16]):raise ValueError('currentEnemy.exact-nominal-enum')
 children=cap.get('childCapabilities',{});keys={source.dictionary.CAP,source.nested.KEYS[source.nested.BORN],source.nested.KEYS[source.nested.BUFF],
  source.BUFF_CAP,source.nullable.CAP,source.strings.CAP,source.AI_CAP}
 if not isinstance(children,dict)or set(children)!=keys:raise ValueError('currentEnemy.exact-child-set')
 dictionary.validate(children[source.dictionary.CAP]);nullable.validate(children[source.nullable.CAP]);_array_cap(children[source.strings.CAP])
 nested.validate(source.nested.BORN,children[source.nested.KEYS[source.nested.BORN]])
 nested.validate(source.nested.BUFF,children[source.nested.KEYS[source.nested.BUFF]])
 ordinary.validate(source.AI,children[source.AI_CAP])
 for binding in cap['program']['childBindings']:
  key=binding['capability'];method='ReadArray'if key==source.strings.CAP else'ReadValue'if key in(source.nested.KEYS[source.nested.BORN],source.AI_CAP)else'ReadPackable'
  join=dict(fieldName=binding['fieldName'],typeName=binding['typeName'],sourceTargetRva=binding.get('sourceTargetRva'),
   typedRequest=dict(methodName=method,methodArguments=['string']if method=='ReadArray'else[binding['typeName']],
    methodSpec=[binding.get('readerMethodDefinition')]))
  if method=='ReadArray':
   s=children[key]
   expected=dict(fieldName='idleBreakAnimations',typeName=source.strings.ARRAY,capability=key,
    readerMethodDefinition=s['arrayReaderMethodDefinition'],sourceTargetRva=s['arrayReaderTargetRva'],countLimit=source.LIMIT,
    initiallyNullArrayRequired=True,actualCallbackEqualsPooledStringRequired=True)
  else:
   binder=source.bind_reference if method=='ReadValue'else source.bind_collection
   expected=binder({},join,dict(nativeInputs={},capabilities=children),key)
  if binding!=expected:raise ValueError('currentEnemy.exact-child-source-binding')
 n=children[source.nullable.CAP]
 if cap.get('nullableSourceBinding')!=dict(fieldName='extraDelayToRecycleTime',typeName=source.nullable.TYPE,capability=source.nullable.CAP,
  readerMethodDefinition=n['readerMethodDefinition'],sourceTargetRva=n['sourceTargetRva']):raise ValueError('currentEnemy.exact-Nullable-source-binding')
 parent=cap.get('parentBinding',{})
 if (any(parent.get(k)!=v for k,v in dict(ownerType='Beyond.Gameplay.LevelData',fieldName=source.FIELD,
  typeName='System.Collections.Generic.List`1<'+source.TYPE+'>',capability=source.CAP,countLimit=source.LIMIT).items())
  or type(parent.get('countLimit'))is not int or type(parent.get('readerMethodDefinition'))is not int or parent['readerMethodDefinition']<0
  or type(parent.get('sourceTargetRva'))is not int or parent['sourceTargetRva']<=0
  or parent.get('actualCallbackEqualsProvedChildRequired')is not True):raise ValueError('currentEnemy.exact-host-parent')


def read(reader,field,cap):
 validate(cap);budget=getattr(reader,'_current_enemy_budget',None)
 if budget is None:budget=[source.NODE_LIMIT];reader._current_enemy_budget=budget
 if budget[0]<=0:raise ValueError(field+':enemy-node-limit')
 budget[0]-=1;start=reader.offset;marker=reader.number('<B',field+'.memberCount')
 if marker==255:return None
 if marker!=30:raise ValueError(field+':enemy-member-count')
 out=dict(startOffset=start,recordType=source.TYPE,memberCount=30);ranges={};children=cap['childCapabilities']
 for member,declared,kind in source.PLAN:
  at=reader.offset;path=field+'.'+member
  if kind=='scalar32':value=reader.number('<I'if declared!='int'and cap['enumBackings'][member]['backing']=='uint'else'<i',path)
  elif kind=='scalar64-bits':value=str(reader.number('<Q',path))
  elif kind=='bool-byte':value=reader.boolean(path)
  elif kind=='byte-payload':value=reader.string(path)
  elif kind=='unity-vector3-raw12':value={axis:reader.single(path+'.'+axis)for axis in'xyz'}
  elif kind=='enemy-empty-dictionary':value=dictionary.read(reader,path,children[source.dictionary.CAP])
  elif kind=='enemy-born-behavior':value=nested.read(reader,path,source.nested.BORN,children[source.nested.KEYS[source.nested.BORN]])
  elif kind=='enemy-ai-override':value=ordinary.read(reader,path,source.AI,children[source.AI_CAP])
  elif kind=='nullable-single-raw8':value=nullable.read(reader,path,children[source.nullable.CAP])
  elif kind in('enemy-spawn-buff-list','pooled-string-array'):
   count=reader.number('<i',path+'.count')
   if not -1<=count<=source.LIMIT:raise ValueError(path+':enemy-list-count-limit')
   if count>budget[0]:raise ValueError(path+':enemy-node-limit')
   reader.need(max(count,0)*(4 if kind=='pooled-string-array'else 1),path+'.elements');budget[0]-=max(count,0)
   rows=[reader.string(path+'['+str(j)+']')if kind=='pooled-string-array'else
    nested.read(reader,path+'['+str(j)+']',source.nested.BUFF,children[source.nested.KEYS[source.nested.BUFF]])for j in range(max(count,0))]
   value=dict(startOffset=at,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)
  else:raise ValueError(path+':closed-current-enemy-operation')
  out[member]=value;ranges[member]=[at,reader.offset]
 out.update(endOffset=reader.offset,fieldRanges=ranges);return out

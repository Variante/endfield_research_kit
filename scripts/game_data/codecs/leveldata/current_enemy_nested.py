"""Finite Enemy born/spawn definitions; no behavior, activation or parent claim."""
from scripts.game_data.memorypack import leveldata_enemy_nested_sources as source
from scripts.game_data.codecs.leveldata import current_leaf_record as leaf


def validate(name,cap):
 if(name not in source.PLANS or not isinstance(cap,dict)or cap.get('typeName')!=name
  or type(cap.get('memberCount'))is not int or cap['memberCount']!=len(source.PLANS[name])
  or type(cap.get('nodeLimit'))is not int or cap['nodeLimit']!=source.NODE_LIMIT
  or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','finiteFloatProfile','ordinaryAdapterAdmitted','actualCallbackEqualsProvedChildRequired'))
  or any(cap.get(k)is not False for k in('wholeGrammarAdmitted','liveFormatterSelectionObserved','parentFieldAdmitted','wholeOwnerAdmitted'))):
  raise ValueError('currentEnemyNested.exact-ordinary-profile:'+str(name))
 source.bind_program(name,dict(wrappedType=name,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in source.PLANS[name]]),cap.get('program'),[])
 for key in('referenceReaderMethodDefinition','referenceReaderTargetRva'):
  if type(cap.get(key))is not int or cap[key]<(1 if key=='referenceReaderTargetRva'else 0):raise ValueError('currentEnemyNested.literal-reference-source')
 wanted={n:t for n,t,k in source.PLANS[name]if k=='scalar32'};enums=cap.get('enumBackings',{})
 if not isinstance(enums,dict)or set(enums)!=set(wanted):raise ValueError('currentEnemyNested.exact-enum-set')
 for member,declared in wanted.items():
  enum=enums[member]
  if(not isinstance(enum,dict)or enum.get('typeName')!=declared or enum.get('backing')not in('int','uint')
   or enum.get('field')!=[declared,enum['backing'],16]):raise ValueError('currentEnemyNested.nominal-enum')
 element=source.SEQ if name==source.BORN else source.KV;children=cap.get('childCapabilities',{})
 expected={source.list_key(element),source.leaf_key(element)}|({source.STRING_CAP}if name==source.BORN else set())
 if not isinstance(children,dict)or set(children)!=expected:raise ValueError('currentEnemyNested.exact-child-set')
 leaf.validate(element,children[source.leaf_key(element)])
 for binding in cap['program']['childBindings']:
  if (type(binding.get('readerMethodDefinition'))is not int or binding['readerMethodDefinition']<0
   or type(binding.get('sourceTargetRva'))is not int or binding['sourceTargetRva']<=0):raise ValueError('currentEnemyNested.literal-list-parent')
  key=binding['capability'];join=dict(fieldName=binding['fieldName'],typeName=binding['typeName'],sourceTargetRva=binding['sourceTargetRva'],
   typedRequest=dict(methodName='ReadPackable',methodArguments=[binding['typeName']],methodSpec=[binding['readerMethodDefinition']]))
  if binding!=source.bind_collection({},join,dict(nativeInputs={},capabilities=children),key):raise ValueError('currentEnemyNested.complete-child-binding')
 if name==source.BORN:
  strings=children[source.STRING_CAP]
  if(strings.get('countRange')!=[-1,source.LIMIT]or type(strings.get('headerBytes'))is not int or strings['headerBytes']!=4
   or strings.get('initiallyNullListRequired')is not True):raise ValueError('currentEnemyNested.exact-string-list-framing')


def _read(reader,field,name,cap,budget):
 if budget[0]<=0:raise ValueError(field+':enemy-nested-node-limit')
 budget[0]-=1;start=reader.offset;marker=reader.number('<B',field+'.memberCount')
 if marker==255:return None
 if marker!=len(source.PLANS[name]):raise ValueError(field+':enemy-nested-member-count')
 out=dict(startOffset=start,recordType=name,memberCount=marker);ranges={}
 for member,declared,kind in source.PLANS[name]:
  at=reader.offset;path=field+'.'+member
  if kind=='scalar32':value=reader.number('<I'if cap['enumBackings'][member]['backing']=='uint'else'<i',path)
  elif kind=='float32-bits':value=reader.single(path)
  elif kind=='bool-byte':value=reader.boolean(path)
  elif kind=='byte-payload':value=reader.string(path)
  elif kind in('pooled-string-list','enemy-reference-list'):
   count=reader.number('<i',path+'.count')
   if not -1<=count<=source.LIMIT:raise ValueError(path+':enemy-nested-list-count-limit')
   if count>budget[0]:raise ValueError(path+':enemy-nested-node-limit')
   reader.need(max(count,0)*(4 if kind=='pooled-string-list'else 1),path+'.elements');budget[0]-=max(count,0)
   if kind=='pooled-string-list':rows=[reader.string(path+'['+str(j)+']')for j in range(max(count,0))]
   else:
    element=source.LISTS[declared];child=cap['childCapabilities'][source.leaf_key(element)]
    rows=[leaf.read(reader,path+'['+str(j)+']',element,child)for j in range(max(count,0))]
   value=dict(startOffset=at,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)
  else:raise ValueError(path+':closed-enemy-nested-operation')
  out[member]=value;ranges[member]=[at,reader.offset]
 out.update(endOffset=reader.offset,fieldRanges=ranges);return out


def read(reader,field,name,cap):
 validate(name,cap)
 budget=getattr(reader,'_current_enemy_nested_budget',None)
 if budget is None:budget=[source.NODE_LIMIT];reader._current_enemy_nested_budget=budget
 return _read(reader,field,name,cap,budget)

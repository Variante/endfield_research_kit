"""Finite NPC group placements; no activation or patrol behavior admission."""
from scripts.game_data.memorypack import leveldata_npc_group_sources as source


def validate(name,cap):
 if (name not in source.PLANS or not isinstance(cap,dict)or cap.get('typeName')!=name
   or type(cap.get('memberCount'))is not int or cap['memberCount']!=len(source.PLANS[name])
   or type(cap.get('nodeLimit'))is not int or cap['nodeLimit']!=source.NODE_LIMIT
   or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','finiteFloatProfile','ordinaryAdapterAdmitted','actualCallbackEqualsProvedChildRequired'))
   or any(cap.get(k)is not False for k in('wholeGrammarAdmitted','liveFormatterSelectionObserved'))):
  raise ValueError('currentNpcGroup.exact-finite-profile:'+name)
 declared=dict(wrappedType=name,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in source.PLANS[name]])
 source.bind_program(name,declared,cap.get('program'),[])
 enums=cap.get('enumBackings',{});expected={n:t for n,t,k in source.PLANS[name]if k=='scalar32'and t!='int'}
 if not isinstance(enums,dict)or set(enums)!=set(expected):raise ValueError('currentNpcGroup.exact-enum-set')
 for member,typename in expected.items():
  enum=enums[member]
  if enum.get('typeName')!=typename or enum.get('backing')not in('int','uint')or enum.get('field')!=[typename,enum['backing'],16]:
   raise ValueError('currentNpcGroup.exact-nominal-enum')
 children=cap.get('childCapabilities',{});keys={source.vectors.CAP}if name==source.SLOT else{source.SLOTS_CAP,source.SLOT_CAP}
 if not isinstance(children,dict)or set(children)!=keys:raise ValueError('currentNpcGroup.exact-child-set')
 if name==source.GROUP:validate(source.SLOT,children[source.SLOT_CAP])
 for binding in cap['program']['childBindings']:
  key=binding['capability']
  if (type(binding.get('readerMethodDefinition'))is not int or binding['readerMethodDefinition']<0
    or type(binding.get('sourceTargetRva'))is not int or binding['sourceTargetRva']<=0
    or type(binding.get('countLimit'))is not int or binding['countLimit']!=source.LIMIT):
   raise ValueError('currentNpcGroup.literal-list-binding')
  join=dict(fieldName=binding['fieldName'],typeName=binding['typeName'],sourceTargetRva=binding['sourceTargetRva'],
   typedRequest=dict(methodName='ReadPackable',methodArguments=[binding['typeName']],methodSpec=[binding['readerMethodDefinition']]))
  actual=source.bind_collection({},join,dict(nativeInputs={},capabilities={key:children[key]}),key)
  if binding!=actual:raise ValueError('currentNpcGroup.complete-list-binding')
 if name==source.GROUP:
  parent=cap.get('parentBinding',{})
  if (any(parent.get(k)!=v for k,v in dict(ownerType='Beyond.Gameplay.LevelData',fieldName='npcGroup',typeName='System.Collections.Generic.List`1<'+source.GROUP+'>',capability=source.CAP,countLimit=source.LIMIT).items())
    or type(parent.get('countLimit'))is not int or type(parent.get('readerMethodDefinition'))is not int or parent['readerMethodDefinition']<0
    or type(parent.get('sourceTargetRva'))is not int or parent['sourceTargetRva']<=0
    or parent.get('actualCallbackEqualsProvedChildRequired')is not True):raise ValueError('currentNpcGroup.exact-host-list-parent')


def _read(reader,field,name,cap,budget):
 if budget[0]<=0:raise ValueError(field+':npc-group-node-limit')
 budget[0]-=1;start=reader.offset;marker=reader.number('<B',field+'.memberCount')
 if marker==255:return None
 if marker!=len(source.PLANS[name]):raise ValueError(field+':npc-group-member-count')
 out=dict(startOffset=start,recordType=name,memberCount=marker);ranges={}
 for member,declared,kind in source.PLANS[name]:
  at=reader.offset;path=field+'.'+member
  if kind=='scalar32':value=reader.number('<I'if cap['enumBackings'].get(member,{}).get('backing')=='uint'else'<i',path)
  elif kind=='scalar64-bits':value=str(reader.number('<Q',path))
  elif kind=='bool-byte':value=reader.boolean(path)
  elif kind=='byte-payload':value=reader.string(path)
  elif kind in('vector3-list','npc-slot-list'):
   count=reader.number('<i',path+'.count')
   if not -1<=count<=source.LIMIT:raise ValueError(path+':npc-group-count-limit')
   reader.need(max(count,0)*(12 if kind=='vector3-list'else 1),path+'.elements');rows=[]
   for index in range(max(count,0)):
    item=path+f'[{index}]'
    value={axis:reader.single(item+'.'+axis)for axis in'xyz'}if kind=='vector3-list'else _read(reader,item,source.SLOT,cap['childCapabilities'][source.SLOT_CAP],budget)
    rows.append(value)
   value=dict(startOffset=at,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)
  else:raise ValueError(path+':closed-npc-group-operation')
  out[member]=value;ranges[member]=[at,reader.offset]
 out.update(endOffset=reader.offset,fieldRanges=ranges);return out


def read(reader,field,cap,*,name=source.GROUP):
 validate(name,cap);state=getattr(reader,'_current_npc_group_budget',None)
 if state is None:state=(cap,[source.NODE_LIMIT]);reader._current_npc_group_budget=state
 elif state[0]is not cap:raise ValueError(field+':mixed-current-npc-group-capability')
 return _read(reader,field,name,cap,state[1])

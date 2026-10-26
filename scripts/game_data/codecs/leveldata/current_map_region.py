"""Finite map-region cursor; current native/owner admission is separate."""
from scripts.game_data.memorypack import leveldata_map_region_sources as source


def validate(name,cap):
 if (name not in source.PLANS or not isinstance(cap,dict)or cap.get('typeName')!=name
   or type(cap.get('memberCount'))is not int or cap['memberCount']!=len(source.PLANS[name])
   or type(cap.get('nodeLimit'))is not int or cap['nodeLimit']!=source.NODE_LIMIT
   or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','finiteFloatProfile','ordinaryAdapterAdmitted','actualCallbackEqualsProvedChildRequired'))
   or any(cap.get(k)is not False for k in('wholeGrammarAdmitted','liveFormatterSelectionObserved'))):
  raise ValueError('currentMapRegion.exact-finite-profile:'+name)
 declared=dict(wrappedType=name,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in source.PLANS[name]])
 source.bind_program(name,declared,cap.get('program'),[])
 enums=cap.get('enumBackings',{});expected={n:t for n,t,k in source.PLANS[name]if k=='scalar32'and t!='int'}
 if set(enums)!=set(expected):raise ValueError('currentMapRegion.exact-enum-set')
 for field,typename in expected.items():
  enum=enums[field]
  if enum.get('typeName')!=typename or enum.get('backing')not in('int','uint')or enum.get('field')!=[typename,enum['backing'],16]:
   raise ValueError('currentMapRegion.exact-nominal-enum')
 children=cap.get('childCapabilities',{});keys={source.VECTORS_CAP}if name==source.SHAPE else{source.SHAPES_CAP,source.SHAPE_CAP,source.integers.CAP}
 if not isinstance(children,dict)or set(children)!=keys:raise ValueError('currentMapRegion.exact-child-set')
 if name==source.REGION:validate(source.SHAPE,children[source.SHAPE_CAP])
 for binding in cap['program']['childBindings']:
  key=binding['capability'];child=children[key]
  if (type(binding.get('readerMethodDefinition'))is not int or binding['readerMethodDefinition']<0
    or type(binding.get('sourceTargetRva'))is not int or binding['sourceTargetRva']<=0
    or type(binding.get('countLimit'))is not int or binding['countLimit']!=source.LIMIT
    or binding.get('actualCallbackEqualsProvedChildRequired')is not True):raise ValueError('currentMapRegion.literal-list-binding')
  join=dict(fieldName=binding['fieldName'],typeName=binding['typeName'],sourceTargetRva=binding['sourceTargetRva'],
   typedRequest=dict(methodName='ReadPackable',methodArguments=[binding['typeName']],methodSpec=[binding['readerMethodDefinition']]))
  source.bind_collection({},join,dict(nativeInputs={},capabilities={key:child}),key)
 if name==source.REGION:
  parent=cap.get('parentBinding',{})
  if (any(parent.get(k)!=v for k,v in dict(ownerType='Beyond.Gameplay.LevelData',fieldName='mapVolumeDatas',typeName='System.Collections.Generic.List`1<'+source.REGION+'>',capability=source.CAP,countLimit=source.LIMIT).items())
    or type(parent.get('countLimit'))is not int or type(parent.get('readerMethodDefinition'))is not int or parent['readerMethodDefinition']<0
    or type(parent.get('sourceTargetRva'))is not int or parent['sourceTargetRva']<=0
    or parent.get('actualCallbackEqualsProvedChildRequired')is not True):raise ValueError('currentMapRegion.exact-host-list-parent')


def _read(reader,field,name,cap,budget):
 if budget[0]<=0:raise ValueError(field+':map-node-limit')
 budget[0]-=1;start=reader.offset;marker=reader.number('<B',field+'.memberCount')
 if marker==255:return None
 if marker!=len(source.PLANS[name]):raise ValueError(field+':map-member-count')
 out=dict(startOffset=start,recordType=name,memberCount=marker);ranges={}
 for member,declared,kind in source.PLANS[name]:
  at=reader.offset;path=field+'.'+member
  if kind=='scalar32':value=reader.number('<I'if cap['enumBackings'].get(member,{}).get('backing')=='uint'else'<i',path)
  elif kind=='bool-byte':value=reader.boolean(path)
  elif kind=='byte-payload':value=reader.string(path)
  elif kind=='float32-bits':value=reader.single(path)
  elif kind=='unity-vector3-raw12':value={axis:reader.single(path+'.'+axis)for axis in'xyz'}
  elif kind in('vector2-list','int32-list','map-shape-list'):
   count=reader.number('<i',path+'.count')
   if not -1<=count<=source.LIMIT:raise ValueError(path+':map-count-limit')
   minimum={'vector2-list':8,'int32-list':4,'map-shape-list':1}[kind];reader.need(max(count,0)*minimum,path+'.elements');rows=[]
   for index in range(max(count,0)):
    item=path+f'[{index}]'
    if kind=='vector2-list':data={axis:reader.single(item+'.'+axis)for axis in'xy'}
    elif kind=='int32-list':data=reader.number('<i',item)
    else:data=_read(reader,item,source.SHAPE,cap['childCapabilities'][source.SHAPE_CAP],budget)
    rows.append(data)
   value=dict(startOffset=at,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)
  else:raise ValueError(path+':closed-map-operation')
  out[member]=value;ranges[member]=[at,reader.offset]
 out.update(endOffset=reader.offset,fieldRanges=ranges);return out


def read(reader,field,cap,*,name=source.REGION):
 validate(name,cap);state=getattr(reader,'_current_map_region_budget',None)
 if state is None:state=(cap,[source.NODE_LIMIT]);reader._current_map_region_budget=state
 elif state[0]is not cap:raise ValueError(field+':mixed-current-map-capability')
 return _read(reader,field,name,cap,state[1])

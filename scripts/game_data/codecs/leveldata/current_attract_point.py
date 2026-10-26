"""Finite stored attract-point cursor; activation and AI behavior are separate."""
from scripts.game_data.memorypack import leveldata_attract_point_sources as source


def validate(cap):
 if (not isinstance(cap,dict)or cap.get('typeName')!=source.TYPE
   or type(cap.get('memberCount'))is not int or cap['memberCount']!=len(source.PLAN)
   or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','finiteFloatProfile',
    'ordinaryAdapterAdmitted','actualCallbackEqualsProvedChildRequired'))
   or any(cap.get(k)is not False for k in('wholeGrammarAdmitted','liveFormatterSelectionObserved'))):
  raise ValueError('currentAttract.exact-finite-profile')
 declared=dict(wrappedType=source.TYPE,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in source.PLAN])
 source.bind_program(declared,cap.get('program'),[])
 enums=cap.get('enumBackings',{});expected={n:t for n,t,k in source.PLAN if k=='scalar32'and t!='int'}
 if not isinstance(enums,dict)or set(enums)!=set(expected):raise ValueError('currentAttract.exact-enum-set')
 for member,typename in expected.items():
  if enums[member]!=dict(typeName=typename,backing='int',field=[typename,'int',16]):
   raise ValueError('currentAttract.exact-nominal-Int32-enum')
 children=cap.get('childCapabilities',{})
 if not isinstance(children,dict)or set(children)!={source.ULONG_CAP,source.STRING_CAP}:raise ValueError('currentAttract.exact-child-set')
 for binding in cap['program']['childBindings']:
  key=binding['capability']
  if (type(binding.get('readerMethodDefinition'))is not int or binding['readerMethodDefinition']<0
    or type(binding.get('sourceTargetRva'))is not int or binding['sourceTargetRva']<=0
    or type(binding.get('countLimit'))is not int or binding['countLimit']!=source.LIMIT):
   raise ValueError('currentAttract.literal-list-binding')
  join=dict(fieldName=binding['fieldName'],typeName=binding['typeName'],sourceTargetRva=binding['sourceTargetRva'],
   typedRequest=dict(methodName='ReadPackable',methodArguments=[binding['typeName']],methodSpec=[binding['readerMethodDefinition']]))
  actual=source.bind_collection({},join,dict(nativeInputs={},capabilities={key:children[key]}),key)
  if binding!=actual:raise ValueError('currentAttract.complete-list-binding')
 parent=cap.get('parentBinding',{})
 if (any(parent.get(k)!=v for k,v in dict(ownerType='Beyond.Gameplay.LevelData',fieldName='npcAttractPointData',typeName=source.LIST,
   capability=source.CAP,countLimit=source.LIMIT).items())or type(parent.get('countLimit'))is not int
   or type(parent.get('readerMethodDefinition'))is not int or parent['readerMethodDefinition']<0
   or type(parent.get('sourceTargetRva'))is not int or parent['sourceTargetRva']<=0
   or parent.get('actualCallbackEqualsProvedChildRequired')is not True):raise ValueError('currentAttract.exact-host-list-parent')


def read(reader,field,cap):
 validate(cap);start=reader.offset;header=reader.number('<B',field+'.memberCount')
 if header==255:return None
 if header!=len(source.PLAN):raise ValueError(field+':attract-member-count')
 out=dict(startOffset=start,recordType=source.TYPE,memberCount=header);ranges={}
 for member,declared,kind in source.PLAN:
  at=reader.offset;path=field+'.'+member
  if kind=='scalar32':value=reader.number('<i',path)
  elif kind=='gameplay-tag32':value=reader.number('<I',path)
  elif kind=='scalar64-bits':value=str(reader.number('<Q',path))
  elif kind=='float32-bits':value=reader.single(path)
  elif kind=='bool-byte':value=reader.boolean(path)
  elif kind=='byte-payload':value=reader.string(path)
  elif kind in('unity-vector3-raw12','unity-quaternion-raw16'):
   value={axis:reader.single(path+'.'+axis)for axis in('xyzw'if kind=='unity-quaternion-raw16'else'xyz')}
  elif kind in('uint64-list','pooled-string-list'):
   count=reader.number('<i',path+'.count')
   if not -1<=count<=source.LIMIT:raise ValueError(path+':attract-count-limit')
   reader.need(max(count,0)*(8 if kind=='uint64-list'else 4),path+'.elements')
   rows=[str(reader.number('<Q',path+f'[{index}]'))if kind=='uint64-list'else reader.string(path+f'[{index}]')for index in range(max(count,0))]
   value=dict(startOffset=at,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)
  else:raise ValueError(path+':closed-attract-operation')
  out[member]=value;ranges[member]=[at,reader.offset]
 out.update(endOffset=reader.offset,fieldRanges=ranges);return out

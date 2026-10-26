"""Finite source-authenticated water-volume cursor without native admission."""
from scripts.game_data.memorypack import leveldata_water_sources as source
from scripts.game_data.codecs.leveldata import current_lang_key


def _parent(binding,field):
 if (field not in source.PARENT_FIELDS or not isinstance(binding,dict)
  or any(binding.get(k)!=v for k,v in dict(ownerType='Beyond.Gameplay.LevelData',fieldName=field,typeName=source.LIST,
   capability=source.CAP,countLimit=source.LIMIT).items())or type(binding.get('countLimit'))is not int
  or type(binding.get('readerMethodDefinition'))is not int or binding['readerMethodDefinition']<0
  or type(binding.get('sourceTargetRva'))is not int or binding['sourceTargetRva']<=0
  or binding.get('actualCallbackEqualsProvedChildRequired')is not True):raise ValueError('currentWater.exact-host-list-parent:'+field)


def validate(cap):
 if (not isinstance(cap,dict)or cap.get('typeName')!=source.TYPE
   or type(cap.get('memberCount'))is not int or cap['memberCount']!=len(source.PLAN)
   or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','finiteFloatProfile',
    'ordinaryAdapterAdmitted','actualCallbackEqualsProvedChildRequired'))
   or any(cap.get(k)is not False for k in('wholeGrammarAdmitted','liveFormatterSelectionObserved'))):
  raise ValueError('currentWater.exact-current-profile')
 declared=dict(wrappedType=source.TYPE,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in source.PLAN])
 source.bind_program(declared,cap.get('program'),[]);en=cap.get('enumBacking',{});typename=source.PLAN[2][1]
 if en.get('typeName')!=typename or en.get('backing')not in('int','uint')or en.get('field')!=[typename,en.get('backing'),16]:
  raise ValueError('currentWater.exact-enum-backing')
 children=cap.get('childCapabilities',{})
 if set(children)!={source.language.CAP,source.vectors.CAP}:raise ValueError('currentWater.exact-child-set')
 current_lang_key.validate(children[source.language.CAP])
 for binding in cap['program']['childBindings']:
  key=binding['capability'];child=children[key]
  if type(binding.get('readerMethodDefinition'))is not int or binding['readerMethodDefinition']<0 or type(binding.get('sourceTargetRva'))is not int or binding['sourceTargetRva']<=0:
   raise ValueError('currentWater.literal-child-binding')
  if key==source.language.CAP:
   if ((binding['readerMethodDefinition'],binding['sourceTargetRva'])!=(child['readerMethodDefinition'],child['sourceTargetRva'])
     or binding.get('managedBytes')!=16 or binding.get('referenceLaneOffsets')!=[0,8]
     or(binding.get('wireMemberCount'),binding.get('positiveWireBytes'),binding.get('nullWireBytes'))!=(1,5,1)
     or any(binding.get(k)is not True for k in('nonserializedRawText','actualCallbackEqualsProvedChildRequired','completeFieldTransferAndFrameProved'))):
    raise ValueError('currentWater.exact-LangKey-parent')
  else:
   join=dict(typeName=source.vectors.LIST,fieldName='points',sourceTargetRva=binding['sourceTargetRva'],
    typedRequest=dict(methodName='ReadPackable',methodArguments=[source.vectors.LIST],methodSpec=[binding['readerMethodDefinition']]))
   source.bind_vectors({},join,dict(nativeInputs={},capabilities={key:child}),key)
   if type(binding.get('countLimit'))is not int or binding['countLimit']!=source.LIMIT or binding.get('actualCallbackEqualsProvedChildRequired')is not True:
    raise ValueError('currentWater.exact-vector3-list-binding')
 _parent(cap.get('parentBinding',{}),'waterVolumes')
 additional=cap.get('additionalParentBindings',{})
 if not isinstance(additional,dict)or not set(additional)<={'riftVolumes'}:raise ValueError('currentWater.closed-additional-parent-set')
 for field,binding in additional.items():_parent(binding,field)


def parent_binding(cap,field):
 validate(cap)
 binding=cap['parentBinding']if field=='waterVolumes'else cap.get('additionalParentBindings',{}).get(field)
 _parent(binding,field)
 return binding


def read(reader,field,cap):
 validate(cap);start=reader.offset;header=reader.number('<B',field+'.memberCount')
 if header==255:return None
 if header!=len(source.PLAN):raise ValueError(field+':water-member-count')
 out=dict(startOffset=start,recordType=source.TYPE,memberCount=header);ranges={}
 for name,declared,kind in source.PLAN:
  at=reader.offset;path=field+'.'+name
  if kind=='scalar32':value=reader.number('<I'if cap['enumBacking']['backing']=='uint'and name=='fillEase'else'<i',path)
  elif kind=='scalar64-bits':value=reader.number('<q'if declared=='long'else'<Q',path);value=str(value)if declared=='ulong'else value
  elif kind=='float32-bits':value=reader.single(path)
  elif kind=='bool-byte':value=reader.boolean(path)
  elif kind=='byte-payload':value=reader.string(path)
  elif kind in('unity-vector3-raw12','unity-quaternion-raw16'):value={axis:reader.single(path+'.'+axis)for axis in('xyzw'if kind=='unity-quaternion-raw16'else'xyz')}
  elif kind=='lang-key':value=current_lang_key.read(reader,path,cap['childCapabilities'][source.language.CAP])
  elif kind=='vector3-list':
   count=reader.number('<i',path+'.count')
   if not -1<=count<=source.LIMIT:raise ValueError(path+':water-count-limit')
   reader.need(max(count,0)*12,path+'.elements')
   rows=[{axis:reader.single(path+f'[{index}].'+axis)for axis in'xyz'}for index in range(max(count,0))]
   value=dict(startOffset=at,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)
  else:raise ValueError(path+':closed-water-operation')
  out[name]=value;ranges[name]=[at,reader.offset]
 out.update(endOffset=reader.offset,fieldRanges=ranges);return out

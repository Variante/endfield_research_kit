"""Current CharInteract bounded sparse owner framing after native admission."""
import struct
from scripts.game_data.string_pool import resolve_string_pool_index

class SparsePerformDecodeError(ValueError):pass

def frame(data,fields,*,prefix=False,actor_fields=None,action_fields=None,strings=None):
 offset=0;values={};ranges=[];actions=[]
 def take(n,name):
  nonlocal offset
  if offset+n>len(data):raise SparsePerformDecodeError(f'{name}: truncated at 0x{offset:x}')
  start=offset;offset+=n;return data[start:offset]
 def empty(name):
  n=int.from_bytes(take(4,name+'.count'),'little',signed=True)
  if n not in(-1,0):raise SparsePerformDecodeError(f'{name}: count {n} outside reviewed null/zero source profile at 0x{offset-4:x}')
  return n
 def actor_value(name):
  marker=take(1,name+'.memberCount')[0]
  if marker==255:return None
  if marker!=13 or actor_fields is None or len(actor_fields)!=13:raise SparsePerformDecodeError(f'{name}: actor member count {marker} outside reviewed MC13/null source profile at 0x{offset-1:x}')
  result={}
  for f in actor_fields:
   wire=f['wire'];key=name+'.'+f['name'];raw=take(f['wireBytes'],key)
   if wire=='pooledStringIndex':
    index=struct.unpack('<i',raw)[0]
    try:value=resolve_string_pool_index(index,strings,key)
    except ValueError as error:raise SparsePerformDecodeError(f'{key}: {error}')from error
   elif wire=='boolByte':value=bool(raw[0])
   else:value=struct.unpack(dict(enum32='<i',uint64='<Q',int64='<q',float32='<f')[wire],raw)[0]
   result[f['name']]=value
  return result
 def pooled(name):
  index=struct.unpack('<i',take(4,name))[0]
  try:return resolve_string_pool_index(index,strings,name)
  except ValueError as error:raise SparsePerformDecodeError(f'{name}: {error}')from error
 def tag_list(name):
  n=struct.unpack('<i',take(4,name+'.count'))[0]
  if n not in(-1,0,1):raise SparsePerformDecodeError(f'{name}: count {n} outside reviewed null/zero/one source profile at 0x{offset-4:x}')
  if n!=1:return []
  if take(1,name+'.tag.memberCount')!=b'\1':raise SparsePerformDecodeError(f'{name}: tag member count outside reviewed MC1 source profile at 0x{offset-1:x}')
  return [struct.unpack('<i',take(4,name+'.tagId'))[0]]
 def action_value(name):
  start=offset;tag=take(1,name+'.unionTag')[0]
  if tag==255:return None
  if tag!=1 or action_fields is None or len(action_fields)!=18:raise SparsePerformDecodeError(f'{name}: action tag {tag} outside reviewed tag1 source profile at 0x{start:x}')
  marker=take(1,name+'.memberCount')[0]
  if marker!=18:raise SparsePerformDecodeError(f'{name}: action member count {marker}, expected18 at 0x{offset-1:x}')
  result={}
  for f in action_fields:
   key=name+'.'+f['name'];kind=f['kind']
   if f['name']=='bodyType':
    if take(1,key+'.memberCount')!=b'\3':raise SparsePerformDecodeError(f'{key}: body member count outside reviewed MC3 source profile at 0x{offset-1:x}')
    result[f['name']]=dict(bodyType=take(1,key+'.bodyType')[0],CustomId=struct.unpack('<i',take(4,key+'.CustomId'))[0],CustomName=pooled(key+'.CustomName'))
   elif kind=='list':result[f['name']]=tag_list(key)
   elif kind=='string':result[f['name']]=pooled(key)
   elif kind=='bool':result[f['name']]=bool(take(1,key)[0])
   else:result[f['name']]=struct.unpack('<ff'if kind=='object'else'<f'if kind=='float32'else'<I',take(8 if kind=='object'else 4,key))
   if kind not in('object','list','string','bool')and f['name']!='bodyType':result[f['name']]=result[f['name']][0]
  action=dict(sourceOffset=start,endOffset=offset,byteLength=offset-start,unionTag=tag,unionTagHex='0x0001',typeName='AddMultiTagsActData',memberCount=18,placement='loopActions',actionIndex=0,**result);actions.append(action);return action
 marker=take(1,'CharInteractPerformRuntimeCfg.memberCount')[0]
 if marker!=len(fields):raise SparsePerformDecodeError(f'CharInteractPerformRuntimeCfg: member count {marker}, expected {len(fields)}')
 for f in fields[:2]if prefix else fields:
  name,mode=f['name'],f['mode'];start=offset
  if mode=='bool':value=bool(take(1,name)[0])
  elif mode in('enum','float'):value=struct.unpack('<f'if mode=='float'else'<i',take(4,name))[0]
  elif mode=='out8'or name=='defaultSubPerformEntry':
   marker=take(1,name+'.memberCount')[0]
   if marker==255:value=None
   elif marker==1:
    value=empty(name+'.entries')
    if mode=='out8'and value!=0:raise SparsePerformDecodeError(f'{name}: dictionary count {value} outside reviewed zero source profile at 0x{offset-4:x}')
   else:raise SparsePerformDecodeError(f'{name}: member count {marker} outside reviewed 1/null source profile at 0x{start:x}')
  elif mode=='reference'and f['type']=='System.Collections.Generic.List`1<Beyond.Gameplay.Core.GameplayTag>':
   n=int.from_bytes(take(4,name+'.count'),'little',signed=True)
   if n not in(-1,0,1):raise SparsePerformDecodeError(f'{name}: count {n} outside reviewed null/zero/one source profile at 0x{start:x}')
   value=[]
   if n==1:
    if take(1,name+'.tag.memberCount')!=b'\1':raise SparsePerformDecodeError(f'{name}: tag member count outside reviewed MC1 source profile at 0x{offset-1:x}')
    value.append(struct.unpack('<i',take(4,name+'.tagId'))[0])
  elif mode=='reference'and f['type']=='System.Collections.Generic.List`1<Beyond.Gameplay.Core.CharInteractPerform.CharInteractPerformActor>':
   n=int.from_bytes(take(4,name+'.count'),'little',signed=True)
   if n not in(-1,0,1):raise SparsePerformDecodeError(f'{name}: count {n} outside reviewed null/zero/one actor source profile at 0x{start:x}')
   value=[actor_value(name+'[0]')]if n==1 else []
  elif mode=='reference'and name=='loopActions':
   n=struct.unpack('<i',take(4,name+'.count'))[0]
   if n not in(-1,0,1):raise SparsePerformDecodeError(f'{name}: count {n} outside reviewed null/zero/one action source profile at 0x{start:x}')
   value=[action_value(name+'[0]')]if n==1 else []
  elif mode=='reference'and f['type'].startswith('System.Collections.Generic.List`1<'):value=empty(name)
  else:raise SparsePerformDecodeError(f'{name}: unreviewed current child at 0x{start:x}')
  values[name]=value;ranges.append(dict(name=name,startOffset=start,endOffset=offset))
 if prefix:return dict(status='bounded_prefix',schemaStatus='named_prefix_opaque_remainder',serializedMemberCount=len(fields),bytesConsumed=offset,activeTagCount=len(values['activeTags'])if isinstance(values['activeTags'],list)else 0,activeTags=values['activeTags']if isinstance(values['activeTags'],list)else [],allowInheritPerform=values['allowInheritPerform'],opaqueRemainderOffset=offset,opaqueRemainderLength=len(data)-offset)
 if offset!=len(data):raise SparsePerformDecodeError(f'CharInteractPerformRuntimeCfg: trailing {len(data)-offset} bytes at 0x{offset:x}')
 actors={f['name']:values[f['name']]for f in fields if f['type']=='System.Collections.Generic.List`1<Beyond.Gameplay.Core.CharInteractPerform.CharInteractPerformActor>'}
 return dict(status='exact_current_char_interact_frame',schemaStatus='named_exact',wholeSchemaExact=True,schemaMappingId='endfield.char-interact-perform-runtime-cfg.sparse.v4',unionMappingId=None,serializedMemberCount=len(fields),bytesConsumed=offset,actionCount=len(actions),actionTypeCounts={'AddMultiTagsActData':len(actions)}if actions else{},actions=actions,actorCollections=actors,audioActionCount=0,audioActions=[],fieldRanges=ranges)

"""Current sparse pooled LevelScript dictionary; the List parent is separate."""
import math
from scripts.game_data.codecs.levelscript.param_graph import Reader as GraphReader,ParamGraphDecodeError
from scripts.game_data.levelscript_interactive_native import validate
class LevelInteractiveCodecError(ValueError):pass
class Reader(GraphReader):
 def key_value(self,field):
  start=self.offset;value=super().key_value(field)
  return dict(value,startOffset=start,endOffset=self.offset)if value is not None else None
 def boolean(self,field):
  start=self.offset;value=self.number('<B',field)
  if value not in(0,1):raise ParamGraphDecodeError(f'{field}:invalid-bool,offset={start},actual={value}')
  return bool(value)
 def single(self,field):
  start=self.offset;value=self.number('<f',field)
  if not math.isfinite(value):raise ParamGraphDecodeError(f'{field}:nonfinite,offset={start},actual={value}')
  return value
 def null_ints(self,field):
  start=self.offset;count=self.number('<i',field+'.count')
  if count!=-1:raise ParamGraphDecodeError(f'{field}:current-nonnull-int-list-source-unproved,offset={start},actual={count},expected=-1')
  return dict(status='null',count=None,values=None)
 def components(self,field):
  start=self.offset;count=self.number('<i',field+'.count')
  if count==-1:return dict(status='null',count=None,entries=None)
  if count not in(0,1,2):raise ParamGraphDecodeError(f'{field}:current-count-source-unproved,offset={start},actual={count},supported=0..2')
  entries=[];seen=set()
  for n in range(count):
   child=f'{field}[{n}]';key=self.number('<i',child+'.componentType')
   if key in seen:raise ParamGraphDecodeError(f'{child}:duplicate-component-key,offset={self.offset-4},actual={key}')
   seen.add(key);entries.append(dict(componentTypeRaw=key,properties=self.items(child+'.properties',self.key_value)))
  return dict(status='present',count=count,entries=entries,startOffset=start,endOffset=self.offset)
 def condition(self,field):
  """Historical/sparse profile stays FF-only; current owners override this."""
  at=self.offset;marker=self.number('<B',field)
  if marker!=255:raise ParamGraphDecodeError(f'{field}:current-positive-condition-source-unproved,offset={at},actual={marker},expected=255')
  return None
 def record(self,field):
  start=self.offset
  if not self.member(field,25):return None
  row=dict(serializedMemberCount=25,startOffset=start,aoiRadiusTypeRaw=self.number('<i',field+'.aoiRadiusType'))
  row['belongLevelScriptId']=str(self.number('<Q',field+'.belongLevelScriptId'));row['createStateRaw']=self.number('<i',field+'.createState');row['dependencyGroupId']=str(self.number('<Q',field+'.dependencyGroupId'));row['entityDataIdKey']=self.string(field+'.entityDataIdKey');row['entityTypeRaw']=self.number('<i',field+'.entityType')
  for name in('forceLoad','keepCrossMap'):row[name]=self.boolean(field+'.'+name)
  row['levelLogicId']=str(self.number('<Q',field+'.levelLogicId'));row['overrideSendDieEvent']=self.boolean(field+'.overrideSendDieEvent')
  for name in('position','rotation','scale'):row[name]={axis:self.single(field+'.'+name+'.'+axis)for axis in'xyz'}
  row['sendDieEvent']=self.boolean(field+'.sendDieEvent');row['componentProperties']=self.components(field+'.componentProperties');row['globalIntKeyList']=self.null_ints(field+'.globalIntKeyList');row['globalProperties']=self.items(field+'.globalProperties',self.key_value)
  for name in('hideInDialog','isClientOnly','isLocked'):row[name]=self.boolean(field+'.'+name)
  row['mapIntKeyList']=self.null_ints(field+'.mapIntKeyList');row['mapProperties']=self.items(field+'.mapProperties',self.key_value);row['modelScale']=self.single(field+'.modelScale')
  row['progressLockCondition']=self.condition(field+'.progressLockCondition');row['properties']=self.items(field+'.properties',self.key_value);row['endOffset']=self.offset;return row

def decode_interactive_dictionary(data,cursor,*,strings=None,game_root=None,gameassembly=None,metadata=None):
 reader=Reader(data,cursor,strings,'interactives');start=cursor
 try:
  count=reader.number('<i','interactives.count')
  if count==-1:return dict(status='null',count=None,entries=None),reader.offset
  if count not in(0,1):raise ParamGraphDecodeError(f'interactives:current-count-source-unproved,offset={start},actual={count},supported=0..1')
  if count:
   audit=validate(game_root=game_root,gameassembly=gameassembly,metadata=metadata)
   if audit.get('status')!='validated':
    error=LevelInteractiveCodecError(f"interactives.nativeContract:offset={start},status={audit.get('status')},detail={str(audit.get('detail',''))[:500]}");error.diagnostics=audit;raise error
  entries=[]
  for n in range(count):
   key=reader.number('<I',f'interactives[{n}].key');entries.append(dict(key=key,value=reader.record(f'interactives[{n}].value')))
  return dict(status='present',count=count,entries=entries,startOffset=start,endOffset=reader.offset),reader.offset
 except ParamGraphDecodeError as error:raise LevelInteractiveCodecError(str(error))from error

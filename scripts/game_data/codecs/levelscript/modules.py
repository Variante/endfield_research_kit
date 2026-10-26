"""Current conditional Rolling/Launcher wire profile; every positive dictionary revalidates native composition."""
import math,struct

class ModuleStructureDecodeError(ValueError):pass

def decode_rolling(data,offset):
 cursor=offset
 def read(fmt):
  nonlocal cursor
  size=struct.calcsize('<'+fmt)
  if type(cursor) is not int or cursor<0 or cursor+size>len(data):raise ModuleStructureDecodeError('truncated rolling body at '+str(cursor))
  value=struct.unpack_from('<'+fmt,data,cursor);cursor+=size;return value[0] if len(value)==1 else value
 def marker(count):
  value=read('B')
  if value not in (255,count):raise ModuleStructureDecodeError('member-count at '+str(cursor-1)+': '+str(value))
  return value!=255
 def boolean():
  value=read('B');return bool(value)
 def single():
  value=read('f')
  if not math.isfinite(value):raise ModuleStructureDecodeError('unsupported nonfinite float profile at '+str(cursor-4))
  return value
 def entity():
  if not marker(3):return dict(logicId=0,slotId=0,useSlotId=False,useSlotIdRawByte=0,constantWasNull=True)
  logic,slot,flag=read('QIB');return dict(logicId=logic,slotId=slot,useSlotId=bool(flag),useSlotIdRawByte=flag,constantWasNull=False)
 def collection(child,min_bytes):
  count=read('i')
  if count==-1:return None
  if count<0 or count>(len(data)-cursor)//min_bytes:raise ModuleStructureDecodeError('invalid or truncated collection count at '+str(cursor-4)+': '+str(count))
  return [child() for _ in range(count)]
 def launcher():
  if not marker(7):return None
  value=dict(closeAfterRepatriate=boolean(),freezeTime=single(),intervalTimeList=collection(single,4),launcherId=read('Q'),maxCount=read('i'),preGenerateCount=read('i'),templateRollingStone=entity());return value
 if not marker(3):return None,cursor
 return dict(disableWhenCompleted=boolean(),id=read('Q'),launcherDataList=collection(launcher,1)),cursor


from scripts.game_data import levelscript_module_structures_native as native

class LevelScriptModuleCodecError(ValueError):pass

def _decode_module_dictionary(data,cursor,rolling_tag,diagnostics=None,*,count_limit=16384,canonical=True):
 """Pure bounded profile; provenance and native selection belong to its owner."""
 if type(rolling_tag)is not int or not 0<=rolling_tag<=65535:raise LevelScriptModuleCodecError('modules.selected-tag-required')
 if type(canonical)is not bool or(count_limit is not None and(type(count_limit)is not int or count_limit<0)):
  raise LevelScriptModuleCodecError('modules.literal-profile-required')
 start=cursor
 def read(fmt):
  nonlocal cursor
  size=struct.calcsize('<'+fmt)
  if type(cursor)is not int or cursor<0 or cursor+size>len(data):raise LevelScriptModuleCodecError('truncated modules at '+str(cursor))
  value=struct.unpack_from('<'+fmt,data,cursor)[0];cursor+=size;return value
 count=read('i')
 if count==-1:return dict(status='null',count=None,entries=None),cursor
 if count<0 or count>(len(data)-cursor)//9:raise LevelScriptModuleCodecError('invalid/truncated modules count at '+str(start)+': '+str(count))
 if count_limit is not None and(type(count_limit)is not int or not 0<=count<=count_limit):raise LevelScriptModuleCodecError('modules.count-limit:'+str(count))
 entries=[];seen=set()
 for index in range(count):
  key=read('Q')
  if key in seen:raise LevelScriptModuleCodecError('duplicate module key: '+str(key))
  seen.add(key);header=cursor;tag=read('B');width=1
  if tag==255:value=None;tag=None
  else:
   if tag==250:
    tag=read('H');width=3
    if canonical and tag<250:raise LevelScriptModuleCodecError('noncanonical extended module tag at '+str(header))
   elif tag>250:raise LevelScriptModuleCodecError('unsupported reserved module marker at '+str(header))
   if tag!=rolling_tag:
    if diagnostics is not None:diagnostics.append(dict(gate='currentRollingOnlyModuleWireProfile',moduleIndex=index,moduleKey=str(key),moduleUnionTag=tag,moduleOffset=header,expectedModuleTag=rolling_tag))
    return None,start
   try:value,cursor=decode_rolling(data,cursor)
   except ModuleStructureDecodeError as error:raise LevelScriptModuleCodecError(str(error))from error
  row=dict(key=str(key),tag=None if tag is None else f'0x{tag:04x}',tagWidth=width,type='RollingStoneControllerData' if tag is not None else None,valueWasNull=value is None)
  if value is not None:
   launchers=value['launcherDataList']
   for launcher in launchers or []:
    if launcher is not None:
     floats=launcher['intervalTimeList'];launcher['intervalTimeList']=dict(status='null'if floats is None else'present',count=None if floats is None else len(floats),values=floats);launcher['templateRollingStone']['logicId']=str(launcher['templateRollingStone']['logicId'])
   row.update(serializedMemberCount=3,disableWhenCompleted=value['disableWhenCompleted'],id=str(value['id']),fields=dict(launcherDataList=dict(status='null'if launchers is None else'present',count=None if launchers is None else len(launchers),values=launchers)))
  entries.append(row)
 return dict(status='present',count=count,entries=entries,startOffset=start,endOffset=cursor),cursor


def decode_module_dictionary(data,cursor,diagnostics=None):
 """Legacy public frontdoor retains its selected native gate for positives."""
 if type(cursor)is not int or not 0<=cursor<=len(data)-4:raise LevelScriptModuleCodecError('truncated modules at '+str(cursor))
 count=struct.unpack_from('<i',data,cursor)[0];tag=0
 if count < -1 or count>max(0,(len(data)-cursor-4)//9):raise LevelScriptModuleCodecError('invalid/truncated modules count at '+str(cursor)+': '+str(count))
 if count>0:
  audit=native.validate()
  if audit.get('status')!='validated':
   if diagnostics is not None:diagnostics.append(dict(gate='currentModuleWireNative',nativeAudit=audit))
   raise LevelScriptModuleCodecError('modules.native:'+str(audit.get('status'))+':'+str(audit.get('detail',''))[:500])
  tag=audit['rollingTag']
 return _decode_module_dictionary(data,cursor,tag,diagnostics,count_limit=None,canonical=False)

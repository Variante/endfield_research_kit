"""Current pooled Blackboard class/list/Param; stored inputs, no runtime values."""
import struct
from scripts.game_data.levelscript_blackboard_native import validate
from scripts.game_data.string_pool import resolve_string_pool_index

class BlackboardDecodeError(ValueError):pass

def decode_blackboard_param(data,offset,*,strings=None,game_root=None):
 audit=validate(game_root=game_root)
 if audit['status']!='validated':raise BlackboardDecodeError(f"blackboard.native:status={audit['status']},detail={audit.get('detail','')}")
 def number(fmt,field):
  nonlocal offset
  size=struct.calcsize(fmt)
  if type(offset) is not int or not 0<=offset<=len(data)-size:raise BlackboardDecodeError(f'{field}:truncated,offset={offset},size={size}')
  value=struct.unpack_from(fmt,data,offset)[0];offset+=size;return value
 def member(field):
  marker=number('<B',field+'.memberCount')
  if marker==255:return False
  if marker!=4:raise BlackboardDecodeError(f'{field}:member-count,expected=4,actual={marker},offset={offset-1}')
  return True
 def string(field):return resolve_string_pool_index(number('<i',field+'.poolIndex'),strings,field)
 if not member('blackboard.param'):return None,offset
 count=number('<i','blackboard.count')
 if not -1<=count<=10000:raise BlackboardDecodeError(f'blackboard.count:unsupported={count},offset={offset-4}')
 values=None if count==-1 else []
 for i in range(max(count,0)):
  field=f'blackboard[{i}]'
  values.append(dict(key=string(field+'.key'),useString=number('<B',field+'.useString')!=0,valueFloat=number('<f',field+'.valueFloat'),valueString=string(field+'.valueString')) if member(field) else None)
 result=dict(value=values,idRef=number('<i','blackboard.idRef'),paramSource=number('<i','blackboard.paramSource'),path=string('blackboard.path'))
 return result,offset

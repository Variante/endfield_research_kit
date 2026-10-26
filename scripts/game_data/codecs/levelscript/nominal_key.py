"""Stored pooled nominal Params; each managed ABI has its own native proof."""
import struct
from scripts.game_data.levelscript_nominal_key_param_native import validate
from scripts.game_data.memorypack.operation_native_validation import validate_native
from scripts.game_data.string_pool import resolve_string_pool_index

class NominalKeyDecodeError(ValueError):pass

def decode_nominal_key_param(data,offset,*,kind,strings=None,game_root=None):
 if kind not in('Param<LangKey>','Param<GlobalBuffId>'):raise NominalKeyDecodeError('nominalKey:unsupported-kind')
 global_id=kind=='Param<GlobalBuffId>';label='globalBuffId'if global_id else'langKey';key='id'if global_id else'key'
 audit=validate_native(validate,kind=kind,game_root=game_root)
 if audit['status']!='validated':raise NominalKeyDecodeError(f"{label}.native:status={audit['status']},detail={audit.get('detail','')}")
 def number(fmt,field):
  nonlocal offset
  size=struct.calcsize(fmt)
  if type(offset)is not int or not 0<=offset<=len(data)-size:raise NominalKeyDecodeError(f'{field}:truncated,offset={offset},size={size}')
  value=struct.unpack_from(fmt,data,offset)[0];offset+=size;return value
 def string(field):return resolve_string_pool_index(number('<i',field+'.poolIndex'),strings,field)
 marker=number('<B',label+'.memberCount')
 if marker==255:return None,offset
 if marker!=4:raise NominalKeyDecodeError(f'{label}:member-count,expected=4,actual={marker},offset={offset-1}')
 marker=number('<B',label+'.value.memberCount')
 if marker not in(1,255):raise NominalKeyDecodeError(f'{label}.value:member-count,expected=1/255,actual={marker},offset={offset-1}')
 value={key:None if marker==255 else string(label+'.value.'+key)}
 return dict(value=value,idRef=number('<i',label+'.idRef'),paramSource=number('<i',label+'.paramSource'),path=string(label+'.path')),offset

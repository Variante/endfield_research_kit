"""Stored pooled LangKey Param; nonserialized rawText is never projected."""
import struct
from scripts.game_data.levelscript_nominal_key_param_native import validate
from scripts.game_data.string_pool import resolve_string_pool_index

class NominalKeyDecodeError(ValueError):pass

def decode_lang_key_param(data,offset,*,strings=None,game_root=None):
 audit=validate(game_root=game_root)
 if audit['status']!='validated':raise NominalKeyDecodeError(f"langKey.native:status={audit['status']},detail={audit.get('detail','')}")
 def number(fmt,field):
  nonlocal offset
  size=struct.calcsize(fmt)
  if type(offset)is not int or not 0<=offset<=len(data)-size:raise NominalKeyDecodeError(f'{field}:truncated,offset={offset},size={size}')
  value=struct.unpack_from(fmt,data,offset)[0];offset+=size;return value
 def string(field):return resolve_string_pool_index(number('<i',field+'.poolIndex'),strings,field)
 marker=number('<B','langKey.memberCount')
 if marker==255:return None,offset
 if marker!=4:raise NominalKeyDecodeError(f'langKey:member-count,expected=4,actual={marker},offset={offset-1}')
 marker=number('<B','langKey.value.memberCount')
 if marker not in(1,255):raise NominalKeyDecodeError(f'langKey.value:member-count,expected=1/255,actual={marker},offset={offset-1}')
 value=dict(key=None if marker==255 else string('langKey.value.key'))
 return dict(value=value,idRef=number('<i','langKey.idRef'),paramSource=number('<i','langKey.paramSource'),path=string('langKey.path')),offset

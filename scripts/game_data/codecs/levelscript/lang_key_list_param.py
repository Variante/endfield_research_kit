"""Bounded current LangKey list Param; rawText is not serialized or projected."""
import struct
from scripts.game_data.levelscript_lang_key_list_param_native import validate
from scripts.game_data.memorypack.operation_native_validation import validate_native
from scripts.game_data.string_pool import resolve_string_pool_index


def decode_lang_key_list_param(data,offset,*,strings=None,game_root=None):
 audit=validate_native(validate,game_root=game_root);expected=dict(status='validated',codecKind='Param<List<LangKey>>',memberCount=4,collectionCounts=[-1,0,1],elementRuntimeBytes=16,elementEncoding='MC1/int32-pool-index-or-default',pathEncoding='int32-pool-index')
 if any(audit.get(k)!=v for k,v in expected.items()):raise ValueError(f"langKeyList.native:status={audit.get('status')},detail={str(audit.get('detail',''))[:500]}")
 def number(fmt,field):
  nonlocal offset
  size=struct.calcsize(fmt)
  if type(offset)is not int or not 0<=offset<=len(data)-size:raise ValueError(f'{field}:truncated,offset={offset},size={size}')
  value=struct.unpack_from(fmt,data,offset)[0];offset+=size;return value
 def pool(field):return resolve_string_pool_index(number('<i',field+'.poolIndex'),strings,field)
 marker=number('<B','langKeyList.memberCount')
 if marker==255:return None,offset
 if marker!=4:raise ValueError(f'langKeyList:member-count,expected=4,actual={marker},offset={offset-1}')
 count=number('<i','langKeyList.value.count')
 if count not in(-1,0,1):raise ValueError(f'langKeyList.value:count-unproved,expected=[-1,0,1],actual={count},offset={offset-4}')
 value=None if count==-1 else[]
 if count==1:
  marker=number('<B','langKeyList.value[0].memberCount')
  if marker not in(1,255):raise ValueError(f'langKeyList.value[0]:member-count,expected=1/255,actual={marker},offset={offset-1}')
  value.append(dict(key=None if marker==255 else pool('langKeyList.value[0].key')))
 return dict(value=value,idRef=number('<i','langKeyList.idRef'),paramSource=number('<i','langKeyList.paramSource'),path=pool('langKeyList.path')),offset

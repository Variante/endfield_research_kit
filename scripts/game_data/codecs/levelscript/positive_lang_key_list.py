"""Own LangKey MC1/default elements under the managed16 list source gate."""
import struct
from scripts.game_data.levelscript_positive_lang_key_lists_native import validate,KIND,LIMIT
from scripts.game_data.memorypack.operation_native_validation import validate_native
from scripts.game_data.string_pool import resolve_string_pool_index


def decode_param(data,offset,*,strings=None,game_root=None):
 audit=validate_native(validate,game_root=game_root)
 expected=dict(status='validated',codecKind=KIND,memberCount=4,countLimit=LIMIT,wireCountBytes=4,
  elementRuntimeBytes=16,elementEncoding='MC1/int32-pool-index-or-default',
  pathEncoding='int32-pool-index',positiveCountsAdmitted=True)
 if any(type(audit.get(k))is not type(v)or audit.get(k)!=v for k,v in expected.items()):
  raise ValueError('positiveLangKeyList.native:status='+str(audit.get('status'))+',detail='+str(audit.get('detail',''))[:500])
 def number(fmt,field):
  nonlocal offset
  size=struct.calcsize(fmt)
  if type(offset)is not int or not 0<=offset<=len(data)-size:raise ValueError(field+':truncated')
  value,=struct.unpack_from(fmt,data,offset);offset+=size;return value
 def pool(field):return resolve_string_pool_index(number('<i',field+'.poolIndex'),strings,field)
 marker=number('<B','positiveLangKeyList.memberCount')
 if marker==255:return None,offset
 if marker!=4:raise ValueError('positiveLangKeyList.member-count='+str(marker))
 count=number('<i','positiveLangKeyList.value.count')
 if count < -1 or count>LIMIT or count>len(data)-offset:raise ValueError('positiveLangKeyList.count-unproved='+str(count))
 value=None if count==-1 else[]
 for i in range(max(count,0)):
  marker=number('<B',f'positiveLangKeyList.value[{i}].memberCount')
  if marker not in(1,255):raise ValueError('positiveLangKeyList.element-member-count='+str(marker))
  value.append(dict(key=None if marker==255 else pool(f'positiveLangKeyList.value[{i}].key')))
 return dict(value=value,idRef=number('<i','positiveLangKeyList.idRef'),
  paramSource=number('<i','positiveLangKeyList.paramSource'),path=pool('positiveLangKeyList.path')),offset

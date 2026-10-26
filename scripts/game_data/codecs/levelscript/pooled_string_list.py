"""Bounded literal List<string> (at most three); Param<List<string>> is separate."""
import struct
from scripts.game_data.levelscript_pooled_string_list_native import validate
from scripts.game_data.memorypack.operation_native_validation import validate_native
from scripts.game_data.string_pool import resolve_string_pool_index

class PooledStringListDecodeError(ValueError):pass


def decode_pooled_string_list(data,offset,*,strings=None,game_root=None):
 audit=validate_native(validate,game_root=game_root)
 if audit.get('status')!='validated'or audit.get('codecKind')!='List<string>':raise PooledStringListDecodeError(f"stringList.native:status={audit.get('status')},detail={audit.get('detail','')}")
 if type(offset)is not int or not 0<=offset<=len(data)-4:raise PooledStringListDecodeError(f'stringList.count:truncated,offset={offset}')
 count,=struct.unpack_from('<i',data,offset);offset+=4
 if count==-1:return None,offset
 if not 0<=count<=3:raise PooledStringListDecodeError(f'stringList.count:unsupported={count},offset={offset-4}')
 if count>(len(data)-offset)//4:raise PooledStringListDecodeError(f'stringList:truncated,offset={offset},count={count},available={len(data)-offset}')
 result=[resolve_string_pool_index(struct.unpack_from('<i',data,offset+4*i)[0],strings,f'stringList[{i}]')for i in range(count)]
 return result,offset+4*count

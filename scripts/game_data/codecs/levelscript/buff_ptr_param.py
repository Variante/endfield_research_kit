"""Current managed16 BuffPtr and concrete MC1 Buff pooled-key grammar."""
import struct
from scripts.game_data.string_pool import resolve_string_pool_index
from scripts.game_data.levelscript_buff_ptr_param_native import (
 current_buff_ptr_params,prepared_buff_ptr_audit,CAPABILITIES)


def decode_buff_ptr_param(data,offset,*,strings=None,game_root=None,operation=None):
 if operation is None:
  with current_buff_ptr_params(game_root=game_root,strings=strings)as selected:
   return decode_buff_ptr_param(data,offset,strings=strings,game_root=game_root,operation=selected)
 audit=prepared_buff_ptr_audit(operation,game_root=game_root,strings=strings)
 if audit.get('status')!='validated' or any(audit.get(k)!=v for k,v in CAPABILITIES.items()):raise ValueError('buffPtrParam.native:missing-exact-capability')
 if type(offset)is not int or not 0<=offset<len(data):return None
 marker=data[offset];offset+=1
 if marker==255:return None,offset
 if marker!=4 or offset>=len(data):return None
 child=data[offset];offset+=1;uid=0;obj=None
 if child==1:
  if offset>=len(data):return None
  nested=data[offset];offset+=1
  if nested==2:
   if offset+5>len(data):return None
   uid=struct.unpack_from('<I',data,offset)[0];offset+=4
   marker=data[offset];offset+=1
   if marker==1:
    if offset+4>len(data):return None
    count=struct.unpack_from('<i',data,offset)[0];offset+=4
    if not -1<=count<=CAPABILITIES['buffObjectListMaxCount']or offset+max(count,0)*4>len(data):return None
    keys=(None if count==-1 else [resolve_string_pool_index(
     struct.unpack_from('<i',data,offset+4*i)[0],strings,'Buff.modifiedBBKeys['+str(i)+']')for i in range(count)])
    offset+=max(count,0)*4;obj={'modifiedBBKeys':keys}
   elif marker!=255:return None
  elif nested!=255:return None
 elif child!=255:return None
 if offset+12>len(data):return None
 id_ref,source,index=struct.unpack_from('<iii',data,offset)
 path=resolve_string_pool_index(index,strings,'path')
 return dict(value={'ptr':{'cachedUid':uid,'obj':obj}},idRef=id_ref,paramSource=source,path=path),offset+12

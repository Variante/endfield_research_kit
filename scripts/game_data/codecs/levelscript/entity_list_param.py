"""Selected finite EntityPtr-list constants and pooled Param tails."""
import struct
from scripts.game_data.codecs.levelscript.entity_ptr_param import decode_entity_ptr_value
from scripts.game_data.string_pool import resolve_string_pool_index
from scripts.game_data.levelscript_entity_list_param_native import current_entity_list_params,prepared_entity_list_audit,CAPABILITIES


def decode_entity_list_constant(data,offset,*,max_count=10000):
 """Pure stored framing; caller must compose the independent native source."""
 if type(max_count)is not int or not 0<=max_count<=10000:raise ValueError('entityList.invalid-count-bound')
 if type(offset)is not int or not 0<=offset<=len(data)-4:return None
 count,=struct.unpack_from('<i',data,offset);cursor=offset+4
 if not -1<=count<=max_count:return None
 if count==-1:return None,cursor
 values=[]
 for _ in range(count):
  decoded=decode_entity_ptr_value(data,cursor)
  if decoded is None:return None
  value,cursor=decoded;values.append(value)
 return values,cursor


def decode_entity_list_param(data,offset,*,strings=None,game_root=None,operation=None):
 if operation is None:
  with current_entity_list_params(game_root=game_root,strings=strings)as selected:
   return decode_entity_list_param(data,offset,strings=strings,game_root=game_root,operation=selected)
 audit=prepared_entity_list_audit(operation,game_root=game_root,strings=strings)
 if audit.get('status')!='validated'or any(audit.get(k)!=v for k,v in CAPABILITIES.items()):
  raise ValueError('entityList.native:missing-exact-capability')
 if type(offset)is not int or not 0<=offset<len(data):return None
 if data[offset]==255:return None,offset+1
 if data[offset]!=4:return None
 constant=decode_entity_list_constant(data,offset+1,max_count=CAPABILITIES['maxConstantCount'])
 if constant is None:return None
 values,cursor=constant
 if cursor+12>len(data):return None
 id_ref,source,index=struct.unpack_from('<iii',data,cursor)
 if index<-2:return None
 path=resolve_string_pool_index(index,strings,'path')
 return dict(value=values,idRef=id_ref,paramSource=source,path=path),cursor+12

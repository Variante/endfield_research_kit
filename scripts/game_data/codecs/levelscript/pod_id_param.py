"""Stored raw8 ID plus two signed bindings and an explicit pool index."""
import struct
from scripts.game_data.string_pool import resolve_string_pool_index

def decode_pod_id_param(data,offset,*,strings=None):
 if type(offset) is not int or not 0<=offset<len(data):return None
 if data[offset]==255:return None,offset+1
 if data[offset]!=4 or offset+21>len(data):return None
 value,id_ref,source,index=struct.unpack_from('<Qiii',data,offset+1)
 path=resolve_string_pool_index(index,strings,'path')
 return dict(value={'id':value},idRef=id_ref,paramSource=source,path=path),offset+21

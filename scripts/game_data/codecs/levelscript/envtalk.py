"""Current pooled EnvTalk values, below the owning native contract gate."""
import struct
from scripts.game_data.string_pool import resolve_string_pool_index
from scripts.game_data.codecs.levelscript.params import decode_pooled_param_tail

def decode_envtalk_param(data,offset,*,strings=None):
 if type(offset) is not int or not 0<=offset<len(data):return None
 if data[offset]==255:return None,offset+1
 if data[offset]!=4 or offset+5>len(data):return None
 count=struct.unpack_from('<i',data,offset+1)[0];cursor=offset+5
 if count==-1:values=None
 elif not 0<=count<=10000:return None
 else:
  values=[]
  for _ in range(count):
   if cursor>=len(data):return None
   marker=data[cursor];cursor+=1
   if marker==255:values.append(dict(envTalkId=None,odds=0));continue
   if marker!=2 or cursor+8>len(data):return None
   index,odds=struct.unpack_from('<ii',data,cursor);cursor+=8
   values.append(dict(envTalkId=resolve_string_pool_index(index,strings,'envTalkId'),odds=odds))
 tail=decode_pooled_param_tail(data,cursor,strings=strings)
 if tail is None:return None
 detail,end=tail;return dict(value=values,**detail),end

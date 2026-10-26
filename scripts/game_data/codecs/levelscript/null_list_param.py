"""Only the native-proved null List constant; positive counts remain unavailable."""
from .params import decode_pooled_param_tail
def decode_null_list_param(payload,cursor,*,strings=None):
 if type(cursor) is not int or not 0<=cursor<len(payload):return None
 if payload[cursor]==255:return None,cursor+1
 if payload[cursor:cursor+5]!=b'\x04\xff\xff\xff\xff':return None
 tail=decode_pooled_param_tail(payload,cursor+5,strings=strings)
 if tail is None:return None
 detail,end=tail
 return dict(value=None,**detail),end

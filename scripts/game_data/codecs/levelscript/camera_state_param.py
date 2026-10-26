"""Pooled reference Param; admit only a native-proved null camera constant."""
from .params import decode_pooled_param_tail


def decode_camera_state_param(data,offset,*,strings=None):
 if type(offset) is not int or not 0<=offset<len(data):return None
 if data[offset]==255:return None,offset+1
 if offset+14>len(data) or data[offset:offset+2]!=b'\x04\xff':return None
 tail=decode_pooled_param_tail(data,offset+2,strings=strings)
 if tail is None:return None
 binding,end=tail
 return dict(value=None,**binding),end

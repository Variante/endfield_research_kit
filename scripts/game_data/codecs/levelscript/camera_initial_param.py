"""Pooled camera Param with an authenticated managed field layout."""
import math,struct
from .params import decode_pooled_param_tail


def decode_camera_initial_param(data,offset,fields,*,strings=None):
 if type(offset) is not int or not 0<=offset<len(data):return None
 if data[offset]==255:return None,offset+1
 if data[offset]!=4 or offset+37>len(data):return None
 raw=data[offset+1:offset+25];value={}
 for name,kind,at in fields:
  if kind=='bool':value[name]=bool(raw[at])
  elif kind=='float':
   number=struct.unpack_from('<f',raw,at)[0]
   if not math.isfinite(number):return None
   value[name]=number
  else:raise ValueError('cameraInitialParam.unproved-field-kind:'+str(kind))
 tail=decode_pooled_param_tail(data,offset+25,strings=strings)
 if tail is None:return None
 binding,end=tail
 return dict(value=value,rawConstantHex=raw.hex(),**binding),end

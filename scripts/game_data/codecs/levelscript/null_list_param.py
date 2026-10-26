"""Native-gated null constants and the current EntityPtr zero-element subset."""
import struct
from .params import decode_pooled_param_tail

def decode_null_list_param(payload,cursor,*,collection_counts,strings=None):
 if collection_counts not in ([-1],[-1,0]) or any(type(n)is not int for n in collection_counts):return None
 if type(cursor) is not int or not 0<=cursor<len(payload):return None
 if payload[cursor]==255:return None,cursor+1
 if payload[cursor]!=4 or cursor+5>len(payload):return None
 count=struct.unpack_from('<i',payload,cursor+1)[0]
 if count not in collection_counts:return None
 tail=decode_pooled_param_tail(payload,cursor+5,strings=strings)
 if tail is None:return None
 detail,end=tail
 return dict(value=None if count==-1 else [],**detail),end

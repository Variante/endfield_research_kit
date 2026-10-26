"""Stored current positive EventArgsPtr key plus Param bindings and pooled path."""
import struct
from scripts.game_data.string_pool import resolve_string_pool_index
from .params import decode_pooled_param_tail

def decode_event_args_param(payload,cursor,*,strings=None):
 if type(cursor) is not int or not 0<=cursor<len(payload):return None
 if payload[cursor]==255:return None,cursor+1
 if cursor+18>len(payload) or payload[cursor:cursor+2]!=b'\x04\x01':return None
 key=resolve_string_pool_index(struct.unpack_from('<i',payload,cursor+2)[0],strings,'EventArgsPtr.key')
 tail=decode_pooled_param_tail(payload,cursor+6,strings=strings)
 if tail is None:return None
 detail,end=tail
 return dict(value=dict(key=key),**detail),end

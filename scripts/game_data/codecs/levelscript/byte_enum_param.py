"""Stored four-member Params with a raw unsigned-byte enum constant."""
from scripts.game_data.codecs.levelscript.params import decode_pooled_param_tail

def decode_byte_enum_param(payload,cursor,*,strings=None):
    if type(cursor) is not int or not 0<=cursor<len(payload):return None
    if payload[cursor]==0xff:return None,cursor+1
    if payload[cursor]!=4 or cursor+14>len(payload):return None
    tail=decode_pooled_param_tail(payload,cursor+2,strings=strings)
    if tail is None:return None
    detail,end=tail
    return {'value':payload[cursor+1],**detail},end

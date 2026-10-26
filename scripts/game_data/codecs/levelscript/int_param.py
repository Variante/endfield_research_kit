"""Stored pool-present integer Params; callers authenticate each native component."""
from __future__ import annotations
import struct
from .params import decode_pooled_param_tail


def decode_int_param(payload, cursor, *, strings=None,unsigned=False,width=4):
    if type(cursor) is not int or not 0<=cursor<len(payload) or type(unsigned) is not bool or type(width) is not int or width not in (4,8):return None
    if payload[cursor]==0xff:return None,cursor+1
    if cursor+width+13>len(payload) or payload[cursor]!=4:return None
    tail=decode_pooled_param_tail(payload,cursor+width+1,strings=strings)
    if tail is None:return None
    detail,end=tail
    fmt={4:'I' if unsigned else 'i',8:'Q' if unsigned else 'q'}[width]
    return {'value':struct.unpack_from('<'+fmt,payload,cursor+1)[0],**detail},end

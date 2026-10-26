"""Stored pool-present finite Single Param; callers authenticate its native code."""
from __future__ import annotations
import math
import struct
from .params import decode_pooled_param_tail


def decode_float_param(payload, cursor, *, strings=None):
    if type(cursor) is not int or not 0<=cursor<len(payload):return None
    if payload[cursor]==0xff:return None,cursor+1
    if cursor+17>len(payload) or payload[cursor]!=4:return None
    value=struct.unpack_from('<f',payload,cursor+1)[0]
    if not math.isfinite(value):return None
    tail=decode_pooled_param_tail(payload,cursor+5,strings=strings)
    if tail is None:return None
    detail,end=tail
    return {'value':value,**detail},end

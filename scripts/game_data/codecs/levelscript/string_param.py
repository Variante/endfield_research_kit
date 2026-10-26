"""Stored pool-present String Param; callers authenticate both pooled reads."""
from __future__ import annotations
import struct
from scripts.game_data.string_pool import resolve_string_pool_index
from .params import decode_pooled_param_tail


def decode_string_param(payload, cursor, *, strings=None):
    if type(cursor) is not int or not 0<=cursor<len(payload):return None
    if payload[cursor]==0xff:return None,cursor+1
    if cursor+17>len(payload) or payload[cursor]!=4:return None
    tail=decode_pooled_param_tail(payload,cursor+5,strings=strings)
    if tail is None:return None
    value=resolve_string_pool_index(struct.unpack_from('<i',payload,cursor+1)[0],strings,'value')
    detail,end=tail
    return {'value':value,**detail},end

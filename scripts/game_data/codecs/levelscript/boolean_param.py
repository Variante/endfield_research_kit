"""Stored pool-present Boolean Param; callers authenticate its native component."""
from __future__ import annotations
from .params import decode_pooled_param_tail


def decode_bool_param(payload, cursor, *, strings=None):
    if type(cursor) is not int or not 0<=cursor<len(payload):return None
    if payload[cursor]==0xff:return None,cursor+1
    if cursor+14>len(payload) or payload[cursor]!=4 or payload[cursor+1] not in (0,1):return None
    tail=decode_pooled_param_tail(payload,cursor+2,strings=strings)
    if tail is None:return None
    detail,end=tail
    return {'value':bool(payload[cursor+1]),**detail},end

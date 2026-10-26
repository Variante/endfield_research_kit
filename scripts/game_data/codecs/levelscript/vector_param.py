"""Finite vector Params with separately authenticated sources and pooled paths."""
from __future__ import annotations
import math
import struct
from .params import decode_pooled_param_tail


def decode_vector_param(payload,cursor,*,dimension,strings=None):
    if type(cursor) is not int or not 0<=cursor<len(payload) or type(dimension) is not int or dimension not in (2,3):return None
    if payload[cursor]==0xff:return None,cursor+1
    if cursor+13+dimension*4>len(payload) or payload[cursor]!=4:return None
    values=struct.unpack_from('<'+'f'*dimension,payload,cursor+1)
    if not all(math.isfinite(v) for v in values):return None
    tail=decode_pooled_param_tail(payload,cursor+1+dimension*4,strings=strings)
    if tail is None:return None
    detail,end=tail
    return {'value':dict(zip(('x','y','z'),values)),**detail},end

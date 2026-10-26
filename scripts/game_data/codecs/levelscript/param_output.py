"""Two-field ParamOutput storage with a signed matching-pool path index."""
from __future__ import annotations
import struct
from scripts.game_data.string_pool import resolve_string_pool_index


def decode_param_output(data,offset,*,strings=None):
    if type(offset) is not int or not 0<=offset<len(data):return None
    if data[offset]==0xff:return None,offset+1
    if data[offset]!=2 or offset+9>len(data):return None
    target,index=struct.unpack_from('<ii',data,offset+1)
    return {'paramTarget':target,'path':resolve_string_pool_index(index,strings,'paramOutput.path')},offset+9

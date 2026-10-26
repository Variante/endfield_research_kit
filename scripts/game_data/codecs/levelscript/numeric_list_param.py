"""Finite independently gated Int32/UInt32/Single list Params with pooled tails."""
from __future__ import annotations

import struct
from scripts.game_data.string_pool import resolve_string_pool_index


def decode_numeric_list_param(payload,cursor,*,kind,strings=None,max_count=10000):
    formats={'Param<List<int>>':'i','Param<List<uint>>':'I','Param<List<float>>':'f'}
    if kind not in formats:
        raise ValueError('numericListParam:unproved-codec='+str(kind))
    if strings is None:raise ValueError('numericListParam:matching-StringPool-required')
    if type(max_count)is not int or not 0<=max_count<=10000:
        raise ValueError('numericListParam:invalid-count-bound')
    if type(cursor)is not int or not 0<=cursor<len(payload):return None
    if payload[cursor]==255:return None,cursor+1
    if payload[cursor]!=4 or cursor+5>len(payload):return None
    count=struct.unpack_from('<i',payload,cursor+1)[0];start=cursor+5
    if not -1<=count<=max_count or start+max(count,0)*4>len(payload):return None
    values=(None if count==-1 else list(struct.unpack_from('<'+str(count)+formats[kind],payload,start)))
    tail=start+max(count,0)*4
    if tail+12>len(payload):return None
    id_ref,source,index=struct.unpack_from('<iii',payload,tail)
    if index < -2:return None
    path=resolve_string_pool_index(index,strings,'path')
    result=dict(value=values,idRef=id_ref,paramSource=source,path=path)
    if kind=='Param<List<float>>':
        # Python's float conversion may quiet a signaling NaN; retain the exact
        # native MOVSS payload independently of that display value.
        result['valueBits']=(None if count==-1 else
            [payload[start+i*4:start+i*4+4].hex()for i in range(count)])
    return result,tail+12

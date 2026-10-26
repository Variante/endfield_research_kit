"""Stored raw16 LevelScriptPtr Param; callers must authenticate its current native component."""
import struct
from scripts.game_data.codecs.levelscript.params import decode_pooled_param_tail

def decode_levelscript_ptr_param(data,offset,*,strings=None):
    if type(offset) is not int or not 0<=offset<len(data):return None
    if data[offset]==255:return None,offset+1
    if data[offset]!=4 or offset+29>len(data):return None
    tail=decode_pooled_param_tail(data,offset+17,strings=strings)
    if tail is None:return None
    binding,end=tail;script_id,level_id=struct.unpack_from('<Qi',data,offset+1)
    return {'value':{'scriptId':str(script_id),'levelId':level_id,'paddingHex':data[offset+13:offset+17].hex()},**binding},end

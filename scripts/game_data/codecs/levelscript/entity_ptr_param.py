"""Stored current EntityPtr Param; caller must authenticate all native components."""
import struct
from scripts.game_data.codecs.levelscript.params import decode_pooled_param_tail


def decode_entity_ptr_param(data,offset,*,strings=None):
    if type(offset) is not int or not 0<=offset<len(data):return None
    if data[offset]==255:return None,offset+1
    if data[offset]!=4 or offset+2>len(data):return None
    marker=data[offset+1];cursor=offset+2
    if marker==3:
        if cursor+13>len(data):return None
        logic,slot,flag=struct.unpack_from('<QIB',data,cursor);cursor+=13
    elif marker==255:logic=slot=flag=0
    else:return None
    tail=decode_pooled_param_tail(data,cursor,strings=strings)
    if tail is None:return None
    binding,end=tail
    return dict(logicId=logic,slotId=slot,useSlotId=bool(flag),useSlotIdRawByte=flag,constantWasNull=marker==255,**binding),end

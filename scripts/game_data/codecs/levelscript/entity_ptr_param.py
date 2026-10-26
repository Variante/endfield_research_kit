"""Stored current EntityPtr Param; caller authenticates all native components.

The proved Boolean leaf reads one byte and normalizes nonzero to true; it
does not reject values above one. Retain that original byte beside the bool.
"""
import struct
from scripts.game_data.codecs.levelscript.params import decode_pooled_param_tail


def decode_entity_ptr_value(data,offset):
    """Stored value grammar; the composing caller authenticates its source."""
    if type(offset) is not int or not 0<=offset<len(data):return None
    marker=data[offset];cursor=offset+1
    if marker==3:
        if cursor+13>len(data):return None
        logic,slot,flag=struct.unpack_from('<QIB',data,cursor);cursor+=13
    elif marker==255:logic=slot=flag=0
    else:return None
    return dict(logicId=logic,slotId=slot,useSlotId=bool(flag),useSlotIdRawByte=flag,constantWasNull=marker==255),cursor


def decode_entity_ptr_param(data,offset,*,strings=None):
    if type(offset) is not int or not 0<=offset<len(data):return None
    if data[offset]==255:return None,offset+1
    if data[offset]!=4:return None
    constant=decode_entity_ptr_value(data,offset+1)
    if constant is None:return None
    value,cursor=constant
    tail=decode_pooled_param_tail(data,cursor,strings=strings)
    if tail is None:return None
    binding,end=tail
    return dict(**value,**binding),end

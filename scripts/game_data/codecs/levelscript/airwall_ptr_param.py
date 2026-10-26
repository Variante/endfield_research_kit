"""Stored raw24 AirWallPtr plus signed bindings and explicit StringPool index."""
import struct
from scripts.game_data.string_pool import resolve_string_pool_index

def decode_airwall_ptr_param(data,offset,*,strings=None):
 if type(offset)is not int or not 0<=offset<len(data):return None
 if data[offset]==255:return None,offset+1
 if data[offset]!=4 or offset+37>len(data):return None
 raw=data[offset+1:offset+25];logic=struct.unpack_from('<Q',raw,8)[0];slot=struct.unpack_from('<I',raw,16)[0];id_ref,source,index=struct.unpack_from('<iii',data,offset+25);path=resolve_string_pool_index(index,strings,'path')
 return dict(value=dict(useSlotId=bool(raw[0]),useSlotIdRawByte=raw[0],logicId=logic,slotId=slot,rawHex=raw.hex().upper()),idRef=id_ref,paramSource=source,path=path),offset+37

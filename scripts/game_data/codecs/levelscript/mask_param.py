"""Current reference mask Param, with positive objects restricted to a null curve."""
import math,struct
from scripts.game_data.codecs.levelscript.params import decode_pooled_param_tail


def decode_mask_param(data,offset,*,strings=None,audio_fields=None):
 if type(offset) is not int or not 0<=offset<len(data):return None
 if data[offset]==255:return None,offset+1
 if offset+14>len(data) or data[offset]!=4:return None
 if data[offset+1]==255:value=None;end=offset+2
 else:
  if offset+44>len(data) or data[offset+1]!=6 or data[offset+18]!=255 or not audio_fields:return None
  raw=data[offset+2:offset+18];audio=dict(rawHex=raw.hex().upper())
  for field in audio_fields:
   value=struct.unpack_from('<'+field['format'],raw,field['offset'])[0]
   if isinstance(value,float) and not math.isfinite(value):return None
   if field['typeName']=='bool':
    if value not in (0,1):return None
    value=bool(value)
   audio[field['name']]=value
  fade_in,fade_out,mask_type=struct.unpack_from('<ffi',data,offset+19)
  if not math.isfinite(fade_in) or not math.isfinite(fade_out):return None
  value=dict(audioBlackScreenBehaviour=audio,curve=None,fadeInDuration=fade_in,fadeOutDuration=fade_out,maskType=mask_type,useCurve=bool(data[offset+31]));end=offset+32
 tail=decode_pooled_param_tail(data,end,strings=strings)
 if tail is None:return None
 binding,end=tail
 return dict(value=value,**binding),end

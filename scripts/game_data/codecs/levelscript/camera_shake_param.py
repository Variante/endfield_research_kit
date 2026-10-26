"""Current managed8 CameraShakeConfigPtr Param with explicit pooled key/path."""
import struct
from scripts.game_data.string_pool import resolve_string_pool_index
from scripts.game_data.levelscript_camera_shake_param_native import (
 current_camera_shake_params,prepared_camera_shake_audit,CAPABILITIES)


def decode_camera_shake_param(data,offset,*,strings=None,game_root=None,operation=None):
 if operation is None:
  with current_camera_shake_params(game_root=game_root,strings=strings) as selected:
   return decode_camera_shake_param(data,offset,strings=strings,game_root=game_root,operation=selected)
 audit=prepared_camera_shake_audit(operation,game_root=game_root,strings=strings)
 if audit.get('status')!='validated' or any(audit.get(k)!=v for k,v in CAPABILITIES.items()):raise ValueError('cameraShakeParam.native:missing-exact-capability')
 if type(offset) is not int or not 0<=offset<len(data):return None
 marker=data[offset];offset+=1
 if marker==255:return None,offset
 if marker!=4 or offset>=len(data):return None
 child=data[offset];offset+=1
 if child==255:key=None
 elif child==1:
  if offset+4>len(data):return None
  index=struct.unpack_from('<i',data,offset)[0];offset+=4
  key=resolve_string_pool_index(index,strings,'cameraShakeConfigPtr.key')
 else:return None
 if offset+12>len(data):return None
 id_ref,source,index=struct.unpack_from('<iii',data,offset)
 path=resolve_string_pool_index(index,strings,'path')
 return dict(value={'key':key},idRef=id_ref,paramSource=source,path=path),offset+12

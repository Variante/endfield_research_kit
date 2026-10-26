"""Selected current PosRot value and pooled reference Param grammar."""
import math,struct
from scripts.game_data.string_pool import resolve_string_pool_index
from scripts.game_data.levelscript_pos_rot_native import load_pos_rot_contract
from scripts.game_data.memorypack.operation_native_validation import validate_native

class PosRotDecodeError(ValueError):pass

def child(data,offset):
 if type(offset) is not int or not 0<=offset<len(data):raise PosRotDecodeError('PosRot.child:truncated')
 marker=data[offset]
 if marker==255:values=(0.,)*6;end=offset+1
 elif marker==2:
  if offset+25>len(data):raise PosRotDecodeError('PosRot.child:truncated')
  values=struct.unpack_from('<6f',data,offset+1);end=offset+25
 else:raise PosRotDecodeError(f'PosRot.member-count:offset={offset},expected=2/255,actual={marker}')
 if not all(math.isfinite(v) for v in values):raise PosRotDecodeError('PosRot.finite-vector-profile')
 return {name:dict(zip(('x','y','z'),values[i*3:i*3+3])) for i,name in enumerate(('eulerAngles','position'))},end

def collection(data,offset):
 if type(offset) is not int or not 0<=offset<=len(data)-4:raise PosRotDecodeError('PosRot.list-count:truncated')
 count=struct.unpack_from('<i',data,offset)[0];offset+=4
 if count==-1:return None,offset
 if not 0<=count<=4096:raise PosRotDecodeError(f'PosRot.list-count:expected=-1..4096,actual={count}')
 values=[]
 for _ in range(count):value,offset=child(data,offset);values.append(value)
 return values,offset

def parameter(data,offset,*,strings=None):
 if type(offset) is not int or not 0<=offset<len(data):raise PosRotDecodeError('PosRot.Param:truncated')
 if data[offset]==255:return None,offset+1
 if data[offset]!=4:raise PosRotDecodeError('PosRot.Param:member-count')
 value,offset=collection(data,offset+1)
 if offset+12>len(data):raise PosRotDecodeError('PosRot.Param:tail-truncated')
 id_ref,source,index=struct.unpack_from('<iii',data,offset)
 try:path=resolve_string_pool_index(index,strings,'PosRot.Param.path')
 except ValueError as error:raise PosRotDecodeError(str(error)) from error
 return dict(value=value,idRef=id_ref,paramSource=source,path=path),offset+12

def _gate(game_root):
 _,audit=validate_native(load_pos_rot_contract,game_root=game_root,include_fact=False)
 if audit.get('status')!='validated' or audit.get('parentProofStatus')!='selected-generated-route':raise PosRotDecodeError(f"PosRot.native:{audit.get('status')},check={audit.get('failedCheck',audit.get('failedGate'))},detail={audit.get('detail','')}")

def decode_pos_rot(data,offset,*,game_root=None):
 _gate(game_root);return child(data,offset)

def decode_pos_rot_list(data,offset,*,game_root=None):
 _gate(game_root);return collection(data,offset)

def decode_pos_rot_param(data,offset,*,strings=None,game_root=None):
 _gate(game_root);return parameter(data,offset,strings=strings)

"""Current pooled key value8 and its independently authenticated Param route."""
import struct
from scripts.game_data.string_pool import resolve_string_pool_index
from scripts.game_data.levelscript_curve_key_param_native import load_curve_key_param_contract

class CurveKeyParamDecodeError(ValueError):pass

def decode_wire(data,offset,*,strings=None):
 def need(size):
  if type(offset) is not int or not 0<=offset<=len(data)-size:raise CurveKeyParamDecodeError(f'CurveKey.Param:truncated,offset={offset},size={size}')
 def string(index,field):
  try:return resolve_string_pool_index(index,strings,field)
  except ValueError as error:raise CurveKeyParamDecodeError(str(error)) from error
 need(1);marker=data[offset];offset+=1
 if marker==255:return None,offset
 if marker!=4:raise CurveKeyParamDecodeError('CurveKey.Param:expected-member4')
 need(1);marker=data[offset];offset+=1
 if marker==255:key=None
 elif marker==1:
  need(4);key=string(struct.unpack_from('<i',data,offset)[0],'CurveKey.key');offset+=4
 else:raise CurveKeyParamDecodeError('CurveKey.child:expected-member1-or-default255')
 need(12);id_ref,source,index=struct.unpack_from('<iii',data,offset)
 return dict(value=dict(key=key),idRef=id_ref,paramSource=source,path=string(index,'CurveKey.path')),offset+12

def decode_curve_key_param(data,offset,*,strings=None,game_root=None):
 _,audit=load_curve_key_param_contract(game_root=game_root)
 if audit.get('status')!='validated' or audit.get('parentProofStatus')!='selected-generated-route':raise CurveKeyParamDecodeError(f"CurveKey.native:{audit.get('status')},check={audit.get('failedCheck')},detail={audit.get('detail','')}")
 return decode_wire(data,offset,strings=strings)

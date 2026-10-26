"""Own two-Int32 Param constant, preserving exact bits and pooled tail."""
import struct
from scripts.game_data.codecs.levelscript.current_condition_param import _validate_shape

VALUE='UnityEngine.Vector2Int'
CAP_SCHEMA='endfield.story-int2-param-capability.v1'


def validate(cap):
 if not isinstance(cap,dict)or cap.get('schema')!=CAP_SCHEMA or cap.get('valueType')!=VALUE:
  raise ValueError('currentInt2Param.exact-owned-nominal')
 _validate_shape(cap,'int2-raw8',8)
 if cap.get('constantRawInt32Axes')!=['x','y']or cap.get('constantValueEvaluationAdmitted')is not False:
  raise ValueError('currentInt2Param.exact-two-Int32-source')


def read(reader,field,cap):
 validate(cap);start=reader.offset;marker=reader.number('<B',field+'.memberCount')
 if marker==255:return None
 if marker!=4:raise ValueError(f'{field}:Int2-Param-member-count,offset={start},expected=4,actual={marker}')
 at=reader.offset;reader.need(8,field+'.constValue');raw=bytes(reader.data[at:at+8]);reader.offset+=8;x,y=struct.unpack('<ii',raw)
 result=dict(startOffset=start,typeName=cap['typeName'],constValue=dict(x=x,y=y,rawHex=raw.hex().upper()),
  idRef=reader.number('<i',field+'.idRef'),paramSource=reader.number('<i',field+'.paramSource'),path=reader.string(field+'.path'))
 result['endOffset']=reader.offset;return result

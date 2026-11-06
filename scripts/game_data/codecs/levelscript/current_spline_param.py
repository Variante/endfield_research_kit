"""Source-owned raw Int32 SplinePtr; no runtime spline lookup."""
from scripts.game_data.codecs.levelscript.current_condition_param import _validate_shape

VALUE='Beyond.Gameplay.Core.SplinePtr'


def validate(cap):
    _validate_shape(cap,'spline-id-int32',4)
    if(cap.get('valueType')!=VALUE or cap.get('constantFields')!=[['id','int',16]]
            or cap.get('rawValueBitsPreserved')is not True or cap.get('runtimeSplineResolutionProved')is not False):
        raise ValueError('currentSplineParam.own-signed-Int32-id')


def read(reader,field,cap):
    validate(cap)
    marker=reader.number('<B',field+'.memberCount')
    if marker==255:return None
    if marker!=4:raise ValueError(field+':Spline-Param-member-count')
    at=reader.offset;identifier=reader.number('<i',field+'.constValue.id')
    return dict(constValue=dict(id=identifier,rawHex=bytes(reader.data[at:reader.offset]).hex().upper()),
        idRef=reader.number('<i',field+'.idRef'),paramSource=reader.number('<i',field+'.paramSource'),
        path=reader.string(field+'.path'))

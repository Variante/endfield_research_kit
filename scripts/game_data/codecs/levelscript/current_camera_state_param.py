"""Own four-field Camera Param with an independently proved FF constant."""
from scripts.game_data.codecs.levelscript.current_condition_param import _validate_shape

VALUE='Beyond.Gameplay.View.CameraControlState'


def validate(cap):
    if not isinstance(cap,dict)or cap.get('valueType')!=VALUE:
        raise ValueError('currentCameraStateParam.own-nominal')
    _validate_shape(cap,'reference-null-only',1)
    if cap.get('constantMarker')!=255 or cap.get('positiveConstantAdmitted')is not False:
        raise ValueError('currentCameraStateParam.own-native-FF-child-required')
    return cap


def read(reader,field,cap):
    validate(cap)
    marker=reader.number('<B',field+'.memberCount')
    if marker==255:return None
    if marker!=4:raise ValueError(field+':Camera-Param-member-count')
    if reader.number('<B',field+'.constValue.memberCount')!=255:
        raise ValueError(field+':positive-Camera-constant-unproved')
    return dict(constValue=None,idRef=reader.number('<i',field+'.idRef'),
        paramSource=reader.number('<i',field+'.paramSource'),path=reader.string(field+'.path'))

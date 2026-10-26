"""Current pooled signed-Int32 camera move state; callers prove native components."""
from scripts.game_data.codecs.levelscript.action_map import ActionMapCodecError
from scripts.game_data.codecs.levelscript.int_param import decode_int_param


def decode_move_state_param(data,offset,enum_values,*,strings=None):
    try:decoded=decode_int_param(data,offset,strings=strings)
    except ValueError as error:raise ActionMapCodecError(f'trackCamera.moveWay:{error}') from error
    if decoded is None:raise ActionMapCodecError(f'trackCamera.moveWay:invalid-param,offset={offset}')
    value,end=decoded
    if value is None:return None,end
    if value['value'] not in enum_values:raise ActionMapCodecError(f"trackCamera.moveWay:unknown-enum={value['value']},offset={offset}")
    return value|{'enumName':enum_values[value['value']]},end

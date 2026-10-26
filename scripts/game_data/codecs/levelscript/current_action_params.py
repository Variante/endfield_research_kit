"""Pooled ActionMap Param adapters behind independent selected native sources."""
from scripts.game_data.memorypack.operation_native_validation import validate_native
from scripts.game_data.memorypack.levelscript_action_param_sources import BUFF_SCHEMA, BUFF_LIST, MODEL_VISIBLE
from scripts.game_data.codecs.levelscript.current_condition_param import _validate_shape
from scripts.game_data.codecs.levelscript.param_graph import Reader, ParamGraphDecodeError


def validate_null_buff_capability(cap):
    if (not isinstance(cap, dict) or cap.get('schema') != BUFF_SCHEMA
            or cap.get('valueType') != BUFF_LIST or cap.get('collectionCounts') != [-1]
            or any(type(n) is not int for n in cap['collectionCounts'])
            or cap.get('positiveElementsAdmitted') is not False):
        raise ValueError('currentActionParams.own-null-Buff-list-source')
    _validate_shape(cap, 'null-buff-list', 4)


def decode(data, offset, *, codec_kind, strings, game_root):
    from scripts.game_data.levelscript_action_params_native import validate
    audit = validate_native(validate, codec_kind=codec_kind, game_root=game_root)
    if audit.get('status') != 'validated' or audit.get('codecKind') != codec_kind:
        raise ParamGraphDecodeError('currentActionParams.native:' + str(audit)[:1400])
    cap = audit.get('capability')
    if codec_kind == 'Param<List<GameplayTag>>':
        from scripts.game_data.codecs.levelscript.current_gameplay_tag_list_param import decode as decode_tags
        return decode_tags(data, offset, field=codec_kind, strings=strings, capability=cap)
    if codec_kind == 'Param<Vector3>[]':
        from scripts.game_data.codecs.levelscript.current_vector_param_array import decode as decode_vectors
        return decode_vectors(data, offset, field=codec_kind, strings=strings, capability=cap)
    if codec_kind == 'Param<ObjectPtr<GlobalBuff>>':
        from scripts.game_data.codecs.levelscript.current_global_buff_param import decode as decode_global
        return decode_global(data, offset, field=codec_kind, strings=strings, capability=cap)
    if codec_kind == 'Param<EntityPtr>[]':
        from scripts.game_data.codecs.levelscript.current_entity_param_array import decode as decode_array
        return decode_array(data, offset, field=codec_kind, strings=strings, capability=cap)
    if codec_kind == 'Param<CommonMaskBlendData>':
        from scripts.game_data.codecs.levelscript.current_mask_curve_param import decode as decode_mask
        return decode_mask(data, offset, field=codec_kind, strings=strings, capability=cap)
    reader = Reader(data, offset, strings, codec_kind)
    if codec_kind == 'Param<ModelVisibleType>':
        from scripts.game_data.codecs.levelscript.current_condition_enum_param import read, validate as check
        check(cap)
        if cap.get('valueType') != MODEL_VISIBLE:
            raise ParamGraphDecodeError('currentActionParams.wrong-ModelVisible-nominal')
        row = read(reader, codec_kind, cap)
        if row is None:
            return None, reader.offset
        value = row.pop('constValue')
        row['value'] = value
        return row, reader.offset
    if codec_kind != 'Param<List<BuffPtr>>':
        raise ParamGraphDecodeError('currentActionParams.finite-codec-domain')
    validate_null_buff_capability(cap)
    start = reader.offset
    marker = reader.number('<B', codec_kind + '.memberCount')
    if marker == 255:
        return None, reader.offset
    if marker != 4:
        raise ParamGraphDecodeError(f'{codec_kind}:Param-member-count,offset={start},expected=4,actual={marker}')
    count = reader.number('<i', codec_kind + '.value.count')
    if count != -1:
        raise ParamGraphDecodeError(f'{codec_kind}:only-null-list-source-proved,offset={start+1},actual={count}')
    result = dict(value=None, idRef=reader.number('<i', codec_kind + '.idRef'),
        paramSource=reader.number('<i', codec_kind + '.paramSource'), path=reader.string(codec_kind + '.path'))
    return result, reader.offset

"""CommonMask Param with its independently owned positive Unity curve child."""
import math
import struct

from scripts.game_data.codecs.levelscript.param_graph import Reader

SCHEMA = 'endfield.levelscript-mask-curve-capability.v1'
TYPE = 'Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.CommonMaskBlendData>'


def validate(cap):
    from scripts.game_data.memorypack.skill_animation_curve_codec import require_capability
    if (not isinstance(cap, dict) or cap.get('schema') != SCHEMA or cap.get('typeName') != TYPE
            or type(cap.get('memberCount')) is not int or cap['memberCount'] != 4
            or type(cap.get('maskMemberCount')) is not int or cap['maskMemberCount'] != 6
            or type(cap.get('audioRawBytes')) is not int or cap['audioRawBytes'] != 16
            or cap.get('fieldOrder') != ['constValue', 'idRef', 'paramSource', 'path']
            or cap.get('maskFieldOrder') != ['audioBlackScreenBehaviour', 'curve', 'fadeInDuration', 'fadeOutDuration', 'maskType', 'useCurve']
            or cap.get('pathEncoding') != 'int32-pool-index'
            or any(cap.get(k) is not True for k in ('positiveMaskAndCurveAdmitted', 'rawBooleanBytePreserved',
                'rawFloatBitsPreserved', 'actualCurveCallbackEqualsProvedChildRequired'))
            or any(cap.get(k) is not False for k in ('curveNullOnly', 'liveFormatterSelectionObserved',
                'runtimeMaskExecutionProved', 'wholeOwnerAdmitted'))):
        raise ValueError('currentMaskCurve.owned-positive-mask-and-curve')
    require_capability(cap.get('curveCapability', {}))
    fields = cap.get('audioFields')
    if (not isinstance(fields, list) or not fields or any(not isinstance(f, dict)
            or type(f.get('name')) is not str or type(f.get('offset')) is not int
            or f.get('format') not in ('f', 'B') or type(f.get('typeName')) is not str
            or not 0 <= f['offset'] <= 16 - struct.calcsize('<' + f['format']) for f in fields)
            or len({f['name'] for f in fields}) != len(fields)):
        raise ValueError('currentMaskCurve.owned-audio-fields')


def _float(reader, field):
    at = reader.offset
    bits = reader.number('<I', field)
    value = struct.unpack('<f', struct.pack('<I', bits))[0]
    return dict(value=value if math.isfinite(value) else None, finite=math.isfinite(value),
                rawHex=bytes(reader.data[at:reader.offset]).hex().upper())


def _curve(reader, field, cap):
    marker = reader.number('<B', field + '.memberCount')
    if marker == 255:
        return None
    if marker != 3:
        raise ValueError(field + ':curve-member-count')
    before = reader.number('<i', field + '.preWrapMode')
    after = reader.number('<i', field + '.postWrapMode')
    at = reader.offset
    reader.need(4, field + '.count')
    count = struct.unpack_from('<i', reader.data, at)[0]
    if not -1 <= count <= cap['countLimit']:
        raise ValueError(field + ':curve-count-limit')
    reader.offset += 4
    reader.need(max(count, 0) * 28, field + '.keys')
    keys = []
    for index in range(max(count, 0)):
        start = reader.offset
        reader.offset += 28
        keys.append(dict(rawHex=bytes(reader.data[start:reader.offset]).hex().upper()))
    return dict(preWrapMode=before, postWrapMode=after, count=count, keys=None if count == -1 else keys)


def read(reader, field, cap):
    validate(cap)
    marker = reader.number('<B', field + '.memberCount')
    if marker == 255:
        return None
    if marker != 4:
        raise ValueError(field + ':mask-Param-member-count')
    marker = reader.number('<B', field + '.constValue.memberCount')
    value = None
    if marker != 255:
        if marker != 6:
            raise ValueError(field + ':mask-member-count')
        at = reader.offset
        reader.need(16, field + '.audio')
        raw = bytes(reader.data[at:at + 16])
        reader.offset += 16
        audio = dict(rawHex=raw.hex().upper())
        for spec in cap['audioFields']:
            number = struct.unpack_from('<' + spec['format'], raw, spec['offset'])[0]
            audio[spec['name']] = (number if not isinstance(number, float) or math.isfinite(number) else None)
        curve = _curve(reader, field + '.curve', cap['curveCapability'])
        fade_in = _float(reader, field + '.fadeInDuration')
        fade_out = _float(reader, field + '.fadeOutDuration')
        kind = reader.number('<i', field + '.maskType')
        use = reader.number('<B', field + '.useCurve')
        value = dict(audioBlackScreenBehaviour=audio, curve=curve, fadeInDuration=fade_in,
                     fadeOutDuration=fade_out, maskType=kind, useCurve=bool(use), useCurveRawByte=use)
    return dict(value=value, idRef=reader.number('<i', field + '.idRef'),
                paramSource=reader.number('<i', field + '.paramSource'), path=reader.string(field + '.path'))


def decode(data, offset, *, field, strings, capability):
    reader = Reader(data, offset, strings, field)
    value = read(reader, field, capability)
    return value, reader.offset

"""AlphaBlend MC3 value framing with a separately owned Beyond curve child."""
from scripts.game_data.memorypack.alpha_blend_value_sources import TYPE, WRAPPER
from scripts.game_data.memorypack.beyond_curve_value_codec import CAPABILITY as CURVE_CAPABILITY, read_curve

CAPABILITY = 'skill-alpha-blend'
ORDER = [dict(fieldName='_blendOption', kind='enum32-bits', childCapability=None),
         dict(fieldName='_blendTime', kind='single-bits', childCapability=None),
         dict(fieldName='_customCurve', kind=CURVE_CAPABILITY, childCapability=CURVE_CAPABILITY)]


def need(key, condition):
    if not condition:
        raise ValueError('alphaBlendValueCodec.' + key)


def require_capability(cap):
    need('own-value56-and-wire-shape', isinstance(cap, dict) and cap.get('typeName') == TYPE
         and cap.get('wrapperName') == WRAPPER
         and all(type(cap.get(k)) is int and cap[k] == v for k, v in
                 (('memberCount', 3), ('managedBytes', 56), ('nullMarker', 255), ('nullWireBytes', 1)))
         and cap.get('referenceLaneOffsets') == [8] and cap.get('paddingByteRanges') == [[52, 56]]
         and all(type(n) is int for n in cap['referenceLaneOffsets'])
         and all(type(n) is int for row in cap['paddingByteRanges'] for n in row)
         and cap.get('orderedReads') == ORDER and cap.get('wireBytes') is None
         and cap.get('positiveWireBytes') is None)
    need('own-source-default-copy-and-child', all(cap.get(k) is True for k in
         ('nullable', 'nullReturnsDefaultValue', 'wholeGrammarAdmitted', 'actualValueReadValueAdmitted',
          'ownConcreteGetterSemanticsProved', 'ownConcreteFactorySemanticsProved',
          'unserializedStatePreservedOnWrapperReuse', 'callbackSelectionConditional'))
         and cap.get('ordinaryOriginalReadValueAdmitted') is False
         and all(type(cap.get(k)) is int and cap[k] > 0 for k in
                 ('valueReaderMethodDefinition', 'valueSourceTargetRva', 'valueDispatcherTargetRva')))
    return cap


def read_alpha(reader, capability=CAPABILITY, *, depth=0):
    need('bounded-depth', type(depth) is int and 0 <= depth <= 64)
    require_capability(reader.operation.child(capability))
    start = reader.pos
    fields = []
    null = reader.peek() == 255
    if null:
        reader.take(1, CAPABILITY + '.default')
    else:
        reader.header(3)
        for field in ORDER:
            at = reader.pos
            if field['childCapability'] is None:
                reader.take(4, CAPABILITY + '.' + field['fieldName'])
            else:
                need('bounded-child-depth', depth < 64)
                read_curve(reader, CURVE_CAPABILITY)
            fields.append(dict(fieldName=field['fieldName'], start=at, end=reader.pos))
    row = dict(kind=CAPABILITY, start=start, end=reader.pos, isNull=null, fields=fields)
    if null:
        row['returnsDefaultValue'] = True
    reader.records.append(row)
    return row

"""Beyond curve value framing under its own current MC3/raw-key source.

The managed16 payload has an array reference and two enum words. Its serialized
keys are headerless FKeyframe32 records; neither Unity curve framing nor the
managed payload width supplies this grammar.
"""
import struct

TYPE = 'Beyond.FAnimationCurve'
WRAPPER = 'Beyond.MemoryPack.Beyond_FAnimationCurveForMemoryPack'
CAPABILITY = 'beyond-curve-value'
KEY_FIELDS = [('time', 'float'), ('value', 'float'), ('inTangent', 'float'),
              ('outTangent', 'float'), ('tangentMode', 'int'), ('weightedMode', 'int'),
              ('inWeight', 'float'), ('outWeight', 'float')]
ORDER = [dict(fieldName='keys', kind='raw-key-array32'),
         dict(fieldName='postWrapMode', kind='enum32-bits'),
         dict(fieldName='preWrapMode', kind='enum32-bits')]


def need(key, condition):
    if not condition:
        raise ValueError('beyondCurveValueCodec.' + key)


def require_capability(cap):
    need('own-value-and-raw-key-shape', isinstance(cap, dict)
         and cap.get('typeName') == TYPE and cap.get('wrapperName') == WRAPPER
         and all(type(cap.get(k)) is int and cap[k] == v for k, v in
                 (('memberCount', 3), ('managedBytes', 16), ('nullMarker', 255),
                  ('nullWireBytes', 1), ('keyframeBytes', 32)))
         and cap.get('referenceLaneOffsets') == [0] and cap.get('paddingByteRanges') == []
         and all(type(n) is int for n in cap['referenceLaneOffsets'])
         and cap.get('keyframeTypeName') == 'Beyond.FKeyframe'
         and cap.get('keyframeFields') == [dict(fieldName=n, declaredType=t, wireOffset=i*4, bytes=4)
                                          for i, (n, t) in enumerate(KEY_FIELDS)]
         and cap.get('orderedReads') == ORDER)
    need('finite-complete-actual-source', type(cap.get('countLimit')) is int
         and 1 <= cap['countLimit'] <= 10000
         and cap.get('collectionCounts') == [-1, 0]
         and all(type(n) is int for n in cap['collectionCounts'])
         and all(cap.get(k) is True for k in ('nullable', 'nullReturnsDefaultValue',
             'wholeGrammarAdmitted', 'actualValueReadValueAdmitted', 'ownConcreteGetterSemanticsProved',
             'ownConcreteFactorySemanticsProved', 'positiveCountsAdmitted', 'rawKeyCopyDomainProved',
             'callbackSelectionConditional'))
         and cap.get('ordinaryOriginalReadValueAdmitted') is False
         and cap.get('wireBytes') is None and cap.get('positiveWireBytes') is None
         and cap.get('elementHeaders') is False
         and all(type(f.get('wireOffset')) is int and type(f.get('bytes')) is int
                 for f in cap['keyframeFields'])
         and all(type(cap.get(k)) is int and cap[k] > 0 for k in
                 ('valueReaderMethodDefinition', 'valueSourceTargetRva', 'valueDispatcherTargetRva')))
    return cap


def read_curve(reader, capability=CAPABILITY):
    cap = require_capability(reader.operation.child(capability))
    start = reader.pos
    if reader.peek() == 255:
        reader.take(1, CAPABILITY + '.default')
        row = dict(kind=CAPABILITY, start=start, end=reader.pos, isNull=True, returnsDefaultValue=True)
    else:
        reader.header(3)
        need('complete-signed-key-count', reader.pos + 4 <= reader.limit)
        count = struct.unpack_from('<i', reader.data, reader.pos)[0]
        need('proved-key-count', -1 <= count <= cap['countLimit'])
        reader.take(4, CAPABILITY + '.keyCount')
        payload_start = reader.pos
        reader.take(max(0, count)*32, CAPABILITY + '.raw-key-bits')
        reader.take(4, CAPABILITY + '.postWrapMode')
        reader.take(4, CAPABILITY + '.preWrapMode')
        row = dict(kind=CAPABILITY, start=start, end=reader.pos, isNull=False, keyCount=count,
                   keyPayloadStart=payload_start, keyPayloadEnd=payload_start + max(0, count)*32,
                   rawKeyBitsPreserved=True)
    reader.records.append(row)
    return row

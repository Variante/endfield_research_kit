"""Operation-scoped Unity curve storage under the complete custom formatter.

The formatter writes Original directly. Headerless Keyframe words belong to
its own bounded array induction; wrapper getters, Beyond curves and runtime
interpolation provide no substitute for this selected capability.
"""
import struct

LABEL = 'skillAnimationCurveCodec'
TYPE = 'UnityEngine.AnimationCurve'
KEY_FIELDS = (
    ('m_Time', 'float'), ('m_Value', 'float'), ('m_InTangent', 'float'),
    ('m_OutTangent', 'float'), ('m_WeightedMode', 'int'),
    ('m_InWeight', 'float'), ('m_OutWeight', 'float'),
)


def require_capability(cap):
    """Check the decoder's shape; native authentication belongs to the owner."""
    if (cap.get('typeName') != TYPE
            or cap.get('formatterTypeName') != 'MemoryPack.AnimationCurveFormatter'
            or type(cap.get('memberCount')) is not int or cap['memberCount'] != 3
            or type(cap.get('nullMarker')) is not int or cap['nullMarker'] != 255
            or not all(cap.get(key) is True for key in (
                'nullAdmitted', 'nullable', 'wholeGrammarAdmitted',
                'ordinaryOriginalReadValueAdmitted', 'ownConcreteFactorySemanticsProved',
                'customFormatterWritesOriginalDirectly', 'positiveCountsAdmitted',
                'keyLoopInductionProved'))
            or cap.get('keyframeTypeName') != 'UnityEngine.Keyframe'
            or type(cap.get('keyframeBytes')) is not int or cap['keyframeBytes'] != 28
            or cap.get('collectionCounts') != [-1, 0]
            or any(type(n) is not int for n in cap['collectionCounts'])
            or type(cap.get('countLimit')) is not int or not 1 <= cap['countLimit'] <= 10000
            or type(cap.get('referenceReaderMethodDefinition')) is not int
            or cap['referenceReaderMethodDefinition'] < 0
            or type(cap.get('referenceReaderTargetRva')) is not int
            or cap['referenceReaderTargetRva'] <= 0):
        raise ValueError(LABEL + '.complete-custom-formatter-capability')
    fields = cap.get('keyframeFields')
    if (not isinstance(fields, list) or len(fields) != len(KEY_FIELDS)
            or any(not isinstance(field, dict) for field in fields)
            or [(field.get('fieldName'), field.get('declaredType')) for field in fields] != list(KEY_FIELDS)
            or any(type(field.get('wireOffset')) is not int or field['wireOffset'] != index * 4
                   or type(field.get('bytes')) is not int or field['bytes'] != 4
                   for index, field in enumerate(fields))):
        raise ValueError(LABEL + '.source-owned-keyframe-layout')
    return cap


def read_curve(reader, capability='curve-profile'):
    cap = require_capability(reader.operation.child(capability))
    start = reader.pos
    if reader.peek() == 255:
        reader.take(1, 'null-unity-curve')
        reader.records.append(dict(kind='unity-animation-curve', start=start, end=reader.pos, isNull=True))
        return
    reader.header(3)
    for field in ('preWrapMode', 'postWrapMode'):
        reader.take(4, TYPE + '.' + field)
    if reader.pos + 4 > reader.limit:
        raise ValueError(LABEL + '.truncated-key-count')
    count = struct.unpack_from('<i', reader.data, reader.pos)[0]
    if not -1 <= count <= cap['countLimit']:
        raise ValueError(LABEL + '.unproved-key-count=' + str(count))
    actual = reader.count(28, nullable=True)
    for _ in range(max(0, actual)):
        for field in cap['keyframeFields']:
            reader.take(4, 'UnityEngine.Keyframe.' + field['fieldName'])
    reader.records.append(dict(kind='unity-animation-curve', start=start, end=reader.pos, keyCount=count))

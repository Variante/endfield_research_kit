"""Own pooled GlobalBuff Param and ObjectPtr16 MC2/default value framing."""
from scripts.game_data.codecs.levelscript.param_graph import Reader

SCHEMA = 'endfield.levelscript-global-buff-param-capability.v1'
VALUE = 'Beyond.ObjectPtr`1<Beyond.Gameplay.Core.GlobalBuff>'
TYPE = 'Beyond.Gameplay.Actions.Param`1<' + VALUE + '>'
BUFF = 'Beyond.Gameplay.Core.GlobalBuff'


def validate(cap):
    expected = dict(schema=SCHEMA, typeName=TYPE, valueType=VALUE, memberCount=4,
                    fieldOrder=['constValue', 'idRef', 'paramSource', 'path'], constantMemberCount=2,
                    constantFieldOrder=['cachedUid', 'obj'], globalBuffType=BUFF, globalBuffMemberCount=0,
                    constantManagedBytes=16, unserializedValueStorageRanges=[[12, 16]],
                    uidWireKind='u32', pathEncoding='int32-pool-index', idRefWireKind='i32', paramSourceWireKind='i32',
                    outerNullReference=True, constantNullDefaultsZero16=True, positiveGlobalBuffAdmitted=True,
                    globalBuffNullReference=True, exactOwnNominalsProved=True,
                    actualParamAndValueAndGlobalCallbacksRequired=True, runtimeGlobalBuffResolutionProved=False,
                    liveFormatterSelectionObserved=False, parentFieldAdmitted=False, wholeOwnerAdmitted=False)
    if not isinstance(cap, dict) or any(type(cap.get(k)) is not type(v) or cap.get(k) != v for k, v in expected.items()):
        raise ValueError('currentGlobalBuffParam.exact-own-Param-ObjectPtr-GlobalBuff')
    for key in ('readerMethodDefinition', 'sourceTargetRva', 'canonicalParamCallbackTargetRva',
                'valueReaderMethodDefinition', 'valueReaderTargetRva', 'valueCallbackTargetRva',
                'canonicalGlobalCallbackTargetRva'):
        if type(cap.get(key)) is not int or cap[key] <= 0:
            raise ValueError('currentGlobalBuffParam.own-typed-reader-callbacks')


def read(reader, field, cap):
    validate(cap)
    marker = reader.number('<B', field+'.memberCount')
    if marker == 255:
        return None
    if marker != 4:
        raise ValueError(field+':global-buff-Param-member-count')
    marker = reader.number('<B', field+'.value.memberCount')
    if marker == 255:
        value = dict(cachedUid=0, obj=None, defaultValue=True)
    elif marker == 2:
        uid = reader.number('<I', field+'.value.cachedUid')
        marker = reader.number('<B', field+'.value.obj.memberCount')
        if marker not in (0, 255):
            raise ValueError(field+':GlobalBuff-member-count')
        value = dict(cachedUid=uid, obj=None if marker == 255 else {}, defaultValue=False)
    else:
        raise ValueError(field+':ObjectPtr-GlobalBuff-member-count')
    return dict(value=value, idRef=reader.number('<i', field+'.idRef'),
                paramSource=reader.number('<i', field+'.paramSource'), path=reader.string(field+'.path'))


def decode(data, offset, *, field, strings, capability):
    reader = Reader(data, offset, strings, field)
    value = read(reader, field, capability)
    return value, reader.offset

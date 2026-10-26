"""Signed-count arrays of the exact independently proved Vector3 Param."""
import struct

from scripts.game_data.codecs.levelscript.param_graph import Reader
from scripts.game_data.codecs.levelscript import current_condition_param as param

SCHEMA = 'endfield.levelscript-vector3-param-array-capability.v1'
VALUE = 'UnityEngine.Vector3'
ELEMENT = 'Beyond.Gameplay.Actions.Param`1<' + VALUE + '>'


def validate(cap):
    expected = dict(schema=SCHEMA, elementType=ELEMENT, closedArrayType=ELEMENT+'[]', countLimit=4096,
        countWireBytes=4, nullCount=-1, freshArrayRequired=True, elementReferenceKind=21,
        referenceSlotBytes=8, elementWireBytes=None, elementGrammarAdmitted=True,
        positiveCountsAdmitted=True, actualElementCallbackEqualsProvedParamRequired=True,
        actualProviderEqualsProvedProviderRequired=True, liveFormatterSelectionObserved=False,
        runtimeValueEvaluationProved=False, parentFieldAdmitted=False, wholeOwnerAdmitted=False)
    if not isinstance(cap, dict) or any(type(cap.get(k)) is not type(v) or cap.get(k) != v for k,v in expected.items()):
        raise ValueError('currentVectorParamArray.exact-reference-Param-array')
    for key in ('readerMethodDefinition','sourceTargetRva','canonicalCallbackTargetRva'):
        if type(cap.get(key)) is not int or cap[key] <= 0:
            raise ValueError('currentVectorParamArray.own-typed-source-and-callback')
    child = cap.get('elementCapability')
    param.validate(child)
    if child['typeName'] != ELEMENT or child['canonicalCallbackTargetRva'] != cap['canonicalCallbackTargetRva']:
        raise ValueError('currentVectorParamArray.same-own-Param-child')
    return cap


def read(reader, field, cap, *, budget=None):
    validate(cap)
    at = reader.offset
    reader.need(4, field+'.count')
    count = struct.unpack_from('<i', reader.data, at)[0]
    if not -1 <= count <= cap['countLimit']:
        raise ValueError(f'{field}:array-count,offset={at},expected=-1..4096,actual={count}')
    if budget is not None:
        if not isinstance(budget,list) or len(budget)!=1 or type(budget[0]) is not int or budget[0]<max(count,0):
            raise ValueError(field+':array-shared-budget')
        budget[0] -= max(count,0)
    reader.offset += 4
    if count == -1:
        return None
    return [param.read(reader, field+'['+str(index)+']', cap['elementCapability']) for index in range(count)]


def decode(data, offset, *, field, strings, capability, budget=None):
    reader = Reader(data, offset, strings, field)
    value = read(reader, field, capability, budget=budget)
    return value, reader.offset

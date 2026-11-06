"""Signed-count arrays of the independently proved Boolean Param."""
import struct
from scripts.game_data.codecs.levelscript.param_graph import Reader
from scripts.game_data.codecs.levelscript import current_condition_param as param

SCHEMA='endfield.levelscript-boolean-param-array-capability.v1'
ELEMENT='Beyond.Gameplay.Actions.Param`1<bool>'


def validate(cap):
    expected=dict(schema=SCHEMA,elementType=ELEMENT,closedArrayType=ELEMENT+'[]',countLimit=4096,
        countWireBytes=4,nullCount=-1,freshArrayRequired=True,elementReferenceKind=21,referenceSlotBytes=8,
        elementWireBytes=None,elementGrammarAdmitted=True,positiveCountsAdmitted=True,
        actualElementCallbackEqualsProvedParamRequired=True,actualProviderEqualsProvedProviderRequired=True,
        liveFormatterSelectionObserved=False,runtimeValueEvaluationProved=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)
    if not isinstance(cap,dict)or any(type(cap.get(k))is not type(v)or cap.get(k)!=v for k,v in expected.items()):
        raise ValueError('currentBooleanParamArray.exact-own-reference-array')
    for k in('readerMethodDefinition','sourceTargetRva','canonicalCallbackTargetRva'):
        if type(cap.get(k))is not int or cap[k]<=0:raise ValueError('currentBooleanParamArray.owned-source-and-callback')
    child=cap.get('elementCapability');param.validate(child)
    if(child['typeName']!=ELEMENT or child.get('valueType')!='bool'or child.get('constantWireKind')!='bool-byte'
            or child.get('constantWireBytes')!=1 or child['canonicalCallbackTargetRva']!=cap['canonicalCallbackTargetRva']):
        raise ValueError('currentBooleanParamArray.independent-Boolean-element')
    return cap


def read(reader,field,cap,*,budget=None):
    validate(cap);at=reader.offset;reader.need(4,field+'.count');count=struct.unpack_from('<i',reader.data,at)[0]
    if not -1<=count<=cap['countLimit']:raise ValueError(f'{field}:array-count,offset={at},expected=-1..4096,actual={count}')
    if budget is not None:
        if not isinstance(budget,list)or len(budget)!=1 or type(budget[0])is not int or budget[0]<max(count,0):
            raise ValueError(field+':array-shared-budget')
        budget[0]-=max(count,0)
    reader.offset+=4
    return None if count==-1 else[param.read(reader,field+'['+str(i)+']',cap['elementCapability'])for i in range(count)]


def decode(data,offset,*,field,strings,capability,budget=None):
    reader=Reader(data,offset,strings,field);value=read(reader,field,capability,budget=budget)
    return value,reader.offset

"""Bounded value arrays on the shared native-owned animation cursor."""
import struct
from scripts.game_data.memorypack.animation_extra_array_components import TYPES,key


def need(check,condition):
    if not condition:raise ValueError('animationExtraArrayCodec.'+check)


def read(reader,capability,*,depth=0,budget=None):
    need('bounded-array-depth',type(depth)is int and 0<=depth<64)
    cap=reader.operation.child(capability);name=cap.get('elementType')
    need('finite-complete-own-value-array',name in TYPES and capability==key(name)
        and cap.get('typeName')==cap.get('closedArrayType')==name+'[]'and cap.get('elementValueType')is True
        and cap.get('elementCapability')=='animation-extra-record:'+name and cap.get('headerBytes')==4
        and cap.get('countRange')==[-1,4096]and cap.get('countLimit')==4096 and cap.get('elementWireBytes')is None
        and all(cap.get(k)is True for k in('wholeGrammarAdmitted','elementGrammarAdmitted','nullable','positiveCountsAdmitted',
            'initiallyNullArrayRequired','actualCallbackEqualsCanonicalRequired'))
        and cap.get('liveFormatterSelectionObserved')is False)
    element=reader.operation.child(cap['elementCapability'])
    need('same-independent-actual-element-capability',element==cap.get('elementCapabilityShape')and element.get('typeName')==name
        and element.get('managedBytes')==cap.get('managedElementBytes')and element.get('wholeGrammarAdmitted')is True
        and element.get('ordinaryOriginalCallbackAdmitted')is True and element.get('ordinaryOriginalReadValueAdmitted')is False
        and element.get('canonicalAdapterTargetRva')==cap.get('canonicalAdapterTargetRva')
        and element.get('formatterDeserializeMethodDefinition')==cap.get('formatterDeserializeMethodDefinition'))
    if budget is None:budget=dict(remaining=16384)
    need('literal-shared-node-budget',isinstance(budget,dict)and set(budget)=={'remaining'}and type(budget['remaining'])is int
        and 0<budget['remaining']<=16384)
    start=reader.pos;need('complete-count-before-consumption',start+4<=reader.limit)
    count=struct.unpack_from('<i',reader.data,start)[0]
    need('bounded-signed-count-before-consumption',-1<=count<=4096)
    need('minimum-child-bytes-and-budget-before-consumption',start+4+max(count,0)<=reader.limit and 1+max(count,0)<=budget['remaining'])
    budget['remaining']-=1;reader.take(4,capability+'.count');elements=[]
    for _ in range(max(count,0)):elements.append(reader.extra_record(cap['elementCapability'],depth=depth+1,budget=budget))
    result=dict(kind=capability,typeName=name+'[]',start=start,end=reader.pos,isNull=count==-1,count=count,
        elements=elements,managedStrideSerialized=False,containingRouteClaimed=False,runtimeAnimationProved=False)
    reader.records.append(result);return result

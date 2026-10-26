"""MC4/default24 ShaderPropertyEntry cursor; managed padding is not wire."""
from scripts.game_data.memorypack.shader_property_value_components import CAPABILITY
from scripts.game_data.memorypack.shader_property_value_sources import TYPE,WRAPPER,ORDER


def need(check,condition):
    if not condition:raise ValueError('shaderPropertyCodec.'+check)


def require_capability(cap):
    need('own-complete-MC4-default24',cap.get('typeName')==TYPE and cap.get('wrapperName')==WRAPPER
        and cap.get('memberCount')==4 and cap.get('orderedFieldNames')==ORDER and cap.get('managedBytes')==24
        and cap.get('valueStorageKind')=='value24'and cap.get('referenceLaneOffsets')==[8]
        and cap.get('paddingByteRanges')==[[20,4]]and cap.get('positiveWireBytes')==17
        and cap.get('nullable')is True and cap.get('nullMarker')==255 and cap.get('nullWireBytes')==1
        and cap.get('nullReturnsDefaultValue')is True and cap.get('wholeGrammarAdmitted')is True
        and cap.get('ordinaryOriginalCallbackAdmitted')is True and cap.get('ordinaryOriginalReadValueAdmitted')is False
        and type(cap.get('originalTypeDefinition'))is int and cap['originalTypeDefinition']>=0
        and all(type(cap.get(k))is int and cap[k]>0 for k in('canonicalAdapterTargetRva','formatterDeserializeMethodDefinition'))
        and isinstance(cap.get('requiredChildCapabilities'),dict)and set(cap['requiredChildCapabilities'])=={'byte-payload'}
        and cap['requiredChildCapabilities']['byte-payload'].get('wholeGrammarAdmitted')is True)
    return cap


def read(reader,*,depth=0,budget=None):
    need('bounded-value-depth',type(depth)is int and 0<=depth<64)
    cap=require_capability(reader.operation.child(CAPABILITY))
    need('own-current-pooled-name-source',reader.operation.child('byte-payload')==cap['requiredChildCapabilities']['byte-payload'])
    if budget is None:budget=dict(remaining=16384)
    need('shared-node-budget-before-consumption',isinstance(budget,dict)and set(budget)=={'remaining'}
        and type(budget['remaining'])is int and 1<=budget['remaining']<=16384)
    start=reader.pos;marker=reader.peek();need('exact-MC4-or-default24',marker in(4,255))
    need('complete-selected-record-before-consumption',start+(1 if marker==255 else 17)<=reader.limit)
    budget['remaining']-=1;reader.take(1,CAPABILITY+'.header');fields=[]
    if marker==255:
        fields=[dict(fieldName=n,value=None)if n=='name'else dict(fieldName=n,rawHex='00000000')for n in ORDER]
    else:
        for name in ORDER:
            value=dict(value=reader.byte_payload())if name=='name'else dict(rawHex=reader.take(4,name).hex())
            fields.append(dict(fieldName=name,**value))
    result=dict(kind=CAPABILITY,typeName=TYPE,start=start,end=reader.pos,isNull=False,defaultValue=marker==255,
        fields=fields,paddingSerialized=False,runtimeAnimationProved=False,containingRouteClaimed=False)
    reader.records.append(result);return result

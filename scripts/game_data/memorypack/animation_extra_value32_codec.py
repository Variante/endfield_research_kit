"""Own MC3/MC6 managed32 value cursors; payload padding is not wire."""
from scripts.game_data.memorypack.animation_extra_value32_components import STATE,PLAY,PLANS,key


def need(check,condition):
    if not condition:raise ValueError('animationExtraValue32Codec.'+check)


def require_capability(cap):
    name=cap.get('typeName');need('finite-own-value32',name in PLANS)
    need('complete-own-wire-and-canonical-callback',cap.get('wholeGrammarAdmitted')is True and cap.get('wireGrammarAdmitted')is True
        and cap.get('canonicalCallbackAbiProved')is True and cap.get('managedBytes')==32 and cap.get('valueStorageKind')=='value32'
        and cap.get('memberCount')==len(PLANS[name])and cap.get('wireFields')==[list(v)for v in PLANS[name]]
        and cap.get('orderedFieldNames')==[n for n,t in PLANS[name]]and cap.get('positiveWireBytes')==(13 if name==STATE else 16)
        and cap.get('ordinaryOriginalCallbackAdmitted')is True and cap.get('ordinaryOriginalReadValueAdmitted')is False
        and cap.get('nullable')is True and cap.get('nullMarker')==255 and cap.get('nullWireBytes')==1
        and cap.get('nullReturnsDefaultValue')is True and cap.get('referenceLaneOffsets')==([0,16]if name==STATE else[0,8,16])
        and cap.get('paddingRangeEncoding')=='start,length'and cap.get('paddingByteRanges')==([[12,4],[28,4]]if name==STATE else[[27,5]])
        and isinstance(cap.get('requiredChildCapabilities'),dict)and set(cap['requiredChildCapabilities'])=={'byte-payload'}
        and all(type(cap.get(k))is int and cap[k]>=0 for k in('originalTypeDefinition','canonicalAdapterTargetRva','formatterDeserializeMethodDefinition')))
    return cap


def read(reader,type_name,*,depth=0,budget=None):
    need('bounded-value-depth',type(depth)is int and 0<=depth<64);cap=require_capability(reader.operation.child(key(type_name)))
    need('own-typed-value-and-pool',cap['typeName']==type_name and reader.operation.child('byte-payload')==cap['requiredChildCapabilities']['byte-payload'])
    if budget is None:budget=dict(remaining=16384)
    need('shared-node-budget-before-consumption',isinstance(budget,dict)and set(budget)=={'remaining'}
        and type(budget['remaining'])is int and 0<budget['remaining']<=16384)
    start=reader.pos;marker=reader.peek();need('exact-own-member-count-or-default',marker in(cap['memberCount'],255))
    need('complete-fixed-wire-before-consumption',start+(1 if marker==255 else cap['positiveWireBytes'])<=reader.limit)
    budget['remaining']-=1;reader.take(1,key(type_name)+'.header');fields=[]
    for name,typ in PLANS[type_name]:
        if marker==255:value=dict(value=None)if typ=='string'else dict(rawHex='00'if typ=='bool'else'00000000')
        elif typ=='string':value=dict(value=reader.byte_payload())
        else:
            raw=reader.take(1 if typ=='bool'else 4,name);value=dict(rawHex=raw.hex())
            if typ=='bool':value['normalizedValue']=raw[0]!=0
        fields.append(dict(fieldName=name,**value))
    result=dict(kind=key(type_name),typeName=type_name,start=start,end=reader.pos,isNull=False,defaultValue=marker==255,
        fields=fields,paddingSerialized=False,nonserializedFieldNames=cap.get('nonserializedFieldNames',[]),
        runtimeAnimationProved=False,containingRouteClaimed=False)
    reader.records.append(result);return result

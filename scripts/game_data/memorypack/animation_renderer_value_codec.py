"""MC1/default8 renderer entry with bounded signed-count pooled string array."""
from scripts.game_data.memorypack.animation_renderer_value_sources import TYPE,WRAPPER
CAPABILITY='animation-extra-record:'+TYPE


def need(check,condition):
    if not condition:raise ValueError('animationRendererCodec.'+check)


def require_capability(cap):
    need('own-complete-MC1-default8',cap.get('typeName')==TYPE and cap.get('wrapperName')==WRAPPER
        and cap.get('memberCount')==1 and cap.get('orderedFieldNames')==['rendererNamePrefixes']and cap.get('managedBytes')==8
        and cap.get('valueStorageKind')=='value8'and cap.get('referenceLaneOffsets')==[0]and cap.get('paddingByteRanges')==[]
        and all(cap.get(k)is True for k in('wholeGrammarAdmitted','nullable','nullReturnsDefaultValue',
            'ordinaryOriginalCallbackAdmitted','ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved'))
        and cap.get('ordinaryOriginalReadValueAdmitted')is False and cap.get('nullMarker')==255 and cap.get('nullWireBytes')==1
        and type(cap.get('originalTypeDefinition'))is int and cap['originalTypeDefinition']>=0
        and all(type(cap.get(k))is int and cap[k]>0 for k in('canonicalAdapterTargetRva','formatterDeserializeMethodDefinition'))
        and cap.get('stringArrayCapability',{}).get('capability')=='story-pooled-string-array'
        and cap['stringArrayCapability'].get('countRange')==[-1,4096]
        and cap['stringArrayCapability'].get('wholeGrammarAdmitted')is True
        and set(cap.get('requiredChildCapabilities',{}))=={'byte-payload'}
        and cap['requiredChildCapabilities']['byte-payload'].get('wholeGrammarAdmitted')is True)
    return cap


def read(reader,*,depth=0,budget=None):
    need('bounded-depth',type(depth)is int and 0<=depth<64);cap=require_capability(reader.operation.child(CAPABILITY))
    need('same-pooled-index-grammar',reader.operation.child('byte-payload')==cap['requiredChildCapabilities']['byte-payload'])
    if budget is None:budget=dict(remaining=16384)
    need('shared-node-budget',isinstance(budget,dict)and set(budget)=={'remaining'}and type(budget['remaining'])is int and 1<=budget['remaining']<=16384)
    start=reader.pos;marker=reader.peek();need('exact-MC1-or-default8',marker in(1,255));count=None
    if marker==1:
        need('complete-array-count',start+5<=reader.limit)
        count=int.from_bytes(reader.data[start+1:start+5],'little',signed=True)
        need('bounded-signed-array-count',-1<=count<=4096)
        need('whole-array-before-consumption',start+5+max(count,0)*4<=reader.limit)
        need('remaining-node-budget',budget['remaining']>=1+max(count,0))
    budget['remaining']-=1;reader.take(1,CAPABILITY+'.header');values=None
    if marker==1:
        reader.take(4,CAPABILITY+'.count')
        if count>=0:
            values=[]
            for _ in range(count):budget['remaining']-=1;values.append(reader.byte_payload())
    result=dict(kind=CAPABILITY,typeName=TYPE,start=start,end=reader.pos,isNull=False,defaultValue=marker==255,
        fields=[dict(fieldName='rendererNamePrefixes',value=values)],runtimeAnimationProved=False,containingRouteClaimed=False)
    reader.records.append(result);return result

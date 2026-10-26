"""SkMorph MC5 or FF/default40; runtime fields and padding consume no bytes."""
from scripts.game_data.memorypack import sk_morph_value_sources as source
from scripts.game_data.memorypack.sk_morph_value_components import CAPABILITY


def need(check,condition):
    if not condition:raise ValueError('skMorphValueCodec.'+check)


def require_capability(cap):
    need('own-whole-MC5-default40',cap.get('typeName')==source.TYPE and cap.get('wrapperName')==source.WRAPPER
        and cap.get('managedBytes')==40 and cap.get('memberCount')==5 and cap.get('positiveWireBytes')==26
        and cap.get('nullable')is True and cap.get('nullMarker')==255 and cap.get('nullWireBytes')==1
        and cap.get('nullReturnsDefaultValue')is True and cap.get('wholeGrammarAdmitted')is True
        and cap.get('ordinaryOriginalReadValueAdmitted')is True and cap.get('ordinaryOriginalCallbackAdmitted')is True
        and cap.get('referenceLaneOffsets')==[24]and cap.get('paddingByteRanges')==source.PADDING
        and cap.get('runtimeOnlyFieldNames')==['motionAsset']
        and cap.get('orderedFieldNames')==['motionAssetPathHash','motionTag','motionType','transitionInfo','useAssetDirectly']
        and all(type(cap.get(k))is int and cap[k]>0 for k in('valueReaderMethodDefinition','valueReaderTargetRva',
            'valueDispatcherTargetRva','canonicalAdapterTargetRva','formatterDeserializeMethodDefinition'))
        and cap.get('runtimeAnimationProved')is False and cap.get('wholeOwnerAdmitted')is False)
    return cap


def read(reader,*,depth=0,budget=None):
    from scripts.game_data.memorypack import animation_transition_value_sources as transition
    need('bounded-value-depth',type(depth)is int and 0<=depth<64)
    cap=require_capability(reader.operation.child(CAPABILITY))
    for name,child in cap['requiredChildCapabilities'].items():need('same-independent-child:'+name,reader.operation.child(name)==child)
    transition.require_capability(reader.operation.child(cap['transitionCapability']))
    if budget is None:budget=dict(remaining=16384)
    need('shared-node-budget-before-consumption',isinstance(budget,dict)and set(budget)=={'remaining'}
        and type(budget['remaining'])is int and 1<=budget['remaining']<=16384)
    start=reader.pos;marker=reader.peek();need('exact-member-count-or-FF',marker in(5,255))
    need('complete-selected-value-before-consumption',start+(1 if marker==255 else 26)<=reader.limit)
    budget['remaining']-=1;reader.take(1,CAPABILITY+'.header')
    if marker==255:
        row=dict(kind=CAPABILITY,typeName=source.TYPE,start=start,end=reader.pos,isNull=True,returnsDefaultValue=True)
    else:
        hash_raw=reader.take(8,'motionAssetPathHash');tag=reader.take(4,'motionTag');motion=reader.take(4,'motionType')
        trans=transition.read(reader,depth=depth+1,budget=budget);boolean=reader.take(1,'useAssetDirectly')
        row=dict(kind=CAPABILITY,typeName=source.TYPE,start=start,end=reader.pos,isNull=False,
            motionAssetPathHashBits=hash_raw.hex(),motionTagBits=tag.hex(),motionTypeBits=motion.hex(),transitionInfo=trans,
            useAssetDirectly=boolean[0]!=0,useAssetDirectlyRawHex=boolean.hex(),runtimeFieldsSerialized=False,paddingSerialized=False)
    row['runtimeAnimationProved']=False;reader.records.append(row);return row

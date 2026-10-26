"""Explicit positive mask-list cursor, gated by the independent loop proof."""
import struct

CAPABILITY='animation-config-bone-weight-masks-positive'
TYPE='System.Collections.Generic.List`1<Beyond.Gameplay.View.Animation.AnimationConfigJson+BoneWeightMaskJsonEntry>'


def need(key,condition):
    if not condition:raise ValueError('animationMaskPositiveCodec.'+key)


def require_capability(cap):
    need('whole-independent-positive-mask-list',cap.get('typeName')==TYPE and cap.get('wholeGrammarAdmitted')is True
        and cap.get('positiveCountsAdmitted')is True and cap.get('countLimit')==4096
        and cap.get('collectionCounts')==[-1,0]and cap.get('memberCount')==2
        and cap.get('fieldOrder')==['layerName','maskPath']and cap.get('elementGrammarAdmitted')is True
        and cap.get('managedElementBytes')==16 and cap.get('positiveElementWireBytes')==13
        and cap.get('nullElementWireBytes')==1 and cap.get('nullElementReturnsDefault16')is True
        and cap.get('pooledLayerNameRequired')is True and cap.get('actualCallbackSelectionConditional')is True
        and cap.get('initiallyNullOutputProved')is True and cap.get('newConstructorCapacityEqualsCountProved')is True
        and cap.get('positiveLoopInductionProved')is True and cap.get('growthAdmitted')is False)
    return cap


def read(reader,*,budget):
    cap=require_capability(reader.operation.child(CAPABILITY));pool=reader.operation.child('byte-payload')
    need('own-pooled-string-source',pool.get('wholeGrammarAdmitted')is True and pool.get('encoding')=='int32-pool-index'
        and pool.get('emptyIndex')==-1 and pool.get('nullIndex')==-2)
    start=reader.pos;need('complete-count-before-consumption',start+4<=reader.limit)
    count=struct.unpack_from('<i',reader.data,start)[0]
    need('bounded-count-before-consumption',-1<=count<=cap['countLimit'])
    nodes=1+max(count,0)
    need('shared-budget-before-consumption',isinstance(budget,dict)and type(budget.get('remaining'))is int
        and budget['remaining']>=nodes)
    budget['remaining']-=nodes;reader.take(4,'boneWeightMasks.count');rows=[]
    for index in range(max(count,0)):
        at=reader.pos;marker=reader.peek();need('own-MC2-or-default16',marker in(2,255));reader.take(1,'boneWeightMasks.memberCount')
        value=(dict(isNull=True,defaultManagedHex='00'*16)if marker==255 else
            dict(isNull=False,layerName=reader.byte_payload(),maskPathRawHex=reader.take(8,'boneWeightMasks.maskPath').hex()))
        rows.append(dict(start=at,end=reader.pos,**value))
    return dict(start=start,end=reader.pos,count=count,isNull=count==-1,rows=rows)

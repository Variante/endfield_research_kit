"""The animation Extra Int32-array wire on the shared owned cursor."""
import struct
from scripts.game_data.memorypack.animation_extra_int_array_components import CAPABILITY


def need(check,condition):
    if not condition:raise ValueError('animationExtraIntArrayCodec.'+check)


def read(reader,*,depth=0,budget=None):
    need('bounded-depth',type(depth)is int and 0<=depth<64)
    cap=reader.operation.child(CAPABILITY)
    need('own-Int32-array-capability',cap.get('typeName')=='int[]'and cap.get('elementType')=='int'
        and cap.get('headerBytes')==4 and cap.get('elementWireBytes')==4 and cap.get('countRange')==[-1,64]
        and cap.get('countLimit')==64 and all(cap.get(k)is True for k in('nullable','positiveCountsAdmitted','rawBitsPreserved','wholeGrammarAdmitted'))
        and all(cap.get(k)is False for k in('booleanNormalizationClaimed','elementCallbackUsed','parentFieldAdmitted','wholeOwnerAdmitted')))
    at=reader.pos;need('complete-count',at+4<=reader.limit);count=struct.unpack_from('<i',reader.data,at)[0]
    need('bounded-count',-1<=count<=64);need('complete-payload',at+4+4*max(0,count)<=reader.limit)
    if budget is None:budget=dict(remaining=16384)
    need('shared-node-budget',type(budget)is dict and set(budget)=={'remaining'}and type(budget['remaining'])is int
        and 1+max(0,count)<=budget['remaining']<=16384)
    budget['remaining']-=1+max(0,count);reader.take(4,CAPABILITY+'.count')
    entries=[dict(rawHex=reader.take(4,CAPABILITY+'.element').hex())for _ in range(max(0,count))]
    result=dict(kind=CAPABILITY,start=at,end=reader.pos,isNull=count==-1,count=count,elements=entries)
    reader.records.append(result);return result

"""Normal binary32 first-prefix RoomVerb three-buffer mixing."""
from __future__ import annotations
from scripts.game_data.wwise_biquad_arithmetic import _add,_mul,_dyadic,UnsupportedArithmetic


def evaluate_prefix(dry,wet_a,wet_b,previous,target,frames,mxcsr):
    if type(mxcsr) is not int or not 0<=mxcsr<2**16 or mxcsr&0x6000:raise UnsupportedArithmetic('nearestRoundingNotObserved')
    if mxcsr&0x1f80!=0x1f80:raise UnsupportedArithmetic('unmaskedExceptionsUnsupported')
    if type(frames) is not int or frames<4 or frames>512 or frames&(frames-1):raise UnsupportedArithmetic('roomBlendFrameCountNotSelected')
    if any(len(a)!=n for a,n in [(dry,4),(wet_a,4),(wet_b,4),(previous,3),(target,3)]):raise ValueError('complete room blend prefix operands required')
    for row in (dry,wet_a,wet_b,previous,target):
        for word in row:_dyadic(word)
    constant=all(a==b or not (a&0x7fffffff) and not (b&0x7fffffff) for a,b in zip(previous,target))
    reciprocal=(127-(frames.bit_length()-1))<<23
    steps=[_mul(_add(b,a^(1<<31)),reciprocal) for a,b in zip(previous,target)] if not constant else [0]*3
    gains=list(previous);result=[]
    for index in range(4):
        # The original helper uses separate MUL/ADD, not fused accumulation.
        result.append(_add(_add(_mul(dry[index],gains[0]),_mul(wet_a[index],gains[1])),_mul(wet_b[index],gains[2])))
        if not constant:gains=[_add(g,s) for g,s in zip(gains,steps)]
    return result

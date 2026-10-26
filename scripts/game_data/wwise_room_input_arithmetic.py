"""Selected standard-stereo fold and bit-preserving circular history prefixes."""
from __future__ import annotations
from scripts.game_data.wwise_biquad_arithmetic import _add,_mul,_dyadic,_word,UnsupportedArithmetic


def _history_binary(a,b,op,mxcsr):
    # DAZ changes only incoming denormals; FTZ applies to each separate native
    # result. Validate inputs outside the output-underflow catch so an unread
    # input policy cannot be mistaken for a tiny computed result.
    a=_word(a);b=_word(b)
    if mxcsr&0x40:
        a=a&0x80000000 if a&0x7f800000==0 else a
        b=b&0x80000000 if b&0x7f800000==0 else b
    an,ae=_dyadic(a);bn,be=_dyadic(b)
    try:return (_add if op=='add' else _mul)(a,b)
    except UnsupportedArithmetic as error:
        if str(error)!='subnormalPolicyUnsupported' or not mxcsr&0x8000:raise
        if op=='mul':n=an*bn
        else:
            e=min(ae,be);n=(an<<(ae-e))+(bn<<(be-e))
        # Original SSE FTZ flushes even a tiny exact value that would round up
        # to the least normal float under gradual-underflow processing.
        return 0x80000000 if n<0 else 0


def fold_prefix(left,right,coefficient,mxcsr):
    if type(mxcsr) is not int or not 0<=mxcsr<2**16 or mxcsr&0x6000 or mxcsr&0x1f80!=0x1f80:raise UnsupportedArithmetic('roomFoldRoundingUnsupported')
    if len(left)!=4 or len(right)!=4:raise ValueError('four words per stereo plane required')
    _dyadic(coefficient)
    for word in left+right:_dyadic(word)
    return [_add(_mul(b,coefficient),_add(_mul(a,coefficient),0)) for a,b in zip(left,right)]


def delay_prefix(history,length,index,frames):
    if len(history)!=4 or not all(type(w) is int and 0<=w<2**32 for w in history):raise ValueError('four old history words required')
    if not all(type(v) is int for v in (length,index,frames)) or not 4<=length<2**32 or not 0<=index<length or not 4<=frames<=512:raise ValueError('room delay extent not selected')
    return list(history),(index+frames)%length


def diffusion_prefix(inputs,history,gain,mxcsr):
    """Four independent paired-history lanes, with one rounding per SSE op."""
    if type(mxcsr) is not int or not 0<=mxcsr<2**16 or mxcsr&0x6000 or mxcsr&0x1f80!=0x1f80:raise UnsupportedArithmetic('roomDiffusionRoundingUnsupported')
    if len(inputs)!=4 or len(history)!=8:raise ValueError('four inputs and four history pairs required')
    add=lambda a,b:_history_binary(a,b,'add',mxcsr)
    mul=lambda a,b:_history_binary(a,b,'mul',mxcsr)
    outputs=[add(mul(add(x,history[2*i+1]^0x80000000),gain),history[2*i]) for i,x in enumerate(inputs)]
    return outputs,[w for pair in zip(inputs,outputs) for w in pair]


def tone_prefix(inputs,matrix,history,mxcsr):
    """Original four-sample expanded matrix kernel, separate MULPS/ADDPS."""
    if type(mxcsr) is not int or not 0<=mxcsr<2**16 or mxcsr&0x6000 or mxcsr&0x1f80!=0x1f80:raise UnsupportedArithmetic('roomToneRoundingUnsupported')
    if len(inputs)!=4 or len(matrix)!=32 or len(history)!=4:raise ValueError('four samples/history and eight coefficient vectors required')
    add=lambda a,b:_history_binary(a,b,'add',mxcsr)
    mul=lambda a,b:_history_binary(a,b,'mul',mxcsr)
    result=[]
    for lane in range(4):
        v=add(mul(inputs[lane],matrix[lane]),mul(history[0],matrix[16+lane]))
        v=add(v,mul(history[1],matrix[20+lane]))
        v=add(mul(inputs[2],matrix[4+lane]),v)
        v=add(mul(inputs[1],matrix[8+lane]),v)
        v=add(v,mul(inputs[0],matrix[12+lane]))
        v=add(v,mul(history[2],matrix[24+lane]))
        v=add(v,mul(history[3],matrix[28+lane]))
        result.append(v)
    return result,[inputs[3],inputs[2],result[3],result[2]]

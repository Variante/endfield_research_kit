
"""Bit-exact bounded EQ and accumulation, with one rounding per native operation.

The selected native contract owns the expression programs. Integer dyadics
avoid host float rounding and the double rounding of a host-emulated FMA.
This evaluator does not load native libraries, initialize Wwise or a device.
"""
from __future__ import annotations


class UnsupportedArithmetic(ValueError):
    pass


def _word(value):
    if type(value) is not int or not 0<=value<2**32:raise ValueError('explicit float32 word required')
    return value


def _dyadic(word):
    word=_word(word);exponent=(word>>23)&255;fraction=word&0x7fffff
    if exponent==255:raise UnsupportedArithmetic('nonfiniteArithmetic')
    if exponent==0 and fraction:raise UnsupportedArithmetic('subnormalPolicyUnsupported')
    return ((-1 if word>>31 else 1)*((1<<23)|fraction),exponent-150) if exponent else (0,-149)


def _rounded(n,exponent,negative_zero=False):
    if not n:return 0x80000000 if negative_zero else 0
    sign=0x80000000 if n<0 else 0;n=abs(n);power=n.bit_length()-1+exponent
    if power < -126:raise UnsupportedArithmetic('subnormalPolicyUnsupported')
    shift=n.bit_length()-24
    if shift>0:
        quotient,remainder=divmod(n,1<<shift);half=1<<(shift-1)
        n=quotient+int(remainder>half or remainder==half and quotient&1)
    else:n<<=-shift
    if n==1<<24:n>>=1;power+=1
    if power>127:raise UnsupportedArithmetic('floatRangeUnsupported')
    return sign|((power+127)<<23)|(n&0x7fffff)


def _add(a,b):
    an,ae=_dyadic(a);bn,be=_dyadic(b);e=min(ae,be)
    return _rounded((an<<(ae-e))+(bn<<(be-e)),e,a==b==0x80000000)


def _mul(a,b):
    an,ae=_dyadic(a);bn,be=_dyadic(b)
    return _rounded(an*bn,ae+be,bool((a^b)>>31))


def _fma(a,b,c):
    an,ae=_dyadic(a);bn,be=_dyadic(b);cn,ce=_dyadic(c);e=min(ae+be,ce)
    return _rounded((an*bn<<(ae+be-e))+(cn<<(ce-e)),e,bool((a^b)>>31) and c==0x80000000)


def evaluate_accumulation_prefix(*,source_words,destination_words,coefficient,step=None,lane_words=(),mxcsr):
    """Original AVX first four lanes: fused source*coefficient + destination.

    A ramp first forms each coefficient with a separate fused step*lane +
    initial coefficient. The selected native contract supplies lane constants.
    """
    if type(mxcsr) is not int or not 0<=mxcsr<2**16 or mxcsr&0x6000:raise UnsupportedArithmetic('nearestRoundingNotObserved')
    if mxcsr&0x1f80!=0x1f80:raise UnsupportedArithmetic('unmaskedExceptionsUnsupported')
    if len(source_words)!=4 or len(destination_words)!=4 or step is not None and len(lane_words)!=4:raise ValueError('four accumulation operands required')
    gains=[coefficient]*4 if step is None else [_fma(step,lane,coefficient) for lane in lane_words]
    return [_fma(source,gain,dest) for source,gain,dest in zip(source_words,gains,destination_words)]


def validate_program(program):
    nodes=program['nodes'];outputs=program['outputs']
    if not 1<=len(nodes)<=512 or len(outputs)!=4:raise ValueError('bounded four-output biquad program required')
    arities={'xor':2,'add32':2,'mul32':2,'fma32':3}
    for i,node in enumerate(nodes):
        if not isinstance(node,list) or not node:raise ValueError('biquad node shape differs')
        op=node[0]
        if op=='word':
            if len(node)!=2:raise ValueError('word node shape differs')
            _word(node[1])
        elif op=='input':
            if len(node)!=4 or node[1] not in ('input','coefficient','history') or type(node[2]) is not int or node[2]!=0 or type(node[3]) is not int or not 0<=node[3]<(5 if node[1]=='coefficient' else 4):raise ValueError('first-buffer input dependency differs')
        elif op not in arities or len(node)!=arities[op]+1 or any(type(r) is not int or not 0<=r<i for r in node[1:]):raise ValueError('biquad operation or dependency differs')
    if any(type(r) is not int or not 0<=r<len(nodes) for r in outputs):raise ValueError('biquad output reference differs')


def evaluate_prefix(program, *, input_words, coefficient_words, history_words, mxcsr):
    validate_program(program)
    if type(mxcsr) is not int or not 0<=mxcsr<2**16 or mxcsr&0x6000:raise UnsupportedArithmetic('nearestRoundingNotObserved')
    if mxcsr&0x1f80!=0x1f80:raise UnsupportedArithmetic('unmaskedExceptionsUnsupported')
    inputs={'input':input_words,'coefficient':coefficient_words,'history':history_words}
    if any(len(inputs[k])!=n for k,n in [('input',4),('coefficient',5),('history',4)]):raise ValueError('complete prefix operands required')
    for words in inputs.values():
        for word in words:_dyadic(word)
    values=[]
    for node in program['nodes']:
        op=node[0]
        if op=='word':value=node[1]
        elif op=='input':value=inputs[node[1]][node[3]]
        else:
            args=[values[r] for r in node[1:]]
            value=args[0]^args[1] if op=='xor' else {'add32':_add,'mul32':_mul,'fma32':_fma}[op](*args)
        values.append(value)
    return [values[r] for r in program['outputs']]



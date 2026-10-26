"""Compare admitted original EQ operands against selected native programs."""
from __future__ import annotations
import struct
from scripts.game_data.wwise_biquad_arithmetic import UnsupportedArithmetic, evaluate_prefix, _dyadic


def compare_prefix(step,declared):
    result=dict(schema='endfield.biquad-first-buffer-prefix.v1',status='biquadOperandsNotAdmitted',wholeEventToDeviceClaim=False,coveredChannels=[0],comparedFrames=0)
    if step.get('status')!='pairedBiquadOperands':return result
    programs=declared.get('prefixPrograms')
    if not programs:return dict(result,status='biquadArithmeticNotDeclared')
    if step['geometry']['segmentCount']!=1 or step['geometry']['bufferCount']!=2:return dict(result,status='biquadGeometryUnsupported')
    mode='avx' if step['geometry']['processorMode']==1 else 'sse'
    before=bytes.fromhex(step['beforePrefix']);after=bytes.fromhex(step['afterPrefix'])
    if len(before)!=16 or len(after)!=16:return dict(result,status='biquadPrefixesIncomplete')
    try:
        words=evaluate_prefix(programs[mode],input_words=list(struct.unpack('<4I',before)),coefficient_words=step['coefficientWords'],history_words=step['initialHistoryWords'],mxcsr=step['mxcsr'])
        actual=struct.unpack('<4I',after)
        for word in actual:_dyadic(word)
    except UnsupportedArithmetic as error:return dict(result,status=str(error),processor=mode)
    expected=struct.pack('<4I',*words)
    mismatches=[dict(frame=i,expectedWord=w,actualWord=actual[i]) for i,w in enumerate(words) if w!=actual[i]]
    nonzero=any(w&0x7fffffff for w in words+list(actual))
    return dict(result,status='prefixDiffers' if mismatches else 'exactFiniteNonzeroBiquadPrefix' if nonzero else 'zeroPrefixOnly',processor=mode,comparedFrames=4,expectedPrefix=expected.hex(),mismatches=mismatches,
        evidenceBoundary='Reviewed first-block instruction expressions explain four observed first-buffer values bit-for-bit under admitted nearest rounding, including distinct SSE rounding and AVX fused operations. Native service/call/operand admission, final history, EQ output gain, other channels, whole buffers and individual Event contribution remain separate.')

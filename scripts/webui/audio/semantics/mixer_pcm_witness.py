"""Bounded constant-matrix equation at the original unfiltered consumer input.

Evidence and admission boundary:

Offline consumer review now separates the earlier source snapshot from the
actual unfiltered matrix-consumer input. The selected full bodies and read
order are recorded in the existing mixer-frame contract and authenticated
during preparation. That consumer takes a cohort of source indices, source
descriptor and filter arrays, an output-descriptor reference, effective gain
pairs and previous/target matrix arrays. It updates bypass filter history, then
accumulates planar contributions into existing output. Matrix rows are padded
to a vector-width boundary; the first two stored coefficients do not include
the second input channel's row. Capturing the caller's row pointers does not
observe this consumer's input PCM.

Audio's `mixer_pcm_witness` checks a supplied bounded first-output equation:
one first-row source, constant gain/matrix, one nonzero channel contribution,
zero initial output and nearest native rounding. Ramps, cross-channel sums,
unsupported float ranges and a source-sample boundary are withheld. Original
isolated native filtered-source and submitted PCM reproduce nonzero prefixes
under supplied identity-matrix/zero-bus/rounding conditions; silence and
terminal gain ramps remain separate. This is a regression of the equation
evaluator, not a live observation of the new consumer boundary or independent
filter parity.
"""
from __future__ import annotations

import math
import struct


def _float(word):
    if type(word) is not int or not 0<=word<2**32:raise ValueError('explicit float32 word required')
    return struct.unpack('<f',struct.pack('<I',word))[0]


def _round(value):
    return struct.unpack('<f',struct.pack('<f',value))[0]


def compare_constant_first_output(source_planes, initial_output, output, *,
        input_boundary, cohort_indices, source_channels, output_channels,
        frame_capacity, valid_frames, previous_gain_bits, target_gain_bits,
        previous_matrix_words, target_matrix_words, matrix_stride, mxcsr):
    """Compare a supplied equation; native invocation/data admission is separate.

    Restrict to one selected source and one nonzero contribution to output plane
    zero. This makes separate MUL+ADD and fused accumulation agree on finite
    normal sample values with zero initial output. Ramps, cross-channel sums,
    filters and nonzero initial accumulation need other independently proved
    evaluators. A source-sample snapshot is not a mixer-kernel input witness.
    """
    base=dict(schema='endfield.constant-mixer-first-output-prefix.v1',
        wholeEventToDeviceClaim=False,coveredOutputChannels=[0],comparedFrames=0)
    def withheld(status):return dict(base,status=status)
    if input_boundary!='unfilteredMatrixConsumerEntry':return withheld('inputBoundaryUnproved')
    if cohort_indices!=[0]:return withheld('sourceCohortNotSingleFirstRow')
    if type(source_channels) is not int or not 1<=source_channels<=2 or type(output_channels) is not int or not 1<=output_channels<=2:
        return withheld('channelLayoutUnsupported')
    if type(frame_capacity) is not int or type(valid_frames) is not int or not 0<valid_frames<=frame_capacity:
        return withheld('frameExtentUnsupported')
    if type(mxcsr) is not int or not 0<=mxcsr<2**32 or mxcsr&0x6000:
        return withheld('nearestRoundingNotObserved')
    if matrix_stride!=((output_channels+7)//8)*8:return withheld('matrixStrideDisagrees')
    if len(source_planes)!=source_channels:return withheld('sourcePlanesMissing')
    needed=(source_channels-1)*matrix_stride+output_channels
    if len(previous_matrix_words)<needed or len(target_matrix_words)<needed:
        return withheld('matrixWordsMissing')
    previous=_float(previous_gain_bits);target=_float(target_gain_bits)
    if not math.isfinite(previous) or not math.isfinite(target):return withheld('nonfiniteGain')
    if 0<abs(previous)<2**-126 or 0<abs(target)<2**-126:return withheld('subnormalPolicyUnsupported')
    if previous!=target:return withheld('gainRampUnsupported')
    factors=[]
    for channel in range(source_channels):
        a=_float(previous_matrix_words[channel*matrix_stride]);b=_float(target_matrix_words[channel*matrix_stride])
        if not math.isfinite(a) or not math.isfinite(b):return withheld('nonfiniteMatrix')
        if 0<abs(a)<2**-126 or 0<abs(b)<2**-126:return withheld('subnormalPolicyUnsupported')
        if a!=b:return withheld('matrixRampUnsupported')
        try:factor=_round(a*previous)
        except OverflowError:return withheld('factorOverflow')
        if not math.isfinite(factor):return withheld('factorOverflow')
        factors.append(factor)
    if sum(value!=0 for value in factors)>1:return withheld('crossChannelAccumulationUnsupported')
    planes=[bytes.fromhex(raw) for raw in source_planes]
    before=bytes.fromhex(initial_output);after=bytes.fromhex(output)
    if any(len(raw)>256 or len(raw)%4 for raw in planes+[before,after]):raise ValueError('bounded complete float32 prefixes required')
    frames=min([valid_frames,len(before)//4,len(after)//4]+[len(raw)//4 for raw in planes])
    if not frames:return withheld('noComparableSamples')
    mismatches=[];signed_zero_differences=0;nonzero=False
    for frame in range(frames):
        initial=struct.unpack_from('<f',before,frame*4)[0]
        actual=struct.unpack_from('<f',after,frame*4)[0]
        samples=[struct.unpack_from('<f',raw,frame*4)[0] for raw in planes]
        if not all(math.isfinite(x) for x in samples+[initial,actual]+factors):return withheld('nonfiniteSamples')
        if initial!=0:return withheld('nonzeroInitialAccumulationUnsupported')
        if any(0<abs(x)<2**-126 for x in samples+factors):return withheld('subnormalPolicyUnsupported')
        expected=0.0
        for sample,factor in zip(samples,factors):
            try:contribution=_round(sample*factor)
            except OverflowError:return withheld('contributionOverflow')
            if not math.isfinite(contribution) or 0<abs(contribution)<2**-126:return withheld('contributionRangeUnsupported')
            expected=_round(expected+contribution)
        nonzero=nonzero or actual!=0 or expected!=0
        if expected!=actual:
            if len(mismatches)<8:mismatches.append(dict(frame=frame,expectedHex=struct.pack('<f',expected).hex(),actualHex=after[frame*4:frame*4+4].hex()))
        elif expected==0 and struct.pack('<f',expected)!=after[frame*4:frame*4+4]:signed_zero_differences+=1
    return dict(base,status='prefixDiffers' if mismatches else 'exactFiniteNonzeroSampleValues' if nonzero else 'zeroPrefixOnly',
        comparedFrames=frames,mismatches=mismatches,signedZeroDifferenceCount=signed_zero_differences,
        evidenceBoundary='Supplied consumer-input planes, constant coefficients/gain and zero initial output explain these first-output-plane sample values. Actual invocation/data admission, other outputs, whole buffers and Event/device attribution remain separate.')

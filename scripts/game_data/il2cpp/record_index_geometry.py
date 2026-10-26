"""Prove a signed high-multiply/add/shift bridge on valid record offsets.

The bound covers every selected nonnegative record index, rather than random
machine arithmetic samples. Input pointer/base/header identity and stability
are conditions; no live metadata pointer or invalid-index behavior is proved.
"""
from __future__ import annotations


def prove_record_index_geometry(*,multiplier,shift,record_bytes,records):
    values=(multiplier,shift,record_bytes,records)
    if any(type(v)!=int for v in values):raise ValueError('recordIndexGeometry.integer-parameters')
    if not -(1<<63)<=multiplier<0 or not 0<=shift<64 or record_bytes<=0 or not 0<records<=1<<31:
        raise ValueError('recordIndexGeometry.parameter-range')
    unsigned=multiplier+(1<<64);power=1<<(64+shift)
    if unsigned!=(power+record_bytes-1)//record_bytes:raise ValueError('recordIndexGeometry.reciprocal')
    largest=records-1;max_delta=largest*record_bytes;excess=unsigned*record_bytes-power
    if max_delta>=1<<63:raise ValueError('recordIndexGeometry.signed-delta-range')
    if not 0<=excess<record_bytes or excess*largest>=power:raise ValueError('recordIndexGeometry.rounding-bound')
    # high_signed(multiplier*n)+n = floor(unsigned*n/2^64).
    # On n=i*record_bytes, the subsequent shift is
    # floor(i + excess*i/power) = i. The pre-shift result is
    # nonnegative and fits signed QWORD, so the sign correction is zero.
    max_pre_shift=(unsigned*max_delta)//(1<<64)
    if not 0<=max_pre_shift<1<<63:raise ValueError('recordIndexGeometry.high-add-range')
    return {'selectedRecordIndicesCheckedByBound':records,'validRecordIndexRange':[0,largest],
        'validRecordDeltaRange':[0,max_delta],'reciprocalExcess':excess,
        'highMultiplyAddAndShiftReturnRecordIndexProved':True,
        'signCorrectionIsZeroForValidSelectedRecordOffsetsProved':True,
        'indexFitsSignedDwordAndPointerRoundTripConditionallyProved':True,
        'actualLiveMetadataPointerOrGlobalStabilityProved':False,'arbitrarySignedDeltaDivisionProved':False}

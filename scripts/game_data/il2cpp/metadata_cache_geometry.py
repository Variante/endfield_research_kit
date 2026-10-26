"""Prove an unsigned high-product/add/shift quotient on record multiples.

For x >= 0, h = high(M*x) <= x, ((x-h)>>1)+h = floor((x+h)/2).
The final shift yields floor((2^64+M)*x / 2^(65+shift)). A reciprocal
error bound proves every record multiple through the selected section size.
This is arithmetic under the named input condition, never live capacity.
"""
from __future__ import annotations


def prove_metadata_cache_geometry(*,multiplier,shift,record_bytes,section_bytes,record_count):
    values=(multiplier,shift,record_bytes,section_bytes,record_count)
    if any(type(v)!=int for v in values):raise ValueError('metadataCacheGeometry.integer-input')
    if not 0<=multiplier<1<<64 or not 0<=shift<=62 or record_bytes<=0 or record_count<0:
        raise ValueError('metadataCacheGeometry.input-range')
    if not 0<=section_bytes<1<<31 or section_bytes!=record_count*record_bytes:
        raise ValueError('metadataCacheGeometry.signed-header-record-size')
    power=1<<(65+shift);reciprocal=(1<<64)+multiplier
    if reciprocal!=(power+record_bytes-1)//record_bytes:raise ValueError('metadataCacheGeometry.reciprocal')
    error=reciprocal*record_bytes-power
    if not 0<=error<record_bytes or error*record_count>=power:
        raise ValueError('metadataCacheGeometry.reciprocal-error-bound')
    high=(multiplier*section_bytes)>>64
    if high>section_bytes or section_bytes+high>=1<<64:raise ValueError('metadataCacheGeometry.intermediate-range')
    actual=(((section_bytes-high)>>1)+high)>>shift
    if actual!=record_count:raise ValueError('metadataCacheGeometry.selected-quotient')
    return {'selectedMetadataSectionBytes':section_bytes,'selectedMetadataRecordCount':record_count,
        'recordMultiplesCheckedByBound':record_count+1,'selectedCacheElementCount':actual,
        'cacheElementBytes':8,'selectedCacheRequestedBytes':actual*8,
        'allSelectedNonnegativeRecordMultipleQuotientsProved':True,
        'selectedNonnegativeSignedDwordSizeAndIntermediateArithmeticProved':True,
        'actualHeaderBytesEqualSelectedMetadataProved':False,'actualCacheAllocationCapacityProved':False}

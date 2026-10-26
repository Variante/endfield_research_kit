"""Bounded v150 common FX controls, below semantic projections.

The prefix API leaves the tail opaque; the complete API requires exact EOF.
FX parameter IDs are plug-in setter IDs, separate from node property names.
"""
from __future__ import annotations

import hashlib
import math
import struct


class EffectControlsError(ValueError):
    def __init__(self,check,offset,required,remaining):
        self.diagnostic=dict(check=check,offset=offset,required=required,remaining=remaining)
        super().__init__(f'{check}: offset={offset} required={required} remaining={remaining}')


class _Reader:
    def __init__(self, data, offset=0):
        self.data = data
        self.offset = offset

    def take(self, fmt, label):
        size = struct.calcsize(fmt)
        if size > len(self.data) - self.offset:
            raise EffectControlsError(label, self.offset, size, len(self.data) - self.offset)
        value = struct.unpack_from(fmt, self.data, self.offset)[0]
        self.offset += size
        return value

    def varuint(self, label):
        start = self.offset; value = 0
        for _ in range(5):
            word = self.take('<B', label); value = (value << 7) | (word & 127)
            if value > 0xffffffff:
                raise EffectControlsError(label + '-overflow', start, 32, value.bit_length())
            if not word & 128:
                return value
        raise EffectControlsError(label + '-unterminated', start, 5, 5)


def read_effect_rtpc(data: bytes, *, bank_version: int) -> dict:
    """Read one HIRC FX body after its object ID has been removed."""
    if bank_version!=150:
        raise EffectControlsError('effect-bank-version',0,150,bank_version)
    reader = _Reader(data); take = reader.take; varuint = reader.varuint
    plugin_class=take('<I','effect-class')
    parameter_bytes=take('<I','effect-parameter-length')
    if parameter_bytes>len(data)-reader.offset:
        raise EffectControlsError('effect-parameter-bytes',reader.offset,parameter_bytes,len(data)-reader.offset)
    parameter=data[reader.offset:reader.offset+parameter_bytes];reader.offset+=parameter_bytes
    media_count=take('<B','effect-media-count');media=[]
    for _ in range(media_count):
        media.append(dict(index=take('<B','effect-media-index'),sourceId=take('<I','effect-media-source')))
    rtpc_offset=reader.offset;count=take('<H','effect-rtpc-count');curves=[]
    for ordinal in range(count):
        start=reader.offset
        key=take('<I','effect-rtpc-id');kind=take('<B','effect-rtpc-type');mode=take('<B','effect-rtpc-accumulation')
        parameter_id=varuint('effect-rtpc-parameter-id');curve_id=take('<I','effect-rtpc-curve-id')
        scaling=take('<B','effect-rtpc-scaling');point_count=take('<H','effect-rtpc-point-count')
        if point_count*12>len(data)-reader.offset:
            raise EffectControlsError('effect-rtpc-points',reader.offset,point_count*12,len(data)-reader.offset)
        points=[]
        for index in range(point_count):
            bits_from=take('<I','effect-rtpc-point-from');bits_to=take('<I','effect-rtpc-point-to');interpolation=take('<I','effect-rtpc-point-interpolation')
            from_value=struct.unpack('<f',struct.pack('<I',bits_from))[0];to_value=struct.unpack('<f',struct.pack('<I',bits_to))[0]
            points.append(dict(index=index,fromBits=bits_from,toBits=bits_to,fromValue=from_value if math.isfinite(from_value) else None,toValue=to_value if math.isfinite(to_value) else None,interpolation=interpolation))
        curves.append(dict(ordinal=ordinal,offset=start,byteLength=reader.offset-start,gameSyncId=key,gameSyncType=kind,gameSyncKey=(kind<<32)|key,accumulation=mode,parameterId=parameter_id,parameterIdLow16=parameter_id&65535,curveId=curve_id,scaling=scaling,pointCount=point_count,points=points))
    return dict(schema='endfield.wwise-effect-rtpc-prefix.v1',pluginClassId=plugin_class,parameterBytes=parameter_bytes,parameterSha256=hashlib.sha256(parameter).hexdigest(),media=media,rtpcOffset=rtpc_offset,rtpcCurveCount=count,rtpcCurves=curves,bytesFramed=reader.offset,remainingStateAndPropertyBytes=len(data)-reader.offset,evidenceBoundary='Exact v150 FX parameter/media/RTPC prefix. Type, accumulation, scaling and interpolation values stay raw. State/default-property tail, current controls, target membership, processing and physical runtime occurrence are not established.')


def read_effect_controls(data: bytes, *, bank_version: int) -> dict:
    """Frame the common FX base body, including state and default controls.

    Values and flags remain raw. Native state-count truncation is rejected,
    since it cannot establish complete framing of a declared larger array.
    """
    result = read_effect_rtpc(data, bank_version=bank_version)
    prefix_extent = result['bytesFramed']; reader = _Reader(data, prefix_extent)
    take = reader.take; varuint = reader.varuint
    def count(label, minimum):
        value = varuint(label)
        if value > (len(data) - reader.offset) // minimum:
            raise EffectControlsError(label + '-extent', reader.offset, value * minimum, len(data) - reader.offset)
        return value
    def value(bits):
        number = struct.unpack('<f', struct.pack('<I', bits))[0]
        return number if math.isfinite(number) else None
    properties = []
    for index in range(count('effect-state-property-count', 3)):
        parameter_id = varuint('effect-state-property-id')
        properties.append(dict(index=index, parameterId=parameter_id, parameterIdLow16=parameter_id & 65535,
                               accumulation=take('<B', 'effect-state-property-mode'), flagRaw=take('<B', 'effect-state-property-flag')))
    groups = []
    for index in range(count('effect-state-group-count', 6)):
        group_id = take('<I', 'effect-state-group-id'); sync_type = take('<B', 'effect-state-sync-type')
        state_count = count('effect-state-count', 6)
        if state_count > 65535:
            raise EffectControlsError('effect-state-count-low16-truncation', reader.offset, 65535, state_count)
        states = []
        for state_index in range(state_count):
            state_id = take('<I', 'effect-state-id'); value_count = take('<H', 'effect-state-value-count')
            if value_count * 6 > len(data) - reader.offset:
                raise EffectControlsError('effect-state-value-extent', reader.offset, value_count * 6, len(data) - reader.offset)
            ids = [take('<H', 'effect-state-value-id') for _ in range(value_count)]
            values = []
            for value_index, parameter_id in enumerate(ids):
                bits = take('<I', 'effect-state-value')
                values.append(dict(index=value_index, parameterId=parameter_id, valueBits=bits, value=value(bits)))
            states.append(dict(index=state_index, stateId=state_id, values=values))
        groups.append(dict(index=index, groupId=group_id, syncType=sync_type, states=states))
    state_end = reader.offset; default_count = take('<H', 'effect-default-count'); defaults = []
    if default_count * 6 > len(data) - reader.offset:
        raise EffectControlsError('effect-default-extent', reader.offset, default_count * 6, len(data) - reader.offset)
    for index in range(default_count):
        parameter_id = varuint('effect-default-id'); flag = take('<B', 'effect-default-flag'); bits = take('<I', 'effect-default-value')
        defaults.append(dict(index=index, parameterId=parameter_id, parameterIdLow16=parameter_id & 65535,
                             flagRaw=flag, valueBits=bits, value=value(bits)))
    if reader.offset != len(data):
        raise EffectControlsError('effect-controls-trailing-bytes', reader.offset, 0, len(data) - reader.offset)
    result.update(schema='endfield.wwise-effect-controls.v1', prefixBytesFramed=prefix_extent,
                  stateProperties=properties, stateGroups=groups, stateBytes=state_end - prefix_extent,
                  defaultProperties=defaults, bytesFramed=reader.offset, remainingStateAndPropertyBytes=0,
                  evidenceBoundary='Exact complete v150 common FX parameter/media/RTPC/state/default framing. Values, flags and IDs remain raw in the plug-in parameter domain. This does not prove native admission, effective live states, accepted setter updates, target membership, processing or physical runtime occurrence.')
    return result

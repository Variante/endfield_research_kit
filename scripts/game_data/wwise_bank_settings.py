"""Exact v150 STMG framing below Audio semantics.

Read widths follow the reviewed native settings consumer. Stored defaults are
not live parameter values; this reader neither initializes Wwise nor selects
an object, bus, State or Switch. Unknown scalar meanings stay anonymous.
"""
from __future__ import annotations

import math
import struct


class BankSettingsError(ValueError):
    def __init__(self, check, *, offset, expected, actual):
        self.diagnostic = dict(check=check, offset=offset, expected=expected, actual=actual)
        super().__init__(f"{check} at {offset}: expected {expected}; actual {actual}")


class _Reader:
    def __init__(self, data):
        self.data, self.at = memoryview(data), 0

    def take(self, size, label):
        if not 0 <= size <= len(self.data)-self.at:
            raise BankSettingsError(label, offset=self.at, expected=size,
                                    actual=len(self.data)-self.at)
        raw = self.data[self.at:self.at+size].tobytes()
        self.at += size
        return raw

    def uint(self, size, label):
        return int.from_bytes(self.take(size, label), 'little')

    def count(self, stride, label):
        value = self.uint(4, label)
        remaining = len(self.data)-self.at
        if value > 65535 or value*stride > remaining:
            raise BankSettingsError(label, offset=self.at-4,
                                    expected=f"0..65535 records fitting {remaining} bytes",
                                    actual=value)
        return value

    def floating(self, label):
        raw = self.take(4, label)
        bits, value = struct.unpack('<I', raw)[0], struct.unpack('<f', raw)[0]
        return dict(bits=bits, value=value if math.isfinite(value) else None)


def read_settings(data: bytes, *, bank_version: int) -> dict:
    if type(bank_version) is not int or bank_version != 150:
        raise BankSettingsError('bankVersion', offset=0, expected=150, actual=bank_version)
    r = _Reader(data)
    header = dict(firstWord=r.uint(2, 'header.firstWord'),
                  firstFloat=r.floating('header.firstFloat'),
                  secondWord=r.uint(2, 'header.secondWord'),
                  thirdWord=r.uint(2, 'header.thirdWord'))
    states = []
    for i in range(r.count(12, 'stateGroups.count')):
        at = r.at
        key = r.uint(4, f'stateGroups[{i}].id')
        transition = r.uint(4, f'stateGroups[{i}].transitionWord')
        rows = [struct.unpack('<3I', r.take(12, f'stateGroups[{i}].records[{j}]'))
                for j in range(r.count(12, f'stateGroups[{i}].records.count'))]
        states.append(dict(offset=at, id=key, transitionWord=transition, records=rows))
    switches = []
    for i in range(r.count(13, 'switchMappings.count')):
        at = r.at
        key = r.uint(4, f'switchMappings[{i}].id')
        parameter = r.uint(4, f'switchMappings[{i}].parameterId')
        kind = r.uint(1, f'switchMappings[{i}].kind')
        points = [r.take(12, f'switchMappings[{i}].points[{j}]').hex()
                  for j in range(r.count(12, f'switchMappings[{i}].points.count'))]
        switches.append(dict(offset=at, id=key, parameterId=parameter, kind=kind, pointsHex=points))
    default_count_offset = r.at
    defaults = []
    for i in range(r.count(21, 'parameterDefaults.count')):
        at = r.at
        key = r.uint(4, f'parameterDefaults[{i}].id')
        value = r.floating(f'parameterDefaults[{i}].default')
        mode = r.uint(4, f'parameterDefaults[{i}].modeWord')
        first = r.floating(f'parameterDefaults[{i}].firstFloat')
        second = r.floating(f'parameterDefaults[{i}].secondFloat')
        binding = r.uint(1, f'parameterDefaults[{i}].bindingByte')
        defaults.append(dict(offset=at, id=key, default=value, modeWord=mode,
                             firstFloat=first, secondFloat=second, bindingByte=binding,
                             rawHex=r.data[at:r.at].tobytes().hex()))
    auxiliary = []
    for i in range(r.count(32, 'auxiliaryRecords.count')):
        at = r.at
        key = r.uint(4, f'auxiliaryRecords[{i}].id')
        values = [r.floating(f'auxiliaryRecords[{i}].floats[{j}]') for j in range(7)]
        auxiliary.append(dict(offset=at, id=key, floats=values))
    if r.at != len(r.data):
        raise BankSettingsError('sectionClosure', offset=r.at, expected=0, actual=len(r.data)-r.at)
    return dict(schema='endfield.wwise-bank-settings.v1', bankVersion=bank_version,
                bytesConsumed=r.at, header=header, stateGroups=states,
                switchMappings=switches, parameterDefaults=defaults,
                defaultCountOffset=default_count_offset, auxiliaryRecords=auxiliary,
                evidenceBoundary='Exact stored framing under the v150 native read order; '
                'defaults, transitions and bindings are stored inputs, not effective live state.')

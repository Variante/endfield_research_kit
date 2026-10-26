"""Check selected literal request and configuration-pointer writer blocks.

The caller authenticates complete program ownership and literal/image bytes.
These are physical argument and result transfers. They do not name a returned
runtime class or assume that initialization ran or its storage survived.
"""
from __future__ import annotations

import struct


def _fail(check, value):
    raise ValueError(f'normalizationProducerInputs.{check}: {str(value)[:400]}')


def _rip(row, prefix):
    at, encoded = row
    raw = bytes.fromhex(encoded)
    if len(raw) != 7 or raw[:3] != bytes.fromhex(prefix):
        _fail('rip-operand', row)
    return at + 7 + struct.unpack_from('<i', raw, 3)[0]


def _target(row):
    at, encoded = row
    raw = bytes.fromhex(encoded)
    if len(raw) == 2 and (0x70 <= raw[0] <= 0x7f or raw[0] == 0xeb):
        return at + 2 + int.from_bytes(raw[1:], 'little', signed=True)
    if len(raw) == 5 and raw[0] == 0xe9:
        return at + 5 + int.from_bytes(raw[1:], 'little', signed=True)
    if len(raw) == 6 and raw[0] == 0x0f and 0x80 <= raw[1] <= 0x8f:
        return at + 6 + int.from_bytes(raw[2:], 'little', signed=True)
    return None


def validate_producer_inputs(program, blocks):
    """Check exact contiguous blocks and all direct branch entries into them."""
    inventory = {}
    previous_end = None
    for row in program:
        if not isinstance(row, list) or len(row) != 2 or type(row[0]) is not int:
            _fail('inventory-row', row)
        at, encoded = row
        raw = bytes.fromhex(encoded)
        if not raw or at in inventory or previous_end is not None and at != previous_end:
            _fail('inventory-contiguous', row)
        inventory[at] = row
        previous_end = at + len(raw)
    branches = [(row[0], _target(row)) for row in program]
    admitted = []
    cells = set()
    for block in blocks:
        rows = block['rows']
        if not rows or any(inventory.get(row[0]) != row for row in rows):
            _fail('owned-block-membership', rows)
        for first, second in zip(rows, rows[1:]):
            if first[0] + len(bytes.fromhex(first[1])) != second[0]:
                _fail('block-contiguous', rows)
        start = rows[0][0]
        end = rows[-1][0] + len(bytes.fromhex(rows[-1][1]))
        if any(start < target < end for _at, target in branches if target is not None):
            _fail('direct-interior-entry', (start, end))
        cell = _rip(rows[-1], '488905')
        if cell != block['cellRva'] or cell in cells:
            _fail('result-cell', cell)
        cells.add(cell)
        if block['kind'] == 'configuration':
            if len(rows) != 2 or _rip(rows[0], '488D05') != block['sourceRva']:
                _fail('configuration-pointer', rows)
            image = bytes.fromhex(block['sourceImageHex'])
            if len(image) != 16:
                _fail('configuration-image-size', len(image))
            admitted.append({'kind': 'configuration', 'cellRva': cell,
                             'sourceRva': block['sourceRva'], 'firstImageByte': image[0],
                             'runtimeConfigurationValueObserved': False})
            continue
        if block['kind'] not in ('freshImageClassRequest', 'retainedImageClassRequest'):
            _fail('block-kind', block['kind'])
        fresh = block['kind'] == 'freshImageClassRequest'
        if len(rows) != (5 if fresh else 4):
            _fail('request-row-count', len(rows))
        for row, literal, prefix in ((rows[0], block['typeName'], '4C8D05'),
                                     (rows[1], block['namespace'], '488D15')):
            data = bytes.fromhex(literal['rawHex'])
            if (_rip(row, prefix) != literal['targetRva'] or not data.endswith(b'\0')
                    or b'\0' in data[:-1] or data[:-1].decode('ascii') != literal['ascii']):
                _fail('request-literal', literal)
        if fresh and _rip(rows[2], '488B0D') != block['imageCellRva']:
            _fail('image-cell', rows[2])
        call = bytes.fromhex(rows[-2][1])
        if len(call) != 5 or call[0] != 0xe8:
            _fail('direct-lookup-call', rows[-2])
        target = rows[-2][0] + 5 + int.from_bytes(call[1:], 'little', signed=True)
        if target != block['lookupTargetRva']:
            _fail('lookup-target', target)
        admitted.append({'kind': 'classRequest', 'cellRva': cell,
            'requestedFullName': block['namespace']['ascii'] + '.' + block['typeName']['ascii'],
            'lookupTargetRva': target, 'imageArgumentSource': 'freshCell' if fresh else 'conditionalIncomingRcx',
            'lookupReturnedNamedClassProved': False})
    return {'checkedBlocks': len(admitted), 'inputs': admitted,
            'localDirectInteriorEntriesExcluded': True,
            'indirectOrExternalEntriesExcluded': False,
            'runtimeInitializationExecuted': False,
            'runtimeCellsUnchangedProved': False,
            'concreteGenericSharingSelected': False,
            'conditions': ['Selected block entered at its first instruction with valid disjoint storage.',
                           'Opaque lookup call returns normally with the regular Win64 ABI.',
                           'Retained-image block receives the stated RCX input; its origin is separate.']}

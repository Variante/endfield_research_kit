"""Prove the actual closed-Double getter's bounded physical read path.

Anonymous slots are shared with the independently checked compiled writer.
No live index equality, object/class parity or intervening-state observation
is supplied by the conditional same-address relation.
"""
from __future__ import annotations

import hashlib

from scripts.game_data.damage_snapshot_cache_flow import _address, _require
from scripts.game_data.il2cpp.context import relative_branch_target
from scripts.game_data.il2cpp.stack_argument_flow import _edge


def check_getter_program(rows, *, pointer, end, slots):
    array, count, length, payload = [slots[key] for key in (
        'arrayReference', 'countDword', 'arrayLengthDword', 'arrayPayload')]
    _require(all(type(value) is int and 0 <= value < 128 for value in (array, count, length, payload)),
             'cache-getter-slot-domain', 'positive disp8 declarations', slots)
    expected = [
        b'\x48\x83\xec\x28', b'\x3b\x51' + bytes([count]), 'count-edge',
        b'\x48\x8b\x49' + bytes([array]), b'\x48\x85\xc9', 'null-edge',
        b'\x3b\x51' + bytes([length]), 'array-edge', b'\x48\x63\xc2',
        b'\xf2\x0f\x10\x44\xc1' + bytes([payload]), b'\x48\x83\xc4\x28', b'\xc3',
    ]
    selected = rows[:len(expected)]
    _require(len(selected) == len(expected), 'cache-getter-program-length', len(expected), len(selected))
    address = pointer; edges = {}
    for row, encoding in zip(selected, expected):
        raw = bytes.fromhex(row['bytes'])
        _require(_address(row) == address and 0 < len(raw) <= 15 and address + len(raw) <= end,
                 'cache-getter-contiguity', hex(address), row['va'])
        if isinstance(encoding, str):
            edge = _edge(row); opcode = b'\x74' if encoding == 'null-edge' else b'\x73'
            _require(len(raw) == 2 and raw.startswith(opcode) and edge is not None,
                     'cache-getter-condition', opcode.hex(), raw.hex())
            edges[encoding] = edge[0]
        else:
            _require(raw == encoding, 'cache-getter-instruction', encoding.hex(), raw.hex())
        address += len(raw)
    boundaries = {_address(row) for row in rows}; normal = {_address(row) for row in selected}
    for name, target in edges.items():
        _require(target in boundaries and target not in normal, 'cache-getter-excluded-edge',
                 'owned instruction boundary outside returning path', [name, hex(target)])
    return {'getterEntry': hex(pointer), 'getterOwnedEnd': hex(end), 'getterFastReturn': selected[-1]['va'],
            'selectedInstructionCount': len(selected), 'excludedTargets': {k: hex(v) for k, v in edges.items()},
            'carrierSlots': {key: slots[key] for key in (
                'arrayReference', 'countDword', 'arrayLengthDword', 'arrayPayload')},
            'indexSource': 'signExtend(incoming Int32 EDX)',
            'arrayReadAddress': 'array payload + signExtend(incoming index) * 8',
            'arrayReadWidthBytes': 8, 'returnRegister': 'xmm0',
            'normalConditions': ['UInt32(index) < UInt32(receiver count)', 'nonnull array carrier',
                                 'UInt32(index) < UInt32(array length)'],
            'managedLayoutProved': False, 'liveIndexEqualityObserved': False}


def same_element_relation(old_count, consumer_index, array_length):
    """A bounded Int32 arithmetic consequence, not an observed invocation."""
    _require(all(type(value) is int for value in (old_count, consumer_index, array_length)),
             'cache-element-arithmetic-types', 'ordinary integer witnesses',
             [old_count, consumer_index, array_length])
    valid = (0 <= old_count < array_length <= 0x7fffffff and consumer_index == old_count)
    if not valid:
        return {'applies': False}
    new_count = old_count + 1
    return {'applies': True, 'newCount': new_count,
            'indexBelowNewCount': consumer_index < new_count,
            'indexBelowArrayLength': consumer_index < array_length,
            'writerElementByteOffset': old_count * 8,
            'readerElementByteOffset': consumer_index * 8}


def check_cache_getter(index, consumer_proof, writer_proof, spec):
    _require(spec.get('slotSource') == 'compiledHelperProof', 'cache-getter-slot-source',
             'compiledHelperProof', spec.get('slotSource'))
    _require(consumer_proof.get('claim') == 'snapshotCacheIndexToReturn'
             and writer_proof.get('claim') == 'snapshotCompiledHelperRawStore',
             'cache-getter-dependencies', 'fresh consumer and physical writer proofs',
             [consumer_proof.get('claim'), writer_proof.get('claim')])
    body = index.body('System.Collections.Generic.List`1', 'get_Item', class_arguments=['System.Double'])
    _require(body.pointer in index.extents, 'cache-getter-pdata-entry', 'exact .pdata entry', hex(body.pointer))
    end = index.extents[body.pointer]
    _require(0 < end - body.pointer <= 1024, 'cache-getter-pdata-extent', 'bounded exact owned extent', [body.pointer, end])
    call = int(consumer_proof['getterCall'], 16)
    raw_call = index.pe.bytes_at_va(call, 5)
    _require(raw_call[:1] == b'\xe8' and relative_branch_target(raw_call, call, source='snapshotCacheGetter') == body.pointer,
             'cache-getter-actual-caller-target', hex(body.pointer), raw_call.hex())
    raw = index.pe.bytes_at_va(body.pointer, end - body.pointer)
    rows = index._decode(body.pointer, end - body.pointer)
    _require(b''.join(bytes.fromhex(row['bytes']) for row in rows) == raw,
             'cache-getter-byte-coverage', 'complete owned byte partition', len(raw))
    proof = check_getter_program(rows, pointer=body.pointer, end=end, slots=writer_proof['anonymousSlots'])
    _require(consumer_proof['cacheField'] == writer_proof['cacheField'],
             'cache-getter-owner-field', writer_proof['cacheField'], consumer_proof['cacheField'])
    return {**proof, 'symbol': body.symbol, 'claim': 'snapshotPhysicalGetterAndConditionalElementJoin',
            'actualCaller': hex(call), 'getterBodySha256': hashlib.sha256(raw).hexdigest(),
            'cacheField': consumer_proof['cacheField'],
            'sameElementConditions': ['same action cache receiver and same array carrier',
                                     'consumer index equals writer old count',
                                     'writer old count is nonnegative and below nonnegative Int32 array length',
                                     'normal writer/getter paths and no intervening/concurrent mutation'],
            'producerConsumerIndexJoinProved': False,
            'boundary': 'The actual registered closed-Double getter checks unsigned count/array bounds and nonnull carrier, sign-extends its incoming index, loads exactly eight bytes into XMM0 and returns through a complete stack epilogue. Its anonymous array/payload slots match the real compiled writer. Equal incoming index and writer old count with unchanged matching receiver/array imply the same eight-byte address and returned stored bits; that equality and heap/class parity are conditions, not observed joins. Throw/failure paths, managed layout and full producer order remain unproved.'}

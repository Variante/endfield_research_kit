"""Prove the actual compiled append target's selected raw-carrier fast path.

The anonymous slots are reviewed structure, not named generic List fields.
Only .pdata-owned code and the checked fast path are admitted. Managed layout,
runtime class parity, resizing and producer/consumer index joins stay separate.
"""
from __future__ import annotations

import hashlib

from scripts.game_data.damage_snapshot_cache_flow import _address, _require
from scripts.game_data.il2cpp.stack_argument_flow import _edge


def check_raw_store_program(rows, *, pointer, end, slots):
    """Check all entry-to-RET instructions of the normally returning fast path.

    The signed count is used for address generation; both capacity comparisons
    use its unsigned DWORD view. A nonnegative Int32 array length and an
    unchanged valid carrier/array are explicit conditions, not observed values.
    """
    offsets = [slots[key] for key in ('counterDword', 'arrayReference', 'countDword',
                                      'arrayLengthDword', 'arrayPayload')]
    _require(all(type(value) is int and 0 <= value < 128 for value in offsets),
             'append-helper-slots', 'positive disp8 declarations', offsets)
    counter, array, count, length, payload = offsets
    _require(len({counter, array, count}) == 3 and not array + 8 > count
             and not count + 4 > counter, 'append-helper-carrier-slots',
             'distinct nonoverlapping reference/count/counter lanes', offsets)
    expected = [
        b'\x48\x89\x5c\x24\x08', b'\x57', b'\x48\x83\xec\x30',
        b'\xff\x41' + bytes([counter]), b'\x49\x8b\xf8',
        b'\x4c\x8b\x49' + bytes([array]), b'\x48\x8b\xd9',
        b'\x48\x63\x51' + bytes([count]), b'\x0f\x29\x74\x24\x20',
        b'\x0f\x28\xf1', b'\x4d\x85\xc9', 'null-edge',
        b'\x41\x3b\x51' + bytes([length]), 'capacity-edge',
        b'\x8d\x42\x01', b'\x89\x41' + bytes([count]),
        b'\x41\x3b\x51' + bytes([length]), 'bounds-edge',
        b'\xf2\x41\x0f\x11\x4c\xd1' + bytes([payload]),
        b'\x48\x8b\x5c\x24\x40', b'\x0f\x28\x74\x24\x20',
        b'\x48\x83\xc4\x30', b'\x5f', b'\xc3',
    ]
    _require(pointer < end and bool(rows), 'append-helper-owned-extent', 'nonempty owned range', [pointer, end])
    selected = rows[:len(expected)]
    _require(len(selected) == len(expected), 'append-helper-program-length', len(expected), len(selected))
    address = pointer; edges = {}
    for row, encoding in zip(selected, expected):
        raw = bytes.fromhex(row['bytes'])
        _require(_address(row) == address and address + len(raw) <= end,
                 'append-helper-contiguity', hex(address), row['va'])
        if isinstance(encoding, str):
            opcode = b'\x74' if encoding == 'null-edge' else b'\x73'
            edge = _edge(row)
            _require(len(raw) == 2 and raw.startswith(opcode) and edge is not None,
                     'append-helper-guard', opcode.hex(), raw.hex())
            edges[encoding] = edge[0]
        else:
            _require(raw == encoding, 'append-helper-instruction', encoding.hex(), raw.hex())
        address += len(raw)
    for kind, target in edges.items():
        _require(target not in {_address(row) for row in selected}, 'append-helper-excluded-edge',
                 'outside selected fast path', [kind, hex(target)])
        # Slow/failure continuations can be separately owned fragments; they
        # must at least be checked native instruction boundaries here.
        _require(target in {_address(row) for row in rows}, 'append-helper-edge-boundary',
                 'instruction boundary in owned helper', [kind, hex(target)])
    return {'helperEntry': hex(pointer), 'helperOwnedEnd': hex(end),
            'fastReturn': selected[-1]['va'], 'selectedInstructionCount': len(selected),
            'excludedTargets': {key: hex(value) for key, value in edges.items()},
            'selectedWrites': [
                {'destination': 'receiver.counterDword', 'widthBytes': 4, 'operation': 'increment modulo 2^32'},
                {'destination': 'receiver.countDword', 'widthBytes': 4, 'value': 'old signed count + 1 low32'},
                {'destination': 'array payload + signExtend(old count) * 8', 'widthBytes': 8, 'value': 'incoming XMM1 low64'},
            ],
            'indexSource': 'signExtend(receiver old Int32 count)',
            'capacityCondition': 'UInt32(old count) < UInt32(array length), checked twice',
            'liveConditions': ['valid unchanged receiver/frame and array storage',
                               'array length is nonnegative Int32', 'no concurrent carrier/array mutation'],
            'namedListMutationProved': False, 'producerConsumerIndexJoinProved': False}


def check_compiled_append_helper(index, append_proof, spec):
    """Bind the already-proved request call to its real .pdata-owned target."""
    _require(append_proof.get('claim') == 'snapshotSimpleValueToAppendRequest',
             'append-helper-request-proof', 'fresh simple append transfer', append_proof.get('claim'))
    pointer = int(append_proof['compiledAppendTarget'], 16)
    _require(pointer in index.extents, 'append-helper-pdata-entry', 'exact .pdata entry', hex(pointer))
    end = index.extents[pointer]
    _require(type(end) is int and 0 < end - pointer <= 2048,
             'append-helper-pdata-extent', 'bounded exact owned range', [hex(pointer), hex(end)])
    raw = index.pe.bytes_at_va(pointer, end - pointer)
    rows = index._decode(pointer, end - pointer)
    _require(b''.join(bytes.fromhex(row['bytes']) for row in rows) == raw,
             'append-helper-byte-coverage', 'complete owned byte partition', len(raw))
    proof = check_raw_store_program(rows, pointer=pointer, end=end, slots=spec['anonymousSlots'])
    _require(append_proof['receiverRegister'] == 'rcx' and append_proof['valueRegister'] == 'xmm1',
             'append-helper-request-abi', ['rcx', 'xmm1'],
             [append_proof['receiverRegister'], append_proof['valueRegister']])
    return {**proof, 'symbol': 'compiled snapshot append helper', 'claim': 'snapshotCompiledHelperRawStore',
            'requestCall': append_proof['appendCall'], 'cacheField': append_proof['cacheField'],
            'anonymousSlots': spec['anonymousSlots'], 'helperBodySha256': hashlib.sha256(raw).hexdigest(),
            'registeredAddEntries': append_proof['registeredAddEntries'],
            'compiledTargetIsRegisteredAddEntry': append_proof['compiledTargetIsRegisteredAddEntry'],
            'boundary': 'The actual physical target receives the previously proved cache RCX and Double XMM1. On its checked nonnull/capacity fast path it increments an anonymous DWORD, writes old count+1 into another DWORD, and stores the incoming Double bits at array payload + signExtend(old count)*8 before a full restoring RET. Slot names, managed List/array layout, runtime class parity, slow paths, cache order and consumer index correspondence remain unproved or conditional; no registered Add identity is inferred.'}

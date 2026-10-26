"""Check the constructor tail helper's bounded reachable entry graph.

This helper has no .pdata entry. The proof certifies two returning paths and
the complete CAS loop from a real incoming transfer, never whole-function
ownership or the backing extent/meaning of its anonymous static storage.
"""
from __future__ import annotations

import struct

from scripts.game_data.damage_snapshot_cache_flow import _address, _require
from scripts.game_data.il2cpp.stack_argument_flow import _edge


def derive_word(slot, base, program):
    """Exact checked unsigned address arithmetic, with explicit no-wrap gate."""
    _require(type(slot) is int and type(base) is int and 0 <= slot < 1 << 64 and 0 <= base < 1 << 64,
             'slot-helper-address-domain', 'UInt64 slot/base', [slot, base])
    key = (slot >> program['addressShift']) & program['pageMask']
    displacement = (key >> program['wordShift']) * 8
    word = base + displacement
    return {'wordAddress': word, 'wordDisplacement': displacement,
            'bitIndex': key & program['bitMask'],
            'validAddressRanges': slot <= (1 << 64) - 8 and word <= (1 << 64) - 8,
            'fieldAndWordDisjoint': slot + 8 <= word or word + 8 <= slot}


def check_slot_entry(rows, *, pointer, program):
    shift, mask, word_shift, bit_mask = [program[key] for key in (
        'addressShift', 'pageMask', 'wordShift', 'bitMask')]
    _require(all(type(value) is int for value in (shift, mask, word_shift, bit_mask))
             and 0 <= shift < 64 and 0 <= word_shift < 64 and 0 <= mask <= 0xffffffff
             and 0 <= bit_mask < 64, 'slot-helper-arithmetic-declarations', 'bounded unsigned bit arithmetic', program)
    expected = ['flag-compare', b'\x4c\x8b\xc1', 'zero-edge',
        b'\x49\xc1\xe8' + bytes([shift]), 'table-lea',
        b'\x41\x81\xe0' + struct.pack('<I', mask), b'\x41\x8b\xc0',
        b'\x48\xc1\xe8' + bytes([word_shift]), b'\x41\x83\xe0' + bytes([bit_mask]),
        b'\x48\x8d\x14\xc1', b'\x0f\x0d\x0a', b'\x48\x8b\x02', b'\x48\x8b\xc8',
        b'\x4c\x0f\xab\xc1', b'\xf0\x48\x0f\xb1\x0a', 'retry-edge', b'\xc3']
    _require(len(rows) >= len(expected), 'slot-helper-entry-length', len(expected), len(rows))
    at = pointer; targets = {}; static = {}
    for row, encoding in zip(rows, expected):
        raw = bytes.fromhex(row['bytes'])
        _require(_address(row) == at and 0 < len(raw) <= 15, 'slot-helper-contiguity', hex(at), row['va'])
        if encoding == 'flag-compare':
            _require(len(raw) == 7 and raw[:2] == b'\x83\x3d' and raw[-1:] == b'\x00',
                     'slot-helper-flag-encoding', 'CMP RIP DWORD, zero', raw.hex())
            static['flagAddress'] = at + len(raw) + struct.unpack_from('<i', raw, 2)[0]
        elif encoding == 'table-lea':
            _require(len(raw) == 7 and raw[:3] == b'\x48\x8d\x0d',
                     'slot-helper-table-encoding', 'LEA RCX RIP address', raw.hex())
            static['baseAddress'] = at + len(raw) + struct.unpack_from('<i', raw, 3)[0]
        elif isinstance(encoding, str):
            edge = _edge(row); opcode = b'\x74' if encoding == 'zero-edge' else b'\x75'
            _require(len(raw) == 2 and raw[:1] == opcode and edge is not None,
                     'slot-helper-edge', opcode.hex(), raw.hex())
            targets[encoding] = edge[0]
        else:
            _require(raw == encoding, 'slot-helper-instruction', encoding.hex(), raw.hex())
        at += len(raw)
    _require(targets['zero-edge'] == _address(rows[16]), 'slot-helper-zero-return', rows[16]['va'], hex(targets['zero-edge']))
    _require(targets['retry-edge'] == _address(rows[11]), 'slot-helper-cas-retry', rows[11]['va'], hex(targets['retry-edge']))
    max_displacement = (mask >> word_shift) * 8
    return {'entry': hex(pointer), 'boundedEntryByteCount': at - pointer, 'selectedInstructionCount': len(expected),
            'returnNodes': [rows[16]['va']], 'retryLoad': rows[11]['va'],
            'edges': {'zeroGateToReturn': hex(targets['zero-edge']),
                      'nonzeroGateFallthrough': rows[3]['va'],
                      'failedCasToReload': hex(targets['retry-edge']),
                      'successfulCasFallthroughToReturn': rows[16]['va']},
            'staticFlagReadWidthBytes': 4, 'staticAddresses': static,
            'derivedWriteFormula': 'base + ((((UInt64(input slot) >> addressShift) & pageMask) >> wordShift) * 8)',
            'maxDerivedWordDisplacement': max_displacement, 'derivedWriteWidthBytes': 8,
            'writeOperations': ['LOCK CMPXCHG of the derived word, candidate = loaded word with selected bit set'],
            'bitIndexBound': bit_mask, 'explicitLocalFrameOrSpAdjustments': False, 'retReturnAddressPopBytes': 8, 'externalCalls': [],
            'pdataFunctionOwnershipProved': False, 'storageExtentOrGcMeaningProved': False}


def check_constructor_slot_helper(index, constructor_proof, spec):
    _require(constructor_proof.get('claim') == 'snapshotConstructorCachePointerStore',
             'slot-helper-constructor-proof', 'fresh constructor tail proof', constructor_proof.get('claim'))
    pointer = int(constructor_proof['slotAddressHelper'], 16)
    # Read only a bounded entry window. No adjacent RET, named method or .pdata
    # estimate supplies an inferred allocation/function extent.
    raw = index.pe.bytes_at_va(pointer, 96)
    rows = index._decode(pointer, len(raw))
    proof = check_slot_entry(rows, pointer=pointer, program=spec['bitAddressProgram'])
    proof['staticAddresses'] = {key: {'preferredVa': hex(value), 'rva': hex(value - index.pe.image_base)}
                                for key, value in proof['staticAddresses'].items()}
    return {**proof, 'symbol': 'constructor slot-address helper entry', 'claim': 'snapshotConstructorSlotHelperNoninterference',
            'cacheField': constructor_proof['cacheField'], 'constructorCacheStore': constructor_proof['cacheStore'],
            'bitAddressProgram': spec['bitAddressProgram'],
            'fieldPreservationConditions': [
                'live relocated base and actual slot produce valid nonwrapping eight-byte ranges',
                'actual input field-slot range is disjoint from the actual derived word write range',
                'flag and derived-word storage are valid; no table allocation extent is assumed',
                'CAS loop normally returns; no concurrent/intervening field or storage interference'],
            'finalFieldPointerPreservation': 'conditional on the listed exact derived-range and normal-return gates',
            'liveHeapClassParityProved': False,
            'boundary': 'The actual constructor slot-address tail target has a checked bounded entry graph: zero DWORD gate returns directly; otherwise input-slot bits select an anonymous RIP-base word, then a complete BTS/LOCK CMPXCHG retry loop returns. Every reachable edge, RET and write width is checked, with no calls or explicit local frame/SP adjustments; RET still pops the eight-byte return address. The derived word may alias valid stack storage; caller frame/return-slot preservation is not claimed. All writes target only that actual derived word. If its eight-byte range is disjoint from the input field slot, valid storage and noninterference/normal return preserve the prior constructor pointer store. No .pdata ownership, table extent/GC meaning, allocator semantics or live class parity is inferred.'}

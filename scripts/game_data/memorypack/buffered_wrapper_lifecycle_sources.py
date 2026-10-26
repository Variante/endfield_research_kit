"""Conditional buffered wrapper headers, construction and cached getter paths.

These algorithms prove complete selected instruction paths and pointer flows.
They do not observe initialization flags, allocations, provider selection or
runtime execution. Runtime constructors and existing-wrapper preparation are
named call boundaries whose effects remain separate work.
"""
from __future__ import annotations

from typing import Any, Callable

from scripts.game_data.memorypack.reference_conversion_sources import validate_program, _target
from scripts.game_data.memorypack.buffered_reference_wrappers import validate_fast_reference_barrier

EXTRA_OPCODES = {'A804': 'test al, 4', '480F44D9': 'cmove rbx, rcx'}


def _codes(proof: dict) -> list[str]:
    return [row[1] for row in proof['program']]


def _match(rows: list, expected: list, *, fail: Callable) -> None:
    if len(rows) != len(expected):
        fail('lifecycle-profile-size', len(expected), len(rows))
    for n, (row, wanted) in enumerate(zip(rows, expected, strict=True)):
        if wanted is not None and row[1] != wanted:
            fail('lifecycle-transfer', {'position': n, 'bytes': wanted}, row)


def _profile(image: Any, proof: dict, expected: list, *, fail: Callable) -> list:
    validate_program(image, proof, fail=fail, extra_opcodes=EXTRA_OPCODES)
    rows = proof['program']
    _match(rows, expected, fail=fail)
    return rows


def _branch(rows: list, n: int, opcode: bytes, taken: bool, *, fail: Callable) -> None:
    at, h = rows[n]
    raw = bytes.fromhex(h)
    if (raw[:len(opcode)] != opcode or
            rows[n + 1][0] != (_target(at, raw) if taken else at + len(raw))):
        fail('lifecycle-selected-guard', {'position': n, 'opcode': opcode.hex(), 'taken': taken}, rows[n:n + 2])


def _call(rows: list, n: int, target: int, *, tail: bool = False, fail: Callable) -> None:
    at, h = rows[n]
    raw = bytes.fromhex(h)
    if len(raw) != 5 or raw[0] != (0xE9 if tail else 0xE8) or _target(at, raw) != target:
        fail('lifecycle-call-target', {'position': n, 'target': target, 'tail': tail}, rows[n])


def _flag(row: list, *, fail: Callable) -> None:
    raw = bytes.fromhex(row[1])
    if len(raw) != 7 or raw[:2] != b'\x80\x3d' or raw[-1] != 0:
        fail('lifecycle-initialization-flag', 'RIP-relative byte comparison with zero', row)


def _barrier_tail(rows: list, n: int, barrier: dict, *, fail: Callable) -> None:
    _call(rows, n, barrier['program'][0][0], tail=True, fail=fail)
    if rows[n + 1:] != barrier['program']:
        fail('lifecycle-restored-frame-tail', 'same complete disabled-helper suffix', rows[n + 1:])


def validate_shared(image: Any, programs: dict, calls: dict, barrier: dict, *, fail: Callable) -> dict:
    """Type-compatible casts return the original pointer; null cast returns zero."""
    fast = validate_fast_reference_barrier(image, barrier, fail=fail)
    if calls['disabledBarrier'] != fast['entryRva']:
        fail('lifecycle-common-barrier', fast['entryRva'], calls['disabledBarrier'])
    r = _profile(image, programs['instanceStore'], [
        '4883EC28', '4C8BD1', '48895118', '4883C118', '4C8BCA', None,
        '498D4A10', '4D894A10', '4883C428', None,
        *[row[1] for row in barrier['program']]], fail=fail)
    _call(r, 5, fast['entryRva'], fail=fail)
    _barrier_tail(r, 9, barrier, fail=fail)

    r = _profile(image, programs['targetClassReady'], [
        '48895C2410', '4889742418', '57', '4883EC20', '488BF9',
        '0FB6813A010000', '90', 'A804', None,
        '488B5C2438', '488B742440', '4883C420', '5F', 'C3'], fail=fail)
    _branch(r, 8, b'\x0f\x85', True, fail=fail)
    r = _profile(image, programs['classCompatibleReady'], [
        '48895C2410', '48896C2418', '4889742420', '57', '4883EC20',
        '488BEA', '488BF9', '0FB6813A010000', '90', 'A804', None,
        '488BCD', None, '0FB68532010000', '388732010000', None,
        '0FB6C8', '488B87C8000000', '48396CC8F8', None, 'B001', None,
        '488B5C2438', '488B6C2440', '488B742448', '4883C420', '5F', 'C3'], fail=fail)
    _branch(r, 10, b'\x0f\x85', True, fail=fail)
    _call(r, 12, calls['targetClassReady'], fail=fail)
    _branch(r, 15, b'\x72', False, fail=fail)
    _branch(r, 19, b'\x75', False, fail=fail)

    r = _profile(image, programs['constructorCastCompatible'], [
        '48895C2408', '57', '4883EC20', '488BFA', '488BD9', '4885C9', None,
        '488B09', None, '84C0', None, '488BC3', '488B5C2430', '4883C420', '5F', 'C3'], fail=fail)
    _branch(r, 6, b'\x74', False, fail=fail)
    _call(r, 8, calls['classCompatible'], fail=fail)
    _branch(r, 10, b'\x74', False, fail=fail)
    r = _profile(image, programs['getterCastCompatible'], [
        '4053', '4883EC20', '488BD9', '4885C9', None, '488B09', None,
        '33C9', '84C0', '480F44D9', '488BC3', '4883C420', '5B', 'C3'], fail=fail)
    _branch(r, 4, b'\x74', False, fail=fail)
    _call(r, 6, calls['classCompatible'], fail=fail)
    r = _profile(image, programs['getterCastNull'], [
        '4053', '4883EC20', '488BD9', '4885C9', None, '33C0', '4883C420', '5B', 'C3'], fail=fail)
    _branch(r, 4, b'\x74', True, fail=fail)
    for key, call in (('instanceStore', 'instanceStore'), ('constructorCastCompatible', 'constructorCast'),
                      ('getterCastCompatible', 'getterCast'), ('getterCastNull', 'getterCast'),
                      ('classCompatibleReady', 'classCompatible'), ('targetClassReady', 'targetClassReady')):
        if programs[key]['program'][0][0] != calls[call]:
            fail('lifecycle-shared-entry', calls[call], programs[key]['program'][0][0])
    return {'baseAndCacheReceiveSameReference': True, 'physicalNamedConstructorIdentityProved': False,
            'compatibleCastsReturnOriginalReference': True, 'nullGetterCastReturnsNull': True,
            'classFlag4AndHierarchyMatchesRequired': True, 'selectedClassHeapOrGlobalWrites': 0,
            'classInitializationSlowPathsProved': False, 'disabledBarrierRequired': True}


def validate_constructor(image: Any, record: dict, calls: dict, barrier: dict, *, kind: str,
                         fail: Callable) -> dict:
    """Forward typed allocation to the runtime ctor and preserve its return alias."""
    proof = record['programs']['constructor']
    prefix = ['48895C2408', '57', '4883EC20', None, '488BF9', None]
    if kind == 'moveTo':
        expected = prefix + [None, '83B9E000000000', None, None, None, '488BD8', '4885C0', None,
            '33D2', '488BC8', None, '4533C0', '488BD3', '488BCF', None, '488B5F10', None,
            '488BCB', None, '48894718', '488BCB', None, None, '488D4F18',
            '488B5C2430', '4883C420', '5F', None]
        positions = {'allocation': 10, 'runtime': 16, 'tail': 33}
    elif kind == 'subSpeed':
        expected = prefix + [None, None, '488BD8', '4885C0', None, '33D2', '488BC8', None,
            '488D4F10', '48895F10', '488B5C2430', '4883C420', '5F', None]
        positions = {'allocation': 7, 'runtime': 13, 'tail': 19}
    else:
        fail('lifecycle-constructor-kind', ['moveTo', 'subSpeed'], kind)
    rows = _profile(image, proof, expected + [r[1] for r in barrier['program']], fail=fail)
    _flag(rows[3], fail=fail)
    _branch(rows, 5, b'\x74', False, fail=fail)
    _call(rows, positions['allocation'], calls['allocation'], fail=fail)
    _call(rows, positions['runtime'], record['runtimeConstructorMethod'][3], fail=fail)
    _barrier_tail(rows, positions['tail'], barrier, fail=fail)
    if kind == 'moveTo':
        _branch(rows, 8, b'\x0f\x84', False, fail=fail)
        _branch(rows, 13, b'\x74', False, fail=fail)
        _call(rows, 20, calls['instanceStore'], fail=fail)
        for n in (24, 28):
            _call(rows, n, calls['constructorCast'], fail=fail)
    else:
        _branch(rows, 10, b'\x74', False, fail=fail)
    return {'typedNonNullAllocationRequired': True, 'sameRuntimeInstanceStored': True,
            'completeConditionalReturnProved': True, 'runtimeConstructorEffectsProved': False}


def validate_getter(image: Any, record: dict, calls: dict, *, fail: Callable) -> dict:
    """Warm equality, cache-null and cache-mismatch all reach a complete return."""
    p = record['programs']
    warm = ['4053', '4883EC20', None, '488BD9', None, '48837B1800', None,
            '488B4310', '48394318', None, '488B4318', '4883C420', '5B', 'C3']
    cold = [None, '48897C2430', '488B7B10', '488BCF', None, '48894318',
            '488BCF', None, None, '488D4B18', None, '488B7C2430', None]
    warm_rows = _profile(image, p['getterWarm'], warm, fail=fail)
    _flag(warm_rows[2], fail=fail)
    for n, opcode in ((4, b'\x74'), (6, b'\x0f\x84'), (9, b'\x0f\x85')):
        _branch(warm_rows, n, opcode, False, fail=fail)
    cold_start = None
    for name, prefix_length in (('getterCacheNull', 7), ('getterCacheMismatch', 10)):
        rows = _profile(image, p[name], warm[:prefix_length] + cold + warm[10:], fail=fail)
        _flag(rows[2], fail=fail)
        _branch(rows, 4, b'\x74', False, fail=fail)
        _branch(rows, 6, b'\x0f\x84', name == 'getterCacheNull', fail=fail)
        if name == 'getterCacheMismatch':
            _branch(rows, 9, b'\x0f\x85', True, fail=fail)
        at = rows[prefix_length][0]
        if cold_start is not None and cold_start != at:
            fail('lifecycle-getter-common-cold-entry', cold_start, at)
        cold_start = at
        for n in (4, 8):
            _call(rows, prefix_length + n, calls['getterCast'], fail=fail)
        _call(rows, prefix_length + 10, calls['disabledBarrier'], fail=fail)
    return {'warmReturnsEqualCacheAndBase': True, 'cacheNullAndMismatchRefreshSameBaseReference': True,
            'coldPreservesRdiThroughReturn': True, 'completeConditionalReturnsProved': 3,
            'underlyingBaseMayBeNull': True, 'runtimeCacheStateObserved': False}


def _epilogue(allocation: int) -> list[str]:
    return [f'488B5C24{allocation + 16:02X}', f'488B6C24{allocation + 24:02X}',
            f'488B7424{allocation + 32:02X}', f'4883C4{allocation:02X}', '5F', 'C3']


def _header(rows: list, record: dict, calls: dict, offsets: dict, *, kind: str,
            prepared: bool, null: bool, fail: Callable) -> int:
    allocation = record['frameAllocation']
    if type(allocation) is not int or allocation not in (32, 48):
        fail('lifecycle-source-frame', 'reviewed 32 or 48-byte local allocation', allocation)
    prefix = ['48895C2408', '48896C2410', '4889742418', '57', f'4883EC{allocation:02X}',
              None, '488BFA', '488BD9', None]
    if kind == 'moveTo':
        prefix += ['488B0F', '4885C9', None]
        if prepared:
            prefix += ['33D2', None, '90', None]
    elif kind != 'subSpeed' or prepared:
        fail('lifecycle-header-kind', 'moveTo optional prepare or subSpeed', [kind, prepared])
    start = len(prefix)
    o = {k: f'{v:02X}' for k, v in offsets.items()}
    middle = [f'837B{o["bufferLength"]}01', None, f'488B43{o["currentPtr"]}', '0FB628',
        f'8B73{o["bufferLength"]}', '83EE01', None, f'48FF43{o["currentPtr"]}',
        f'FF43{o["advancedCount"]}', f'FF43{o["consumed"]}', f'8973{o["bufferLength"]}', '4080FDFF', None]
    _match(rows[:start + len(middle)], prefix + middle, fail=fail)
    _flag(rows[5], fail=fail)
    _branch(rows, 8, b'\x0f\x84', False, fail=fail)
    if kind == 'moveTo':
        _branch(rows, 11, b'\x0f\x85', prepared, fail=fail)
        if prepared:
            _call(rows, 13, calls['prepareExistingWrapper'], fail=fail)
    _branch(rows, start + 1, b'\x0f\x8c', False, fail=fail)
    _branch(rows, start + 6, b'\x0f\x88', False, fail=fail)
    _branch(rows, start + 12, b'\x0f\x84', null, fail=fail)
    return start + len(middle)


def validate_sources(image: Any, record: dict, calls: dict, offsets: dict, expected_field_prefix: list,
                     *, kind: str, fail: Callable) -> dict:
    """One buffered header plus complete caller epilogues; field effects separate."""
    if (set(offsets) != {'currentPtr', 'bufferLength', 'advancedCount', 'consumed'} or
            any(type(v) is not int or not 0 <= v < 128 for v in offsets.values()) or len(set(offsets.values())) != 4):
        fail('lifecycle-reader-offsets', 'four distinct bounded physical offsets', offsets)
    p = record['programs']
    epilogue = _epilogue(record['frameAllocation'])
    _match(record['epilogue'], epilogue, fail=fail)
    for name in ('null', 'nullPrepared') if kind == 'moveTo' else ('null',):
        proof = p[name]
        validate_program(image, proof, fail=fail, extra_opcodes=EXTRA_OPCODES)
        rows = proof['program']
        n = _header(rows, record, calls, offsets, kind=kind, prepared=name == 'nullPrepared', null=True, fail=fail)
        _match(rows[n:], ['488BCF', '48C70700000000', None, None, *epilogue], fail=fail)
        _call(rows, n + 2, calls['disabledBarrier'], fail=fail)
        if rows[-6:] != record['epilogue']:
            fail('lifecycle-null-normal-epilogue', record['epilogue'], rows[-6:])

    canonical = None
    for name in ('normalNew', 'normalReused'):
        proof = p[name]
        validate_program(image, proof, fail=fail, extra_opcodes=EXTRA_OPCODES)
        rows = proof['program']
        n = _header(rows, record, calls, offsets, kind=kind,
                    prepared=kind == 'moveTo' and name == 'normalReused', null=False, fail=fail)
        count = f'4080FD{record["memberCount"]:02X}'
        _match(rows[n:n + 2], ['48833F00', None], fail=fail)
        new = name == 'normalNew'
        _branch(rows, n + 1, b'\x75' if kind == 'moveTo' else b'\x0f\x84',
                not new if kind == 'moveTo' else new, fail=fail)
        count_n = n + 2
        if new:
            alloc = [None, None, '488BF0', '4885C0', None, '33D2', '488BC8', None,
                     '488BCF', '488937', None]
            if kind == 'subSpeed':
                alloc += ['90', None]
            _match(rows[count_n:count_n + len(alloc)], alloc, fail=fail)
            _call(rows, count_n + 1, calls['allocation'], fail=fail)
            _branch(rows, count_n + 4, b'\x0f\x84', False, fail=fail)
            _call(rows, count_n + 7, record['constructorMethod'][3], fail=fail)
            _call(rows, count_n + 10, calls['disabledBarrier'], fail=fail)
            count_n += len(alloc)
        _match(rows[count_n:count_n + 2], [count, None], fail=fail)
        _branch(rows, count_n + 1, b'\x0f\x85', False, fail=fail)
        suffix = rows[count_n:]
        if canonical is not None and suffix != canonical:
            fail('lifecycle-new-reused-same-fields', canonical[:2], suffix[:2])
        canonical = suffix
        if rows[-6:] != record['epilogue']:
            fail('lifecycle-complete-source-epilogue', record['epilogue'], rows[-6:])
    reference = p['normalNew']['program'] if kind == 'moveTo' else p['normalReused']['program']
    if reference[:-6] != expected_field_prefix:
        fail('lifecycle-current-field-program-join', 'same reviewed field-owner prefix',
             {'expectedRows': len(expected_field_prefix), 'actualRows': len(reference[:-6])})
    return {'memberCount': record['memberCount'], 'bufferedHeaderBytes': 1, 'nullClearsWrapperReference': True,
            'pointerUpdateBits': 64, 'counterUpdateBits': 32, 'counterArithmetic': 'native modulo width',
            'completeNullReturns': 2 if kind == 'moveTo' else 1, 'completeNormalReturns': 2,
            'currentFieldProgramJoined': True, 'fieldEffectsRevalidated': False,
            'existingWrapperPreparationEffectsProved': False, 'refillAndFailureEffectsProved': False}

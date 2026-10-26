"""Validate conditional MoveTo/SubSpeed wrapper lifecycles on selected inputs.

Field effects are owned by the existing parent, SubSpeed and setter validators.
This owner closes the selected header, wrapper construction and cached getter
paths, and records the remaining runtime/allocation/provider boundaries.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import (
    open_native_image, read_reviewed_contract, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH,
)
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError, _fingerprint, _package_import_closure
from scripts.game_data.memorypack import buffered_wrapper_lifecycle_sources as lifecycle

LABEL = 'buffMoveToLifecycle'
SCHEMA = 'endfield.buff-move-to-lifecycle-native-contract.v1'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_move_to_lifecycle_native.json'
DEPENDENCY_SCHEMAS = {
    'parent': 'endfield.buff-move-to-source-native-contract.v2',
    'subSpeed': 'endfield.buff-move-to-subspeed-source-native-contract.v1',
    'fieldTransfers': 'endfield.buff-move-to-setter-transfers-native-contract.v1',
    'barrier': 'endfield.buff-timeline-source-wrappers-native-contract.v1',
}


def _fail(check: str, expected: Any, actual: Any, **scope: Any) -> None:
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
                            expected=str(expected)[:1800], actual=str(actual)[:2200])
    error.diagnostic.update(validator=LABEL, check=check, scope=scope)
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _contract() -> dict:
    c, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status='exact-current-build', label=LABEL)
    names = c.get('dependencies', {})
    if (set(names) != set(DEPENDENCY_SCHEMAS) or set(c.get('records', {})) != {'moveTo', 'subSpeed'} or
            any(not isinstance(name, str) or Path(name).name != name or '/' in name or '\\' in name
                or not name.endswith('_native.json') for name in names.values())):
        _fail('contract-scope', 'named parent/SubSpeed/field-transfer/barrier dependencies and two records', names)
    return c


def _validate_layout(image: Any, c: dict, dependencies: dict) -> dict:
    expected_getter = dependencies['fieldTransfers']['profile']['getterMethod']
    if c['records']['moveTo']['getterMethod'] != expected_getter:
        _fail('current-field-getter-join', expected_getter, c['records']['moveTo']['getterMethod'])
    selected = NativeReferenceContext(image)
    if not selected.is_value_type('MemoryPack.MemoryPackReader'):
        _fail('reader-value-type', 'MemoryPackReader is a value type', False)
    offsets = {}
    for row in c['readerFields']:
        name = row['name']
        actual = selected.field('MemoryPack.MemoryPackReader::' + name)
        expected_type = 'byte*' if name == 'currentPtr' else 'int'
        if (actual[1:] != (row['typeName'], row['runtimeOffset']) or row['typeName'] != expected_type or
                row['valueOffset'] != row['runtimeOffset'] - 16 or name in offsets):
            _fail('reader-field-layout', row, actual)
        offsets[name] = row['valueOffset']
    expected_fields = []
    for row in c['wrapperFields']:
        actual = selected.field(row['qualified'])
        if list(actual) != row['field']:
            _fail('wrapper-field-layout', row, actual)
        expected_fields.append(actual)
    if len(expected_fields) != 3:
        _fail('wrapper-field-coverage', 'base, MoveTo cache and SubSpeed instance fields', expected_fields)
    parent = c['records']['moveTo']
    child = c['records']['subSpeed']
    wrapper, runtime = [image.type_name(parent[k]) for k in ('wrapperTypeDefinition', 'runtimeTypeDefinition')]
    base_wrapper = selected.parent(wrapper)
    cache = selected.field(wrapper + '::__realInstance')
    base = selected.field(base_wrapper + '::___instance')
    sub_wrapper, sub_runtime = [image.type_name(child[k]) for k in ('wrapperTypeDefinition', 'runtimeTypeDefinition')]
    sub = selected.field(sub_wrapper + '::__instance')
    if (cache != (wrapper, runtime, 24) or base[2] != 16 or selected.parent(runtime) != base[1] or
            sub != (sub_wrapper, sub_runtime, 16) or set(expected_fields) != {cache, base, sub}):
        _fail('owned-wrapper-slots', 'selected base/cache/direct instance fields with exact declared types', [cache, base, sub])
    for key, dependency in (('moveTo', 'parent'), ('subSpeed', 'subSpeed')):
        record, source = c['records'][key], dependencies[dependency]['records'][key]
        for name in ('readerMethod', 'wrapperTypeDefinition', 'runtimeTypeDefinition'):
            if record[name] != source[name]:
                _fail('source-record-identity', source[name], record[name], record=key, field=name)
        if record['memberCount'] != len(source['members']):
            _fail('source-member-count', len(source['members']), record['memberCount'], record=key)
        for name in ('readerMethod', 'constructorMethod', 'runtimeConstructorMethod', 'getterMethod'):
            method = record[name]
            if method is not None:
                image.validate_method_row(method, label=LABEL)
                if name in ('constructorMethod', 'runtimeConstructorMethod') and (
                        method[2] != '.ctor' or method[1] != image.type_name(
                            record['wrapperTypeDefinition' if name == 'constructorMethod' else 'runtimeTypeDefinition'])):
                    _fail('constructor-owner', 'same selected wrapper/runtime type', method)
                if name == 'getterMethod' and (
                        method[2] != 'get___instance' or method[1] != image.type_name(record['wrapperTypeDefinition'])):
                    _fail('getter-owner', 'same selected wrapper get___instance', method)
        if record['programs']['constructor']['program'][0][0] != record['constructorMethod'][3]:
            _fail('constructor-entry', record['constructorMethod'], record['programs']['constructor']['program'][0])
        for name, proof in record['programs'].items():
            expected_entry = record['getterMethod'][3] if name.startswith('getter') else (
                record['constructorMethod'][3] if name == 'constructor' else record['readerMethod'][3])
            if proof['program'][0][0] != expected_entry:
                _fail('record-program-entry', expected_entry, proof['program'][0], record=key, program=name)
    return offsets


def _validate_typed_arguments(image: Any, c: dict) -> dict:
    usages = {row['instructionRva']: row for row in c['typedUsages']}
    if len(usages) != len(c['typedUsages']):
        _fail('typed-usage-uniqueness', 'distinct instruction positions', len(usages))
    used = set()
    def argument(row: list, type_name: str, opcode: str) -> None:
        usage = usages.get(row[0])
        if (usage is None or usage['instructionHex'] != row[1] or usage['typeName'] != type_name or
                usage['tag'] not in (1, 2) or not row[1].startswith(opcode)):
            _fail('typed-call-argument', {'instruction': row, 'type': type_name, 'opcode': opcode}, usage)
        validate_typed_usage_context(image, usage, label=LABEL)
        used.add(row[0])
    for key, source_position, constructor_position in (('moveTo', 27, 9), ('subSpeed', 24, 6)):
        r = c['records'][key]
        wrapper, runtime = [image.type_name(r[k]) for k in ('wrapperTypeDefinition', 'runtimeTypeDefinition')]
        argument(r['programs']['normalNew']['program'][source_position], wrapper, '488B0D')
        argument(r['programs']['constructor']['program'][constructor_position], runtime, '488B0D')
        if key == 'moveTo':
            for n in (22, 27):
                argument(r['programs']['constructor']['program'][n], runtime, '488B15')
            for name, prefix in (('getterCacheNull', 7), ('getterCacheMismatch', 10)):
                for n in (prefix, prefix + 7):
                    argument(r['programs'][name]['program'][n], runtime, '488B15')
    if used != set(usages):
        _fail('typed-argument-coverage', sorted(usages), sorted(used))
    return {'typedAllocationAndCastUsages': len(used), 'liveInitializedUsageCellsObserved': False}


def _validate_image(image: Any, c: dict, dependencies: dict) -> dict:
    offsets = _validate_layout(image, c, dependencies)
    typed = _validate_typed_arguments(image, c)
    barrier = dependencies['barrier']['barrierProgram']
    shared = lifecycle.validate_shared(image, c['sharedPrograms'], c['calls'], barrier, fail=_fail)
    results = {}
    for kind in ('moveTo', 'subSpeed'):
        r = c['records'][kind]
        expected = (dependencies['fieldTransfers']['profile']['parentProgram'] if kind == 'moveTo' else
                    dependencies['subSpeed']['records']['subSpeed']['directDataSource']['parentProgram'])
        source = lifecycle.validate_sources(image, r, c['calls'], offsets, expected, kind=kind, fail=_fail)
        constructor = lifecycle.validate_constructor(image, r, c['calls'], barrier, kind=kind, fail=_fail)
        getter = lifecycle.validate_getter(image, r, c['calls'], fail=_fail) if kind == 'moveTo' else None
        results[kind] = {'source': source, 'constructor': constructor, 'getter': getter}
    return {'records': results, 'shared': shared, 'typedArguments': typed,
            'finalAccumulatedInstanceStateProved': False, 'runtimeConstructorEffectsProved': False,
            'enabledBarrierEffectsProved': False, 'providerSelectionProved': False}


def validate_current_native_contract(*, gameassembly: Path | None = None, metadata: Path | None = None) -> dict:
    c = _contract()
    pins = c['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                       gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return {'status': gate.status, 'detail': gate.detail, 'nativeInputs': pins}
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    def unity_matches() -> bool:
        return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == pins['UnityPlayer.dll']
    if not unity_matches():
        return {'status': 'mismatched' if unity.is_file() else 'missing', 'detail': 'UnityPlayer.dll missing or mismatched', 'nativeInputs': pins}
    dependencies = {key: read_reviewed_contract(CONTRACTS_DIR / name, schema=DEPENDENCY_SCHEMAS[key],
                    status='exact-current-build', label=LABEL)[0] for key, name in c['dependencies'].items()}
    if any(row.get('nativeInputs') != pins for row in dependencies.values()):
        _fail('dependency-build', pins, {key: row.get('nativeInputs') for key, row in dependencies.items()})
    source_paths = {CONTRACT_PATH, *(CONTRACTS_DIR / name for name in c['dependencies'].values()),
                    *_package_import_closure(Path(__file__)), NATIVE_MAPPER_PATH, METADATA_HELPER_PATH,
                    Path(gate.gameassembly), Path(gate.metadata), unity}
    inputs = [_fingerprint(path) for path in sorted(source_paths)]
    try:
        summary = _validate_image(open_native_image(gate.gameassembly, gate.metadata), c, dependencies)
    except ValueError as error:
        if isinstance(error, CensusGateError):
            raise
        _fail('native-lifecycle-composition', 'bounded selected programs and typed fields', str(error))
    for row in inputs:
        now = _fingerprint(Path(row['path']))
        if now != row:
            _fail('source-drift', row, now)
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated' or not unity_matches():
        return {'status': after.status if after.status != 'validated' else 'mismatched',
                'detail': 'selected native inputs changed during validation', 'nativeInputs': pins}
    return {'status': 'validated', 'nativeInputs': pins, 'summary': summary,
            'proofSources': inputs, 'evidenceBoundary': c['evidenceBoundary'],
            'wholeActionAdmitted': False, 'wholeRootAdmitted': False, 'runtimeExecutionKnown': False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    report = args.report.resolve()
    if not report.is_relative_to(Path(__file__).resolve().parents[3] / 'reports'):
        parser.error('--report must be inside the repository reports directory')
    result = validate_current_native_contract(gameassembly=args.gameassembly, metadata=args.metadata)
    if result['status'] != 'validated':
        print(json.dumps({'status': result['status'], 'detail': result.get('detail'), 'reportPreserved': report.as_posix()}), flush=True)
        raise SystemExit(1)
    result['schema'] = 'endfield.buff-move-to-lifecycle-validation.v1'
    result['checkedAtUtc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'report': report.as_posix()}), flush=True)


if __name__ == '__main__':
    main()

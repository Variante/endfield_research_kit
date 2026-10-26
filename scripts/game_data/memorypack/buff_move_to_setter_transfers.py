"""Complete conditional MoveTo setter transfers and shared reference returns.

This validator owns static native composition only. It does not admit an
action grammar, select a live formatter, or publish a WebUI/root result.
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
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError, _fingerprint, _package_import_closure
from scripts.game_data.memorypack import buff_move_to_source as parent
from scripts.game_data.memorypack import buff_move_to_subspeed_source as child
from scripts.game_data.memorypack import selected_wrapper_setter_sources as transfers
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack.buffered_reference_wrappers import validate_fast_reference_barrier
from scripts.game_data.memorypack.read_value_reference_sources import validate_read_value_context, validate_read_value_transfer

LABEL = 'buffMoveToSetterTransfers'
SCHEMA = 'endfield.buff-move-to-setter-transfers-native-contract.v1'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_move_to_setter_transfers_native.json'


def _fail(check: str, expected: Any, actual: Any, **scope: Any) -> None:
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
                            expected=str(expected)[:1800], actual=str(actual)[:2200])
    error.diagnostic.update(validator=LABEL, check=check, scope=scope)
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _contract() -> dict:
    c, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status='exact-current-build', label=LABEL)
    names = c.get('dependencies', {})
    if (set(names) != {'parent', 'subSpeed', 'sharedReturn', 'sharedInstance', 'barrier'}
            or any(not isinstance(name, str) or Path(name).name != name or '/' in name or '\\' in name
                   or not name.endswith('_native.json') for name in names.values())
            or c.get('parentRecord') != 'moveTo' or c.get('profile', {}).get('mode') != transfers.MODE):
        _fail('contract-scope', 'named parent, shared-return and disabled-barrier dependencies with a selected setter profile', names)
    return c


def _field_coverage(record: dict, profile: dict) -> dict:
    """Compose only the direct profiles actually checked by the parent owner."""
    covered = set(profile['memberIndices'])
    inherited = []
    vectors = []
    common = record.get('inheritedDirectActionSource', {}).get('mode')
    for index, member in enumerate(record['members']):
        if member['assignment']['kind'] != 'direct-store':
            continue
        if index < record['inheritedMemberCount'] and common == 'reader-rbx-wrapper-ref-rdi-four-common-direct-stores':
            inherited.append(index)
            covered.add(index)
        elif member['kind'] == 'raw12' and member.get('unmanagedOutputSource', {}).get('mode') == 'unmanaged-output12':
            vectors.append(index)
            covered.add(index)
    expected = set(range(len(record['members'])))
    if covered != expected:
        _fail('field-transfer-coverage', sorted(expected), {'covered': sorted(covered), 'missing': sorted(expected - covered)})
    return {'fields': len(covered), 'inheritedDirectTransfers': len(inherited), 'unmanagedVectorTransfers': len(vectors)}


def _validate_image(image: Any, c: dict, dependencies: dict, *, parent_result: dict, child_result: dict) -> dict:
    pc, cc = dependencies['parent'], dependencies['subSpeed']
    record = pc['records'][c['parentRecord']]
    source = json.loads((CONTRACTS_DIR / record['sourceContract']).read_bytes())
    for name in pc['sourceSupplements']:
        for window in json.loads((CONTRACTS_DIR / name).read_bytes())['codeWindows']:
            if window not in source['codeWindows']:
                source['codeWindows'].append(window)
    for window in c['supplementalWindows']:
        if window not in source['codeWindows']:
            source['codeWindows'].append(window)
    setter_result = transfers.validate(image, source, record, c['profile'], fail=_fail)
    coverage = _field_coverage(record, c['profile'])
    common = dependencies['sharedReturn']
    barrier = dependencies['barrier']
    instance = dependencies['sharedInstance']
    provider = next(row for row in instance['methodContexts'] if row['typeName'] == 'MemoryPack.MemoryPackFormatterProvider')
    generic = GenericEntries(image)
    declaration = validate_read_value_context(image, common['readValueContext'], provider, generic, fail=_fail)
    returned = validate_read_value_transfer(image, common['programs']['readValue'], common['calls'], fail=_fail)
    fast = validate_fast_reference_barrier(image, barrier['barrierProgram'], fail=_fail)
    target = common['calledEntryRva']
    if target != common['programs']['readValue']['program'][0][0]:
        _fail('shared-return-entry', 'same actual physical outer program', target)
    contexts = {row['instructionRva']: row for row in source['nestedContexts']}
    joined = []
    for key, selected in (('moveTo', record), ('subSpeed', cc['records']['subSpeed'])):
        for member in selected['members']:
            if member['sourceCall']['targetRva'] != target:
                continue
            context = contexts.get(member.get('sourceContextInstructionRva'))
            if context is None or context['methodSpec'][0] != common['declaration'][0]:
                _fail('shared-return-declaration', common['declaration'], member, record=key)
            named.check_call(image, member['sourceCall'], label=LABEL, fail=_fail)
            named.check_typed_context(image, context, member['declaredType'], label=LABEL, fail=_fail)
            joined.append({'record': key, 'fieldName': member['fieldName'], 'declaredType': member['declaredType']})
    tail_returns = []
    for transfer in c['profile']['transfers']:
        if transfer['mode'] == 'reference-return':
            if transfer['postStoreTailTargetRva'] != fast['entryRva']:
                _fail('setter-post-store-target', fast['entryRva'], transfer['postStoreTailTargetRva'])
            tail_returns.append(transfer['fieldName'])
    post_returns = []
    for member in cc['records']['subSpeed']['members']:
        call = member.get('directDataStore', {}).get('postStoreCall')
        if call is not None:
            if call['targetRva'] != fast['entryRva']:
                _fail('subspeed-post-store-target', fast['entryRva'], call, field=member['fieldName'])
            named.check_call(image, call, label=LABEL, fail=_fail)
            post_returns.append(member['fieldName'])
    return {'setterTransfers': setter_result, 'parentSourceValidation': parent_result,
            'subSpeedSourceValidation': child_result, 'declaredReadValueContext': declaration,
            'physicalOuterReturn': returned, 'typedSourceCallsJoined': joined,
            'disabledPostStoreHelper': fast, 'referenceSetterTailReturns': tail_returns,
            'subSpeedPostStoreReturns': post_returns,
            'fieldTransferCoverage': coverage, 'selectedCurrentFieldTransferPaths': coverage['fields'],
            'physicalNamedDefinitionProved': False, 'liveTypedFormatterSelectionProved': False,
            'enabledBarrierEffectsProved': False}


def validate_current_native_contract(*, gameassembly: Path | None = None, metadata: Path | None = None) -> dict:
    c = _contract()
    pins = c['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                       gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return {'status': gate.status, 'detail': gate.detail, 'nativeInputs': pins}
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'

    def unity_matches():
        return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == pins['UnityPlayer.dll']

    if not unity_matches():
        return {'status': 'mismatched' if unity.is_file() else 'missing', 'detail': 'UnityPlayer.dll missing or mismatched', 'nativeInputs': pins}
    schemas = {'parent': 'endfield.buff-move-to-source-native-contract.v2',
               'subSpeed': 'endfield.buff-move-to-subspeed-source-native-contract.v1',
               'sharedReturn': 'endfield.buff-timeline-read-value-native-contract.v3',
               'sharedInstance': 'endfield.buff-timeline-instance-native-contract.v1',
               'barrier': 'endfield.buff-timeline-source-wrappers-native-contract.v1'}
    dependencies = {key: read_reviewed_contract(CONTRACTS_DIR / name, schema=schemas[key],
                    status='exact-current-build', label=LABEL)[0] for key, name in c['dependencies'].items()}
    if any(row.get('status') != 'exact-current-build' or row.get('nativeInputs') != pins for row in dependencies.values()):
        _fail('dependency-build', pins, {key: row.get('nativeInputs') for key, row in dependencies.items()})
    if (parent.CONTRACT_PATH.name != c['dependencies']['parent']
            or child.CONTRACT_PATH.name != c['dependencies']['subSpeed']):
        _fail('source-owner-dependencies', 'maintained parent and SubSpeed owners', c['dependencies'])
    source_paths = [CONTRACT_PATH, *(CONTRACTS_DIR / name for name in c['dependencies'].values()),
                    CONTRACTS_DIR / dependencies['parent']['records']['moveTo']['sourceContract'],
                    *(CONTRACTS_DIR / name for name in dependencies['parent']['sourceSupplements']),
                    *_package_import_closure(Path(__file__)), NATIVE_MAPPER_PATH, METADATA_HELPER_PATH,
                    Path(gate.gameassembly), Path(gate.metadata), unity]
    inputs = [_fingerprint(path) for path in sorted(set(source_paths))]
    parent_result = parent.validate_current_native_contract(gameassembly=gate.gameassembly, metadata=gate.metadata)
    child_result = child.validate_current_native_contract(gameassembly=gate.gameassembly, metadata=gate.metadata)
    for key, result in (('parent', parent_result), ('subSpeed', child_result)):
        if result.get('status') != 'validated' or result.get('nativeInputs') != pins:
            _fail('source-native-gate', 'validated selected parent/child inputs', result, owner=key)
    try:
        summary = _validate_image(open_native_image(gate.gameassembly, gate.metadata), c, dependencies,
                                  parent_result=parent_result, child_result=child_result)
    except ValueError as error:
        if isinstance(error, CensusGateError):
            raise
        _fail('native-transfer-composition', 'bounded actual programs and named fields', str(error))
    for row in inputs:
        if _fingerprint(Path(row['path'])) != row:
            _fail('source-drift', row, _fingerprint(Path(row['path'])))
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated' or not unity_matches():
        return {'status': after.status if after.status != 'validated' else 'mismatched',
                'detail': 'selected native inputs changed during validation', 'nativeInputs': pins}
    return {'status': 'validated', 'nativeInputs': pins, 'summary': summary,
            'provenance': {'proofSources': inputs}, 'childSchemaAdmitted': False,
            'wholeActionAdmitted': False, 'wholeRootAdmitted': False, 'runtimeExecutionKnown': False,
            'evidenceBoundary': c['evidenceBoundary']}


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
        print(json.dumps({'status': result['status'], 'detail': result.get('detail'),
                          'reportPreserved': report.as_posix()}, ensure_ascii=True), flush=True)
        raise SystemExit(1)
    result['proofSources'] = result.get('provenance', {}).get('proofSources', [])
    result['schema'] = 'endfield.buff-move-to-setter-transfers-validation.v1'
    result['checkedAtUtc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'report': report.as_posix()}, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()

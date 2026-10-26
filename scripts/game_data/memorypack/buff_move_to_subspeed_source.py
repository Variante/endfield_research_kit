"""Maintain SubSpeed source names and conditional owned operand transfers.

No decoder or action registration is published here. Missing generic body
identity, child grammar admission and actual movement remain separate gaps.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import (
    METADATA_HELPER_PATH, NATIVE_MAPPER_PATH, open_native_image, read_reviewed_contract)
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError, _fingerprint, _package_import_closure
from scripts.game_data.memorypack import direct_data_sources as transfers
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import utf8_source_helper as strings

LABEL = 'buffMoveToSubSpeedSource'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_move_to_subspeed_source_native.json'
RECORD = 'subSpeed'


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(CONTRACT_PATH,
        schema='endfield.buff-move-to-subspeed-source-native-contract.v1',
        status='exact-current-build', label=LABEL)
    records = value.get('records', {})
    if set(records) != {RECORD} or 'actionDispatch' in value:
        raise ValueError(f'{LABEL}.contract:child-source-scope')
    record = records[RECORD]
    names = [record.get('sourceContract'), *value.get('sourceSupplements', ())]
    if (not isinstance(value.get('sourceSupplements'), list) or len(names) != len(set(names))
            or any(not isinstance(name, str) or Path(name).name != name
                   or '/' in name or '\\' in name or not name.endswith('_native.json') for name in names)
            or record.get('inheritedMemberCount') != 0
            or len(record.get('members', ())) != 5
            or (record.get('directDataSource') or {}).get('mode') != transfers.MODE):
        raise ValueError(f'{LABEL}.contract:source-profiles')
    return value


def _fail(check: str, expected: Any, actual: Any, *, record: str = RECORD, field: str = '') -> None:
    contract = _contract()
    error = CensusGateError(f'{LABEL}.{check}',
        source=(CONTRACTS_DIR / contract['records'][RECORD]['sourceContract']).as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, record=record, field=field,
                            nativeInputs=contract['nativeInputs'])
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _skip(status: str, detail: str, pins: dict) -> dict:
    return {'status': status, 'detail': detail, 'nativeInputs': pins,
            'childSchemaAdmitted': False, 'wholeActionAdmitted': False, 'wholeRootAdmitted': False}


def validate_current_native_contract(*, gameassembly: Path, metadata: Path) -> dict[str, Any]:
    contract = _contract(); pins = contract['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return _skip(gate.status, gate.detail, pins)
    record = contract['records'][RECORD]
    source_path = CONTRACTS_DIR / record['sourceContract']
    supplements = [CONTRACTS_DIR / name for name in contract['sourceSupplements']]
    paths = set(_package_import_closure(Path(__file__))) | {
        CONTRACT_PATH, source_path, *supplements, strings.CONTRACT_PATH,
        NATIVE_MAPPER_PATH, METADATA_HELPER_PATH}
    inputs = sorted((_fingerprint(path) for path in paths), key=lambda row: row['path'])
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    if not unity.is_file():
        return _skip('missing', 'UnityPlayer.dll absent beside selected GameAssembly.dll', pins)
    if _fingerprint(unity)['sha256'] != pins['UnityPlayer.dll']:
        return _skip('mismatched', 'Selected UnityPlayer.dll hash differs', pins)
    string_result = strings.validate_current_native_contract(gameassembly=gate.gameassembly, metadata=gate.metadata)
    if string_result.get('status') != 'validated' or string_result.get('nativeInputs') != pins:
        status = string_result.get('status', 'unresolved')
        return _skip('mismatched' if status == 'validated' else status,
                     'Physical string helper not validated for selected build', pins)
    image = open_native_image(gate.gameassembly, gate.metadata)
    source = json.loads(source_path.read_bytes())
    audit = buff_action_read_order(image.pe, image.metadata, image.registration,
        image.instantiations, image.modules, image.owners,
        source=str(gate.gameassembly), contract_path=source_path)
    for path in supplements:
        supplement = json.loads(path.read_bytes())
        if (supplement.get('schemaVersion') != 1 or not isinstance(supplement.get('methods'), list)
                or not isinstance(supplement.get('codeWindows'), list)):
            _fail('supplement-shape', 'reviewed formatter methods and windows', path.name)
        for method in supplement['methods']:
            image.validate_method_row(method, label=LABEL)
        image.check_windows(supplement['codeWindows'], label=LABEL)
        for window in supplement['codeWindows']:
            if window not in source['codeWindows']:
                source['codeWindows'].append(window)
    proved = named.validate_named_records(image, source, contract['records'], label=LABEL, fail=_fail)
    expected = {RECORD: [{'fieldName': m['fieldName'], 'kind': m['kind']} for m in record['members']]}
    if proved != expected:
        _fail('proved-members', expected, proved)
    transfer = transfers.validate_direct_data_sources(image, source, record,
        source_string_helpers=string_result['sourceHelpers'],
        fail=lambda check, expected, actual: _fail(check, expected, actual))
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated':
        return _skip(after.status, after.detail, pins)
    if not unity.is_file() or _fingerprint(unity)['sha256'] != pins['UnityPlayer.dll']:
        return _skip('mismatched' if unity.is_file() else 'missing', 'Selected UnityPlayer.dll changed during validation', pins)
    for before in inputs:
        actual = _fingerprint(Path(before['path']))
        if before != actual:
            _fail('source-drift', before, actual)
    return {'status': 'validated', 'nativeInputs': pins, 'recordMembers': proved,
        'sourceReadOrderAudit': audit, 'operandTransfer': transfer,
        'physicalStringHelper': string_result, 'provenance': {'inputs': inputs},
        'childSchemaAdmitted': False, 'wholeActionAdmitted': False, 'wholeRootAdmitted': False,
        'providerSelectionAndExecutionProved': False, 'evidenceBoundary': contract['evidenceBoundary']}

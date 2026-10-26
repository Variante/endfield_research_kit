"""Current MoveTo parent source evidence, without recursive action admission.

Names, declared destinations and the selected union route are direct evidence.
Only the explicitly declared operand-transfer profiles are checked. Child
grammar, remaining owned operand flow and actual movement remain unresolved.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import (
    METADATA_HELPER_PATH, NATIVE_MAPPER_PATH, open_native_image, read_reviewed_contract,
)
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError, _fingerprint, _package_import_closure
from scripts.game_data.memorypack import named_native_records as named

LABEL = 'buffMoveToSource'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_move_to_source_native.json'
RECORD = 'moveTo'


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(CONTRACT_PATH,
        schema='endfield.buff-move-to-source-native-contract.v2',
        status='exact-current-build', label=LABEL)
    records = value.get('records', {})
    dispatch = value.get('actionDispatch', {})
    if (set(records) != {RECORD} or len(dispatch) != 1 or set(dispatch.values()) != {RECORD}
            or any(not tag.isdecimal() or not 0 <= int(tag) <= 65535 for tag in dispatch)):
        raise ValueError(f'{LABEL}.contract:parent-source-shape')
    record = records[RECORD]
    names = [record.get('sourceContract'), *value.get('sourceSupplements', ())]
    if (not isinstance(value.get('sourceSupplements'), list)
            or len(names) != len(set(names))
            or any(not isinstance(name, str) or Path(name).name != name
                   or '/' in name or '\\' in name or not name.endswith('_native.json') for name in names)
            or record.get('inheritedMemberCount') != 4
            or (record.get('inheritedDirectActionSource') or {}).get('mode')
                != 'reader-rbx-wrapper-ref-rdi-four-common-direct-stores'):
        raise ValueError(f'{LABEL}.contract:source-profiles')
    return value


def _members(contract: dict[str, Any]) -> dict[str, Any]:
    return {key: [{'fieldName': member['fieldName'], 'kind': member['kind']}
                  for member in record['members']]
            for key, record in contract['records'].items()}


def _fail(check: str, expected: Any, actual: Any, *, record: str = RECORD,
          field: str = '') -> None:
    contract = _contract()
    error = CensusGateError(f'{LABEL}.{check}',
        source=(CONTRACTS_DIR / contract['records'][record]['sourceContract']).as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, record=record, field=field,
                            nativeInputs=contract['nativeInputs'])
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _skip(status: str, detail: str, pins: dict[str, Any]) -> dict[str, Any]:
    return {'status': status, 'detail': detail, 'nativeInputs': pins,
            'wholeActionAdmitted': False, 'wholeRootAdmitted': False}


def validate_current_native_contract(*, gameassembly: Path | None = None,
                                     metadata: Path | None = None) -> dict[str, Any]:
    contract = _contract()
    pins = contract['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return _skip(gate.status, gate.detail, pins)
    record = contract['records'][RECORD]
    source_path = CONTRACTS_DIR / record['sourceContract']
    supplemental_paths = [CONTRACTS_DIR / name for name in contract['sourceSupplements']]
    paths = set(_package_import_closure(Path(__file__))) | {
        CONTRACT_PATH, source_path, *supplemental_paths, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH}
    inputs = sorted((_fingerprint(path) for path in paths), key=lambda row: row['path'])
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    if not unity.is_file():
        return _skip('missing', 'UnityPlayer.dll is absent beside selected GameAssembly.dll', pins)
    if _fingerprint(unity)['sha256'] != pins['UnityPlayer.dll']:
        return _skip('mismatched', 'UnityPlayer.dll hash differs from reviewed source contract', pins)
    image = open_native_image(gate.gameassembly, gate.metadata)
    source = json.loads(source_path.read_bytes())
    audit = buff_action_read_order(image.pe, image.metadata, image.registration,
        image.instantiations, image.modules, image.owners,
        source=str(gate.gameassembly), contract_path=source_path, native_image=image)
    for path in supplemental_paths:
        supplement = json.loads(path.read_bytes())
        if (supplement.get('schemaVersion') != 1 or not isinstance(supplement.get('methods'), list)
                or not isinstance(supplement.get('codeWindows'), list)):
            _fail('supplement-shape', 'reviewed formatter method/window declarations', path.name)
        for method in supplement['methods']:
            image.validate_method_row(method, label=LABEL)
        image.check_windows(supplement['codeWindows'], label=LABEL)
        for window in supplement['codeWindows']:
            if window not in source['codeWindows']:
                source['codeWindows'].append(window)
    proved = named.validate_named_records(image, source, contract['records'], label=LABEL, fail=_fail)
    if proved != _members(contract):
        _fail('proved-members', _members(contract), proved)
    routes, route_audit = load_action_routes(gameassembly=gate.gameassembly, metadata=gate.metadata)
    tag = int(next(iter(contract['actionDispatch'])))
    route = routes.get(tag)
    if (route_audit.get('status') != 'validated' or route is None or route.status != 'resolved'
            or route.wrapper_type_definition != record['wrapperTypeDefinition']
            or route.wrapper_name != record['wrapperTypeName']
            or route.inherited_member_count != record['inheritedMemberCount']
            or list(route.member_order) != [member['fieldName'] for member in record['members']]
            or list(route.member_declared_types) != [member['declaredType'] for member in record['members']]):
        _fail('dispatcher-members', {'tag': tag, 'wrapper': record['wrapperTypeName'],
            'members': [member['fieldName'] for member in record['members']]},
            {'audit': route_audit.get('status'), 'route': None if route is None else route.row()})
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated':
        return _skip(after.status, after.detail, pins)
    if not unity.is_file():
        return _skip('missing', 'UnityPlayer.dll disappeared during source validation', pins)
    if _fingerprint(unity)['sha256'] != pins['UnityPlayer.dll']:
        return _skip('mismatched', 'UnityPlayer.dll changed during source validation', pins)
    for before in inputs:
        actual = _fingerprint(Path(before['path']))
        if actual != before:
            _fail('source-drift', before, actual)
    return {'status': 'validated', 'nativeInputs': pins, 'recordMembers': proved,
        'actionDispatch': contract['actionDispatch'], 'sourceReadOrderAudit': audit,
        'dispatcherRoute': route.row(), 'provenance': {'inputs': inputs},
        'wholeActionAdmitted': False, 'wholeRootAdmitted': False,
        'providerSelectionAndExecutionProved': False,
        'evidenceBoundary': contract['evidenceBoundary']}

"""Static Timeline/ForceSync registration and reference-wrapper joins.

This validator grants no stored element, list or root admission. The source
element lane and the nullable/list composition obligations remain separate.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.formatter_composition import (
    validate_registered_formatter_composition, validate_source_list_formatter_registration)
from scripts.game_data.il2cpp.formatter_registration import (
    validate_eager_wrap_registration, validate_wrapper_formatter_registration,
    validate_reference_wrapper_forwarding)
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.named_native_records import check_typed_context
from scripts.game_data.memorypack.corpus_gate import CensusGateError

LABEL = 'buffTimelineStaticComposition'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_timeline_static_composition_native.json'
SCHEMA = 'endfield.buff-timeline-static-composition-native-contract.v1'
SCOPE = 'static-registration-and-wrapper-forwarding-only'
ORIGINALS = {'Beyond.Gameplay.Core.TimelineAction+TimelineActionData',
             'Beyond.Gameplay.Core.TimelineAction+ForceSyncAnimData'}


def _fail(check: str, expected: Any, actual: Any) -> None:
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, scope=SCOPE)
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _contract() -> dict:
    contract, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA,
        status='exact-current-build', label=LABEL)
    if contract.get('scope') != SCOPE:
        _fail('scope', SCOPE, contract.get('scope'))
    for key in ('adapterRegistrationFlows', 'wrapperConversions'):
        rows = contract[key]
        if len(rows) != 2 or {r['originalType'] for r in rows} != ORIGINALS:
            _fail('concrete-types', sorted(ORIGINALS), {key: rows})
    return contract


def _validate_image(image: Any, contract: dict) -> dict:
    source, _ = read_reviewed_contract(CONTRACTS_DIR / contract['dependencies']['sourceElements'],
        schema='endfield.buff-timeline-element-sources-native-contract.v1', status='exact-current-build', label=LABEL)
    root, _ = read_reviewed_contract(CONTRACTS_DIR / contract['dependencies']['rootSourceList'],
        schema='endfield.buff-timeline-empty-native-contract.v1', status='exact-current-build', label=LABEL)
    if any(d['nativeInputs'] != contract['nativeInputs'] for d in (source, root)):
        _fail('dependency-build', contract['nativeInputs'], [d['nativeInputs'] for d in (source, root)])
    composition = contract['composition']
    validate_registered_formatter_composition(image, composition, label=LABEL)
    image.validate_method_row(contract['eagerOwnerMethod'], label=LABEL)
    originals = {r['originalType']: r for r in composition['registrations']}
    interfaces = {r['originalType']: r for r in composition['interfaces']}
    concrete = {r['runtimeTypeName']: r for r in source['records'].values()}
    if set(originals) != ORIGINALS or set(interfaces) != ORIGINALS or set(concrete) != ORIGINALS:
        _fail('source-composition-bijection', sorted(ORIGINALS), [sorted(originals), sorted(interfaces), sorted(concrete)])
    for flow in contract['adapterRegistrationFlows']:
        expected = originals[flow['originalType']]
        if (flow['wrapperType'] != expected['wrapperType']
                or flow['constructor']['methodSpecIndex'] != expected['constructorMethodSpecIndex']
                or flow['allocation']['typeIndex'] != expected['adapterTypeIndex']
                or flow['key']['typeIndex'] != expected['keyTypeIndex']):
            _fail('registration-source-identity', expected, flow)
        validate_eager_wrap_registration(image, flow, label=LABEL)
    entries = GenericEntries(image)
    shared = contract['sharedConstructorEntries']
    if len(shared) != 2 or {tuple(r['requestedConcreteArguments']) for r in shared} != {
            (r['originalType'], r['wrapperType']) for r in contract['adapterRegistrationFlows']}:
        _fail('shared-constructor-bijection', 'one independent shared entry per concrete context', shared)
    for row in shared:
        if (row['classArguments'] != ['object', 'object'] or row['methodArguments'] != []
                or row['conditionalInflationOnly'] is not True):
            _fail('shared-entry-boundary', 'independent Object/Object registration only', row)
        actual = entries.resolve(row['definition'], row['classArguments'], row['methodArguments'])
        if json.loads(json.dumps(actual)) != row['registration']:
            _fail('shared-entry-registration', row['registration'], actual)
        flow = next(f for f in contract['adapterRegistrationFlows']
                    if [f['originalType'], f['wrapperType']] == row['requestedConcreteArguments'])
        if (row['definition'] != flow['constructor']['methodSpec'][0]
                or actual['pointer'] - image.pe.image_base != flow['constructorThunk']['sharedTargetRva']):
            _fail('shared-entry-thunk-target', flow['constructorThunk'], row)
    wrappers = {}
    for conversion in contract['wrapperConversions']:
        original = conversion['originalType']; expected = concrete[original]; interface = interfaces[original]
        if (conversion['wrapperType'] != expected['wrapperTypeName']
                or interface['wrapperDefinition'] != expected['wrapperTypeDefinition']
                or conversion['sourceMethod'] != expected['readerMethod']
                or conversion['getterMethod'][0] != interface['getValueMethodIndex']
                or conversion['formatterMethod'][0] != interface['formatterDeserializeMethodIndex']):
            _fail('wrapper-source-forwarding-identity', expected['readerMethod'], conversion)
        validate_reference_wrapper_forwarding(image, conversion, label=LABEL)
        wrappers[conversion['wrapperType']] = conversion['formatterMethod'][1]
    flows = contract['wrapperRegistrationFlows']
    if len(flows) != 2 or {f['wrapperType'] for f in flows} != set(wrappers):
        _fail('wrapper-registration-bijection', sorted(wrappers), flows)
    for flow in flows:
        interface = next(r for r in interfaces.values() if r['wrapperType'] == flow['wrapperType'])
        if (flow['formatterType'] != wrappers[flow['wrapperType']]
                or flow['formatterDefinition'] != interface['formatterDefinition']
                or flow['wrapperDefinition'] != interface['wrapperDefinition']):
            _fail('registered-wrapper-formatter', wrappers[flow['wrapperType']], flow['formatterType'])
        validate_wrapper_formatter_registration(image, flow, label=LABEL)
    flow = dict(contract['sourceListRegistration'], sourceContext=root['listSourceContext'])
    if flow['elementType'] != 'Beyond.Gameplay.Core.TimelineAction+TimelineActionData':
        _fail('source-list-element', 'TimelineActionData', flow['elementType'])
    check_typed_context(image, flow['sourceContext'], root['timelineFieldType'], label=LABEL, fail=_fail)
    validate_source_list_formatter_registration(image, flow, label=LABEL)
    return {'staticAdapterFlows': 2, 'constructorThunks': 2, 'wrapperRegistrations': 2,
            'typedWrapperConversions': 2, 'sourceListRegistrations': 1}


def validate_current_native_contract(*, gameassembly: Path | None = None,
                                      metadata: Path | None = None) -> dict:
    contract = _contract(); pins = contract['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return {'status': gate.status, 'detail': gate.detail, 'nativeInputs': pins, 'scope': SCOPE}
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    def unity_matches() -> bool:
        return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == pins['UnityPlayer.dll']
    if not unity_matches():
        return {'status': 'mismatched' if unity.is_file() else 'missing',
                'detail': 'UnityPlayer.dll missing or mismatched', 'nativeInputs': pins, 'scope': SCOPE}
    try:
        summary = _validate_image(open_native_image(gate.gameassembly, gate.metadata), contract)
    except ValueError as error:
        if isinstance(error, CensusGateError):
            raise
        _fail('native-static-flow', 'current concrete identity and complete programs', str(error))
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated' or not unity_matches():
        return {'status': after.status if after.status != 'validated' else 'mismatched',
                'detail': 'native inputs changed during validation', 'nativeInputs': pins, 'scope': SCOPE}
    return {'status': 'validated', 'scope': SCOPE, 'nativeInputs': pins, 'summary': summary,
            'positiveListAdmitted': False, 'wholeRootAdmitted': False, 'runtimeMeaningExact': False,
            'evidenceBoundary': contract['evidenceBoundary']}

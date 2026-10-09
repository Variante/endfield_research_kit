"""Conditional abstract action adapter and complete union false/output return."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack import buff_action_union_header as headers
from scripts.game_data.memorypack import buff_timeline_instance as instances
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack.reference_instance_sources import validate_positive_instance_transfer
from scripts.game_data.memorypack.union_false_sources import validate_union_false_return

LABEL = 'buffActionReference'
SCHEMA = 'endfield.buff-action-reference-native-contract.v1'
SCOPE = 'conditional-abstract-adapter-and-buffered-union-false-return-only'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_action_reference_native.json'


def _fail(check: str, expected: Any, actual: Any) -> None:
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
                           expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, scope=SCOPE)
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _contract() -> dict:
    c, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status='exact-current-build', label=LABEL)
    if (c.get('scope') != SCOPE or set(c['abstractPrograms']) != {'nonnull', 'nullWrapperOutput'}
            or set(c['dependencies']) != {'header', 'instance', 'reference', 'source', 'wrappers'}):
        _fail('action-reference-scope', 'two abstract output paths and five exact native dependencies', c.get('scope'))
    return c


def _validate_image(image: Any, c: dict) -> dict:
    schemas = {'header': headers.SCHEMA, 'instance': instances.SCHEMA,
        'reference': 'endfield.buff-timeline-reference-native-contract.v2',
        'source': 'endfield.buff-timeline-element-sources-native-contract.v1',
        'wrappers': 'endfield.buff-timeline-source-wrappers-native-contract.v1'}
    deps = {k: read_reviewed_contract(CONTRACTS_DIR / c['dependencies'][k], schema=s,
            status='exact-current-build', label=LABEL)[0] for k, s in schemas.items()}
    if any(d['nativeInputs'] != c['nativeInputs'] for d in deps.values()):
        _fail('action-reference-dependency-build', c['nativeInputs'], {k: d['nativeInputs'] for k, d in deps.items()})
    header, instance, reference, source, wrappers = (deps[k] for k in schemas)
    header_summary = headers._validate_image(image, header)
    instance_summary = instances._validate_image(image, instance)
    row = next(r for r in reference['sharedEntries'] if not r['nonnull'])
    actual = GenericEntries(image).resolve(row['method'][0], row['classArguments'], row['methodArguments'])
    if json.loads(json.dumps(actual)) != row['registration']:
        _fail('abstract-adapter-independent-entry', row['registration'], actual)
    entry = actual['pointer'] - image.pe.image_base
    if any(p['program'][0][0] != entry or p['codeWindows'][0]['startRva'] != entry
           for p in c['abstractPrograms'].values()):
        _fail('abstract-adapter-actual-entry', entry, c['abstractPrograms'])
    transfers = {k: validate_positive_instance_transfer(image, p, instance['calls'],
        source['readerFieldsUnboxedOffsets'], null_wrapper=k == 'nullWrapperOutput',
        creation='abstract', fail=_fail) for k, p in c['abstractPrograms'].items()}
    false = c['unionFalseProgram']
    if (false['program'][0][0] != header['callerMethod'][3]
            or false['program'][:16] != header['callerPrefix']['program'][:16]
            or false['codeWindows'][0] != header['callerPrefix']['codeWindows'][0]):
        _fail('union-false-caller-and-helper-join', 'same owned caller entry and initialized AL prefix', false)
    clear = validate_union_false_return(image, false, header['helperEntryRva'], c['barrierTrampoline'],
                                        wrappers['barrierProgram'], fail=_fail)
    return {'staticActionBinding': header_summary,
            'ownedSharedAdapterContexts': instance_summary['additionalMethodContexts'],
            'conditionalTypeFlags': instance_summary['conditionalTypeFlags'],
            'abstractAdapterTransfers': transfers, 'unionFalseReturn': clear,
            'runtimeClassAttributeBridge': 'conditional', 'actualArrayCallbackSelection': 'unresolved',
            'positiveUnionSwitchAndConcreteChildComposition': 'unresolved',
            'reservedMarkerCanonicalAdmission': False}


def validate_current_native_contract(*, gameassembly: Path | None = None, metadata: Path | None = None) -> dict:
    c = _contract()
    pins = c['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                        gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return {'status': gate.status, 'detail': gate.detail, 'nativeInputs': pins, 'scope': SCOPE}
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    def unity_matches():
        return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == pins['UnityPlayer.dll']
    if not unity_matches():
        return {'status': 'mismatched' if unity.is_file() else 'missing', 'detail': 'UnityPlayer.dll missing or mismatched',
                'nativeInputs': pins, 'scope': SCOPE}
    try:
        summary = _validate_image(open_native_image(gate.gameassembly, gate.metadata), c)
    except ValueError as error:
        if isinstance(error, CensusGateError):
            raise
        _fail('native-action-reference', 'current owned abstract/output/return joins', str(error))
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                         gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated' or not unity_matches():
        return {'status': after.status if after.status != 'validated' else 'mismatched',
                'detail': 'native inputs changed during action reference validation', 'nativeInputs': pins, 'scope': SCOPE}
    return {'status': 'validated', 'scope': SCOPE, 'nativeInputs': pins, 'summary': summary,
            'childSchemaAdmitted': False, 'positiveListAdmitted': False, 'wholeRootAdmitted': False,
            'runtimeMeaningExact': False, 'reservedMarkerCanonicalAdmission': False,
            'evidenceBoundary': c['evidenceBoundary']}

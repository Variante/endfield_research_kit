"""Join declared action adapter ABI to the owned array transfer, selection open."""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.formatter_callback_signatures import validate_adapter_callback_signature
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.native_image import (open_native_image, read_reviewed_contract,
    NATIVE_MAPPER_PATH, METADATA_HELPER_PATH)
from scripts.game_data.memorypack import (buff_sequence_array_source as arrays,
    buff_action_union_header as headers, buff_action_reference as actions)
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError, _fingerprint, _parser_source_snapshots

LABEL = 'buffActionArrayCallbackBinding'
SCHEMA = 'endfield.buff-action-array-callback-binding-native-contract.v1'
SCOPE = 'declared-adapter-slot-abi-and-static-array-transfer-only'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_action_array_callback_binding_native.json'


def _fail(check: str, expected: Any, actual: Any) -> None:
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, scope=SCOPE)
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _contract() -> dict:
    c, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status='exact-current-build', label=LABEL)
    if (c.get('scope') != SCOPE or set(c.get('dependencies', {})) != {'array','header','reference','actionReference'}
            or set(c.get('callbackSpecification', {})) != {'typeName','typeDefinition','flags',
                'deserializeMethod','baseFormatterType','slot','returnTypeFlags','baseMethodFlags','baseSlotWord'}):
        _fail('binding-scope', 'four independently owned dependencies and complete declared signature', c.get('scope'))
    if set(c.get('arrayTransferJoin', {})) != {'sameReaderRegister','formatterRegister','childOutputRegister',
            'childOutputAddress','runtimeReferenceStride'}:
        _fail('array-transfer-scope', 'all five owned Reader/receiver/output transfer joins', c.get('arrayTransferJoin'))
    return c


def _proof_sources() -> list[dict]:
    """Freeze imports and the recursively referenced reviewed contract data.

    Dynamic hashes are report provenance, not pinned integrity checks for git
    files. Native bytes still have their separate selected-build gates.
    """
    sources = _parser_source_snapshots(Path(__file__))
    pending = {CONTRACT_PATH}
    for row in sources:
        for node in ast.walk(ast.parse(Path(row['path']).read_text(encoding='utf-8-sig'))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = node.value
                if value.endswith('.json') and Path(value).name == value and (CONTRACTS_DIR / value).is_file():
                    pending.add(CONTRACTS_DIR / value)
    seen = set()
    def references(value):
        if isinstance(value, dict):
            for child in value.values(): yield from references(child)
        elif isinstance(value, list):
            for child in value: yield from references(child)
        elif isinstance(value, str) and value.endswith('.json') and Path(value).name == value:
            target = CONTRACTS_DIR / value
            if target.is_file(): yield target
    while pending:
        path = pending.pop()
        if path in seen: continue
        seen.add(path)
        pending.update(set(references(json.loads(path.read_bytes()))) - seen)
    paths = seen | {NATIVE_MAPPER_PATH, METADATA_HELPER_PATH}
    return sources + [_fingerprint(path) for path in sorted(paths)]


def _compose(signature: dict, array: dict, header: dict, action: dict, expected_transfer: dict) -> dict:
    element = array['elementType']; context = array['ownedArrayContext']; transfer = array['completeSourcePrograms']
    if signature['originalType'] != element:
        _fail('original-element-join', signature['originalType'], element)
    if not (context['readArrayOverloadsReciprocallyJoined'] is True
            and context['emptyArrayTypeProviderAndDeserializeOwned'] is True
            and transfer['completeSelectedReturns'] is True
            and signature['declaredAdapterSlotAndABIProved'] is True
            and signature['reciprocalOriginalParentSubstitutionProved'] is True
            and signature['closedEagerArgumentOrderProved'] is True
            and signature['readerByrefSameUnboxedType'] is True
            and signature['originalOutputByrefSameClosedReferenceType'] is True):
        _fail('complete-declared-transfer-join', 'complete independently proved array/adapter declarations', [signature, context])
    if (context['formatterSlot'] != signature['slot'] or transfer['formatterSlot'] != signature['slot']
            or transfer['runtimeReferenceStride'] != 8 or transfer['childOutputRegister'] != 'r8'):
        _fail('slot-and-reference-output-join', 'same slot and full Win64 original reference byref output', transfer)
    for name,wanted in expected_transfer.items():
        if transfer[name] != wanted:
            _fail('owned-array-transfer-join', {name:wanted}, {name:transfer[name]})
    if (header['staticOriginalAdapterRegistration'] != 'proved'
            or header['staticWrapperUnionRegistration'] != 'proved'):
        _fail('static-registration-join', 'both current original/adapter and wrapper/union static flows', header)
    return {'declaredSignature': signature, 'arrayElementType': element,
        'sameReaderRegister': transfer['sameReaderRegister'], 'formatterReceiverRegister': transfer['formatterRegister'],
        'childOutputAddress': transfer['childOutputAddress'], 'formatterSlot': signature['slot'],
        'abstractSharedAdapterTransfers': action['abstractAdapterTransfers'], 'unionFalseReturn': action['unionFalseReturn'],
        'nominalArrayCallbackAbiJoined': True, 'actualArrayCallbackTargetProved': False,
        'runtimeClassAttributeBridge': 'conditional', 'callbackCursorEqualityProved': False,
        'positiveListAdmitted': False, 'wholeRootAdmitted': False}


def _validate_image(image: Any, c: dict) -> dict:
    schemas = {'array': arrays.SCHEMA, 'header': headers.SCHEMA,
        'reference': 'endfield.buff-timeline-reference-native-contract.v2', 'actionReference': actions.SCHEMA}
    deps = {key: read_reviewed_contract(CONTRACTS_DIR / c['dependencies'][key], schema=schema,
        status='exact-current-build', label=LABEL)[0] for key,schema in schemas.items()}
    if any(row['nativeInputs'] != c['nativeInputs'] for row in deps.values()):
        _fail('binding-dependency-build', c['nativeInputs'], {k:v['nativeInputs'] for k,v in deps.items()})
    array = arrays._validate_image(image, deps['array'])
    header = headers._validate_image(image, deps['header'])
    action = actions._validate_image(image, deps['actionReference'])
    rows = [row for row in deps['reference']['sharedEntries'] if not row['nonnull']]
    spec = c['callbackSpecification']; eager = deps['header']['adapterRegistrationFlow']
    if len(rows) != 1 or rows[0]['method'] != spec['deserializeMethod']:
        _fail('independent-adapter-method-join', 'same independently registered adapter metadata declaration', rows)
    slot_rows = [row for row in deps['array']['genericContexts'][1]['entries'] if row['relativeSlot'] == spec['slot']]
    if len(slot_rows) != 1:
        _fail('base-deserialize-context-slot', 'one exact array formatter declaration', slot_rows)
    base = slot_rows[0]['methodSpec'][0]
    signature = validate_adapter_callback_signature(image, spec, eager, base, fail=_fail)
    summary = _compose(signature, array, header, action, c['arrayTransferJoin'])
    entries = GenericEntries(image)
    shared = entries.resolve(rows[0]['method'][0], rows[0]['classArguments'], rows[0]['methodArguments'])
    if json.loads(json.dumps(shared)) != rows[0]['registration']:
        _fail('independent-shared-registration', rows[0]['registration'], shared)
    try:
        closed = {'status':'registered', 'registration':entries.resolve(spec['deserializeMethod'][0],
            eager['constructor']['classArguments'], [])}
    except ValueError as error:
        closed = {'status':'no-unique-closed-registration', 'detail':str(error)}
    summary['selectedClosedCompiledRegistration'] = closed
    summary['independentSharedRegistration'] = shared
    return summary


def validate_current_native_contract(*, gameassembly: Path | None = None, metadata: Path | None = None) -> dict:
    c = _contract(); pins = c['nativeInputs']; sources = _proof_sources()
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gameassembly, metadata=metadata)
    result = {'status':gate.status, 'scope':SCOPE, 'nativeInputs':pins, 'provenance':{'inputs':sources},
        'childSchemaAdmitted':False, 'positiveListAdmitted':False, 'wholeRootAdmitted':False,
        'actualArrayCallbackTargetProved':False, 'callbackCursorEqualityProved':False, 'runtimeMeaningExact':False,
        'evidenceBoundary':c['evidenceBoundary']}
    if gate.status != 'validated': return {**result, 'detail':gate.detail}
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    def unity_hash():
        if not unity.is_file(): return None
        with unity.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest().upper()
    current_unity = unity_hash()
    if current_unity != pins['UnityPlayer.dll']:
        return {**result, 'status':'missing' if current_unity is None else 'mismatched', 'detail':'UnityPlayer.dll missing or mismatched'}
    try:
        summary = _validate_image(open_native_image(gate.gameassembly, gate.metadata), c)
    except (ValueError, KeyError, IndexError, TypeError) as error:
        if isinstance(error, CensusGateError): raise
        _fail('native-callback-binding', 'complete current declared slot/ABI/transfer joins', str(error))
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    after_unity = unity_hash()
    if after.status != 'validated' or after_unity != pins['UnityPlayer.dll']:
        return {**result, 'status':after.status if after.status != 'validated' else 'missing' if after_unity is None else 'mismatched',
            'detail':'native inputs changed during declared callback binding validation'}
    drift = [row['path'] for row in sources if _fingerprint(Path(row['path'])) != row]
    if drift: _fail('proof-source-drift', 'unchanged complete source/contract closure', drift)
    return {**result, 'status':'validated', 'summary':summary}

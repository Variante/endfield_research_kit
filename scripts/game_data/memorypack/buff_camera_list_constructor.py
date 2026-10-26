"""Camera list static registration and complete shared constructor control."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.formatter_registration_flow import validate_formatter_registration_flow
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex, read_exception_directory
from scripts.game_data.il2cpp.list_formatter_constructor_control import validate_list_formatter_constructor_control
from .named_native_records import check_typed_context

CONTRACT_PATH = CONTRACTS_DIR / 'buff_camera_list_constructor_native.json'
SCHEMA = 'endfield.buff-camera-list-constructor-native-contract.v1'
LABEL = 'buffCameraListConstructor'


def _skip(status, detail, pins):
    return {'status': status, 'detail': detail, 'nativeInputs': pins,
            'positiveListGrammarProved': False, 'wholeRootAdmitted': False, 'runtimeExecutionKnown': False}


def _validate_image(image, contract):
    def fail(check, expected, actual, **details):
        raise ValueError(json.dumps({'validator': LABEL, 'check': check, 'source': CONTRACT_PATH.as_posix(),
            'expected': str(expected)[:1000], 'actual': str(actual)[:1000], 'details': details}))
    dependency, _ = read_reviewed_contract(CONTRACTS_DIR / contract['sourceContract'],
        schema='endfield.buff-camera-usp-damage-actions-native-contract.v1', status='exact-current-build', label=LABEL)
    if dependency['nativeInputs'] != contract['nativeInputs']:
        fail('dependency-build', contract['nativeInputs'], dependency['nativeInputs'])
    row = contract['sharedConstructor']; image.validate_method_row(row['method'], label=LABEL)
    if row['method'][1:] != ['MemoryPack.Formatters.ListFormatter`1', '.ctor'] or row['classArguments'] != ['object'] or row['methodArguments'] != []:
        fail('shared-entry-selection', 'independent ListFormatter<Object> constructor', row)
    actual = GenericEntries(image).resolve(row['method'][0], row['classArguments'], row['methodArguments'])
    if json.loads(json.dumps(actual)) != row['registration']:
        fail('shared-entry-registration', row['registration'], actual)
    function = contract['function']; base = image.pe.image_base
    if actual['pointer'] - base != function['entryRva']:
        fail('actual-constructor-entry', function['entryRva'], actual['pointer'] - base)
    directory, size, raw = read_exception_directory(image.pe)
    unwind = UnwindChainIndex(raw, lambda at,n: image.pe.bytes_at_va(base+at,n), table_rva=directory, image_size=size)
    family = json.loads(json.dumps(unwind.family(function['entryRva'])))
    if family != function['unwindFamily']:
        fail('complete-exception-range-family', function['unwindFamily'], family)
    windows = function['codeWindows']
    if (len(windows) != 2 or [(w['startRva'],w['endRva']) for w in windows]
            != [tuple(r['runtimeTriple'][:2]) for r in family['ranges']]):
        fail('complete-code-window-membership', 'two exact declared exception ranges', windows)
    image.check_windows(windows, label=LABEL)
    bodies = [image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']) for w in windows]
    control = validate_list_formatter_constructor_control(*bodies,
        primary_va=base+windows[0]['startRva'], cold_va=base+windows[1]['startRva'])
    if contract['sourceRoles'] != ['cameraGroups','cameraConditions']:
        fail('source-role-membership', ['cameraGroups','cameraConditions'], contract['sourceRoles'])
    sources = {}; bindings = []
    for role in contract['sourceRoles']:
        flow = dependency['formatterRegistrations'][role]
        if (flow['constructor']['methodSpec'][0] != row['method'][0]
                or flow['actualCalls']['constructor'] != function['entryRva']):
            fail('camera-actual-shared-constructor', function['entryRva'], flow['actualCalls'])
        record = dependency['records'][flow['sourceRecord']]
        name = record['sourceContract']
        if Path(name).name != name or not name.endswith('.json'):
            fail('source-contract-basename', 'contract basename', name)
        source = sources.setdefault(name, json.loads((CONTRACTS_DIR/name).read_bytes()))
        image.validate_method_row(flow['ownerMethod'], label=LABEL)
        image.check_windows([flow['ownerWindow']], label=LABEL)
        for field in flow['sourceFields']:
            members = [m for m in record['members'] if m['fieldName'] == field]
            if len(members) != 1 or members[0]['declaredType'] != flow['keyType']:
                fail('field-type-key', flow['keyType'], members, field=field)
            contexts = [c for c in source['nestedContexts'] if c['instructionRva'] == members[0]['sourceContextInstructionRva']]
            if len(contexts) != 1: fail('one-field-context', 1, len(contexts), field=field)
            check_typed_context(image, contexts[0], flow['keyType'], label=LABEL, fail=fail)
            summary = validate_formatter_registration_flow(image, flow, contexts[0], label=LABEL)
            bindings.append({'fieldName': field, 'elementType': summary['elementType'],
                'staticRegistration': summary, 'matchesIndependentSharedConstructor': True})
    if [b['fieldName'] for b in bindings] != ['enterConditionsOr','leaveConditionsOr','and']:
        fail('all-source-fields', 'both parent lists and group inner list', bindings)
    return {'sharedConstructorControl': control, 'sourceBindings': bindings,
        'concreteRuntimeInflationObserved': False, 'indirectInitializationEffectsProved': False}


def validate_current_native_contract(*, gameassembly: Path, metadata: Path):
    contract, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status='exact-current-build', label=LABEL)
    pins = contract['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'], gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated': return _skip(gate.status, gate.detail, pins)
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    def unity_matches():
        if not unity.is_file(): return False
        with unity.open('rb') as stream:
            return hashlib.file_digest(stream,'sha256').hexdigest().upper() == pins['UnityPlayer.dll']
    if not unity_matches(): return _skip('mismatched' if unity.is_file() else 'missing','Selected UnityPlayer.dll missing or mismatched',pins)
    summary = _validate_image(open_native_image(gate.gameassembly,gate.metadata),contract)
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'], gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status != 'validated' or not unity_matches():
        return _skip(after.status if after.status != 'validated' else 'mismatched','Selected native inputs changed',pins)
    return {'status':'validated','nativeInputs':pins,'summary':summary,'positiveListGrammarProved':False,
        'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'evidenceBoundary':contract['evidenceBoundary']}

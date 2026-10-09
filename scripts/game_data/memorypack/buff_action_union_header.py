"""Static original action binding and current buffered union tag-helper control."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
from scripts.game_data.il2cpp.formatter_registration import (
    validate_eager_wrap_registration, validate_wrapper_formatter_registration)
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack.union_header_sources import (
    validate_union_header_programs, validate_union_header_caller_prefix)

LABEL = 'buffActionUnionHeader'
SCHEMA = 'endfield.buff-action-union-header-native-contract.v1'
SCOPE = 'static-action-binding-and-buffered-union-header-control-only'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_action_union_header_native.json'


def _fail(check: str, expected: Any, actual: Any) -> None:
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
                           expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, scope=SCOPE)
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _contract() -> dict:
    c, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status='exact-current-build', label=LABEL)
    if (c.get('scope') != SCOPE or set(c['programs']) != {'shortTag', 'extendedTag', 'highMarkerFalse'}
            or set(c['types']) != {'original', 'wrapper', 'formatter'}):
        _fail('union-header-scope', 'three typed owners and complete selected helper paths', c.get('scope'))
    return c


def _validate_image(image: Any, c: dict) -> dict:
    selected = NativeReferenceContext(image)
    arrays, _ = read_reviewed_contract(CONTRACTS_DIR / c['arraySourceDependency'],
        schema='endfield.buff-sequence-array-source-native-contract.v1', status='exact-current-build', label=LABEL)
    if arrays['nativeInputs'] != c['nativeInputs']:
        _fail('array-dependency-build', c['nativeInputs'], arrays['nativeInputs'])
    types = c['types']
    if arrays['readArrayUsage']['methodArguments'] != [types['original']['typeName']]:
        _fail('array-original-action-type', 'same already proved original array element', arrays['readArrayUsage'])
    validate_typed_usage_context(image, arrays['readArrayUsage'], label=LABEL)
    for role, row in types.items():
        td = selected.index.types[row['typeName']]
        wanted_abstract = role != 'formatter'
        if (td.index != row['definition'] or td.flags != row['flags']
                or bool(td.flags & 0x80) != wanted_abstract or selected.is_value_type(row['typeName'])):
            _fail('metadata-owner-and-abstract-mask', {'role': role, 'abstract': wanted_abstract}, row)
    image.validate_method_row(c['eagerOwnerMethod'], label=LABEL)
    eager = c['adapterRegistrationFlow']
    if [eager['originalType'], eager['wrapperType']] != [types[k]['typeName'] for k in ('original', 'wrapper')]:
        _fail('original-adapter-binding', 'same original/base-wrapper pair', eager)
    validate_eager_wrap_registration(image, eager, label=LABEL)
    shared = c['sharedConstructorEntry']
    actual = GenericEntries(image).resolve(shared['definition'], shared['classArguments'], shared['methodArguments'])
    if (json.loads(json.dumps(actual)) != shared['registration']
            or actual['pointer'] - image.pe.image_base != eager['constructorThunk']['sharedTargetRva']):
        _fail('independent-shared-adapter-constructor', 'same independently registered shared constructor', shared)
    registration = c['wrapperRegistrationFlow']
    if [registration['wrapperType'], registration['formatterType']] != [types[k]['typeName'] for k in ('wrapper', 'formatter')]:
        _fail('wrapper-union-registration', 'same wrapper and named union formatter', registration)
    validate_wrapper_formatter_registration(image, registration, label=LABEL)
    method = c['callerMethod']
    image.validate_method_row(method, label=LABEL)
    m = image.metadata.methods[method[0]]
    parameters = image.metadata.parameters_for(m)
    if (method[1:3] != [types['formatter']['typeName'], 'Deserialize'] or m.flags & 0x10
            or selected.type_name(m.return_type) != 'void' or len(parameters) != 2):
        _fail('union-caller-declaration', 'instance void Deserialize(ref Reader, ref base wrapper)', method)
    for parameter, wanted, kind in zip(parameters, ('MemoryPack.MemoryPackReader', types['wrapper']['typeName']), (0x11, 0x12)):
        raw = image.pe.bytes_at_va(selected.type_pointer(parameter.type_index), 16)
        if selected.type_name(parameter.type_index) != wanted or raw[10:12] != bytes((kind, 0x20)):
            _fail('union-caller-byref-arguments', wanted, raw.hex())
    offsets = c['readerFieldsUnboxedOffsets']
    if offsets != {n: selected.field('MemoryPack.MemoryPackReader::' + n)[2] - 16 for n in offsets}:
        _fail('reader-layout', 'same metadata-owned unboxed Reader fields', offsets)
    caller = c['callerPrefix']
    if caller['program'][0][0] != method[3]:
        _fail('caller-entry', method[3], caller['program'][0])
    helper = c['helperEntryRva']
    if any(p['program'][0][0] != helper or p['codeWindows'] != [c['helperWindow']] for p in c['programs'].values()):
        _fail('actual-helper-window', 'same actual called physical helper window', c['programs'])
    control = validate_union_header_programs(image, c['programs'], offsets, fail=_fail)
    caller_control = validate_union_header_caller_prefix(image, caller, helper, fail=_fail)
    return {'staticOriginalAdapterRegistration': 'proved', 'staticWrapperUnionRegistration': 'proved',
            'originalAndBaseWrapperMetadataAbstract': True, 'runtimeClassAttributeBridge': 'conditional',
            'abstractWrapperCreationAndActualCallbackSelection': 'unresolved',
            'bufferedTagHelper': control, 'callerTagTransfer': caller_control,
            'physicalHelperNamedIdentity': 'unresolved',
            'completeUnionAndChildCursorComposition': 'unresolved'}


def validate_current_native_contract(*, gameassembly: Path | None = None, metadata: Path | None = None) -> dict:
    c = _contract()
    pins = c['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                        gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return {'status': gate.status, 'detail': gate.detail, 'scope': SCOPE, 'nativeInputs': pins}
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    def unity_matches():
        return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == pins['UnityPlayer.dll']
    if not unity_matches():
        return {'status': 'mismatched' if unity.is_file() else 'missing', 'detail': 'UnityPlayer.dll missing or mismatched',
                'scope': SCOPE, 'nativeInputs': pins}
    try:
        summary = _validate_image(open_native_image(gate.gameassembly, gate.metadata), c)
    except ValueError as error:
        if isinstance(error, CensusGateError):
            raise
        _fail('native-union-header', 'complete current static bindings and selected tag-helper/caller paths', str(error))
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                         gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated' or not unity_matches():
        return {'status': after.status if after.status != 'validated' else 'mismatched',
                'detail': 'native inputs changed during union header validation', 'scope': SCOPE, 'nativeInputs': pins}
    return {'status': 'validated', 'scope': SCOPE, 'nativeInputs': pins, 'summary': summary,
            'childSchemaAdmitted': False, 'positiveListAdmitted': False, 'wholeRootAdmitted': False,
            'runtimeMeaningExact': False, 'reservedMarkerCanonicalAdmission': False, 'evidenceBoundary': c['evidenceBoundary']}

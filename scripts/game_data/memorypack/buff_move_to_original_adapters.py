"""Validate current MoveTo/SubSpeed original adapters and concrete conversions."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import struct
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import (
    open_native_image, read_reviewed_contract, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH,
)
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.formatter_composition import (
    validate_registered_formatter_composition, validate_generic_contexts, validate_typed_usage_context,
)
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.il2cpp.formatter_callback_signatures import validate_adapter_callback_signature
from scripts.game_data.memorypack.reference_conversion_sources import validate_conversion_context, validate_formatter_dispatch
from scripts.game_data.memorypack.read_value_reference_sources import validate_read_value_context
from scripts.game_data.memorypack import original_adapter_sources as transfers
from scripts.game_data.memorypack import buff_move_to_formatter_routes as wrapper_routes
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError, _fingerprint, _package_import_closure

LABEL = 'buffMoveToOriginalAdapters'
SCHEMA = 'endfield.buff-move-to-original-adapters-native-contract.v1'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_move_to_original_adapters_native.json'
DEPENDENCY_SCHEMAS = {
    'parent': 'endfield.buff-move-to-source-native-contract.v2',
    'subSpeed': 'endfield.buff-move-to-subspeed-source-native-contract.v1',
    'formatterRoutes': wrapper_routes.SCHEMA,
    'lifecycle': 'endfield.buff-move-to-lifecycle-native-contract.v1',
    'callback': 'endfield.buff-action-array-callback-binding-native-contract.v1',
    'reference': 'endfield.buff-timeline-reference-native-contract.v2',
    'readValue': 'endfield.buff-timeline-read-value-native-contract.v3',
    'provider': 'endfield.buff-formatter-provider-native-contract.v1',
}


def _fail(check: str, expected: Any, actual: Any) -> None:
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
                           expected=str(expected)[:1600], actual=str(actual)[:1800])
    error.diagnostic.update(validator=LABEL, check=check)
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _contract() -> dict:
    c, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status='exact-current-build', label=LABEL)
    names = c.get('dependencies', {})
    if (set(names) != set(DEPENDENCY_SCHEMAS) or set(c.get('records', {})) != {'moveTo', 'subSpeed'}
            or any(not isinstance(n, str) or Path(n).name != n or '/' in n or '\\' in n
                   or not n.endswith('_native.json') for n in names.values())):
        _fail('contract-scope', 'eight named dependencies and both original/wrapper pairs', names)
    return c


def _dependency(key: str, name: str) -> dict:
    path = CONTRACTS_DIR / name
    try:
        return read_reviewed_contract(path, schema=DEPENDENCY_SCHEMAS[key],
                                      status='exact-current-build', label=LABEL)[0]
    except (FileNotFoundError, ValueError) as error:
        _fail('dependency-contract', {'path': path.as_posix(), 'schema': DEPENDENCY_SCHEMAS[key],
                                      'status': 'exact-current-build'}, str(error))


def _shared_deserialize_join(image: Any, entries: Any, deps: dict) -> dict:
    definition = deps['callback']['callbackSpecification']['deserializeMethod'][0]
    shared = entries.resolve(definition, ['object', 'object'], [])
    proof = deps['reference']['conversionPrograms']['formatterDispatch']
    row = proof['program'][21]
    raw = bytes.fromhex(row[1])
    image.check_instruction_windows([row], label=LABEL)
    if (len(raw) != 7 or raw[:3] != b'\x48\x8d\x05'
            or proof['program'][0][0] != deps['readValue']['calls']['formatterDispatch']
            or shared['methodDefinitionIndices'] != [definition]):
        _fail('shared-adapter-deserialize-owner', 'unique independently registered adapter and actual dispatcher operand', row)
    candidate = row[0] + 7 + struct.unpack_from('<i', raw, 3)[0]
    if candidate != shared['pointer'] - image.pe.image_base:
        _fail('shared-adapter-optimized-pointer', 'same physical independent adapter and first optimized dispatch case',
              {'candidateRva': candidate, 'independentRva': shared['pointer'] - image.pe.image_base})
    return {'independentPhysicalAdapterJoinedToOptimizedCase': True,
            'concreteClosedMethodInfoRetainedAsCondition': True,
            'objectArgumentsSubstitutedForConcreteTypes': False, 'actualRuntimeSelectionProved': False}


def _cached_getter_target(image: Any, selected: Any, target: list, wrapper: str, original: str) -> int:
    image.validate_method_row(target, label=LABEL)
    method = image.metadata.methods[target[0]]
    if (target[1:3] != [wrapper, 'get___instance'] or method.flags & 0x10 or method.parameter_count
            or selected.type_name(method.return_type) != original):
        _fail('original-cached-getter-join', 'same instance cached getter returning the original reference', target)
    return target[3]


def _child_contexts(image: Any, c: dict, deps: dict, entries: Any, selected: Any) -> dict:
    parent = deps['parent']['records']['moveTo']
    child = c['records']['subSpeed']
    members = [m for m in parent['members'] if m['declaredType'] == child['runtimeTypeName']]
    rows = c['childReadValueContexts']
    if len(rows) != len(members) or not members:
        _fail('child-context-coverage', 'every current parent SubSpeed source', len(rows))
    key_pointer = selected.type_pointer(child['adapterRegistrationFlow']['key']['typeIndex'])
    for row, member in zip(rows, members, strict=True):
        usage = row['usage']
        if (row['fieldName'] != member['fieldName'] or row['sourceCall'] != member['sourceCall']
                or usage['instructionRva'] != member['sourceContextInstructionRva']
                or usage['tag'] != 6 or not usage['instructionHex'].startswith('488B15')
                or usage['methodSpec'][0] != deps['readValue']['declaration'][0]
                or usage['classArguments'] != [] or usage['methodArguments'] != [child['runtimeTypeName']]):
            _fail('child-closed-original-context', 'same current child call and original SubSpeed argument', row)
        validate_typed_usage_context(image, usage, label=LABEL)
        arguments = image.instantiations.resolve(usage['methodSpec'][2]).arguments
        if len(arguments) != 1 or arguments[0].type_pointer_va != key_pointer:
            _fail('child-original-key-pointer', 'exact same original type pointer as eager key', usage)
        call = row['sourceCall']
        raw = image.pe.bytes_at_va(image.pe.image_base + call['rva'], 5)
        target = call['rva'] + 5 + struct.unpack_from('<i', raw, 1)[0]
        if raw[0] != 0xe8 or target != call['targetRva'] or target != deps['readValue']['calledEntryRva']:
            _fail('child-actual-shared-call', 'same actual physical ReadValue input target', call)
    validate_generic_contexts(image, [deps['readValue']['readValueContext'], deps['provider']['providerContext']], label=LABEL)
    context = validate_read_value_context(image, deps['readValue']['readValueContext'],
                                         deps['provider']['providerContext'], entries, fail=_fail)
    return {'fields': [r['fieldName'] for r in rows], 'sameOriginalTypeAsEagerKey': True,
            'ownedReadValueProviderAndFormatterContext': context,
            'physicalReadValueNamedIdentityProved': False, 'actualProviderSelectionProved': False}


def _validate_image(image: Any, c: dict, deps: dict) -> dict:
    selected = NativeReferenceContext(image)
    entries = GenericEntries(image)
    composition = c['composition']
    if (len(composition['registrations']) != 2 or len(composition['interfaces']) != 2
            or len(composition['genericContexts']) != 1
            or composition['genericContexts'][0]['definition'] != deps['callback']['callbackSpecification']['typeDefinition']):
        _fail('composition-coverage', 'both current original/wrapper pairs', composition)
    validate_registered_formatter_composition(image, composition, label=LABEL)
    eager = c['eagerOwnerMethod']
    image.validate_method_row(eager, label=LABEL)
    if eager[1:3] != ['Beyond.MemoryPack.MemoryPackGeneratedInit_Gameplay_Beyond', 'InitEager']:
        _fail('eager-method-owner', 'actual named generated InitEager owner', eager)
    eager_end = image.mapper.pdata_function_extents(image.pe).get(image.pe.image_base + eager[3])
    wrapper_summary = wrapper_routes._validate_image(image, deps['formatterRoutes'],
        {k: deps[k] for k in ('parent', 'subSpeed', 'lifecycle')})
    context = validate_conversion_context(image, composition['genericContexts'][0], entries, fail=_fail)
    shared_deserialize = _shared_deserialize_join(image, entries, deps)
    result = {}
    for kind, source_key in (('moveTo', 'parent'), ('subSpeed', 'subSpeed')):
        record = c['records'][kind]
        source = deps[source_key]['records'][kind]
        for key in ('runtimeTypeDefinition', 'runtimeTypeName', 'wrapperTypeDefinition', 'wrapperTypeName'):
            if record[key] != source[key]:
                _fail('original-source-record', source[key], record[key])
        for role in ('runtime', 'wrapper'):
            if image.type_name(record[role + 'TypeDefinition']) != record[role + 'TypeName']:
                _fail('original-type-definition', record[role + 'TypeName'], record[role + 'TypeDefinition'])
        original, wrapper = record['runtimeTypeName'], record['wrapperTypeName']
        flow = record['adapterRegistrationFlow']
        registrations = [r for r in composition['registrations'] if r['originalType'] == original]
        interfaces = [r for r in composition['interfaces'] if r['originalType'] == original]
        if len(registrations) != 1 or len(interfaces) != 1:
            _fail('original-composition-bijection', 'one owned registration/interface per record', original)
        registration, interface = registrations[0], interfaces[0]
        if (flow['originalType'] != original or flow['wrapperType'] != wrapper
                or flow['allocation']['typeIndex'] != registration['adapterTypeIndex']
                or flow['key']['typeIndex'] != registration['keyTypeIndex']
                or flow['constructor']['methodSpecIndex'] != registration['constructorMethodSpecIndex']):
            _fail('eager-registered-pair', 'identical current allocation, original key and closed constructor', flow)
        window = flow['window']
        if eager_end is None or not eager[3] <= window['startRva'] < window['endRva'] <= eager_end - image.pe.image_base:
            _fail('eager-block-owner', 'selected complete block inside actual named eager method', window)
        validate_eager_wrap_registration(image, flow, label=LABEL)
        shared = entries.resolve(flow['constructor']['methodSpec'][0], ['object', 'object'], [])
        if (json.loads(json.dumps(shared)) != c['sharedConstructorEntry']
                or shared['pointer'] - image.pe.image_base != flow['constructorThunk']['sharedTargetRva']
                or shared['methodDefinitionIndices'] != [flow['constructor']['methodSpec'][0]]):
            _fail('concrete-thunk-shared-body', 'same independent physical constructor with concrete context retained', shared)
        callback = validate_adapter_callback_signature(image, deps['callback']['callbackSpecification'], flow,
            deps['readValue']['readValueContext']['entries'][2]['methodSpec'][0], fail=_fail)
        td = image.metadata.types[record['wrapperTypeDefinition']]
        section = image.metadata.sections['interfaceOffsets']
        at, length = section.offset + td.interface_offsets_start * 8, td.interface_offsets_count * 8
        if not section.offset <= at <= section.offset + section.size - length:
            _fail('original-interface-range', 'bounded complete owned interface table', [at, length])
        pairs = [{'ordinal': n, 'typeIndex': idx, 'offset': off, 'typeName': selected.type_name(idx)}
                 for n, (idx, off) in enumerate(struct.iter_unpack('<ii', image.metadata.buf[at:at + length]))]
        if (pairs != record['interfacePairs'] or td.flags != record['wrapperMetadataFlags']
                or td.flags & 0x80 or selected.is_value_type(original) or selected.is_value_type(wrapper)
                or interface['getValueMethodIndex'] != record['getterMethod'][0]
                or interface['formatterDeserializeMethodIndex'] != deps['formatterRoutes']['records'][kind]['deserializeMethod'][0]):
            _fail('original-typed-wrapper', 'same concrete reference wrapper, owned getter and current formatter', record)
        getter = record['getterMethod']
        image.validate_method_row(getter, label=LABEL)
        method = image.metadata.methods[getter[0]]
        if (getter[1:3] != [wrapper, 'GetValue'] or method.flags & 0x10 or method.parameter_count
                or method.declaring_type != td.index or selected.type_name(method.return_type) != original
                or record['getterEntry']['program'][0][0] != getter[3]):
            _fail('original-getter-declaration', 'owned instance GetValue returning the exact original reference', getter)
        if kind == 'moveTo':
            target = deps['lifecycle']['records'][kind]['getterMethod']
            target_rva = _cached_getter_target(image, selected, target, wrapper, original)
            if record['getterEntryKind'] != 'tail-to-cached-instance':
                _fail('original-cached-getter-join', 'same current cached-instance getter', target)
            getter_transfer = transfers.validate_getter_entry(image, record['getterEntry'],
                kind=record['getterEntryKind'], target_rva=target_rva, field_offset=None, fail=_fail)
        else:
            field = selected.field(wrapper + '::__instance')
            if field != (wrapper, original, 16) or record['getterEntryKind'] != 'direct-instance-return':
                _fail('original-direct-getter-field', 'metadata-owned original instance field', field)
            getter_transfer = transfers.validate_getter_entry(image, record['getterEntry'],
                kind=record['getterEntryKind'], target_rva=None, field_offset=field[2], fail=_fail)
        interface_transfer = transfers.validate_repeated_interface_lookup(
            image, record['interfaceConversionProgram'], deps['reference']['conversionPrograms']['interfaceConversion'],
            ordinal=record['typedInterfaceOrdinal'], pairs=pairs, type_index=interface['interfaceTypeIndex'],
            getter_rva=getter[3], fail=_fail)
        formatter_transfer = validate_formatter_dispatch(image, deps['reference']['conversionPrograms']['formatterDispatch'],
            [deps['formatterRoutes']['records'][kind]['deserializeMethod'][3]], fail=_fail)
        result[kind] = {'originalType': original, 'wrapperType': wrapper,
            'staticOriginalAdapterRegistrationProved': True, 'concreteConstructorContextRetained': True,
            'declaredOriginalAdapterCallback': callback, 'getterEntry': getter_transfer,
            'typedInterfaceLookup': interface_transfer, 'nestedFormatterFallback': formatter_transfer,
            'wrapperReaderRoute': wrapper_summary[kind]['deserializeTail'],
            'originalAdapterProviderSelectionProved': False}
    return {'records': result, 'ownedAdapterContext': context, 'sharedDeserializeJoin': shared_deserialize,
            'childReadValueJoin': _child_contexts(image, c, deps, entries, selected),
            'eagerExecutionObserved': False, 'allocationAndConstructorEffectsProved': False,
            'providerDictionaryEffectsProved': False, 'finalAccumulatedInstanceStateProved': False}


def validate_current_native_contract(*, gameassembly: Path | None = None, metadata: Path | None = None) -> dict:
    c = _contract()
    native = c['nativeInputs']
    pair = check_installed_native_inputs(native['GameAssembly.dll'], native['global-metadata.dat'],
                                         gameassembly=gameassembly, metadata=metadata)
    if pair.status != 'validated':
        return {'status': pair.status, 'detail': pair.detail, 'nativeInputs': native}
    unity = Path(pair.gameassembly).parent / 'UnityPlayer.dll'
    def unity_matches():
        return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == native['UnityPlayer.dll']
    if not unity_matches():
        return {'status': 'mismatched' if unity.is_file() else 'missing', 'detail': 'UnityPlayer.dll differs', 'nativeInputs': native}
    deps = {k: _dependency(k, n) for k, n in c['dependencies'].items()}
    if any(d['nativeInputs'] != native for d in deps.values()):
        _fail('dependency-build', native, {k: d['nativeInputs'] for k, d in deps.items()})
    paths = {CONTRACT_PATH, *(CONTRACTS_DIR / n for n in c['dependencies'].values()),
             *_package_import_closure(Path(__file__)), NATIVE_MAPPER_PATH, METADATA_HELPER_PATH,
             Path(pair.gameassembly), Path(pair.metadata), unity}
    sources = [_fingerprint(p) for p in sorted(paths)]
    try:
        summary = _validate_image(open_native_image(pair.gameassembly, pair.metadata), c, deps)
    except ValueError as error:
        if isinstance(error, CensusGateError):
            raise
        _fail('native-original-adapters', 'current closed adapters and complete concrete conversion routes', str(error))
    for row in sources:
        actual = _fingerprint(Path(row['path']))
        if actual != row:
            _fail('source-drift', row, actual)
    after = check_installed_native_inputs(native['GameAssembly.dll'], native['global-metadata.dat'],
                                          gameassembly=pair.gameassembly, metadata=pair.metadata)
    if after.status != 'validated' or not unity_matches():
        return {'status': after.status if after.status != 'validated' else 'mismatched',
                'detail': 'native inputs changed during validation', 'nativeInputs': native}
    return {'status': 'validated', 'nativeInputs': native, 'proofSources': sources, 'summary': summary,
            'evidenceBoundary': c['evidenceBoundary'], 'actualProviderSelectionProved': False,
            'wholeActionAdmitted': False, 'wholeRootAdmitted': False, 'runtimeExecutionKnown': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    report = args.report.resolve()
    if not report.is_relative_to(Path(__file__).resolve().parents[3] / 'reports'):
        parser.error('--report must be inside reports')
    result = validate_current_native_contract(gameassembly=args.gameassembly, metadata=args.metadata)
    if result['status'] != 'validated':
        print(json.dumps({'status': result['status'], 'detail': result.get('detail'), 'reportPreserved': report.as_posix()}))
        raise SystemExit(1)
    result.update(schema='endfield.buff-move-to-original-adapters-validation.v1',
                  checkedAtUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'originalAdapterPairs': len(result['summary']['records']),
                      'report': report.as_posix()}), flush=True)


if __name__ == '__main__':
    main()

"""Reference ABI, null marker and conditional conversion below list admission."""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.formatter_composition import validate_registered_formatter_composition
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack.reference_nullable_sources import (
    validate_reference_adapter_abi, validate_buffered_null_reference)
from scripts.game_data.memorypack.reference_conversion_sources import (
    validate_conversion_context, validate_nonnull_transfer,
    validate_formatter_dispatch, validate_interface_conversion)

LABEL = 'buffTimelineReference'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_timeline_reference_native.json'
SCHEMA = 'endfield.buff-timeline-reference-native-contract.v2'
SCOPE = 'buffered-null-and-conditional-reference-conversion'


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
    entries = contract['sharedEntries']
    if (len(entries) != 2 or {r['method'][2] for r in entries} != {'Deserialize','DeserializeNotNull'}
            or any(r['classArguments'] != ['object','object'] or r['methodArguments'] != []
                   or r['nonnull'] != (r['method'][2] == 'DeserializeNotNull') for r in entries)):
        _fail('shared-entry-scope', 'one independent Object/Object entry per selected ABI', entries)
    return contract


def _validate_image(image: Any, contract: dict) -> dict:
    static, _ = read_reviewed_contract(CONTRACTS_DIR / contract['dependencies']['staticComposition'],
        schema='endfield.buff-timeline-static-composition-native-contract.v1',
        status='exact-current-build', label=LABEL)
    source, _ = read_reviewed_contract(CONTRACTS_DIR / contract['dependencies']['readerLayout'],
        schema='endfield.buff-timeline-element-sources-native-contract.v1',
        status='exact-current-build', label=LABEL)
    if any(c['nativeInputs'] != contract['nativeInputs'] for c in (static, source)):
        _fail('dependency-build', contract['nativeInputs'], [c['nativeInputs'] for c in (static, source)])
    validate_registered_formatter_composition(image, static['composition'], label=LABEL)
    selected = NativeReferenceContext(image)
    bindings = [[r['originalType'],r['wrapperType']] for r in static['composition']['registrations']]
    if (len(bindings) != 2
            or any(selected.is_value_type(n) or n not in selected.index.types for pair in bindings for n in pair)
            or {r['runtimeTypeName'] for r in source['records'].values()} != {p[0] for p in bindings}):
        _fail('concrete-reference-bindings', 'two source-owned reference pairs', bindings)
    offsets = source['readerFieldsUnboxedOffsets']
    if (set(offsets) != {'currentPtr','bufferLength','advancedCount','consumed'}
            or image.type_name(source['readerTypeDefinition']) != 'MemoryPack.MemoryPackReader'
            or not selected.is_value_type('MemoryPack.MemoryPackReader')
            or offsets != {n:selected.field('MemoryPack.MemoryPackReader::'+n)[2]-16 for n in offsets}
            or len(set(offsets.values())) != 4):
        _fail('reader-layout', 'four distinct metadata-owned unboxed fields', offsets)
    entries = GenericEntries(image)
    for row in contract['sharedEntries']:
        actual = entries.resolve(row['method'][0], row['classArguments'], row['methodArguments'])
        if json.loads(json.dumps(actual)) != row['registration']:
            _fail('shared-physical-registration', row['registration'], actual)
        validate_reference_adapter_abi(image, row['method'], nonnull=row['nonnull'], fail=_fail)
    adapter = next(r for r in contract['sharedEntries'] if not r['nonnull'])
    if adapter['registration']['pointer'] - image.pe.image_base != contract['nullProgram']['window']['startRva']:
        _fail('null-program-entry', adapter['registration']['pointer'], contract['nullProgram']['window'])
    null = validate_buffered_null_reference(image, contract['nullProgram'], offsets, fail=_fail)
    programs = contract['conversionPrograms'];calls = contract['conversionCalls']
    helper = next(r for r in contract['sharedEntries'] if r['nonnull'])
    helper_rva = helper['registration']['pointer'] - image.pe.image_base
    for key in ('nonnull','nullWrapperOutput'):
        if programs[key]['codeWindows'][0]['startRva'] != helper_rva:
            _fail('nonnull-physical-entry', helper_rva, programs[key]['codeWindows'][0])
    for key in ('formatterDispatch','interfaceConversion'):
        if calls[key] != programs[key]['codeWindows'][0]['startRva']:
            _fail('conversion-call-entry', calls[key], programs[key]['codeWindows'][0])
    pointers = [r['formatterMethod'][3] for r in static['wrapperConversions']]
    getters = [r['getterMethod'][3] for r in static['wrapperConversions']]
    dispatch = validate_formatter_dispatch(image, programs['formatterDispatch'], pointers, fail=_fail)
    conversion = validate_interface_conversion(image, programs['interfaceConversion'], getters, fail=_fail)
    if dispatch['classPrepareHelperRva'] != conversion['classPrepareHelperRva']:
        _fail('conversion-class-helper', dispatch['classPrepareHelperRva'], conversion['classPrepareHelperRva'])
    contexts = [r for r in static['composition']['genericContexts']
                if r['typeName'] == helper['method'][1] and not r['isMethod']]
    if len(contexts) != 1:
        _fail('conversion-owned-context', 'one source-owned adapter context', len(contexts))
    context = validate_conversion_context(image, contexts[0], entries, fail=_fail)
    interfaces = _interface_ordinals(image, contract['interfacePairs'], static, selected,
                                    conversion['interfaceOrdinal'])
    transfers = {key:validate_nonnull_transfer(image, programs[key], calls,
                    null_wrapper=empty, fail=_fail)
                 for key, empty in (('nonnull',False),('nullWrapperOutput',True))}
    return {'referenceAbiDeclarations':2, 'conditionalConcreteArguments':bindings,
            'bufferedNullProgram':null, 'staticConversionContext':context,
            'selectedConcreteInterfaces':interfaces, 'formatterDispatch':dispatch,
            'interfaceConversion':conversion, 'conditionalTransferPrograms':transfers}


def _interface_ordinals(image: Any, expected_rows: list, static: dict,
                       selected: Any, ordinal: int) -> list:
    """Actual ordered table pairs select the typed interface, not the first pair."""
    by_wrapper = {r['wrapperType']:r for r in expected_rows}
    declarations = static['composition']['interfaces']
    if (len(by_wrapper) != len(expected_rows)
            or set(by_wrapper) != {r['wrapperType'] for r in declarations}):
        _fail('conversion-wrapper-bijection', 'one ordered interface table per wrapper', expected_rows)
    result = []
    for row in declarations:
        owner = image.metadata.types[row['wrapperDefinition']]
        section = image.metadata.sections['interfaceOffsets']
        offset = section.offset + owner.interface_offsets_start * 8
        size = owner.interface_offsets_count * 8
        if not section.offset <= offset <= section.offset + section.size - size:
            _fail('conversion-interface-table-range', 'bounded ordered table', [offset,size])
        actual = [{'ordinal':n,'typeIndex':index,'typeName':selected.type_name(index),'offset':value}
                  for n,(index,value) in enumerate(struct.iter_unpack('<ii',image.metadata.buf[offset:offset+size]))]
        if actual != by_wrapper[row['wrapperType']]['pairs'] or not 0 <= ordinal < len(actual):
            _fail('conversion-interface-table', by_wrapper[row['wrapperType']]['pairs'], actual)
        match = actual[ordinal]
        if (match['typeIndex'] != row['interfaceTypeIndex'] or match['offset'] != row['interfaceOffset']
                or any(p['typeIndex'] == match['typeIndex'] for p in actual[:ordinal])):
            _fail('conversion-interface-ordinal', 'selected original interface after nonmatches', actual)
        result.append({'wrapperType':row['wrapperType'],'ordinal':ordinal,
                       'vtableSlot':match['offset'],'originalType':row['originalType']})
    return result


def validate_current_native_contract(*, gameassembly: Path | None = None,
                                      metadata: Path | None = None) -> dict:
    contract = _contract(); pins = contract['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return {'status':gate.status, 'detail':gate.detail, 'nativeInputs':pins, 'scope':SCOPE}
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    def unity_matches() -> bool:
        return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == pins['UnityPlayer.dll']
    if not unity_matches():
        return {'status':'mismatched' if unity.is_file() else 'missing',
                'detail':'UnityPlayer.dll missing or mismatched', 'nativeInputs':pins, 'scope':SCOPE}
    try:
        summary = _validate_image(open_native_image(gate.gameassembly, gate.metadata), contract)
    except ValueError as error:
        if isinstance(error, CensusGateError):
            raise
        _fail('native-reference-flow', 'current reference ABI, null path and conditional conversions', str(error))
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated' or not unity_matches():
        return {'status':after.status if after.status != 'validated' else 'mismatched',
                'detail':'native inputs changed during validation', 'nativeInputs':pins, 'scope':SCOPE}
    return {'status':'validated', 'scope':SCOPE, 'nativeInputs':pins, 'summary':summary,
            'positiveListAdmitted':False, 'wholeRootAdmitted':False, 'runtimeMeaningExact':False,
            'evidenceBoundary':contract['evidenceBoundary']}

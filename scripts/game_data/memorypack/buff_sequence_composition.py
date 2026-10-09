"""Concrete Sequence adapter/wrapper registration and conditional nested calls."""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.formatter_composition import validate_registered_formatter_composition
from scripts.game_data.il2cpp.formatter_registration import (
    validate_eager_wrap_registration, validate_wrapper_formatter_registration, validate_reference_wrapper_forwarding)
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack.reference_conversion_sources import (
    validate_conversion_context, validate_formatter_dispatch, validate_interface_conversion)
from scripts.game_data.memorypack import buff_sequence as sequence

LABEL = 'buffSequenceComposition'
SCHEMA = 'endfield.buff-sequence-static-composition-native-contract.v1'
SCOPE = 'static-sequence-registration-and-nested-fallback-only'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_sequence_static_composition_native.json'


def _fail(check: str, expected: Any, actual: Any) -> None:
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, scope=SCOPE)
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _contract() -> dict:
    c, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status='exact-current-build', label=LABEL)
    if (c.get('scope') != SCOPE or len(c['composition']['registrations']) != 1
            or c['composition']['registrations'][0]['originalType'] != sequence.TYPE_NAME):
        _fail('sequence-scope', 'one independently proved concrete Sequence composition', c.get('scope'))
    return c


def _owned_window(image: Any, method: list, window: dict) -> None:
    image.validate_method_row(method, label=LABEL)
    start = image.pe.image_base + method[3]
    end = image.mapper.pdata_function_extents(image.pe).get(start)
    if end is None or not method[3] <= window['startRva'] < window['endRva'] <= end - image.pe.image_base:
        _fail('registration-window-owner', 'complete selected block inside the named physical method', [method, window])


def _validate_image(image: Any, c: dict) -> dict:
    event, _ = read_reviewed_contract(CONTRACTS_DIR / c['dependencies']['event'],
        schema='endfield.buff-shared-event-maps-native-contract.v1', status='exact-current-build', label=LABEL)
    reference, _ = read_reviewed_contract(CONTRACTS_DIR / c['dependencies']['reference'],
        schema='endfield.buff-timeline-reference-native-contract.v2', status='exact-current-build', label=LABEL)
    if event['nativeInputs'] != c['nativeInputs'] or reference['nativeInputs'] != c['nativeInputs']:
        _fail('dependency-build', 'all dependencies describe the selected build', c['nativeInputs'])
    sequence.validate_selected_source(image, event)
    source = json.loads((CONTRACTS_DIR / event['sequence']['dependency']).read_bytes())[event['sequence']['section']]
    original = sequence.TYPE_NAME; wrapper = source['wrapperName']; composition = c['composition']
    if (len(composition['interfaces']) != 1 or composition['registrations'][0]['wrapperType'] != wrapper
            or composition['interfaces'][0]['originalType'] != original or composition['interfaces'][0]['wrapperType'] != wrapper):
        _fail('source-wrapper-bijection', [original, wrapper], composition)
    validate_registered_formatter_composition(image, composition, label=LABEL)
    entries = GenericEntries(image); selected = NativeReferenceContext(image)
    adapter = c['adapterRegistrationFlow']; registration = composition['registrations'][0]
    if (adapter['originalType'] != original or adapter['wrapperType'] != wrapper
            or adapter['allocation']['typeIndex'] != registration['adapterTypeIndex']
            or adapter['key']['typeIndex'] != registration['keyTypeIndex']
            or adapter['constructor']['methodSpecIndex'] != registration['constructorMethodSpecIndex']):
        _fail('adapter-registration-source', 'same concrete allocation, key and constructor context', adapter)
    _owned_window(image, c['eagerOwnerMethod'], adapter['window'])
    validate_eager_wrap_registration(image, adapter, label=LABEL)
    shared = c['sharedConstructorEntry']
    if (shared['classArguments'] != ['object','object'] or shared['methodArguments'] != []
            or shared['requestedConcreteArguments'] != [original,wrapper] or shared['conditionalInflationOnly'] is not True
            or shared['definition'] != adapter['constructor']['methodSpec'][0]):
        _fail('shared-constructor-context', 'independent Object/Object entry with the concrete context retained', shared)
    actual = entries.resolve(shared['definition'], shared['classArguments'], shared['methodArguments'])
    if (json.loads(json.dumps(actual)) != shared['registration']
            or actual['pointer'] - image.pe.image_base != adapter['constructorThunk']['sharedTargetRva']):
        _fail('shared-constructor-physical-entry', 'thunk target equals independently registered shared entry', actual)
    conversion = c['wrapperConversion']; interface = composition['interfaces'][0]
    if (conversion['originalType'] != original or conversion['wrapperType'] != wrapper
            or conversion['sourceMethod'] != source['methods'][0] or conversion['formatterMethod'] != source['methods'][1]
            or interface['wrapperDefinition'] != source['wrapperTypeDefinition']
            or conversion['getterMethod'][0] != interface['getValueMethodIndex']
            or conversion['formatterMethod'][0] != interface['formatterDeserializeMethodIndex']):
        _fail('source-forwarding-join', 'same independently proved Sequence source and typed interface', conversion)
    validate_reference_wrapper_forwarding(image, conversion, label=LABEL)
    flow = c['wrapperRegistrationFlow']
    if (flow['wrapperType'] != wrapper or flow['formatterType'] != conversion['formatterMethod'][1]
            or flow['wrapperDefinition'] != interface['wrapperDefinition'] or flow['formatterDefinition'] != interface['formatterDefinition']
            or c['wrapperRegistrationMethod'][1:3] != [wrapper,'RegisterFormatter']):
        _fail('wrapper-formatter-registration', 'same concrete wrapper formatter', flow)
    _owned_window(image, c['wrapperRegistrationMethod'], flow['window'])
    validate_wrapper_formatter_registration(image, flow, label=LABEL)
    td = image.metadata.types[interface['wrapperDefinition']]
    flags = c['wrapperMetadataFlags']
    if (flags != {'definition': td.index, 'wrapperType': wrapper, 'flags': td.flags}
            or td.flags & 0x80 or selected.is_value_type(wrapper) or selected.is_value_type(original)):
        _fail('concrete-wrapper-attributes', 'reference wrapper with abstract mask clear', flags)
    section = image.metadata.sections['interfaceOffsets']; at = section.offset + td.interface_offsets_start * 8
    length = td.interface_offsets_count * 8
    if not section.offset <= at <= section.offset + section.size - length:
        _fail('interface-range', 'bounded complete owned interface table', [at,length])
    pairs = [{'ordinal': n, 'typeIndex': idx, 'offset': off, 'typeName': selected.type_name(idx)}
        for n,(idx,off) in enumerate(struct.iter_unpack('<ii', image.metadata.buf[at:at+length]))]
    if pairs != c['interfacePairs'] or len(pairs) < 2 or pairs[1]['typeIndex'] != interface['interfaceTypeIndex']:
        _fail('typed-interface-ordinal', 'same typed original interface at the separately proved ordinal one', pairs)
    context = next(r for r in composition['genericContexts'] if r['typeName'] == 'Beyond.MemoryPack.GenericMemoryPackFormatter`2' and not r['isMethod'])
    owned_context = validate_conversion_context(image, context, entries, fail=_fail)
    dispatch = validate_formatter_dispatch(image, reference['conversionPrograms']['formatterDispatch'],
        [conversion['formatterMethod'][3]], fail=_fail)
    getter = validate_interface_conversion(image, reference['conversionPrograms']['interfaceConversion'],
        [conversion['getterMethod'][3]], fail=_fail)
    return {'originalType': original, 'wrapperType': wrapper, 'staticAdapterFlows': 1,
        'constructorThunks': 1, 'wrapperRegistrations': 1, 'typedWrapperConversions': 1,
        'ownedAdapterContext': owned_context, 'nestedFormatterFallback': dispatch,
        'typedGetterFallback': getter, 'wrapperMetadataMaskClear': True,
        'runtimeInitializationObserved': False, 'sourceCursorCompositionProved': False}


def validate_current_native_contract(*, gameassembly: Path | None = None,
                                     metadata: Path | None = None) -> dict:
    c = _contract(); pins = c['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'], gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return {'status': gate.status, 'detail': gate.detail, 'scope': SCOPE, 'nativeInputs': pins}
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    def unity_matches(): return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == pins['UnityPlayer.dll']
    if not unity_matches():
        return {'status': 'mismatched' if unity.is_file() else 'missing', 'detail': 'UnityPlayer.dll missing or mismatched', 'scope': SCOPE, 'nativeInputs': pins}
    try:
        summary = _validate_image(open_native_image(gate.gameassembly, gate.metadata), c)
    except ValueError as error:
        if isinstance(error, CensusGateError): raise
        _fail('native-sequence-composition', 'current concrete identity and complete static programs', str(error))
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'], gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated' or not unity_matches():
        return {'status': after.status if after.status != 'validated' else 'mismatched',
            'detail': 'native inputs changed during Sequence composition validation', 'scope': SCOPE, 'nativeInputs': pins}
    return {'status': 'validated', 'scope': SCOPE, 'nativeInputs': pins, 'summary': summary,
        'positiveListAdmitted': False, 'wholeRootAdmitted': False, 'runtimeMeaningExact': False,
        'evidenceBoundary': c['evidenceBoundary']}

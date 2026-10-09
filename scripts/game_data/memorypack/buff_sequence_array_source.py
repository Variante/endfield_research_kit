"""Complete selected Sequence reference-array source paths, below child admission."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import (
    validate_generic_contexts, validate_typed_usage_context)
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import buff_sequence as sequence
from scripts.game_data.memorypack import buff_timeline_read_value as read_value
from scripts.game_data.memorypack import buff_timeline_source_wrappers as wrappers
from scripts.game_data.memorypack.array_reference_sources import (
    validate_read_array_context, validate_sequence_array_programs)
from scripts.game_data.memorypack.buffered_reference_wrappers import validate_fast_reference_barrier

LABEL = 'buffSequenceArraySource'
SCHEMA = 'endfield.buff-sequence-array-source-native-contract.v1'
SCOPE = 'selected-buffered-sequence-array-source-control-only'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_sequence_array_source_native.json'


def _fail(check: str, expected: Any, actual: Any) -> None:
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, scope=SCOPE)
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _contract() -> dict:
    c, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status='exact-current-build', label=LABEL)
    if (c.get('scope') != SCOPE or set(c['dependencies']) != {'event','readValue','sourceWrappers'}
            or set(c['programs']) != {'ff','nullArray','emptyArray','singleElement','twoElements'}
            or len(c['genericContexts']) != 2):
        _fail('array-source-scope', 'both ReadArray contexts and five complete selected source paths', c.get('scope'))
    return c


def _validate_image(image: Any, c: dict) -> dict:
    schemas = {'event': 'endfield.buff-shared-event-maps-native-contract.v1',
        'readValue': read_value.SCHEMA, 'sourceWrappers': wrappers.SCHEMA}
    deps = {k: read_reviewed_contract(CONTRACTS_DIR / c['dependencies'][k], schema=s,
        status='exact-current-build', label=LABEL)[0] for k,s in schemas.items()}
    if any(d['nativeInputs'] != c['nativeInputs'] for d in deps.values()):
        _fail('dependency-build', 'all dependencies describe the selected native build', c['nativeInputs'])
    event = deps['event']; sequence.validate_selected_source(image, event)
    declaration = event['sequence']
    source = json.loads((CONTRACTS_DIR / declaration['dependency']).read_bytes())[declaration['section']]
    if c['sourceMethod'] != source['methods'][0]:
        _fail('named-source-owner', 'same independently authenticated Sequence source', c['sourceMethod'])
    result = read_value._validate_image(image, deps['readValue'])
    selected = NativeReferenceContext(image)
    if not selected.is_value_type('MemoryPack.MemoryPackReader'):
        _fail('reader-receiver', 'same unboxed Reader value type', c['readerFieldsUnboxedOffsets'])
    offsets = c['readerFieldsUnboxedOffsets']
    if (set(offsets) != {'currentPtr','bufferLength','advancedCount','consumed','totalLength'}
            or offsets != {n: selected.field('MemoryPack.MemoryPackReader::'+n)[2]-16 for n in offsets}
            or any(type(n) is not int or not 0 <= n < 128 for n in offsets.values())
            or len(set(offsets.values())) != 5):
        _fail('reader-layout', 'five distinct bounded metadata-owned unboxed Reader fields', offsets)
    fields = c['originalFieldOffsets']
    expected = {k: declaration['runtimeType']['fieldOffsets'][n] for k,n in (
        ('actionData','actionData'), ('guard','onlyExecuteWhenSourceIsGuard'),
        ('main','onlyExecuteWhenSourceIsMainChar'))}
    if fields != expected:
        _fail('original-field-layout', 'same metadata-owned original array and ordered terminal flags', fields)
    wrapper = source['wrapperName']; original = sequence.TYPE_NAME
    actual_instance = selected.field(wrapper+'::__instance')
    if actual_instance != (wrapper,original,16):
        _fail('wrapper-original-instance', 'same named original reference at the observed wrapper offset', actual_instance)
    td = image.metadata.types[declaration['runtimeType']['typeDefinition']]
    array_fields = [f for f in image.metadata.fields_for(td) if image.metadata.string(f.name_index) == 'actionData']
    if len(array_fields) != 1:
        _fail('array-field-owner', 'one exact original actionData field', len(array_fields))
    raw = image.pe.bytes_at_va(selected.type_pointer(array_fields[0].type_index),16)
    if raw[10:12] != b'\x1d\x00':
        _fail('concrete-array-field', 'undecorated SZARRAY of a named reference class', raw.hex())
    element_pointer = int.from_bytes(raw[:8],'little')
    element = image.pe.bytes_at_va(element_pointer,16)
    element_name = 'Beyond.Gameplay.Core.AbilityAction+AbilityActionData'
    if (element[10:12] != b'\x12\x00' or image.type_name(int.from_bytes(element[:8],'little')) != element_name
            or selected.is_value_type(element_name)):
        _fail('reference-element', 'same complete concrete original action reference type', element.hex())
    usage = c['readArrayUsage']
    if (usage['tag'] != 6 or usage['typeName'] != 'MemoryPack.MemoryPackReader'
            or usage['methodName'] != 'ReadArray' or usage['methodArguments'] != [element_name]):
        _fail('owned-read-array-usage', 'actual closed Reader.ReadArray usage for the original field element', usage)
    validate_typed_usage_context(image, usage, label=LABEL)
    validate_generic_contexts(image, c['genericContexts'], label=LABEL)
    context = validate_read_array_context(image, c['genericContexts'], usage, GenericEntries(image),
        element_pointer, result['ownedReadValueContext']['formatterDeserializeDefinition'], fail=_fail)
    provider_definition = c['genericContexts'][1]['entries'][3]['methodSpec'][0]
    if provider_definition != result['ownedReadValueContext']['providerMethodDefinition']:
        _fail('canonical-provider-declaration', 'same independently proved provider result signature', provider_definition)
    barrier_program = deps['sourceWrappers']['barrierProgram']
    barrier = validate_fast_reference_barrier(image, barrier_program, fail=_fail)
    for key,p in c['programs'].items():
        windows = [source['codeWindows'][0]] + ([barrier_program['codeWindows'][0]] if key == 'ff' else [])
        if p['codeWindows'] != windows or p['program'][0][0] != source['methods'][0][3]:
            _fail('source-program-window-owner', 'same complete source and independently owned FF barrier windows', key)
    calls = c['calls']
    if (set(calls) != {'emptyArray','arrayAllocation','getFormatter','classPrepare'}
            or calls['getFormatter'] != result['physicalFormatterProvider']['providerTransfer']['entryRva']
            or calls['classPrepare'] != deps['readValue']['calls']['classPrepare']):
        _fail('array-provider-physical-join', 'same proved actual provider and class-preparation helper', calls)
    programs = validate_sequence_array_programs(image, c['programs'], offsets, fields,
        calls, usage, barrier_program, fail=_fail)
    # This guard is independently tied to the actual barrier's disabled state.
    at,h = c['programs']['singleElement']['program'][111]; raw = bytes.fromhex(h)
    if at+7+int.from_bytes(raw[2:6],'little',signed=True) != barrier['disabledFlagRva']:
        _fail('array-field-barrier-state', 'same independently proved disabled barrier flag', [at,h])
    return {'originalType': original, 'elementType': element_name, 'ownedArrayContext': context,
        'completeSourcePrograms': programs,
        'physicalFormatterProviderReturn': 'proved-conditional',
        'physicalEmptyAndAllocationIdentity': 'unresolved',
        'runtimeContextInflation': 'conditional', 'originalChildCursorComposition': 'unresolved'}


def validate_current_native_contract(*, gameassembly: Path | None = None,
                                     metadata: Path | None = None) -> dict:
    c = _contract(); pins = c['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return {'status': gate.status, 'detail': gate.detail, 'scope': SCOPE, 'nativeInputs': pins}
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    def unity_matches(): return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == pins['UnityPlayer.dll']
    if not unity_matches():
        return {'status': 'mismatched' if unity.is_file() else 'missing',
            'detail': 'UnityPlayer.dll missing or mismatched', 'scope': SCOPE, 'nativeInputs': pins}
    try:
        summary = _validate_image(open_native_image(gate.gameassembly,gate.metadata), c)
    except ValueError as error:
        if isinstance(error,CensusGateError): raise
        _fail('native-array-source', 'complete current source/context/cursor/return joins', str(error))
    after = check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
        gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status != 'validated' or not unity_matches():
        return {'status': after.status if after.status != 'validated' else 'mismatched',
            'detail': 'native inputs changed during array source validation', 'scope': SCOPE, 'nativeInputs': pins}
    return {'status': 'validated', 'scope': SCOPE, 'nativeInputs': pins, 'summary': summary,
        'childSchemaAdmitted': False, 'positiveListAdmitted': False, 'wholeRootAdmitted': False,
        'runtimeMeaningExact': False, 'evidenceBoundary': c['evidenceBoundary']}

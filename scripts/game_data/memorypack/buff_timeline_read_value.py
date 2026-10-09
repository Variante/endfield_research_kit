"""Selected physical child ReadValue transfers; independent body identity open."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import buff_timeline_instance as instance
from scripts.game_data.memorypack import buff_timeline_element_sources as sources
from scripts.game_data.memorypack import buff_sequence_composition as sequence_composition
from scripts.game_data.memorypack import buff_formatter_provider as formatter_provider
from scripts.game_data.memorypack.buffered_reference_wrappers import validate_fast_reference_barrier
from scripts.game_data.memorypack.read_value_reference_sources import (
    validate_read_value_context, validate_read_value_transfer, validate_optimized_adapter_transfer)

LABEL = 'buffTimelineReadValue'
SCHEMA = 'endfield.buff-timeline-read-value-native-contract.v3'
SCOPE = 'selected-physical-read-value-and-inlined-adapter-transfer-only'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_timeline_read_value_native.json'


def _fail(check: str, expected: Any, actual: Any) -> None:
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, scope=SCOPE)
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _contract() -> dict:
    c, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status='exact-current-build', label=LABEL)
    if (c.get('scope') != SCOPE or set(c['programs']) != {'readValue','nonnull','nullWrapperOutput','ff'}
            or set(c['dependencies']) != {'instance','source','reference','sourceWrappers','sequenceComposition','formatterProvider'}):
        _fail('read-value-scope', 'outer helper and all three selected inline return paths', c.get('scope'))
    return c


def _validate_image(image: Any, c: dict) -> dict:
    schemas = {'instance': instance.SCHEMA, 'source': sources.SCHEMA,
        'reference': 'endfield.buff-timeline-reference-native-contract.v2',
        'sourceWrappers': 'endfield.buff-timeline-source-wrappers-native-contract.v1',
        'sequenceComposition': sequence_composition.SCHEMA,
        'formatterProvider': formatter_provider.SCHEMA}
    deps = {k: read_reviewed_contract(CONTRACTS_DIR / c['dependencies'][k], schema=s,
        status='exact-current-build', label=LABEL)[0] for k, s in schemas.items()}
    if any(d['nativeInputs'] != c['nativeInputs'] for d in deps.values()):
        _fail('dependency-build', 'all dependencies describe the selected native inputs', c['nativeInputs'])
    # These are newly joined physical/context dependencies, not root admission.
    source_result = sources._validate_image(image, deps['source'])
    instance_result = instance._validate_image(image, deps['instance'])
    sequence_result = sequence_composition._validate_image(image, deps['sequenceComposition'])
    provider_result = formatter_provider._validate_image(image, deps['formatterProvider'])
    entries = GenericEntries(image)
    read_context = c['readValueContext']
    provider = next(r for r in deps['instance']['methodContexts'] if r['typeName'] == 'MemoryPack.MemoryPackFormatterProvider')
    validate_generic_contexts(image, [read_context, provider], label=LABEL)
    context = validate_read_value_context(image, read_context, provider, entries, fail=_fail)
    m = image.metadata.methods[read_context['definition']]
    declaration = [m.index, image.type_name(m.declaring_type), image.metadata.string(m.name_index)]
    if declaration != c['declaration']:
        _fail('method-declaration', 'same metadata declaration, without named physical body claim', declaration)
    independent = c['independentEntry']
    if independent['classArguments'] != [] or independent['methodArguments'] != ['object']:
        _fail('independent-entry-selection', 'independent closed Object registration', independent)
    actual = entries.resolve(m.index, independent['classArguments'], independent['methodArguments'])
    if json.loads(json.dumps(actual)) != independent['registration']:
        _fail('independent-entry-registration', independent['registration'], actual)
    physical_match = actual['pointer'] - image.pe.image_base == c['calledEntryRva']
    if physical_match != c['physicalEntryMatchedIndependentObject']:
        _fail('physical-entry-comparison', c['physicalEntryMatchedIndependentObject'], physical_match)
    children = [r for r in deps['source']['records']['timeline']['members'] if r['kind'] == 'closed-reference-read']
    if len(children) != 2 or any(r['sourceCall']['targetRva'] != c['calledEntryRva']
            or r['sourceContext']['methodSpec'][0:2] != [m.index,-1] for r in children):
        _fail('source-child-binding', 'both owned closed reference contexts call the same actual helper', children)
    if sequence_result['originalType'] != children[0]['declaredType']:
        _fail('sequence-child-composition', 'registered Sequence type matches the actual closed child context', sequence_result)
    calls = c['calls']
    if calls['wrapperGetFormatter'] != provider_result['providerTransfer']['entryRva']:
        _fail('physical-provider-return-join', 'same actual helper with independently proved context/return', calls)
    if any(calls[k] != deps['instance']['calls'][k] for k in deps['instance']['calls']):
        _fail('physical-helper-join', 'same proved instance type/provider/dispatcher/interface helpers', calls)
    if calls['classPrepare'] != instance_result['formatterDispatch']['classPrepareHelperRva']:
        _fail('class-prepare-helper', 'same physical vtable preparation helper', calls)
    outer = c['programs']['readValue']
    if outer['program'][0][0] != c['calledEntryRva']:
        _fail('outer-physical-entry', c['calledEntryRva'], outer['program'][0])
    transfer = validate_read_value_transfer(image, outer, calls, fail=_fail)
    reference = deps['reference']
    adapter = next(r for r in reference['sharedEntries'] if not r['nonnull'])
    adapter_entry = entries.resolve(adapter['method'][0], adapter['classArguments'], adapter['methodArguments'])['pointer'] - image.pe.image_base
    offsets = deps['source']['readerFieldsUnboxedOffsets']
    inline = {}
    for mode in ('nonnull','nullWrapperOutput','ff'):
        p = c['programs'][mode]
        if p['program'][0][0] != calls['formatterDispatch']:
            _fail('inline-dispatch-entry', calls['formatterDispatch'], p['program'][0])
        inline[mode] = validate_optimized_adapter_transfer(image, p, calls, offsets,
            adapter_entry=adapter_entry, mode=mode, fail=_fail)
    barrier = validate_fast_reference_barrier(image, deps['sourceWrappers']['barrierProgram'], fail=_fail)
    at, h = c['programs']['nonnull']['program'][147]; raw = bytes.fromhex(h)
    if at + 7 + int.from_bytes(raw[2:6], 'little', signed=True) != barrier['disabledFlagRva']:
        _fail('inline-barrier-state', 'same independently proved disabled-barrier flag', [at,h])
    return {'ownedReadValueContext': context, 'sourceChildFields': [r['fieldName'] for r in children],
        'sourceFieldTransfers': source_result, 'outerReadValueTransfer': transfer,
        'optimizedAdapterTransfers': inline,
        'physicalEntryMatchedIndependentObject': physical_match,
        'physicalBodyIdentity': 'unresolved',
        'concreteNestedFallbackProvedFor': ['timeline','forceSync','sequence'],
        'sequenceConcreteWrapperComposition': 'proved-static',
        'sequenceStaticAndFallback': sequence_result,
        'physicalWrapperGetFormatterEffects': 'unresolved',
        'physicalWrapperGetFormatterReturn': 'proved-conditional',
        'physicalFormatterProvider': provider_result,
        'runtimeProviderAndContextSelection': 'conditional',
        'originalChildCursorComposition': 'unresolved'}


def validate_current_native_contract(*, gameassembly: Path | None = None,
                                     metadata: Path | None = None) -> dict:
    c = _contract(); pins = c['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return {'status': gate.status, 'detail': gate.detail, 'nativeInputs': pins, 'scope': SCOPE}
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    def unity_matches():
        return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == pins['UnityPlayer.dll']
    if not unity_matches():
        return {'status': 'mismatched' if unity.is_file() else 'missing', 'detail': 'UnityPlayer.dll missing or mismatched', 'scope': SCOPE, 'nativeInputs': pins}
    try:
        summary = _validate_image(open_native_image(gate.gameassembly, gate.metadata), c)
    except ValueError as error:
        if isinstance(error, CensusGateError): raise
        _fail('native-read-value-transfer', 'current complete ABI/context/value paths', str(error))
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated' or not unity_matches():
        return {'status': after.status if after.status != 'validated' else 'mismatched',
            'detail': 'native inputs changed during ReadValue validation', 'scope': SCOPE, 'nativeInputs': pins}
    return {'status': 'validated', 'scope': SCOPE, 'nativeInputs': pins, 'summary': summary,
        'childSchemaAdmitted': False, 'positiveListAdmitted': False, 'wholeRootAdmitted': False,
        'runtimeMeaningExact': False, 'evidenceBoundary': c['evidenceBoundary']}

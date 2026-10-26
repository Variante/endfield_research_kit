"""Authenticate context adapter, selector source and fallback interface slot.

This selected static program proves normal value transfers under its stated
storage/ABI conditions. It never evaluates a Buff condition or selects a live
runtime receiver, initialized interface cell or actual method pair.
"""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path
from types import SimpleNamespace
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import (
    open_native_image, read_reviewed_contract, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH,
)
from scripts.game_data.il2cpp.protocol import load_metadata_helper
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.accumulator_immediate_instructions import decode_accumulator_immediate_instructions
from scripts.game_data.il2cpp.context_adapter_control import prove_context_adapter_control
from scripts.game_data.il2cpp.context_fallback_control import prove_context_fallback_control
from scripts.game_data.il2cpp.class_selector_source import metadata_selector_column, prove_creation_selector_copy
from scripts.game_data.il2cpp.class_creation_instructions import decode_class_creation_instructions
from scripts.game_data.memorypack import buff_formatter_class_creation as parent_owner
from scripts.game_data.memorypack.corpus_gate import _fingerprint
from scripts.game_data.memorypack.native_owner import fail, proof_sources, validate_owner

LABEL = 'buffConditionContextAdapter'
SCHEMA = 'endfield.buff-condition-context-adapter-native-contract.v2'
SCOPE = 'complete-adapter-selector-source-and-fallback-interface-slot-static-control'
PATH = CONTRACTS_DIR / 'buff_condition_context_adapter_native.json'


def _fail(check, expected, actual, *, native_inputs=None):
    fail(LABEL, SCOPE, PATH, check, expected, actual, native_inputs=native_inputs)


def _contract():
    contract, _ = read_reviewed_contract(PATH, schema=SCHEMA, status='exact-current-build', label=LABEL)
    if (contract.get('scope'), contract.get('parentContract')) != (SCOPE, parent_owner.PATH.name):
        _fail('contract-shape', (SCOPE, parent_owner.PATH.name), contract.get('scope'))
    if not isinstance(contract.get('cases'), list) or len(contract['cases']) != 5:
        _fail('contract-cases', 'five distinct named Context field joins', contract.get('cases'))
    return contract


def _proof_sources():
    return proof_sources(__file__, PATH,
        parent_owner._proof_sources() + [_fingerprint(METADATA_HELPER_PATH)], NATIVE_MAPPER_PATH)


def _owned_rows(image, index, block, decoder):
    base = image.pe.image_base
    entry = base + block['entryRva']
    if entry not in index.extents:
        raise ValueError(LABEL + '.missing-owned-entry')
    actual = sorted(set([(entry, index.extents[entry])] +
        [(a, a + n) for a, n in index.chained_fragments.get(entry, [])]))
    if actual != [(base + w['startRva'], base + w['endRva']) for w in block['ownedWindows']]:
        raise ValueError(LABEL + '.complete-owned-windows-differ')
    rows = []
    for window in block['ownedWindows']:
        start, end = base + window['startRva'], base + window['endRva']
        raw = image.pe.bytes_at_va(start, end - start)
        if ('rawHex' in window and raw != bytes.fromhex(window['rawHex'])) or hashlib.sha256(raw).hexdigest().upper() != window['sha256']:
            raise ValueError(LABEL + '.owned-native-bytes-differ')
        decoded = decoder(image.mapper, raw, start)
        at = start
        for row in decoded:
            packet = bytes.fromhex(row['bytes'])
            if not packet or int(row['va'], 16) != at or raw[at-start:at-start+len(packet)] != packet or row['text'].startswith('db'):
                raise ValueError(LABEL + '.incomplete-owned-instruction-partition')
            at += len(packet)
        if at != end:
            raise ValueError(LABEL + '.uncovered-owned-tail')
        rows.extend(decoded)
    return rows


def _named_case(image, selected, column, case, context_type):
    found = [row for row in column['rows'] if row['selectorWord'] == case['selectorWord']]
    if found != [case['uniqueCurrentMetadataType']]:
        raise ValueError(LABEL + '.unique-selector-named-row-differs')
    row = found[0]
    name = row['typeName']
    td = image.metadata.types[row['typeDefinition']]
    if selected.is_value_type(name) or td.generic_container_index >= 0:
        raise ValueError(LABEL + '.named-reference-type-required')
    matches = []
    for field in image.metadata.fields_for(td):
        attributes = selected.field_attributes(field.type_index)
        if attributes & 0x10 or selected.type_name(field.type_index) != context_type:
            continue
        qualified = name + '::' + image.metadata.string(field.name_index)
        owner, declared, offset = selected.field(qualified)
        if offset == case['inputByteOffset']:
            matches.append({'field': owner + '::' + qualified.split('::', 1)[1],
                'declaredType': declared, 'instanceByteOffset': offset, 'isStatic': False,
                'fieldAttributes': attributes})
    if matches != [case['namedContextField']]:
        raise ValueError(LABEL + '.unique-instance-context-field-differs')
    section = image.metadata.sections['interfaces']
    first, end = section.offset + td.interfaces_start * 4, section.offset + (td.interfaces_start + td.interfaces_count) * 4
    if td.interfaces_count and not section.offset <= first <= end <= section.offset + section.size:
        raise ValueError(LABEL + '.declared-interface-range')
    interfaces = [selected.type_name(struct.unpack_from('<i', image.metadata.buf, at)[0])
        for at in range(first, end, 4)] if td.interfaces_count else []
    if interfaces != case['declaredInterfaces']:
        raise ValueError(LABEL + '.declared-interfaces-differ')
    methods = [m for m in image.metadata.methods_for(td)
        if image.metadata.string(m.name_index) == 'get_context' and m.parameter_count == 0]
    if len(methods) != 1:
        raise ValueError(LABEL + '.unique-named-getter-required')
    method = methods[0]
    if method.flags & 0x10 or selected.type_name(method.return_type) != context_type:
        raise ValueError(LABEL + '.instance-context-getter-signature')
    getter = case['namedGetter']
    if image.validate_method_row(getter['method'], label=LABEL+'.namedGetter') != method.index:
        raise ValueError(LABEL + '.registered-getter-differs')
    pointer = image.method_pointer_va(method)
    raw = image.pe.bytes_at_va(pointer, getter['closedEntryBytes'])
    if raw != bytes.fromhex(getter['rawHex']) or hashlib.sha256(raw).hexdigest().upper() != getter['sha256']:
        raise ValueError(LABEL + '.closed-getter-bytes-differ')
    from scripts.game_data.il2cpp.memory_moves import decode_memory_move
    decoded = decode_memory_move(raw, 0, pointer)
    if decoded is None or raw[decoded[1]:] != b'\xc3':
        raise ValueError(LABEL + '.closed-getter-load-return-required')
    fact = decoded[0]['memoryOperation']; address = fact['address']
    if (fact['direction'], fact['register'], fact['registerBits'], fact['memoryBytes'],
        address['base'], address['index'], address['scale'], address['displacement'], address['ripRelative'], address['addressBits']) != (
        'load', 'rax', 64, 8, 'rcx', None, 1, case['inputByteOffset'], False, 64):
        raise ValueError(LABEL + '.closed-getter-field-transfer-differs')
    return {'type': name, 'field': matches[0], 'closedRegisteredGetterProved': True,
        'completeGetterPaddingProved': False, 'runtimeReceiverIdentityProved': False}


def _interface_slot(image, selected, fallback, declaration):
    cell = image.pe.image_base + fallback['capturedComparisonCellRva']
    raw = image.pe.bytes_at_va(cell, 8)
    type_index = unresolved_usage_index(raw, image.registration['typesCount'], tag=1,
        source=str(image.gameassembly), offset=cell)
    name = selected.type_name(type_index)
    td = selected.index.types.get(name)
    if td is None or not td.flags & 0x20 or td.generic_container_index >= 0:
        raise ValueError(LABEL + '.nongeneric-interface-declaration-required')
    slot = fallback['resolverCall']['r8d']
    if slot != fallback['matchedPairAddress']['slot']:
        raise ValueError(LABEL + '.resolver-inline-slot-differs')
    methods = [m for m in image.metadata.methods_for(td) if m.slot == slot]
    if len(methods) != 1:
        raise ValueError(LABEL + '.unique-interface-slot-required')
    method = methods[0]
    actual = {'usageCellRva': cell-image.pe.image_base, 'usageRawHex': raw.hex().upper(),
        'registeredTypeIndex': type_index, 'typeName': name, 'typeDefinition': td.index,
        'typeFlags': td.flags, 'typeIsInterface': True, 'interfaceMethod': {
            'methodDefinition': method.index, 'name': image.metadata.string(method.name_index),
            'slot': method.slot, 'parameterCount': method.parameter_count, 'flags': method.flags,
            'returnType': selected.type_name(method.return_type)},
        'runtimeUsageCellResolvedIdentityProved': False, 'runtimePairMethodIdentityProved': False}
    if actual != declaration:
        raise ValueError(LABEL + '.stored-interface-slot-join-differs')
    return actual


def _validate_selected(gameassembly, contract, *, metadata_path):
    parent = parent_owner._contract()
    if parent['nativeInputs'] != contract['nativeInputs']:
        raise ValueError(LABEL + '.parent-native-build-differs')
    parent_summary = parent_owner._validate_selected(gameassembly, parent, metadata_path=metadata_path)
    image = open_native_image(Path(gameassembly), Path(metadata_path))
    index = BodyIndex(image); base = image.pe.image_base
    adapter_rows = _owned_rows(image, index, contract['adapter'], decode_accumulator_immediate_instructions)
    adapter = prove_context_adapter_control(adapter_rows, contract['adapter']['ownedWindows'], base, contract['adapter']['entryRva'])
    if adapter['fallback']['targetRva'] != contract['fallback']['entryRva']:
        raise ValueError(LABEL + '.actual-adapter-fallback-target-differs')
    fallback_rows = _owned_rows(image, index, contract['fallback'], decode_accumulator_immediate_instructions)
    fallback = prove_context_fallback_control(fallback_rows, contract['fallback']['ownedWindows'], base, contract['fallback']['entryRva'])
    column = metadata_selector_column(load_metadata_helper(METADATA_HELPER_PATH), image.metadata)
    if {k: v for k, v in column.items() if k != 'rows'} != contract['metadataColumn']:
        raise ValueError(LABEL + '.anonymous-metadata-column-differs')
    creation_block = {**parent['function'], 'ownedWindows': parent['function']['codeWindows']}
    creation_rows = _owned_rows(image, index, creation_block, decode_class_creation_instructions)
    copy = prove_creation_selector_copy(creation_rows, base, parent,
        adapter['unconditionalInputReads'][1]['byteOffset'], column['columnByteOffset'])
    if copy != contract['allocationSelectorCopy']:
        raise ValueError(LABEL + '.allocation-selector-copy-differs')
    expected_cases = [{k: case[k] for k in ('selectorWord', 'returnKind', 'inputByteOffset', 'loadRva', 'returnRva')}
        for case in contract['cases']]
    if adapter['selectorCases'] != expected_cases:
        raise ValueError(LABEL + '.adapter-case-transfers-differ')
    selected = NativeReferenceContext(image, index=index)
    context_type = contract['interfaceSlot']['interfaceMethod']['returnType']
    cases = [_named_case(image, selected, column, case, context_type) for case in contract['cases']]
    interface = _interface_slot(image, selected, fallback, contract['interfaceSlot'])
    return {'adapter': adapter, 'fallback': fallback, 'allocationSelectorCopy': copy,
        'metadataRowsChecked': len(column['rows']), 'namedContextCases': cases,
        'storedInterfaceSlot': interface, 'parentCreationInstructionsChecked': parent_summary['checkedInstructions'],
        'conditions': contract['conditions']}


def validate_current_native_contract(*, gameassembly, metadata):
    def selected_body(selected_ga, contract):
        return _validate_selected(selected_ga, contract, metadata_path=Path(metadata))
    owner = SimpleNamespace(_contract=_contract, _proof_sources=_proof_sources, _fail=_fail,
        _fingerprint=_fingerprint, SCOPE=SCOPE, check_installed_native_inputs=check_installed_native_inputs,
        _validate_selected=selected_body)
    return validate_owner(owner, gameassembly=gameassembly, metadata=metadata,
        open_claims={'runtimeContextIdentityProved': False, 'preparationOrResolverEffectsAndTerminationProved': False,
            'wholeConditionExecutionProved': False, 'wholeRootAdmitted': False},
        check='native-context-adapter-control', expected='complete owned adapter/fallback, anonymous selector copy, named fields and stored interface slot',
        phase='Buff condition context adapter')

"""Validate built-in control producers on an explicitly gated opened image."""
from __future__ import annotations

import struct
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.wwise_source_native import _collect_opened_source_image
from scripts.game_data.wwise_source_queue_native import validate_native_group_declarations, validate_native_group_windows

SCHEMA = 'endfield.wwise-built-in-parameters-native.v5'


def load_contract():
    value, _ = read_reviewed_contract(CONTRACTS_DIR / 'wwise_builtin_parameters_native.json',
                                     schema=SCHEMA, status='reviewedCurrentBuild', label='built-in-parameters')
    return value


def validate(contract, image, selected_inputs):
    """The caller first gates its explicit GameAssembly/metadata/Ak paths."""
    if contract['schema'] != SCHEMA or contract['status'] != 'reviewedCurrentBuild' or contract['nativeInputs'] != selected_inputs:
        raise ValueError('Built-in parameter schema/status/selected inputs differ')
    groups = list(contract['nativeGroups'])
    expected = {'wwise_inheritance_native': {'settingsLoader', 'settingsSpecialBinding', 'parameterEntryConstructor', 'parameterEntryFactory'},
                'wwise_effect_lifecycle_native': {'gameSyncSubscriberCallback', 'gameSyncAddTarget', 'gameSyncTargetInsert'}}
    owners = {}
    for dependency in contract['dependencies']:
        name = dependency['ownerContract']
        if name not in expected or name in owners or set(dependency['groups']) != expected[name]:
            raise ValueError('Built-in parameter borrowed group roster differs')
        owner, _ = read_reviewed_contract(CONTRACTS_DIR / (name + '.json'), schema=dependency['ownerSchema'],
                                         status='reviewedCurrentBuild', label='built-in-owner')
        if owner['nativeInputs'] != selected_inputs:
            raise ValueError('Built-in parameter borrowed inputs differ')
        owners[name] = owner
        for key in dependency['groups']:
            groups.append(next(group for group in owner['nativeGroups'] if group['key'] == key))
    if set(owners) != set(expected):
        raise ValueError('Built-in parameter borrowed owners missing')
    validate_native_group_declarations(groups)
    _, bodies, records = _collect_opened_source_image(image, 'selected built-in parameter producers')
    validate_native_group_windows(groups, image, bodies, records)
    indexed = {group['key']: group for group in groups}
    for binding in contract['fieldBindings']:
        witness = next(w for w in indexed[binding['group']]['instructionWitnesses'] if w['role'] == binding['role'])
        raw = bytes.fromhex(witness['instructionHex']); begin = binding['operandOffset']; end = begin + binding['operandBytes']
        expected = contract['layout'][binding['field']]
        if binding['index'] is not None:
            expected = expected[binding['index']]
        if not 0 <= begin < end <= len(raw) or int.from_bytes(raw[begin:end], 'little') != expected:
            raise ValueError('Built-in parameter field differs: ' + binding['role'])
    layout = contract['layout']
    if layout['bindingListStride'] != 16 or layout['bindingRowStride'] != 8 or layout['bindingListBase'] != layout['bindingIndexBias'] * layout['bindingListStride']:
        raise ValueError('Built-in parameter list layout differs')
    for binding in contract['callBindings']:
        witness = next(w for w in indexed[binding['group']]['instructionWitnesses'] if w['role'] == binding['role'])
        raw = bytes.fromhex(witness['instructionHex']); at = int(witness['rva'], 16)
        if len(raw) != 5 or raw[0] != 0xe8 or at + 5 + struct.unpack_from('<i', raw, 1)[0] != int(indexed[binding['targetGroup']]['entryRva'], 16):
            raise ValueError('Built-in parameter direct call differs: ' + binding['role'])
    callback = contract['subscriberCallbackOwner']
    if callback['ownerContract'] != 'wwise_effect_lifecycle_native' or callback['addressPoint'] != 'subscriberAddressPoint':
        raise ValueError('Built-in subscriber callback owner differs')
    point = owners[callback['ownerContract']][callback['addressPoint']]
    witness = next(w for w in indexed[callback['dispatchGroup']]['instructionWitnesses'] if w['role'] == callback['dispatchRole'])
    if bytes.fromhex(witness['instructionHex']) != bytes.fromhex('ff50') + bytes([point['callbackSlot']]):
        raise ValueError('Built-in subscriber callback virtual slot differs')
    target = image.image_base + int(indexed[point['callbackGroup']]['entryRva'], 16)
    if image.bytes_at_va(image.image_base + int(point['rva'], 16) + point['callbackSlot'], 8) != struct.pack('<Q', target):
        raise ValueError('Built-in subscriber callback virtual target differs')
    transition = contract['transition']; factor = transition['scaleFactor']
    witness = next(w for w in indexed[transition['group']]['instructionWitnesses'] if w['role'] == factor['role'])
    raw = bytes.fromhex(witness['instructionHex']); at = int(witness['rva'], 16); operand = factor['operandOffset']
    if not 0 <= operand <= len(raw) - 4 or at + len(raw) + struct.unpack_from('<i', raw, operand)[0] != int(factor['rva'], 16):
        raise ValueError('Built-in transition duration constant address differs')
    if image.bytes_at_va(image.image_base + int(factor['rva'], 16), 4) != struct.pack('<I', factor['word']):
        raise ValueError('Built-in transition duration constant differs')
    receiver = contract['transitionReceiverAddressPoint']; at = int(receiver['leaRva'], 16); raw = bytes.fromhex(receiver['leaHex'])
    if not any(int(w['rva'],16)<=at and at+len(raw)<=int(w['rva'],16)+w['bodyLength'] for w in indexed[receiver['constructorGroup']]['windows']):
        raise ValueError('Transition receiver address point outside constructor body')
    if len(raw)!=7 or raw[:3]!=bytes.fromhex('488d05') or image.bytes_at_va(image.image_base+at,7)!=raw or at+7+struct.unpack_from('<i',raw,3)[0]!=int(receiver['rva'],16):
        raise ValueError('Transition receiver constructed address point differs')
    dispatch = next(w for w in indexed[receiver['dispatchGroup']]['instructionWitnesses'] if w['role']==receiver['dispatchRole'])
    if receiver['slot']!=0 or bytes.fromhex(dispatch['instructionHex'])!=bytes.fromhex('ff10'):
        raise ValueError('Transition receiver virtual dispatch differs')
    target = image.image_base+int(indexed[receiver['receiverGroup']]['entryRva'],16)
    if image.bytes_at_va(image.image_base+int(receiver['rva'],16),8)!=struct.pack('<Q',target):
        raise ValueError('Transition receiver virtual target differs')
    return dict(nativeEntryRvas={key: group['entryRva'] for key, group in indexed.items()},
                evidenceBoundary=contract['evidenceBoundary'])

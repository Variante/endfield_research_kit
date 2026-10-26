"""Selected Room parameter cloning, update dispatch and ownership release."""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import load_native_mapper
from scripts.game_data.wwise_source_native import _collect_opened_source_image
from scripts.game_data.wwise_source_queue_native import (
    validate_native_group_declarations, validate_native_group_windows,
)


def load_contract():
    contract, _ = read_reviewed_contract(
        CONTRACTS_DIR / 'wwise_room_parameters_native.json',
        schema='endfield.wwise-room-parameters-native.v2',
        status='reviewedCurrentBuild', label='wwise-room-parameters',
    )
    return contract


def validate(contract, image, selected_inputs):
    if (contract.get('schema') != 'endfield.wwise-room-parameters-native.v2'
            or contract.get('status') != 'reviewedCurrentBuild'
            or contract['nativeInputs'] != selected_inputs):
        raise ValueError('Room parameter schema/status/selected inputs differ')
    owners = {}
    for name in ('parameter', 'configuration'):
        owner, _ = read_reviewed_contract(
            CONTRACTS_DIR / (contract[name + 'OwnerContract'] + '.json'),
            schema=contract[name + 'OwnerSchema'], status='reviewedCurrentBuild',
            label='room-parameter-owner',
        )
        if owner['nativeInputs'] != selected_inputs:
            raise ValueError('Room parameter owner inputs differ')
        owners[name] = owner
    groups = contract['nativeGroups']
    validate_native_group_declarations(groups)
    _, bodies, records = _collect_opened_source_image(image, 'selected Room parameters')
    validate_native_group_windows(groups, image, bodies, records)
    indexed = {group['key']: group for group in groups}

    def read(group, address, size):
        if not any(int(window['rva'], 16) <= address
                   and address + size <= int(window['rva'], 16) + window['bodyLength']
                   for window in indexed[group]['windows']):
            raise ValueError('Room parameter instruction/table outside complete body')
        return image.bytes_at_va(image.image_base + address, size)

    parameter = owners['parameter']
    registration = parameter['registrationWitnesses'][contract['factoryClassId']]
    factory = int(registration['parameterFactoryRva'], 16)
    raw = image.bytes_at_va(image.image_base + factory, registration['parameterFactoryBodyLength'])
    if hashlib.sha256(raw).hexdigest() != registration['parameterFactoryBodySha256']:
        raise ValueError('Room parameter factory body differs')
    address = int(registration['vtableLeaRva'], 16)
    raw = image.bytes_at_va(image.image_base + address, 7)
    vtable = int(registration['vtableRva'], 16)
    if (raw[:3].hex() != registration['vtableLeaPrefixHex']
            or address + 7 + struct.unpack_from('<i', raw, 3)[0] != vtable):
        raise ValueError('Room parameter factory address point differs')
    slots = contract['parameterSlots']
    if sorted(slot['slot'] for slot in slots) != [0, 8, 16, 32]:
        raise ValueError('Room parameter lifecycle slots differ')
    for slot in slots:
        pointer = struct.unpack('<Q', image.bytes_at_va(image.image_base + vtable + slot['slot'], 8))[0]
        if pointer != image.image_base + int(indexed[slot['group']]['entryRva'], 16):
            raise ValueError('Room parameter lifecycle slot target differs')
    leaf = contract['initializeLeaf']
    raw = bytes.fromhex(leaf['bytesHex'])
    entry = int(leaf['entryRva'], 16)
    if (leaf['slot'] != 24 or len(raw) != leaf['byteLength']
            or hashlib.sha256(raw).hexdigest() != leaf['sha256']
            or image.bytes_at_va(image.image_base + entry, len(raw)) != raw
            or struct.unpack('<Q', image.bytes_at_va(image.image_base + vtable + leaf['slot'], 8))[0]
            != image.image_base + entry):
        raise ValueError('Room parameter stackless initialization differs')
    bulk = parameter['parameterSchemas'][contract['factoryClassId']]['setParamsBlock']
    bulk_entry = int(bulk['rva'], 16)
    if (hashlib.sha256(image.bytes_at_va(image.image_base + bulk_entry, bulk['bodyLength'])).hexdigest()
            != bulk['bodySha256']
            or struct.unpack('<Q', image.bytes_at_va(image.image_base + vtable
                                                   + registration['setParamsBlockSlot'], 8))[0]
            != image.image_base + bulk_entry):
        raise ValueError('Room parameter bulk initialization owner differs')

    dispatch = contract['dispatch']
    remap = bytes(dispatch['remapBytes'])
    group = dispatch['group']
    targets = [int(value, 16) for value in dispatch['targetRvas']]
    witnesses = {row['role']: row for row in indexed[group]['instructionWitnesses']}
    maximum = bytes.fromhex(witnesses['maximumId']['instructionHex'])
    remap_read = bytes.fromhex(witnesses['remap']['instructionHex'])
    target_read = bytes.fromhex(witnesses['targetLookup']['instructionHex'])
    if (maximum != b'\x83\xf8' + bytes([dispatch['maximumId']])
            or struct.unpack_from('<I', remap_read, 4)[0] != int(dispatch['remapRva'], 16)
            or struct.unpack_from('<I', target_read, 3)[0] != int(dispatch['targetTableRva'], 16)):
        raise ValueError('Room parameter dispatch operands differ')
    null_result = witnesses['nullInputResult']
    if read(group, int(null_result['rva'], 16), 5) != b'\xb8' + struct.pack('<I', dispatch['nullInputResult']):
        raise ValueError('Room parameter null-input result differs')
    if (len(remap) != dispatch['maximumId'] + 1 or not targets or max(remap) >= len(targets)
            or read(group, int(dispatch['remapRva'], 16), len(remap)) != remap
            or read(group, int(dispatch['targetTableRva'], 16), len(targets) * 4)
            != struct.pack('<' + str(len(targets)) + 'I', *targets)):
        raise ValueError('Room parameter update dispatch tables differ')
    default = int(dispatch['defaultRva'], 16)
    if read(group, default, 5) != b'\xb8' + struct.pack('<I', dispatch['defaultResult']):
        raise ValueError('Room parameter successful no-op result differs')
    rows = dispatch['rows']
    ids = [row['parameterId'] for row in rows]
    if (len(set(ids)) != len(ids)
            or set(ids) != {index for index, slot in enumerate(remap) if targets[slot] != default}):
        raise ValueError('Room parameter defined-ID coverage differs')
    projection = owners['configuration']['parameterProjection']
    known = {offset for begin, end in projection['knownRanges'] for offset in range(begin, end)}
    for row in rows:
        address = int(row['branchRva'], 16)
        if address != targets[remap[row['parameterId']]]:
            raise ValueError('Room parameter ID/branch target differs')
        source_prefix = read(group, address, 4)
        if (row['sourceBytes'] == 1 and source_prefix != b'\x41\x80\x38\x00'
                or row['sourceBytes'] == 4 and not (source_prefix[:3] == b'\x41\x8b\x00'
                                                  or source_prefix == b'\xf3\x41\x0f\x10')
                or row['sourceBytes'] not in (1, 4)):
            raise ValueError('Room parameter update source width differs')
        values, dirty = [], []
        for store in row['stores']:
            raw = bytes.fromhex(store['instructionHex'])
            if read(group, int(store['rva'], 16), len(raw)) != raw:
                raise ValueError('Room parameter update store bytes differ')
            opcode_at = 3 if raw[:3] == b'\xf3\x0f\x11' else 1 if raw[0] in (0x88, 0x89, 0xc6) else None
            if opcode_at is None:
                raise ValueError('Room parameter update store opcode differs')
            modrm = raw[opcode_at]
            mode = modrm >> 6
            width = 1 if raw[0] in (0x88, 0xc6) else 4
            if modrm & 7 != 3 or mode not in (1, 2):
                raise ValueError('Room parameter update store base differs')
            offset = int.from_bytes(raw[opcode_at + 1:opcode_at + 1 + (1 if mode == 1 else 4)],
                                    'little', signed=True)
            if (offset, width) != (store['offset'], store['bytes']):
                raise ValueError('Room parameter update store extent differs')
            if offset in projection['transientBytes']:
                if raw[0] != 0xc6 or raw[-1] != 1:
                    raise ValueError('Room parameter dirty store differs')
                dirty.append(offset)
            else:
                if not set(range(offset, offset + width)) <= known:
                    raise ValueError('Room parameter update writes outside known settings')
                values.append((offset, width))
        if values != [(row['storedOffset'], row['storedBytes'])] or dirty != row['dirtyOffsets']:
            raise ValueError('Room parameter value/dirty projection differs')
        raw = bytes.fromhex(row['branchBytesHex'])
        if not raw or raw[-1:] != b'\xc3' or read(group, address, len(raw)) != raw:
            raise ValueError('Room parameter update branch bytes/return differ')

    clone = contract['clone']
    if clone['byteExtent'] != projection['byteExtent']:
        raise ValueError('Room parameter clone extent differs')
    witnesses = {row['role']: row for row in indexed[clone['group']]['instructionWitnesses']}
    allocation = witnesses['allocationSize']
    if read(clone['group'], int(allocation['rva'], 16), 5) != b'\xba' + struct.pack('<I', clone['byteExtent']):
        raise ValueError('Room parameter clone allocation extent differs')
    lea = witnesses['vtable']
    at = int(lea['rva'], 16)
    raw = read(clone['group'], at, 7)
    if raw[:3] != b'\x48\x8d\x05' or at + 7 + struct.unpack_from('<i', raw, 3)[0] != vtable:
        raise ValueError('Room parameter clone class differs')
    copied = set()
    for span in clone['copies']:
        begin, size = span['sourceOffset'], span['bytes']
        if (begin != span['destinationOffset'] or size not in (4, 8, 16)
                or not 8 <= begin < begin + size <= clone['byteExtent']
                or copied.intersection(range(begin, begin + size))):
            raise ValueError('Room parameter clone copy extent differs')
        for key in ('load', 'store'):
            raw = bytes.fromhex(span[key + 'Hex'])
            if read(clone['group'], int(span[key + 'Rva'], 16), len(raw)) != raw:
                raise ValueError('Room parameter clone copy bytes differ')
            prefix = 2 if raw[:2] in (b'\x0f\x10', b'\x0f\x11') else 3 if raw[:3] in (b'\xf2\x0f\x10', b'\xf2\x0f\x11') else 1
            if size != {1: 4, 2: 16, 3: 8}[prefix]:
                raise ValueError('Room parameter clone copy width differs')
            modrm = raw[prefix]
            mode = modrm >> 6
            actual = int.from_bytes(raw[prefix + 1:prefix + 1 + (1 if mode == 1 else 4)], 'little', signed=True)
            if mode not in (1, 2) or modrm & 7 != (3 if key == 'load' else 2) or actual != begin:
                raise ValueError('Room parameter clone copy operand differs')
        copied.update(range(begin, begin + size))
    if copied != set(range(8, clone['byteExtent'])):
        raise ValueError('Room parameter clone stored-byte coverage differs')
    if sorted(store['offset'] for store in clone['dirtyStores']) != projection['transientBytes']:
        raise ValueError('Room parameter clone dirty coverage differs')
    for store in clone['dirtyStores']:
        raw = bytes.fromhex(store['instructionHex'])
        if (raw[0] != 0xc6 or raw[-1] != store['value'] or store['value'] != 1
                or read(clone['group'], int(store['rva'], 16), len(raw)) != raw
                or int.from_bytes(raw[2:-1], 'little', signed=True) != store['offset']):
            raise ValueError('Room parameter clone dirty operand differs')
    def witness(group, role):
        row = next(value for value in indexed[group]['instructionWitnesses'] if value['role'] == role)
        raw = bytes.fromhex(row['instructionHex'])
        if read(group, int(row['rva'], 16), len(raw)) != raw:
            raise ValueError('Effect parameter ownership witness differs')
        return row, raw

    for binding in contract['ownershipFieldBindings']:
        _, raw = witness(binding['group'], binding['role'])
        begin = binding['operandOffset']
        end = begin + binding['operandBytes']
        if int.from_bytes(raw[begin:end], 'little') != contract['ownershipLayout'][binding['layoutField']]:
            raise ValueError('Effect parameter ownership field differs')
    for binding in contract['ownershipCallBindings']:
        row, raw = witness(binding['group'], binding['role'])
        at = int(row['rva'], 16)
        if raw[:1] != b'\xe8' or len(raw) != 5 or at + 5 + struct.unpack_from('<i', raw, 1)[0] != int(indexed[binding['targetGroup']]['entryRva'], 16):
            raise ValueError('Effect parameter ownership direct call differs')
    for binding in contract['ownershipVirtualBindings']:
        _, raw = witness(binding['group'], binding['role'])
        slot = binding['slot']
        if raw != b'\xff\x50' + bytes([slot]):
            raise ValueError('Effect parameter ownership virtual call differs')
        target = int(leaf['entryRva'], 16) if binding['parameterTarget'] == 'initializeLeaf' else int(indexed[binding['parameterTarget']]['entryRva'], 16)
        if struct.unpack('<Q', image.bytes_at_va(image.image_base + vtable + slot, 8))[0] != image.image_base + target:
            raise ValueError('Effect parameter ownership selected class slot differs')
    globals_by_role = {}
    for binding in contract['ownershipGlobals']:
        row, raw = witness(binding['group'], binding['role'])
        target = int(row['rva'], 16) + len(raw) + struct.unpack_from('<i', raw, binding['operandOffset'])[0]
        if target != int(binding['rva'], 16):
            raise ValueError('Effect parameter ownership global operand differs')
        globals_by_role[binding['role']] = binding['rva']
    _, stride = witness('effectParameterRegistryCreate', 'registryStride')
    _, selected = witness('effectParameterRegistryCreate', 'selectedRegistryRecord')
    _, factory_read = witness('effectParameterRegistryCreate', 'parameterFactory')
    registry_layout = contract['runtimeRegistryLayout']
    if stride != b'\x48\x83\xc0' + bytes([registry_layout['byteStride']]) or selected[-1] + factory_read[-1] != registry_layout['parameterFactoryOffset']:
        raise ValueError('Effect parameter runtime registry layout differs')
    return dict(ownershipGlobals=globals_by_role, parameterVtableRva=registration['vtableRva'], parameterFactoryRva=registration['parameterFactoryRva'],
                initializeRva=leaf['entryRva'], bulkInitializeRva=bulk['rva'],
                serializedByteLengths=parameter['parameterSchemas'][contract['factoryClassId']]['parameterByteLengths'],
                nativeEntryRvas={key: value['entryRva'] for key, value in indexed.items()})


def load_validated(*, gameassembly, metadata, ak_sound_engine):
    audit = dict(status='missing', detail='three explicit native paths required')
    if any(path is None for path in (gameassembly, metadata, ak_sound_engine)):
        return None, audit
    try:
        contract = load_contract()
        inputs = contract['nativeInputs']
        gate = check_installed_native_inputs(inputs['gameAssemblySha256'], inputs['globalMetadataSha256'],
                                            gameassembly=Path(gameassembly), metadata=Path(metadata), require_metadata=True)
        audit.update(status=gate.status, detail=gate.detail)
        if gate.status != 'validated':
            return None, audit
        path = Path(ak_sound_engine)
        if not path.is_file():
            return None, dict(status='missing', detail='selected AkSoundEngine.dll missing')
        if path.stat().st_size != inputs['akSoundEngineFileSize'] or sha256_file(path).casefold() != inputs['akSoundEngineSha256'].casefold():
            return None, dict(status='mismatched', detail='selected AkSoundEngine.dll size/hash differs')
        image = load_native_mapper(NATIVE_MAPPER_PATH).PeImage(path)
        if hashlib.sha256(image.buf).hexdigest() != inputs['akSoundEngineSha256'].casefold():
            raise ValueError('opened Room parameter image differs')
        proof = validate(contract, image, inputs)
        audit.update(proof, status='validated', detail='selected Room parameter lifecycle and update dispatch validated',
                     evidenceBoundary=contract['evidenceBoundary'])
        return contract, audit
    except FileNotFoundError as error:
        audit.update(status='missing', detail=str(error)[:320])
    except (OSError, ValueError, KeyError, TypeError, IndexError, StopIteration, struct.error) as error:
        audit.update(status='mismatched', detail=str(error)[:320])
    return None, audit

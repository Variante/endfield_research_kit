"""Authenticate complete stored FX control framing on three selected inputs."""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import load_native_mapper
from scripts.game_data.wwise_source_native import _collect_opened_source_image
from scripts.game_data.wwise_source_queue_native import validate_native_group_declarations, validate_native_group_windows

SCHEMA = 'endfield.wwise-effect-controls-native.v1'


def load_contract():
    contract, _ = read_reviewed_contract(CONTRACTS_DIR / 'wwise_effect_controls_native.json',
                                        schema=SCHEMA, status='reviewedCurrentBuild', label='effect-controls')
    return contract


def validate(contract, image, selected_inputs):
    if contract['schema'] != SCHEMA or contract['status'] != 'reviewedCurrentBuild' or contract['nativeInputs'] != selected_inputs:
        raise ValueError('Effect controls schema/status/selected inputs differ')
    groups = list(contract['nativeGroups']); owners = {}
    expected = {'wwise_room_parameters_native': {'effectTemplateConstructor', 'effectTemplateLoad'},
                'wwise_effect_lifecycle_native': {'sharedFxFactory', 'customFxFactory'}}
    for dependency in contract['nativeGroupDependencies']:
        name = dependency['ownerContract']
        if name in owners or name not in expected or set(dependency['groups']) != expected[name]:
            raise ValueError('Effect controls borrowed owner/group roster differs')
        owner, _ = read_reviewed_contract(CONTRACTS_DIR / (name + '.json'), schema=dependency['ownerSchema'],
                                         status='reviewedCurrentBuild', label='effect-control-owner')
        if owner['nativeInputs'] != selected_inputs:
            raise ValueError('Effect controls borrowed inputs differ')
        owners[name] = owner
        for key in dependency['groups']:
            groups.append(next(group for group in owner['nativeGroups'] if group['key'] == key))
    if set(owners) != set(expected):
        raise ValueError('Effect controls borrowed owners missing')
    validate_native_group_declarations(groups)
    _, bodies, records = _collect_opened_source_image(image, 'selected complete effect controls')
    validate_native_group_windows(groups, image, bodies, records)
    indexed = {group['key']: group for group in groups}
    def checked(group, at, raw):
        if not 1 <= len(raw) <= 15 or not any(int(w['rva'], 16) <= at and at + len(raw) <= int(w['rva'], 16) + w['bodyLength'] for w in group['windows']):
            raise ValueError('Effect control operand outside authenticated body')
        if image.bytes_at_va(image.image_base + at, len(raw)) != raw:
            raise ValueError('Effect control operand bytes differ')
    if {point['key'] for point in contract['stateAddressPoints']} != {'base', 'shared', 'custom'} or len(contract['stateAddressPoints']) != 3:
        raise ValueError('Effect control state address-point roster differs')
    for point in contract['stateAddressPoints']:
        at = int(point['leaRva'], 16); raw = bytes.fromhex(point['leaHex'])
        checked(indexed[point['group']], at, raw)
        if len(raw) != 7 or raw[:3] != bytes.fromhex('488d05') or at + 7 + struct.unpack_from('<i', raw, 3)[0] != int(point['vtableRva'], 16):
            raise ValueError('Effect control state address point differs')
        if point['slot'] != contract['stateReadCall']['slot']:
            raise ValueError('Effect control state virtual slot differs')
        target = image.image_base + int(indexed[point['targetGroup']]['entryRva'], 16)
        if image.bytes_at_va(image.image_base + int(point['vtableRva'], 16) + point['slot'], 8) != struct.pack('<Q', target):
            raise ValueError('Effect control state virtual target differs')
    call = contract['stateReadCall']; raw = bytes.fromhex(call['instructionHex'])
    checked(indexed[call['group']], int(call['rva'], 16), raw)
    if raw != bytes.fromhex('ff50') + bytes([call['slot']]):
        raise ValueError('Effect control state dispatch differs')
    for row in contract['defaultReadInstructions']:
        checked(indexed['effectTemplateLoad'], int(row['rva'], 16), bytes.fromhex(row['instructionHex']))
    return dict(roomClassId=int(owners['wwise_effect_lifecycle_native']['observer']['parameterClassId'], 16),
                evidenceBoundary=contract['evidenceBoundary'])


def load_validated(*, gameassembly, metadata, ak_sound_engine):
    audit = dict(status='missing', detail='three explicit native paths required')
    if any(path is None for path in (gameassembly, metadata, ak_sound_engine)):
        return None, audit
    try:
        contract = load_contract(); inputs = contract['nativeInputs']
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
            raise ValueError('opened effect controls image differs')
        proof = validate(contract, image, inputs)
        audit.update(proof, status='validated', detail='selected complete FX state/default framing validated')
        return contract, audit
    except FileNotFoundError as error:
        audit.update(status='missing', detail=str(error)[:320])
    except (OSError, ValueError, KeyError, TypeError, IndexError, StopIteration, struct.error) as error:
        audit.update(status='mismatched', detail=str(error)[:320])
    return None, audit

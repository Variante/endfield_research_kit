"""Selected bank references, subscriber targets and effect-template destruction."""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import load_native_mapper
from scripts.game_data.wwise_room_parameters_native import load_contract as load_parameters, validate as validate_parameters
from scripts.game_data.wwise_source_native import _collect_opened_source_image
from scripts.game_data.wwise_source_queue_native import validate_native_group_declarations, validate_native_group_windows

SCHEMA = 'endfield.wwise-effect-lifecycle-native.v9'


def load_contract():
    value, _ = read_reviewed_contract(CONTRACTS_DIR / 'wwise_effect_lifecycle_native.json',
                                     schema=SCHEMA, status='reviewedCurrentBuild', label='wwise-effect-lifecycle')
    return value


def validate(contract, image, selected_inputs):
    if (contract['schema'] != SCHEMA or contract['status'] != 'reviewedCurrentBuild'
            or contract['nativeInputs'] != selected_inputs):
        raise ValueError('Effect lifecycle schema/status/selected inputs differ')
    parameters = load_parameters()
    if parameters['schema'] != contract['parameterOwnerSchema'] or contract['parameterOwnerContract'] != 'wwise_room_parameters_native':
        raise ValueError('Effect lifecycle parameter owner differs')
    parameter_proof = validate_parameters(parameters, image, selected_inputs)
    groups = list(contract['nativeGroups'])
    dependencies=contract['nativeGroupDependencies']
    if len(dependencies)!=1:
        raise ValueError('Effect lifecycle requires its single original curve owner')
    dependency=dependencies[0]
    if dependency['ownerContract']!='wwise_inheritance_native' or dependency['ownerGroup']!='curveEvaluation':
        raise ValueError('Effect lifecycle notification curve owner differs')
    owner,_=read_reviewed_contract(CONTRACTS_DIR/(dependency['ownerContract']+'.json'),schema=dependency['ownerSchema'],status='reviewedCurrentBuild',label='effect-notification-curve-owner')
    if owner['nativeInputs']!=selected_inputs:
        raise ValueError('Effect lifecycle notification curve inputs differ')
    groups.append(next(g for g in owner['nativeGroups'] if g['key']==dependency['ownerGroup']))
    validate_native_group_declarations(groups)
    _, bodies, records = _collect_opened_source_image(image, 'selected effect lifecycle')
    validate_native_group_windows(groups, image, bodies, records)
    indexed = {g['key']: g for g in parameters['nativeGroups']}
    if any(g['key'] in indexed for g in groups):
        raise ValueError('Effect lifecycle duplicates a parameter owner group')
    indexed.update({g['key']: g for g in groups})
    globals_by_role = {}
    for binding in contract['bindings']:
        group = indexed[binding['group']]
        if 'witness' in binding:
            witness = next(w for w in group['instructionWitnesses'] if w['role'] == binding['witness'])
        else:
            # A new edge in a borrowed, fully authenticated body belongs here;
            # it does not require copying or mutating the owner's catalog.
            witness=dict(rva=binding['instructionRva'],instructionHex=binding['instructionHex'])
        address = int(witness['rva'], 16)
        raw = bytes.fromhex(witness['instructionHex'])
        if not 1<=len(raw)<=15 or not any(int(w['rva'],16)<=address and address+len(raw)<=int(w['rva'],16)+w['bodyLength'] for w in group['windows']):
            raise ValueError('Effect lifecycle binding outside authenticated body: '+binding['role'])
        if image.bytes_at_va(image.image_base + address, len(raw)) != raw:
            raise ValueError('Effect lifecycle instruction differs: ' + binding['role'])
        kind = binding['kind']
        if kind == 'immediate':
            begin = binding['operandOffset']; end = begin + binding['operandBytes']
            if not 0 <= begin < end <= len(raw) or int.from_bytes(raw[begin:end], 'little') != binding['value']:
                raise ValueError('Effect lifecycle field/immediate differs: ' + binding['role'])
            if binding['role'] in contract['layout'] and contract['layout'][binding['role']] != binding['value']:
                raise ValueError('Effect lifecycle layout differs: ' + binding['role'])
        elif kind == 'zeroMemory':
            # No displacement in the selected MOV from [RDX]. The complete
            # body and witness above authenticate this exact operand form.
            if binding['value'] != 0 or raw != b'\x44\x8b\x32' or contract['layout'][binding['role']] != 0:
                raise ValueError('Effect lifecycle zero displacement differs')
        elif kind == 'direct':
            if (len(raw) != 5 or raw[0] not in (0xe8, 0xe9)
                    or address + 5 + struct.unpack_from('<i', raw, 1)[0]
                    != int(indexed[binding['value']]['entryRva'], 16)):
                raise ValueError('Effect lifecycle direct target differs: ' + binding['role'])
        elif kind == 'virtual':
            if raw != b'\xff\x50' + bytes([binding['value']]):
                raise ValueError('Effect lifecycle virtual call differs')
        elif kind == 'rip':
            offset = binding['operandOffset']
            if binding['operandBytes'] != 4 or not 0 <= offset <= len(raw) - 4:
                raise ValueError('Effect lifecycle RIP operand invalid')
            if address + len(raw) + struct.unpack_from('<i', raw, offset)[0] != int(binding['value'], 16):
                raise ValueError('Effect lifecycle global differs: ' + binding['role'])
            globals_by_role[binding['role']] = binding['value']
        else:
            raise ValueError('Effect lifecycle binding kind unsupported')
    point = contract['templateAddressPoint']; address = int(point['constructorLeaRva'], 16)
    raw = image.bytes_at_va(image.image_base + address, 7)
    if raw[:3] != b'\x48\x8d\x05' or address + 7 + struct.unpack_from('<i', raw, 3)[0] != int(point['rva'], 16):
        raise ValueError('Effect template address point differs')
    for slot in point['slots']:
        actual = struct.unpack('<Q', image.bytes_at_va(image.image_base + int(point['rva'], 16) + slot['slot'], 8))[0]
        if actual != image.image_base + int(indexed[slot['group']]['entryRva'], 16):
            raise ValueError('Effect template virtual target differs')
    for derived in contract['derivedTemplateAddressPoints']:
        address=int(derived['factoryLeaRva'],16);raw=image.bytes_at_va(image.image_base+address,7)
        if raw[:3]!=b'\x48\x8d\x05' or address+7+struct.unpack_from('<i',raw,3)[0]!=int(derived['rva'],16):
            raise ValueError('Derived effect template factory address point differs')
        for slot in derived['slots']:
            actual=struct.unpack('<Q',image.bytes_at_va(image.image_base+int(derived['rva'],16)+slot['slot'],8))[0]
            if actual!=image.image_base+int(indexed[slot['group']]['entryRva'],16):raise ValueError('Derived effect template virtual target differs')
    subscriber = contract['subscriberAddressPoint']; address = int(subscriber['destructorLeaRva'], 16)
    raw = image.bytes_at_va(image.image_base + address, 7)
    if (raw[:3] != b'\x48\x8d\x05' or address + 7 + struct.unpack_from('<i', raw, 3)[0] != int(subscriber['rva'], 16)
            or struct.unpack('<Q', image.bytes_at_va(image.image_base + int(subscriber['rva'], 16) + subscriber['slot'], 8))[0]
            != image.image_base + int(indexed[subscriber['group']]['entryRva'], 16)):
        raise ValueError('Effect subscriber key getter address point differs')
    if struct.unpack('<Q',image.bytes_at_va(image.image_base+int(subscriber['rva'],16)+subscriber['callbackSlot'],8))[0] != image.image_base+int(indexed[subscriber['callbackGroup']]['entryRva'],16):
        raise ValueError('Effect subscriber callback address point differs')
    return dict(nativeEntryRvas={k: g['entryRva'] for k, g in indexed.items()}, lifecycleGlobals=globals_by_role,
                parameterProof=parameter_proof, templateVtableRva=point['rva'])


def load_validated(*, gameassembly, metadata, ak_sound_engine):
    audit = dict(status='missing', detail='three explicit native paths required')
    if any(p is None for p in (gameassembly, metadata, ak_sound_engine)):
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
            raise ValueError('opened effect lifecycle image differs')
        proof = validate(contract, image, inputs)
        audit.update(proof, status='validated', detail='selected bank/subscriber/final destruction routes validated',
                     evidenceBoundary=contract['evidenceBoundary'])
        return contract, audit
    except FileNotFoundError as error:
        audit.update(status='missing', detail=str(error)[:320])
    except (OSError, ValueError, KeyError, TypeError, IndexError, StopIteration, struct.error) as error:
        audit.update(status='mismatched', detail=str(error)[:320])
    return None, audit

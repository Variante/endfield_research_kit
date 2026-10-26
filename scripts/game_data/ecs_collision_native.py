"""Authenticate packed ECS collider framing and separate physics/entity identities."""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH, open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import load_native_mapper, runtime_type_field_offsets
from scripts.game_data.il2cpp.body_claims import evaluate
from scripts.game_data.mission_trace_capture_prepare import SelectedMethods

CONTRACT = CONTRACTS_DIR / 'ecs_collision_native.json'
SCHEMA = 'endfield.ecs-collision-native.v3'
OWNERSHIP_CONTRACT = CONTRACTS_DIR / 'ecs_collision_ownership.json'


def require(value, detail):
    if not value:
        raise ValueError('ecs-collision-native:' + detail)


def validate_player(pe, contract):
    require(contract.get('schema') == SCHEMA and contract.get('status') == 'reviewed', 'schema/status')
    windows = {}
    for spec in contract['codeWindows']:
        role = spec['role']
        require(role not in windows and 1 <= spec['bytes'] <= 16384, 'window identity/bound:' + role)
        raw = pe.bytes_at_va(pe.image_base + spec['rva'], spec['bytes'])
        require(hashlib.sha256(raw).hexdigest() == spec['sha256'], 'code window hash:' + role)
        windows[role] = raw
    require(windows and contract['probes'], 'empty native proof')
    for probe in contract['probes']:
        raw = windows[probe['role']]
        at, expected = probe['offset'], bytes.fromhex(probe['hex'])
        require(0 <= at <= len(raw)-len(expected) and raw[at:at+len(expected)] == expected,
                'instruction probe:' + probe['role'] + ':' + str(at))
        if 'layoutField' in probe:
            value = contract['layout']
            for key in probe['layoutField'].split('.'):
                value = value[key]
            require(probe['mode'] in ('u8','andMaskComplement8','fixedSarOne') and 0 <= probe['operandOffset'] < len(expected), 'operand mode/bound')
            if probe['mode'] == 'fixedSarOne':
                require(value == 1 and expected == bytes.fromhex('d1fe'), 'encoded shift-one operand:' + probe['layoutField'])
                continue
            actual = expected[probe['operandOffset']]
            encoded = value if probe['mode'] == 'u8' else (~value)&255
            require(actual == encoded, f"operand:{probe['layoutField']}:expected={encoded},actual={actual}")
    declarations={row['role']:row for row in contract['codeWindows']}
    for call in contract.get('directCalls', []):
        raw=windows[call['role']]
        at=call['offset']
        require(0 <= at <= len(raw)-5 and raw[at] == 0xe8, 'direct call opcode:' + call['role'])
        target=declarations[call['role']]['rva']+at+5+struct.unpack_from('<i',raw,at+1)[0]
        require(target == declarations[call['targetRole']]['rva'], 'direct call target:' + call['role'])
    return contract


def validate_sources(pe, contract):
    """Prove the collision callbacks without borrowing the wider row decoder.

    These are constructor-selected defaults, not a runtime registration receipt.
    The independently pinned descriptor, assignment and publication bodies own
    the slot width and copy programme; no field-2 schema is implied here.
    """
    windows = {row['role']: row for row in contract['codeWindows']}
    selected = contract['selectedDefaultSlot3']
    require([r['selector'] for r in selected] == [2, 5, 6, 7, 9], 'source selectors')
    registration = windows['source_registration']

    def read(at, size):
        require(registration['rva'] <= at <= registration['rva']+registration['bytes']-size,
                'source programme outside registration span')
        return pe.bytes_at_va(pe.image_base+at, size)

    def call(at, role):
        raw = read(at, 5)
        require(raw[0] == 0xe8 and at+5+struct.unpack_from('<i', raw, 1)[0] == windows[role]['rva'],
                'source helper target:' + role)

    for row in selected:
        selector, stack = row['selector'], row['descriptorStack']
        require(0 <= stack <= 32767, 'source descriptor stack bound')
        require(read(row['descriptorRva'], 2) == bytes((0xb2, selector)), 'source descriptor selector')
        require(read(row['descriptorLeaRva'], 7) == bytes.fromhex('488d8d')+struct.pack('<i', stack),
                'source descriptor base')
        call(row['descriptorCallRva'], 'source_descriptor')
        at = row['functionLeaRva']
        raw = read(at, 7)
        require(raw[:3] == bytes.fromhex('488d05') and
                at+7+struct.unpack_from('<i', raw, 3)[0] == windows[row['producerRole']]['rva'],
                'source callback address')
        require(read(at+7, 10) == bytes.fromhex('48895c24504889442458'), 'source inline callback value')
        if selector == 9:
            require(read(at+17, 23) == bytes.fromhex('4c8d442450488d442450b203488d8d')+
                    struct.pack('<i', stack)+bytes.fromhex('48894588'), 'indexed source slot three')
            call(at+40, 'source_indexed_assignment')
        else:
            require(read(at+17, 21) == bytes.fromhex('488d542450488d442450488d8d')+
                    struct.pack('<i', stack+8+3*64)+bytes.fromhex('48894588'), 'source slot three')
            call(at+38, 'source_assignment')
        at = row['publicationRva']
        require(read(at, 13) == bytes.fromhex('488d4f08')+bytes((0xb2, selector))+
                bytes.fromhex('4c8d85')+struct.pack('<i', stack), 'source publication arguments')
        call(at+13, 'source_publication')
        literal = row['keyLiteral']
        require(pe.bytes_at_va(pe.image_base+literal['rva'], 12) == struct.pack('<3I', *row['key']),
                'source counted-prefix key')
        producer = windows[row['producerRole']]
        for address, size, prefix, target in ((literal['loadRva'], 8, 'f20f1005', literal['rva']),
                                             (literal['tailLoadRva'], 6, '8b05', literal['rva']+8)):
            require(producer['rva'] <= address <= producer['rva']+producer['bytes']-size,
                    'source key read outside callback')
            raw = pe.bytes_at_va(pe.image_base+address, size)
            require(raw.startswith(bytes.fromhex(prefix)) and
                    address+size+struct.unpack_from('<i', raw, size-4)[0] == target, 'source key RIP read')
    return selected


def load(*, gameassembly: Path, metadata: Path, unityplayer: Path, contract_path=CONTRACT):
    audit = dict(validator='ecs_collision_native', status='failed', diagnostics=[])
    try:
        contract, digest = read_reviewed_contract(contract_path, schema=SCHEMA, label='ecs-collision', status='reviewed')
        inputs = contract['nativeInputs']
        gate = check_installed_native_inputs(inputs['gameAssemblySha256'], inputs['metadataSha256'],
                                              gameassembly=gameassembly, metadata=metadata)
        audit.update(status=gate.status, detail=gate.detail)
        if gate.status != 'validated':
            return None, audit
        if not unityplayer.is_file() or sha256_file(unityplayer).lower() != inputs['unityPlayerSha256'].lower():
            audit.update(status='missing' if not unityplayer.is_file() else 'mismatched', detail='UnityPlayer missing/hash differs')
            return None, audit
        player = load_native_mapper(NATIVE_MAPPER_PATH).PeImage(unityplayer)
        validate_player(player, contract)
        validate_sources(player, contract)
        selected = SelectedMethods(open_native_image(gameassembly, metadata))
        for name,expected in contract['enums'].items():
            require(selected.enum_members(name) == expected, 'parameter enum defaults:' + name)
        require(selected.value_size('UnityEngine.HyperGryph.ECS.Entity') == contract['layout']['entity']['bytes'], 'Entity width')
        require(contract['managedTypes'], 'empty managed layout proof')
        for spec in contract['managedTypes']:
            name = spec['type']
            require(selected.value_size(name) == spec['bytes'], 'value width:' + name)
            image = selected.image
            offsets = runtime_type_field_offsets(image.metadata, image.pe, image.registration, selected.index.types[name].index)
            actual={field:offsets.get(field,-1)-16 for field in spec['fields']}
            require(actual == spec['fields'], 'unboxed field offsets:' + name + ':expected=' + json.dumps(spec['fields']) + ',actual=' + json.dumps(actual))
        claims, _ = read_reviewed_contract(OWNERSHIP_CONTRACT, schema='endfield.ecs-collision-ownership.v1', label='ecs-collision-ownership', status='reviewed')
        methods, failures = evaluate(selected.index, claims['methods'])
        require(not failures and len(methods) == len(claims['methods']), 'ownership claims:' + json.dumps(failures[:3])[:1000])
        after = check_installed_native_inputs(inputs['gameAssemblySha256'], inputs['metadataSha256'],
                                               gameassembly=gameassembly, metadata=metadata)
        require(after.status == 'validated' and sha256_file(unityplayer).lower() == inputs['unityPlayerSha256'].lower(), 'native inputs changed during validation')
        audit.update(status='validated', contractSha256=digest, nativeInputs=inputs,
                     windows=len(contract['codeWindows']), probes=len(contract['probes']), ownershipMethods=methods,
                     ownershipBoundary=claims['evidenceBoundary'], evidenceBoundary=contract['evidenceBoundary'])
        return contract, audit
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as error:
        audit.update(status='failed', diagnostics=[dict(check='selected_ecs_layout', source=str(contract_path), detail=str(error)[:1200])])
        return None, audit

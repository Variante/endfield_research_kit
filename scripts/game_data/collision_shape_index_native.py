"""Authenticate the separate auxiliary and enumerated ECS shape index domains."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import load_native_mapper
from scripts.game_data.il2cpp.unwind_chains import read_exception_directory, UnwindChainIndex

CONTRACT = CONTRACTS_DIR / 'collision_shape_index_native.json'
SCHEMA = 'endfield.collision-shape-index-native.v2'


def validate_player(pe, contract):
    if contract.get('schema') != SCHEMA or contract.get('status') != 'reviewed':
        raise ValueError('shape index schema/status')
    table, size, raw = read_exception_directory(pe)
    index = UnwindChainIndex(raw, lambda r,n: pe.bytes_at_va(pe.image_base+r,n),
                             table_rva=table, image_size=size)
    windows = {}
    for spec in contract['codeWindows']:
        role = spec['role']
        if role in windows or not 0 < spec['bytes'] <= 4096:
            raise ValueError('shape index window identity/bound:' + role)
        body = pe.bytes_at_va(pe.image_base+spec['rva'], spec['bytes'])
        if hashlib.sha256(body).hexdigest() != spec['sha256']:
            raise ValueError('shape index window hash:' + role)
        family = index.family(spec['rva'])
        ranges = [p['runtimeTriple'] for p in family['ranges']]
        if ranges != spec['runtimeRanges'] or any(not spec['rva'] <= a < b <= spec['rva']+spec['bytes'] for a,b,_ in ranges):
            raise ValueError('shape index unwind membership:' + role)
        windows[role] = body
    for probe in contract['probes']:
        body = windows[probe['role']]
        at, expected = probe['offset'], bytes.fromhex(probe['hex'])
        if not expected or not 0 <= at <= len(body)-len(expected) or body[at:at+len(expected)] != expected:
            raise ValueError('shape index instruction:' + probe['role'] + ':' + str(at))
        if 'field' in probe:
            value = contract
            for name in probe['field'].split('.'):
                value = value[name]
            start, width = probe['operandOffset'], probe['operandBytes']
            if width not in (1,4) or not 0 <= start <= len(expected)-width or int.from_bytes(expected[start:start+width], 'little') != value:
                raise ValueError('shape index field operand:' + probe['field'])
    return contract


def load(*, gameassembly: Path, metadata: Path, unityplayer: Path, contract_path=CONTRACT):
    audit = dict(validator='collision_shape_index_native', status='failed', diagnostics=[])
    try:
        contract, _ = read_reviewed_contract(contract_path, schema=SCHEMA, label='collision-shape-index', status='reviewed')
        inputs = contract['nativeInputs']
        gate = check_installed_native_inputs(inputs['gameAssemblySha256'], inputs['metadataSha256'],
                                            gameassembly=gameassembly, metadata=metadata)
        audit.update(status=gate.status, detail=gate.detail, nativeInputs=inputs)
        if gate.status != 'validated':
            return None, audit
        if not unityplayer.is_file():
            audit.update(status='missing', detail='UnityPlayer.dll missing:' + str(unityplayer))
            return None, audit
        before = sha256_file(unityplayer).lower()
        if before != inputs['unityPlayerSha256'].lower():
            audit.update(status='mismatched', detail='UnityPlayer.dll hash differs', actualUnityPlayerSha256=before)
            return None, audit
        validate_player(load_native_mapper(NATIVE_MAPPER_PATH).PeImage(unityplayer), contract)
        after = check_installed_native_inputs(inputs['gameAssemblySha256'], inputs['metadataSha256'],
                                             gameassembly=gameassembly, metadata=metadata)
        if after.status != 'validated' or sha256_file(unityplayer).lower() != before:
            raise ValueError('native inputs changed during shape index validation')
        audit.update(status='validated', codeWindows=len(contract['codeWindows']), probes=len(contract['probes']))
        return contract, audit
    except (OSError, ValueError, KeyError, IndexError, TypeError, RuntimeError) as error:
        audit.update(status='failed', diagnostics=[dict(check='shape_index_native', source=str(contract_path), detail=str(error)[:1200])])
        return None, audit

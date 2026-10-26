"""Validate the named worker task that produces broadphase dependencies.

This compiled route supplies no saved-task enqueue or simulation generation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.collision_runtime_mesh_native import load_code_layout, validate_code_layout
from scripts.game_data.collision_pair_step_native import (
    CONTRACT as SHARED, validate_program, _instruction, _rip,
)
from scripts.game_data.corpus_common import atomic_write_text

CONTRACT = CONTRACTS_DIR / 'collision_narrowphase_task_native.json'
SCHEMA = 'endfield.collision-narrowphase-task-native.v1'


def validate(pe, contract, *, schema=SCHEMA):
    windows = validate_code_layout(pe, contract, schema=schema)
    if contract['sharedContract'] != SHARED.name:
        raise ValueError('narrowphase task shared contract differs')
    shared = json.loads(SHARED.read_text('utf-8'))
    if contract['nativeInputs'] != shared['nativeInputs']:
        raise ValueError('narrowphase task native inputs differ')
    validate_program(pe, shared)
    definitions = {w['role']: w for w in shared['codeWindows']}
    ctor = contract['constructor']; window = definitions[ctor['windowRole']]
    raw = pe.bytes_at_va(pe.image_base+window['rva'], window['bytes'])
    field = contract['sceneField']; layout = shared['layout']['task']
    if (_rip(window, raw, ctor['vtableLea']) != contract['vtableRva'] or
            _instruction(raw, ctor['vtableStore'], '488986') != field or
            _instruction(raw, ctor['ownerStore'], '4889b6') != field+layout['owner'] or
            _rip(window, raw, ctor['nameLea']) != contract['nameRva'] or
            _instruction(raw, ctor['nameStore'], '488986') != field+shared['taskNameField']):
        raise ValueError('narrowphase task constructor coordinates differ')
    table = pe.image_base+contract['vtableRva']; run, data = windows['run']
    getter = next(x['rva'] for x in shared['nameGetterLeaves'] if x['role']=='embedded')
    wrapper = pe.u64_at_va(pe.image_base+shared['taskTypes'][0]['vtableRva']+8)
    if (contract['runSlot'] != shared['runSlot'] or
            pe.u64_at_va(table+contract['runSlot']*8) != pe.image_base+run['rva'] or
            contract['nameGetterRva'] != getter or
            pe.u64_at_va(table+16) != pe.image_base+getter or
            pe.u64_at_va(table+8) != wrapper):
        raise ValueError('narrowphase task virtual slots differ')
    name = contract['name'].encode('ascii')+b'\0'
    if pe.bytes_at_va(pe.image_base+contract['nameRva'], len(name)) != name:
        raise ValueError('narrowphase task name differs')
    prefix = b'\x48\x8b\x51'+bytes([layout['continuation']])+b'\x48\x8b\x49'+bytes([layout['owner']])+b'\xe9'
    if len(data) != len(prefix)+4 or not data.startswith(prefix):
        raise ValueError('narrowphase task owner/continuation tail thunk differs')
    target = run['rva']+len(data)+struct.unpack_from('<i', data, len(prefix))[0]
    if target != definitions['task_dependency_wiring']['rva']:
        raise ValueError('narrowphase task dependency target differs')
    return contract


def load(*, gameassembly, metadata, unityplayer):
    return load_code_layout(gameassembly=Path(gameassembly), metadata=Path(metadata),
        unityplayer=Path(unityplayer), contract_path=CONTRACT, schema=SCHEMA,
        validator='collision_narrowphase_task_native', validate=validate)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('gameassembly', 'metadata', 'unityplayer', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(argv)
    contract, gate = load(gameassembly=args.gameassembly, metadata=args.metadata, unityplayer=args.unityplayer)
    report = dict(schema=SCHEMA, status=gate['status'], gate=gate)
    if contract:
        report.update(task=contract['name'], evidenceBoundary=contract['evidenceBoundary'])
    from scripts.game_data.collision_runtime_mesh import _output_path
    atomic_write_text(_output_path(args.output), json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))
    return int(contract is None)


if __name__ == '__main__':
    raise SystemExit(main())

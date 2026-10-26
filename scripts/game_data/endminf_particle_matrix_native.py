"""Authenticate the selected particle matrix path and its file-backed constants.

The contract describes code and layout, not an observed live branch. A .data
zero-fill address has no installed-file value; its initializer is separate.


Evidence and admission boundary
-------------------------------
Exact selected-input authentication covers the getter's packed branch flag and
complete unwind families. Conditional numeric replay under recorded unsorted,
zero-pivot mode and stable bracketing flags builds a scaled affine inverse from
camera-to-world; substituting stored world-to-view changes float32 results.
Ordered instructions reproduce retained head anchors, not full attributes, live
branch execution, simulation or calibration. Reciprocal-square-root correction
has a runtime initializer and zero-fill storage: a virtual-tail RVA has no file
value. Require strict raw-backed PE reads and an explicit initializer/current-CPU
condition; never read accidental bytes in the following section or feed observed
runtime operands into source rendering.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH
from scripts.game_data.il2cpp.protocol import load_native_mapper
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex, read_exception_directory

CONTRACT = CONTRACTS_DIR / 'endminf_particle_matrix_native.json'
SCHEMA = 'endfield.endminf-particle-matrix-native.v1'


def load(*, gameassembly=None, metadata=None, unity_player=None):
    c = json.loads(CONTRACT.read_bytes())
    if c.get('schema') != SCHEMA or c.get('status') != 'reviewed':
        raise ValueError('particle-matrix.contract: reviewed schema required')
    pins = c['nativeInputs']
    gate = check_installed_native_inputs(pins['gameAssemblySha256'], pins['metadataSha256'],
                                         gameassembly=gameassembly, metadata=metadata)
    audit = dict(validator='endminf-particle-matrix', status=gate.status, detail=gate.detail,
                 contract=str(CONTRACT), liveBranchExecutionProven=False)
    if gate.status != 'validated':
        return None, audit
    audit['selectedNativeInputs'] = dict(gameAssembly=dict(path=str(gate.gameassembly),sha256=gate.gameassembly_sha256),
                                        metadata=dict(path=str(gate.metadata),sha256=gate.metadata_sha256))
    player = Path(unity_player) if unity_player is not None else gate.gameassembly.parent / 'UnityPlayer.dll'
    audit['unityPlayer'] = str(player)
    if not player.is_file():
        audit.update(status='missing', detail='selected UnityPlayer.dll is absent')
        return None, audit
    raw = player.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    audit['unityPlayerSha256'] = actual
    if actual.lower() != pins['unityPlayerSha256'].lower():
        audit.update(status='mismatched', detail='selected UnityPlayer.dll hash differs',
                     expected=pins['unityPlayerSha256'], actual=actual)
        return None, audit
    check = 'pe-image'
    try:
        pe = load_native_mapper(NATIVE_MAPPER_PATH).PeImage(player)
        read = lambda rva, size: pe.bytes_at_va(pe.image_base + rva, size)
        table, size, exception = read_exception_directory(pe)
        index = UnwindChainIndex(exception, read, table_rva=table, image_size=size)
        windows = {}
        for f in c['functions']:
            check = 'function:' + f['role']
            if f['role'] in windows:
                raise ValueError('duplicate role')
            if f['kind'] == 'unwindFamily':
                if index.resolve(f['entryRva']) != f['entryRva']:
                    raise ValueError('entry is not its complete unwind primary')
                if [(a, b-a) for a,b,_ in index.families[f['entryRva']]] != [(w['rva'],w['bytes']) for w in f['ranges']]:
                    raise ValueError('complete unwind family ranges differ')
            elif f['kind'] != 'codeWindow':
                raise ValueError('unknown function boundary')
            chunks = []
            for w in f['ranges']:
                if not 0 < w['bytes'] <= 65536:
                    raise ValueError('unbounded code range')
                data = read(w['rva'], w['bytes'])
                digest = hashlib.sha256(data).hexdigest()
                if digest != w['sha256']:
                    raise ValueError(f'window={w["rva"]:#x} expected={w["sha256"]} actual={digest}')
                chunks.append((w['rva'], data))
            windows[f['role']] = chunks
        roles = set()
        for stage in c['stages']:
            check = 'stage:' + stage['role']
            a, b = stage['beginRva'], stage['endRva']
            if (stage['role'] in roles or not 0 < b-a <= 4096 or
                not any(start <= a < b <= start+len(data) for chunks in windows.values() for start,data in chunks)):
                raise ValueError('stage escapes authenticated code windows or duplicates a role')
            roles.add(stage['role'])
        constants = {}
        for v in c['constants']:
            check = 'constant:' + v['role']
            data = read(v['rva'], v['bytes'])  # Strict PE reader refuses virtual zero-fill.
            if data.hex() != v['hex']:
                raise ValueError('file-backed constant bytes differ')
            constants[v['role']] = data
        check = 'runtime-calibration-storage'
        storage = c['runtimeCalibration']['storageRva']
        offset, section, rva = pe.file_offset_for_va(pe.image_base + storage)
        if offset is not None or not any(s['virtualAddress'] <= rva and rva+16 <= s['virtualAddress']+s['virtualSize'] for s in pe.sections):
            raise ValueError('declared zero-fill storage boundary differs')
        audit.update(status='validated', detail='code families and file-backed constants checked',
                     functionRoles=len(windows), constants=len(constants), runtimeCalibrationValueObserved=False)
        return SimpleNamespace(contract=c, pe=pe, windows=windows, constants=constants), audit
    except (ValueError, KeyError, IndexError) as error:
        audit.update(status='validation_failed', failedCheck=check, detail=str(error)[:700])
        return None, audit

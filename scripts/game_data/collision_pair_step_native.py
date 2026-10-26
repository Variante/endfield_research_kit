"""Authenticate the compiled broadphase-task to pair-filter route.

This proves task types, owner coordinates and original calls on selected bytes.
It does not assign an archived pair to a simulation generation. That requires
observed original production, reference release and run for the same task.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.collision_runtime_mesh_native import load_code_layout, validate_code_layout
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex, read_exception_directory

CONTRACT = CONTRACTS_DIR / 'collision_pair_step_native.json'
SCHEMA = 'endfield.collision-pair-step-native.v3'


def _instruction(raw, at, prefix, width=4):
    prefix = bytes.fromhex(prefix)
    end = at+len(prefix)+width
    if at < 0 or end > len(raw) or raw[at:at+len(prefix)] != prefix:
        raise ValueError('pair-step instruction differs/clipped:'+str(at))
    return int.from_bytes(raw[at+len(prefix):end], 'little', signed=False)


def _rip(window, raw, at):
    value = _instruction(raw, at, '488d05')
    return window['rva']+at+7+struct.unpack('<i', value.to_bytes(4, 'little'))[0]


def _validate_tasks(pe,contract,windows):
    tasks = {t['role']:t for t in contract['taskTypes']}
    names = {n['role']:n for n in contract['taskNames']}
    if len(tasks) != len(contract['taskTypes']) or set(tasks) != set(names):
        raise ValueError('pair-step task/name coverage')
    if contract['runSlot'] != 7 or contract['ownerSceneCell'] != 0:
        raise ValueError('pair-step task dispatch/receiver model')
    leaves = {leaf['role']:leaf for leaf in contract['nameGetterLeaves']}
    for leaf in leaves.values():
        data = bytes.fromhex(leaf['hex'])
        if pe.bytes_at_va(pe.image_base+leaf['rva'],len(data)) != data:
            raise ValueError('pair-step name getter leaf:'+leaf['role'])
    embedded = bytes.fromhex(leaves['embedded']['hex'])
    if embedded != b'\x48\x8b\x41'+bytes([contract['taskNameField']])+b'\xc3':
        raise ValueError('pair-step embedded name coordinate')
    for role, task in tasks.items():
        table = pe.image_base+task['vtableRva']
        if pe.u64_at_va(table+contract['runSlot']*8) != pe.image_base+windows[task['runRole']][0]['rva']:
            raise ValueError('pair-step concrete run vtable:'+role)
        name = names[role]
        if 'sceneField' in task:
            if task['ownerKind'] not in ('internalScene', 'publicScene'):
                raise ValueError('pair-step embedded owner must be Scene:'+role)
            getter = leaves['embedded']['rva']; name_rva = name['nameRva']
        else:
            if task['ownerKind'] != 'nphaseCore':
                raise ValueError('pair-step filter owner must be NPhaseCore')
            getter = name['getterRva']; leaf = leaves[role]
            data = bytes.fromhex(leaf['hex'])
            if len(data) != 8 or data[-1] != 0xc3:
                raise ValueError('pair-step constant name leaf extent')
            name_rva = _rip(dict(rva=getter),data,0)
        if pe.u64_at_va(table+2*8) != pe.image_base+getter:
            raise ValueError('pair-step concrete name vtable:'+role)
        expected = task['name'].encode('ascii')+b'\0'
        if name['text'] != task['name'] or pe.bytes_at_va(pe.image_base+name_rva,len(expected)) != expected:
            raise ValueError('pair-step task name:'+role)

    if {c['taskRole'] for c in contract['constructors']} != set(tasks):
        raise ValueError('pair-step constructor coverage')
    for ctor in contract['constructors']:
        task = tasks[ctor['taskRole']]; window, data = windows[ctor['windowRole']]
        if _rip(window,data,ctor['vtableLea']) != task['vtableRva']:
            raise ValueError('pair-step constructor vtable target:'+task['role'])
        if 'sceneField' in task:
            base = contract['layout']['scene'][task['sceneField']]
            public = task['ownerKind'] == 'publicScene'
            if (_instruction(data,ctor['vtableStore'],'488987' if public else '488986') != base or
                _instruction(data,ctor['ownerStore'],'4889bf' if public else '4889b6') != base+contract['layout']['task']['owner'] or
                _instruction(data,ctor['nameStore'],'488987' if public else '488986') != base+contract['taskNameField'] or
                _rip(window,data,ctor['nameLea']) != names[task['role']]['nameRva']):
                raise ValueError('pair-step constructor Scene/name/owner coordinates:'+task['role'])
        elif (data[ctor['vtableStore']:ctor['vtableStore']+3] != b'\x48\x89\x03' or
              _instruction(data,ctor['ownerStore'],'48894b',1) != contract['layout']['task']['owner']):
            raise ValueError('pair-step constructor NPhaseCore owner')


def validate_program(pe, contract, *, schema=None):
    schema = schema or contract['schema']
    if schema not in (SCHEMA, 'endfield.collision-pair-step-native.v2'):
        raise ValueError('pair-step schema differs')
    windows = validate_code_layout(pe, contract, schema=schema)
    table, size, raw = read_exception_directory(pe)
    index = UnwindChainIndex(raw, lambda at, n: pe.bytes_at_va(pe.image_base+at, n),
                             table_rva=table, image_size=size)
    covered = set()
    for family in contract['codeFamilies']:
        actual = [part['runtimeTriple'] for part in index.family(family['rva'])['ranges']]
        if actual != family['runtimeRanges']:
            raise ValueError('pair-step unwind family differs:'+family['role'])
        slices = sorted((w['rva'], w['rva']+w['bytes'], role) for role, (w, _) in windows.items()
                        if role == family['role'] or role.startswith(family['role']+'_part_'))
        for start, end, _ in actual:
            cursor = start
            for a, b, role in slices:
                if start <= a < end:
                    if a != cursor or b > end:
                        raise ValueError('pair-step family missing/overlapping slice:'+role)
                    cursor = b; covered.add(role)
            if cursor != end:
                raise ValueError('pair-step family incomplete:'+family['role'])
    leaves = set(contract.get('leafWindows', []))
    if covered | leaves != set(windows) or covered & leaves:
        raise ValueError('pair-step undeclared family window')

    _validate_tasks(pe,contract,windows)

    # Reuse the reviewed general pair route, rather than duplicating its body.
    from scripts.game_data.collision_pair_filter_native import CONTRACT as PAIR, validate_program as validate_pair
    from scripts.game_data.collision_geometry_state_native import CONTRACT as TASK, validate as validate_task
    pair = json.loads(PAIR.read_text('utf-8')); task = json.loads(TASK.read_text('utf-8'))
    if pair['nativeInputs'] != contract['nativeInputs'] or task['nativeInputs'] != contract['nativeInputs']:
        raise ValueError('pair-step shared native inputs differ')
    validate_pair(pe,pair); validate_task(pe,task)
    if schema == SCHEMA:
        if contract['simulationSeedRole']!='npSimulate':
            raise ValueError('pair-step original simulation root task differs')
        seeded=next(t for t in contract['taskTypes'] if t['role']==contract['simulationSeedRole'])
        guard=next(w for w in task['codeWindows'] if w['role']=='scene_simulate_guard')
        raw=pe.bytes_at_va(pe.image_base+guard['rva'],guard['bytes'])
        for operand in contract['simulationSeedOperands']:
            if _instruction(raw,operand['offset'],operand['prefix'])!=contract['layout']['scene'][seeded['sceneField']]:
                raise ValueError('pair-step original simulation root release coordinate')
        if contract['publicSceneDelta'] != pair['layout']['scene']['publicDelta']:
            raise ValueError('pair-step public/internal Scene delta differs')
        for role in ('np_simulate_bridge', 'np_collide_bridge'):
            data = windows[role][1]
            prefix = bytes.fromhex('488bc14c8bc24883c1')+bytes([-contract['publicSceneDelta']])+bytes.fromhex('f30f108888240000e9')
            if len(data) != 23 or not data.startswith(prefix):
                raise ValueError('pair-step public Scene bridge differs:'+role)
        for typed in contract['taskTypes'][3:]:
            if typed['ownerKind'] == 'publicScene':
                continue
            data = windows[typed['runRole']][1]
            prefix = b'\x48\x8b\x51'+bytes([contract['layout']['task']['continuation']])+b'\x48\x8b\x49'+bytes([contract['layout']['task']['owner']])+b'\xe9'
            if len(data) != 13 or not data.startswith(prefix):
                raise ValueError('pair-step original task owner/continuation thunk:'+typed['role'])
    wrapper = next(w['rva'] for w in task['codeWindows'] if w['role']=='task_run')
    for typed in contract['taskTypes']:
        if pe.u64_at_va(pe.image_base+typed['vtableRva']+8) != pe.image_base+wrapper:
            raise ValueError('pair-step original run wrapper:'+typed['role'])
    other = {w['role']:w for w in pair['codeWindows']}
    for link in contract['callLinks']:
        window, data = windows[link['role']]; at = link['offset']
        displacement = _instruction(data,at,link['opcode'])
        actual = window['rva']+at+5+struct.unpack('<i',displacement.to_bytes(4,'little'))[0]
        if link['targetContract'] not in ('self','pairFilter'):
            raise ValueError('pair-step unknown call contract')
        target = windows[link['targetRole']][0] if link['targetContract']=='self' else other[link['targetRole']]
        if actual != target['rva']:
            raise ValueError('pair-step original callee:'+link['role'])
    return contract


def load(*, gameassembly, metadata, unityplayer):
    return load_code_layout(gameassembly=Path(gameassembly),metadata=Path(metadata),unityplayer=Path(unityplayer),
        contract_path=CONTRACT,schema=SCHEMA,validator='collision_pair_step_native',validate=validate_program)


def capture_declarations(pe,contract):
    validate_program(pe,contract)
    roles=('postBroadPhase','postBroadPhaseCont','overlapFilter')
    if contract['schema']==SCHEMA:
        roles+=('rigidBodyNarrowPhase','updateShapes','preNarrowPhase','npSimulate','npCollide')
    if tuple(t['role'] for t in contract['taskTypes'])!=roles:
        raise ValueError('pair-step compiled task role order')
    if any(contract['layout']['task'][name]+width>56 for name,width in (('owner',8),('continuation',8))):
        raise ValueError('pair-step task base snapshot bound')
    expected=((84,'task_dependency_wiring'),(85,'post_broadphase_scene'))
    if contract['schema']==SCHEMA:
        expected+=((91,'native_scene_simulate'),(92,'native_scene_collide'),(93,'update_shapes_producer'))
    if tuple((h['kind'],h['windowRole']) for h in contract['hooks'])!=expected:
        raise ValueError('pair-step observer identity/order')
    windows={w['role']:w for w in contract['codeWindows']};hooks=[]
    for hook in contract['hooks']:
        arguments=['pointer','f32','pointer'] if hook['kind'] in (91,92) else ['pointer','pointer']
        if hook['abi']!=dict(arguments=arguments,returnMode='void'):
            raise ValueError('pair-step compiled producer ABI:'+hook['role'])
        w=windows[hook['windowRole']];entry=bytes.fromhex(hook['entryHex'])
        if not 5<=len(entry)<=32 or pe.bytes_at_va(pe.image_base+w['rva'],len(entry))!=entry:
            raise ValueError('pair-step producer hook entry:'+hook['role'])
        hooks.append(dict(**hook,rva=w['rva'],expectedBytes=entry.hex()))
    limits=contract['limits']
    if set(limits)!={'maxProducers','maxSeeds'} or any(type(v) is not int or not 1<=v<=8192 for v in limits.values()):
        raise ValueError('pair-step unsafe producer bounds')
    return dict(contract=contract,hooks=hooks,pins=[dict(module='unityPlayer',rva=w['rva'],
        expectedBytes=pe.bytes_at_va(pe.image_base+w['rva'],w['bytes']).hex()) for w in contract['codeWindows']])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('gameassembly','metadata','unityplayer','output'):
        parser.add_argument('--'+flag,type=Path,required=True)
    args = parser.parse_args(argv)
    contract, gate = load(gameassembly=args.gameassembly,metadata=args.metadata,unityplayer=args.unityplayer)
    report = dict(schema=SCHEMA,status=gate['status'],gate=gate,taskTypes=[],callLinks=[])
    if contract:
        report.update(taskTypes=contract['taskTypes'],callLinks=contract['callLinks'],layout=contract['layout'],
            evidenceBoundary=contract['evidenceBoundary'],livePairToStep='unresolved_requires_original_task_lifecycle')
    from scripts.game_data.collision_runtime_mesh import _output_path
    from scripts.game_data.corpus_common import atomic_write_text
    atomic_write_text(_output_path(args.output),json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=gate['status'],tasks=len(report['taskTypes']),diagnostics=gate.get('diagnostics',[]))))
    return int(contract is None)


if __name__=='__main__':raise SystemExit(main())

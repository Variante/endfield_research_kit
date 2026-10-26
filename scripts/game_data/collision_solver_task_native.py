"""Authenticate PGS task types and the original continuation-release route.

Context-owned solver tasks are separate from Scene-owned broadphase tasks.
The declarations prove compiled layout and dispatch, not a live generation.
"""
from pathlib import Path
import hashlib
import json
import struct

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.collision_runtime_mesh_native import load_code_layout
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex, read_exception_directory

CONTRACT = CONTRACTS_DIR / 'collision_solver_task_native.json'
SCHEMA = 'endfield.collision-solver-task-native.v1'


def validate(pe, contract, *, schema=SCHEMA):
    if contract['schema'] != schema or contract['status'] != 'reviewed':
        raise ValueError('solver-task schema/status')
    windows = {}
    for w in contract['codeWindows']:
        if w['role'] in windows or not 0 < w['bytes'] <= 4096 or w['module'] != 'unityPlayer':
            raise ValueError('solver-task window identity/bounds')
        raw = pe.bytes_at_va(pe.image_base+w['rva'], w['bytes'])
        if hashlib.sha256(raw).hexdigest() != w['sha256']:
            raise ValueError('solver-task code hash:'+w['role'])
        windows[w['role']] = (w, raw)
    table, size, raw = read_exception_directory(pe)
    index = UnwindChainIndex(raw, lambda a,n: pe.bytes_at_va(pe.image_base+a,n), table_rva=table, image_size=size)
    covered = set()
    for f in contract['codeFamilies']:
        actual = [p['runtimeTriple'] for p in index.family(f['rva'])['ranges']]
        if actual != f['runtimeRanges']:
            raise ValueError('solver-task complete unwind family:'+f['role'])
        family = [windows[f['role']]]
        family += [windows[f['role']+'_part_'+str(i)] for i in range(1,len(actual))]
        if [(w['rva'],w['rva']+w['bytes']) for w,_ in family] != [(a,b) for a,b,_ in actual]:
            raise ValueError('solver-task family extent:'+f['role'])
        covered.update(w['role'] for w,_ in family)
    for leaf in contract['leafWindows']:
        if windows[leaf['role']][1] != bytes.fromhex(leaf['hex']):
            raise ValueError('solver-task straight-line leaf:'+leaf['role'])
        covered.add(leaf['role'])
    if covered != set(windows):
        raise ValueError('solver-task incomplete code boundary coverage')
    for p in contract['instructionProbes']:
        value = bytes.fromhex(p['hex'])
        if not any(w['rva'] <= p['rva'] and p['rva']+len(value) <= w['rva']+w['bytes'] for w,_ in windows.values()):
            raise ValueError('solver-task probe outside authenticated body')
        if pe.bytes_at_va(pe.image_base+p['rva'],len(value)) != value:
            raise ValueError('solver-task instruction probe')
    for operand in contract['fieldOperands']:
        w,raw=windows[operand['role']];at=operand['offset'];prefix=bytes.fromhex(operand['prefix'])
        group,name=operand['field'].split('.')
        if operand['mode']!='u8' or raw[at:at+len(prefix)]!=prefix or raw[at+len(prefix)]!=contract['layout'][group][name]:
            raise ValueError('solver-task consumed field operand:'+operand['field'])
    layout = contract['layout']
    if layout != dict(task=dict(manager=16,continuation=24,references=32,prefixBytes=64),
                      root=dict(context=40,islandManager=48,auxiliary=56,runSlot=56)):
        raise ValueError('solver-task compiled adapter coordinates')
    tasks = contract['taskTypes']
    if [t['role'] for t in tasks] != list(range(1,11)):
        raise ValueError('solver-task compiled role order')
    for t in tasks:
        table = pe.image_base+t['vtableRva']
        for slot in contract['sharedTaskSlots']:
            if pe.u64_at_va(table+slot['offset']) != pe.image_base+slot['targetRva']:
                raise ValueError('solver-task common virtual slot:'+t['name'])
        if (pe.u64_at_va(table+16) != pe.image_base+t['getterRva'] or
                pe.u64_at_va(table+56) != pe.image_base+t['runRva'] or
                windows[t['windowRole']][0]['rva'] != t['runRva']):
            raise ValueError('solver-task concrete dispatch:'+t['name'])
        getter = pe.bytes_at_va(pe.image_base+t['getterRva'],8)
        if getter[:3] != b'\x48\x8d\x05' or getter[-1] != 0xc3 or t['getterRva']+7+struct.unpack_from('<i',getter,3)[0] != t['nameRva']:
            raise ValueError('solver-task constant name getter')
        name = t['name'].encode('ascii')+b'\0'
        if pe.bytes_at_va(pe.image_base+t['nameRva'],len(name)) != name:
            raise ValueError('solver-task concrete name')
    root = contract['rootProducer']
    if tuple(root[k] for k in ('kind','rootRole','contextArgument','islandArgument','continuationArgument','auxiliaryArgument','sceneArgument')) != (67,1,0,1,2,3,5):
        raise ValueError('solver-task original PGS argument roles')
    stores = root['rootStoreRvas']
    lea=stores[0]-10;code=pe.bytes_at_va(pe.image_base+lea,7)
    if code[:3]!=b'\x48\x8d\x05' or lea+7+struct.unpack_from('<i',code,3)[0]!=tasks[0]['vtableRva']:
        raise ValueError('solver-task root constructor vtable')
    for a,code in zip(stores,('498906','49897e28','4d897e30','49894638','4d896618')):
        if pe.bytes_at_va(pe.image_base+a,len(bytes.fromhex(code))) != bytes.fromhex(code):
            raise ValueError('solver-task root field store')
    call = pe.bytes_at_va(pe.image_base+root['workerCallRva'],5)
    if call[0] != 0xe8 or root['workerCallRva']+5+struct.unpack_from('<i',call,1)[0] != root['workerTargetRva']:
        raise ValueError('solver-task original root worker call')
    h = contract['hooks']
    if len(h)!=1 or h[0]['kind']!=102 or h[0]['abi']!=dict(arguments=['pointer'],returnMode='void'):
        raise ValueError('solver-task compiled release ABI')
    if next(s['targetRva'] for s in contract['sharedTaskSlots'] if s['offset']==48) != windows['base_release'][0]['rva']:
        raise ValueError('solver-task original release virtual slot')
    if set(contract['limits']) != {'maxReleases','maxAtomics','maxRuns','maxQueued','maxCompletions'} or any(type(n) is not int or not 1<=n<=8192 for n in contract['limits'].values()):
        raise ValueError('solver-task unsafe bounds')
    return contract


def load(*, gameassembly, metadata, unityplayer):
    return load_code_layout(gameassembly=Path(gameassembly),metadata=Path(metadata),unityplayer=Path(unityplayer),
        contract_path=CONTRACT,schema=SCHEMA,validator='collision_solver_task_native',validate=validate)


def capture_declarations(pe, contract):
    validate(pe,contract)
    windows = {w['role']:w for w in contract['codeWindows']}
    hooks=[]
    for h in contract['hooks']:
        w=windows[h['windowRole']];entry=bytes.fromhex(h['entryHex'])
        if not 5<=len(entry)<=32 or pe.bytes_at_va(pe.image_base+w['rva'],len(entry))!=entry:
            raise ValueError('solver-task release hook entry')
        hooks.append(dict(**h,rva=w['rva'],expectedBytes=entry.hex()))
    return dict(contract=contract,hooks=hooks,pins=[dict(module='unityPlayer',rva=w['rva'],
        expectedBytes=pe.bytes_at_va(pe.image_base+w['rva'],w['bytes']).hex()) for w in contract['codeWindows']])


def main(argv=None):
    import argparse
    from scripts.game_data.corpus_common import atomic_write_text
    from scripts.game_data.collision_runtime_mesh import _output_path
    parser=argparse.ArgumentParser(description=__doc__)
    for flag in ('gameassembly','metadata','unityplayer','output'):parser.add_argument('--'+flag,type=Path,required=True)
    a=parser.parse_args(argv);contract,gate=load(gameassembly=a.gameassembly,metadata=a.metadata,unityplayer=a.unityplayer)
    report=dict(schema=SCHEMA,status=gate['status'],gate=gate)
    if contract:report.update(taskTypes=contract['taskTypes'],evidenceBoundary=contract['evidenceBoundary'])
    atomic_write_text(_output_path(a.output),json.dumps(report,indent=2)+'\n');print(json.dumps(gate));return int(contract is None)


if __name__=='__main__':raise SystemExit(main())

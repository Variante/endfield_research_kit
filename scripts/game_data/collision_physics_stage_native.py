"""Validate original geometry-getter and solver adapters against selected bytes."""
from __future__ import annotations

import hashlib
import struct

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.il2cpp.unwind_chains import read_exception_directory, UnwindChainIndex

CONTRACT = CONTRACTS_DIR / 'collision_physics_stage_native.json'
SCHEMA = 'endfield.collision-physics-stage-native.v1'
ROLES = ('triangle_getter', 'pgs_prepare', 'tgs_prepare', 'pgs_contact', 'pgs_static',
         'pgs_contact4', 'pgs_static4', 'pgs_friction_contact', 'pgs_friction_static',
         'pgs_friction_contact4', 'pgs_friction_static4', 'tgs_contact', 'tgs_contact4', 'tgs_extended_contact')
KINDS = (48, 50, 51, *range(54, 64), 65)
ARGUMENTS = (('pointer',)*2, ('pointer',)*3+('u32','u32','pointer'),
             ('pointer',)*3+('u32',)+('pointer',)*3+('f32',)*3+('u32',),
             *(('pointer','u32','pointer'),)*8,
             *(('pointer',)*3+('f32','f32','pointer'),)*3)
RETURNS = ('bool', 'u32', *('void',)*12)


def validate_image(pe, contract, *, cache_layout=None):
    def need(ok, check):
        if not ok:
            raise ValueError('collision-physics-stage:' + check)
    need(contract.get('schema') == SCHEMA and contract.get('status') == 'reviewed', 'schema/status')
    windows = {w['role']: w for w in contract['codeWindows']}
    need(len(windows) == len(contract['codeWindows']), 'duplicate window')
    table, size, raw = read_exception_directory(pe)
    chains = UnwindChainIndex(raw, lambda r, n: pe.bytes_at_va(pe.image_base+r, n), table_rva=table, image_size=size)
    pins=[]
    for w in windows.values():
        ranges=w['ranges']
        need(ranges and ranges[0]['rva'] == w['rva'], 'entry boundary:'+w['role'])
        if 'runtimeTriple' in ranges[0]:
            current=chains.family(w['rva'])['ranges']
            need([p['runtimeTriple'] for p in current] == [p['runtimeTriple'] for p in ranges], 'unwind family:'+w['role'])
        else:
            boundary='complete native range with explicit return' if w['role']=='pgs_prepare_task' else 'complete leaf with explicit return/tail branch'
            need(len(ranges)==1 and ranges[0].get('boundary')==boundary, 'explicit function boundary:'+w['role'])
        for n,p in enumerate(ranges):
            need(1<=p['bytes']<=16384, 'window bound:'+w['role'])
            data=pe.bytes_at_va(pe.image_base+p['rva'],p['bytes'])
            need(hashlib.sha256(data).hexdigest()==p['sha256'], 'window bytes:'+w['role']+':'+str(n))
            pins.append(dict(module='unityPlayer',rva=p['rva'],expectedBytes=data.hex()))
    hooks=contract['hooks']
    need(tuple(h['role'] for h in hooks)==ROLES and tuple(h['kind'] for h in hooks)==KINDS, 'compiled hook order')
    result=[]
    for n,h in enumerate(hooks):
        need(tuple(h['abi']['arguments'])==ARGUMENTS[n] and h['abi']['returnMode']==RETURNS[n], 'compiled ABI:'+h['role'])
        w=windows[h['windowRole']];p=w['ranges'][0]
        data=pe.bytes_at_va(pe.image_base+w['rva'],p['bytes'])
        entry=bytes.fromhex(h['entryHex'])
        need(5<=len(entry)<=32 and data.startswith(entry), 'hook entry:'+h['role'])
        result.append(dict(**h,module='unityPlayer',rva=w['rva'],expectedBytes=entry.hex()))
    need(len({h['rva'] for h in result})==len(result), 'aliased hooks')
    for t in contract['dispatchTables']:
        targets=struct.unpack('<10Q',pe.bytes_at_va(pe.image_base+t['rva'],80))
        need([x-pe.image_base if x else 0 for x in targets]==t['targets'], 'dispatch table:'+t['role'])
        need(t['contactSlots']==([1,3,5,6,7,8] if t['role']=='tgs' else [1,5,6,7,8]), 'contact dispatch slots')
        allowed={h['rva'] for h in result if h['role'].startswith(t['role']+'_')}
        need(all(t['targets'][slot] in allowed for slot in t['contactSlots']), 'uncovered contact dispatch:'+t['role'])
    for p in contract['probes']:
        data=bytes.fromhex(p['hex'])
        need(pe.bytes_at_va(pe.image_base+p['rva'],len(data))==data, 'operand bytes:'+p['role'])
        at=1 if p['mode']=='rel32' else 3
        need((data[0]==0xe8 if at==1 else data[:2] in (b'\x4c\x8d',b'\x48\x8d')) and
             p['rva']+len(data)+struct.unpack_from('<i',data,at)[0]==p['targetRva'], 'operand target:'+p['role'])
    layout=contract['layout']
    if cache_layout is not None:
        from scripts.game_data.collision_runtime_mesh_native import validate_layout
        need(cache_layout['nativeInputs']==contract['nativeInputs'],'cache selected inputs differ')
        validate_layout(pe,cache_layout)
        mesh=cache_layout['layout']['mesh'];triangle=cache_layout['layout']['triangle']
        need(layout['meshVtableRva']==mesh['vtableRva'] and layout['meshCacheOffset']==mesh['holderOffset']+mesh['heldTriangleOffset'] and
             layout['triangleVtableRva']==triangle['vtableRva'],'cache ownership layout bridge')
    # The original hit writer calls the same concrete PxShape vtable slot.
    getter=result[0]['rva']
    need(struct.unpack('<Q',pe.bytes_at_va(pe.image_base+layout['shapeVtableRva']+15*8,8))[0]==pe.image_base+getter, 'getter vtable slot')
    limits=contract['limits']
    bounds=dict(maxGeometry=(1,8192),maxCacheSamples=(1,16384),maxMeshRoutes=(1,16384),
                maxMeshesPerProducer=(1,256),maxCandidatesPerGetter=(1,32),maxPrepCalls=(1,2048),
                maxPrepPairs=(1,16384),maxPairsPerPrep=(1,128),maxHeaders=(1,65536),maxDescriptors=(1,262144),
                maxSolveCalls=(1,4096),maxSolvePairs=(1,16384),maxConstraintBytes=(64,16384),maxPairRoutes=(1,16384),sampleEvery=(1,1024),maxContextBytes=(128,1024),maxSolverCacheBytes=(64,192))
    need(set(limits)==set(bounds) and all(type(limits[k]) is int and lo<=limits[k]<=hi for k,(lo,hi) in bounds.items()), 'unsafe limits')
    need(layout['descriptorBytes']==48 and layout['headerBytes']==8 and layout['geometryBytes']==48 and
         layout['geometryConsumedBytes']==36 and layout['geometryMeshOffset']==40 and layout['cmBytes']<=144, 'compiled record widths')
    result=dict(contract=contract,hooks=result,pins=pins)
    if cache_layout is not None:result['cacheLayout']=cache_layout
    return result


def load(pe, native_inputs):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,label='collision-physics-stage',status='reviewed')
    if {k:v.lower() for k,v in native_inputs.items()}!=contract['nativeInputs']:
        raise ValueError('collision-physics-stage:selected inputs differ')
    from scripts.game_data.collision_runtime_mesh_native import CONTRACT as CACHE_CONTRACT, SCHEMA as CACHE_SCHEMA
    cache,_=read_reviewed_contract(CACHE_CONTRACT,schema=CACHE_SCHEMA,label='collision-stage-cache',status='reviewed')
    return validate_image(pe,contract,cache_layout=cache)

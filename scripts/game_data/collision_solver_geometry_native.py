"""Authenticate primitive geometry bytes usable in saved solver-core samples."""
import hashlib
import json
from pathlib import Path

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.collision_runtime_mesh_native import load_code_layout, validate_layout

CONTRACT=CONTRACTS_DIR/'collision_solver_geometry_native.json'
SCHEMA='endfield.collision-solver-geometry-native.v1'


def validate(pe, c, *, schema=SCHEMA):
    if c['schema']!=schema or c['status']!='reviewed':raise ValueError('solver-geometry schema/status')
    from scripts.game_data.collision_physics_stage_native import validate_image
    shape=json.loads((CONTRACTS_DIR/c['sharedContracts'][0]).read_text('utf-8'))
    stage=json.loads((CONTRACTS_DIR/c['sharedContracts'][1]).read_text('utf-8'))
    if c['sharedContracts']!=['collision_runtime_shape_native.json','collision_physics_stage_native.json'] or c['nativeInputs']!=shape['nativeInputs'] or c['nativeInputs']!=stage['nativeInputs']:
        raise ValueError('solver-geometry shared selected inputs')
    validate_layout(pe,shape,schema=shape['schema']);validate_image(pe,stage)
    s=c['layout']['shape'];core=c['layout']['core'];ss=shape['layout']['shape'];g=shape['layout']['geometry']
    if s!=dict(vtable=ss['vtableRva'],inlineGeometry=ss['inlineGeometry'],bufferFlags=ss['bufferFlags'],
               bufferPointer=ss['bufferPointer'],bufferedGeometry=ss['bufferedGeometry'],geometryMask=ss['geometryBufferedMask']):
        raise ValueError('solver-geometry native public shape fields')
    if core!=dict(apiDelta=stage['layout']['shapeCoreCandidateApiDelta'],geometry=s['inlineGeometry']-stage['layout']['shapeCoreCandidateApiDelta'],prefixBytes=80,
                  trianglePointer=s['inlineGeometry']-stage['layout']['shapeCoreCandidateApiDelta']+g['triangleMesh']):
        raise ValueError('solver-geometry embedded prefix coordinates')
    for name,rule in c['primitives'].items():
        if c['geometryTypes'].get(str(rule['type']))!=name:raise ValueError('solver-geometry typed enum declaration')
        cursor=4
        for field,spec in sorted(rule['fields'].items(),key=lambda item:item[1]['offset']):
            if spec['offset']!=cursor or spec['count'] not in (1,3):raise ValueError('solver-geometry primitive scalar layout')
            cursor+=4*spec['count']
        if cursor!=rule['bytes'] or core['geometry']+cursor>core['prefixBytes']:raise ValueError('solver-geometry primitive extent')
    windows={}
    for w in c['codeWindows']:
        if w['role'] in windows or w['module']!='unityPlayer' or not 1<=w['bytes']<=256:raise ValueError('solver-geometry getter boundary')
        raw=pe.bytes_at_va(pe.image_base+w['rva'],w['bytes'])
        if raw.hex()!=w['leafHex'] or hashlib.sha256(raw).hexdigest()!=w['sha256'] or raw[-1]!=0xc3:
            raise ValueError('solver-geometry complete getter leaf:'+w['role'])
        windows[w['role']]=(w,raw)
    if {x['kind'] for x in c['getters']}!=set(c['primitives']) or len(c['getters'])!=len(c['primitives']):raise ValueError('solver-geometry getter identities')
    for getter in c['getters']:
        w,raw=windows[getter['windowRole']];typ=c['primitives'][getter['kind']]['type']
        if getter['type']!=typ or raw[:7]!=b'\x83\xb9'+s['inlineGeometry'].to_bytes(4,'little')+bytes([typ]):
            raise ValueError('solver-geometry original type predicate')
        if pe.u64_at_va(pe.image_base+s['vtable']+getter['slot']*8)!=pe.image_base+w['rva']:
            raise ValueError('solver-geometry concrete getter vtable')
        if raw[12:16]!=b'\xf6\x41'+bytes([s['bufferFlags'],s['geometryMask']]):raise ValueError('solver-geometry buffered predicate')
        if not any(code in raw for code in (b'\x48\x8b\x49'+bytes([s['bufferPointer']]),b'\x48\x8b\x41'+bytes([s['bufferPointer']]))):
            raise ValueError('solver-geometry buffer pointer')
        if not any(code in raw for code in (b'\x48\x83\xc1'+bytes([s['bufferedGeometry']]),b'\x48\x83\xc0'+bytes([s['bufferedGeometry']]))):
            raise ValueError('solver-geometry buffered geometry address')
        copy=getter['copy']
        if raw[copy['offset']:]!=bytes.fromhex(copy['hex']):raise ValueError('solver-geometry complete typed copy')
        cursor=0
        for offset,width in copy['extents']:
            if offset!=cursor or width not in (4,8):raise ValueError('solver-geometry native copy extent')
            cursor+=width
        if cursor!=c['primitives'][getter['kind']]['bytes']:raise ValueError('solver-geometry native copy size')
    return c


def load(*, gameassembly, metadata, unityplayer):
    return load_code_layout(gameassembly=Path(gameassembly),metadata=Path(metadata),unityplayer=Path(unityplayer),
        contract_path=CONTRACT,schema=SCHEMA,validator='collision_solver_geometry_native',validate=validate)

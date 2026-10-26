"""Authenticate bounded PGS response fields on explicitly selected native files."""
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.collision_runtime_mesh_native import load_code_layout, validate_code_layout

CONTRACT = CONTRACTS_DIR / 'collision_solver_response_native.json'
SCHEMA = 'endfield.collision-solver-response-native.v1'


def validate_image(pe, contract, *, schema=SCHEMA):
    windows=validate_code_layout(pe,contract,schema=schema)
    variants=contract['variants']
    if tuple((v['kind'],v['role'],v['wrapper'],v['core']) for v in variants)!=((58,'pgs_friction_contact','contact_wrapper','contact_core'),(59,'pgs_friction_static','static_wrapper','static_core')):
        raise ValueError('solver-response original adapter identities')
    for v in variants:
        if not v['constraintTags'] or len(set(v['constraintTags']))!=len(v['constraintTags']):
            raise ValueError('solver-response constraint tag declaration')
        for tag in v['constraintTags']:
            if type(tag) is not int or not 0<=tag<10 or pe.u64_at_va(pe.image_base+v['dispatchTableRva']+tag*8)!=pe.image_base+windows[v['wrapper']][0]['rva']:
                raise ValueError('solver-response native dispatch tag')
    mask=contract['vectorMask']
    if bytes.fromhex(mask['hex'])!=b'\xff'*12+b'\0'*4 or pe.bytes_at_va(pe.image_base+mask['rva'],16)!=bytes.fromhex(mask['hex']):
        raise ValueError('solver-response vector lane mask')
    layout=contract['layout'];d,h,b=layout['descriptor'],layout['header'],layout['body']
    if not (0<=d['constraint']<=40 and 0<=d['length']<=46 and d['stride']==48 and
            0<=h['normalCount']<h['bytes'] and 0<=h['frictionCount']<h['bytes'] and h['forceStride']==4 and
            0<h['pointStride']<=256 and 0<h['bytes']<=256 and
            0<=b['vector0']<=20 and b['vector0']+12<=b['vector1']<=20 and b['vector1']%4==0):
        raise ValueError('solver-response bounded consumed layout')
    if contract['limits']!=dict(maxNormals=255,maxConstraintBytes=65536):
        raise ValueError('solver-response compiled sample limits')
    return windows


def load(*,gameassembly,metadata,unityplayer):
    return load_code_layout(gameassembly=gameassembly,metadata=metadata,unityplayer=unityplayer,
        contract_path=CONTRACT,schema=SCHEMA,validator='collision_solver_response_native',validate=validate_image)

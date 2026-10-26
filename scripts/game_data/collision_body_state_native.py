"""Authenticate typed body/shape/scene reads; add no native game calls or hooks."""
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.collision_runtime_mesh_native import validate_layout
from scripts.game_data.il2cpp.native_image import read_reviewed_contract

CONTRACT=CONTRACTS_DIR/'collision_body_state_native.json'
SCHEMA='endfield.collision-body-state-native.v2'


def validate(pe,contract):
    validate_layout(pe,contract,schema=SCHEMA)
    actor=contract['layout']['actor']
    if actor['staticScb']!=actor['scene'] or actor['staticScb']+actor['staticControl']!=actor['control']:
        raise ValueError('collision-body-state:static/dynamic registration offsets differ')
    if contract['representation']!=dict(snapshotBytes=128,filterBytes=32,geometryKind=76,staticClass=1,dynamicClass=2,simulationMask=1,queryMask=2,triggerMask=4):
        raise ValueError('collision-body-state:compiled widths/classes/masks')
    limits=contract['limits']
    if set(limits)!= {'maxBodyStates','sampleEvery'} or not all(type(v) is int for v in limits.values()) or not 1<=limits['maxBodyStates']<=8192 or not 1<=limits['sampleEvery']<=128:
        raise ValueError('collision-body-state:unsafe limits')
    return dict(contract=contract,pins=[dict(module='unityPlayer',rva=w['rva'],expectedBytes=pe.bytes_at_va(pe.image_base+w['rva'],w['bytes']).hex()) for w in contract['codeWindows']])


def load(pe,native_inputs):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,label='collision-body-state',status='reviewed')
    if contract['nativeInputs']!={k:v.lower() for k,v in native_inputs.items()}:raise ValueError('collision-body-state:selected native inputs differ')
    return validate(pe,contract)

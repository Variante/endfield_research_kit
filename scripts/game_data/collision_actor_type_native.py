"""Authenticate actor concrete-type name leaves; infer no pose or simulation state."""
import hashlib,json,struct
from pathlib import Path
from scripts.common import check_installed_native_inputs,sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH,read_reviewed_contract
from scripts.game_data.il2cpp.protocol import load_native_mapper

CONTRACT=CONTRACTS_DIR/'collision_actor_type_native.json'
SCHEMA='endfield.collision-actor-type-native.v1'

def validate(pe,contract):
    if contract['schema']!=SCHEMA or contract['status']!='reviewed':raise ValueError('actor type contract schema/status')
    rows=contract['types'];result={}
    if not 1<=len(rows)<=16:raise ValueError('actor type count bound')
    for row in rows:
        table=row['vtableRva'];getter=row['getterRva'];slot=row['slot'];raw=pe.bytes_at_va(pe.image_base+getter,8)
        if table in result or slot!=1 or pe.u64_at_va(pe.image_base+table+slot*8)!=pe.image_base+getter:
            raise ValueError('actor type concrete vtable/getter')
        if raw[:3]!=b'\x48\x8d\x05' or raw[-1]!=0xc3 or hashlib.sha256(raw).hexdigest()!=row['getterSha256']:
            raise ValueError('actor type complete pure name leaf')
        target=getter+7+struct.unpack_from('<i',raw,3)[0]
        expected=row['name'].encode('ascii')+b'\0'
        if not 1<len(expected)<=128 or target!=row['nameRva'] or pe.bytes_at_va(pe.image_base+target,len(expected))!=expected:
            raise ValueError('actor type target/name')
        result[table]=row['name']
    return result

def load(*,gameassembly,metadata,unityplayer):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,label='collision-actor-type',status='reviewed')
    gate=check_installed_native_inputs(contract['nativeInputs']['gameAssemblySha256'],contract['nativeInputs']['metadataSha256'],gameassembly=gameassembly,metadata=metadata)
    status=dict(status=gate.status,detail=gate.detail)
    if gate.status!='validated':return None,status
    if not Path(unityplayer).is_file():return None,dict(status='missing',detail='UnityPlayer.dll missing')
    if sha256_file(Path(unityplayer)).lower()!=contract['nativeInputs']['unityPlayerSha256']:return None,dict(status='mismatched',detail='UnityPlayer.dll hash differs')
    pe=load_native_mapper(NATIVE_MAPPER_PATH).PeImage(Path(unityplayer))
    if hashlib.sha256(pe.buf).hexdigest()!=contract['nativeInputs']['unityPlayerSha256']:raise ValueError('actor type native changed while opening')
    return validate(pe,contract),status

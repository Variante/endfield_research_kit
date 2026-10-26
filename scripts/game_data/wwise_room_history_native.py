"""Selected complete RoomVerb tone and paired-history diffusion kernels."""
from __future__ import annotations
import struct
import hashlib
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.wwise_room_input_native import load_contract as load_input,validate as validate_input
from scripts.game_data.wwise_source_native import _collect_opened_source_image
from scripts.game_data.wwise_source_queue_native import validate_native_group_declarations,validate_native_group_windows


def load_contract():
    c,_=read_reviewed_contract(CONTRACTS_DIR/'wwise_room_history_native.json',schema='endfield.wwise-room-history-native.v4',status='reviewedCurrentBuild',label='wwise-room-history')
    return c


def validate(c,pipeline,image,selected_inputs):
    if c.get('schema')!='endfield.wwise-room-history-native.v4' or c.get('status')!='reviewedCurrentBuild' or c['nativeInputs']!=selected_inputs:
        raise ValueError('room history schema/status/selected inputs differ')
    source=validate_input(load_input(),pipeline,image,selected_inputs)
    groups=c['nativeGroups']+[source[k] for k in c['borrowedGroups']]
    validate_native_group_declarations(groups)
    _,bodies,records=_collect_opened_source_image(image,'selected AkSoundEngine')
    validate_native_group_windows(groups,image,bodies,records)
    indexed={g['key']:g for g in groups}
    for b in c['callBindings']:
        at=int(b['rva'],16)
        if not any(int(w['rva'],16)<=at and at+5<=int(w['rva'],16)+w['bodyLength'] for w in indexed[b['group']]['windows']):
            raise ValueError('room history caller outside complete body')
        raw=image.bytes_at_va(image.image_base+at,5)
        if raw[0]!=0xe8 or at+5+struct.unpack_from('<i',raw,1)[0]!=int(indexed[b['targetGroup']]['entryRva'],16) or at+5!=int(b['returnRva'],16):
            raise ValueError('room history native call differs')
    for b in c['fieldBindings']:
        at=int(b['rva'],16);raw=bytes.fromhex(b['instructionHex'])
        if not any(int(w['rva'],16)<=at and at+len(raw)<=int(w['rva'],16)+w['bodyLength'] for w in indexed[b['group']]['windows']) or image.bytes_at_va(image.image_base+at,len(raw))!=raw:
            raise ValueError('room diffusion worker field instruction differs')
        displacement=struct.unpack_from('<I',raw,1)[0] if raw[0]==0xbf else raw[-1]
        if displacement!=c['layout'][b['layoutField']]:raise ValueError('room diffusion worker field differs')
    witnesses={w['role']:bytes.fromhex(w['instructionHex']) for w in indexed['roomDiffusionKernel']['instructionWitnesses']}
    if any(witnesses[role][-1]!=c['layout'][field] for role,field in [('index','diffusionIndex'),('ring','diffusionRing'),('gainField','diffusionGain')]) or c['layout']['diffusionLength']!=0 or witnesses['doubleIndex']!=bytes.fromhex('448d0c1b') or c['layout']['diffusionHistoryStrideBytes']!=8:
        raise ValueError('room diffusion paired history layout differs')
    if c['layout']['toneHistoryWords']!=4 or c['layout']['toneMatrixWords']!=32 or c['layout']['toneMatrixHistoryOffset']!=-16:
        raise ValueError('room tone operand extent differs')
    validate_diffusion_configuration(c,indexed,image)
    return indexed


def validate_diffusion_configuration(c,indexed,image):
    """Authenticate the existing parameter owner and complete refresh consumer."""
    d=c['diffusionConfiguration'];g=indexed[d['group']]
    p,_=read_reviewed_contract(CONTRACTS_DIR/(d['parameterOwnerContract']+'.json'),schema='endfield.wwise-effect-parameters-native.v4',status='reviewedCurrentBuild',label='room-diffusion-parameter-owner')
    if p['nativeInputs']!=c['nativeInputs']:raise ValueError('room diffusion parameter owner inputs differ')
    method=p['parameterSchemas'][d['classId']]['setParamsBlock'];start=int(method['rva'],16);size=method['bodyLength']
    if hashlib.sha256(image.bytes_at_va(image.image_base+start,size)).hexdigest()!=method['bodySha256']:raise ValueError('room diffusion parameter body differs')
    raw={}
    for b in d['bulkTransport']:
        at=int(b['rva'],16);data=bytes.fromhex(b['instructionHex'])
        if not start<=at<=start+size-len(data) or image.bytes_at_va(image.image_base+at,len(data))!=data:raise ValueError('room diffusion serialized transport differs')
        raw[b['role']]=data
    if set(raw)!= {'sourceBase','readControl','storeControl'} or raw['sourceBase']!=bytes.fromhex('488d5a')+bytes([d['serializedOffset']]) or raw['readControl']!=bytes.fromhex('f30f1003') or raw['storeControl']!=bytes.fromhex('f30f1141')+bytes([d['storedControlOffset']]):raise ValueError('room diffusion serialized/control relation differs')
    def read(at,n):
        if not any(int(w['rva'],16)<=at and at+n<=int(w['rva'],16)+w['bodyLength'] for w in g['windows']):raise ValueError('room diffusion configuration operand outside complete body')
        return image.bytes_at_va(image.image_base+at,n)
    witnesses={w['role']:bytes.fromhex(w['instructionHex']) for w in g['instructionWitnesses']}
    expected_offsets=[c['layout']['diffusionFirstState']+j*c['layout']['diffusionStateStride']+c['layout']['diffusionGain'] for j in range(c['layout']['diffusionStateCount'])]
    if d['stateGainOffsets']!=expected_offsets or [witnesses[k][-1] for k in ('controlRead','clearRefreshFlag')]!=[d['storedControlOffset'],0] or witnesses['clearRefreshFlag'][-2]!=d['refreshFlagOffset'] or struct.unpack_from('<I',witnesses['changeSelection'],3)[0]!=d['cachedControlOffset']:raise ValueError('room diffusion configuration fields differ')
    if [witnesses[k][-1] for k in ('firstGainStore','secondGainStore','thirdGainStore','fourthGainStore')]!=expected_offsets:raise ValueError('room diffusion gain stores differ')
    if d['thresholdRoles']!=['firstThreshold','secondThreshold','maximum','positiveZero'] or sorted(b['role'] for b in d['constants'])!=['firstThreshold','maximum','scale','secondThreshold']:raise ValueError('room diffusion constant roles differ')
    for b in d['constants']:
        at=int(b['loadRva'],16);data=bytes.fromhex(b['instructionHex']);target=int(b['rva'],16)
        if read(at,len(data))!=data or at+len(data)+struct.unpack_from('<i',data,len(data)-4)[0]!=target or image.bytes_at_va(image.image_base+target,4)!=struct.pack('<I',b['word']):raise ValueError('room diffusion configuration constant differs')

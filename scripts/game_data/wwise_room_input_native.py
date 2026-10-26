"""Authenticate RoomVerb input fold and circular-delay bodies on selected images."""
from __future__ import annotations
import struct
import hashlib
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.wwise_room_blend_native import load_contract as load_room,validate as validate_room
from scripts.game_data.wwise_source_native import _collect_opened_source_image
from scripts.game_data.wwise_source_queue_native import validate_native_group_declarations,validate_native_group_windows


def load_contract():
    c,_=read_reviewed_contract(CONTRACTS_DIR/'wwise_room_input_native.json',schema='endfield.wwise-room-input-observer.v4',status='reviewedCurrentBuild',label='wwise-room-input')
    return c


def validate_tone_transport(c,image):
    b=c['parameterTransport'];p,_=read_reviewed_contract(CONTRACTS_DIR/(b['ownerContract']+'.json'),schema='endfield.wwise-effect-parameters-native.v4',status='reviewedCurrentBuild',label='room-input-tone-owner')
    if p['nativeInputs']!=c['nativeInputs']:raise ValueError('room tone parameter owner inputs differ')
    method=p['parameterSchemas'][b['classId']]['setParamsBlock'];start=int(method['rva'],16);size=method['bodyLength']
    if hashlib.sha256(image.bytes_at_va(image.image_base+start,size)).hexdigest()!=method['bodySha256']:raise ValueError('room tone parameter body differs')
    raw={}
    for name in ('sourceBase','cursor','readByte','storeByte'):
        anchor=b[name];at=int(anchor['rva'],16);data=bytes.fromhex(anchor['instructionHex'])
        if not start<=at<=start+size-len(data) or image.bytes_at_va(image.image_base+at,len(data))!=data:raise ValueError('room tone parameter transport differs')
        raw[name]=data
    if raw['sourceBase'][:3]!=bytes.fromhex('488d5a') or raw['cursor'][:3]!=bytes.fromhex('488d4b') or raw['readByte'][:3]!=bytes.fromhex('0fb641') or raw['storeByte'][:2]!=bytes.fromhex('8887'):raise ValueError('room tone parameter operands differ')
    if sum(struct.unpack('<b',raw[n][-1:])[0] for n in ('sourceBase','cursor','readByte'))!=b['serializedOffset'] or struct.unpack_from('<i',raw['storeByte'],2)[0]!=c['layout'][b['layoutField']]:raise ValueError('room tone serialized/destination offset differs')


def validate(c,pipeline,image,selected_inputs):
    if c.get('schema')!='endfield.wwise-room-input-observer.v4' or c.get('status')!='reviewedCurrentBuild' or c['nativeInputs']!=selected_inputs:raise ValueError('room input schema/status/selected inputs differ')
    room=validate_room(load_room(),pipeline,image,selected_inputs);groups=c['nativeGroups']+[room[k] for k in c['borrowedGroups']]
    validate_native_group_declarations(groups);_,bodies,records=_collect_opened_source_image(image,'selected AkSoundEngine');validate_native_group_windows(groups,image,bodies,records)
    indexed={g['key']:g for g in groups}
    def read(group,at,size):
        if not any(int(w['rva'],16)<=at and at+size<=int(w['rva'],16)+w['bodyLength'] for w in indexed[group]['windows']):raise ValueError('room input instruction outside complete body')
        return image.bytes_at_va(image.image_base+at,size)
    for b in c['callBindings']:
        at=int(b['rva'],16);raw=read(b['group'],at,5)
        if raw[0]!=0xe8 or at+5+struct.unpack_from('<i',raw,1)[0]!=int(indexed[b['targetGroup']]['entryRva'],16) or at+5!=int(b['returnRva'],16):raise ValueError('room input native call differs')
    for b in c['fieldBindings']:
        raw=bytes.fromhex(b['instructionHex'])
        if read(b['group'],int(b['rva'],16),len(raw))!=raw or struct.unpack_from('<i',raw,b['displacementOffset'])[0]!=c['layout'][b['layoutField']]:raise ValueError('room input delay branch field differs')
    for kind in ('roomDelayCopy','roomDelaySwap'):
        witnesses={w['role']:bytes.fromhex(w['instructionHex']) for w in indexed[kind]['instructionWitnesses']}
        if witnesses['index'][-1]!=c['layout']['ringIndex'] or witnesses['buffer'][-1]!=c['layout']['ringPointer'] or c['layout']['ringLength']!=0 or witnesses['length'][-1]>>6:raise ValueError('room circular header differs from native reads')
    unit=c['foldUnit'];at=int(unit['loadRva'],16);raw=bytes.fromhex(unit['instructionHex'])
    if read('roomInputFold',at,len(raw))!=raw or at+len(raw)+struct.unpack_from('<i',raw,len(raw)-4)[0]!=int(unit['rva'],16) or unit['word']!=0x3f800000 or image.bytes_at_va(image.image_base+int(unit['rva'],16),4)!=struct.pack('<I',unit['word']):raise ValueError('room fold unit constant differs')
    validate_tone_transport(c,image)
    return indexed

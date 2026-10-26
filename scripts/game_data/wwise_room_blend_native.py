"""Selected original RoomVerb stereo dispatch and three-buffer blend."""
from __future__ import annotations
import struct
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.wwise_bus_processing_native import load_contract as load_bus,validate as validate_bus
from scripts.game_data.wwise_source_native import _collect_opened_source_image
from scripts.game_data.wwise_source_queue_native import validate_native_group_declarations,validate_native_group_windows


def load_contract():
    c,_=read_reviewed_contract(CONTRACTS_DIR/'wwise_room_blend_native.json',schema='endfield.wwise-room-blend-observer.v2',status='reviewedCurrentBuild',label='wwise-room-blend')
    return c


def validate(c,pipeline,image,selected_inputs):
    if c.get('schema')!='endfield.wwise-room-blend-observer.v2' or c.get('status')!='reviewedCurrentBuild':raise ValueError('room blend contract schema/status differs')
    bus=load_bus()
    if c['nativeInputs']!=selected_inputs or bus['nativeInputs']!=selected_inputs:raise ValueError('room blend selected native inputs differ')
    indexed=validate_bus(bus,pipeline,image)
    groups=list(c['nativeGroups'])+[indexed[k] for k in c['borrowedGroups']]
    validate_native_group_declarations(groups);_,bodies,records=_collect_opened_source_image(image,'selected AkSoundEngine');validate_native_group_windows(groups,image,bodies,records)
    indexed={g['key']:g for g in groups}
    def read(group,at,size):
        if not any(int(w['rva'],16)<=at and at+size<=int(w['rva'],16)+w['bodyLength'] for w in indexed[group]['windows']):raise ValueError('room blend instruction outside complete body')
        return image.bytes_at_va(image.image_base+at,size)
    for b in c['callBindings']:
        at=int(b['rva'],16);raw=read(b['group'],at,5)
        if raw[0]!=0xe8 or at+5+struct.unpack_from('<i',raw,1)[0]!=int(indexed[b['targetGroup']]['entryRva'],16) or at+5!=int(b['returnRva'],16):raise ValueError('room blend native call differs')
    for b in c['abiBindings']:
        raw=bytes.fromhex(b['instructionHex'])
        if read(b['group'],int(b['rva'],16),len(raw))!=raw:raise ValueError('room blend stack/floating ABI differs')
    unit=c['unitConstant'];at=int(unit['loadRva'],16);raw=bytes.fromhex(unit['instructionHex'])
    if read('roomVerbBlend',at,len(raw))!=raw or at+len(raw)+struct.unpack_from('<i',raw,len(raw)-4)[0]!=int(unit['rva'],16) or unit['word']!=0x3f800000 or image.bytes_at_va(image.image_base+int(unit['rva'],16),4)!=struct.pack('<I',unit['word']):raise ValueError('room blend reciprocal unit constant differs')
    d=c['stereoDispatch'];table=int(d['tableRva'],16)
    if d['format']!=12546 or d['tableIndex']!=0 or struct.unpack('<I',read('roomVerbExecute',table,4))[0]!=int(d['branchRva'],16):raise ValueError('room stereo dispatch differs')
    at=int(d['callRva'],16);raw=read('roomVerbExecute',at,5)
    if raw[0]!=0xe8 or at+5+struct.unpack_from('<i',raw,1)[0]!=int(indexed[d['targetGroup']]['entryRva'],16):raise ValueError('room stereo direct call differs')
    return indexed

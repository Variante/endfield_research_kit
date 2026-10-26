"""Selected complete RoomVerb early, late feedback and wet-damping bodies."""
from __future__ import annotations
import struct
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.wwise_room_history_native import load_contract as load_history,validate as validate_history
from scripts.game_data.wwise_source_native import _collect_opened_source_image
from scripts.game_data.wwise_source_queue_native import validate_native_group_declarations,validate_native_group_windows


def load_contract():
    c,_=read_reviewed_contract(CONTRACTS_DIR/'wwise_room_wet_native.json',schema='endfield.wwise-room-wet-native.v1',status='reviewedCurrentBuild',label='wwise-room-wet')
    return c


def validate(c,pipeline,image,selected_inputs):
    if c.get('schema')!='endfield.wwise-room-wet-native.v1' or c.get('status')!='reviewedCurrentBuild' or c['nativeInputs']!=selected_inputs:raise ValueError('room wet schema/status/selected inputs differ')
    previous=validate_history(load_history(),pipeline,image,selected_inputs)
    groups=c['nativeGroups']+[previous[k] for k in c['borrowedGroups']]
    validate_native_group_declarations(groups);_,bodies,records=_collect_opened_source_image(image,'selected AkSoundEngine');validate_native_group_windows(groups,image,bodies,records)
    indexed={g['key']:g for g in groups}
    l=c['layout'];s=c['selection']
    if l['ringHeaderStride']!=24 or [l[k] for k in ('ringLength','ringPointer','ringIndex')]!=[0,8,16] or l['fdnFilterStride']!=12 or l['earlyRightCoefficients']!=l['earlyLeftCoefficients']+s['maxTaps']*4 or l['earlyRightIndices']!=l['earlyLeftIndices']+s['maxTaps']*2 or l['earlyRightCount']!=l['earlyLeftCount']+2:raise ValueError('room wet stored representation differs')
    def read(group,at,size):
        if not any(int(w['rva'],16)<=at and at+size<=int(w['rva'],16)+w['bodyLength'] for w in indexed[group]['windows']):raise ValueError('room wet operand outside complete body')
        return image.bytes_at_va(image.image_base+at,size)
    for b in c['callBindings']:
        at=int(b['rva'],16);raw=read(b['group'],at,5)
        if raw[0]!=0xe8 or at+5+struct.unpack_from('<i',raw,1)[0]!=int(indexed[b['targetGroup']]['entryRva'],16) or at+5!=int(b['returnRva'],16):raise ValueError('room wet direct native call differs')
    for b in c['fieldBindings']:
        raw=bytes.fromhex(b['instructionHex']);at=int(b['rva'],16)
        if read(b['group'],at,len(raw))!=raw or int.from_bytes(raw[b['displacementOffset']:b['displacementOffset']+b['displacementBytes']],'little')!=c['layout'][b['layoutField']]:raise ValueError('room wet worker layout differs')
    if sorted(b['role'] for b in c['constants'])!=['feedbackSumScale','scalarOutputSigns','signMask']:raise ValueError('room feedback required constant roles differ')
    for b in c['constants']:
        at=int(b['loadRva'],16);raw=bytes.fromhex(b['instructionHex']);data=struct.pack('<'+str(len(b['words']))+'I',*b['words'])
        if read('roomFdnKernel',at,len(raw))!=raw or at+len(raw)+struct.unpack_from('<i',raw,len(raw)-4)[0]!=int(b['rva'],16) or image.bytes_at_va(image.image_base+int(b['rva'],16),len(data))!=data:raise ValueError('room feedback constant differs')
        if b['role']=='feedbackSumScale' and (len(b['words'])!=4 or len(set(b['words']))!=1) or b['role']=='signMask' and b['words']!=[0x80000000] or b['role']=='scalarOutputSigns' and b['words']!=[0x3f800000,0xbf800000,0x3f800000,0xbf800000]:raise ValueError('room feedback constant shape differs')
    return indexed

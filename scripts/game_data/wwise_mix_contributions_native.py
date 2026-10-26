"""Authenticate accumulation operands using the existing authored-parameter bodies."""
from __future__ import annotations
import hashlib
import struct
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.wwise_authored_parameters_native import load_authored_parameters_contract
from scripts.game_data.wwise_source_native import _collect_opened_source_image
from scripts.game_data.wwise_source_queue_native import validate_native_group_declarations, validate_native_group_windows


def load_contract():
    value,_=read_reviewed_contract(CONTRACTS_DIR/'wwise_mix_contributions_native.json',
        schema='endfield.wwise-mix-contributions-observer.v2',status='reviewedCurrentBuild',label='wwise-mix-contributions')
    return value


def validate(contract, image, selected_inputs):
    if contract.get('schema')!='endfield.wwise-mix-contributions-observer.v2' or contract.get('status')!='reviewedCurrentBuild':raise ValueError('mix contribution contract schema/status differs')
    owner=load_authored_parameters_contract()
    if contract['nativeInputs']!=selected_inputs or owner['nativeInputs']!=selected_inputs:
        raise ValueError('mix contribution selected native inputs differ')
    if contract['ownerContract']!='wwise_authored_parameters_native':raise ValueError('mix body owner differs')
    keys=contract['borrowedGroups']
    groups=[g for g in owner['nativeGroups'] if g['key'] in keys]
    if len(groups)!=len(keys) or len(set(keys))!=len(keys):raise ValueError('mix contribution body dependency missing')
    validate_native_group_declarations(groups)
    _,bodies,records=_collect_opened_source_image(image,'selected AkSoundEngine')
    validate_native_group_windows(groups,image,bodies,records)
    indexed={g['key']:g for g in groups}
    def read(group,at,length):
        if not any(int(w['rva'],16)<=at and at+length<=int(w['rva'],16)+w['bodyLength'] for w in indexed[group]['windows']):
            raise ValueError('mix instruction outside authenticated body')
        return image.bytes_at_va(image.image_base+at,length)
    for b in contract['callBindings']:
        at=int(b['rva'],16);raw=read(b['group'],at,5)
        if raw[0]!=0xe8 or at+5+struct.unpack_from('<i',raw,1)[0]!=int(indexed[b['targetGroup']]['entryRva'],16) or int(b['returnRva'],16)!=at+5:
            raise ValueError('mix contribution native direct call differs')
    for b in contract['instructionBindings']:
        raw=bytes.fromhex(b['instructionHex'])
        if not 1<=len(raw)<=15 or read(b['group'],int(b['rva'],16),len(raw))!=raw:raise ValueError('mix contribution ABI/arithmetic instruction differs')
    d=contract['rampLaneData'];raw=image.bytes_at_va(image.image_base+int(d['rva'],16),d['bytes'])
    at=int(d['loadRva'],16);binding=next(b for b in contract['instructionBindings'] if int(b['rva'],16)==at)
    ins=bytes.fromhex(binding['instructionHex'])
    if d['bytes']!=32 or hashlib.sha256(raw).hexdigest()!=d['sha256'] or list(struct.unpack('<8I',raw))!=contract['rampLaneWords'] or at+len(ins)+struct.unpack_from('<i',ins,len(ins)-4)[0]!=int(d['rva'],16):
        raise ValueError('mix contribution first ramp lanes differ')
    return indexed

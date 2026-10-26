"""Prepare bounded ECS collision observers from reviewed native declarations."""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.ecs_collision_native import validate_player
from scripts.game_data.streaming.collision_native import validate_join

CONTRACT = CONTRACTS_DIR / 'collision_ecs_capture_native.json'
SCHEMA = 'endfield.collision-ecs-capture-native.v1'
ROLES = ('decode', 'resource_resolve', 'terrain_resolve', 'record_entity', 'resource_object',
         'producer_2', 'producer_5', 'producer_6', 'producer_7', 'producer_9')
ARGUMENTS = (('pointer','i32','pointer','i32','i32'), ('pointer',)*5, ('pointer',)*5,
             ('pointer',)*2, ('pointer',), *(('u64','pointer'),)*5)
RETURNS = ('pointer','bool','bool','void','pointer', *('bool',)*5)


def validate_image(pe, contract, ecs, streaming, marker):
    def need(ok, label):
        if not ok:
            raise ValueError('collision-ecs-capture:' + label)
    need(contract['schema'] == SCHEMA and contract['status'] == 'reviewed', 'schema/status')
    need(all({k:v.lower() for k,v in dep['nativeInputs'].items()} == contract['nativeInputs']
             for dep in (ecs, streaming, marker)), 'selected native inputs differ')
    validate_player(pe, ecs)
    validate_join(pe, streaming, ecs, marker)
    windows = {'ecs': {w['role']:w for w in ecs['codeWindows']},
               'streaming': {w['role']:w for w in streaming['codeWindows']},
               'observer': {w['role']:w for w in contract['codeWindows']}}
    need(len(windows['observer']) == len(contract['codeWindows']) == 2, 'observer window identity')
    for row in windows['observer'].values():
        need(16 <= row['bytes'] <= 4096, 'observer window bound')
        raw = pe.bytes_at_va(pe.image_base+row['rva'], row['bytes'])
        need(hashlib.sha256(raw).hexdigest() == row['sha256'], 'window bytes:' + row['role'])
    layout = contract['layout']
    need(all(layout[f] == ecs['layout'][f] for f in ('actor','userdata','registry')), 'layout bridge')
    need(layout['shapeTaggedUserdata'] == 16 and layout['contextBytes'] == 144, 'compiled read layout')
    need(ecs['decoderABI'] == dict(arguments=list(ARGUMENTS[0]), returnMode='pointer',
         lengthUnit='u32-words', meshElementBytes=4, heightmapArgument='resolved native object instance ID'), 'decoder ABI')
    limits = contract['limits']
    bounds = dict(maxDecoders=(1,8192),maxProducers=(1,16384),maxResources=(1,32768),
                  maxPayloadBytes=(64,65536),maxMeshIds=(1,1024),maxActorsPerProducer=(1,4),
                  maxRegistryCapacity=(1,1048576),maxRows=(200000,600000))
    need(set(limits) == set(bounds) and all(type(limits[k]) is int and lo <= limits[k] <= hi
         for k,(lo,hi) in bounds.items()), 'unsafe observer limits')
    hooks = contract['hooks']
    need(tuple(h['role'] for h in hooks) == ROLES and [h['kind'] for h in hooks] == list(range(37,47)), 'hook order')
    result=[]
    for n,h in enumerate(hooks):
        need(tuple(h['abi']['arguments']) == ARGUMENTS[n] and h['abi']['returnMode'] == RETURNS[n], 'compiled ABI:' + h['role'])
        w=windows[h['owner']][h['windowRole']]
        raw=pe.bytes_at_va(pe.image_base+w['rva'], w['bytes'])
        entry=bytes.fromhex(h['entryHex'])
        need(16 <= len(entry) <= 32 and raw.startswith(entry), 'hook entry:' + h['role'])
        result.append(dict(**h, module='unityPlayer', rva=w['rva'], expectedBytes=raw.hex()))
    need(len({h['rva'] for h in result}) == len(result), 'aliased hook entry')
    witness=contract['registry']; w=windows['ecs'][witness['witnessRole']]
    raw=pe.bytes_at_va(pe.image_base+w['rva']+witness['witnessOffset'],7)
    need(raw.hex() == witness['witnessHex'] and raw[:3] == b'\x48\x8b\x05', 'registry RIP instruction')
    need(w['rva']+witness['witnessOffset']+7+struct.unpack_from('<i',raw,3)[0] == witness['singletonRva'], 'registry address operand')
    # Shape userdata is the same tagged +16 pointer, proved by the selected
    # lookup's first-shape and indexed-shape branches, never guessed from names.
    shape=windows['ecs']['shape_userdata_lookup']
    raw=pe.bytes_at_va(pe.image_base+shape['rva'],shape['bytes'])
    need(bytes.fromhex('488b40104883e0f8') in raw and bytes.fromhex('488b58104883e3f8') in raw, 'shape userdata operands')
    return dict(contract=contract, hooks=result)


def load(pe, native_inputs):
    contract,_ = read_reviewed_contract(CONTRACT, schema=SCHEMA, label='collision-ecs-capture', status='reviewed')
    ecs,_ = read_reviewed_contract(CONTRACTS_DIR/'ecs_collision_native.json', schema='endfield.ecs-collision-native.v2', label='ecs-collision', status='reviewed')
    streaming,_ = read_reviewed_contract(CONTRACTS_DIR/'streaming_collision_native.json', schema='endfield.streaming-collision-native.v2', label='streaming-collision', status='reviewed')
    marker,_ = read_reviewed_contract(CONTRACTS_DIR/'streaming_marker17_native.json', schema='endfield.streaming-marker17-native-contract.v2', label='marker17', status='validated-conditional-static')
    if {k:v.lower() for k,v in native_inputs.items()} != contract['nativeInputs']:
        raise ValueError('collision-ecs-capture:selected inputs differ')
    return validate_image(pe, contract, ecs, streaming, marker)

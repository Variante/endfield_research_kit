"""Prepare bounded ECS collision observers from reviewed native declarations."""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.ecs_collision_native import validate_player, validate_sources
from scripts.game_data.il2cpp.unwind_chains import read_exception_directory, UnwindChainIndex

CONTRACT = CONTRACTS_DIR / 'collision_ecs_capture_native.json'
SCHEMA = 'endfield.collision-ecs-capture-native.v2'
ROLES = ('decode', 'resource_resolve', 'terrain_resolve', 'record_entity', 'resource_object',
         'producer_2', 'producer_5', 'producer_6', 'producer_7', 'producer_9')
ARGUMENTS = (('pointer','i32','pointer','i32','i32'), ('pointer',)*5, ('pointer',)*5,
             ('pointer',)*2, ('pointer',), *(('u64','pointer'),)*5)
RETURNS = ('pointer','bool','bool','void','pointer', *('bool',)*5)


def validate_image(pe, contract, ecs):
    def need(ok, label):
        if not ok:
            raise ValueError('collision-ecs-capture:' + label)
    need(contract['schema'] == SCHEMA and contract['status'] == 'reviewed', 'schema/status')
    need({k:v.lower() for k,v in ecs['nativeInputs'].items()} == contract['nativeInputs'],
         'selected native inputs differ')
    validate_player(pe, ecs)
    selected = {row['selector']:row for row in validate_sources(pe, ecs)}
    windows = {'ecs': {w['role']:w for w in ecs['codeWindows']},
               'observer': {w['role']:w for w in contract['codeWindows']}}
    need(len(windows['observer']) == len(contract['codeWindows']), 'observer window identity')
    for row in windows['observer'].values():
        need(1 <= row['bytes'] <= 4096, 'observer window bound')
        raw = pe.bytes_at_va(pe.image_base+row['rva'], row['bytes'])
        need(hashlib.sha256(raw).hexdigest() == row['sha256'], 'window bytes:' + row['role'])
    table, size, raw = read_exception_directory(pe)
    chains = UnwindChainIndex(raw, lambda at,n:pe.bytes_at_va(pe.image_base+at,n),
                              table_rva=table, image_size=size)
    covered = set()
    for family in contract['codeFamilies']:
        ranges = [part['runtimeTriple'] for part in chains.family(family['rva'])['ranges']]
        need(ranges == family['runtimeRanges'], 'observer unwind family:' + family['role'])
        for n,(start,end,_) in enumerate(ranges):
            role = family['role']+(f'_part_{n}' if n else '')
            row = windows['observer'][role]
            need((row['rva'],row['bytes']) == (start,end-start), 'observer family coverage:' + role)
            covered.add(role)
    need(covered | {'resource_valid'} == set(windows['observer']), 'observer family/leaf coverage')
    for probe in contract['probes']:
        row = windows['observer'][probe['role']]
        expected = bytes.fromhex(probe['hex']); at = probe['offset']
        need(expected and 0 <= at <= row['bytes']-len(expected) and
             pe.bytes_at_va(pe.image_base+row['rva']+at,len(expected)) == expected,
             'observer instruction:' + probe['role'])
    for call in contract['directCalls']:
        row = windows['observer'][call['role']]; at = call['offset']
        need(0 <= at <= row['bytes']-5, 'observer call bound')
        raw = pe.bytes_at_va(pe.image_base+row['rva']+at,5)
        need(raw[0] == 0xe8 and row['rva']+at+5+struct.unpack_from('<i',raw,1)[0] ==
             windows['observer'][call['targetRole']]['rva'], 'observer direct call:' + call['role'])
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
        if h['role'].startswith('producer_'):
            selector = int(h['role'].split('_')[1])
            need(h['owner'] == 'ecs' and h['windowRole'] == selected[selector]['producerRole'],
                 'producer label differs from current selected callback')
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
    need(bytes.fromhex('488b40104883e0f8') in raw and bytes.fromhex('488b78104883e7f8') in raw, 'shape userdata operands')
    return dict(contract=contract, hooks=result)


def load(pe, native_inputs):
    contract,_ = read_reviewed_contract(CONTRACT, schema=SCHEMA, label='collision-ecs-capture', status='reviewed')
    ecs,_ = read_reviewed_contract(CONTRACTS_DIR/'ecs_collision_native.json', schema='endfield.ecs-collision-native.v3', label='ecs-collision', status='reviewed')
    if {k:v.lower() for k,v in native_inputs.items()} != contract['nativeInputs']:
        raise ValueError('collision-ecs-capture:selected inputs differ')
    return validate_image(pe, contract, ecs)

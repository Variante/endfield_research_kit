"""Interpret selected, authenticated Streaming bodies as stored ECS colliders.

The caller authenticates the VFS file, marker directory and native contracts.
This reader never turns serialized row IDs or resource keys into live entities.
"""
from __future__ import annotations

import hashlib
import struct
from collections import Counter

from scripts.game_data.ecs_collision import decode, annotate_parameters
from scripts.game_data.streaming import framing as fmt
from scripts.game_data.streaming.marker17 import parse_marker17_body


def pack_key(words):
    if len(words) != 3 or any(type(w) is not int or not 0 <= w <= 0xffffffff for w in words):
        raise ValueError('streaming-collision: key must have three uint32 words')
    return ((((words[0]<<8)|words[1])<<16)|words[2])&0xffffffff


def project(data: bytes, row: dict, *, source: str, source_contract: dict,
            ecs_contract: dict, native_validated: bool = False) -> dict:
    def need(ok, detail):
        if not ok:raise ValueError(f'{source}: streaming-collision: {detail}')

    need(native_validated is True, 'native source proof required')
    selector=row['rowSelectorU32']; key=row['key']
    need(row['rootMarker'] == 2 and row['marker'] == 17 and row['keyStatus'] == 'unique', 'selected context')
    table=fmt._table_layout(data,row['nestedTableOffset'])
    vectors={f:fmt._bounded_vector(data,table,f,width,source) for f,width in ((3,4),(4,1),(5,4))}
    count=vectors[3][1];need(all(v[1] == count for v in vectors.values()), 'nested parallel counts')
    keys=[fmt._u32(data,vectors[3][0]+4+i*4) for i in range(count)]
    occurrences=Counter(keys)

    def resolve(wanted, marker, width=None):
        need(occurrences[wanted] == 1, f'key={wanted:08X}: expected one occurrence, actual={occurrences[wanted]}')
        index=keys.index(wanted); at=vectors[4][0]+4+index
        need(data[at] == marker, f'key={wanted:08X}, offset={at}: expected marker={marker}, actual={data[at]}')
        slot=vectors[5][0]+4+index*4; target=fmt._bounded_anonymous_target(data,slot,source)
        if width is not None:need(target <= len(data)-width, f'key={wanted:08X}, offset={target}: expected readable span={width}, EOF={len(data)}')
        return index,slot,target

    index,slot,_=resolve(key,17)
    need(index == row['elementIndex'] and slot == row['targetSlotOffset'], 'directory index/slot replay')
    ranges,n=fmt._nested_reference_ranges(data,slot,17,source)
    start,end=ranges[-1][0]+4,ranges[-1][1];body=data[start:end]
    need(n == row['byteCount'], 'body count replay')
    parse_marker17_body(body,source=source,selector=selector,key=key,base_offset=start,native_layout_validated=True)
    profiles={r['selector']:r for r in source_contract['meshSources']}
    meshes=[]; resources=[]; source_count=None

    def resource(words,role):
        resource_key=pack_key(words)
        element,resource_slot,target=resolve(resource_key,source_contract['resourceRead']['resourceMarker'],source_contract['resourceRead']['bytes'])
        raw=data[target:target+16];key64,word8,word12=struct.unpack('<QII',raw)
        return dict(resourceRole=role,key=words,packedKeyHex=f'{resource_key:08X}',elementIndex=element,
                    targetSlot=resource_slot,readStart=target,readEnd=target+16,raw16Hex=raw.hex(),
                    resourceKey64Hex=f'{key64:016X}',word8=word8,word12=word12,
                    nativeValidityPredicate=key64 != 0 and word8 not in (0,11),
                    identityStatus='unresolved-resource-map-to-CAB-PathID',extentStatus='consumed-span-only')
    if selector in profiles:
        profile=profiles[selector];need(key == pack_key(profile['bodyKey']), 'source profile body key')
        _,_,target=resolve(pack_key(profile['countKey']),source_contract['resourceRead']['countMarker'],4)
        source_count=struct.unpack_from('<i',data,target)[0]
        need(0 <= source_count <= min(count,65536,ecs_contract['limits']['maxRecords']), f'mesh count at offset={target}: expected bounded count, actual={source_count}')
        for ordinal in range(source_count):
            words=list(profile['meshKeyBase']);words[2]=ordinal
            meshes.append(dict(meshSlot=ordinal,**resource(words,'mesh')))
    for spec in source_contract['fixedResourceSources']:
        if spec['selector'] == selector:
            need(key == pack_key(spec['bodyKey']), 'fixed resource profile body key')
            resources.append(resource(spec['resourceKey'],spec['resourceRole']))
    projection=decode(body,layout=ecs_contract['layout'],kinds=ecs_contract['kinds'],limits=ecs_contract['limits'],mesh_count=source_count or 0)
    annotate_parameters(projection,ecs_contract['enums'])
    # Preserve the exact byte hash and offsets; avoid duplicating every record's bytes.
    for record in projection['records']:record.pop('rawHex',None)
    return dict(status='decoded-stored-collider',selector=selector,outerRowIndex=row['outerRowIndex'],
                outerRowOffset=row['outerRowOffset'],nestedTableOffset=row['nestedTableOffset'],
                keyHex=f'{key:08X}',bodyStart=start,bodyEnd=end,bodySha256=hashlib.sha256(body).hexdigest(),
                projection=projection,sourceMeshCount=source_count,meshInputs=meshes,resourceInputs=resources,
                terrainResourceStatus='stored-resource-key; runtime texture/height bytes unresolved' if projection['kind'] == 'terrain' else None,
                evidenceBoundary='conditional: default callback-compatible stored definition; runtime root pairing, callback override, resource load, live entity and hit ownership unresolved')
